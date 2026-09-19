"""Vista markdown de la wiki en datos/wiki/pages/ (seccion 8.1 del contrato).

Las filas de SQLite son la fuente de verdad; este arbol es una vista generada
que el agente LEE como archivos y que nunca se edita a mano:

    pages/index.md            como esta organizado el arbol + conteos
    pages/log.md              una linea por accion aplicada (solo se agrega)
    pages/<kind>/index.md     una linea por pagina: - [titulo](archivo.md) - resumen
    pages/<kind>/<archivo>.md pagina con front matter, hechos y fuentes

Este modulo no importa store.py (store lo importa a el): las funciones reciben
el WikiStore como argumento.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

KIND_TITULO = {
    "lemma": "Lemas (diccionario inga)", "suffix": "Sufijos", "grammar": "Gramatica",
    "convention": "Convenciones de traduccion", "case": "Casos resueltos",
}
KIND_DESCRIPCION = {
    "lemma": "una pagina por palabra inga del diccionario; significados citados, notas dialectales",
    "suffix": "una pagina por sufijo: funcion, forma y ejemplos citados de la gramatica",
    "grammar": "temas de gramatica (orden, tiempos, clausulas) citados de Levinsohn y el apendice",
    "convention": "decisiones de estilo y ortografia para traducir",
    "case": "correcciones concretas aprendidas del feedback",
}
SECTION_TITULO = {
    "meaning": "Significado", "morphology": "Morfologia", "usage": "Uso",
    "example": "Ejemplos", "note": "Notas",
}
ESTADO = {"active": "activo", "pending": "pendiente", "superseded": "reemplazado",
          "rejected": "rechazado"}
MAX_INDEX_BYTES = 400_000
_INDEX_SUMMARY = 110


# ---------------------------------------------------------------- nombres de archivo
def ascii_slug(slug: str) -> str:
    """Nombre de archivo: minusculas, espacios a guion, plegado a ASCII (ñ -> n)."""
    s = unicodedata.normalize("NFD", (slug or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9._-]+", "-", s).strip("-.")
    return s or "pagina"


def relative_path(kind: str, slug: str, tomados) -> str:
    """Ruta '<kind>/<archivo>.md' libre; las colisiones reciben sufijo numerico."""
    base = ascii_slug(slug)
    if base.startswith("index"):  # index.md e index-a.md son de los indices
        base = "p-" + base
    cand = f"{kind}/{base}.md"
    n = 2
    while cand in tomados:
        cand = f"{kind}/{base}-{n}.md"
        n += 1
    return cand


# ---------------------------------------------------------------- pagina
def _una_linea(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def _fact_lines(f: dict) -> list[str]:
    extra = ""
    if f["status"] == "pending":
        extra = " (estado: pendiente)"
    elif f["status"] == "superseded":
        por = f" por {f['superseded_by']}" if f.get("superseded_by") else ""
        extra = f" (estado: reemplazado{por})"
    elif f["status"] == "rejected":
        extra = " (estado: rechazado)"
    elif f.get("superseded_by"):
        extra = f" (reemplazo pendiente: {f['superseded_by']})"
    out = [f"- [{f['id']}] {_una_linea(f['text'])}{extra}"]
    for s in f["sources"]:
        cita = f' "{_una_linea(s["quote"])}"' if s.get("quote") else ""
        out.append(f"  - fuente: {s['type']} {s['ref']}{cita}")
    return out


def render_page(page: dict) -> str:
    """Texto del archivo de una pagina (get_page con include_inactive=True)."""
    fm = [
        "---",
        f"id: {page['id']}",
        f"kind: {page['kind']}",
        f"title: {json.dumps(page['title'], ensure_ascii=False)}",
        f"status: {page['status']}",
        f"version: {page['version']}",
        f"aliases: {json.dumps(page.get('aliases') or [], ensure_ascii=False)}",
        f"updated_at: {page['updated_at']}",
        "---",
        "",
        f"# {page['title']}",
    ]
    lines = fm
    if page.get("summary"):
        lines += ["", _una_linea(page["summary"])]
    vivos = [f for f in page["facts"] if f["status"] in ("active", "pending")]
    historial = [f for f in page["facts"] if f["status"] in ("superseded", "rejected")]
    actual = None
    for f in vivos:
        if f["section"] != actual:
            actual = f["section"]
            lines += ["", f"## {SECTION_TITULO.get(actual, actual)}"]
        lines += _fact_lines(f)
    if not vivos:
        lines += ["", "(sin hechos activos)"]
    if historial:
        lines += ["", "## Historial"]
        for f in historial:
            lines += _fact_lines(f)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- escritura
def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_page(store, page_id: str) -> str | None:
    """Re-renderiza el archivo de una pagina; devuelve su ruta relativa."""
    rel = store.path_for(page_id)
    page = store.get_page(page_id, include_inactive=True)
    if rel is None or page is None:
        return None
    _write(Path(store.pages_root) / rel, render_page(page))
    return rel


def _index_line(row: dict) -> str:
    resumen = _una_linea(row["summary"])
    if len(resumen) > _INDEX_SUMMARY:
        resumen = resumen[:_INDEX_SUMMARY - 4].rstrip() + " ..."
    archivo = row["path"].split("/", 1)[1]
    return f"- [{row['title']}]({archivo})" + (f" - {resumen}" if resumen else "")


def write_kind_index(store, kind: str) -> None:
    """<kind>/index.md; si pasa de ~400 KB se parte por letra en index-<letra>.md."""
    raiz = Path(store.pages_root) / kind
    filas = store.page_rows(kind)
    cabecera = [
        f"# {KIND_TITULO.get(kind, kind)} ({len(filas)} paginas)", "",
        f"Tipo `{kind}`: {KIND_DESCRIPCION.get(kind, '')}.",
        "Este indice sirve para ELEGIR que pagina abrir, nunca para responder: "
        "abre la pagina y cita sus hechos y fuentes.", "",
    ]
    lineas = [_index_line(r) for r in filas]
    texto = "\n".join(cabecera + lineas) + "\n"
    raiz.mkdir(parents=True, exist_ok=True)
    for viejo in raiz.glob("index-*.md"):
        viejo.unlink()
    if len(texto.encode("utf-8")) <= MAX_INDEX_BYTES:
        _write(raiz / "index.md", texto)
        return
    grupos: dict[str, list[str]] = {}
    for r, linea in zip(filas, lineas):
        letra = r["path"].split("/", 1)[1][:1]
        letra = letra if letra.isalpha() else "0"
        grupos.setdefault(letra, []).append(linea)
    partes = []
    for letra in sorted(grupos):
        _write(raiz / f"index-{letra}.md", "\n".join(
            [f"# {KIND_TITULO.get(kind, kind)} - {letra.upper()} ({len(grupos[letra])} paginas)", ""]
            + grupos[letra]) + "\n")
        partes.append(f"- [{letra.upper()}](index-{letra}.md) - {len(grupos[letra])} paginas")
    _write(raiz / "index.md", "\n".join(
        cabecera + ["El indice es grande y esta partido por letra inicial del archivo:", ""]
        + partes) + "\n")


def write_root_index(store) -> None:
    stats = store.stats()
    lines = [
        "# Wiki Inga", "",
        "Vista en markdown de la wiki curada (la fuente de verdad son las filas de SQLite; "
        "estos archivos se regeneran y no se editan a mano).",
        "Este indice sirve para ELEGIR que pagina abrir, nunca para responder.", "",
        "## Como esta organizado", "",
    ]
    for kind in KIND_TITULO:
        n = stats["pages"].get(kind, 0)
        lines.append(f"- [{kind}/]({kind}/index.md) - {n} paginas - {KIND_DESCRIPCION[kind]}")
    lines += [
        "- [log.md](log.md) - bitacora de acciones aplicadas (solo se agrega)", "",
        "## Como leer una pagina", "",
        "- Front matter: id (`<kind>:<slug>`), estado, version y alias de busqueda.",
        "- Cada hecho es una vineta `- [f_xxxxxxxx] texto`; debajo van sus fuentes "
        "`- fuente: <tipo> <ref> \"cita\"`.",
        "- `(estado: pendiente)` = propuesto por feedback y aun sin revision humana: usalo con cautela.",
        "- `## Historial` guarda hechos reemplazados o rechazados; no los uses para traducir.",
        "- Tipos de fuente: dictionary `lema:<lema>`, grammar `levinsohn:L<a>-L<b>` o "
        "`rosetta:L<a>-L<b>`, corpus `<libro> <cap>:<vers>`, feedback `feedback:<id>`.", "",
        "## Conteos", "",
        f"- paginas: {stats['pages']['total']}",
        f"- hechos activos: {stats['facts']['active']}, pendientes: {stats['facts']['pending']}, "
        f"reemplazados: {stats['facts']['superseded']}, rechazados: {stats['facts']['rejected']}",
    ]
    _write(Path(store.pages_root) / "index.md", "\n".join(lines) + "\n")


def append_log(store, actor: str, op: str, page_id: str | None, fact_ids=(), note: str = "") -> None:
    path = Path(store.pages_root) / "log.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not path.exists()
    from datetime import datetime, timezone  # local: evita ruido en el espacio del modulo

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    campos = [ts, _una_linea(actor) or "anon", op, page_id or "-", ", ".join(fact_ids) or "-"]
    if note:
        campos.append(_una_linea(note)[:200])
    with path.open("a", encoding="utf-8") as fh:
        if nuevo:
            fh.write("# Bitacora de la wiki\n\nUna linea por accion aplicada: "
                     "hora UTC | actor | op | pagina | hechos | nota\n\n")
        fh.write("- " + " | ".join(campos) + "\n")


def render_all(store) -> dict:
    """Reconstruye todo el arbol (menos log.md, que solo se agrega)."""
    raiz = Path(store.pages_root)
    raiz.mkdir(parents=True, exist_ok=True)
    vigentes = set()
    n = 0
    for kind in KIND_TITULO:
        for r in store.page_rows(kind):   # las paginas retiradas (superseded) no se materializan
            page = store.get_page(r["id"], include_inactive=True)
            if page is None:
                continue
            _write(raiz / r["path"], render_page(page))
            vigentes.add(r["path"])
            n += 1
        write_kind_index(store, kind)
    borrados = 0
    for kind in KIND_TITULO:
        carpeta = raiz / kind
        if not carpeta.is_dir():
            continue
        for f in carpeta.glob("*.md"):
            rel = f"{kind}/{f.name}"
            if rel not in vigentes and not f.name.startswith("index"):
                f.unlink()
                borrados += 1
    write_root_index(store)
    if not (raiz / "log.md").exists():
        append_log(store, "render", "render_all", None, note=f"{n} paginas")
    return {"pages": n, "removed": borrados, "root": str(raiz)}
