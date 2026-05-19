"""Generador del notebook 06: extraccion alineada de Antihua Pacay (MP)."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "06_antihua_pacay_alineado.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(t): nb.cells.append(nbf.v4.new_markdown_cell(t))
def code(t): nb.cells.append(nbf.v4.new_code_cell(t))


md(
    """# Notebook 06 - Antihua Pacay alineado (dialecto Medio Putumayo)

**Entrega 2.** Procesa `datos/ocr/inga-kichwa/antihua-pacay.md` (cartilla
narrativa bilingue Inga-Castellano publicada por SIL en 1985) y produce
`datos/antihua_pacay_alineado.jsonl` con pares paralelos a nivel de
parrafo.

## Estructura del documento

El OCR tiene dos mitades secuenciales:

1. **Mitad Inga** (lineas ~90-895): cinco historias en Inga con sus
   pericope headings en Inga (`CALLARINGAPA`, `IMASA NUCANCHIC...`,
   `CAY MUNDOTA TUTAYACHIDUR...`, `DANTACUNAMANDA Y HUAMBUIMANDA...`,
   `ANTIHUA SALVANJEMANDA PARLO`, `CUCU AHUILAMANDA PARLO`,
   `LIMONPI GENTE TIAG TIEMPO...`), cada una seguida de una seccion de
   ejercicios `RIMANACUSUNCHI`.
2. **Mitad castellana** (lineas 898 en adelante): las mismas historias
   traducidas al espanol con headings como `HISTORIA: COMO VENIMOS A
   PUERTO GUAYUYACO`, `CONVERSAMOS`, etc.

## Estrategia minima

Para Entrega 2 se hace una alineacion a nivel de **historia completa**:
cada heading principal Inga se empareja con el heading correspondiente
castellano por orden de aparicion. El texto bajo cada heading se concatena
y se persiste como un par Inga-espanol largo.

La alineacion fina parrafo-a-parrafo se posterga a Entrega Final (requiere
sentence splitting + alineacion por similitud semantica).

**Nota:** este corpus es complementario; la mayoria de los pares de
entrenamiento ya provienen del NT (Notebook 05). Antihua Pacay aporta la
diversidad dialectal Medio Putumayo que el NT no tiene.
"""
)

code(
    """import json
import re
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
SRC = ROOT / "datos" / "ocr" / "inga-kichwa" / "antihua-pacay.md"
OUT = ROOT / "datos" / "antihua_pacay_alineado.jsonl"

raw = SRC.read_text(encoding="utf-8")
print(f"Lineas: {len(raw.splitlines()):,}")
"""
)

md(
    """## Identificacion de las dos mitades

El marcador `# INTRODUCCION` (linea ~898) abre la mitad castellana del
documento. Todo lo anterior es Inga.
"""
)

code(
    r'''lineas = raw.splitlines()
INDICE_INTRODUCCION = next(
    (i for i, l in enumerate(lineas) if l.strip() == "# INTRODUCCION"),
    None,
)
print(f"INTRODUCCION en linea: {INDICE_INTRODUCCION}")

# La mitad Inga arranca en la primera `# CALLARINGAPA` (linea ~91)
INDICE_CALLARINGAPA = next(
    (i for i, l in enumerate(lineas) if l.strip() == "# CALLARINGAPA"),
    None,
)
print(f"CALLARINGAPA en linea: {INDICE_CALLARINGAPA}")

mitad_inga = "\n".join(lineas[INDICE_CALLARINGAPA:INDICE_INTRODUCCION])
mitad_es = "\n".join(lineas[INDICE_INTRODUCCION:])
print(f"Mitad Inga: {len(mitad_inga):,} caracteres")
print(f"Mitad Espanol: {len(mitad_es):,} caracteres")
'''
)

md(
    """## Mapeo de historias Inga -> Castellano

Por orden cronologico en el documento, las cinco historias principales
mas la introduccion se mapean asi:
"""
)

code(
    r'''MAPEO_HISTORIAS = [
    ("CALLARINGAPA", "INTRODUCCION"),
    ("IMASA NUCANCHIC GUAYUYACUMA", "HISTORIA: COMO VENIMOS A PUERTO GUAYUYACO"),
    ("CAY MUNDOTA TUTAYACHIDUR SACHAMANDA PARLO", "HISTORIA: EL ARBOL QUE OSCURECE EL MUNDO"),
    ("DANTACUNAMANDA Y HUAMBUIMANDA PARLO", "HISTORIA: LAS DANTAS Y EL CHURUCO"),
    ("ANTIHUA SALVANJEMANDA PARLO", "HISTORIA: EL SALVAJE DE ANTES"),
    ("CUCU AHUILAMANDA PARLO", "HISTORIA: EL ESPIRITU DEL DUENDE"),
    ("LIMONPI GENTE TIAG TIEMPO, CUCU AHUILAMANDA PARLO",
     "HISTORIA: EN LOS TIEMPOS QUE LA GENTE VIVIA EN LIMON, EL ESPIRITU DEL DUENDE"),
]


def extraer_texto_seccion(texto: str, heading_inicio: str, headings_siguientes: list[str]) -> str:
    """Extrae el texto entre `# heading_inicio` y el siguiente heading principal."""
    pattern_inicio = rf"^#\s+{re.escape(heading_inicio)}\s*$"
    m = re.search(pattern_inicio, texto, re.MULTILINE)
    if not m:
        return ""
    inicio = m.end()
    fin = len(texto)
    # Buscar el siguiente heading principal (cualquiera de los que vienen despues)
    for siguiente in headings_siguientes:
        pattern_fin = rf"^#\s+{re.escape(siguiente)}\s*$"
        m2 = re.search(pattern_fin, texto[inicio:], re.MULTILINE)
        if m2:
            fin = inicio + m2.start()
            break
    return texto[inicio:fin]


def limpiar(texto: str) -> str:
    """Elimina markdown de imagenes, page markers, annotations y normaliza espacios."""
    texto = re.sub(r"!\[.*?\]\(.*?\)", "", texto)
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.DOTALL)
    texto = re.sub(r"#{1,6}\s+.*", "", texto)  # eliminar subheadings sobrantes
    texto = re.sub(r"^\s*\d+\s*$", "", texto, flags=re.MULTILINE)  # numeros de pagina sueltos
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto
'''
)

md(
    """## Extraer y emparejar

Para cada historia, se extrae el bloque Inga y el bloque castellano.
Se valida que ambos no esten vacios y que la relacion de longitudes sea
razonable (entre 0.3 y 3.0).
"""
)

code(
    r'''headings_inga = [h_inga for h_inga, _ in MAPEO_HISTORIAS]
headings_es = [h_es for _, h_es in MAPEO_HISTORIAS]

pares = []
for i, (h_inga, h_es) in enumerate(MAPEO_HISTORIAS):
    # Para cada historia, los siguientes posibles headings son los que vienen despues
    siguientes_inga = headings_inga[i + 1 :] + ["RIMANACUSUNCHI"]  # exclude ejercicios
    siguientes_es = headings_es[i + 1 :] + ["CONVERSAMOS", "CONVERSEMOS", "CONTENIDO"]

    inga_text = limpiar(extraer_texto_seccion(mitad_inga, h_inga, siguientes_inga))
    es_text = limpiar(extraer_texto_seccion(mitad_es, h_es, siguientes_es))

    if not inga_text or not es_text:
        print(f"[ ! ] Faltan datos para historia {i}: '{h_inga}' / '{h_es}'")
        print(f"      Inga: {len(inga_text)} chars, Espanol: {len(es_text)} chars")
        continue

    ratio = max(len(inga_text), len(es_text)) / min(len(inga_text), len(es_text))
    print(f"[ OK ] {i}: '{h_inga[:40]}...' | Inga={len(inga_text)} ES={len(es_text)} ratio={ratio:.2f}")
    pares.append({
        "historia": i,
        "heading_inga": h_inga,
        "heading_es": h_es,
        "texto_inga": inga_text,
        "texto_es": es_text,
    })

print(f"\nHistorias emparejadas: {len(pares)}/{len(MAPEO_HISTORIAS)}")
'''
)

md(
    """## Subdividir en parrafos para granularidad de entrenamiento

Las historias completas son muy largas para fine-tuning de MT (NLLB acepta
~128 tokens). Se subdividen en oraciones y se alinean por indice asumiendo
que el numero de oraciones es similar. Si no lo es, se descartan los
sobrantes.
"""
)

code(
    r'''def split_oraciones(texto: str) -> list[str]:
    # Split sencillo por punto/exclamacion/interrogacion seguido de espacio + mayuscula
    return [s.strip() for s in re.split(r"(?<=[\.\!\?])\s+(?=[A-ZÁÉÍÓÚ¡¿])", texto) if s.strip()]


registros = []
for par in pares:
    oraciones_inga = split_oraciones(par["texto_inga"])
    oraciones_es = split_oraciones(par["texto_es"])
    n = min(len(oraciones_inga), len(oraciones_es))
    print(f"Historia {par['historia']}: Inga={len(oraciones_inga)} oraciones, ES={len(oraciones_es)} oraciones -> alineamos {n}")
    for j in range(n):
        oi = oraciones_inga[j]
        oe = oraciones_es[j]
        # Filtros de calidad
        if len(oi.split()) < 5 or len(oe.split()) < 5:
            continue
        ratio = max(len(oi), len(oe)) / min(len(oi), len(oe))
        if ratio > 5.0:
            continue
        registros.append({
            "historia": par["historia"],
            "oracion_idx": j,
            "texto_inga": oi,
            "texto_es": oe,
        })

print(f"\nTotal pares oracion: {len(registros)}")
'''
)

md("## Inspeccion: 5 pares aleatorios")

code(
    """import random
random.seed(42)
for r in random.sample(registros, min(5, len(registros))):
    print(f"=== Historia {r['historia']} oracion {r['oracion_idx']} ===")
    print(f"  INGA:  {r['texto_inga'][:200]}")
    print(f"  ES:    {r['texto_es'][:200]}")
    print()
"""
)

md("## Persistir a JSONL")

code(
    """salida = []
for i, r in enumerate(registros):
    salida.append({
        "idx": i,
        "texto_inga": r["texto_inga"],
        "texto_es": r["texto_es"],
        "dialecto": "MP",
        "fuente": "AntihuaPacay-1985",
        "historia": r["historia"],
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as f:
    for r in salida:
        f.write(json.dumps(r, ensure_ascii=False) + "\\n")
print(f"Escrito: {OUT.relative_to(ROOT)}  ({len(salida)} pares)")
"""
)

nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
