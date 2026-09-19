"""Recursos de `inga_cli`: Wiki (lecturas y escrituras) y Feedback (lecturas).

La regla de corroboracion vive AQUI, en el camino de escritura, y la aplica el
codigo, no el modelo (seccion 8.2):
- todo hecho escrito en una corrida de triage cita `feedback:<id>`;
- queda `active` solo si ademas trae >= 1 fuente no-feedback que el codigo
  re-verifica (lema existente, cita hallada en el rango de lineas citado,
  versiculo en train); si no, se fuerza a `pending`;
- las fuentes no verificables nunca llegan a la wiki.
El contexto (`CliContext`) registra lo escrito para que el triage derive de ahi
el veredicto y el estado del feedback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agent.cli.registry import Action, ActionError, Registry, Resource
from src.agent.verify import normalize_ref, verify_source

Section = Literal["meaning", "morphology", "usage", "example", "note"]
Kind = Literal["lemma", "suffix", "grammar", "convention", "case"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceIn(_In):
    """Fuente corroborante. La fuente feedback:<id> la agrega el codigo: no la incluyas."""

    type: Literal["dictionary", "grammar", "corpus"]
    ref: str = Field(min_length=1, max_length=200, description=(
        "dictionary: lema:<lema>; grammar: levinsohn:L<ini>-L<fin> o rosetta:L<ini>-L<fin> "
        "(lineas de fuentes/gramatica.md o fuentes/rosetta.md); corpus: <libro> <cap>:<vers>"))
    quote: str = Field(min_length=1, max_length=300,
                       description="Cita textual COPIADA de la fuente (el codigo la re-verifica).")


class FactIn(_In):
    section: Section
    text: str = Field(min_length=3, max_length=400,
                      description="Una frase clara en espanol que se entienda sola.")
    sources: list[SourceIn] = Field(default_factory=list, max_length=4, description=(
        "Fuentes corroborantes verificables. Con al menos una verificada el hecho queda activo; "
        "con la lista vacia queda pendiente de revision humana."))


class AddFactIn(_In):
    page_id: str = Field(min_length=3, description="Id de la pagina (lemma:sinchi) o su ruta (wiki/lemma/sinchi.md).")
    fact: FactIn


class SupersedeFactIn(_In):
    fact_id: str = Field(pattern=r"^f_[0-9a-f]{8}$", description="Id del hecho activo a reemplazar, como aparece en la pagina: [f_xxxxxxxx].")
    new_fact: FactIn


class UpsertPageIn(_In):
    kind: Kind
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[^\s/?#:%\\A-Z]+$",
                      description="Minusculas, sin espacios (usa guiones).")
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(default="", max_length=300)
    aliases: list[str] = Field(default_factory=list, max_length=8)
    facts: list[FactIn] = Field(min_length=1, max_length=5)


class NoChangeIn(_In):
    reason: str = Field(min_length=15, max_length=600,
                        description="Por que la wiki no debe cambiar (que dicen las fuentes).")
    evidence: list[SourceIn] = Field(default_factory=list, max_length=4,
                                     description="Fuentes que contradicen o no respaldan la correccion.")


class GetPageIn(_In):
    page_id: str = Field(min_length=3, description="Id (lemma:sinchi) o ruta (wiki/lemma/sinchi.md).")


class FindPagesIn(_In):
    query: str = Field(min_length=1, max_length=80)
    kind: Kind | None = None
    limit: int = Field(default=10, ge=1, le=20)


class FeedbackGetIn(_In):
    id: int | None = Field(default=None, description="Id del feedback; por defecto el de esta corrida.")


class FeedbackListIn(_In):
    status: Literal["new", "auto_applied", "pending_review", "approved", "rejected"] | None = None
    limit: int = Field(default=10, ge=1, le=30)


@dataclass
class CliContext:
    """Estado de una corrida: a que feedback pertenece y que se escribio."""

    store: Any
    feedback_id: int | None = None
    actor: str = "agent"
    facts: list[dict] = field(default_factory=list)      # {"fact_id","page_id","text","status"}
    evidence: list[dict] = field(default_factory=list)   # {"type","ref","quote","verified","check"}
    applied: list[dict] = field(default_factory=list)    # {"action","result"}
    no_change: list[str] = field(default_factory=list)
    forced: dict[str, int] = field(default_factory=dict)  # intentos con fuentes no verificables


# --- regla de corroboracion en el camino de escritura -----------------------------

def _check_sources(ctx: CliContext, sources: list[SourceIn]) -> tuple[list[dict], list[dict]]:
    """Re-verifica cada fuente. Devuelve (verificadas, rechazadas con motivo) y las anota como evidencia."""
    ok, malas = [], []
    for s in sources:
        item = {"type": s.type, "ref": normalize_ref(s.type, s.ref), "quote": s.quote[:300]}
        try:
            verificada, motivo = verify_source(item, ctx.store)
        except Exception as e:  # un fallo de verificacion nunca aprueba
            verificada, motivo = False, f"error al verificar: {type(e).__name__}"
        anotada = {**item, "verified": verificada, "check": motivo}
        if anotada not in ctx.evidence:
            ctx.evidence.append(anotada)
        if verificada and item not in ok:
            ok.append(item)
        elif not verificada:
            malas.append({"ref": item["ref"], "motivo": motivo})
    return ok, malas


def _prepare(ctx: CliContext, fact: FactIn, clave: str) -> tuple[dict, str, list[dict]]:
    """Arma el hecho final: fuentes verificadas + feedback, y el estado que decide el CODIGO."""
    ok, malas = _check_sources(ctx, fact.sources)
    if fact.sources and not ok:
        # Hay fuentes pero ninguna verifica: primero se da la oportunidad de corregirlas.
        ctx.forced[clave] = ctx.forced.get(clave, 0) + 1
        if ctx.forced[clave] <= 2:
            detalle = "; ".join(f"{m['ref']}: {m['motivo']}" for m in malas)
            raise ActionError(
                f"Error: ninguna fuente pudo verificarse ({detalle}). No se escribio nada. Copia la cita "
                "literal de la fuente (fs_grep / fs_leer en fuentes/) y usa la ref exacta; o reenvia con "
                "\"sources\": [] para dejar el hecho pendiente de revision humana."
            )
        # tercer intento fallido: se escribe igual, pero pendiente y sin esas fuentes
    sources = list(ok)
    if ctx.feedback_id is not None:
        fb = ctx.store.get_feedback(ctx.feedback_id) or {}
        cita = str(fb.get("correction") or fb.get("comment") or "")[:300]
        sources.append({"type": "feedback", "ref": f"feedback:{ctx.feedback_id}", "quote": cita})
    if not sources:
        raise ActionError("Error: sin feedback asociado, un hecho necesita al menos una fuente verificable.")
    status = "active" if ok else "pending"
    return {"section": fact.section, "text": " ".join(fact.text.split()), "sources": sources}, status, malas


def _page_id(ctx: CliContext, ref: str) -> str:
    ref = ref.strip()
    if ref.endswith(".md") or ref.startswith("wiki/"):
        to_id = getattr(ctx.store, "page_id_for_path", None)
        pid = to_id(ref) if to_id else None
        if not pid:
            raise ActionError(f"Error: la ruta '{ref}' no corresponde a ninguna pagina. Usa el id (lemma:<slug>).")
        return pid
    return ref


def _apply(ctx: CliContext, action: dict, textos: list[str], status: str, malas: list[dict]) -> dict:
    res = ctx.store.apply_action(action, actor=ctx.actor)
    ctx.applied.append({"action": action, "result": res})
    if not res.get("ok"):
        raise ActionError(f"Error: la wiki rechazo la accion: {res.get('error')}")
    nuevos = [{"fact_id": fid, "page_id": res.get("page_id"), "text": t, "status": status}
              for fid, t in zip(res.get("fact_ids") or [], textos)]
    ctx.facts.extend(nuevos)
    out = {"ok": True, "page_id": res.get("page_id"), "fact_ids": res.get("fact_ids"), "status": status,
           "version": res.get("version")}
    if status == "pending":
        out["nota"] = "Sin fuente no-feedback verificada: el hecho queda pendiente de revision humana."
    if malas:
        out["fuentes_descartadas"] = malas
    return out


def _add_fact(ctx: CliContext, data: AddFactIn) -> dict:
    pid = _page_id(ctx, data.page_id)
    if ctx.store.get_page(pid) is None:
        raise ActionError(f"Error: la pagina {pid} no existe. Buscala con find-pages o creala con upsert-page.")
    fact, status, malas = _prepare(ctx, data.fact, f"add:{pid}:{data.fact.text[:40]}")
    return _apply(ctx, {"op": "add_fact", "page_id": pid, "fact": fact, "status": status},
                  [fact["text"]], status, malas)


def _supersede_fact(ctx: CliContext, data: SupersedeFactIn) -> dict:
    fact, status, malas = _prepare(ctx, data.new_fact, f"sup:{data.fact_id}")
    return _apply(ctx, {"op": "supersede_fact", "fact_id": data.fact_id, "new_fact": fact, "status": status},
                  [fact["text"]], status, malas)


def _upsert_page(ctx: CliContext, data: UpsertPageIn) -> dict:
    pid = f"{data.kind}:{data.slug}"
    if ctx.store.get_page(pid) is not None:
        raise ActionError(f"Error: la pagina {pid} ya existe; desde feedback no se reescribe su cabecera. "
                          "Usa add-fact (o supersede-fact) sobre ella.")
    facts, estados, malas = [], [], []
    for i, f in enumerate(data.facts):
        fact, status, m = _prepare(ctx, f, f"ups:{pid}:{i}")
        facts.append({**fact, "status": status})
        estados.append(status)
        malas.extend(m)
    page = {"id": pid, "kind": data.kind, "slug": data.slug, "title": data.title,
            "summary": data.summary, "aliases": data.aliases}
    res = ctx.store.apply_action({"op": "upsert_page", "page": page, "facts": facts}, actor=ctx.actor)
    ctx.applied.append({"action": {"op": "upsert_page", "page": page, "facts": facts}, "result": res})
    if not res.get("ok"):
        raise ActionError(f"Error: la wiki rechazo la accion: {res.get('error')}")
    for fid, f in zip(res.get("fact_ids") or [], facts):
        ctx.facts.append({"fact_id": fid, "page_id": pid, "text": f["text"], "status": f["status"]})
    out = {"ok": True, "page_id": pid, "fact_ids": res.get("fact_ids"), "status": estados}
    if malas:
        out["fuentes_descartadas"] = malas
    return out


def _no_change(ctx: CliContext, data: NoChangeIn) -> dict:
    _check_sources(ctx, data.evidence)
    ctx.no_change.append(data.reason)
    return {"ok": True, "registrado": "sin cambios en la wiki", "reason": data.reason}


def _get_page(ctx: CliContext, data: GetPageIn) -> dict:
    pid = _page_id(ctx, data.page_id)
    page = ctx.store.get_page(pid)
    if page is None:
        raise ActionError(f"Error: la pagina {pid} no existe. Prueba find-pages.")
    return page


def _find_pages(ctx: CliContext, data: FindPagesIn) -> dict:
    return {"pages": ctx.store.find_pages(data.query, kind=data.kind, limit=data.limit)}


def _feedback_public(row: dict) -> dict:
    return {k: row.get(k) for k in ("id", "created_at", "author", "direccion", "source_text", "model_output",
                                    "correction", "comment", "translation_id", "status", "reviewer", "review_note")}


def _feedback_get(ctx: CliContext, data: FeedbackGetIn) -> dict:
    fid = data.id if data.id is not None else ctx.feedback_id
    if fid is None:
        raise ActionError("Error: indica el id del feedback: --input '{\"id\": 3}'.")
    row = ctx.store.get_feedback(fid)
    if row is None:
        raise ActionError(f"Error: no existe el feedback {fid}.")
    return _feedback_public(row)


def _feedback_list(ctx: CliContext, data: FeedbackListIn) -> dict:
    return {"feedback": [_feedback_public(r) for r in ctx.store.list_feedback(status=data.status, limit=data.limit)]}


def build_registry(ctx: CliContext) -> Registry:
    wiki = Resource("Wiki", "paginas y hechos citados de la wiki inga")
    wiki.add(Action("add-fact", "agrega un hecho a una pagina existente; input {page_id, fact:{section,text,sources:[{type,ref,quote}]}}",
                    AddFactIn, _add_fact, "write"))
    wiki.add(Action("supersede-fact", "reemplaza un hecho activo erroneo; input {fact_id, new_fact:{section,text,sources}}",
                    SupersedeFactIn, _supersede_fact, "write"))
    wiki.add(Action("upsert-page", "crea una pagina nueva con sus hechos; input {kind,slug,title,summary,aliases,facts:[...]}",
                    UpsertPageIn, _upsert_page, "write"))
    wiki.add(Action("no-change", "declara que la wiki no debe cambiar; input {reason, evidence:[{type,ref,quote}]}",
                    NoChangeIn, _no_change, "write"))
    wiki.add(Action("get-page", "pagina completa como JSON; input {page_id}", GetPageIn, _get_page))
    wiki.add(Action("find-pages", "busca paginas; input {query, kind?, limit?}", FindPagesIn, _find_pages))
    fb = Resource("Feedback", "correcciones enviadas por usuarios")
    fb.add(Action("get", "un feedback (por defecto el de esta corrida); input {id?}", FeedbackGetIn, _feedback_get))
    fb.add(Action("list", "feedback recientes; input {status?, limit?}", FeedbackListIn, _feedback_list))
    return Registry([wiki, fb], ctx)
