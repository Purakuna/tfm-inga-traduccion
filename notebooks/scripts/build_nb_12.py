"""Generador del notebook 12: extraccion estructurada del AT Inga (Pasajes Historicos)."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "12_extraccion_AT_inga.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(t): nb.cells.append(nbf.v4.new_markdown_cell(t))
def code(t): nb.cells.append(nbf.v4.new_code_cell(t))


md(
    """# Notebook 12 - Extraccion estructurada del Antiguo Testamento Inga

**Entrega 2 - Expansion del corpus.**

Parsea `datos/ocr/at-pasajes-inga/inbPOT-Catholic.txt` (Pasajes Historicos
del AT en Inga, edicion Catolica con deuterocanonicos, 1997) y produce
`datos/at_inga_estructurado.jsonl` con la tupla (libro, capitulo,
versiculo, texto_inga).

## Estrategia

El PDF tiene texto extraible nativo (Word 2010 export), sin OCR necesario.
La estructura es similar al NT Inga: cabeceras de libro en mayusculas
centradas, marcadores de versiculo ASCII inline.

Los libros deuterocanonicos (Sabiduria, Eclesiastico, 2 Macabeos) se
detectan pero no se alinearan contra RV1909 (que es canon protestante).
Quedaran disponibles como dato monolingue Inga para futura referencia.
"""
)

code(
    """import json
import re
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
SRC = ROOT / "datos" / "ocr" / "at-pasajes-inga" / "inbPOT-Catholic.txt"
OUT = ROOT / "datos" / "at_inga_estructurado.jsonl"

raw = SRC.read_text(encoding="utf-8")
print(f"Lineas: {len(raw.splitlines()):,}")
"""
)

md("## Mapeo libros AT Inga -> canonico espanol")

code(
    """# Cada libro tiene su nombre Inga (puede ser largo o corto) + a veces el espanol entre parentesis
LIBROS_AT = {
    "KALLARIIKUNAMANDA": "Genesis",
    "EJIPTO ALPAMANDA LLUGSISKAMANDA": "Exodo",
    "EJIPTOMANDA LLUGSISKAMANDA": "Exodo",
    "LEBIMANDAKUNATA IMA RURANGAPA CHAIAGTA": "Levitico",
    "LEBIMANDAKUNATA": "Levitico",
    "NUMEROS": "Numeros",
    "DEUTERONOMIO": "Deuteronomio",
    "JOSUE": "Josue",
    "JOSUÉ": "Josue",
    "JUECES": "Jueces",
    "1 SAMUEL": "1 Samuel",
    "2 SAMUEL": "2 Samuel",
    "1 REYES": "1 Reyes",
    "2 REYES": "2 Reyes",
    "1 CRONICAS": "1 Cronicas",
    "1 CRÓNICAS": "1 Cronicas",
    "2 CRONICAS": "2 Cronicas",
    "2 CRÓNICAS": "2 Cronicas",
    "2 MACABEOS": "2 Macabeos",  # deuterocanonico
    "SALMOS": "Salmos",
    "PROVERBIOS": "Proverbios",
    "ECLESIASTES": "Eclesiastes",
    "ECLESIASTÉS": "Eclesiastes",
    "SABIDURIA": "Sabiduria",  # deuterocanonico
    "ECLESIASTICO": "Eclesiastico",  # deuterocanonico
    "ISAIAS": "Isaias",
    "ISAÍAS": "Isaias",
    "JEREMIAS": "Jeremias",
    "EZEQUIEL": "Ezequiel",
    "OSEAS": "Oseas",
    "AMOS": "Amos",
    "JONAS": "Jonas",
    "HABACUC": "Habacuc",
    "SOFONIAS": "Sofonias",
    "ZACARIAS": "Zacarias",
    "ZACARÍAS": "Zacarias",
    "MALAQUIAS": "Malaquias",
    "MALAQUÍAS": "Malaquias",
}

LIBROS_CANONICOS_PROTESTANTES = {
    "Genesis", "Exodo", "Levitico", "Numeros", "Deuteronomio", "Josue", "Jueces",
    "1 Samuel", "2 Samuel", "1 Reyes", "2 Reyes", "1 Cronicas", "2 Cronicas",
    "Salmos", "Proverbios", "Eclesiastes",
    "Isaias", "Jeremias", "Ezequiel", "Oseas", "Amos", "Jonas",
    "Habacuc", "Sofonias", "Zacarias", "Malaquias",
}

LIBROS_DEUTERO = {"Sabiduria", "Eclesiastico", "2 Macabeos"}

print(f"Libros mapeados: {len(set(LIBROS_AT.values()))}")
print(f"De estos, alineables con RV1909 (canon protestante): {len(LIBROS_CANONICOS_PROTESTANTES)}")
print(f"Deuterocanonicos (solo Inga monolingue): {len(LIBROS_DEUTERO)}")
"""
)

md("## Detectores")

code(
    r'''# Lineas de heading de libro: en mayusculas, indentadas con espacios al inicio,
# usualmente unicas en la linea (sin texto adicional).
RE_BOOK_HEADING = re.compile(r"^\s+([A-ZÁÉÍÓÚ0-9 ]+)\s*$")

# Marcador de versiculo ASCII: 1-3 digitos seguidos de espacio y mayuscula
# (Inga usa mayuscula al inicio de oracion, y los marcadores de versiculo van
# tipicamente al inicio del texto que sigue).
RE_VERSE_ASCII = re.compile(
    r"(?:^|(?<=[\s\.\?\!:;\)]))(?P<num>\d{1,3})\s+(?P<letra>[A-ZÁÉÍÓÚÑ¿¡])"
)


def detect_book(line: str) -> str | None:
    """Devuelve el nombre canonico del libro si esta linea es un heading."""
    m = RE_BOOK_HEADING.match(line)
    if not m:
        return None
    raw = re.sub(r"\s+", " ", m.group(1)).strip()
    # Match exacto en el diccionario
    if raw in LIBROS_AT:
        return LIBROS_AT[raw]
    # Match parcial - el OCR puede tener variaciones menores
    for alias, canonico in LIBROS_AT.items():
        if raw == alias or alias in raw:
            return canonico
    return None


def find_chapter_marker(line: str) -> int | None:
    """Detecta una linea que es solo el numero de capitulo (e.g. '   2   ').

    En el OT Inga los capitulos se marcan a veces como una linea con solo el
    digito grande (mas que las marcas de versiculo). Pero la convencion no es
    estricta. Como fallback, sumamos 1 al capitulo cuando vemos un versiculo
    con numero menor al previo dentro del mismo libro.
    """
    s = line.strip()
    if s.isdigit() and 1 <= int(s) <= 200:
        return int(s)
    return None
'''
)

md("## Parser stateful")

code(
    r'''def parse_at_inga(raw_text: str):
    registros = []
    libro = None
    capitulo = 1
    verso_actual = None
    texto_actual: list[str] = []
    en_seccion_contenido = False  # arrancamos a procesar despues de la primera cabecera de libro

    def flush():
        nonlocal texto_actual, verso_actual
        if libro is None or verso_actual is None:
            texto_actual = []
            return
        texto = " ".join(texto_actual).strip()
        if not texto or len(texto.split()) < 3:
            texto_actual = []
            return
        registros.append({
            "libro": libro,
            "capitulo": capitulo,
            "versiculo": verso_actual,
            "texto_inga": texto,
        })
        texto_actual = []

    versiculo_max_visto = 0  # para detectar cambios de capitulo por reinicio
    for raw_line in raw_text.splitlines():
        line = raw_line.rstrip()

        # Heading de libro nuevo
        bk = detect_book(line)
        if bk is not None:
            flush()
            libro = bk
            capitulo = 1
            verso_actual = None
            versiculo_max_visto = 0
            en_seccion_contenido = True
            continue

        # Estamos antes de la primera cabecera de libro: descartar
        if not en_seccion_contenido or libro is None:
            continue

        # Lineas que son solo numero (probable cambio de capitulo)
        n = find_chapter_marker(line)
        if n is not None:
            # Solo aceptamos como cambio de capitulo si es estrictamente mayor al
            # capitulo actual (evita falsos positivos con numeros sueltos de versiculo)
            if n > capitulo:
                flush()
                capitulo = n
                verso_actual = None
                versiculo_max_visto = 0
            continue

        # Linea vacia o linea de copyright/footer
        if not line.strip():
            continue
        if "Wycliffe" in line or "Pasajes del Antiguo" in line:
            continue
        # Saltar pericope titles indentados pero no en mayusculas todas
        if re.match(r"^\s+[A-ZÁÉÍÓÚ][^a-záéíóú\d]{6,}$", line):
            # Cabecera mayuscula pura no mapeada -> pericope title, descartar
            continue

        # Buscar marcadores de versiculo dentro de la linea
        positions = []
        for m in RE_VERSE_ASCII.finditer(line):
            n_v = int(m.group("num"))
            if 1 <= n_v <= 200:
                positions.append((m.start("num"), m.start("letra"), n_v))

        if not positions:
            # Continuacion de versiculo previo
            if verso_actual is not None and line.strip():
                texto_actual.append(line.strip())
            continue

        # Texto antes del primer marcador: continuacion del verso previo
        if positions[0][0] > 0:
            prefijo = line[: positions[0][0]].strip()
            if prefijo and verso_actual is not None:
                texto_actual.append(prefijo)

        for i, (s, e, n_v) in enumerate(positions):
            next_s = positions[i + 1][0] if i + 1 < len(positions) else len(line)
            # Heuristica: si el numero baja respecto al maximo visto en el capitulo,
            # probablemente cambio de capitulo (algunos OT no marcan capitulo explicitamente)
            if n_v < versiculo_max_visto - 5:
                flush()
                capitulo += 1
                versiculo_max_visto = 0
            flush()
            verso_actual = n_v
            versiculo_max_visto = max(versiculo_max_visto, n_v)
            texto = line[e:next_s].strip()
            if texto:
                texto_actual.append(texto)

    flush()
    return registros


registros = parse_at_inga(raw)
print(f"Total registros extraidos: {len(registros):,}")
df = pd.DataFrame(registros)
print(f"Libros encontrados: {df.libro.nunique()}")
print("Distribucion por libro:")
print(df.groupby("libro").size().sort_values(ascending=False).head(15).to_string())
'''
)

md("## Validacion + persistir")

code(
    """OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as f:
    for r in registros:
        f.write(json.dumps(r, ensure_ascii=False) + "\\n")
print(f"Escrito: {OUT.relative_to(ROOT)}  ({len(registros):,} registros)")

# Cobertura: cuantos son alineables con RV1909
alineables = df[df.libro.isin(LIBROS_CANONICOS_PROTESTANTES)]
deutero = df[df.libro.isin(LIBROS_DEUTERO)]
print()
print(f"Alineables contra RV1909: {len(alineables):,}")
print(f"Deuterocanonicos (Inga monolingue): {len(deutero):,}")
"""
)

md("## Inspeccion: 5 registros aleatorios")

code(
    """muestra = df.sample(min(5, len(df)), random_state=42)
for _, row in muestra.iterrows():
    print(f"{row.libro} {row.capitulo}:{row.versiculo}")
    print(f"  {row.texto_inga[:200]}")
    print()
"""
)

nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
