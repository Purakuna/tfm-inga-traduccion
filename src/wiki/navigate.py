"""Normalizacion ortografica y resolucion de tokens contra la wiki.

Las reglas de `normalize` salen de los datos, no de intuicion. Evidencia medida
sobre el lado inga de datos/splits/train.jsonl (94,401 tokens, 13,502 tipos) y
los 3,202 lemas inga del diccionario (nunca val/test):

R1  y -> i          0 tokens con "y" en el corpus y 0 lemas; el corpus escribe
                    iukai, iuiai, kaugsai, "i" como conjuncion. El apendice
                    gramatical (grafia antigua) escribe -y, cay, pay.
R2  qu+e/i -> ki, q -> k
                    "q" solo en 6 tokens (erratas tiakuq-); el corpus escribe killa.
R3  c -> k salvo "ch" y salvo c+e/i
                    "c" fuera de "ch" solo aparece en nombres propios que el corpus
                    conserva (Cristo, Jesucristo, Marcos, Lucas, Pentecostes): se
                    protegen. El apendice escribe -cuna, -rca, nuca; el corpus -kuna,
                    -rka, nuka.
R4  hu+vocal -> w   0 tokens nativos con "hu"+vocal fuera de ch/sh (kichui no cuenta);
                    el apendice escribe huasi, -hua; el corpus wasi, -wa.
R5  gua -> wa al inicio de palabra o tras vocal
                    0 tokens con "gua" en el corpus; el diccionario adapta "aguantar"
                    como awantai. Tras consonante NO se toca (bungua, minguanti son lemas).
R6  aw+consonante -> aug+consonante
                    1 token con aw+C (errata) frente a 1,449 con aug+C (kaugsai,
                    chaugpi, waugki); 0 lemas con aw+C.
R7  ñuka... -> nuka...
                    nuka 711 y nukanchi 273 tokens frente a 0 de ñuka; el diccionario
                    lista nuka, nukanchi, nukapa. Es regla lexica: la ñ se conserva en
                    el resto (ñi 376, ña 182, ñawi, ñugpa).
No se normaliza: sh (85 lemas la usan), ts, j inicial, e/o, tildes finales (iuka con
tilde = 3a persona) ni la sonorizacion tras nasal; esas diferencias dialectales se
prueban solo como variantes de ultimo recurso en `resolve` y quedan marcadas.
"""
from __future__ import annotations

import re
import unicodedata

from src.wiki.store import WikiStore
from src.wiki.validation import fold

# ---------------------------------------------------------------- normalize
_RE_PALABRA = re.compile(r"[^\W\d_]+", re.UNICODE)
_RE_PROTEGIDO = re.compile(r"^(jesu)?crist|^marcos|^lucas|^pentecost")
_VOCAL = "aeiouáéíóú"


def _normalize_word(w: str) -> str:
    w = unicodedata.normalize("NFC", w.lower())
    protegido = bool(_RE_PROTEGIDO.match(fold(w)))
    # R7 lexica
    if w.startswith("ñuka"):
        w = "n" + w[1:]
    # R2
    w = re.sub(r"qu[e\u00e9]", "ki", w)
    w = re.sub(r"qu(?=[i\u00ed])", "k", w)
    w = w.replace("q", "k")
    # R3
    if not protegido:
        w = re.sub(r"c(?![heiéí])", "k", w)
    # R4: hu+vocal, pero no la h de ch/sh
    w = re.sub(rf"(?<![cs])hu(?=[{_VOCAL}])", "w", w)
    # R5
    w = re.sub(rf"(^|(?<=[{_VOCAL}]))gua", "wa", w)
    # R1
    w = w.replace("y", "i").replace("ý", "í")
    # R6
    w = re.sub(rf"aw(?=[^{_VOCAL}w\W])", "aug", w)
    return w


def normalize(text: str, direccion: str = "inga2es") -> str:
    """Lleva grafias quechua/kichwa comunes a la ortografia del corpus inga.

    Devuelve el texto en minusculas con la puntuacion intacta. Con
    direccion="es2inga" el texto es espanol y solo se pasa a minusculas.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    if direccion == "es2inga":
        return text.lower()
    return _RE_PALABRA.sub(lambda m: _normalize_word(m.group(0)), text)


# ---------------------------------------------------------------- sufijos de respaldo
# Inventario minimo verificado en datos/ocr/inga-kichwa/rosetta-morfosintactico.md
# (grafia del apendice -> grafia del corpus, linea). Solo se usa cuando la wiki no
# tiene paginas `suffix` o cuando sus alias no alcanzan a segmentar un token.
FALLBACK_SUFFIXES: dict[str, str] = {
    "kuna": "rosetta:L62 (-cuna, plural)",
    "pura": "rosetta:L70 (-pura, entre)",
    "ta": "rosetta:L82 (-ta, acusativo; L126 'por')",
    "pa": "rosetta:L91 (-pa, genitivo 'de, para')",
    "manda": "rosetta:L97 (-manda, ablativo)",
    "pagmanda": "rosetta:L97 (-pagmanda, desde donde una persona)",
    "wa": "rosetta:L104 (-hua, instrumento/acompanante 'con')",
    "sina": "rosetta:L114 (-sina, comparativo 'como')",
    "pi": "rosetta:L123 (-pi, locativo 'en')",
    "pagpi": "rosetta:L123 (-pagpi, en donde una persona)",
    "ma": "rosetta:L124 (-ma, 'a, hasta')",
    "pagma": "rosetta:L124 (-pagma, a donde una persona)",
    "kama": "rosetta:L125 (-cama, 'hasta')",
    "pagkama": "rosetta:L125 (-pagcama)",
    "ka": "rosetta:L820 (clitico -c/-ca, contraste o progresion)",
    "mi": "rosetta:L792 (-mi, certidumbre en afirmativas)",
    "chu": "rosetta:L793 (-chu, en oraciones negativas)",
    "si": "rosetta:L794 (-si)",
    "char": "rosetta:L795 (-char, duda)",
    "ngapa": "rosetta:L834 (-ngapa, proposito; L584 pusangapa)",
    "nkama": "rosetta:L834 (-ncama, limite)",
    "gta": "rosetta:L834 (-gta, limite)",
    "spa": "rosetta:L854 (-spa, subordinada)",
    "gpi": "rosetta:L861 (-gpi, subordinada)",
    "rka": "rosetta:L404 (-rca, preterito)",
    "ku": "rosetta:L386 (-cu, progresivo singular)",
    "naku": "rosetta:L386 (-nacu, progresivo plural)",
    "ri": "rosetta:L314 (-ri, reflexivo/reciproco/incoativo)",
    "chi": "rosetta:L314 (-chi, causativo)",
    "ni": "rosetta:L363 (-ni, 1a singular)",
    "ngi": "rosetta:L364 (-ngui, 2a singular; el corpus escribe kangi)",
    "nchi": "rosetta:L367 (-nchi, 1a plural)",
    "n": "rosetta:L369 (-n ante -cuna, 3a plural)",
    "sa": "rosetta:L454 (-sa, futuro 1a singular)",
    "nga": "rosetta:L456 (-nga, futuro 3a; L38 nominalizador)",
    "sunchi": "rosetta:L458 (-sunchi, futuro 1a plural)",
    "ntra": "rosetta:L468 (-ntra, condicional)",
    "ska": "rosetta:L44 (-sca, participio pasado)",
    "g": "rosetta:L34 (-g, agente)",
}

_cache: dict[str, tuple[int, dict]] = {}


def _index(store: WikiStore) -> dict:
    """Indice de lemas y sufijos de la wiki, en cache por version de datos."""
    clave = str(store.db_path)
    version = store.data_version()
    hit = _cache.get(clave)
    if hit and hit[0] == version:
        return hit[1]
    formas: dict[str, list[str]] = {}      # forma completa o raiz verbal -> paginas
    completas: set[str] = set()            # solo formas completas (lemas y alias)
    frases: dict[str, list[str]] = {}      # lemas de varias palabras
    for alias, page_id, es_verbo in store.lemma_index():
        alias = alias.replace("-", " ").strip()
        if not alias:
            continue
        if " " in alias:
            frases.setdefault(alias, [])
            if page_id not in frases[alias]:
                frases[alias].append(page_id)
            continue
        completas.add(alias)
        claves = [alias]
        # formas de cita verbales terminan en -i / -ai / -ii: iukai -> iuka, nii -> ni
        # (los infinitivos tambien se listan como sustantivos: manchai 'miedo', kaugsai 'vida')
        if alias.endswith("i") and len(alias) >= 3 and (
                es_verbo or (len(alias) >= 5 and alias[-2] in "aiu")):
            claves.append(alias[:-1])
        for k in claves:
            formas.setdefault(k, [])
            if page_id not in formas[k]:
                formas[k].append(page_id)
    sufijos: dict[str, list[str]] = {}
    for alias, page_id in store.suffix_keys():
        alias = normalize(alias).strip("- ")
        alias = fold(alias)
        if alias and " " not in alias:
            sufijos.setdefault(alias, [])
            if page_id not in sufijos[alias]:
                sufijos[alias].append(page_id)
    idx = {"formas": formas, "completas": completas, "frases": frases, "sufijos": sufijos,
           "max_frase": max((len(f.split()) for f in frases), default=1)}
    _cache[clave] = (version, idx)
    return idx


MAX_SUFFIX_PAGES = 4
_MAX_SEGMENTACIONES = 24


# sufijos derivativos verbales: van entre la raiz y la flexion (rosetta L314-L339, L386, L699-L713)
_DERIVATIVOS = frozenset({"chi", "ri", "ku", "naku", "mu", "pu", "pua", "raia", "naia", "ia", "wa"})
_CASO = frozenset({"pa", "ta", "pi", "ma", "manda", "wa", "pagma", "pagpi", "pagmanda", "sina"})
_CLITICOS_FINALES = frozenset({"k", "m", "s"})   # formas reducidas de -ka, -mi, -pas: solo al final


def _segmentations(resto: str, inventario, memo: dict | None = None, primero: bool = True) -> list[list[str]]:
    """Todas las particiones de `resto` en sufijos del inventario (cadena raiz+deriv+flexion).

    Las piezas de una letra sobre-generan, asi que se restringen: -k, -m, -s solo como
    ultima pieza de la palabra; las demas (-g, -n, -i) solo pegadas a una raiz conocida o
    tras derivativos verbales (suia-ku-g). `primero` = hasta aqui solo hubo derivativos.
    """
    if memo is None:
        memo = {}
    if resto == "":
        return [[]]
    clave = (resto, primero)
    if clave in memo:
        return memo[clave]
    out: list[list[str]] = []
    for n in range(min(len(resto), 10), 0, -1):
        pieza = resto[:n]
        if pieza not in inventario:
            continue
        if n == 1:
            if pieza in _CLITICOS_FINALES:
                if len(resto) != 1:
                    continue
            elif not primero:
                continue
        for cola in _segmentations(resto[n:], inventario, memo, primero and pieza in _DERIVATIVOS):
            if pieza == "n" and cola and cola[0] in _CASO:
                continue   # -n es verbal (3a persona): no le sigue un caso nominal (Juan-pa no es jua-n-pa)
            out.append([pieza] + cola)
            if len(out) >= _MAX_SEGMENTACIONES:
                break
        if len(out) >= _MAX_SEGMENTACIONES:
            break
    memo[clave] = out
    return out


def _segment(resto: str, inventario, memo: dict | None = None, primero: bool = True) -> list[str] | None:
    """Mejor particion: menos piezas de una letra y, a igualdad, menos piezas."""
    segs = _segmentations(resto, inventario, memo, primero)
    if not segs:
        return None
    return min(segs, key=lambda sg: (sum(len(x) == 1 for x in sg), len(sg)))


def _pages_for(piezas: list[str], sufijos: dict) -> list[str]:
    paginas: list[str] = []
    for p in piezas:
        for pid in sufijos.get(p, []):   # un alias compartido (nga, ta) devuelve todas sus paginas
            if pid not in paginas:
                paginas.append(pid)
    return paginas


def _best_split(tok: str, idx: dict, inv: set) -> dict | None:
    """Mejor (raiz, sufijos) que explica TODO el token con este inventario."""
    formas, sufijos = idx["formas"], idx["sufijos"]
    mejor = None
    for n in range(len(tok) - 1, 1, -1):          # raiz >= 2 letras
        pref = tok[:n]
        if pref not in formas:
            continue
        memo: dict = {}
        segs = _segmentations(tok[n:], inv, memo)
        if not segs:
            continue
        for sg in segs:
            # menos piezas de una letra > raiz mas larga > menos piezas
            nota = (sum(len(x) == 1 for x in sg), -n, len(sg))
            if mejor is None or nota < mejor["nota"]:
                mejor = {"nota": nota, "raiz": pref, "piezas": sg, "segs": segs}
    if mejor is None:
        return None
    piezas = mejor["piezas"]
    paginas = _pages_for(piezas, sufijos)
    alternativa = None
    # una pieza compuesta (kunata) puede ser tambien dos sufijos (kuna + ta): se ofrecen ambas
    # lecturas, salvo que la particion sea el mismo morfema escrito en dos (nga+pa de -ngapa)
    for sg in mejor["segs"]:
        if len(sg) == len(piezas) + 1 and all(len(x) >= 2 for x in sg):
            pag_alt = _pages_for(sg, sufijos)
            if pag_alt and not set(pag_alt) & set(paginas):
                alternativa = sg
                paginas = pag_alt + paginas     # lectura atomica primero
                break
    res = {"lemmas": list(formas[mejor["raiz"]]), "piezas": alternativa or piezas,
           "paginas": paginas[:MAX_SUFFIX_PAGES]}
    if alternativa:
        res["piezas_alt"] = piezas
    return res


def _match_inga(tok: str, idx: dict) -> tuple[list[str], list[str], list[str], list[str] | None] | None:
    """(paginas de lema, sufijos pelados, paginas de sufijo, lectura alternativa) o None."""
    formas, sufijos = idx["formas"], idx["sufijos"]
    if tok in idx["completas"]:
        return list(formas[tok]), [], [], None
    inventarios = []
    if sufijos:
        inventarios.append(set(sufijos))
        inventarios.append(set(sufijos) | set(FALLBACK_SUFFIXES))
    else:
        inventarios.append(set(FALLBACK_SUFFIXES))
    split = None
    for inv in inventarios:
        split = _best_split(tok, idx, inv)
        if split is not None:
            break
    if tok in formas:
        # coincide solo con una raiz verbal (kani = raiz de kanii): tambien puede ser
        # raiz + sufijo (ka-ni 'soy'); se devuelven ambas lecturas, la segmentada primero
        # si no usa piezas de una letra
        exactas = list(formas[tok])
        if split is None or any(len(x) == 1 for x in split["piezas"]):
            return exactas, [], [], None
        lemas = split["lemmas"] + [x for x in exactas if x not in split["lemmas"]]
        return lemas, split["piezas"], split["paginas"], split.get("piezas_alt")
    if split is None:
        return None
    return split["lemmas"], split["piezas"], split["paginas"], split.get("piezas_alt")


def _variants(tok: str) -> list[str]:
    """Variantes dialectales de ultimo recurso (kichwa unificado -> inga)."""
    cand = []

    def add(x):
        if x and x != tok and x not in cand:
            cand.append(x)

    if tok.startswith("ñ"):
        add("n" + tok[1:])
    elif tok.startswith("n"):
        add("ñ" + tok[1:])
    add(tok.replace("sh", "s"))
    if tok.endswith("k") or tok.endswith("j"):
        add(tok[:-1])          # ngapak / ngapaj -> ngapa, nukanchik -> nukanchi
        add(tok[:-1] + "g")    # shuk -> sug tras sh->s
    sonoro = tok.replace("nt", "nd").replace("mp", "mb").replace("nk", "ng")
    add(sonoro)                # -manta -> -manda, -nkapa -> -ngapa
    add(sonoro.replace("sh", "s"))
    if sonoro.endswith("k"):
        add(sonoro[:-1])
    if tok.startswith("j") and len(tok) > 3:
        add(tok[1:])           # el diccionario lista jutku/utku, jichu/ichu
    return cand


def _resolve_inga(sentence: str, store: WikiStore) -> list[dict]:
    idx = _index(store)
    items = []
    for m in _RE_PALABRA.finditer(sentence):
        crudo = m.group(0)
        norm = _normalize_word(crudo)
        items.append({"token": crudo, "normalized": norm, "lemma_pages": [],
                      "suffix_pages": [], "resolved": False, "_key": fold(norm)})
    # palabra por palabra
    for it in items:
        tok = it["_key"]
        hit = _match_inga(tok, idx)
        if hit is None:
            for v in _variants(tok):
                hit = _match_inga(v, idx)
                if hit is not None:
                    it["variant"] = v
                    break
        if hit is not None:
            it["lemma_pages"], piezas, it["suffix_pages"], alt = hit
            if piezas:
                it["suffixes"] = piezas
            if alt:
                it["suffixes_alt"] = alt
            it["resolved"] = True
    # lemas de varias palabras (Taita Dius, achka runakuna): se anteponen a cada token
    if idx["frases"]:
        claves = [it["_key"] for it in items]
        for n in range(min(idx["max_frase"], 4), 1, -1):
            for i in range(0, len(items) - n + 1):
                cabeza = " ".join(claves[i:i + n - 1])
                ultimo = claves[i + n - 1]
                paginas = None
                for corte in range(len(ultimo), 1, -1):
                    frase = (cabeza + " " + ultimo[:corte]).strip()
                    if frase in idx["frases"] and (
                            corte == len(ultimo)
                            or _segment(ultimo[corte:], set(idx["sufijos"]) | set(FALLBACK_SUFFIXES))
                            is not None):
                        paginas = idx["frases"][frase]
                        break
                if paginas:
                    for it in items[i:i + n]:
                        for pid in reversed(paginas):
                            if pid not in it["lemma_pages"]:
                                it["lemma_pages"].insert(0, pid)
                        it["resolved"] = True
    for it in items:
        it.pop("_key", None)
    return items


# ---------------------------------------------------------------- es2inga
STOPWORDS_ES = frozenset("""
a al algo ante con contra de del desde donde durante e el ella ellas ellos en entre era eran
es esa esas ese eso esos esta estas este esto estos fue fueron ha han has hasta hay he la las le
les lo los mas me mi mis muy ni o os para pero por porque que se sea ser si sin sobre son su sus
tambien te ti tu tus u un una unas uno unos y ya yo el tu nos vosotros usted ustedes como cuando
cual cuales quien quienes cuyo cuya esta estan estaba estaban este fui sido siendo
hacia tras segun mientras aunque sino pues asi tan tanto cada todo toda todos todas otro otra otros otras
mio mia tuyo suya suyo nuestro nuestra vuestro les aquel aquella aquellos aquellas alli aqui ahi
""".split())

_TERMINACIONES_VERBO = (
    "andose", "iendose", "ando", "iendo", "yendo", "aron", "ieron", "aban", "ian", "aras", "eras",
    "iras", "aran", "eran", "iran", "amos", "emos", "imos", "aste", "iste", "aba", "ado", "ido",
    "ada", "ida", "ados", "idos", "adas", "idas", "are", "ere", "ire", "ara", "era", "ira", "ais",
    "eis", "ia", "io", "an", "en", "as", "es", "ad", "ed", "id", "a", "e", "o",
)


def spanish_candidates(tok: str) -> list[str]:
    """Lematizacion simple del espanol: plurales, genero, cliticos y finales verbales."""
    t = fold(tok)
    cand = [t]

    def add(x):
        if len(x) >= 2 and x not in cand:
            cand.append(x)

    if t.endswith("ces"):
        add(t[:-3] + "z")
    if t.endswith("es"):
        add(t[:-2])
    if t.endswith("s"):
        add(t[:-1])
    if t.endswith("as"):
        add(t[:-2] + "o")
    if t.endswith("a"):
        add(t[:-1] + "o")
    base = t
    for clitico in ("selo", "sela", "melo", "nos", "les", "los", "las", "se", "me", "te", "le", "lo", "la"):
        if base.endswith(clitico) and len(base) - len(clitico) >= 4 and base[:-len(clitico)][-1] in "rao":
            base = base[:-len(clitico)]
            add(base)
            break
    if base.endswith(("ar", "er", "ir")):
        add(base + "se")
    for fin in _TERMINACIONES_VERBO:
        if base.endswith(fin) and len(base) - len(fin) >= 2:
            raiz = base[:-len(fin)]
            raices = [raiz]
            # diptongacion: quier- -> quer-, pued- -> pod-
            if "ie" in raiz:
                raices.append(raiz[::-1].replace("ei", "e", 1)[::-1])
            if "ue" in raiz:
                raices.append(raiz[::-1].replace("eu", "o", 1)[::-1])
            for rz in raices:
                for inf in ("ar", "er", "ir"):
                    add(rz + inf)
                    add(rz + inf + "se")
            break
    return cand


def _resolve_es(sentence: str, store: WikiStore) -> list[dict]:
    items = []
    memo: dict[str, tuple[list[str], str]] = {}
    for m in _RE_PALABRA.finditer(sentence):
        crudo = m.group(0)
        norm = crudo.lower()
        it = {"token": crudo, "normalized": norm, "lemma_pages": [], "suffix_pages": [],
              "resolved": False}
        clave = fold(norm)
        if clave in STOPWORDS_ES or len(clave) < 2:
            it["stopword"] = True
            items.append(it)
            continue
        if clave not in memo:
            # se prueban todas las formas candidatas y gana la de mejor rango de glosa
            # ("casa" como glosa completa de wasi antes que "casas" dentro de una frase)
            mejor: tuple[int, list[str], str] | None = None
            for cand in spanish_candidates(clave):
                hits = store.find_by_gloss(cand, limit=8)
                if not hits:
                    continue
                tope = max(h.get("rank", 0) for h in hits)
                if mejor is None or tope > mejor[0]:
                    fuertes = [h for h in hits if h.get("rank", 0) >= 2]
                    elegidos = fuertes[:5] if fuertes else hits[:3]
                    mejor = (tope, [h["id"] for h in elegidos], cand)
                if tope >= 3:
                    break
            memo[clave] = (mejor[1], mejor[2]) if mejor else ([], clave)
        paginas, forma = memo[clave]
        if forma != clave:
            it["variant"] = forma
        it["lemma_pages"] = list(paginas)
        it["resolved"] = bool(it["lemma_pages"])
        items.append(it)
    return items


def resolve(sentence: str, direccion: str, store: WikiStore) -> list[dict]:
    """Un item por token: {"token","normalized","lemma_pages","suffix_pages","resolved"}.

    Claves extra opcionales: "suffixes" (piezas peladas), "suffixes_alt" (otra lectura
    de las mismas letras, p. ej. -kunata frente a -kuna + -ta), "variant" (forma
    alternativa que resolvio), "stopword" (es2inga).
    """
    if not sentence or not sentence.strip():
        return []
    if direccion == "es2inga":
        return _resolve_es(sentence, store)
    if direccion != "inga2es":
        raise ValueError(f"direccion desconocida: {direccion!r}")
    return _resolve_inga(sentence, store)
