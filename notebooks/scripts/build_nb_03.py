"""Helper que genera notebooks/03_extraccion_NT_inga_estructurada.ipynb.

Se ejecuta con `uv run python notebooks/scripts/build_nb_03.py` y produce el
notebook que parsea datos/ocr/inga-kichwa/00-WNTinb-web.md en versiculos
estructurados (libro, capitulo, versiculo, texto_inga) y persiste a
datos/nt_inga_estructurado.jsonl.
"""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "03_extraccion_NT_inga_estructurada.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(text: str) -> None:
    nb.cells.append(nbf.v4.new_markdown_cell(text))


def code(text: str) -> None:
    nb.cells.append(nbf.v4.new_code_cell(text))


md(
    """# Notebook 03 - Extraccion estructurada del NT Inga

**Entrega 2.** Parsea el OCR de Wycliffe `datos/ocr/inga-kichwa/00-WNTinb-web.md`
(595 paginas) y produce `datos/nt_inga_estructurado.jsonl` con la tupla cannica
`(libro, capitulo, versiculo, texto_inga)`. Insumo principal para la alineacion
con Reina-Valera 1909 que se ejecuta en el siguiente notebook.

## Estrategia

El OCR tiene tres tipos de senales utiles:

1. **Running headers** al inicio de cada pagina, en mayusculas: `HECHOS 1`,
   `HECHOS 1, 2`, `1 KORINTOPI CRISTOWA TUKUSKAKUNATA 5`. Cuando la cabecera
   incluye dos numeros (`X, Y`) significa que la pagina cubre el final del
   capitulo X y el inicio del capitulo Y.
2. **Markdown headings** `# BOOK_NAME` que marcan el inicio fisico de cada
   libro (es la unica senal para los 4 libros de un solo capitulo: Filemon,
   2/3 Juan, Judas).
3. **Marcadores de versiculo** dentro del texto, en dos formas mezcladas:
   - Caracteres Unicode superindice (`¹`, `²`, ..., concatenables como `¹²`).
   - Digitos ASCII al inicio de palabra (`13 `, `14 `).

Se filtran: pericope titles (`## ...`), pies de copyright, page markers
(`<!-- Page N -->`), numeros de pagina sueltos y bloques de introduccion
no biblicos.

## Salida

Un JSONL con un objeto por versiculo. Cuando el OCR concatena dos versos
en un solo marcador (p.ej. `⁴-⁵`), se emiten dos registros con el mismo
texto y el campo `verso_combinado=True`.
"""
)

code(
    """import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
SRC = ROOT / "datos" / "ocr" / "inga-kichwa" / "00-WNTinb-web.md"
OUT = ROOT / "datos" / "nt_inga_estructurado.jsonl"

raw = SRC.read_text(encoding="utf-8")
print(f"Lineas: {len(raw.splitlines()):,}")
print(f"Caracteres: {len(raw):,}")
"""
)

md(
    """## Diccionario de libros: alias del OCR -> nombre canonico

Los libros aparecen tanto en running headers como en markdown headings con
diferentes ortografias (`HECHOS` / `San Mateo` / `1 KORINTOPI CRISTOWA
TUKUSKAKUNATA` / `FILEMONTA`). Se mapea todo a un nombre canonico en
espanol que coincide con la nomenclatura de la Reina-Valera 1909.
"""
)

code(
    """LIBROS_CANONICOS = {
    # Evangelios y Hechos
    "SAN MATEO": "Mateo",
    "SAN MARCOS": "Marcos",
    "SAN LUCAS": "Lucas",
    "SAN JUAN": "Juan",           # evangelio. La epistola se desambigua por contexto
    "HECHOS": "Hechos",
    # Cartas paulinas
    "ROMAPI CRISTOWA TUKUSKAKUNATA": "Romanos",
    "1 KORINTOPI CRISTOWA TUKUSKAKUNATA": "1 Corintios",
    "2 KORINTOPI CRISTOWA TUKUSKAKUNATA": "2 Corintios",
    "GALASIAPI CRISTOWA TUKUSKAKUNATA": "Galatas",
    "EFESOPI CRISTOWA TUKUSKAKUNATA": "Efesios",
    "FILIPOSPI CRISTOWA TUKUSKAKUNATA": "Filipenses",
    "KOLOSASPI CRISTOWA TUKUSKAKUNATA": "Colosenses",
    "1 TESALONIKAPI CRISTOWA TUKUSKAKUNATA": "1 Tesalonicenses",
    "2 TESALONIKAPI CRISTOWA TUKUSKAKUNATA": "2 Tesalonicenses",
    "1 TIMOTEOTA": "1 Timoteo",
    "2 TIMOTEOTA": "2 Timoteo",
    "TITOTA": "Tito",
    "FILEMONTA": "Filemon",
    # Cartas generales
    "HEBREOKUNATA": "Hebreos",
    "SANTIAGO": "Santiago",
    "1 SAN PEDRO": "1 Pedro",
    "2 SAN PEDRO": "2 Pedro",
    "1 SAN JUAN": "1 Juan",
    "2 SAN JUAN": "2 Juan",
    "3 SAN JUAN": "3 Juan",
    "SAN JUDAS": "Judas",
    # Apocalipsis
    "APOCALIPSIS": "Apocalipsis",
}
print(f"Libros canonicos esperados: {len(LIBROS_CANONICOS)}")
assert len(LIBROS_CANONICOS) == 27, "El NT debe tener 27 libros"
"""
)

md(
    """## Detectores

Cuatro funciones puras que devuelven `None` si la linea no es del tipo
buscado, o el dato extraido si lo es. Esto permite priorizar el tipo de
linea cuando se procesa el texto de forma stateful.
"""
)

code(
    r'''SUPERS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
SUPER_TO_DIGIT = str.maketrans(SUPERS, "0123456789")

# Cabecera de pagina: "HECHOS 1", "HECHOS 1, 2", "1 KORINTOPI CRISTOWA TUKUSKAKUNATA 14"
# El nombre puede empezar por digito + espacio ("1 KORINTOPI ...").
RE_RUNHEAD = re.compile(r"^(?P<libro>[0-9]?\s?[A-ZÁÉÍÓÚ ]+?)\s+(?P<c1>[0-9]+)(?:,\s*(?P<c2>[0-9]+))?\s*$")

# Markdown heading que abre libro: "# FILEMONTA", "# SAN JUAN", "# APOCALIPSIS".
# Excluye titulos de pericope (que llevan minusculas o frases compuestas).
RE_BOOK_HEADING = re.compile(r"^#\s+([0-9]?\s?[A-ZÁÉÍÓÚ ]+)\s*$")

# Page marker insertado por el OCR: "<!-- Page 482 -->".
RE_PAGE = re.compile(r"^<!--\s*Page\s+\d+\s*-->\s*$")

# Linea solo con numero de pagina suelta: "476".
RE_PAGENUM = re.compile(r"^\s*\d+\s*$")

# Pericope title en markdown: "## titulo ..." o "### titulo ...".
RE_PERICOPE = re.compile(r"^#{2,}\s+")

# Patron para encontrar marcadores de versiculo dentro del texto:
#  - Uno o varios superindices contiguos opcionalmente con guion: "⁴-⁵", "¹²".
#  - O un grupo de digitos ASCII al inicio (sera filtrado contextualmente despues).
RE_VERSE_SUPER = re.compile(rf"[{SUPERS}]+(?:-[{SUPERS}]+)?")


def normalizar_libro(raw_name: str) -> str | None:
    """Mapea un nombre crudo (running header) a la clave canonica.

    Esta funcion se usa SOLO para running headers que llevan numero de
    capitulo (`SAN JUAN 3` es inequivocamente evangelio Juan cap 3,
    `1 SAN JUAN 3` es 1 Juan cap 3). Para markdown headings ambiguos
    se usa `resolver_book_heading` que considera el contexto.
    """
    nombre = re.sub(r"\s+", " ", raw_name.strip().upper())
    if nombre in LIBROS_CANONICOS:
        return LIBROS_CANONICOS[nombre]
    for alias, canonico in LIBROS_CANONICOS.items():
        if nombre == alias or alias in nombre or nombre in alias:
            return canonico
    return None


# Aliases ambiguos: cuando aparecen como `# HEADING` sin running header
# desambiguador, se resuelven al siguiente libro no visto en la secuencia
# canonica esperada.
ALIAS_AMBIGUO_A_SECUENCIA = {
    "SAN JUAN": ["Juan", "1 Juan", "2 Juan", "3 Juan"],
    "SAN PEDRO": ["1 Pedro", "2 Pedro"],
}


def resolver_book_heading(raw_name: str, libros_vistos: set[str]) -> str | None:
    """Resuelve un `# heading` considerando que libros ya fueron procesados.

    Orden de prioridad:
      1. Si el nombre raw esta en la tabla de alias ambiguos, asignar el siguiente
         libro de la secuencia canonica que aun no se haya visto.
      2. Si no es ambiguo, usar el mapping directo.
    """
    nombre = re.sub(r"\s+", " ", raw_name.strip().upper())
    if nombre in ALIAS_AMBIGUO_A_SECUENCIA:
        for candidato in ALIAS_AMBIGUO_A_SECUENCIA[nombre]:
            if candidato not in libros_vistos:
                return candidato
        return None
    if nombre in LIBROS_CANONICOS:
        return LIBROS_CANONICOS[nombre]
    return None


def parse_running_header(line: str):
    m = RE_RUNHEAD.match(line)
    if not m:
        return None
    canonico = normalizar_libro(m.group("libro"))
    if canonico is None:
        return None
    c1 = int(m.group("c1"))
    c2 = int(m.group("c2")) if m.group("c2") else None
    return canonico, c1, c2


def parse_book_heading_raw(line: str):
    """Devuelve el nombre raw del heading (sin normalizar) o None."""
    m = RE_BOOK_HEADING.match(line)
    return m.group(1) if m else None
'''
)

md(
    """## Parser principal

Walk lineal con estado: mantiene libro/capitulo actuales segun la ultima
cabecera vista, y para cada linea de texto extrae versiculos descomponiendo
por el patron de superindices o, en su defecto, por digitos ASCII iniciales
que parezcan marcadores de versiculo (digit + espacio + mayuscula).
"""
)

code(
    r'''# Marcador ASCII de versiculo: 1-3 digitos seguidos de espacio y mayuscula
# (Inga y espanol usan mayuscula al inicio de oracion). Debe estar precedido por
# inicio de linea, espacio, o signo de puntuacion (no por digito ni guion).
RE_VERSE_ASCII = re.compile(
    r"(?:^|(?<=[\s\.\?\!:;\)]))(?P<num>\d{1,3})\s+(?P<letra>[A-ZÁÉÍÓÚÑ])"
)


def extraer_versiculos_de_linea(linea: str):
    """Itera tuples (verso_marker, texto) encontrados en una linea de texto.

    Maneja tres casos:
      - Marcadores Unicode superindice: '⁴-⁵Kam ...' o '¹⁰Nuka ...'.
      - Marcadores ASCII en cualquier posicion: '13 Paita ...', incluso mid-line.
      - Texto sin marcador: se trata como continuacion del verso anterior.

    Los marcadores ASCII y Unicode se combinan en una sola lista ordenada por
    posicion en la linea para no perder ninguno.
    """
    positions = []
    # Superindices Unicode (inequivocos)
    for m in RE_VERSE_SUPER.finditer(linea):
        positions.append((m.start(), m.end(), m.group(0).translate(SUPER_TO_DIGIT)))
    # ASCII mid-line: rango de 1 a 200 considerado verso plausible
    for m in RE_VERSE_ASCII.finditer(linea):
        n = int(m.group("num"))
        if 1 <= n <= 200:
            # El marcador termina al inicio de la letra mayuscula del texto.
            positions.append((m.start("num"), m.start("letra"), str(n)))

    if not positions:
        yield (None, linea.strip())
        return

    # Ordenar por posicion de inicio
    positions.sort(key=lambda x: x[0])

    # Bloque previo al primer marcador: continuacion del verso anterior.
    if positions[0][0] > 0:
        prefijo = linea[: positions[0][0]].strip()
        if prefijo:
            yield (None, prefijo)

    # Para cada marcador, el texto va hasta el siguiente marcador (o fin de linea).
    for i, (s, e, marker) in enumerate(positions):
        next_s = positions[i + 1][0] if i + 1 < len(positions) else len(linea)
        texto = linea[e:next_s].strip()
        yield (marker, texto)


def parse_nt_inga(raw_text: str):
    """Devuelve lista de dicts (libro, capitulo, versiculo, texto_inga, verso_combinado)."""
    registros = []
    libro = None
    capitulo = None
    verso_actual = None
    texto_actual: list[str] = []
    verso_combinado = False
    libros_vistos: set[str] = set()

    def flush():
        nonlocal texto_actual, verso_actual, verso_combinado
        if libro is None or capitulo is None or verso_actual is None:
            texto_actual = []
            return
        texto = " ".join(texto_actual).strip()
        if not texto:
            texto_actual = []
            return
        # Marcadores combinados tipo "4-5" producen dos registros con mismo texto.
        if "-" in str(verso_actual):
            try:
                a, b = [int(x) for x in str(verso_actual).split("-", 1)]
            except ValueError:
                a, b = None, None
            if a is not None and b is not None and 0 < a <= b < 200:
                for v in range(a, b + 1):
                    registros.append({
                        "libro": libro,
                        "capitulo": capitulo,
                        "versiculo": v,
                        "texto_inga": texto,
                        "verso_combinado": True,
                    })
                texto_actual = []
                return
        try:
            v = int(verso_actual)
        except ValueError:
            texto_actual = []
            return
        registros.append({
            "libro": libro,
            "capitulo": capitulo,
            "versiculo": v,
            "texto_inga": texto,
            "verso_combinado": verso_combinado,
        })
        texto_actual = []

    for raw_line in raw_text.splitlines():
        line = raw_line.rstrip()

        if not line:
            continue
        if RE_PAGE.match(line):
            continue
        if RE_PAGENUM.match(line) and len(line.strip()) <= 4:
            continue
        if "Wycliffe" in line and "©" in line:  # pie de pagina con copyright
            continue
        if RE_PERICOPE.match(line):
            continue

        # 1. Running header de pagina (mas frecuente).
        h = parse_running_header(line)
        if h is not None:
            nuevo_libro, c1, c2 = h
            if libro != nuevo_libro:
                flush()
                libro = nuevo_libro
                libros_vistos.add(libro)
                verso_actual = None
            # La pagina puede cubrir transicion c1->c2; el numero relevante es
            # c2 si esta presente, porque el texto que sigue es ya del nuevo capitulo.
            target = c2 if c2 is not None else c1
            if capitulo != target:
                flush()
                capitulo = target
                verso_actual = None
            continue

        # 2. Markdown heading nivel 1: puede abrir libro nuevo o ser pericope.
        if line.lstrip().startswith("#") and not line.lstrip().startswith("##"):
            raw_heading = parse_book_heading_raw(line)
            if raw_heading is not None:
                bh = resolver_book_heading(raw_heading, libros_vistos)
                if bh is not None and bh in set(LIBROS_CANONICOS.values()):
                    if libro != bh:
                        flush()
                        libro = bh
                        libros_vistos.add(libro)
                        capitulo = 1  # libros de 1 capitulo empiezan implicitamente
                        verso_actual = None
                    continue
            # Es un # heading pero no es un libro -> pericope title; descartar
            continue

        # 3. Linea de contenido. Extraer marcadores de versiculo.
        if libro is None:
            # Texto antes del primer libro: prefacio, descartar.
            continue
        if capitulo is None:
            capitulo = 1  # asumir cap 1 si todavia no se ha visto un header

        for marker, texto in extraer_versiculos_de_linea(line):
            if marker is None:
                # Continuacion del verso actual
                if texto:
                    texto_actual.append(texto)
            else:
                # Nuevo marcador de verso: hacer flush del anterior.
                flush()
                verso_actual = marker
                verso_combinado = "-" in marker
                if texto:
                    texto_actual.append(texto)

    flush()
    return registros


registros = parse_nt_inga(raw)
print(f"Total registros extraidos: {len(registros):,}")
'''
)

md(
    """## Validacion: cobertura por libro

Se compara contra el conteo canonico del NT (~7.957 versiculos) y se reporta
distribucion por libro. Una desviacion grande en algun libro indica que el
parser no esta atrapando bien los marcadores en esa seccion.
"""
)

code(
    r'''CONTEO_CANONICO = {
    "Mateo": 1071, "Marcos": 678, "Lucas": 1151, "Juan": 879, "Hechos": 1007,
    "Romanos": 433, "1 Corintios": 437, "2 Corintios": 257, "Galatas": 149,
    "Efesios": 155, "Filipenses": 104, "Colosenses": 95,
    "1 Tesalonicenses": 89, "2 Tesalonicenses": 47,
    "1 Timoteo": 113, "2 Timoteo": 83, "Tito": 46, "Filemon": 25,
    "Hebreos": 303, "Santiago": 108,
    "1 Pedro": 105, "2 Pedro": 61,
    "1 Juan": 105, "2 Juan": 13, "3 Juan": 15, "Judas": 25,
    "Apocalipsis": 404,
}
TOTAL_CANONICO = sum(CONTEO_CANONICO.values())
print(f"Total canonico NT: {TOTAL_CANONICO}")

df = pd.DataFrame(registros)
# Para libros con verso_combinado, contar solo unicos por (libro, capitulo, versiculo).
unicos = df.drop_duplicates(subset=["libro", "capitulo", "versiculo"])
conteo_extraido = unicos.groupby("libro").size().to_dict()

print(f"{'Libro':<22}{'Canonico':>10}{'Extraido':>10}{'Cobertura':>12}")
print("-" * 54)
total_extraido = 0
for libro, canon in CONTEO_CANONICO.items():
    ext = conteo_extraido.get(libro, 0)
    cov = (ext / canon * 100) if canon else 0
    total_extraido += ext
    flag = " " if cov >= 90 else "!"
    print(f"{libro:<22}{canon:>10}{ext:>10}{cov:>11.1f}% {flag}")
print("-" * 54)
print(f"{'TOTAL':<22}{TOTAL_CANONICO:>10}{total_extraido:>10}{total_extraido/TOTAL_CANONICO*100:>11.1f}%")
'''
)

md(
    """## Inspeccion cualitativa: 5 versiculos aleatorios

Verifica que el contenido extraido es coherente (no incluye headers ni
fragmentos de pericope). Se imprime libro/capitulo/versiculo + texto inga.
"""
)

code(
    """muestra = df.drop_duplicates(subset=["libro", "capitulo", "versiculo"]).sample(5, random_state=42)
for _, row in muestra.iterrows():
    print(f"{row.libro} {row.capitulo}:{row.versiculo}")
    print(f"  {row.texto_inga[:200]}")
    print()
"""
)

md(
    """## Persistir a JSONL

Formato del registro:

```json
{"libro": "Mateo", "capitulo": 1, "versiculo": 1, "texto_inga": "...", "verso_combinado": false}
```

Si el OCR marcaba `4-5` (verso combinado), se duplica el texto en los dos
registros (verso 4 y verso 5) con `verso_combinado=true` para que la
alineacion los pueda recuperar individualmente.
"""
)

code(
    """OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as f:
    for r in registros:
        f.write(json.dumps(r, ensure_ascii=False) + "\\n")
print(f"Escrito: {OUT.relative_to(ROOT)}  ({len(registros):,} registros)")
"""
)

OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
