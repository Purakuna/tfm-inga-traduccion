"""Construye las semillas de gramatica y sufijos de la wiki inga (workstream B).

Fuentes (unicas): la gramatica pedagogica de Levinsohn y el apendice
morfosintactico (rosetta), ambos OCR en datos/ocr/inga-kichwa/.

Flujo:
  1. extraccion: Gemini lee ventanas con numeros de linea y devuelve paginas con
     hechos; cada hecho trae rango de lineas y una cita textual.
  2. verificacion EN CODIGO: la cita debe aparecer (tras plegar espacios,
     mayusculas y acentos; con tolerancia difusa para OCR) dentro del rango
     citado. Lo que no pasa se descarta y se cuenta.
  3. fusion por slug entre ventanas y deduplicacion de hechos casi identicos.
  4. juez: una llamada por pagina que ve cada hecho junto a las lineas citadas
     y marca fiel / parcial / no_sustentado; solo sobreviven los fieles. El
     juez tambien redacta titulo y resumen a partir de los hechos fieles.
  5. conversion ortografica determinista de las formas inga marcadas con
     llaves {..} desde la ortografia de las fuentes (c/qu, hu, y, j) a la del
     corpus (k, w, i, g), y calculo de alias para los sufijos.
  6. escritura de suffixes.jsonl y grammar.jsonl + validacion.

Reanudable: las respuestas crudas del modelo se guardan en
datos/wiki/seed/.cache/. Uso:

    PYTHONPATH=. uv run python scripts/build_wiki_grammar.py [--workers 6]
        [--solo-extraer] [--sin-juez]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import random
import re
import sys
import threading
import time
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google.genai import errors as genai_errors
from google.genai import types

from src.models.gemini_rag import DEFAULT_MODEL, _get_client

RAIZ = Path(__file__).resolve().parents[1]
DIR_OCR = RAIZ / "datos" / "ocr" / "inga-kichwa"
DIR_SEED = RAIZ / "datos" / "wiki" / "seed"
DIR_CACHE = DIR_SEED / ".cache"
RUTA_TRAIN = RAIZ / "datos" / "splits" / "train.jsonl"

DOCS = {
    "levinsohn": DIR_OCR / "gramatica-pedagogica-levinsohn.md",
    "rosetta": DIR_OCR / "rosetta-morfosintactico.md",
}
# Rangos utiles de la gramatica (se omiten vocabularios, indices y bibliografia).
RANGOS_LEVINSOHN = [(1, 2667), (3225, 6312)]
TAM_VENTANA = 650
SOLAPE = 80

VERSION_PROMPT = "v4"
CAP_TITULO, CAP_RESUMEN, CAP_TEXTO, CAP_CITA, CAP_HECHOS = 120, 300, 400, 300, 40
SECCIONES = ["meaning", "morphology", "usage", "example", "note"]
UMBRAL_DIFUSO = 0.85
HOLGURA_LINEAS = 2
MAX_DESVIO_REANCLAJE = 40
MIN_CITA = 8

# Inventario preferido de slugs de sufijos (ortografia del corpus) con la forma
# en que lo escriben las fuentes. Sale de los cuadros de sufijos de las propias
# fuentes (rosetta completo; Levinsohn L1295-L1340, L4723-L4760, L6237-L6312).
INVENTARIO_SUFIJOS = {
    "kuna": "-cuna", "pura": "-pura", "ta": "-ta", "pa": "-pa/-pag/-paj",
    "manda": "-manda", "wa": "-hua", "sina": "-sina", "pi": "-pi", "ma": "-ma",
    "kama": "-cama", "nig": "-nig/-nij", "lla": "-lla", "llata": "-llata(ta)",
    "ndi": "-ndi", "iug": "-yug", "pas": "-pas/-s", "jim": "-jim/-ajim",
    "tum": "-tum", "itu": "-ito/-ita/-ico/-ica/-sito/-sita",
    "g": "-g/-j", "dur": "-dor/-dora", "diru": "-dero", "nga": "-nga",
    "ska": "-sca", "du": "-do", "i": "-y", "ri": "-ri", "chi": "-chi",
    "ia": "-ya", "raia": "-raya", "naia": "-naya", "mu": "-mu", "pu": "-pu",
    "pua": "-pua", "ku": "-cu", "naku": "-nacu", "gri": "-gri", "gsamu": "-gsamu",
    "ni": "-ni", "ngi": "-ngui", "n": "-n", "nchi": "-nchi", "ngichi": "-nguichi",
    "iki": "-yqui/-qui", "chita": "-chita", "kunata": "-cunata",
    "rka": "-rca/-rsha/-sha", "sa": "-sa", "sunchi": "-sunchi/-sun",
    "nkangi": "-ncangui", "saki": "-saqui/-scaqui", "ntra": "-ntra",
    "spa": "-spa", "gpi": "-gpi/-jpi", "ura": "-hora", "nkama": "-ncama",
    "gta": "-gta/-jta", "ngapa": "-ngapa/-nga", "mi": "-mi", "chu": "-chu",
    "si": "-si", "char": "-char", "ka": "-ca/-c", "tak": "-ta/-tac (interrogativo)",
    "ra": "-ra", "wanta": "-huanta",
}

# Alias adicionales por pagina: formas de superficie compuestas que aparecen en
# los paradigmas de las fuentes y que un token del corpus puede llevar al final.
ALIAS_EXTRA = {
    "kuna": ["-nkuna"],
    "pi": ["-pagpi"],
    "ma": ["-pagma"],
    "kama": ["-pagkama"],
    "manda": ["-pagmanda"],
    "ngi": ["-ngi"],
    "ngichi": ["-ngichi"],
    "iki": ["-iki", "-ki"],
    "nga": ["-ngakuna"],
    "mi": ["-m"],
    "nkangi": ["-nkangichi"],
    "chita": ["-ikichita"],
}

# Slugs propuestos por el modelo que son variantes de una pagina existente.
FUSION_SLUGS = {("suffix", "kar"): "ka", ("suffix", "ngakuna"): "nga",
                ("suffix", "nkangichi"): "nkangi", ("suffix", "s"): "pas"}
# La pronunciacion no es una convencion de escritura: va como gramatica.
TIPO_FORZADO = {"pronunciacion-alfabeto": "grammar"}

# Zonas donde el OCR desalineo una tabla y el texto resultante dice algo que el
# original no dice. En rosetta L792-L795 la glosa del reportativo ('repitiendo
# las palabras de otra persona') quedo pegada a -chu y la linea de -si vacia
# (comparese con Levinsohn L2028). Se descartan los hechos que citen esa zona
# y cuyo texto coincida con el patron.
EXCLUSIONES_OCR = [("rosetta", 793, 794, re.compile(r"repit|repet|palabras de otr", re.I))]

# Hechos escritos a mano a partir de lineas leidas por el autor del script; la
# cita se verifica en codigo igual que las del modelo.
HECHOS_FIJOS = {
    ("grammar", "variacion-dialectal"): [{
        "section": "note",
        "text": ("Levinsohn distingue cuatro dialectos principales del inga en Colombia, con un grado muy alto "
                 "de mutua comprensión, y los numera: 1 Santiago (Santiago y Colón, Valle de Sibundoy), "
                 "2 San Andrés, 3 Ingano (al este de Mocoa), 4 Aponte (Nariño). Las diferencias principales "
                 "están en la pronunciación de ciertas letras y sufijos."),
        "sources": [
            ("levinsohn", 185, 185, "Cuatro dialectos principales del inga se sabe que existen en Colombia, pero hay entre ellos un grado muy alto de intercomunicación y mutua comprensión. Las principales diferencias se encuentran en la pronunciación de ciertas letras y sufijos."),
            ("levinsohn", 189, 192, "1. Santiago - ubicado en los pueblos de Santiago y Colón, Valle de Sibundoy, Putumayo. 2. San Andrés - ubicado sobre el pueblo de San Andrés, a 3 kilómetros de Santiago. 3. Ingano - hablado al este de Mocoa, en superficies selváticas, Putumayo"),
        ],
    }],
}

TEMAS_GRAMATICA = {
    "orden-oracion": "Orden de las palabras en la oracion",
    "frase-nominal": "Frase nominal: adjetivos, intensificadores y sufijos de caso",
    "frase-posicional": "Frases de lugar y sustantivos posicionales",
    "pronombres-personales": "Pronombres personales",
    "posesivos": "Posesion y posesivos",
    "demostrativos": "Demostrativos",
    "interrogativos": "Palabras y frases interrogativas",
    "preguntas-si-no": "Preguntas de si o no",
    "negacion": "Negacion",
    "verbo-ser-estar": "El verbo ser/estar",
    "existencia-y-tener": "Existencia y tener",
    "presente-general": "Presente general (paradigma)",
    "presente-progresivo": "Presente progresivo o continuativo",
    "preterito": "Preterito (pasado)",
    "copreterito": "Copreterito (pasado progresivo)",
    "futuro": "Futuro",
    "potencial-futuro-inmediato": "Tiempos potenciales y futuro inmediato",
    "condicional": "Condicional",
    "hipotetico": "Aspecto hipotetico",
    "tiempos-perfectos": "Tiempos perfectos y participio pasado",
    "imperativo": "Imperativo de segunda persona",
    "imperativo-indirecto-exhortativo": "Imperativo indirecto y exhortativo",
    "objeto-en-el-verbo": "Marcacion del complemento de persona en el verbo",
    "infinitivos-nominalizacion": "Infinitivos y nominalizacion",
    "verbos-auxiliares": "Verbos auxiliares y perifrasis",
    "verbos-derivados": "Derivacion verbal (causativo, reflexivo, cambio de estado)",
    "verbos-impersonales": "Verbos impersonales",
    "verbos-movimiento": "Verbos y sufijos de movimiento y beneficio",
    "subordinacion-temporal": "Clausulas subordinadas de tiempo y cambio de sujeto",
    "subordinacion-proposito": "Clausulas de proposito",
    "subordinacion-causa": "Clausulas de causa",
    "subordinacion-limite": "Clausulas de limite (hasta, mientras)",
    "condicion-y-concesion": "Oraciones condicionales y concesivas",
    "clausulas-relativas": "Clausulas relativas y formas con agentivo",
    "evidencialidad": "Cliticos de certidumbre, reportativo y duda",
    "foco-y-topico": "Foco, enfasis y topico",
    "comparacion": "Comparacion",
    "numeros": "Numeros y cantidades",
    "cuantificadores": "Cuantificadores e intensificadores",
    "expresiones-de-tiempo": "Expresiones de tiempo",
    "discurso-reportado": "Discurso reportado y citas",
    "conectores-discurso": "Conectores del discurso",
    "coordinacion": "Coordinacion de frases y oraciones",
    "prestamos-espanol": "Prestamos del espanol y su adaptacion",
    "diminutivos-apreciativos": "Diminutivos, apreciativos y despectivos",
    "pronunciacion-alfabeto": "Pronunciacion y alfabeto de las fuentes",
    "acento": "Acento y su desplazamiento",
    "variacion-dialectal": "Variacion dialectal",
    "tiempos-en-narracion": "Uso de los tiempos en la narracion",
    "orden-sufijos": "Orden relativo de los sufijos",
    "saludos-formulas": "Saludos, despedidas y formulas",
    "inga-hablado-y-escrito": "Inga hablado y escrito",
}

_lock_log = threading.Lock()


def log(msg: str) -> None:
    with _lock_log:
        print(msg, flush=True)


# --------------------------------------------------------------------------
# Normalizacion de texto y verificacion de citas
# --------------------------------------------------------------------------

_RE_RUIDO = re.compile(r"[|*_#>$\\`]")
_RE_ESPACIOS = re.compile(r"\s+")
_TRAD_COMILLAS = str.maketrans({
    0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"',
    0x2013: "-", 0x2014: "-", 0x00AB: '"', 0x00BB: '"',
})


def plegar(s: str) -> str:
    """Pliega mayusculas, acentos, marcas de tabla markdown y espacios."""
    s = s.translate(_TRAD_COMILLAS)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = _RE_RUIDO.sub(" ", s.lower())
    s = s.replace("<br/>", " ").replace("<br>", " ")
    return _RE_ESPACIOS.sub(" ", s).strip()


_RE_SEGMENTOS = re.compile(r"\s*(?:\[\.\.\.\]|\.\.\.|\u2026|\n)\s*")


def cita_limpia(cita: str) -> str:
    """Une los segmentos de una cita con ' ... ' y colapsa espacios."""
    partes = [_RE_ESPACIOS.sub(" ", x).strip() for x in _RE_SEGMENTOS.split(cita)]
    partes = [x for x in partes if x]
    return " ... ".join(partes)


class Documento:
    """Documento fuente con lineas numeradas desde 1 y texto plegado indexado."""

    def __init__(self, nombre: str, ruta: Path):
        self.nombre = nombre
        self.lineas = ruta.read_text(encoding="utf-8").split("\n")
        self.n = len(self.lineas)
        self._plegadas = [plegar(l) for l in self.lineas]
        # Texto global plegado con el offset de inicio de cada linea.
        self._inicio = []
        partes, pos = [], 0
        for p in self._plegadas:
            self._inicio.append(pos)
            if p:
                partes.append(p)
                pos += len(p) + 1
        self._global = " ".join(partes)

    def _offset(self, linea: int) -> int:
        linea = max(1, min(self.n, linea))
        return self._inicio[linea - 1]

    def _linea_de(self, offset: int) -> int:
        # ultima linea cuyo inicio <= offset y que tenga contenido
        lo, hi = 0, self.n - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._inicio[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        while lo > 0 and not self._plegadas[lo] :
            lo -= 1
        return lo + 1

    def texto_rango(self, ini: int, fin: int) -> str:
        ini, fin = max(1, ini), min(self.n, fin)
        return " ".join(p for p in self._plegadas[ini - 1:fin] if p)

    def numerado(self, ini: int, fin: int) -> str:
        ini, fin = max(1, ini), min(self.n, fin)
        out = []
        for i in range(ini, fin + 1):
            l = self.lineas[i - 1].rstrip()
            if l.strip():
                out.append(f"L{i}: {l}")
        return "\n".join(out)

    def verificar(self, cita: str, ini: int, fin: int) -> tuple[str, int, int, float]:
        """Devuelve (modo, ini, fin, ratio); modo en exacta|reanclada|difusa|falla."""
        q = plegar(cita)
        if len(q) < MIN_CITA or ini < 1 or fin < ini or ini > self.n:
            return ("falla", ini, fin, 0.0)
        fin = min(fin, self.n)
        a = self._offset(ini - HOLGURA_LINEAS)
        b_linea = min(self.n, fin + HOLGURA_LINEAS)
        b = self._inicio[b_linea - 1] + len(self._plegadas[b_linea - 1])
        zona = self._global[a:b]
        k = zona.find(q)
        if k >= 0:
            return ("exacta", self._linea_de(a + k), self._linea_de(a + k + len(q) - 1), 1.0)
        # Cita exacta pero con lineas mal citadas: reanclar si esta cerca.
        mejor, pos = None, self._global.find(q)
        while pos >= 0:
            l0 = self._linea_de(pos)
            desvio = 0 if ini <= l0 <= fin else min(abs(l0 - ini), abs(l0 - fin))
            if mejor is None or desvio < mejor[0]:
                mejor = (desvio, pos)
            pos = self._global.find(q, pos + 1)
        if mejor is not None and mejor[0] <= MAX_DESVIO_REANCLAJE:
            p = mejor[1]
            return ("reanclada", self._linea_de(p), self._linea_de(p + len(q) - 1), 1.0)
        # Cita en segmentos (el modelo unio trozos con '...' o salto de linea):
        # cada segmento debe aparecer textual dentro de la zona citada.
        segmentos = [plegar(x) for x in _RE_SEGMENTOS.split(cita)]
        segmentos = [x for x in segmentos if x]
        if len(segmentos) > 1 and all(len(x) >= 6 and x in zona for x in segmentos):
            return ("segmentada", max(1, ini), fin, 1.0)
        # Coincidencia difusa tolerante a OCR dentro de la zona citada.
        if len(q) >= 20 and zona:
            ratio = _mejor_ratio(zona, q)
            if ratio >= UMBRAL_DIFUSO:
                return ("difusa", max(1, ini), fin, ratio)
        return ("falla", ini, fin, 0.0)


def _mejor_ratio(zona: str, q: str) -> float:
    n = len(q)
    if len(zona) <= n:
        return difflib.SequenceMatcher(None, zona, q, autojunk=False).ratio()
    paso = max(1, n // 25)
    mejor = 0.0
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(q)
    for i in range(0, len(zona) - n + 1 + paso, paso):
        sm.set_seq1(zona[i:i + n])
        if sm.real_quick_ratio() < UMBRAL_DIFUSO or sm.quick_ratio() < UMBRAL_DIFUSO:
            continue
        r = sm.ratio()
        if r > mejor:
            mejor = r
            if mejor > 0.98:
                break
    return mejor


# --------------------------------------------------------------------------
# Conversion ortografica fuentes -> corpus (solo dentro de llaves {..})
# --------------------------------------------------------------------------

_ACENTOS = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")


def _caso(orig: str, nuevo: str) -> str:
    return nuevo.capitalize() if orig[:1].isupper() else nuevo


def a_corpus(s: str) -> str:
    """Convierte una forma inga de la ortografia de las fuentes a la del corpus.

    Reglas regulares observadas entre las fuentes (1978) y el corpus/diccionario:
    qu->k, c->k (c+e/i->s), hu+vocal->w, gu+e/i->g, y->i, j final de silaba->g,
    'hora'->'ura', sin tildes. Los sufijos prestados -dor/-dero/-do pasan a
    -dur/-diru/-du.
    """
    s = s.translate(_ACENTOS)
    fijos = {"-dor": "-dur", "-dora": "-dura", "-dero": "-diru", "-do": "-du",
             "-ito": "-itu", "-ico": "-iku", "-sito": "-situ", "-ica": "-ika"}
    if s.lower() in fijos:
        return fijos[s.lower()]
    s = re.sub(r"hora", lambda m: _caso(m.group(), "ura"), s, flags=re.I)
    s = re.sub(r"qu", lambda m: _caso(m.group(), "k"), s, flags=re.I)
    s = re.sub(r"hu(?=[aeiou])", lambda m: _caso(m.group(), "w"), s, flags=re.I)
    s = re.sub(r"gu(?=[ei])", lambda m: _caso(m.group(), "g"), s, flags=re.I)
    s = re.sub(r"c(?=[ei])", lambda m: _caso(m.group(), "s"), s, flags=re.I)
    s = re.sub(r"c(?!h)", lambda m: _caso(m.group(), "k"), s, flags=re.I)
    s = re.sub(r"y", lambda m: _caso(m.group(), "i"), s, flags=re.I)
    s = re.sub(r"j(?![aeiou])", lambda m: _caso(m.group(), "g"), s, flags=re.I)
    return s


_RE_LLAVES = re.compile(r"\{([^{}]*)\}")


def convertir_llaves(texto: str, registro: list[str] | None = None) -> str:
    # puntuacion tipografica -> ASCII (las citas no pasan por aqui y quedan textuales)
    texto = texto.translate(_TRAD_COMILLAS).replace(chr(0x2026), "...")
    def rep(m):
        forma = m.group(1).strip()
        if registro is not None:
            registro.append(forma)
        return a_corpus(forma)
    texto = _RE_LLAVES.sub(rep, texto)
    return texto.replace("{", "").replace("}", "")


def formas_de(cadena: str) -> list[str]:
    """Expande '-ta(ta)/-tac' en ['-ta', '-tata', '-tac'] (minusculas, sin tilde)."""
    out = []
    for parte in re.split(r"[/,;]| o ", cadena):
        parte = parte.strip().lower().translate(_ACENTOS)
        parte = re.sub(r"\s*\(.*?[ a-z]{4,}.*?\)\s*$", "", parte)  # glosas entre parentesis
        if not parte:
            continue
        variantes = [parte]
        if "(" in parte:
            variantes = [re.sub(r"\(([a-zñ]+)\)", "", parte), re.sub(r"\(([a-zñ]+)\)", r"\1", parte)]
        for v in variantes:
            v = v.strip().lstrip("-").strip()
            if re.fullmatch(r"[a-zñ]{1,12}", v):
                out.append(v)
    return out


# --------------------------------------------------------------------------
# Llamadas a Gemini con cache y reintentos
# --------------------------------------------------------------------------

USO = Counter()
_lock_uso = threading.Lock()


def _clave(*partes: str) -> str:
    return hashlib.sha1("\x1f".join(partes).encode("utf-8")).hexdigest()[:20]


def llamar_json(etiqueta: str, sistema: str, prompt: str, esquema: dict) -> dict:
    """Llama al modelo con esquema JSON; cachea la respuesta cruda en disco."""
    DIR_CACHE.mkdir(parents=True, exist_ok=True)
    ruta = DIR_CACHE / f"{etiqueta}-{_clave(VERSION_PROMPT, DEFAULT_MODEL, sistema, prompt)}.json"
    if ruta.exists():
        guardado = json.loads(ruta.read_text(encoding="utf-8"))
        _sumar_uso(guardado.get("uso", {}), cache=True)
        return guardado["datos"]
    config = types.GenerateContentConfig(
        system_instruction=sistema,
        response_mime_type="application/json",
        response_schema=esquema,
        max_output_tokens=65536,
        temperature=0.2,
        http_options=types.HttpOptions(timeout=900_000),
    )
    cliente = _get_client()
    ultimo = None
    for intento in range(6):
        t0 = time.time()
        try:
            resp = cliente.models.generate_content(model=DEFAULT_MODEL, contents=prompt, config=config)
            datos = json.loads(resp.text or "")
        except genai_errors.APIError as e:
            ultimo = e
            if e.code not in (408, 429, 500, 502, 503, 504):
                raise
            espera = min(120, 2 ** intento * 5) + random.random() * 3
            log(f"  [{etiqueta}] API {e.code}; reintento en {espera:.0f}s")
            time.sleep(espera)
            continue
        except (json.JSONDecodeError, TypeError, OSError) as e:
            ultimo = e
            log(f"  [{etiqueta}] respuesta invalida ({type(e).__name__}); reintento")
            time.sleep(3 + intento * 2)
            continue
        um = resp.usage_metadata
        uso = {
            "entrada": um.prompt_token_count or 0,
            "salida": um.candidates_token_count or 0,
            "razonamiento": um.thoughts_token_count or 0,
            "segundos": round(time.time() - t0, 1),
        }
        ruta.write_text(json.dumps({"etiqueta": etiqueta, "uso": uso, "datos": datos},
                                   ensure_ascii=False), encoding="utf-8")
        _sumar_uso(uso, cache=False)
        return datos
    raise RuntimeError(f"[{etiqueta}] sin respuesta valida tras reintentos: {ultimo}")


def _sumar_uso(uso: dict, cache: bool) -> None:
    with _lock_uso:
        for k in ("entrada", "salida", "razonamiento", "segundos"):
            USO[k] += uso.get(k, 0)
        USO["llamadas_cache" if cache else "llamadas_nuevas"] += 1


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

SISTEMA_BASE = """Eres un linguista que construye una wiki CITADA del idioma inga (quechua de Colombia) para un agente de traduccion inga<->espanol de una tesis de maestria. Recibes un fragmento de un documento fuente con lineas numeradas ('L<n>: texto'). El fragmento es OCR de una publicacion de 1978 y usa la ortografia de esa epoca (c/qu, hu, y, j).

REGLAS ESTRICTAS
1. Extrae UNICAMENTE lo que dice el fragmento. Prohibido usar tu conocimiento de quechua, kichwa u otras fuentes. Un hecho gramatical equivocado es peor que un hecho ausente: ante la duda, omite.
2. Cada hecho lleva: 'ref_start' y 'ref_end' (numeros de linea del fragmento que sustentan el hecho, rango corto, idealmente <= 12 lineas) y 'quote': una cita TEXTUAL copiada de esas lineas, contigua, sin el prefijo 'L<n>:', de 15 a 250 caracteres, sin corregir ortografia ni erratas del OCR y sin puntos suspensivos. Si la cita abarca varias lineas consecutivas, unelas con un espacio. La cita debe contener la evidencia del hecho (la regla o el ejemplo con su glosa).
3. 'text': el hecho en espanol claro (con tildes), <= 350 caracteres, AUTOCONTENIDO: nombra siempre el sufijo, la palabra o la construccion de que habla (no escribas 'Sufijo de objeto' sino 'El sufijo {-ta} marca el complemento de objeto'). Cada forma inga (palabra, frase, raiz o sufijo) va entre llaves EXACTAMENTE como la escribe la fuente, por ejemplo {runacuna}, {-cuna}, {Huasimanda samucuni.}; las glosas en espanol van entre comillas simples y fuera de las llaves. Excepcion: en hechos sobre letras, alfabeto o pronunciacion NO uses llaves (usa comillas simples).
4. 'section': 'morphology' (funcion del sufijo, a que se une, orden respecto de otros sufijos, alomorfos, paradigmas), 'usage' (como se traduce o se usa, patrones de traduccion al espanol, restricciones, diferencias dialectales), 'example' (una palabra o frase de ejemplo con su glosa copiada de la fuente), 'meaning' (significado), 'note' (advertencias, excepciones).
5. En los hechos de seccion 'example' el 'text' DEBE contener el ejemplo mismo: la palabra o frase inga entre llaves seguida de su glosa en espanol entre comillas simples, y si hace falta una breve aclaracion; p. ej.: {Huasimanda samucuni.} 'Vengo de la casa.' (ablativo {-manda}). Nunca escribas solo 'Ejemplo de uso de ...'. Los ejemplos solo valen si la fuente da la traduccion o glosa en espanol dentro del rango citado, y la cita debe incluir el ejemplo y su glosa. No uses oraciones de ejercicios sin traduccion. Si un ejemplo parece tener una errata evidente de OCR, omitelo.
6. No repitas el mismo hecho con otras palabras. No inventes etiquetas de dialecto: usa las de la fuente (Santiago/Sant, San Andres/S.A, Yunguillo, Aponte, Mocoa, dialecto 1/2...) solo cuando la fuente las mencione.
7. Ignora listas de vocabulario, indices, encabezados de pagina y numeros de pagina, salvo que contengan informacion gramatical.
Responde solo con el JSON del esquema."""

INSTR_SUFIJOS = """TAREA: paginas de SUFIJOS y cliticos (kind 'suffix'). Una pagina por sufijo o enclitico que el fragmento explique: marcadores de caso, plural, posesion, terminaciones verbales de persona/tiempo/aspecto, subordinadores, cliticos de evidencia/foco/topico/negacion/interrogacion, sufijos derivativos (causativo, reflexivo...), nominalizadores, imperativos y sufijos prestados del espanol.

Para cada pagina:
- 'slug': usa uno de los slugs preferidos de la lista cuando corresponda (la lista da 'slug = forma en las fuentes'). Si el sufijo no esta en la lista, propone un slug nuevo: el sufijo sin guion, en minusculas, con estas sustituciones: qu->k, c->k, hu->w, gu(e/i)->g, y->i, j final->g.
- Sufijos homografos (misma forma, funciones distintas, p. ej. {-hua} 'con' y {-hua} 'a mi'; {-chu} negativo/interrogativo e imperativo indirecto; {-chi} causativo y plural) comparten UNA pagina; escribe un hecho por cada funcion.
- 'source_forms': TODAS las formas de superficie y alomorfos con que el fragmento escribe el sufijo (p. ej. ["-rca", "-rsha", "-sha"]), con guion inicial, tal como aparecen en la fuente.
- Hechos que interesan: funcion ('morphology'); a que clase de palabra se une y orden relativo con otros sufijos ('morphology'); como se traduce al espanol ('usage'); diferencias entre dialectos ('usage' o 'note'); de 1 a 3 ejemplos con glosa copiados de la fuente ('example').
- Las combinaciones fijas (p. ej. {-pagma}, {-llata}, {-nguichi}) van en la pagina del slug preferido que corresponda o, si no hay, en la del ultimo sufijo de la combinacion.

SLUGS PREFERIDOS:
{inventario}"""

INSTR_GRAMATICA = """TAREA: paginas de TEMAS DE GRAMATICA (kind 'grammar') utiles para traducir: orden de palabras, frase nominal, pronombres y posesivos, paradigmas de conjugacion por tiempo, negacion, preguntas, subordinacion y cambio de sujeto, evidencialidad, comparacion, numeros, discurso reportado, adaptacion de prestamos del espanol, convenciones de escritura y pronunciacion que describe la fuente, y diferencias dialectales (Santiago, San Andres, Yunguillo, Aponte, Mocoa...).

Para cada pagina:
- 'slug': usa uno de los slugs preferidos de la lista cuando el contenido corresponda (la lista da 'slug = tema'). Solo si nada encaja, propone un slug nuevo en espanol, minusculas, con guiones, sin tildes.
- 'kind': 'grammar' casi siempre. Usa 'convention' SOLO para convenciones explicitas de escritura que la fuente declare (como se escribe, puntuacion, alfabeto adoptado).
- 'source_forms': deja la lista vacia.
- Escribe hechos sobre la construccion completa (paradigmas con todas las personas, patrones de oracion, reglas de orden), no sobre sufijos aislados; para un paradigma, un hecho por paradigma o por grupo de personas con las formas y sus glosas, y la cita tomada de las filas de la tabla.
- Incluye ejemplos de oraciones completas con su traduccion ('example').

SLUGS PREFERIDOS:
{inventario}"""

ESQUEMA_EXTRACCION = {
    "type": "OBJECT",
    "properties": {
        "pages": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "slug": {"type": "STRING"},
                    "kind": {"type": "STRING", "enum": ["suffix", "grammar", "convention"]},
                    "title": {"type": "STRING"},
                    "source_forms": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "facts": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "section": {"type": "STRING", "enum": SECCIONES},
                                "text": {"type": "STRING"},
                                "ref_start": {"type": "INTEGER"},
                                "ref_end": {"type": "INTEGER"},
                                "quote": {"type": "STRING"},
                            },
                            "required": ["section", "text", "ref_start", "ref_end", "quote"],
                        },
                    },
                },
                "required": ["slug", "kind", "title", "source_forms", "facts"],
            },
        }
    },
    "required": ["pages"],
}

SISTEMA_JUEZ = """Eres un revisor estricto de una wiki citada del idioma inga. Recibes una pagina con hechos numerados; cada hecho trae su cita y las LINEAS REALES de la fuente que cita. Las formas inga van entre llaves {..} en la ortografia de la fuente; conserva esa convencion y esa ortografia en lo que escribas.

Para cada hecho decide 'verdict':
- 'fiel': todo lo que afirma el hecho (funcion, glosa, formas, dialecto, orden) esta dicho en las lineas mostradas. La redaccion puede resumir, pero no anadir.
- 'parcial': parte del hecho no aparece en las lineas mostradas, o generaliza mas de lo que dice la fuente.
- 'no_sustentado': las lineas no dicen eso, el hecho contradice la fuente, atribuye un ejemplo o glosa equivocada, o el hecho no pertenece al tema de esta pagina.
No uses tu conocimiento de quechua para completar: juzga solo contra las lineas. Se severo: ante la duda, 'parcial'.
'duplicate_of': si el hecho repite la informacion de otro hecho fiel de numero MENOR, pon ese numero; si no, -1.
'priority': 1 = esencial para traducir (funcion, regla, paradigma, patron de traduccion), 2 = util (ejemplos claros, dialectos), 3 = marginal.

Luego redacta, usando SOLO los hechos fieles:
- 'label': etiqueta corta de la funcion o tema (<= 70 caracteres, sin llaves), p. ej. 'plural nominal; plural de 3a persona verbal'.
- 'summary': resumen en espanol de 1 o 2 frases (<= 230 caracteres) para que un traductor sepa que encontrara en la pagina.
Responde solo con el JSON del esquema."""

ESQUEMA_JUEZ = {
    "type": "OBJECT",
    "properties": {
        "label": {"type": "STRING"},
        "summary": {"type": "STRING"},
        "facts": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "i": {"type": "INTEGER"},
                    "verdict": {"type": "STRING", "enum": ["fiel", "parcial", "no_sustentado"]},
                    "duplicate_of": {"type": "INTEGER"},
                    "priority": {"type": "INTEGER"},
                },
                "required": ["i", "verdict", "duplicate_of", "priority"],
            },
        },
    },
    "required": ["label", "summary", "facts"],
}


# --------------------------------------------------------------------------
# Fase 1: extraccion por ventanas
# --------------------------------------------------------------------------

def ventanas() -> list[tuple[str, int, int]]:
    out = [("rosetta", 13, 931)]
    for ini, fin in RANGOS_LEVINSOHN:
        a = ini
        while a <= fin:
            b = min(fin, a + TAM_VENTANA - 1)
            out.append(("levinsohn", a, b))
            if b == fin:
                break
            a = b + 1 - SOLAPE
    return out


def extraer_ventana(docs: dict[str, Documento], doc: str, ini: int, fin: int, pasada: str) -> dict:
    if pasada == "sufijos":
        inventario = "\n".join(f"- {k} = {v}" for k, v in INVENTARIO_SUFIJOS.items())
        instr = INSTR_SUFIJOS.replace("{inventario}", inventario)
    else:
        inventario = "\n".join(f"- {k} = {v}" for k, v in TEMAS_GRAMATICA.items())
        instr = INSTR_GRAMATICA.replace("{inventario}", inventario)
    nombre = ("'Una gramatica pedagogica del inga' (Levinsohn)" if doc == "levinsohn"
              else "'Apuntes sobre la gramatica inga', apendice B del Diccionario inga (Tandioy, Levinsohn y Maffla, 1978)")
    prompt = (f"{instr}\n\nDOCUMENTO: {nombre}. FRAGMENTO: lineas {ini} a {fin}.\n"
              f"Se exhaustivo: recorre el fragmento de principio a fin.\n\n"
              f"=== FRAGMENTO ===\n{docs[doc].numerado(ini, fin)}\n=== FIN ===")
    etiqueta = f"ext-{pasada}-{doc}-{ini}-{fin}"
    datos = llamar_json(etiqueta, SISTEMA_BASE, prompt, ESQUEMA_EXTRACCION)
    n = sum(len(p.get("facts", [])) for p in datos.get("pages", []))
    log(f"  {etiqueta}: {len(datos.get('pages', []))} paginas, {n} hechos")
    return {"doc": doc, "ini": ini, "fin": fin, "pasada": pasada, "datos": datos}


def slug_limpio(slug: str, kind: str) -> str:
    s = slug.strip().lower().translate(_ACENTOS)
    if kind == "suffix":
        s = s.lstrip("-")
        if s not in INVENTARIO_SUFIJOS:
            s = a_corpus(s)
        return re.sub(r"[^a-zñ]", "", s)
    s = s.replace("ñ", "n")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


# --------------------------------------------------------------------------
# Fase 2-3: verificacion en codigo, fusion y deduplicacion
# --------------------------------------------------------------------------

def verificar_y_fusionar(docs: dict[str, Documento], resultados: list[dict]) -> tuple[dict, Counter]:
    paginas: dict[tuple[str, str], dict] = {}
    cuenta = Counter()
    for res in resultados:
        doc = docs[res["doc"]]
        for p in res["datos"].get("pages", []):
            kind = p.get("kind") or ("suffix" if res["pasada"] == "sufijos" else "grammar")
            if res["pasada"] == "sufijos":
                kind = "suffix"
            elif kind == "suffix":
                kind = "grammar"
            slug = slug_limpio(p.get("slug", ""), kind)
            slug = FUSION_SLUGS.get((kind, slug), slug)
            kind = TIPO_FORZADO.get(slug, kind)
            if not slug:
                cuenta["pagina_sin_slug"] += 1
                continue
            pag = paginas.setdefault((kind, slug), {
                "kind": kind, "slug": slug, "titulos": [], "formas": [], "hechos": []})
            pag["titulos"].append(p.get("title", ""))
            for f in p.get("source_forms", []):
                pag["formas"].extend(formas_de(f))
            for h in p.get("facts", []):
                cuenta["hechos_modelo"] += 1
                texto = _RE_ESPACIOS.sub(" ", h.get("text", "")).strip()
                cruda = h.get("quote", "")
                if len(cruda) > CAP_CITA:
                    cruda = cruda[:CAP_CITA].rsplit(" ", 1)[0]
                cita = _RE_ESPACIOS.sub(" ", cruda).strip()
                if not texto or h.get("section") not in SECCIONES:
                    cuenta["descartado_formato"] += 1
                    continue
                try:
                    ini, fin = int(h["ref_start"]), int(h["ref_end"])
                except (KeyError, TypeError, ValueError):
                    cuenta["descartado_formato"] += 1
                    continue
                # el rango debe caer en la ventana que vio el modelo
                if ini < res["ini"] - 1 or fin > res["fin"] + 1 or fin - ini > 60:
                    cuenta["descartado_rango"] += 1
                    continue
                if any(res["doc"] == d and ini <= z1 and fin >= z0 and pat.search(texto)
                       for d, z0, z1, pat in EXCLUSIONES_OCR):
                    cuenta["descartado_zona_ocr"] += 1
                    continue
                modo, a, b, ratio = doc.verificar(cruda, ini, fin)
                if modo == "segmentada":
                    cita = cita_limpia(cruda)[:CAP_CITA]
                cuenta[f"cita_{modo}"] += 1
                if modo == "falla":
                    continue
                pag["hechos"].append({
                    "section": h["section"], "text": texto,
                    "sources": [{"doc": res["doc"], "ini": a, "fin": b, "quote": cita, "modo": modo}],
                })
    for pag in paginas.values():
        pag["hechos"] = _dedupe(pag["hechos"], cuenta)
    return paginas, cuenta


def _dedupe(hechos: list[dict], cuenta: Counter) -> list[dict]:
    out: list[dict] = []
    for h in hechos:
        clave = plegar(h["text"])
        dup = None
        for o in out:
            if o["section"] != h["section"]:
                continue
            misma_cita = any(plegar(s["quote"]) == plegar(t["quote"])
                             for s in o["sources"] for t in h["sources"])
            r = difflib.SequenceMatcher(None, plegar(o["text"]), clave, autojunk=False).ratio()
            if r >= 0.9 or (misma_cita and r >= 0.75):
                dup = o
                break
        if dup is None:
            out.append(h)
            continue
        cuenta["dedupe_casi_identico"] += 1
        for s in h["sources"]:
            ya = any(s["doc"] == t["doc"] and s["ini"] == t["ini"] and s["fin"] == t["fin"]
                     for t in dup["sources"])
            if not ya and len(dup["sources"]) < 3:
                dup["sources"].append(s)
    return out


# --------------------------------------------------------------------------
# Fase 4: juez por pagina
# --------------------------------------------------------------------------

def juzgar_pagina(docs: dict[str, Documento], pag: dict) -> dict:
    bloques = []
    for i, h in enumerate(pag["hechos"]):
        s = h["sources"][0]
        lineas = docs[s["doc"]].numerado(s["ini"] - 3, s["fin"] + 3)
        bloques.append(f"[{i}] seccion={h['section']}\nHECHO: {h['text']}\nCITA: {s['quote']}\n"
                       f"LINEAS DE LA FUENTE ({s['doc']}):\n{lineas}")
    if pag["kind"] == "suffix":
        tema = (f"sufijo o clitico '{pag['slug']}' (slug en ortografia moderna; en las fuentes: "
                f"{', '.join('-' + f for f in sorted(set(pag['formas']))) or 'ver hechos'})")
    else:
        tema = f"tema gramatical '{pag['slug']}' ({TEMAS_GRAMATICA.get(pag['slug'], pag['titulos'][0] if pag['titulos'] else '')})"
    prompt = f"PAGINA: {pag['kind']}:{pag['slug']} - {tema}\n\n" + "\n\n".join(bloques)
    datos = llamar_json(f"juez-{pag['kind']}-{pag['slug']}", SISTEMA_JUEZ, prompt, ESQUEMA_JUEZ)
    return datos


def aplicar_juicio(pag: dict, juicio: dict | None, cuenta: Counter) -> None:
    if juicio is None:
        pag["label"], pag["summary"] = "", ""
        for h in pag["hechos"]:
            h["priority"] = 2
        return
    por_i = {v.get("i"): v for v in juicio.get("facts", [])}
    fieles = []
    for i, h in enumerate(pag["hechos"]):
        v = por_i.get(i)
        if v is None:
            cuenta["juez_sin_veredicto"] += 1
            continue
        cuenta[f"juez_{v['verdict']}"] += 1
        if v["verdict"] != "fiel":
            continue
        d = v.get("duplicate_of", -1)
        if isinstance(d, int) and 0 <= d < i and por_i.get(d, {}).get("verdict") == "fiel":
            cuenta["juez_duplicado"] += 1
            continue
        h["priority"] = v.get("priority", 2) if v.get("priority") in (1, 2, 3) else 2
        fieles.append(h)
    pag["hechos"] = fieles
    pag["label"] = juicio.get("label", "").strip()
    pag["summary"] = juicio.get("summary", "").strip()


# --------------------------------------------------------------------------
# Fase 5-6: ensamblado final, alias, pagina de ortografia y escritura
# --------------------------------------------------------------------------

def tokens_train() -> Counter:
    c = Counter()
    with RUTA_TRAIN.open(encoding="utf-8") as fh:
        for linea in fh:
            d = json.loads(linea)
            c.update(re.findall(r"[a-záéíóúñ]+", d["texto_inga"].lower()))
    return c


_PREFIJOS_COMBINADOS = ("pag", "bag")


def alias_de(pag: dict, slugs_pagina: set[str]) -> tuple[list[str], list[str]]:
    """Devuelve (alias, formas_fuente) para una pagina de sufijo.

    Las formas del inventario y de ALIAS_EXTRA entran siempre. Las que propone
    el modelo se filtran: fuera las de una sola letra, las que pertenecen a otra
    pagina (otro slug u otra entrada del inventario) y las combinaciones con
    otros sufijos delante, salvo -pag/-bag + caso.
    """
    slug = pag["slug"]
    propias = formas_de(INVENTARIO_SUFIJOS.get(slug, ""))
    extra = [a.lstrip("-") for a in ALIAS_EXTRA.get(slug, [])]
    ajenas = set(slugs_pagina) - {slug}
    for otro, formas in INVENTARIO_SUFIJOS.items():
        if otro != slug:
            ajenas.update(a_corpus(f) for f in formas_de(formas))
            ajenas.add(otro)
    seguras = {slug, *extra, *(a_corpus(f) for f in propias)}
    fuente = list(propias)
    for f in dict.fromkeys(pag["formas"]):
        c = a_corpus(f)
        if f in fuente:
            continue
        if c in seguras:
            fuente.append(f)
            continue
        if len(c) == 1 or c in ajenas:
            continue
        if c.endswith(slug) and c[: -len(slug)] not in _PREFIJOS_COMBINADOS:
            continue
        if c.startswith(slug) and c[len(slug):] in ajenas:
            continue
        fuente.append(f)
    corpus = [slug] + [a_corpus(f) for f in fuente] + extra
    alias = []
    for f in dict.fromkeys(corpus + fuente):
        alias.extend([f"-{f}", f])
    return alias, fuente


# Levinsohn numera los dialectos (L189-L192); se anota el nombre junto al numero
# y se agrega esa linea como fuente adicional del hecho.
DIALECTOS_LEVINSOHN = {"1": ("Santiago", 189), "2": ("San Andrés", 190),
                       "3": ("Ingano, al este de Mocoa", 191), "4": ("Aponte", 192)}
_RE_DIALECTO = re.compile(r"dialectos?\s+((?:[1-4]\s*(?:,|y|o|e)?\s*)+)", re.I)


def anotar_dialectos(texto: str, fuentes: list[dict], docs: dict) -> str:
    if not any(f["ref"].startswith("levinsohn:") for f in fuentes):
        return texto
    nums = sorted({n for m in _RE_DIALECTO.finditer(texto) for n in re.findall(r"[1-4]", m.group(1))})
    if not nums:
        return texto
    clave = " [Dialectos: " + ", ".join(f"{n} = {DIALECTOS_LEVINSOHN[n][0]}" for n in nums) + "]"
    if len(texto) + len(clave) > CAP_TEXTO:
        return texto
    a, b = DIALECTOS_LEVINSOHN[nums[0]][1], DIALECTOS_LEVINSOHN[nums[-1]][1]
    cita = " ".join(docs["levinsohn"].lineas[i - 1].strip() for i in range(a, b + 1))
    if len(cita) > CAP_CITA:
        a = b = DIALECTOS_LEVINSOHN[nums[0]][1]
        cita = docs["levinsohn"].lineas[a - 1].strip()
    if docs["levinsohn"].verificar(cita, a, b)[0] == "falla" or len(fuentes) >= 4:
        return texto
    fuentes.append({"type": "grammar", "ref": f"levinsohn:L{a}-L{b}", "quote": cita})
    return texto + clave


def ensamblar(pag: dict, registro_formas: list[str], docs: dict, slugs_pagina: set[str]) -> dict | None:
    if not pag["hechos"]:
        return None
    orden_sec = {s: i for i, s in enumerate(["morphology", "meaning", "usage", "example", "note"])}
    for fijo in HECHOS_FIJOS.get((pag["kind"], pag["slug"]), []):
        fuentes = []
        for d, a, b, cita in fijo["sources"]:
            if docs[d].verificar(cita, a, b)[0] == "falla":
                raise RuntimeError(f"hecho fijo con cita no verificable: {d}:L{a}-L{b}")
            fuentes.append({"doc": d, "ini": a, "fin": b, "quote": cita})
        pag["hechos"].append({"section": fijo["section"], "text": fijo["text"],
                              "sources": fuentes, "priority": 1})
    hechos = sorted(pag["hechos"], key=lambda h: (h.get("priority", 2), orden_sec[h["section"]]))
    hechos = hechos[:CAP_HECHOS]
    hechos.sort(key=lambda h: orden_sec[h["section"]])
    facts = []
    for h in hechos:
        texto = convertir_llaves(h["text"], registro_formas)
        if len(texto) > CAP_TEXTO:
            continue
        fuentes = [{"type": "grammar", "ref": f"{s['doc']}:L{s['ini']}-L{s['fin']}",
                    "quote": s["quote"][:CAP_CITA]} for s in h["sources"]]
        texto = anotar_dialectos(texto, fuentes, docs)
        facts.append({"section": h["section"], "text": texto, "sources": fuentes})
    if not facts:
        return None
    label = convertir_llaves(pag.get("label", "")) or (pag["titulos"][0] if pag["titulos"] else pag["slug"])
    resumen = convertir_llaves(pag.get("summary", ""))
    salida = {"id": f"{pag['kind']}:{pag['slug']}", "kind": pag["kind"], "slug": pag["slug"]}
    if pag["kind"] == "suffix":
        alias, fuente = alias_de(pag, slugs_pagina)
        titulo = f"-{pag['slug']} ({label})"
        distintas = [f"-{f}" for f in fuente if a_corpus(f) != f]
        if distintas:
            nota = f" En las fuentes (ortografía de 1978): {', '.join(distintas[:4])}."
            if len(resumen) + len(nota) <= CAP_RESUMEN:
                resumen += nota
        salida.update({"title": titulo[:CAP_TITULO], "summary": resumen[:CAP_RESUMEN], "aliases": alias})
    else:
        base = TEMAS_GRAMATICA.get(pag["slug"])
        titulo = label[:1].upper() + label[1:] if label else (base or pag["slug"])
        salida.update({"title": titulo[:CAP_TITULO], "summary": resumen[:CAP_RESUMEN]})
    salida["facts"] = facts
    return salida


PARES_ORTOGRAFIA = [
    ("c/qu de las fuentes = k del corpus", [("nuca", "nuka"), ("runacuna", "runakuna"), ("quilla", "killa"), ("quiquin", "kikin")]),
    ("hu + vocal de las fuentes = w del corpus", [("huasi", "wasi"), ("huarmi", "warmi"), ("huañuy", "wañui")]),
    ("y de las fuentes = i del corpus", [("yacu", "iaku"), ("pay", "pai"), ("yachachig", "iachachig"), ("riy", "rii")]),
    ("gui de las fuentes = gi del corpus", [("cangui", "kangi"), ("munangui", "munangi")]),
    ("j final de sílaba de las fuentes = g del corpus", [("paypaj", "paipag"), ("nijpi", "nigpi"), ("suj", "sug")]),
    ("sufijo -hora de las fuentes = -ura del corpus", [("chihora", "chiura"), ("cunahora", "kunaura")]),
]
# Prestamos del espanol: la correspondencia no es regular (e/o de la fuente
# frente a i/u del corpus), por eso se listan pares completos atestiguados.
PARES_PRESTAMOS = [("puebloma", "puibluma")]


def pagina_ortografia(docs: dict[str, Documento]) -> dict | None:
    """Pagina de convencion construida por codigo: cada hecho cita una linea de
    las fuentes con la grafia antigua y un versiculo de TRAIN con la del corpus."""
    versos = []
    with RUTA_TRAIN.open(encoding="utf-8") as fh:
        for linea in fh:
            versos.append(json.loads(linea))
    facts = []
    grupos = [(r, p, True) for r, p in PARES_ORTOGRAFIA]
    grupos.append(("en préstamos del español las fuentes conservan e/o donde el corpus escribe i/u "
                   "(la conversión automática de esta wiki NO aplica este cambio)", PARES_PRESTAMOS, False))
    for regla, pares, regular in grupos:
        for vieja, nueva in pares:
            fuente = None
            for nombre in ("rosetta", "levinsohn"):
                d = docs[nombre]
                pat = re.compile(rf"(?<![a-zñ]){re.escape(vieja)}(?![a-zñ])", re.I)
                for i, l in enumerate(d.lineas, 1):
                    if pat.search(l) and 15 <= len(l.strip()) <= CAP_CITA:
                        fuente = (nombre, i, l.strip())
                        break
                if fuente:
                    break
            verso = None
            pat_n = re.compile(rf"(?<![a-zñ]){re.escape(nueva)}(?![a-zñ])", re.I)
            for v in versos:
                m = pat_n.search(v["texto_inga"])
                if m:
                    a = max(0, m.start() - 80)
                    trozo = v["texto_inga"][a:m.end() + 80].strip()
                    verso = (f"{v['libro']} {v['capitulo']}:{v['versiculo']}", trozo)
                    break
            if not (fuente and verso) or (regular and a_corpus(vieja) != nueva):
                continue
            facts.append({
                "section": "note",
                "text": (f"Regla: {regla}. Las fuentes gramaticales (1978) escriben '{vieja}'; "
                         f"el corpus escribe '{nueva}'."),
                "sources": [
                    {"type": "grammar", "ref": f"{fuente[0]}:L{fuente[1]}-L{fuente[1]}", "quote": fuente[2]},
                    {"type": "corpus", "ref": verso[0], "quote": verso[1][:CAP_CITA]},
                ],
            })
    if not facts:
        return None
    return {
        "id": "convention:ortografia-fuentes-vs-corpus", "kind": "convention",
        "slug": "ortografia-fuentes-vs-corpus",
        "title": "Ortografía de las fuentes gramaticales (1978) frente a la del corpus",
        "summary": ("Correspondencias regulares entre la grafía de Levinsohn y del apéndice (c, qu, hu, y, j) y la "
                    "del corpus (k, w, i, g). En esta wiki las formas inga de los hechos se muestran ya "
                    "convertidas a la grafía del corpus; las citas conservan la grafía original."),
        "facts": facts,
    }


def validar(ruta: Path, docs: dict[str, Documento]) -> dict:
    ids, n_hechos, errores = set(), 0, []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        try:
            p = json.loads(linea)
        except json.JSONDecodeError:
            errores.append(f"L{n}: no es JSON")
            continue
        if p["id"] in ids or p["id"] != f"{p['kind']}:{p['slug']}":
            errores.append(f"{p['id']}: id duplicado o inconsistente")
        ids.add(p["id"])
        if len(p["title"]) > CAP_TITULO or len(p["summary"]) > CAP_RESUMEN or not p["title"]:
            errores.append(f"{p['id']}: titulo/resumen fuera de limite")
        if not (1 <= len(p["facts"]) <= CAP_HECHOS):
            errores.append(f"{p['id']}: {len(p['facts'])} hechos")
        for f in p["facts"]:
            n_hechos += 1
            if f["section"] not in SECCIONES or not (0 < len(f["text"]) <= CAP_TEXTO):
                errores.append(f"{p['id']}: hecho invalido")
            if not f["sources"]:
                errores.append(f"{p['id']}: hecho sin fuente")
            for s in f["sources"]:
                if len(s["quote"]) > CAP_CITA or s["type"] not in ("grammar", "corpus"):
                    errores.append(f"{p['id']}: fuente invalida")
                if s["type"] == "grammar":
                    m = re.fullmatch(r"(levinsohn|rosetta):L(\d+)-L(\d+)", s["ref"])
                    if not m:
                        errores.append(f"{p['id']}: ref invalida {s['ref']}")
                        continue
                    modo = docs[m.group(1)].verificar(s["quote"], int(m.group(2)), int(m.group(3)))[0]
                    if modo == "falla":
                        errores.append(f"{p['id']}: cita no verificable {s['ref']}")
    return {"paginas": len(ids), "hechos": n_hechos, "errores": errores}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--solo-extraer", action="store_true")
    ap.add_argument("--sin-juez", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    DIR_CACHE.mkdir(parents=True, exist_ok=True)
    (DIR_CACHE / ".gitignore").write_text("*\n", encoding="utf-8")
    docs = {k: Documento(k, v) for k, v in DOCS.items()}

    tareas = [(d, a, b, pasada) for d, a, b in ventanas() for pasada in ("sufijos", "gramatica")]
    log(f"Fase 1: {len(tareas)} llamadas de extraccion ({DEFAULT_MODEL})")
    resultados = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futuros = {ex.submit(extraer_ventana, docs, *t): t for t in tareas}
        for fut in as_completed(futuros):
            try:
                resultados.append(fut.result())
            except Exception as e:  # una ventana fallida no tumba el resto
                log(f"  ERROR en {futuros[fut]}: {type(e).__name__}: {e}")
    resultados.sort(key=lambda r: (r["pasada"], r["doc"] != "rosetta", r["ini"]))
    if args.solo_extraer:
        log(f"uso: {dict(USO)}")
        return 0

    paginas, cuenta = verificar_y_fusionar(docs, resultados)
    n_verif = sum(len(p["hechos"]) for p in paginas.values())
    log(f"Fase 2-3: {len(paginas)} paginas, {n_verif} hechos verificados y fusionados")
    log(f"  conteos: {dict(cuenta)}")

    paginas = {k: p for k, p in paginas.items() if p["hechos"]}
    if not args.sin_juez:
        log(f"Fase 4: juez sobre {len(paginas)} paginas")
        juicios = {}
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futuros = {ex.submit(juzgar_pagina, docs, p): k for k, p in paginas.items()}
            for fut in as_completed(futuros):
                k = futuros[fut]
                try:
                    juicios[k] = fut.result()
                except Exception as e:
                    log(f"  ERROR juez {k}: {type(e).__name__}: {e}")
        for k, p in paginas.items():
            if k in juicios:
                aplicar_juicio(p, juicios[k], cuenta)
            else:
                # sin juicio no se publica la pagina (preferimos ausencia a error)
                cuenta["paginas_sin_juicio"] += 1
                p["hechos"] = []
    else:
        for p in paginas.values():
            aplicar_juicio(p, None, cuenta)

    registro: list[str] = []
    slugs_suf = {p["slug"] for p in paginas.values() if p["kind"] == "suffix" and p["hechos"]}
    finales = [x for x in (ensamblar(p, registro, docs, slugs_suf) for p in paginas.values()) if x]
    orto = pagina_ortografia(docs)
    sufijos = sorted((p for p in finales if p["kind"] == "suffix"), key=lambda p: p["slug"])
    gramatica = sorted((p for p in finales if p["kind"] != "suffix"), key=lambda p: (p["kind"], p["slug"]))
    if orto:
        gramatica.append(orto)

    DIR_SEED.mkdir(parents=True, exist_ok=True)
    for nombre, lote in (("suffixes.jsonl", sufijos), ("grammar.jsonl", gramatica)):
        with (DIR_SEED / nombre).open("w", encoding="utf-8") as fh:
            for p in lote:
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")

    # Informe
    toks = tokens_train()
    log("\n=== RESUMEN ===")
    log(f"conteos: {json.dumps(dict(cuenta), ensure_ascii=False)}")
    for nombre in ("suffixes.jsonl", "grammar.jsonl"):
        v = validar(DIR_SEED / nombre, docs)
        log(f"{nombre}: {v['paginas']} paginas, {v['hechos']} hechos, {len(v['errores'])} errores")
        for e in v["errores"][:20]:
            log(f"  ! {e}")
    log("cobertura de alias de sufijos en TRAIN (tokens distintos que terminan en el alias):")
    for p in sufijos:
        vistos = []
        for a in p["aliases"]:
            if a.startswith("-"):
                continue
            n = sum(1 for t in toks if t.endswith(a) and len(t) > len(a) + 1)
            vistos.append(f"{a}:{n}")
        log(f"  {p['slug']:<10} {len(p['facts']):>2} hechos  {' '.join(vistos)}")
    palabras = [w.lower() for f in registro for w in re.findall(r"[A-Za-zñÑáéíóú]+", a_corpus(f))
                if not f.strip().startswith("-")]
    if palabras:
        ok = sum(1 for w in palabras if w in toks)
        log(f"formas inga convertidas: {len(palabras)} palabras, {ok} ({ok / len(palabras):.0%}) atestiguadas en TRAIN")
    # Precio supuesto de gemini-3.1-pro-preview: 2 USD/M entrada, 12 USD/M salida (incluye razonamiento).
    usd = USO["entrada"] / 1e6 * 2 + (USO["salida"] + USO["razonamiento"]) / 1e6 * 12
    log(f"uso Gemini: {dict(USO)}; costo estimado ~{usd:.2f} USD; reloj {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
