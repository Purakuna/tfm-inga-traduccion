"""Re-verificacion por codigo de la evidencia que cita el agente en el triage.

La regla de corroboracion no confia en el LLM: cada fuente no-feedback se
comprueba contra los datos reales (lema en lexico/wiki, rango de lineas en el
OCR conteniendo la cita, versiculo en TRAIN). Este modulo solo lee
`datos/splits/train.jsonl`; val y test no se tocan nunca desde el agente.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from src.agent.tools import REF_DOCUMENTO, ROOT, doc_lines, fold

TRAIN_PATH = ROOT / "datos" / "splits" / "train.jsonl"
NON_FEEDBACK_TYPES = ("dictionary", "grammar", "corpus")
MAX_RANGE = 400  # lineas; un rango mayor no es una cita, es el documento
_MARGIN = 3  # tolerancia de lineas alrededor del rango citado
_OVERLAP = 0.6

_RE_RANGE = re.compile(r"^\s*([a-z]+)\s*:\s*L?(\d+)\s*(?:-\s*L?(\d+))?\s*$", re.I)
_RE_VERSE = re.compile(r"^\s*(.+?)\s+(\d+)\s*:\s*(\d+)\s*$")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", fold(text))


def quote_matches(quote: str, haystack: str) -> bool:
    """La cita aparece aproximadamente en el texto (OCR ruidoso, acentos, saltos).

    Primero subcadena sobre tokens plegados; si no, solapamiento de tokens.
    """
    q = _tokens(quote)
    if not q:
        return False
    h = _tokens(haystack)
    if " ".join(q) in " ".join(h):
        return True
    hs = set(h)
    hits = sum(1 for t in q if t in hs)
    return len(q) >= 2 and hits / len(q) >= _OVERLAP


@lru_cache(maxsize=1)
def _lexico() -> dict[str, list[str]]:
    """lema plegado -> textos de sus entradas en la tabla LanceDB `lexico`."""
    import lancedb

    from src.rag.indexes import INDEX_DIR

    table = lancedb.connect(INDEX_DIR).open_table("lexico")
    rows = table.to_arrow().select(["lema", "text"]).to_pylist()
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(fold(r["lema"]).strip(), []).append(r["text"] or "")
    return out


@lru_cache(maxsize=1)
def _train() -> dict[tuple[str, int, int], str]:
    """(libro plegado, cap, vers) -> texto inga + espanol. SOLO el split de train."""
    out: dict[tuple[str, int, int], str] = {}
    with TRAIN_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            key = (fold(str(r["libro"])).strip(), int(r["capitulo"]), int(r["versiculo"]))
            out[key] = out.get(key, "") + " " + r["texto_inga"] + " " + r["texto_es"]
    return out


def _quote_in_dictionary(lema_fold: str, quote: str) -> bool:
    """La cita aparece en el OCR del diccionario en una ventana que nombra al lema."""
    lines = doc_lines("diccionario")
    patron = re.compile(r"(?<![a-z0-9])" + re.escape(lema_fold) + r"(?![a-z0-9])")
    for i, line in enumerate(lines):
        if patron.search(fold(line)) and quote_matches(quote, " ".join(lines[i: i + 3])):
            return True
    return False


def _page_text(page: dict) -> str:
    partes = [page.get("title", ""), page.get("summary", "")]
    for f in page.get("facts", []):
        partes.append(f.get("text", ""))
        partes.extend(s.get("quote", "") or "" for s in f.get("sources", []))
    return " ".join(partes)


def verify_source(src: dict, store: Any = None) -> tuple[bool, str]:
    """Comprueba que una fuente {type, ref, quote} existe de verdad.

    Devuelve (ok, motivo). Las fuentes de tipo feedback no se verifican aqui
    (no cuentan como corroboracion) y devuelven False.
    """
    tipo = str(src.get("type") or src.get("source_type") or "").strip().lower()
    ref = str(src.get("ref") or src.get("source_ref") or "").strip()
    quote = str(src.get("quote") or "").strip()
    if tipo not in NON_FEEDBACK_TYPES:
        return False, f"tipo '{tipo}' no corrobora"
    if not ref:
        return False, "ref vacia"

    if tipo == "dictionary":
        lema = ref.split(":", 1)[1] if ref.lower().startswith("lema:") else ref
        clave = fold(lema).strip()
        if not clave:
            return False, "lema vacio"
        textos = list(_lexico().get(clave, []))
        if store is not None:
            page = store.get_page("lemma:" + clave.replace(" ", "-")) or store.get_page("lemma:" + clave)
            if page:
                textos.append(_page_text(page))
        if not textos:
            return False, f"lema '{lema}' no esta en el lexico ni en la wiki"
        if quote and not quote_matches(quote, " ".join(textos)):
            # El lexico indexado perdio algunas acepciones del OCR (p. ej. "sinchi adj, adv
            # duro; fuerte"): la cita tambien vale si esta en el diccionario escaneado
            # junto al lema.
            if _quote_in_dictionary(clave, quote):
                return True, "lema verificado; cita hallada en el diccionario escaneado"
            return False, f"la cita no coincide con la entrada de '{lema}'"
        return True, "lema verificado"

    if tipo == "grammar":
        m = _RE_RANGE.match(ref)
        if not m or m.group(1).lower() not in ("levinsohn", "rosetta"):
            return False, "ref de gramatica invalida (levinsohn:L<ini>-L<fin> o rosetta:...)"
        lines = doc_lines(REF_DOCUMENTO[m.group(1).lower()])
        ini = int(m.group(2))
        fin = int(m.group(3) or ini)
        if ini < 1 or fin < ini or fin > len(lines) or fin - ini > MAX_RANGE:
            return False, f"rango L{ini}-L{fin} fuera del documento ({len(lines)} lineas)"
        if not quote:
            return False, "una fuente de gramatica exige cita textual"
        tramo = " ".join(lines[max(0, ini - 1 - _MARGIN): fin + _MARGIN])
        if not quote_matches(quote, tramo):
            return False, f"la cita no aparece en L{ini}-L{fin}"
        return True, "rango y cita verificados"

    # corpus
    m = _RE_VERSE.match(ref)
    if not m:
        return False, "ref de corpus invalida (<libro> <cap>:<vers>)"
    key = (fold(m.group(1)).strip(), int(m.group(2)), int(m.group(3)))
    texto = _train().get(key)
    if texto is None:
        return False, f"'{ref}' no esta en train"
    if quote and not quote_matches(quote, texto):
        return False, f"la cita no coincide con {ref}"
    return True, "versiculo de train verificado"


def normalize_ref(tipo: str, ref: str) -> str:
    """Lleva la ref al formato canonico que valida la wiki (seccion 1 del contrato)."""
    tipo, ref = (tipo or "").strip().lower(), (ref or "").strip()
    if tipo == "grammar":
        m = _RE_RANGE.match(ref)
        if m:
            ini = int(m.group(2))
            fin = int(m.group(3) or ini)
            return f"{m.group(1).lower()}:L{ini}-L{fin}"
    if tipo == "dictionary" and not ref.lower().startswith("lema:"):
        return f"lema:{ref}"
    if tipo == "dictionary":
        return "lema:" + ref.split(":", 1)[1].strip()
    if tipo == "corpus":
        m = _RE_VERSE.match(ref)
        if m:
            return f"{m.group(1)} {int(m.group(2))}:{int(m.group(3))}"
    return ref


def verify_evidence(evidence: list[dict], store: Any = None) -> list[dict]:
    """Anota cada evidencia con `verified` y `check` (motivo)."""
    out = []
    for ev in evidence or []:
        if not isinstance(ev, dict):
            continue
        item = {
            "type": str(ev.get("type") or "").strip().lower(),
            "ref": normalize_ref(str(ev.get("type") or ""), str(ev.get("ref") or "")),
            "quote": str(ev.get("quote") or "").strip()[:300],
        }
        if item["type"] == "feedback":
            item["verified"], item["check"] = False, "feedback no corrobora"
        else:
            try:
                item["verified"], item["check"] = verify_source(item, store)
            except Exception as e:  # un fallo de verificacion nunca aprueba
                item["verified"], item["check"] = False, f"error al verificar: {type(e).__name__}"
        out.append(item)
    return out


def is_corroborated(verified_evidence: list[dict]) -> bool:
    """Hay al menos una fuente no-feedback verificada."""
    return any(e.get("verified") and e.get("type") in NON_FEEDBACK_TYPES for e in verified_evidence)
