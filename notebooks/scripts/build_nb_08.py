"""Generador del notebook 08: indexacion vectorial RAG (Gemini + LanceDB)."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "08_indexacion_vectorial.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(t): nb.cells.append(nbf.v4.new_markdown_cell(t))
def code(t): nb.cells.append(nbf.v4.new_code_cell(t))


md(
    """# Notebook 08 - Indexacion vectorial RAG (Gemini embeddings + LanceDB)

**Entrega 2.** Construye los tres indices independientes del sistema RAG
multi-indice y los persiste en `lance_indexes/` para consulta posterior
desde el pipeline LLM+RAG (Notebook 11).

## Indices construidos

1. **lexico**: 4,900 entradas del Diccionario Inga (Tandioy 1997). Cada
   entrada se indexa por la composicion `lema (cat): glosa` para que el
   embedding capture tanto la palabra Inga como su definicion castellana.
2. **gramatical**: chunks de la Gramatica Pedagogica (Levinsohn) y el
   apendice morfosintactico Rosetta, segmentados por bloques de ~500
   palabras o por heading.
3. **ejemplos**: los 4,471 pares de train.jsonl indexados por la oracion
   Inga, devolviendo tambien el texto espanol como contexto para few-shot.

## Configuracion del embedder

Modelo: `gemini-embedding-001` con output reducido a 768 dimensiones para
compatibilidad con LanceDB. Batch de 100 textos por request.

## Tiempo esperado

~9,500 embeddings totales / 100 por batch = ~95 requests. A ~1-2s por
batch ~ 2-3 minutos. Requiere `GOOGLE_API_KEY` en `.env`.
"""
)

code(
    """import sys
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import re
import pandas as pd
from src.rag.indexes import build_index, list_tables, count
"""
)

md("## Indice 1: lexico (Diccionario Inga)")

code(
    """diccionario = pd.read_json(ROOT / "datos" / "diccionario_inga.jsonl", lines=True)
print(f"Entradas en diccionario: {len(diccionario):,}")
print("Ejemplos:")
print(diccionario.head(3).to_string(index=False))
"""
)

code(
    r'''registros_lexico = []
for _, row in diccionario.iterrows():
    lema = row["lema"]
    cat = row.get("cat", "")
    glosa = row.get("glosa", "")
    # Texto indexable: combina lema + categoria + glosa para captar ambas semanticas
    text = f"{lema} ({cat}): {glosa}".strip()
    registros_lexico.append({
        "text": text,
        "lema": lema,
        "cat": cat,
        "glosa": glosa,
    })

n = build_index("lexico", registros_lexico, text_field="text")
print(f"Indice lexico creado: {n:,} entradas")
'''
)

md(
    """## Indice 2: gramatical (Levinsohn + Rosetta)

Segmenta el OCR de la Gramatica Pedagogica y el apendice Rosetta
morfosintactico en chunks tematicos. Estrategia simple: dividir por
parrafos (doble salto de linea) y mantener solo los chunks con >= 30
palabras (descarta lineas residuales como page numbers).
"""
)

code(
    r'''def chunk_doc(path: Path, fuente: str, min_palabras: int = 30) -> list[dict]:
    """Chunkea un documento markdown por parrafos largos."""
    text = path.read_text(encoding="utf-8")
    # Eliminar markdown ruido
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    parrafos = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for i, p in enumerate(parrafos):
        clean = re.sub(r"\s+", " ", p).strip()
        if len(clean.split()) >= min_palabras:
            chunks.append({"text": clean, "fuente": fuente, "chunk_id": i})
    return chunks


gramatica_chunks = chunk_doc(
    ROOT / "datos" / "ocr" / "inga-kichwa" / "gramatica-pedagogica-levinsohn.md",
    "Levinsohn-Gramatica-Pedagogica",
)
rosetta_chunks = chunk_doc(
    ROOT / "datos" / "ocr" / "inga-kichwa" / "rosetta-morfosintactico.md",
    "Rosetta-Morfosintactico",
)
registros_gramatical = gramatica_chunks + rosetta_chunks
print(f"Chunks Levinsohn: {len(gramatica_chunks):,}")
print(f"Chunks Rosetta: {len(rosetta_chunks):,}")
print(f"Total gramatical: {len(registros_gramatical):,}")

if registros_gramatical:
    n = build_index("gramatical", registros_gramatical, text_field="text")
    print(f"Indice gramatical creado: {n:,} entradas")
else:
    print("WARNING: sin chunks gramaticales para indexar")
'''
)

md(
    """## Indice 3 (a): ejemplos (indexado por texto Inga)

Para traduccion Inga -> espanol, los ejemplos paralelos se indexan por la
oracion Inga (input). Cuando se recupera, se devuelve tambien el texto
espanol para usar como few-shot en el prompt del LLM.
"""
)

code(
    """train = pd.read_json(ROOT / "datos" / "splits" / "train.jsonl", lines=True)
registros_ejemplos_inga = []
for _, row in train.iterrows():
    registros_ejemplos_inga.append({
        "text": row["texto_inga"],
        "texto_inga": row["texto_inga"],
        "texto_es": row["texto_es"],
        "libro": row["libro"],
        "capitulo": int(row["capitulo"]),
        "versiculo": int(row["versiculo"]),
    })
print(f"Pares en train: {len(registros_ejemplos_inga):,}")

n = build_index("ejemplos", registros_ejemplos_inga, text_field="text")
print(f"Indice ejemplos (Inga) creado: {n:,} entradas")
"""
)

md(
    """## Indice 3 (b): ejemplos_es (indexado por texto espanol, para es2inga)

Para soportar la direccion Espanol -> Inga del Notebook 11, se construye un
segundo indice paralelo con el mismo contenido pero indexado por la
oracion espanola (la query). Asi un Spanish-input recupera los pares
paralelos mas similares semanticamente.
"""
)

code(
    """registros_ejemplos_es = []
for _, row in train.iterrows():
    registros_ejemplos_es.append({
        "text": row["texto_es"],
        "texto_inga": row["texto_inga"],
        "texto_es": row["texto_es"],
        "libro": row["libro"],
        "capitulo": int(row["capitulo"]),
        "versiculo": int(row["versiculo"]),
    })
n = build_index("ejemplos_es", registros_ejemplos_es, text_field="text")
print(f"Indice ejemplos_es (espanol) creado: {n:,} entradas")
"""
)

md(
    """## Validacion: queries de prueba

Ejecuta tres queries en Inga distintas, una orientada al indice lexico
(palabra suelta), otra al gramatical (concepto morfologico), otra a
ejemplos (frase larga). Inspeccion cualitativa de los top-3 de cada indice.
"""
)

code(
    """from src.rag.retriever import retrieve

queries = [
    ("wasi", "palabra inga 'casa'"),
    ("imasa parlangapa", "frase comun 'como decir'"),
    ("Taita Diuska runakunata kuianmi", "oracion biblica completa"),
]

for q, descripcion in queries:
    print(f"\\n=== Query: '{q}' ({descripcion}) ===")
    ctx = retrieve(q, top_k_per_index=3)
    print(f"  Lexico top-3:")
    for r in ctx.lexico:
        print(f"    - {r.get('lema', '?')} ({r.get('cat', '?')}): {r.get('glosa', '?')[:80]}")
    print(f"  Gramatical top-3:")
    for r in ctx.gramatical:
        print(f"    - ({r.get('fuente', '?')}) {r.get('text', '?')[:120]}")
    print(f"  Ejemplos top-3:")
    for r in ctx.ejemplos:
        print(f"    - {r.get('libro', '?')} {r.get('capitulo', 0)}:{r.get('versiculo', 0)}")
        print(f"      INGA: {r.get('texto_inga', '?')[:100]}")
        print(f"      ES:   {r.get('texto_es', '?')[:100]}")
"""
)

md("## Resumen final de indices")

code(
    """print("=" * 60)
print("INDICES RAG - Entrega 2")
print("=" * 60)
for table in list_tables():
    print(f"  {table:<14} {count(table):>6,} entradas")
print("=" * 60)
"""
)

nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
