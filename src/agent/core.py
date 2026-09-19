"""Nucleo del agente wiki: translate, ask y triage_feedback.

Los tres son generadores que emiten eventos {"event": <tipo>, "data": {...}}
con las formas de la seccion 5 del contrato. Siempre terminan con `done`, y
cualquier excepcion se convierte en un evento `error` previo.

El bucle de function calling es manual (sin function calling automatico del
SDK) para poder emitir cada llamada como evento, respetar el tope de llamadas
y conservar intactas las partes que devuelve el modelo (thought signatures).
"""
from __future__ import annotations

import os

import json
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Iterator

from google.genai import types

from src.agent import hints, llm, prompts
from src.agent.cli.resources import CliContext, build_registry
from src.agent.tools import (
    CLI_TOOL,
    Toolbox,
    cap,
    cli_declaration,
    declarations,
    search_examples,
    summarize_result,
    wiki_path,
)

# El agente investiga lo que necesite. Estos topes NO son un presupuesto de trabajo: son un
# freno de seguridad contra bucles y gasto descontrolado (se ajustan por variable de entorno).
MAX_TOOL_CALLS = int(os.environ.get("INGA_AGENT_MAX_CALLS", "60"))
MAX_TOOL_TURNS = int(os.environ.get("INGA_AGENT_MAX_TURNS", "30"))
MAX_PAGES = 12
MAX_PAGES_CHARS = 9000
PER_PAGE_CHARS = 1500
SUFFIX_SLOTS = 4  # cupos que los sufijos pueden quitarle a los lemas dentro de MAX_PAGES
N_EXAMPLES = 5
TRACE_TOOL_CHARS = 1500
# El triage investiga Y escribe por la CLI. Los topes van separados para que leer nunca
# se coma las llamadas que hacen falta para escribir; tambien son frenos de seguridad.
TRIAGE_READ_CALLS = MAX_TOOL_CALLS
TRIAGE_CLI_CALLS = 20
TRIAGE_MAX_TURNS = MAX_TOOL_TURNS

DIRECCIONES = ("inga2es", "es2inga")
MODES = ("fast", "agent")
CONFIDENCES = ("low", "medium", "high")
SECTIONS = ("meaning", "morphology", "usage", "example", "note")
KINDS = ("lemma", "suffix", "grammar", "convention", "case")
VERDICTS = ("supported", "needs_review", "contradicted")

_RE_PAGE_ID = re.compile(r"\b(?:lemma|suffix|grammar|convention|case):[a-z0-9ñü][a-z0-9ñü_\-']*", re.I)

# El embedding de la consulta es una llamada de red; corre en paralelo a la navegacion.
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent-retrieve")


def ev(event: str, **data: Any) -> dict:
    return {"event": event, "data": data}


def _status(stage: str, message: str) -> dict:
    return ev("status", stage=stage, message=message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get_store(store: Any) -> Any:
    if store is not None:
        return store
    from src.wiki.store import WikiStore

    return WikiStore()


# --- navegacion y precarga -----------------------------------------------------

def navigate(text: str, direccion: str, store: Any) -> tuple[str, list[dict]]:
    """normalize + resolve de src.wiki.navigate, con forma de salida garantizada."""
    from src.wiki import navigate as nav

    normalized = nav.normalize(text) if direccion == "inga2es" else " ".join(text.split())
    tokens = []
    for t in nav.resolve(text, direccion, store) or []:
        item = {
            "token": t.get("token", ""),
            "normalized": t.get("normalized", ""),
            "lemma_pages": list(t.get("lemma_pages") or []),
            "suffix_pages": list(t.get("suffix_pages") or []),
            "resolved": bool(t.get("resolved")),
        }
        # Extras de la implementacion real (no estan en el contrato, no estorban):
        # sufijos pelados aunque aun no tengan pagina, y marca de palabra funcional.
        if t.get("suffixes"):
            item["suffixes"] = list(t["suffixes"])
        if t.get("stopword"):
            item["stopword"] = True
        tokens.append(item)
    return normalized, tokens


def select_pages(tokens: list[dict], max_pages: int = MAX_PAGES) -> list[str]:
    """Elige que paginas precargar: lemas antes que sufijos, por rondas.

    Ronda 0 toma el primer candidato de cada palabra, ronda 1 el segundo, etc.,
    para que una palabra con muchos candidatos no deje sin pagina a las demas.
    """
    def rondas(campo: str) -> list[str]:
        out: list[str] = []
        listas = [list(t.get(campo) or []) for t in tokens]
        for r in range(max((len(l) for l in listas), default=0)):
            for l in listas:
                if r < len(l) and l[r] not in out:
                    out.append(l[r])
        return out

    lemas, sufijos = rondas("lemma_pages"), rondas("suffix_pages")
    n_suf = min(len(sufijos), SUFFIX_SLOTS)
    elegidas = lemas[: max_pages - n_suf]
    elegidas += sufijos[: max_pages - len(elegidas)]
    return elegidas


def load_pages(
    store: Any, page_ids: list[str], max_chars: int = MAX_PAGES_CHARS, from_files: bool = False
) -> tuple[list[dict], dict[str, str]]:
    """Carga paginas como markdown acotado. Devuelve (metadatos, {id: markdown}).

    Cada pagina va encabezada por su archivo en el montaje wiki/ para que el
    modelo pueda navegar desde ahi con fs_leer / fs_grep. Con `from_files` se
    usa el archivo materializado (trae los ids de hecho `[f_xxxxxxxx]`, que el
    triage necesita); si no existe, se cae a render_markdown.
    """
    meta, md = [], {}
    usados = 0
    for pid in page_ids:
        page = store.get_page(pid)
        if page is None:
            continue
        ruta = wiki_path(store, pid)
        texto = None
        if from_files and ruta and getattr(store, "pages_root", None):
            archivo = store.pages_root / ruta[len("wiki/"):]
            if archivo.is_file() and not archivo.is_symlink():
                texto = archivo.read_text(encoding="utf-8")
        if texto is None:
            texto = store.render_markdown(pid)
        texto = cap(texto, PER_PAGE_CHARS + (700 if from_files else 0))
        if ruta:
            texto = f"[archivo: {ruta}]\n{texto}"
        if usados + len(texto) > max_chars and md:
            break
        usados += len(texto)
        md[pid] = texto
        meta.append({"id": page["id"], "kind": page["kind"], "title": page["title"],
                     "summary": page.get("summary", "")})
    return meta, md


def candidate_paths(store: Any, tokens: list[dict], loaded: set[str]) -> dict[str, str]:
    """Ruta en wiki/ de las paginas candidatas que NO se precargaron (para que el agente las abra)."""
    out: dict[str, str] = {}
    for t in tokens:
        for pid in list(t.get("lemma_pages") or [])[:6] + list(t.get("suffix_pages") or [])[:4]:
            if pid not in loaded and pid not in out:
                ruta = wiki_path(store, pid)
                if ruta:
                    out[pid] = ruta
    return out


# --- parseo tolerante del JSON final --------------------------------------------

def parse_json_object(text: str) -> dict | None:
    """Extrae el primer objeto JSON de la respuesta, tolerando cercas y texto alrededor."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.I)
    t = re.sub(r"\s*```$", "", t)
    candidatos = [t]
    ini, fin = t.find("{"), t.rfind("}")
    if ini != -1 and fin > ini:
        candidatos.append(t[ini: fin + 1])
    for c in candidatos:
        for variante in (c, re.sub(r",\s*([}\]])", r"\1", c)):
            try:
                obj = json.loads(variante)
            except ValueError:
                continue
            if isinstance(obj, dict):
                return obj
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                return obj[0]
    return None


def parse_translation(text: str) -> dict:
    """Normaliza la respuesta final a la forma de la seccion 4, sin lanzar nunca."""
    obj = parse_json_object(text)
    if obj is None:
        m = re.search(r'"translation"\s*:\s*"((?:[^"\\]|\\.)*)"', text or "")
        if m:
            try:
                trad = json.loads('"' + m.group(1) + '"')
            except ValueError:
                trad = m.group(1)
            obj = {"translation": trad, "confidence": "low",
                   "notes": "La respuesta del modelo llego con JSON incompleto."}
        else:
            limpio = re.sub(r"^```(?:json)?|```$", "", (text or "").strip()).strip()
            obj = {"translation": limpio, "confidence": "low",
                   "notes": "El modelo no devolvio JSON; se tomo el texto como traduccion."}
    trad = obj.get("translation")
    if isinstance(trad, list):
        trad = " ".join(str(x) for x in trad)
    alts = obj.get("alternatives") or []
    if isinstance(alts, str):
        alts = [alts]
    alts = [str(a).strip() for a in alts if str(a).strip() and str(a).strip() != str(trad or "").strip()][:2]
    conf = str(obj.get("confidence") or "").strip().lower()
    used = obj.get("used_pages") or []
    if isinstance(used, str):
        used = [used]
    return {
        "translation": str(trad or "").strip(),
        "alternatives": alts,
        "confidence": conf if conf in CONFIDENCES else "low",
        "notes": str(obj.get("notes") or "").strip(),
        "used_pages": [str(u).strip() for u in used if _RE_PAGE_ID.fullmatch(str(u).strip())],
    }


# --- bucle manual de function calling -----------------------------------------

def tool_loop(
    contents: list,
    system: str,
    toolbox: Toolbox,
    calls_log: list[dict],
    max_calls: int | None = None,
    stream: bool = False,
    thinking_level: str | None = "LOW",
    max_turns: int | None = None,
    extra_decls: tuple = (),
    gate: Any = None,
    force_first: str | None = None,
) -> Iterator[dict]:
    """Bucle de herramientas. Emite tool_call/tool_result (y answer_delta si stream).

    Es un generador cuyo valor de retorno (via `yield from`) es el texto final.
    Cada turno del modelo se anade al historial tal cual llego (con sus thought
    signatures); las respuestas de todas las llamadas paralelas de un turno van
    juntas en un unico Content de rol user.

    `max_calls` y `max_turns` son frenos de seguridad altos, no un presupuesto:
    el modelo decide cuanto investigar. Cada turno es una ida y vuelta al modelo
    (2-4 s); las llamadas paralelas de un mismo turno salen casi gratis.

    `gate(nombre)` permite un presupuesto por herramienta: si devuelve texto, la
    llamada no se ejecuta y ese texto es la respuesta. `force_first` obliga a
    que el primer turno llame a esa herramienta. El turno final del modelo
    tambien se anade a `contents`, para poder continuar la conversacion.
    """
    max_calls = MAX_TOOL_CALLS if max_calls is None else max_calls
    max_turns = MAX_TOOL_TURNS if max_turns is None else max_turns
    decls = list(declarations()) + list(extra_decls)
    texto_total = ""
    empujado = False
    turnos = 0
    for _ in range(max_turns + 3):
        agotado = len(calls_log) >= max_calls or turnos >= max_turns
        config = llm.build_config(system, tools=decls, thinking_level=thinking_level,
                                  allow_tools=not agotado,
                                  force_tool=force_first if turnos == 0 else None)
        parts: list[types.Part] = []
        if stream:
            turno_con_texto = False
            for chunk in llm.generate_stream(contents, config):
                nuevas = llm.response_parts(chunk)
                parts.extend(nuevas)
                delta = llm.parts_text(nuevas)
                if delta:
                    if texto_total and not turno_con_texto:
                        delta = "\n\n" + delta  # separa el texto de turnos distintos
                    turno_con_texto = True
                    texto_total += delta
                    yield ev("answer_delta", text=delta)
        else:
            parts = llm.response_parts(llm.generate(contents, config))
            texto_total = llm.parts_text(parts) or texto_total

        llamadas = [p.function_call for p in parts if p.function_call]
        if not llamadas:
            if texto_total.strip() or empujado:
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
                return texto_total
            # Turno vacio (p. ej. function call malformado): se pide el cierre una vez.
            empujado = True
            if parts:
                contents.append(types.Content(role="model", parts=parts))
            contents.append(types.Content(role="user", parts=[types.Part(text=prompts.FORCE_FINAL)]))
            continue

        contents.append(types.Content(role="model", parts=parts))
        turnos += 1
        respuestas = []
        for fc in llamadas:
            args = dict(fc.args or {})
            veto = gate(fc.name) if gate else None
            if agotado or len(calls_log) >= max_calls:
                salida = "Tope de seguridad de herramientas alcanzado: responde con lo que ya tienes."
            elif veto:
                salida = veto
            else:
                n = len(calls_log) + 1
                yield ev("tool_call", id=n, name=fc.name, args=args)
                yield _status("tool", f"Consultando {fc.name}")
                salida = toolbox.call(fc.name, args)
                calls_log.append({"id": n, "name": fc.name, "args": args,
                                  "output": salida[:TRACE_TOOL_CHARS]})
                yield ev("tool_result", id=n, name=fc.name,
                         summary=summarize_result(fc.name, args, salida), chars=len(salida))
            respuestas.append(types.Part(function_response=types.FunctionResponse(
                id=fc.id, name=fc.name, response={"result": salida})))
        contents.append(types.Content(role="user", parts=respuestas))
    return texto_total


# --- translate ------------------------------------------------------------------

def translate(
    text: str, direccion: str, mode: str = "fast", store: Any = None, save: bool = True
) -> Iterator[dict]:
    """Traduce con la wiki precargada. `save=False` no deja fila en translations (eval)."""
    try:
        yield from _translate(text, direccion, mode, store, save)
    except Exception as e:
        yield ev("error", message=f"{type(e).__name__}: {str(e)[:300]}")
    yield ev("done")


def _translate(text: str, direccion: str, mode: str, store: Any, save: bool) -> Iterator[dict]:
    t0 = time.time()
    text = (text or "").strip()
    if not text:
        raise ValueError("texto vacio")
    if direccion not in DIRECCIONES:
        raise ValueError("direccion debe ser inga2es o es2inga")
    if mode not in MODES:
        raise ValueError("mode debe ser fast o agent")
    store = _get_store(store)

    fut_examples = _pool.submit(search_examples, text, direccion, N_EXAMPLES)

    yield _status("normalize", "Normalizando la ortografia al estandar del corpus")
    yield _status("navigate", "Resolviendo cada palabra contra la wiki")
    normalized, tokens = navigate(text, direccion, store)
    yield ev("navigation", normalized=normalized, tokens=tokens)

    pages_meta, pages_md = load_pages(store, select_pages(tokens))
    yield ev("pages", pages=pages_meta)

    yield _status("retrieve", "Buscando oraciones parecidas en el corpus de entrenamiento")
    try:
        examples = fut_examples.result(timeout=30)
    except Exception:  # sin ejemplos se puede traducir igual
        examples = []
    yield ev("examples", examples=examples)

    pistas = hints.build(store, tokens, direccion)
    prompt = prompts.user_translate(text, normalized, direccion, pistas, examples,
                                    other_paths=candidate_paths(store, tokens, set(pages_md)) if mode == "agent" else None)
    calls_log: list[dict] = []
    toolbox = Toolbox(store)
    if mode == "fast":
        yield _status("think", f"Traduciendo con {len(pages_md)} paginas y {len(examples)} ejemplos")
        config = llm.build_config(prompts.system_translate(direccion, agent=False), json_output=True)
        resp = llm.generate(prompt, config)
        raw = llm.parts_text(llm.response_parts(resp))
        if not raw.strip():
            raise RuntimeError(f"Gemini no devolvio texto: {llm.finish_reason(resp)}")
    else:
        yield _status("think", "El agente revisa las paginas y decide si necesita consultar mas")
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        raw = yield from tool_loop(
            contents, prompts.system_translate(direccion, agent=True, max_calls=MAX_TOOL_CALLS),
            toolbox, calls_log,
        )
        if not raw.strip():
            raise RuntimeError("El agente termino sin respuesta")

    yield _status("write", "Armando el resultado")
    final = parse_translation(raw)
    if not final["translation"]:
        raise RuntimeError("El modelo no devolvio una traduccion")
    conocidas = set(pages_md) | set(toolbox.pages_read)
    final["used_pages"] = [p for p in final["used_pages"] if p in conocidas or store.get_page(p)]

    elapsed = round(time.time() - t0, 2)
    translation_id = uuid.uuid4().hex
    trace = {
        "navigation": {"normalized": normalized, "tokens": tokens},
        "pages": pages_meta,
        "pages_markdown": pages_md,
        "hints": pistas,
        "examples": examples,
        "tool_calls": calls_log,
        "final": final,
        "model": llm.model_name(),
        "elapsed_s": elapsed,
    }
    if save:
        translation_id = store.save_translation({
            "id": translation_id, "created_at": _now(), "direccion": direccion,
            "source_text": text, "normalized_text": normalized, "output": final["translation"],
            "mode": mode, "trace_json": trace,
        })
    yield ev("result", translation_id=translation_id, **final, mode=mode, elapsed_s=elapsed)


# --- ask ------------------------------------------------------------------------

def _trace_of(translation: dict) -> dict:
    trace = translation.get("trace")
    if trace is None:
        raw = translation.get("trace_json")
        if isinstance(raw, str) and raw:
            try:
                trace = json.loads(raw)
            except ValueError:
                trace = None
        elif isinstance(raw, dict):
            trace = raw
    return trace or {}


def cited_pages(answer: str, store: Any) -> list[str]:
    """Ids de pagina mencionados en la respuesta que existen de verdad en la wiki."""
    out: list[str] = []
    for m in _RE_PAGE_ID.finditer(answer or ""):
        pid = m.group(0).rstrip("-'").lower()
        if pid not in out and store.get_page(pid) is not None:
            out.append(pid)
    return out


def ask(
    translation_id: str, question: str, history: list[dict] | None = None, store: Any = None
) -> Iterator[dict]:
    try:
        yield from _ask(translation_id, question, history, store)
    except Exception as e:
        yield ev("error", message=f"{type(e).__name__}: {str(e)[:300]}")
    yield ev("done")


def _ask(translation_id: str, question: str, history: list[dict] | None, store: Any) -> Iterator[dict]:
    question = (question or "").strip()
    if not question:
        raise ValueError("pregunta vacia")
    store = _get_store(store)
    translation = store.get_translation(translation_id)
    if translation is None:
        raise ValueError(f"no existe la traduccion {translation_id}")
    trace = _trace_of(translation)

    yield _status("retrieve", "Cargando la traza registrada de la traduccion")
    contents = [types.Content(role="user", parts=[types.Part(
        text=prompts.user_ask(translation, trace, "(contexto cargado; espera la pregunta)"))]),
        types.Content(role="model", parts=[types.Part(text="Traza cargada.")])]
    for h in (history or [])[-8:]:
        rol = "model" if h.get("role") == "assistant" else "user"
        contenido = str(h.get("content") or "").strip()
        if contenido:
            contents.append(types.Content(role=rol, parts=[types.Part(text=contenido[:2000])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))

    yield _status("think", "Revisando la traza y las fuentes citadas")
    calls_log: list[dict] = []
    system = prompts.SYSTEM_ASK.replace("{max_calls}", str(MAX_TOOL_CALLS))
    answer = yield from tool_loop(contents, system, Toolbox(store), calls_log, stream=True)
    answer = answer.strip()
    if not answer:
        raise RuntimeError("El modelo no devolvio respuesta")
    yield ev("answer", text=answer, cited_pages=cited_pages(answer, store))


# --- triage de feedback ---------------------------------------------------------

def triage_feedback(feedback_id: int, store: Any = None) -> Iterator[dict]:
    try:
        yield from _triage(feedback_id, store)
    except Exception as e:
        yield ev("error", message=f"{type(e).__name__}: {str(e)[:300]}")
    yield ev("done")


def _triage_context(feedback: dict, store: Any) -> tuple[list[dict], dict[str, str], str]:
    """Paginas relacionadas con la correccion y resumen de la traduccion original."""
    ids: list[str] = []
    resumen = ""
    if feedback.get("translation_id"):
        tr = store.get_translation(feedback["translation_id"])
        if tr:
            trace = _trace_of(tr)
            final = trace.get("final") or {}
            ids.extend(final.get("used_pages") or [])
            resumen = (f"Modo {tr.get('mode')}. Notas del traductor: {final.get('notes', '')}\n"
                       f"Paginas usadas: {', '.join(final.get('used_pages') or []) or 'ninguna'}")
    inga = feedback.get("source_text") if feedback.get("direccion") == "inga2es" else feedback.get("correction")
    try:
        _, tokens = navigate(str(inga or ""), "inga2es", store)
        ids.extend(p for p in select_pages(tokens, 8) if p not in ids)
    except Exception:
        pass
    meta, md = load_pages(store, ids[:8], max_chars=7000, from_files=True)
    return meta, md, resumen


def derive_outcome(ctx: CliContext) -> tuple[str, str]:
    """(veredicto, estado del feedback) derivados de lo ESCRITO, no de lo que diga el modelo.

    todos los hechos activos -> supported / auto_applied
    algun hecho pendiente    -> needs_review / pending_review
    solo no-change           -> contradicted / rejected (por el agente, con su motivo)
    nada                     -> needs_review / pending_review (que decida una persona)
    """
    if ctx.facts:
        if all(f["status"] == "active" for f in ctx.facts):
            return "supported", "auto_applied"
        return "needs_review", "pending_review"
    if ctx.no_change:
        return "contradicted", "rejected"
    return "needs_review", "pending_review"


def _triage(feedback_id: int, store: Any) -> Iterator[dict]:
    store = _get_store(store)
    feedback = store.get_feedback(int(feedback_id))
    if feedback is None:
        raise ValueError(f"no existe el feedback {feedback_id}")

    yield _status("navigate", "Ubicando las paginas de la wiki que toca la correccion")
    pages_meta, pages_md, resumen = _triage_context(feedback, store)
    yield ev("pages", pages=pages_meta)

    yield _status("think", "El agente investiga la correccion en las fuentes")
    ctx = CliContext(store=store, feedback_id=feedback["id"], actor=f"agent:feedback:{feedback['id']}")
    registry = build_registry(ctx)
    toolbox = Toolbox(store, cli=registry)
    calls_log: list[dict] = []
    contents = [types.Content(role="user", parts=[types.Part(
        text=prompts.user_triage(feedback, list(pages_md.values()), resumen))])]
    system = prompts.SYSTEM_TRIAGE.replace("{max_calls}", str(TRIAGE_READ_CALLS))
    cli_decl = (cli_declaration(registry.describe()),)

    def gate(name: str) -> str | None:
        """Presupuesto separado: leer no puede gastarse las llamadas que hacen falta para escribir."""
        es_cli = name == CLI_TOOL
        usadas = sum(1 for c in calls_log if (c["name"] == CLI_TOOL) == es_cli)
        if es_cli and usadas >= TRIAGE_CLI_CALLS:
            return "Presupuesto de inga_cli agotado: cierra con el JSON de la justificacion."
        if not es_cli and usadas >= TRIAGE_READ_CALLS:
            return ("Presupuesto de lectura agotado. Con lo que ya viste, registra AHORA el resultado con "
                    "inga_cli (add-fact, supersede-fact, upsert-page o no-change) y luego cierra.")
        return None

    total = TRIAGE_READ_CALLS + TRIAGE_CLI_CALLS
    raw = yield from tool_loop(contents, system, toolbox, calls_log, max_calls=total,
                               max_turns=TRIAGE_MAX_TURNS, extra_decls=cli_decl, gate=gate)
    if not ctx.facts and not ctx.no_change and gate(CLI_TOOL) is None:
        # El modelo cerro sin escribir (a veces hasta afirma que escribio). Se le exige el registro:
        # el primer turno queda obligado a llamar a inga_cli.
        yield _status("think", "El agente no registro nada: se le exige escribir el resultado con inga_cli")
        contents.append(types.Content(role="user", parts=[types.Part(text=prompts.TRIAGE_MUST_WRITE)]))
        raw2 = yield from tool_loop(contents, system, toolbox, calls_log, max_calls=total, max_turns=MAX_TOOL_TURNS,
                                    extra_decls=cli_decl, gate=gate, force_first=CLI_TOOL)
        raw = raw2 if (raw2 or "").strip() else raw

    yield _status("write", "Derivando el veredicto de lo que quedo escrito en la wiki")
    obj = parse_json_object(raw) or {}
    rationale = str(obj.get("rationale") or "").strip() or (raw or "").strip()[:1200]
    verdict, status = derive_outcome(ctx)
    if ctx.no_change and not ctx.facts:
        rationale = (rationale + " " if rationale else "") + "[Motivo registrado: " + " | ".join(ctx.no_change) + "]"
    if not rationale:
        rationale = "El agente no entrego una justificacion legible."
    if not ctx.facts and not ctx.no_change:
        rationale += " [Codigo: el agente no escribio nada ni declaro no-change; pasa a revision humana.]"
    elif verdict == "needs_review" and ctx.facts:
        rationale += (" [Codigo: al menos un hecho quedo sin fuente no-feedback verificable, asi que queda "
                      "pendiente hasta que una persona lo revise.]")

    errors = [f"{a['action'].get('op')}: {a['result'].get('error')}" for a in ctx.applied
              if not a["result"].get("ok")]
    triage = {
        "verdict": verdict, "status": status, "llm_verdict": str(obj.get("verdict") or "").strip().lower() or None,
        "rationale": rationale, "evidence": ctx.evidence, "facts": ctx.facts, "actions": ctx.applied,
        "no_change": ctx.no_change, "errors": errors, "tool_calls": calls_log,
        "model": llm.model_name(), "created_at": _now(),
    }
    campos: dict[str, Any] = {"status": status, "triage_json": json.dumps(triage, ensure_ascii=False)}
    if status == "rejected":
        # Rechazado por el agente: queda a la vista en Revision (historial) con su motivo.
        campos.update(reviewer="agent", reviewed_at=_now(), review_note=" | ".join(ctx.no_change)[:1000])
    store.update_feedback(feedback["id"], **campos)
    yield ev("triage", feedback_id=feedback["id"], verdict=verdict, status=status,
             rationale=rationale, evidence=ctx.evidence, facts=ctx.facts)
