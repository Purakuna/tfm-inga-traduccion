"""Genera datos/wiki/seed/lemmas.jsonl POR CODIGO (sin LLM) desde la tabla LanceDB `lexico`.

Uso:  PYTHONPATH=. uv run python scripts/build_wiki_lemmas.py [--sample 40]

Reglas (contrato 2026-09-19-inga-wiki-agent-design.md, seccion 2):
- una pagina por lema inga distinto; los homografos comparten pagina con un
  hecho `meaning` por fila del diccionario (la categoria queda en el texto);
- las filas con lema en espanol (seccion Espanol-Inga del diccionario) NO crean
  pagina: se vuelven hechos `meaning` en las paginas inga que mencionan;
- los lemas de varias palabras tienen pagina propia (slug con guiones);
- notas dialectales y variantes ("(AP, achijii - Yun, jachii - Mocoa)",
  "(tambien Chalai)") -> hecho `note` con el parentesis literal; las variantes
  que son claramente otra grafia del mismo lema pasan ademas a `aliases`;
- remisiones "(vease X)" -> hecho `note` con los page_id que existen.
Ningun significado se inventa: cada hecho cita la fila de origen.

Heuristica lema inga / lema espanol: la tabla conserva el orden del diccionario
(seccion Inga-Espanol y luego Espanol-Inga). Se busca el punto de corte que
minimiza el desacuerdo con una senal por letras (el inga del diccionario no usa
e, o, y, q, v, x, z ni c fuera de ch). Si el mejor corte deja mas de 8% de
desacuerdo, el script aborta en vez de adivinar.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANCE_DIR = ROOT / "lance_indexes"
OUT = ROOT / "datos" / "wiki" / "seed" / "lemmas.jsonl"

MAX_FACT = 400
MAX_QUOTE = 300
MAX_SUMMARY = 300
MAX_TITLE = 120
MAX_FACTS_PAGE = 38  # margen bajo el tope de 40 hechos activos

DIALECTOS = {
    "AP": "Alto Putumayo (Valle de Sibundoy)",
    "MP": "Medio Putumayo, Bota Caucana y Caqueta",
    "SA": "San Andres (Alto Putumayo)",
    "Sant": "Santiago (Alto Putumayo)",
    "Yun": "Yunguillo (Bota Caucana)",
    "Gua": "Puerto Guayuyaco",
}
LUGARES = ("Mocoa", "Aponte")
_DIAL = "|".join(list(DIALECTOS) + list(LUGARES))
_RE_ES_LETRAS = re.compile(r"[eoyqvxz]|c(?!h)")
_RE_PAREN = re.compile(r"\(([^()]*)\)")
_RE_VARIANTE_DIAL = re.compile(
    rf"([a-zñ/ ]+?)\s+-\s+((?:{_DIAL})(?:\s*,\s*(?:{_DIAL}))*)(?=\s*(?:,|;|$))", re.I)
_RE_TAMBIEN = re.compile(r"tambi[eé]n\s+([^;()]+?)(?=,?\s*v[eé]anse?\b|;|$)", re.I)
_RE_VEASE = re.compile(r"v[eé]anse?\s+([^;()]+?)(?=;|$)", re.I)
_RE_CAT_ES = re.compile(r"\b(v\.t\.|v\.i\.|v\.r\.|v\.impers\.|p\.p\.)\s")
_RE_INGA_FORM = re.compile(r"^[a-zñ]+( [a-zñ]+){0,3}$")

_TILDE_ENIE = chr(0x303)  # tilde combinante de la enie


def fold(text: str) -> str:
    """Minusculas sin tildes, conserva la enie."""
    out = []
    for ch in unicodedata.normalize("NFD", text.lower()):
        if unicodedata.category(ch) == "Mn" and ch != _TILDE_ENIE:
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def fix_ocr_lema(lema: str) -> str:
    """OCR: 'Il' inicial por 'll' (Ilugsii = llugsii, Ilasa = llasa).

    Los lemas del diccionario van en minuscula (ilichu, ilili, illai son genuinos); una
    I mayuscula seguida de l minuscula al inicio de palabra es la ll mal leida. 39 lemas
    de la tabla y sus remisiones vienen asi, todos en la zona alfabetica de la LL.
    """
    return " ".join(re.sub(r"^Il(?=[a-z\u00f1])", "ll", w) for w in lema.split())


def slugify(lema: str) -> str:
    return re.sub(r"\s+", "-", fold(fix_ocr_lema(lema)).strip())


def clip(text: str, n: int) -> str:
    text = text.strip()
    if len(text) <= n:
        return text
    corte = text[: n - 4]
    if " " in corte[-40:]:
        corte = corte[: corte.rfind(" ")]
    return corte.rstrip(" ,;:") + " ..."


def lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def es_otra_grafia(variante: str, lema: str, dialectal: bool) -> bool:
    """Variante claramente ortografica: mismas palabras y distancia de edicion corta.

    Las variantes con marca de dialecto ("achijii - Yun") admiten algo mas de distancia
    que las de "tambien X", que a veces son sinonimos y no grafias.
    """
    v, l = fold(variante).split(), fold(lema).split()
    if v == l or len(v) != len(l):
        return False
    for a, b in zip(v, l):
        d = lev(a, b)
        n = max(len(a), len(b))
        if dialectal:
            ok = d <= 2 and d / n <= 0.34
        else:
            ok = d <= 1 or (d == 2 and n >= 8)
        if not ok or (d > 0 and n < 4):
            return False
    return True


# ---------------------------------------------------------------- carga y clasificacion
def load_rows() -> list[dict]:
    import lancedb

    db = lancedb.connect(str(LANCE_DIR))
    tabla = db.open_table("lexico")  # solo lectura: nunca se escribe en lance_indexes
    n = tabla.count_rows()
    filas = tabla.search().select(["lema", "cat", "glosa", "text"]).limit(n).to_list()
    out = []
    for f in filas:
        r = {k: (f.get(k) or "").strip() for k in ("lema", "cat", "glosa", "text")}
        r["lema_tabla"] = r["lema"]           # `text` conserva la fila literal para la cita
        r["lema"] = fix_ocr_lema(r["lema"])
        out.append(r)
    return out


DICC_MD = ROOT / "datos" / "ocr" / "inga-kichwa" / "diccionario-inga.md"
_CAT = r"(?:adj|adv|s|v\.t\.|v\.i\.|v\.r\.|v\.impers\.|interj|pron|interrog|conj|p\.p\.|rel|dem|poses|intens|pl\.)"
_CATS = rf"{_CAT}(?:(?:, ?|\. | ){_CAT})*"
_LETRAS = "A-Za-z\u00f1\u00d1\u00e1\u00e9\u00ed\u00f3\u00fa"
_PAL = rf"[{_LETRAS}]+"
_FORMA = rf"{_PAL}(?:/-?{_PAL})*(?: {_PAL}(?:/-?{_PAL})*){{0,3}}"
# "<lema>[, <lema2>] [(<palabra opcional>)] <cat(s)> [<glosa>]"; el lema es perezoso para
# que "masa adv rel ..." no se lea como lema "masa adv" + categoria "rel"
_RE_ENTRADA_MD = re.compile(
    rf"^[\u00bf\u00a1]?({_FORMA}?(?:, {_FORMA}?)?)[?!]?(?: \(({_PAL}(?: {_PAL})?)\))? ({_CATS})(?: (\S.*))?$")
_RE_RESTO_LINEA = re.compile(r"^(?:[^()]*\)|\([^()]*\)|\S+ \([^()]*\)) (?=\S)")


def _gkey(texto: str) -> str:
    """Clave de comparacion de glosas: ASCII, sin espacios ni puntuacion."""
    t = unicodedata.normalize("NFD", texto.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", t)


def _expand_forma(forma: str) -> list[str]:
    """'kakudur/-a' -> [kakudur, kakudura]; 'augtu/autu' -> [augtu, autu]; limita combinaciones."""
    opciones = []
    for w in forma.split():
        alts = w.split("/")
        base = alts[0]
        lista = [base]
        for a in alts[1:]:
            if a.startswith("-"):   # kakudur/-a -> kakudura; subrina/-u -> subrinu
                raiz = base[:-1] if base[-1:] in "aiu" else base
                lista.append(raiz + a[1:])
            else:
                lista.append(a)
        opciones.append(lista)
    out = []
    for combo in itertools.islice(itertools.product(*opciones), 8):
        f = " ".join(combo)
        if f not in out:
            out.append(f)
    return out


def _match_entrada(linea: str):
    m = _RE_ENTRADA_MD.match(linea)
    if not m:
        return None
    formas_txt, opcional, cat, glosa = m.groups()
    formas: list[str] = []
    for trozo in formas_txt.split(", "):
        for f in _expand_forma(trozo.strip()):
            f = fix_ocr_lema(f)
            if f and f not in formas:
                formas.append(f)
    if not formas or parece_es(formas[0]):
        return None
    formas = [f for f in formas if not parece_es(f)]
    # el parentesis tras el lema puede ser palabra opcional (kakug (warmi)) o etimologia
    # (sachuku (sacha uku)); no se distingue con seguridad, asi que no genera alias
    cat = re.sub(r"\.? (?=[a-z])", ", ", cat.replace(", ", " ")).replace(".,", ".,")
    cat = re.sub(r"(adj|adv|s|interj|pron|conj|rel|dem|poses|intens)\.,", r"\1,", cat)
    return formas, cat, (glosa or "").strip()


def _parentesis_abiertos(texto: str) -> bool:
    return texto.count("(") > texto.count(")")


_RE_SUBENTRADA = re.compile(rf"^\S+(?: \S+){{0,3}} {_CAT}\.?(?: |$)")


def parse_md_entries(palabras_inga: set[str] | None = None) -> list[dict]:
    """Entradas de la seccion Inga-Espanol del markdown del diccionario.

    Conservador con el ruido del OCR: solo lineas con la forma
    "<lema> <categoria(s)> <glosa>" (lema con letras del inga; admite "lema, lema2",
    "lema/-a", "lema (opcional)" e interjecciones entre signos). Una linea que empieza con
    el final de la anterior ("rurai) manai v.t. pedir") se acepta si el resto cumple la forma.
    Las lineas siguientes SIN linea en blanco y que empiezan en minuscula, digito o
    parentesis se unen a la glosa (glosas partidas por el OCR). Quedan fuera los ejemplos
    de uso (empiezan con mayuscula), las subentradas y las frases de ejemplo en minuscula
    que empiezan con una palabra inga ("iskai killa dos meses"), salvo que la glosa tenga
    un parentesis aun abierto.
    """
    palabras_inga = palabras_inga or set()
    if not DICC_MD.exists():
        return []
    lineas = DICC_MD.read_text(encoding="utf-8").split("\n")
    try:
        ini = next(i for i, l in enumerate(lineas) if l.strip() == "Diccionario Inga-Espa\u00f1ol")
        fin = next(i for i, l in enumerate(lineas) if l.strip() == "Espa\u00f1ol - Inga")
    except StopIteration:
        return []
    out = []
    i = ini
    while i < fin:
        cruda = lineas[i].strip()
        i += 1
        if not cruda or cruda.startswith(("#", "<!--", "|")):
            continue
        hit = _match_entrada(cruda)
        recortada = False
        if hit is None:
            m = _RE_RESTO_LINEA.match(cruda)
            if m:
                hit = _match_entrada(cruda[m.end():])
                recortada = hit is not None
        if hit is None:
            continue
        formas, cat, glosa = hit
        verbatim = [cruda]
        n_linea = i  # 1-based de la linea de cabecera
        while i < fin:
            sig = lineas[i].strip()
            # parentesis abierto partido por UNA linea en blanco: "(tambien" / "" / "nukanchipa - Sant)"
            if (not sig and _parentesis_abiertos(glosa) and i + 1 < fin):
                prox = lineas[i + 1].strip()
                m2 = _RE_RESTO_LINEA.match(prox)
                if m2 and _match_entrada(prox[m2.end():]) is not None:
                    # "kuruiai) umutu adj corto": cierra este parentesis y sigue otra entrada
                    cola = prox[:m2.end()].strip()
                    glosa = (glosa + " " + cola).strip()
                    verbatim.append(cola)
                    lineas[i + 1] = prox[m2.end():]
                    i += 1
                    break
                if (prox and len(prox) < 80 and prox.count(")") > prox.count("(")
                        and _match_entrada(prox) is None and not prox.startswith(("#", "<!--", "|"))):
                    glosa = (glosa + " " + prox).strip()
                    verbatim.append(prox)
                    i += 2
                    continue
            if (not sig or sig.startswith(("#", "<!--", "|")) or not re.match(r"[a-z\u00f1\u00e1\u00e9\u00ed\u00f3\u00fa(0-9]", sig)
                    or _match_entrada(sig) is not None):
                break
            m2 = _RE_RESTO_LINEA.match(sig)
            if m2 and _parentesis_abiertos(glosa) and _match_entrada(sig[m2.end():]) is not None:
                cola = sig[:m2.end()].strip()
                glosa = (glosa + " " + cola).strip()
                verbatim.append(cola)
                lineas[i] = sig[m2.end():]
                break
            if not _parentesis_abiertos(glosa) and not sig.startswith("("):
                primera = fold(re.split(r"[\s,;/]", sig, 1)[0])
                raiz = fold(formas[0].split()[-1])
                raiz = raiz[:-1] if raiz.endswith("i") and len(raiz) > 3 else raiz
                if (primera in palabras_inga or _RE_SUBENTRADA.match(sig)
                        or re.match(r"^[^()]{1,40} \(v[e\u00e9]anse? ", sig)      # remision "X (vease Y)"
                        or (len(raiz) >= 3 and primera.startswith(raiz))):       # frase con el lema flexionado
                    break
            glosa = (glosa + " " + sig).strip()
            verbatim.append(sig)
            i += 1
        if not glosa:
            continue
        out.append({"lema": formas[0], "formas": formas, "cat": cat, "glosa": glosa,
                    "text": " ".join(verbatim), "md_line": n_linea, "recortada": recortada})
    return out


def merge_md_entries(inga_rows: list[dict], entradas: list[dict]) -> tuple[list[dict], Counter, list[dict]]:
    """Completa las filas de `lexico` con lo que el markdown trae y la tabla perdio.

    - sentido nuevo: el lema existe pero ninguna fila suya tiene esa glosa (sinchi adj, adv);
    - lema nuevo: la tabla no lo trae (mana, chi, iapa);
    - glosa extendida: la fila de la tabla es solo la primera linea de una glosa partida.
    """
    c = Counter()
    por_lema: dict[str, list[dict]] = defaultdict(list)
    for r in inga_rows:
        por_lema[fold(r["lema"])].append(r)
    lemas_tabla = set(por_lema)
    agregados = []
    for e in entradas:
        c["entradas_md"] += 1
        ke = _gkey(e["glosa"])
        filas = [r for f in e["formas"] for r in por_lema.get(fold(f), [])]
        igual = None
        for r in filas:
            kr = _gkey(r["glosa"])
            if kr and ke and (kr[:25] == ke[:25] or kr[:40] in ke or ke[:40] in kr):
                igual = r
                break
        if igual is not None:
            c["ya_en_tabla"] += 1
            kr = _gkey(igual["glosa"])
            if ke.startswith(kr) and len(ke) > len(kr) + 3 and not igual.get("_md"):
                igual["glosa"], igual["text"], igual["_md"] = e["glosa"], e["text"], True
                igual["md_line"] = e["md_line"]
                c["glosas_extendidas"] += 1
            continue
        fila = {"lema": e["lema"], "cat": e["cat"], "glosa": e["glosa"], "text": e["text"],
                "md_line": e["md_line"], "formas": e["formas"], "_md": True,
                "_nuevo_lema": not any(fold(f) in lemas_tabla for f in e["formas"])}
        # si el lema principal no esta en la tabla pero otra forma si, el sentido va a esa pagina
        if fold(fila["lema"]) not in lemas_tabla:
            for f in e["formas"]:
                if fold(f) in lemas_tabla:
                    fila["lema"] = por_lema[fold(f)][0]["lema"]
                    break
        c["lemas_nuevos" if fila["_nuevo_lema"] else "sentidos_nuevos"] += 1
        if e["recortada"]:
            c["de_linea_recortada"] += 1
        por_lema[fold(fila["lema"])].append(fila)
        agregados.append(fila)
    return inga_rows + agregados, c, agregados


def parece_es(lema: str) -> bool:
    return bool(_RE_ES_LETRAS.search(fold(lema)))


def find_boundary(rows: list[dict]) -> tuple[int, dict]:
    """Indice donde empieza la seccion Espanol-Inga y un reporte de desacuerdos."""
    flags = [parece_es(r["lema"]) for r in rows]
    total_no_es = flags.count(False)
    es_antes = 0      # filas con letras de espanol antes del corte (error)
    no_es_antes = 0
    mejor, mejor_err = 0, None
    for i in range(len(rows) + 1):
        err = es_antes + (total_no_es - no_es_antes)
        if mejor_err is None or err < mejor_err:
            mejor, mejor_err = i, err
        if i < len(rows):
            if flags[i]:
                es_antes += 1
            else:
                no_es_antes += 1
    inga_con_letras_es = [rows[i]["text"] for i in range(mejor) if flags[i]]
    rep = {
        "boundary": mejor,
        "n_inga": mejor,
        "n_es": len(rows) - mejor,
        "inga_con_letras_es": inga_con_letras_es,
        "es_sin_letras_es": sum(1 for i in range(mejor, len(rows)) if not flags[i]),
        "desacuerdo": mejor_err / max(1, len(rows)),
    }
    return mejor, rep


# ---------------------------------------------------------------- paginas inga
def notas_de_glosa(lema: str, glosa: str) -> tuple[list[str], list[tuple[str, bool]], list[str]]:
    """(parentesis dialectales literales, variantes (forma, es_dialectal), remisiones)."""
    dialectales, variantes, remisiones = [], [], []
    for par in _RE_PAREN.findall(glosa):
        tiene_dial = False
        for m in _RE_VARIANTE_DIAL.finditer(par):
            forma = m.group(1).strip(" ,")
            forma = re.sub(r"^.*,\s*", "", forma)  # quita "AP, " inicial
            tiene_dial = True
            for f in forma.split("/"):
                f = f.strip()
                if f and _RE_INGA_FORM.match(fold(f)) and fold(f) not in DIALECTOS_FOLD:
                    variantes.append((f, True))
        m = _RE_TAMBIEN.search(par)
        if m:
            tiene_dial = True
            for f in re.split(r"[,/]", m.group(1)):
                f = f.strip()
                if f and _RE_INGA_FORM.match(fold(f)):
                    variantes.append((f, False))
        m = _RE_VEASE.search(par)
        if m:
            for f in re.split(r"[,/]", m.group(1)):
                f = f.strip()
                if f and _RE_INGA_FORM.match(fold(f)):
                    remisiones.append(f)
        if tiene_dial:
            dialectales.append(f"({par})")
    return dialectales, variantes, remisiones


DIALECTOS_FOLD = {fold(d) for d in list(DIALECTOS) + list(LUGARES)}


def resumen(filas: list[dict]) -> str:
    partes = []
    for r in filas:
        g = r["glosa"]
        for _ in range(3):
            g = _RE_PAREN.sub(" ", g)
        g = re.sub(r"\s+", " ", g).strip(" ;,")
        g = re.sub(r"\s+([;,])", r"\1", g)
        if g:
            partes.append(f"{r['cat']}: {g}" if r["cat"] else g)
    return clip(" | ".join(partes), MAX_SUMMARY)


def partir_hecho(r: dict) -> list[str]:
    """Texto del hecho de significado; si pasa de 400 se parte por acepciones numeradas."""
    base = f"{r['lema']} ({r['cat']}): " if r["cat"] else f"{r['lema']}: "
    full = base + r["glosa"]
    if len(full) <= MAX_FACT:
        return [full]
    trozos = [t.strip() for t in re.split(r"(?=\(\d+\)\s)", r["glosa"]) if t.strip()]
    out = []
    for t in trozos:
        out.append(clip(base + t, MAX_FACT))
    return out or [clip(full, MAX_FACT)]


def src_dict(r: dict) -> dict:
    return {"type": "dictionary", "ref": f"lema:{r['lema']}", "quote": clip(r["text"], MAX_QUOTE)}


def build_pages(inga_rows: list[dict]) -> dict[str, dict]:
    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in inga_rows:
        if r["lema"] and r["glosa"]:
            grupos[slugify(r["lema"])].append(r)
    pages: dict[str, dict] = {}
    for slug, filas in grupos.items():
        formas = [f["lema"] for f in filas]
        titulo = next((f for f in formas if f == f.lower()), formas[0])
        page = {
            "id": f"lemma:{slug}", "kind": "lemma", "slug": slug, "title": clip(titulo, MAX_TITLE),
            "summary": resumen(filas), "aliases": [], "facts": [],
            "_variantes": [], "_remisiones": [], "_rows": filas,
        }
        for f in formas:
            if f not in page["aliases"]:
                page["aliases"].append(f)
        vistos = set()
        for r in filas:
            for texto in partir_hecho(r):
                if texto in vistos:
                    continue
                vistos.add(texto)
                page["facts"].append({"section": "meaning", "text": texto, "sources": [src_dict(r)]})
        pages[slug] = page
    # formas alternativas de la cabecera del markdown ("auka, augka", "kakug (warmi)")
    for page in pages.values():
        for r in page["_rows"]:
            for f in r.get("formas") or []:
                if slugify(f) not in pages and f not in page["aliases"] and len(f) <= 80:
                    page["aliases"].append(f)
    return pages


def add_notes(pages: dict[str, dict]) -> Counter:
    c = Counter()
    for slug, page in pages.items():
        vistos = set()
        for r in page["_rows"]:
            dialectales, variantes, remisiones = notas_de_glosa(r["lema"], r["glosa"])
            if dialectales:
                usados = [d for d in DIALECTOS if re.search(rf"\b{d}\b", " ".join(dialectales))]
                abrev = "; ".join(f"{d} = {DIALECTOS[d]}" for d in usados)
                texto = f"Nota dialectal del diccionario para {r['lema']} ({r['cat']}): " + " ".join(dialectales)
                if abrev:
                    texto += f". Abreviaturas: {abrev}."
                texto = clip(texto, MAX_FACT)
                if texto not in vistos:
                    vistos.add(texto)
                    page["facts"].append({"section": "note", "text": texto, "sources": [src_dict(r)]})
                    c["note_dialectal"] += 1
            for v, dialectal in variantes:
                if slugify(v) in pages:
                    c["variante_con_pagina_propia"] += 1
                    continue
                if es_otra_grafia(v, r["lema"], dialectal):
                    if v not in page["aliases"]:
                        page["aliases"].append(v)
                        c["alias_variante"] += 1
                else:
                    c["variante_no_alias"] += 1
            existentes = []
            for x in remisiones + [v for v, _ in variantes]:
                s = slugify(x)
                if s in pages and s != slug and s not in existentes:
                    existentes.append(s)
            if existentes:
                texto = clip(
                    f"Remisiones del diccionario desde {r['lema']} ({r['cat']}): "
                    + ", ".join(f"{s.replace('-', ' ')} [lemma:{s}]" for s in existentes), MAX_FACT)
                if texto not in vistos:
                    vistos.add(texto)
                    page["facts"].append({"section": "note", "text": texto, "sources": [src_dict(r)]})
                    c["note_remision"] += 1
    return c


# ---------------------------------------------------------------- filas espanol-inga
def limpiar_lema_es(lema: str, lemas_inga_1: set[str]) -> tuple[str, bool]:
    """Quita una palabra inga pegada al inicio por un salto de linea del OCR.

    Ej.: 'kusma turbarse (v.i.): irkiai' viene de 'tunica ... s / kusma turbarse v.i. irkiai'.
    Solo se aplica si la primera palabra es un lema inga y el resto tiene letras de espanol.
    """
    palabras = lema.split()
    if len(palabras) >= 2 and fold(palabras[0]) in lemas_inga_1 and not parece_es(palabras[0]):
        resto = " ".join(palabras[1:])
        if parece_es(resto):
            return resto, True
    return lema, False


def objetivos_inga(glosa: str) -> list[str]:
    """Formas inga candidatas de una glosa Espanol-Inga (con variantes a/b y (opcionales))."""
    g = _RE_CAT_ES.sub(" , ", glosa + " ")
    crudos = [p.strip() for p in re.split(r"[,;]", g) if p.strip()]
    out = []
    for p in crudos:
        versiones = {_RE_PAREN.sub(" ", p), p.replace("(", " ").replace(")", " ")}
        for v in versiones:
            v = re.sub(r"\s*/\s*", "/", v)
            palabras = v.split()
            if not palabras or len(palabras) > 5:
                continue
            alternativas = [w.split("/") for w in palabras]
            if any(len(a) > 4 for a in alternativas):
                continue
            for combo in itertools.islice(itertools.product(*alternativas), 16):
                forma = " ".join(w for w in combo if w)
                if forma and forma not in out:
                    out.append(forma)
    return out


def attach_es_rows(pages: dict[str, dict], es_rows: list[dict]) -> tuple[Counter, list[dict]]:
    c = Counter()
    sin_destino = []
    lemas_1 = {s for s in pages if "-" not in s}
    for r in es_rows:
        if not r["lema"] or not r["glosa"]:
            c["es_vacia"] += 1
            continue
        lema_es, limpiado = limpiar_lema_es(r["lema"], lemas_1)
        if limpiado:
            c["es_lema_limpiado"] += 1
        destinos = []
        for forma in objetivos_inga(r["glosa"]):
            s = slugify(forma)
            if s not in pages and s.startswith("il"):
                s2 = "ll" + s[2:]  # OCR: 'Iluspichii' por 'lluspichii' (I mayuscula por l)
                if s2 in pages:
                    s = s2
                    c["ocr_Il_ll"] += 1
            if s in pages and s not in destinos:
                destinos.append(s)
        if not destinos:
            c["es_sin_destino"] += 1
            sin_destino.append(r)
            continue
        c["es_con_destino"] += 1
        texto = clip(f"{lema_es} ({r['cat']}): {r['glosa']} [entrada espanol-inga del diccionario]",
                     MAX_FACT)
        for s in destinos:
            page = pages[s]
            if any(f["text"] == texto for f in page["facts"]):
                continue
            page["facts"].append({
                "section": "meaning", "text": texto,
                "sources": [{"type": "dictionary", "ref": f"lema:{r['lema']}",
                             "quote": clip(r["text"], MAX_QUOTE)}],
            })
            c["hechos_es"] += 1
    return c, sin_destino


def finalize(pages: dict[str, dict]) -> tuple[list[dict], Counter]:
    c = Counter()
    out = []
    for slug in sorted(pages):
        p = pages[slug]
        facts = p["facts"]
        if len(facts) > MAX_FACTS_PAGE:
            # se conservan primero significados, luego notas; se informa el recorte
            orden = sorted(range(len(facts)), key=lambda i: (facts[i]["section"] != "meaning", i))
            facts = [facts[i] for i in sorted(orden[:MAX_FACTS_PAGE])]
            c["paginas_recortadas"] += 1
        aliases = [a for a in p["aliases"] if len(a) <= 80]
        out.append({"id": p["id"], "kind": "lemma", "slug": slug, "title": p["title"],
                    "summary": p["summary"], "aliases": aliases, "facts": facts})
        c["pages"] += 1
        c["facts"] += len(facts)
        c["aliases"] += len(aliases)
        if len(p["_rows"]) > 1:
            c["paginas_homografas"] += 1
        if "-" in slug:
            c["paginas_multipalabra"] += 1
    return out, c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sample", type=int, default=0,
                    help="imprime N filas al azar a cada lado del corte para revision manual")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    rows = load_rows()
    boundary, rep = find_boundary(rows)
    print(f"filas lexico: {len(rows)} | corte Inga-Espanol / Espanol-Inga en fila {boundary} "
          f"({rep['n_inga']} inga, {rep['n_es']} espanol)")
    print(f"desacuerdo de la senal por letras con el corte: {rep['desacuerdo']:.1%} "
          f"(inga con letras de espanol: {len(rep['inga_con_letras_es'])}; "
          f"espanol sin letras distintivas: {rep['es_sin_letras_es']})")
    for t in rep["inga_con_letras_es"]:
        print(f"  revisar (seccion inga, letras de espanol): {t[:100]}")
    if rep["desacuerdo"] > 0.08:
        print("ERROR: el orden de la tabla no separa las dos secciones; no se genera la semilla.",
              file=sys.stderr)
        return 2

    inga_rows, es_rows = rows[:boundary], rows[boundary:]
    if args.sample:
        rnd = random.Random(42)
        print(f"\n--- muestra seccion INGA ({args.sample}) ---")
        for r in rnd.sample(inga_rows, args.sample):
            print("  ", r["text"][:110])
        print(f"--- muestra seccion ESPANOL ({args.sample}) ---")
        for r in rnd.sample(es_rows, args.sample):
            print("  ", r["text"][:110])

    palabras_inga = {w for r in inga_rows for w in fold(r["lema"]).split()}
    entradas = parse_md_entries(palabras_inga)
    todas, c_md, agregados = merge_md_entries(inga_rows, entradas)
    print("markdown del diccionario: " + ", ".join(f"{k}={v}" for k, v in sorted(c_md.items())))
    n_tabla = sum(1 for r in inga_rows if r["glosa"])
    print(f"  validacion del patron: {c_md['ya_en_tabla']} de {c_md['entradas_md']} entradas leidas coinciden "
          f"con una fila de lexico ({c_md['ya_en_tabla'] / max(1, c_md['entradas_md']):.1%}); "
          f"lexico tiene {n_tabla} filas inga")
    if args.sample:
        rnd = random.Random(7)
        nuevos_sentidos = [r for r in agregados if not r["_nuevo_lema"]]
        print(f"--- muestra de sentidos recuperados ({min(15, len(nuevos_sentidos))}) ---")
        for r in rnd.sample(nuevos_sentidos, min(15, len(nuevos_sentidos))):
            print(f"   L{r['md_line']}: {r['lema']} ({r['cat']}): {r['glosa'][:110]}")
    pages = build_pages(todas)
    c_notes = add_notes(pages)
    c_es, sin_destino = attach_es_rows(pages, es_rows)
    out, c_fin = finalize(pages)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for p in out:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\nescrito {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")
    for nombre, cnt in (("paginas", c_fin), ("notas", c_notes), ("espanol-inga", c_es)):
        print(f"  {nombre}: " + ", ".join(f"{k}={v}" for k, v in sorted(cnt.items())))
    if sin_destino:
        print(f"  filas espanol-inga sin pagina inga de destino: {len(sin_destino)} (ejemplos)")
        for r in sin_destino[:12]:
            print(f"    {r['text'][:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
