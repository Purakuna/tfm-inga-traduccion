"""Pistas compactas de la wiki para el prompt de traduccion.

En vez de pegar las paginas completas (que empujaban al modelo a traducir
palabra por palabra con el primer sentido del diccionario), se le entrega una
linea por palabra con sus lecturas posibles, como PISTAS y no como mandato:

- DiPMT (Ghazvininejad, Gonen y Zettlemoyer, 2023, arXiv:2302.07856): el
  diccionario rinde cuando se da como lista de traducciones posibles para un
  subconjunto de palabras, no como texto que obliga.
- LingoLLM (Zhang et al., 2024, arXiv:2402.18025) y Court y Elsner (WMT 2024,
  arXiv:2406.15625, quechua surenho -> espanol): la entrada segmentada en raiz +
  sufijos con glosas ayuda, y la calidad de lo recuperado es critica: un
  candidato equivocado hace danho.

Lo unico que entra con prioridad sobre el criterio del modelo son los hechos
cuya fuente es un hablante (feedback), porque es lo que ni los libros ni el
modelo saben.
"""
from __future__ import annotations

import re
from typing import Any

from src.wiki import navigate

MAX_SENTIDOS = 3
MAX_GLOSA = 110
_RE_ES_PRIMERO = re.compile(r"\[entrada espanol-inga")


def _corta(texto: str, n: int = MAX_GLOSA) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= n else texto[: n - 3].rstrip() + "..."


def _es_de_hablante(fact: dict) -> bool:
    return any(s.get("type") == "feedback" for s in fact.get("sources") or [])


def _sentidos(page: dict, direccion: str) -> list[str]:
    """Sentidos del lema: los del diccionario inga-espanol primero."""
    propios, inversos = [], []
    for f in page.get("facts") or []:
        if f.get("section") != "meaning" or f.get("status") != "active" or _es_de_hablante(f):
            continue
        (inversos if _RE_ES_PRIMERO.search(f["text"]) else propios).append(f["text"])
    elegidos = propios or inversos
    if direccion == "es2inga":
        elegidos = propios + inversos
    out = []
    for t in elegidos[:MAX_SENTIDOS]:
        t = _RE_ES_PRIMERO.split(t)[0].strip()
        # "tukui (v.i.): llegar a ser" -> "(v.i.) llegar a ser": el lema ya va al inicio de la linea
        t = re.sub(r"^[^()]{1,40}\s*(\([^)]*\))\s*:\s*", r"\1 ", t)
        out.append(_corta(t))
    return out


def _sufijos_sueltos(tok: dict, idx: dict, posicion: int) -> list[str] | None:
    """Piezas si la palabra entera se lee como sufijos escritos aparte (p. ej. 'kunata')."""
    norm = tok.get("normalized") or ""
    if posicion == 0 or len(norm) < 4:
        return None
    piezas = navigate._segment(norm, set(idx["sufijos"]))
    if piezas and all(len(p) >= 3 for p in piezas):
        return piezas
    return None


def build(store: Any, tokens: list[dict], direccion: str) -> dict:
    """Devuelve {"lineas": [...], "hablantes": [...], "paginas": [...]} para el prompt."""
    # El inventario de sufijos solo hace falta hacia el espanol, y solo existe en el store real.
    idx = {"sufijos": {}}
    if direccion == "inga2es" and hasattr(store, "suffix_keys"):
        idx = navigate._index(store)
    lineas: list[str] = []
    hablantes: list[str] = []
    vistas: set[str] = set()
    cache: dict[str, dict | None] = {}

    def page(pid: str) -> dict | None:
        if pid not in cache:
            cache[pid] = store.get_page(pid)
        return cache[pid]

    def recoge_hablantes(p: dict) -> None:
        if p["id"] in vistas:
            return
        vistas.add(p["id"])
        for f in p.get("facts") or []:
            if _es_de_hablante(f) and f.get("status") in ("active", "pending"):
                marca = "" if f["status"] == "active" else " (pendiente de revision: usalo con cautela)"
                hablantes.append(f"- [{p['id']}] {_corta(f['text'], 300)}{marca}")

    for i, tok in enumerate(tokens):
        forma = str(tok.get("token", ""))
        norm = tok.get("normalized") or ""
        cab = forma if not norm or norm == forma.lower() else f"{forma} -> {norm}"
        lecturas: list[str] = []
        for pid in (tok.get("lemma_pages") or [])[:3]:
            p = page(pid)
            if not p:
                continue
            recoge_hablantes(p)
            sentidos = _sentidos(p, direccion)
            if sentidos:
                lecturas.append(f"{p['title']} {' / '.join(sentidos)} [{pid}]")
        sufijos = []
        for pid in (tok.get("suffix_pages") or [])[:4]:
            p = page(pid)
            if p:
                recoge_hablantes(p)
                sufijos.append(f"{_corta(p['title'], 70)} [{pid}]")
        sueltos = _sufijos_sueltos(tok, idx, i) if direccion == "inga2es" else None

        if tok.get("stopword"):
            continue
        linea = f"- {cab}: "
        if lecturas:
            linea += " | ".join(lecturas)
        else:
            linea += ("sin pagina en la wiki (puede ser prestamo del espanol adaptado, con e->i y o->u, "
                      "un nombre propio o una variante): decide por contexto")
        if sufijos:
            linea += " ; sufijos: " + ", ".join(sufijos)
        if sueltos:
            linea += (" ; OJO: tambien puede ser sufijo(s) de la palabra anterior escritos aparte: "
                      + " + ".join("-" + s for s in sueltos))
        lineas.append(linea)

    # Paginas de construcciones (convention / case) cuyo alias aparece en la oracion.
    for tok in tokens:
        norm = tok.get("normalized") or ""
        if len(norm) < 3:
            continue
        for kind in ("convention", "case"):
            for res in store.find_pages(norm, kind=kind, limit=3):
                p = page(res["id"])
                if not p or norm not in [a.lower().strip("- ") for a in p.get("aliases") or []]:
                    continue
                if p["id"] in vistas:
                    continue
                vistas.add(p["id"])
                for f in p.get("facts") or []:
                    if f.get("status") in ("active", "pending"):
                        marca = "" if f["status"] == "active" else " (pendiente de revision: usalo con cautela)"
                        hablantes.append(f"- [{p['id']}] {_corta(f['text'], 300)}{marca}")

    return {"lineas": lineas, "hablantes": hablantes, "paginas": sorted(vistas)}
