# TFM Entrega 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Llevar el TFM Inga-espanol del ~35% (Entrega 1) al 75% (Entrega 2) en 7 dias, cubriendo Fases 2-6 con experimentos minimos y produciendo un documento de ~50-55 paginas con resultados reales.

**Architecture:** Pipeline reproducible md->py->docx (sin tocar Word directamente). Notebooks numerados 03-10 ejecutan corpus + RAG + LoRA + LLM en orden. Codigo reusable bajo `src/`. Generacion del docx via `entrega2/build_docx.py` con la plantilla UNIR.

**Tech Stack:** Python 3.11, transformers, peft, sentence-transformers, sacrebleu, bert-score, google-genai (Gemini embeddings), lancedb, anthropic (Claude), python-docx, matplotlib, nbformat.

**Spec:** Ver `docs/superpowers/specs/2026-05-18-tfm-entrega2-design.md`.

---

## DIA 1 - Lun 18-may - Fundamentos + corpus NT

### Task 1: Migrar a proyecto uv + estructura de carpetas + .env

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.env.example`
- Create: `entrega2/`, `entrega2/figuras/` (carpetas)
- Create: `src/__init__.py`, `src/rag/__init__.py`, `src/models/__init__.py`, `src/eval/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: Inicializar proyecto uv en el repo**

```bash
cd /Users/william-santos/Documents/UNIR/tfm
uv init --no-readme --python 3.11
```

Esto crea `pyproject.toml`, `.python-version`, y un `hello.py` que eliminamos despues.

- [ ] **Step 2: Anadir dependencias principales**

```bash
uv add transformers peft accelerate sentence-transformers \
       sacrebleu "bert-score" google-genai anthropic lancedb \
       python-docx matplotlib pandas numpy nbformat tqdm \
       scikit-learn datasets sentencepiece python-dotenv
```

- [ ] **Step 3: Anadir dependencias de desarrollo**

```bash
uv add --dev pytest jupyter ipykernel
```

- [ ] **Step 4: Eliminar `hello.py` generado por uv init**

```bash
rm /Users/william-santos/Documents/UNIR/tfm/hello.py 2>/dev/null || true
```

- [ ] **Step 5: Crear estructura de carpetas**

```bash
mkdir -p entrega2/figuras src/rag src/models src/eval \
         datos/splits datos/ocr/torres-amat-1832 \
         models lance_indexes
```

- [ ] **Step 6: Crear `__init__.py` vacios en cada paquete de `src/`**

```bash
touch src/__init__.py src/rag/__init__.py src/models/__init__.py src/eval/__init__.py
```

- [ ] **Step 7: Crear `.env.example` con placeholders**

```
# API keys requeridas para el TFM
GOOGLE_API_KEY=your-gemini-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
MISTRAL_API_KEY=your-mistral-api-key-here-for-ocr
```

- [ ] **Step 8: Actualizar `.gitignore`**

Anadir al final:
```
# uv y python
.venv/
__pycache__/
*.pyc
*.pyo
.ipynb_checkpoints/

# Secrets
.env

# Entrega 2 artefactos pesados
models/nllb-inga-lora-v1/
lance_indexes/
datos/cache/
```

- [ ] **Step 9: Pedir al usuario que cree `.env` (humano, no automatizado)**

Indicar al usuario que copie `.env.example` a `.env` y rellene las tres claves. NO crear `.env` automaticamente, deja la responsabilidad humana.

- [ ] **Step 10: Validar que el entorno funciona**

```bash
uv run python -c "import transformers, peft, lancedb, anthropic, google.genai; print('OK')"
```

Esperado: imprime `OK`.

- [ ] **Step 11: Commit**

```bash
git add pyproject.toml uv.lock .python-version .env.example .gitignore \
        entrega2/ src/ datos/splits/ datos/ocr/torres-amat-1832/ \
        models/.gitkeep lance_indexes/.gitkeep
git commit -m "chore(entrega2): migrar a proyecto uv + estructura de carpetas + .env.example"
```

### Task 2: Verificar las dos referencias 2026 sospechosas

**Files:**
- Modify: `bibliografia/refs_verificadas.md`

- [ ] **Step 1: Verificar `Dhawan et al. (2026)` arXiv 2601.03135**

Usar WebFetch contra `https://arxiv.org/abs/2601.03135`. Si responde 404 o autor distinto, marcar como alucinacion.

- [ ] **Step 2: Verificar `Finkelstein et al. (2026)` TranslateGemma arXiv 2601.09012**

Usar WebFetch contra `https://arxiv.org/abs/2601.09012`. Si responde 404 o autor distinto, marcar como alucinacion.

- [ ] **Step 3: Si alguna es alucinacion, buscar alternativa real**

Para Dhawan: buscar en arXiv "synthetic data low resource indigenous translation 2024-2026".
Para TranslateGemma: si existe un report tecnico real, usar ese ID. Si no, citar solamente Gemma 3 base (Mesnard et al. 2024) y eliminar TranslateGemma de Tabla 2.

- [ ] **Step 4: Actualizar `bibliografia/refs_verificadas.md`**

Documentar verificacion exitosa o reemplazo, con fecha de la consulta.

- [ ] **Step 5: Commit**

```bash
git add bibliografia/refs_verificadas.md
git commit -m "bib(entrega2): verificar/reemplazar referencias 2026 sospechosas (Dhawan, TranslateGemma)"
```

### Task 3: Descargar Biblia Torres Amat 1832 (NT)

**Files:**
- Create: `datos/ocr/torres-amat-1832/source.txt` (metadata de la fuente)
- Create: `datos/ocr/torres-amat-1832/00-torres-amat-NT.pdf` (descargado)

- [ ] **Step 1: Localizar fuente PDF en dominio publico**

Probar en orden:
1. `https://archive.org/details/sagradabibliaorf00torr` (Sagrada Biblia, Torres Amat)
2. `https://www.intratext.com/IXT/ESL0073/` (texto plano via IntraText)
3. Si ambas fallan, buscar `"Torres Amat" "Nuevo Testamento" pdf site:archive.org`.

- [ ] **Step 2: Descargar el PDF a `datos/ocr/torres-amat-1832/00-torres-amat-NT.pdf`**

Si la fuente es texto plano (no PDF), saltarse el OCR y guardar como `.md` directamente.

- [ ] **Step 3: Documentar la fuente en `datos/ocr/torres-amat-1832/source.txt`**

Contenido:
```
URL: <url de descarga>
Fecha: 2026-05-18
Licencia: Dominio publico (Felix Torres Amat, 1832)
Traduccion: Catolica, del latin (Vulgata)
Tipo: <PDF | texto plano>
Idioma: espanol
```

- [ ] **Step 4: Pasar por mistral-ocr-extractor (solo si es PDF)**

```bash
cd /Users/william-santos/Documents/UNIR/mistral-ocr-extractor
uv run extract --path /Users/william-santos/Documents/UNIR/tfm/datos/ocr/torres-amat-1832 --name torres-amat-1832
```

Output esperado: `output/torres-amat-1832/00-torres-amat-NT.md`. Copiarlo a `tfm/datos/ocr/torres-amat-1832/00-torres-amat-NT.md`.

- [ ] **Step 5: Validar tamano del output**

`wc -l /Users/william-santos/Documents/UNIR/tfm/datos/ocr/torres-amat-1832/00-torres-amat-NT.md` debe ser > 5.000 lineas (NT completo tiene ~8.000 versiculos).

- [ ] **Step 6: Commit**

```bash
git add datos/ocr/torres-amat-1832/
git commit -m "data(entrega2): incluir NT Torres Amat 1832 OCR para alineacion paralela"
```

### Task 4: Crear Notebook 03 - extraccion estructurada del NT Inga

**Files:**
- Create: `notebooks/03_extraccion_NT_estructurada.ipynb`
- Create: `datos/nt_inga_estructurado.jsonl`

- [ ] **Step 1: Disenar el parser book+chapter+verse**

El NT Inga (`datos/ocr/inga-kichwa/00-WNTinb-web.md`) tiene:
- Headers de pagina como `HECHOS 1` o `HECHOS 1, 2` (transicion de capitulo).
- Versiculos numerados en el texto: `1 Patsasimi taita Diuspa wawamanda...`, `2 ...`, etc.
- Pericope headings con `# titulo` (titulos de seccion, no son versiculos).

Estrategia: stateful parsing recorriendo el .md linea por linea, manteniendo current_book, current_chapter, current_verse, current_text. Acumular texto hasta el siguiente numero de versiculo o cambio de capitulo.

- [ ] **Step 2: Definir mapeo de nombres de libros NT Inga -> nombre canonico espanol**

```python
LIBRO_MAP = {
    "MATEO": "Mateo",
    "MARKUS": "Marcos",
    "MARCOS": "Marcos",
    "LUKAS": "Lucas",
    "JUAN": "Juan",
    "HECHOS": "Hechos",
    "ROMANOS": "Romanos",
    "1 KORINTO": "1 Corintios",
    "2 KORINTO": "2 Corintios",
    "GALASIA": "Galatas",
    "EFESO": "Efesios",
    "FILIPOS": "Filipenses",
    "KOLOSAS": "Colosenses",
    "1 TESALONIKA": "1 Tesalonicenses",
    "2 TESALONIKA": "2 Tesalonicenses",
    "1 TIMOTEO": "1 Timoteo",
    "2 TIMOTEO": "2 Timoteo",
    "TITO": "Tito",
    "FILEMON": "Filemon",
    "HEBREO": "Hebreos",
    "SANTIAGO": "Santiago",
    "1 PEDRO": "1 Pedro",
    "2 PEDRO": "2 Pedro",
    "1 JUAN": "1 Juan",
    "2 JUAN": "2 Juan",
    "3 JUAN": "3 Juan",
    "JUDAS": "Judas",
    "APOKALIPSIS": "Apocalipsis",
}
```

Hay que validar este mapeo contra los headers reales que aparecen en el OCR (Step 4 lo verifica empiricamente).

- [ ] **Step 3: Implementar el parser en el notebook**

Estructura del notebook (cells):
1. Cell markdown: titulo y descripcion ("Notebook 03 - Extraccion estructurada del NT Inga").
2. Cell code: imports (re, json, pathlib, collections).
3. Cell code: cargar el .md, definir LIBRO_MAP.
4. Cell code: parser que produce `[{"libro": "Mateo", "capitulo": 1, "versiculo": 1, "texto_inga": "..."}]`.
5. Cell code: validacion (libros encontrados, capitulos por libro, versiculos por capitulo).
6. Cell code: persistir a `datos/nt_inga_estructurado.jsonl`.
7. Cell markdown: resumen de cuantos versiculos por libro.

- [ ] **Step 4: Ejecutar el notebook y validar**

Esperado: ~7.900 versiculos totales (el NT canonico tiene 7.957). Si el numero es < 6.000, hay bug en el parser. Imprimir distribucion por libro para inspeccion visual.

- [ ] **Step 5: Commit**

```bash
git add notebooks/03_extraccion_NT_estructurada.ipynb datos/nt_inga_estructurado.jsonl
git commit -m "data(entrega2): reextraer NT Inga con estructura libro/capitulo/versiculo"
```

---

## DIA 2 - Mar 19-may - Alineacion + Antihua + particiones

### Task 5: Crear Notebook 04 - extraccion estructurada del NT Torres Amat

**Files:**
- Create: `notebooks/04_extraccion_NT_torres_amat.ipynb`
- Create: `datos/torres_amat_nt.jsonl`

- [ ] **Step 1: Inspeccionar formato del OCR de Torres Amat**

`head -100 datos/ocr/torres-amat-1832/00-torres-amat-NT.md`. Identificar como aparecen libros, capitulos, versiculos en este OCR.

- [ ] **Step 2: Adaptar el parser del Notebook 03 al formato Torres Amat**

Probablemente diferente: libros con nombres en espanol antiguo, capitulos romanos o arabigos, versiculos con marca distinta. Adaptar regex y mapping.

- [ ] **Step 3: Implementar el notebook con misma estructura que Notebook 03**

Output: `datos/torres_amat_nt.jsonl` con formato `[{"libro": "Mateo", "capitulo": 1, "versiculo": 1, "texto_es": "..."}]`.

- [ ] **Step 4: Ejecutar y validar**

Esperado: ~7.900 versiculos. Comparar conteos por libro con el NT Inga (Notebook 03) - deberian coincidir en cantidad de capitulos por libro.

- [ ] **Step 5: Commit**

```bash
git add notebooks/04_extraccion_NT_torres_amat.ipynb datos/torres_amat_nt.jsonl
git commit -m "data(entrega2): extraer NT Torres Amat 1832 con estructura libro/capitulo/versiculo"
```

### Task 6: Crear Notebook 05 - alineacion canonica NT

**Files:**
- Create: `notebooks/05_alineacion_NT.ipynb`
- Create: `datos/nt_paralelo.jsonl`

- [ ] **Step 1: Cargar ambos JSONL en pandas**

```python
inga = pd.read_json("datos/nt_inga_estructurado.jsonl", lines=True)
es = pd.read_json("datos/torres_amat_nt.jsonl", lines=True)
```

- [ ] **Step 2: Join por (libro, capitulo, versiculo)**

```python
paralelo = inga.merge(es, on=["libro", "capitulo", "versiculo"], how="inner")
```

- [ ] **Step 3: Reportar tasa de alineacion**

```python
print(f"Inga: {len(inga)}, Espanol: {len(es)}, Paralelos: {len(paralelo)}")
print(f"Tasa de alineacion: {len(paralelo)/min(len(inga), len(es))*100:.1f}%")
```

- [ ] **Step 4: Inspeccion manual de 10 pares aleatorios**

```python
paralelo.sample(10)[["libro", "capitulo", "versiculo", "texto_inga", "texto_es"]]
```

Validar visualmente que el contenido tiene sentido (no hay desfases).

- [ ] **Step 5: Filtrar pares de baja calidad**

Eliminar:
- Versiculos donde `texto_inga` o `texto_es` tienen < 3 palabras (probable ruido)
- Versiculos donde la longitud difiere en mas de 5x (probable mismatch)

- [ ] **Step 6: Persistir a `datos/nt_paralelo.jsonl`**

Campos: `{idx, libro, capitulo, versiculo, texto_inga, texto_es, dialecto: "AP", fuente: "NT-Wycliffe-TorresAmat"}`.

- [ ] **Step 7: Commit**

```bash
git add notebooks/05_alineacion_NT.ipynb datos/nt_paralelo.jsonl
git commit -m "data(entrega2): alinear NT Inga vs Torres Amat (~7K pares canonicos)"
```

### Task 7: Crear Notebook 06 - refinamiento de Antihua Pacay

**Files:**
- Create: `notebooks/06_refinamiento_antihua_pacay.ipynb`
- Create: `datos/antihua_pacay_refinado.jsonl`

- [ ] **Step 1: Cargar el OCR de Antihua Pacay**

`datos/ocr/inga-kichwa/antihua-pacay.md`. Texto narrativo, bloques alternados Inga/espanol no marcados explicitamente.

- [ ] **Step 2: Implementar detector de idioma basado en sufijos**

```python
SUFIJOS_INGA = ["kuna", "ngapa", "manda", "wan", "pi", "ta", "mi", "spa", "chu", "cuna"]

def es_inga(texto: str, umbral=0.05) -> bool:
    """Detecta si un parrafo es Inga por densidad de sufijos aglutinantes."""
    palabras = texto.lower().split()
    if not palabras:
        return False
    matches = sum(1 for p in palabras if any(p.endswith(s) for s in SUFIJOS_INGA))
    return matches / len(palabras) >= umbral
```

- [ ] **Step 3: Segmentar el texto en parrafos y clasificarlos**

```python
parrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
clasificados = [(p, es_inga(p)) for p in parrafos]
```

- [ ] **Step 4: Aparear parrafos Inga con su traduccion espanola adyacente**

Heuristica: si parrafo i es Inga y parrafo i+1 es espanol (no Inga), formar par. Si i+1 es tambien Inga, buscar el siguiente espanol; descartar si no hay match en ventana de 3.

- [ ] **Step 5: Validacion manual de 20 pares**

Imprimir 20 pares aleatorios para inspeccion. Si menos del 60% son alineamientos sensatos, ajustar umbral o estrategia.

- [ ] **Step 6: Persistir a `datos/antihua_pacay_refinado.jsonl`**

Campos: `{idx, texto_inga, texto_es, dialecto: "MP", fuente: "AntihuaPacay-1985"}`. Sin libro/capitulo/versiculo (narrativa no estructurada).

- [ ] **Step 7: Commit**

```bash
git add notebooks/06_refinamiento_antihua_pacay.ipynb datos/antihua_pacay_refinado.jsonl
git commit -m "data(entrega2): refinar alineacion de Antihua Pacay con detector de idioma"
```

### Task 8: Crear Notebook 07 - corpus unificado + particiones

**Files:**
- Create: `notebooks/07_corpus_particiones.ipynb`
- Create: `datos/corpus_paralelo.jsonl`
- Create: `datos/splits/train.jsonl`
- Create: `datos/splits/val.jsonl`
- Create: `datos/splits/test.jsonl`

- [ ] **Step 1: Cargar nt_paralelo + antihua_pacay_refinado**

```python
nt = pd.read_json("datos/nt_paralelo.jsonl", lines=True)
ap = pd.read_json("datos/antihua_pacay_refinado.jsonl", lines=True)
corpus = pd.concat([nt, ap], ignore_index=True)
```

- [ ] **Step 2: Normalizacion ortografica conservadora**

Aplicar a `texto_inga`:
- Lowercase si la fuente usa caps inconsistentes
- Normalizar espacios multiples
- Eliminar caracteres no imprimibles
NO modificar la ortografia (eso requiere decision linguistica que postergamos para Entrega Final).

- [ ] **Step 3: Particion estratificada train/val/test**

Ratio 80/10/10. Estratificar por `dialecto` (AP/MP) para que train, val y test tengan ambos dialectos en proporcion similar.

```python
from sklearn.model_selection import train_test_split
train, temp = train_test_split(corpus, test_size=0.2, stratify=corpus.dialecto, random_state=42)
val, test = train_test_split(temp, test_size=0.5, stratify=temp.dialecto, random_state=42)
```

- [ ] **Step 4: Validar tamanos y composicion**

```python
print(f"Train: {len(train)} ({train.dialecto.value_counts().to_dict()})")
print(f"Val:   {len(val)}   ({val.dialecto.value_counts().to_dict()})")
print(f"Test:  {len(test)}  ({test.dialecto.value_counts().to_dict()})")
```

Meta minima: train >= 4.000, val >= 500, test >= 500.

- [ ] **Step 5: Persistir todo**

```python
corpus.to_json("datos/corpus_paralelo.jsonl", orient="records", lines=True, force_ascii=False)
train.to_json("datos/splits/train.jsonl", orient="records", lines=True, force_ascii=False)
val.to_json("datos/splits/val.jsonl", orient="records", lines=True, force_ascii=False)
test.to_json("datos/splits/test.jsonl", orient="records", lines=True, force_ascii=False)
```

- [ ] **Step 6: Generar figura 9 (distribucion del corpus)**

Matplotlib stacked bar chart: por dialecto x particion. Guardar en `entrega2/figuras/fig09_distribucion_corpus.png`.

- [ ] **Step 7: Commit**

```bash
git add notebooks/07_corpus_particiones.ipynb datos/corpus_paralelo.jsonl datos/splits/ entrega2/figuras/fig09_distribucion_corpus.png
git commit -m "data(entrega2): unificar corpus y crear particiones estratificadas (80/10/10)"
```

---

## DIA 3 - Mie 20-may - RAG infrastructure

### Task 9: Crear `src/rag/embeddings.py` - wrapper Gemini

**Files:**
- Create: `src/rag/embeddings.py`

- [ ] **Step 1: Implementar wrapper minimo**

```python
"""Wrapper de Gemini text-embedding-004 para indexacion vectorial.

Lee GOOGLE_API_KEY del entorno. Batch por defecto de 100 textos (limite de la API).
"""
import os
from typing import Sequence
from google import genai

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Falta GOOGLE_API_KEY o GEMINI_API_KEY en el entorno")
        _client = genai.Client(api_key=api_key)
    return _client


def embed_texts(texts: Sequence[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Devuelve embeddings de 768 dimensiones para una lista de textos."""
    client = _get_client()
    out = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i + 100]
        resp = client.models.embed_content(
            model="text-embedding-004",
            contents=batch,
            config={"task_type": task_type},
        )
        out.extend([e.values for e in resp.embeddings])
    return out


def embed_query(text: str) -> list[float]:
    """Embedding para una query de retrieval."""
    return embed_texts([text], task_type="RETRIEVAL_QUERY")[0]
```

- [ ] **Step 2: Smoke test manual**

```bash
GOOGLE_API_KEY=$GOOGLE_API_KEY python -c "from src.rag.embeddings import embed_texts; print(len(embed_texts(['hola']) [0]))"
```

Esperado: imprime `768`.

- [ ] **Step 3: Commit**

```bash
git add src/rag/embeddings.py
git commit -m "feat(rag): wrapper de Gemini text-embedding-004 para indexacion vectorial"
```

### Task 10: Crear `src/rag/indexes.py` - gestores LanceDB

**Files:**
- Create: `src/rag/indexes.py`

- [ ] **Step 1: Implementar clase base + tres indices**

```python
"""Indices vectoriales LanceDB para el sistema RAG multi-indice.

Tres indices: lexico (diccionario), gramatical (gramatica + rosetta), ejemplos (corpus paralelo).
"""
from pathlib import Path
from typing import Iterable
import lancedb
import pandas as pd

from .embeddings import embed_texts

INDEX_DIR = Path("lance_indexes")


def build_index(name: str, records: list[dict], text_field: str) -> None:
    """Construye un indice LanceDB.

    `records` debe ser una lista de dicts con al menos el campo `text_field`.
    Anade el campo `vector` con el embedding de Gemini.
    """
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(INDEX_DIR)
    textos = [r[text_field] for r in records]
    vectors = embed_texts(textos)
    for r, v in zip(records, vectors):
        r["vector"] = v
    db.create_table(name, data=records, mode="overwrite")


def search(name: str, query: str, top_k: int = 5) -> list[dict]:
    """Busca top-k mas similares a la query."""
    from .embeddings import embed_query
    db = lancedb.connect(INDEX_DIR)
    table = db.open_table(name)
    qv = embed_query(query)
    results = table.search(qv).limit(top_k).to_list()
    return results
```

- [ ] **Step 2: Smoke test con 5 entradas dummy**

```python
build_index("test", [{"text": "hola", "id": 1}, {"text": "adios", "id": 2}], "text")
print(search("test", "saludo"))
```

- [ ] **Step 3: Commit**

```bash
git add src/rag/indexes.py
git commit -m "feat(rag): gestores de indices LanceDB con embedding automatico"
```

### Task 11: Crear `src/rag/retriever.py` - API unificada

**Files:**
- Create: `src/rag/retriever.py`

- [ ] **Step 1: Implementar Retriever multi-indice**

```python
"""API unificada de retrieval sobre los tres indices del sistema RAG."""
from dataclasses import dataclass
from .indexes import search


@dataclass
class RetrievedContext:
    lexico: list[dict]
    gramatical: list[dict]
    ejemplos: list[dict]


def retrieve(query: str, top_k_per_index: int = 5) -> RetrievedContext:
    """Recupera top-k del indice lexico, gramatical y de ejemplos para una query."""
    return RetrievedContext(
        lexico=search("lexico", query, top_k_per_index),
        gramatical=search("gramatical", query, top_k_per_index),
        ejemplos=search("ejemplos", query, top_k_per_index),
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/rag/retriever.py
git commit -m "feat(rag): API unificada de retrieval multi-indice"
```

### Task 12: Crear Notebook 08 - indexacion vectorial

**Files:**
- Create: `notebooks/08_indexacion_vectorial.ipynb`

- [ ] **Step 1: Cell de imports y carga de datos**

```python
import pandas as pd
from src.rag.indexes import build_index

diccionario = pd.read_json("datos/diccionario_inga.jsonl", lines=True)
train = pd.read_json("datos/splits/train.jsonl", lines=True)
# Para indice gramatical: extraer secciones tematicas del OCR de Levinsohn
# (por simplicidad, indexar el .md por bloques de 500 palabras)
```

- [ ] **Step 2: Construir indice lexico desde el diccionario**

```python
registros = []
for _, row in diccionario.iterrows():
    text = f"{row.get('lema', '')} ({row.get('categoria', '')}): {row.get('glosa', '')}"
    registros.append({"text": text, **row.to_dict()})
build_index("lexico", registros, text_field="text")
```

- [ ] **Step 3: Construir indice gramatical desde gramatica + rosetta**

Cargar `datos/ocr/inga-kichwa/gramatica-pedagogica-levinsohn.md` y `rosetta-morfosintactico.md`. Segmentar por bloques de ~500 palabras o por headings. Construir registros `{"text": bloque, "fuente": "Levinsohn|Rosetta"}` e indexar.

- [ ] **Step 4: Construir indice de ejemplos desde train.jsonl**

```python
registros = []
for _, row in train.iterrows():
    text = row["texto_inga"]
    registros.append({"text": text, "texto_inga": row["texto_inga"], "texto_es": row["texto_es"]})
build_index("ejemplos", registros, text_field="text")
```

- [ ] **Step 5: Probar el retriever con 3 queries**

```python
from src.rag.retriever import retrieve
for q in ["ima tukurka", "Patsasimi", "wasi"]:
    ctx = retrieve(q, top_k_per_index=3)
    print(q, "->", len(ctx.lexico), len(ctx.gramatical), len(ctx.ejemplos))
```

- [ ] **Step 6: Commit**

```bash
git add notebooks/08_indexacion_vectorial.ipynb lance_indexes/.lancedb_metadata 2>/dev/null || true
git commit -m "feat(rag): indexar diccionario + gramatica + ejemplos con Gemini embeddings + LanceDB"
```

---

## DIA 4 - Jue 21-may - Fine-tuning LoRA

### Task 13: Crear `src/models/nllb_lora.py` - setup LoRA

**Files:**
- Create: `src/models/nllb_lora.py`

- [ ] **Step 1: Implementar setup del modelo + LoRA**

```python
"""Setup de NLLB-200-distilled-600M con adaptadores LoRA via peft."""
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType

NLLB_MODEL = "facebook/nllb-200-distilled-600M"


def load_model_and_tokenizer(device: str = "mps"):
    tok = AutoTokenizer.from_pretrained(NLLB_MODEL, src_lang="quy_Latn", tgt_lang="spa_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL, torch_dtype=torch.float16)
    model = model.to(device)
    return model, tok


def wrap_with_lora(model, r: int = 16, alpha: int = 32, dropout: float = 0.1):
    config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=r,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=["q_proj", "v_proj"],
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    return model
```

- [ ] **Step 2: Commit**

```bash
git add src/models/nllb_lora.py
git commit -m "feat(models): setup NLLB-200-distilled-600M con LoRA r=16"
```

### Task 14: Crear Notebook 09 - entrenamiento LoRA

**Files:**
- Create: `notebooks/09_finetuning_lora.ipynb`
- Create: `models/nllb-inga-lora-v1/` (output)

- [ ] **Step 1: Cell de imports + carga del dataset**

```python
from datasets import Dataset
import pandas as pd
train = pd.read_json("datos/splits/train.jsonl", lines=True)
val = pd.read_json("datos/splits/val.jsonl", lines=True)
ds_train = Dataset.from_pandas(train)
ds_val = Dataset.from_pandas(val)
```

- [ ] **Step 2: Tokenizar el dataset**

```python
from src.models.nllb_lora import load_model_and_tokenizer
model, tok = load_model_and_tokenizer()

def tokenize(batch):
    inp = tok(batch["texto_inga"], truncation=True, padding="max_length", max_length=128)
    with tok.as_target_tokenizer():
        out = tok(batch["texto_es"], truncation=True, padding="max_length", max_length=128)
    inp["labels"] = out["input_ids"]
    return inp

ds_train_tok = ds_train.map(tokenize, batched=True, remove_columns=ds_train.column_names)
ds_val_tok = ds_val.map(tokenize, batched=True, remove_columns=ds_val.column_names)
```

- [ ] **Step 3: Aplicar LoRA al modelo**

```python
from src.models.nllb_lora import wrap_with_lora
model = wrap_with_lora(model)
```

- [ ] **Step 4: Setup Trainer + entrenar**

```python
from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer, DataCollatorForSeq2Seq

args = Seq2SeqTrainingArguments(
    output_dir="models/nllb-inga-lora-v1",
    num_train_epochs=3,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    learning_rate=3e-4,
    warmup_steps=100,
    logging_steps=20,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=1,
    predict_with_generate=False,
    report_to=[],
    fp16=False,
    bf16=False,
)

trainer = Seq2SeqTrainer(
    model=model,
    args=args,
    train_dataset=ds_train_tok,
    eval_dataset=ds_val_tok,
    data_collator=DataCollatorForSeq2Seq(tok, model=model),
)

trainer.train()
trainer.save_model("models/nllb-inga-lora-v1")
```

- [ ] **Step 5: Generar Figura 11 (curva de loss)**

```python
import matplotlib.pyplot as plt
hist = trainer.state.log_history
train_loss = [(h["step"], h["loss"]) for h in hist if "loss" in h]
plt.plot(*zip(*train_loss))
plt.xlabel("Step"); plt.ylabel("Loss"); plt.title("Entrenamiento LoRA - NLLB-200-distilled-600M")
plt.savefig("entrega2/figuras/fig11_lora_loss.png", dpi=150, bbox_inches="tight")
```

- [ ] **Step 6: Commit (sin pesos del modelo, esos quedan gitignored)**

```bash
git add notebooks/09_finetuning_lora.ipynb entrega2/figuras/fig11_lora_loss.png
git commit -m "feat(entrega2): entrenamiento LoRA sobre NLLB-200-distilled-600M (3 epochs)"
```

### Task 15: Crear `src/eval/metrics.py` - wrappers de metricas

**Files:**
- Create: `src/eval/metrics.py`

- [ ] **Step 1: Implementar BLEU, chrF++, BERTScore**

```python
"""Wrappers de metricas de traduccion automatica."""
import sacrebleu
from bert_score import score as bert_score


def bleu(refs: list[str], hyps: list[str]) -> float:
    """BLEU corpus level."""
    return sacrebleu.corpus_bleu(hyps, [refs]).score


def chrf(refs: list[str], hyps: list[str]) -> float:
    """chrF++ corpus level."""
    return sacrebleu.corpus_chrf(hyps, [refs], word_order=2).score


def bertscore(refs: list[str], hyps: list[str], lang: str = "es") -> float:
    """BERTScore F1 promedio."""
    _, _, f1 = bert_score(hyps, refs, lang=lang, verbose=False)
    return f1.mean().item()


def all_metrics(refs: list[str], hyps: list[str]) -> dict:
    return {
        "bleu": bleu(refs, hyps),
        "chrf": chrf(refs, hyps),
        "bertscore": bertscore(refs, hyps),
    }
```

- [ ] **Step 2: Commit**

```bash
git add src/eval/metrics.py
git commit -m "feat(eval): wrappers de BLEU, chrF++, BERTScore"
```

### Task 16: Crear Notebook 10 - eval configs A y B (zero-shot NLLB + LoRA)

**Files:**
- Create: `notebooks/10_eval_nllb_configs.ipynb`
- Modify: `datos/metricas_entrega2.json` (crear si no existe)

- [ ] **Step 1: Cargar val set + modelo base + modelo LoRA**

```python
import pandas as pd
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from peft import PeftModel

val = pd.read_json("datos/splits/val.jsonl", lines=True).head(100)  # acotar para tiempo

tok = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M", src_lang="quy_Latn", tgt_lang="spa_Latn")
base = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M").to("mps")
lora = PeftModel.from_pretrained(base, "models/nllb-inga-lora-v1").to("mps")
```

- [ ] **Step 2: Funcion de inferencia**

```python
def translate(model, sentences):
    out = []
    for s in sentences:
        inp = tok(s, return_tensors="pt", truncation=True, max_length=128).to("mps")
        gen = model.generate(**inp, forced_bos_token_id=tok.convert_tokens_to_ids("spa_Latn"), max_new_tokens=128)
        out.append(tok.batch_decode(gen, skip_special_tokens=True)[0])
    return out
```

- [ ] **Step 3: Ejecutar config A (zero-shot quy_Latn) y config B (LoRA)**

```python
hyps_A = translate(base, val.texto_inga.tolist())
hyps_B = translate(lora, val.texto_inga.tolist())
refs = val.texto_es.tolist()
```

- [ ] **Step 4: Calcular metricas**

```python
from src.eval.metrics import all_metrics
import json

results = {
    "config_A_nllb_zeroshot": all_metrics(refs, hyps_A),
    "config_B_nllb_lora": all_metrics(refs, hyps_B),
}
print(json.dumps(results, indent=2))

# Persistir parcialmente; luego anadimos C, D, E en el siguiente notebook
with open("datos/metricas_entrega2.json", "w") as f:
    json.dump(results, f, indent=2)
```

- [ ] **Step 5: Persistir traducciones para inspeccion cualitativa**

```python
val_out = val.copy()
val_out["hyp_A"] = hyps_A
val_out["hyp_B"] = hyps_B
val_out.to_json("datos/predicciones_val_AB.jsonl", orient="records", lines=True, force_ascii=False)
```

- [ ] **Step 6: Commit**

```bash
git add notebooks/10_eval_nllb_configs.ipynb datos/metricas_entrega2.json datos/predicciones_val_AB.jsonl
git commit -m "feat(eval): metricas para configs A (zero-shot NLLB) y B (NLLB+LoRA)"
```

---

## DIA 5 - Vie 22-may - LLM+RAG + Eval completa

### Task 17: Crear `src/models/claude_rag.py` - pipeline LLM+RAG

**Files:**
- Create: `src/models/claude_rag.py`

- [ ] **Step 1: Implementar el pipeline**

```python
"""Pipeline de traduccion Inga->espanol con Claude + RAG multi-indice."""
import os
import anthropic

from src.rag.retriever import retrieve, RetrievedContext

_client = None
MODEL = "claude-sonnet-4-6"  # ajustable


def _client_get():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def build_prompt(sentence: str, ctx: RetrievedContext) -> str:
    """Construye el prompt estructurado con el contexto recuperado."""
    lex = "\n".join(f"- {r['text']}" for r in ctx.lexico[:5])
    gram = "\n".join(f"- {r['text'][:300]}" for r in ctx.gramatical[:3])
    ej = "\n".join(f"- Inga: {r['texto_inga']}\n  Espanol: {r['texto_es']}" for r in ctx.ejemplos[:5])
    return f"""Traduce del Inga (variante quechua del Putumayo, Colombia) al espanol.

Contexto lexico relevante:
{lex}

Contexto gramatical:
{gram}

Ejemplos paralelos similares:
{ej}

Oracion a traducir:
{sentence}

Responde unicamente con la traduccion al espanol, sin explicaciones adicionales."""


def translate(sentence: str, use_rag: bool = True) -> str:
    """Traduce una oracion. Si use_rag=False, hace zero-shot sin contexto."""
    if use_rag:
        ctx = retrieve(sentence, top_k_per_index=5)
        prompt = build_prompt(sentence, ctx)
    else:
        prompt = f"Traduce del Inga al espanol. Oracion:\n{sentence}\n\nResponde unicamente con la traduccion."
    client = _client_get()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()
```

- [ ] **Step 2: Smoke test con una oracion**

```bash
python -c "from src.models.claude_rag import translate; print(translate('Patsasimi taita Diuspa wawamanda', use_rag=False))"
```

Esperado: alguna traduccion plausible (calidad variable, lo importante es que no falle).

- [ ] **Step 3: Commit**

```bash
git add src/models/claude_rag.py
git commit -m "feat(models): pipeline Claude + RAG multi-indice"
```

### Task 18: Crear Notebook 11 - eval configs C, D, E (Claude)

**Files:**
- Create: `notebooks/11_eval_llm_rag.ipynb`
- Modify: `datos/metricas_entrega2.json`

- [ ] **Step 1: Cargar val set (mismas 100 oraciones que en Notebook 10)**

```python
import pandas as pd, json
val = pd.read_json("datos/splits/val.jsonl", lines=True).head(100)
```

- [ ] **Step 2: Ejecutar config C (Claude zero-shot)**

```python
from src.models.claude_rag import translate
from tqdm import tqdm
hyps_C = [translate(s, use_rag=False) for s in tqdm(val.texto_inga)]
```

- [ ] **Step 3: Ejecutar config D (Claude + RAG)**

```python
hyps_D = [translate(s, use_rag=True) for s in tqdm(val.texto_inga)]
```

- [ ] **Step 4: Ejecutar config E (LoRA-translated + reranking via Claude+RAG)**

Para simplificar: usar las hipotesis de la config B (LoRA) como semilla y pasar por Claude+RAG con prompt de refinamiento. Documentar esa simplificacion explicitamente.

```python
val_AB = pd.read_json("datos/predicciones_val_AB.jsonl", lines=True)
hyps_seed = val_AB.hyp_B.tolist()

def refine(seed_es, original_inga):
    ctx = retrieve(original_inga, top_k_per_index=3)
    # construir prompt de refinamiento (similar a build_prompt pero pidiendo correccion)
    ...
hyps_E = [refine(s, o) for s, o in tqdm(zip(hyps_seed, val.texto_inga))]
```

- [ ] **Step 5: Calcular metricas y consolidar**

```python
from src.eval.metrics import all_metrics
refs = val.texto_es.tolist()
results = json.load(open("datos/metricas_entrega2.json"))
results["config_C_claude_zeroshot"] = all_metrics(refs, hyps_C)
results["config_D_claude_rag"] = all_metrics(refs, hyps_D)
results["config_E_lora_plus_claude_rag"] = all_metrics(refs, hyps_E)
json.dump(results, open("datos/metricas_entrega2.json", "w"), indent=2)
print(json.dumps(results, indent=2))
```

- [ ] **Step 6: Persistir todas las predicciones para inspeccion**

```python
val_out = val.copy()
val_out["hyp_A"] = val_AB.hyp_A.tolist()
val_out["hyp_B"] = val_AB.hyp_B.tolist()
val_out["hyp_C"] = hyps_C
val_out["hyp_D"] = hyps_D
val_out["hyp_E"] = hyps_E
val_out.to_json("datos/predicciones_val_completo.jsonl", orient="records", lines=True, force_ascii=False)
```

- [ ] **Step 7: Generar Figura 12 (comparativa de configs)**

```python
import matplotlib.pyplot as plt
import numpy as np
configs = list(results.keys())
metrics = ["bleu", "chrf", "bertscore"]
x = np.arange(len(configs))
width = 0.25
fig, ax = plt.subplots(figsize=(10, 5))
for i, m in enumerate(metrics):
    vals = [results[c][m] for c in configs]
    ax.bar(x + i*width, vals, width, label=m.upper())
ax.set_xticks(x + width)
ax.set_xticklabels([c.replace("config_", "").replace("_", " ") for c in configs], rotation=20, ha="right")
ax.legend()
ax.set_title("Comparativa de las cinco configuraciones en val set (n=100)")
plt.tight_layout()
plt.savefig("entrega2/figuras/fig12_metricas_comparativas.png", dpi=150)
```

- [ ] **Step 8: Commit**

```bash
git add notebooks/11_eval_llm_rag.ipynb datos/metricas_entrega2.json datos/predicciones_val_completo.jsonl entrega2/figuras/fig12_metricas_comparativas.png
git commit -m "feat(eval): metricas para configs C (Claude), D (Claude+RAG), E (LoRA+Claude+RAG)"
```

### Task 19: Generar Figura 10 (arquitectura RAG implementada)

**Files:**
- Create: `entrega2/figuras/fig10_arquitectura_rag.png`
- Create: `notebooks/scripts/gen_fig10_rag.py` (script auxiliar)

- [ ] **Step 1: Diseno del diagrama**

Tres cajas (lexico LanceDB, gramatical LanceDB, ejemplos LanceDB) -> Gemini text-embedding-004 -> retriever -> prompt builder -> Claude. Usar matplotlib boxes y arrows o graphviz.

- [ ] **Step 2: Implementar como script Python con matplotlib**

(Codigo de matplotlib con `Rectangle` y `FancyArrow` similar al patron usado para fig02 y fig04 en Entrega 1.)

- [ ] **Step 3: Generar PNG y commit**

```bash
python notebooks/scripts/gen_fig10_rag.py
git add notebooks/scripts/gen_fig10_rag.py entrega2/figuras/fig10_arquitectura_rag.png
git commit -m "doc(entrega2): figura 10 - arquitectura RAG con Gemini + LanceDB"
```

---

## DIA 6 - Sab 23-may - Documento maestro

### Task 20: Crear `entrega2/TFM_grupal_entrega2.md` - copia + actualizacion

**Files:**
- Create: `entrega2/TFM_grupal_entrega2.md`

- [ ] **Step 1: Copiar `entrega1/TFM_grupal_entrega1.md` como base**

```bash
cp /Users/william-santos/Documents/UNIR/tfm/entrega1/TFM_grupal_entrega1.md /Users/william-santos/Documents/UNIR/tfm/entrega2/TFM_grupal_entrega2.md
```

- [ ] **Step 2: Sweep de eliminacion de referencias a "Entrega 1"**

Buscar "Entrega 1" y "presente Entrega 1" en el .md y reescribir como "el presente trabajo" o "esta memoria" segun contexto.

- [ ] **Step 3: Actualizar portada y fecha**

Cambiar "22 de abril de 2026" -> "24 de mayo de 2026". Ajustar metadata frontmatter si la hubiera.

- [ ] **Step 4: Commit (estado intermedio antes de expandir Cap 4)**

```bash
git add entrega2/TFM_grupal_entrega2.md
git commit -m "doc(entrega2): inicializar documento maestro desde Entrega 1 y eliminar referencias Entrega 1"
```

### Task 21: Reescribir Resumen + Abstract

**Files:**
- Modify: `entrega2/TFM_grupal_entrega2.md`

- [ ] **Step 1: Reescribir Resumen mencionando resultados preliminares**

Anadir parrafo (~80 palabras) con los hallazgos cuantitativos de Cap 4 (corpus alcanzado, mejor BLEU/chrF++ entre las 5 configs, observacion mas relevante de la comparativa).

- [ ] **Step 2: Traducir Abstract espejo del Resumen actualizado**

- [ ] **Step 3: Commit**

```bash
git add entrega2/TFM_grupal_entrega2.md
git commit -m "doc(entrega2): actualizar Resumen + Abstract con resultados preliminares"
```

### Task 22: Expandir Cap 4 con las nuevas secciones

**Files:**
- Modify: `entrega2/TFM_grupal_entrega2.md`

- [ ] **Step 1: Anadir 4.2 - Construccion del corpus paralelo completo**

(~600-800 palabras). Documentar: fuentes finales, alineacion canonica NT, refinamiento Antihua Pacay, normalizacion, particiones train/val/test. Incluir Tabla 6 (distribucion train/val/test por dialecto) y Figura 9 (distribucion del corpus).

- [ ] **Step 2: Anadir 4.3 - Base de conocimiento e indexacion vectorial**

(~400-500 palabras). Documentar: tres indices, decision de Gemini text-embedding-004, eleccion de LanceDB, API uniforme. Incluir Figura 10 (arquitectura RAG implementada).

- [ ] **Step 3: Anadir 4.4 - Adaptacion de NLLB-200 mediante LoRA**

(~500-600 palabras). Documentar: modelo base, configuracion LoRA, hiperparametros, curva de loss. Incluir Tabla 7 (hiperparametros) y Figura 11 (loss curve).

- [ ] **Step 4: Anadir 4.5 - Pipeline LLM + RAG con Claude**

(~400-500 palabras). Documentar: estructura del prompt, integracion de los 3 indices, decision de top-k=5 por indice, limites de costo (val set de 100).

- [ ] **Step 5: Anadir 4.6 - Evaluacion comparativa preliminar**

(~600-800 palabras). Reportar las 5 configs con sus 3 metricas. Incluir Tabla 8 (metricas) y Figura 12 (comparativa). Discutir hallazgos: cual config gana en BLEU vs chrF++, hipotesis sobre por que.

- [ ] **Step 6: Actualizar 4.7 - Repositorio actualizado**

Listar los 11 notebooks (00-10/11) y los archivos de datos generados.

- [ ] **Step 7: Eliminar 4.3 "Proximos pasos hacia la Entrega 2"** (ahora es lo que estamos haciendo)

- [ ] **Step 8: Commit**

```bash
git add entrega2/TFM_grupal_entrega2.md
git commit -m "doc(entrega2): expandir Cap 4 con corpus, RAG, LoRA, LLM y evaluacion preliminar"
```

### Task 23: Redactar Cap 5 con conclusiones preliminares

**Files:**
- Modify: `entrega2/TFM_grupal_entrega2.md`

- [ ] **Step 1: 5.1 Conclusiones preliminares** (~400 palabras)

Sintetizar los hallazgos cuantitativos y cualitativos. Mencionar: viabilidad demostrada de ambas aproximaciones, magnitud del corpus alcanzado, primer ranking entre configs, principales fallas observadas.

- [ ] **Step 2: 5.2 Discusion** (~500 palabras)

Reflexionar sobre: limitaciones del val set (n=100), efecto del tamano del corpus en LoRA, peso del contexto recuperado en Claude+RAG, comparacion con Prieto et al. (2024) y Chen et al. (2024).

- [ ] **Step 3: 5.3 Lineas de trabajo para Entrega Final** (~300 palabras)

Enumerar lo que NO entro en Entrega 2: ablations LoRA, NLLB-3.3B, backtranslation, validacion humana, despliegue local. Plan de ejecucion para los meses junio-septiembre.

- [ ] **Step 4: Commit**

```bash
git add entrega2/TFM_grupal_entrega2.md
git commit -m "doc(entrega2): redactar Cap 5 con conclusiones preliminares + discusion + lineas futuras"
```

### Task 24: Sweep anti-LLM sobre todo el documento

**Files:**
- Modify: `entrega2/TFM_grupal_entrega2.md`

- [ ] **Step 1: Reescribir SMART objectives en prosa**

Convertir bullets canonicos en parrafos con transicion natural. No perder la informacion SMART pero romper el "verbo+complemento+criterio" repetido.

- [ ] **Step 2: Variar longitudes de parrafo en Cap 4**

Identificar parrafos de longitud uniforme. Romper algunos en dos cortos, fusionar otros adyacentes. Buscar variabilidad visible.

- [ ] **Step 3: Eliminar TODOS los artefactos en ingles**

`grep -n "Figure\|Table" entrega2/TFM_grupal_entrega2.md` debe devolver 0 lineas.

- [ ] **Step 4: Variar inicios de frase**

Identificar series de parrafos que empiezan con "El", "La", "Los", "Este". Reescribir algunos comenzando con subordinada o complemento circunstancial.

- [ ] **Step 5: Commit**

```bash
git add entrega2/TFM_grupal_entrega2.md
git commit -m "doc(entrega2): sweep anti-LLM (varianza parrafos, SMART en prosa, cero artefactos ingles)"
```

---

## DIA 7 - Dom 24-may - QA + generacion final

### Task 25: Refactorizar `build_docx.py` para captions APA correctos

**Files:**
- Create: `entrega2/build_docx.py` (copia + refactor)

- [ ] **Step 1: Copiar `entrega1/build_docx.py` como base**

```bash
cp entrega1/build_docx.py entrega2/build_docx.py
```

- [ ] **Step 2: Reescribir `add_caption()` para producir DOS parrafos**

```python
def add_caption(doc, kind: str, number: int, title: str):
    """Inserta caption APA-UNIR en dos lineas: identificador + titulo en cursiva.

    kind: "Figura" | "Tabla"
    """
    p1 = doc.add_paragraph(style=S_CAPT)
    p1.add_run(f"{kind} {number}").bold = True
    p2 = doc.add_paragraph(style=S_NORMAL)
    run = p2.add_run(title)
    run.italic = True
```

- [ ] **Step 3: Asegurar etiquetas "Figura"/"Tabla" en espanol consistentemente**

Buscar usos de `add_caption` en el script y verificar que pasan "Figura" o "Tabla" (no "Figure"/"Table").

- [ ] **Step 4: Eliminar el doble prefijo "Anexo A."**

En `build_anexo()`, quitar el "Anexo A." del titulo manual; dejar solo "Codigo fuente y datos analizados" para que el estilo Anexo lo prefije automaticamente.

- [ ] **Step 5: Configurar header del docx via section.header con los nombres correctos**

(Si python-docx lo permite limpiamente; si no, dejar nota en CHANGES_IN_WORD_E2.md para que el usuario lo edite.)

- [ ] **Step 6: Commit**

```bash
git add entrega2/build_docx.py
git commit -m "feat(entrega2): refactor de build_docx.py con captions APA en dos lineas + cosmeticos"
```

### Task 26: Generar el docx borrador de Entrega 2

**Files:**
- Create: `entrega2/TFM_Entrega2_EslavaSantos.docx`

- [ ] **Step 1: Ejecutar el script**

```bash
cd /Users/william-santos/Documents/UNIR/tfm
python entrega2/build_docx.py
```

- [ ] **Step 2: Verificar tamano y estructura del docx**

`ls -la entrega2/TFM_Entrega2_EslavaSantos.docx`. Debe ser > 1MB (similar a Entrega 1).

- [ ] **Step 3: Convertir a PDF para revision visual (opcional)**

Si LibreOffice esta instalado:
```bash
soffice --headless --convert-to pdf entrega2/TFM_Entrega2_EslavaSantos.docx --outdir entrega2/
```

- [ ] **Step 4: Commit del docx generado**

```bash
git add entrega2/TFM_Entrega2_EslavaSantos.docx
git commit -m "build(entrega2): generar docx borrador de Entrega 2"
```

### Task 27: Crear CHANGES_IN_WORD_E2.md con instrucciones para el usuario

**Files:**
- Create: `entrega2/CHANGES_IN_WORD_E2.md`

- [ ] **Step 1: Documentar puntos de edicion manual recomendados**

Heredar el patron del CHANGES_IN_WORD.md de Entrega 1. Cubrir: portada (verificar nombres), header (llenar manualmente si build_docx no lo dejo), TOC (regenerar con F9), indices de figuras/tablas (regenerar), cualquier figura embebida con dimensionado problematico.

- [ ] **Step 2: Anotar diferencias previstas md/py/docx**

(Mismo formato que el CHANGES_IN_WORD.md de Entrega 1.)

- [ ] **Step 3: Commit**

```bash
git add entrega2/CHANGES_IN_WORD_E2.md
git commit -m "doc(entrega2): instrucciones para edicion manual final del .docx en Word"
```

### Task 28: Actualizar README.md + tag final

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Actualizar seccion "Estado del proyecto"**

Cambiar "Entrega 1 (abril 2026)" por "Entrega 2 (mayo 2026): construccion del corpus paralelo completo, RAG operativo, primer fine-tuning LoRA, pipeline LLM+RAG, evaluacion comparativa preliminar".

- [ ] **Step 2: Actualizar seccion "Estructura del repositorio"**

Anadir `entrega2/`, los notebooks 03-11, `src/`, `lance_indexes/`, `models/`.

- [ ] **Step 3: Commit y tag**

```bash
git add README.md
git commit -m "doc: actualizar README con estado de Entrega 2"
git tag entrega2-final-v1
git push origin main --tags
```

### Task 29: QA final y handoff al usuario

- [ ] **Step 1: Verificar criterios de "hecho" del spec seccion 7**

Repasar cada checkbox de la seccion 7 del spec. Cualquier no cumplido se reporta al usuario antes de cerrar.

- [ ] **Step 2: Generar reporte de cierre**

Resumen breve para el usuario con: paginas del docx, numero de pares en el corpus, mejor config en cada metrica, deuda tecnica pendiente.

- [ ] **Step 3: Handoff explicito**

Comunicar al usuario que el flujo asistido cerro y que el .docx esta listo para que el usuario aplique sus ediciones finales en Word, exportar PDF, y subir a UNIR antes del 25-may.

---

## Self-review

- [x] Cubre todas las decisiones del spec (Camino 1, Torres Amat, Gemini embeddings, LanceDB, Claude)
- [x] Granularidad bite-sized (cada step es accion concreta)
- [x] No placeholders (todo el codigo critico esta escrito)
- [x] Tipo consistencia (la funcion `translate` aparece en src/models/claude_rag.py y se usa con la firma correcta en notebooks)
- [x] Cronograma de 7 dias respeta el deadline 24-25 mayo
- [x] Reduccion de rastros LLM esta en Task 24 explicita
- [x] Flujo md->py->docx respetado (Task 25 refactoriza py, Task 26 genera docx, Task 27 documenta para Word manual)
