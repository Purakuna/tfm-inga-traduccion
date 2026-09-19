"""Validacion de paginas, hechos y fuentes de la wiki Inga.

Las reglas salen del contrato (docs/superpowers/specs/2026-09-19-inga-wiki-agent-design.md,
seccion 2 y 3). Este modulo no toca la base de datos: solo revisa formas y
limites. La comprobacion de que un `feedback:<id>` existe la hace el store.
"""
from __future__ import annotations

import re
import unicodedata

KINDS = ("lemma", "suffix", "grammar", "convention", "case")
SECTIONS = ("meaning", "morphology", "usage", "example", "note")
FACT_STATUSES = ("active", "pending", "superseded", "rejected")
PAGE_STATUSES = ("active", "superseded")
FEEDBACK_STATUSES = ("new", "auto_applied", "pending_review", "approved", "rejected")
SOURCE_TYPES = ("dictionary", "grammar", "corpus", "feedback")
DIRECCIONES = ("inga2es", "es2inga")

MAX_TITLE = 120
MAX_SUMMARY = 300
MAX_FACT = 400
MAX_QUOTE = 300
MAX_SLUG = 80
MAX_ALIAS = 80
MAX_ACTIVE_FACTS = 40

_RE_SLUG_PROHIBIDO = re.compile(r"[\s/?#:%\\]")
_RE_REF_GRAMMAR = re.compile(r"^(levinsohn|rosetta):L\d+(-L?\d+)?$")
_RE_REF_DICT = re.compile(r"^lema:.+$")
_RE_REF_FEEDBACK = re.compile(r"^feedback:(\d+)$")

_TILDE_ENIE = chr(0x303)  # tilde combinante de la enie


class ValidationError(ValueError):
    """Error de validacion con mensaje apto para devolver al agente."""


def fold(text: str) -> str:
    """Minusculas y sin tildes; conserva la enie (distingue ni / ñi, ano / año)."""
    if not text:
        return ""
    out = []
    for ch in unicodedata.normalize("NFD", text.lower()):
        if unicodedata.category(ch) == "Mn" and ch != _TILDE_ENIE:
            continue
        out.append(ch)
    res = unicodedata.normalize("NFC", "".join(out))
    # una tilde de enie sobre otra letra que no sea n (raro, OCR) se descarta
    return "".join(
        c for c in res if not (unicodedata.category(c) == "Mn")
    )


def _req_str(value, campo: str, maximo: int | None = None, vacio_ok: bool = False) -> str:
    if value is None and vacio_ok:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{campo}: se esperaba texto")
    value = value.strip()
    if not value and not vacio_ok:
        raise ValidationError(f"{campo}: no puede estar vacio")
    if maximo is not None and len(value) > maximo:
        raise ValidationError(f"{campo}: {len(value)} caracteres, maximo {maximo}")
    return value


def feedback_id_from_ref(ref: str) -> int | None:
    """Devuelve el id numerico de un ref `feedback:<id>` o None."""
    m = _RE_REF_FEEDBACK.match(ref or "")
    return int(m.group(1)) if m else None


def validate_source(src: dict) -> dict:
    """Normaliza una fuente a {"type","ref","quote"} o lanza ValidationError."""
    if not isinstance(src, dict):
        raise ValidationError("source: se esperaba un objeto {type, ref, quote}")
    stype = src.get("type", src.get("source_type"))
    ref = src.get("ref", src.get("source_ref"))
    quote = src.get("quote", "")
    if stype not in SOURCE_TYPES:
        raise ValidationError(
            f"source.type desconocido: {stype!r} (validos: {', '.join(SOURCE_TYPES)})"
        )
    ref = _req_str(ref, "source.ref", 200)
    quote = _req_str(quote, "source.quote", MAX_QUOTE, vacio_ok=True)
    if stype == "dictionary" and not _RE_REF_DICT.match(ref):
        raise ValidationError(f"source.ref de dictionary debe ser 'lema:<lema>': {ref!r}")
    if stype == "grammar" and not _RE_REF_GRAMMAR.match(ref):
        raise ValidationError(
            "source.ref de grammar debe ser 'levinsohn:L<a>-L<b>' o 'rosetta:L<a>-L<b>': "
            f"{ref!r}"
        )
    if stype == "feedback" and not _RE_REF_FEEDBACK.match(ref):
        raise ValidationError(f"source.ref de feedback debe ser 'feedback:<id>': {ref!r}")
    if stype != "feedback" and not quote:
        raise ValidationError(f"source.quote vacio para fuente {stype} ({ref}): cita el texto")
    return {"type": stype, "ref": ref, "quote": quote}


def validate_fact(fact: dict, status: str | None = None) -> dict:
    """Normaliza un hecho a {"section","text","status","sources"}."""
    if not isinstance(fact, dict):
        raise ValidationError("fact: se esperaba un objeto {section, text, sources}")
    section = fact.get("section")
    if section not in SECTIONS:
        raise ValidationError(
            f"fact.section desconocida: {section!r} (validas: {', '.join(SECTIONS)})"
        )
    text = _req_str(fact.get("text"), "fact.text", MAX_FACT)
    st = status or fact.get("status") or "active"
    if st not in ("active", "pending"):
        raise ValidationError(f"fact.status al crear debe ser active o pending: {st!r}")
    sources = fact.get("sources")
    if not isinstance(sources, (list, tuple)) or len(sources) == 0:
        raise ValidationError("fact.sources: cada hecho necesita al menos una fuente")
    vistos = set()
    limpias = []
    for s in sources:
        v = validate_source(s)
        clave = (v["type"], v["ref"], v["quote"])
        if clave not in vistos:
            vistos.add(clave)
            limpias.append(v)
    return {"section": section, "text": text, "status": st, "sources": limpias}


def validate_page(page: dict) -> dict:
    """Normaliza la cabecera de una pagina; exige id == '<kind>:<slug>'."""
    if not isinstance(page, dict):
        raise ValidationError("page: se esperaba un objeto")
    kind = page.get("kind")
    if kind not in KINDS:
        raise ValidationError(f"page.kind desconocido: {kind!r} (validos: {', '.join(KINDS)})")
    slug = _req_str(page.get("slug"), "page.slug", MAX_SLUG)
    if _RE_SLUG_PROHIBIDO.search(slug):
        raise ValidationError(f"page.slug con caracteres no permitidos: {slug!r}")
    if slug != slug.lower():
        raise ValidationError(f"page.slug debe ir en minusculas: {slug!r}")
    esperado = f"{kind}:{slug}"
    pid = page.get("id") or esperado
    if pid != esperado:
        raise ValidationError(f"page.id {pid!r} no coincide con '<kind>:<slug>' = {esperado!r}")
    title = _req_str(page.get("title"), "page.title", MAX_TITLE)
    summary = _req_str(page.get("summary", ""), "page.summary", MAX_SUMMARY, vacio_ok=True)
    aliases_in = page.get("aliases") or []
    if not isinstance(aliases_in, (list, tuple)):
        raise ValidationError("page.aliases: se esperaba una lista")
    aliases = []
    for a in aliases_in:
        a = _req_str(a, "page.aliases[]", MAX_ALIAS)
        if a not in aliases:
            aliases.append(a)
    return {"id": pid, "kind": kind, "slug": slug, "title": title,
            "summary": summary, "aliases": aliases}
