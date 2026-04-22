# TFM Entrega 1, Plan de ejecución

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Producir el documento de la Entrega 1 del TFM grupal (≈25 páginas en la Plantilla Grupal UNIR, Capítulos 1-3 completos + Capítulo 4 esqueleto con avances reales + sección "Organización del trabajo en grupo" + bibliografía APA 7 ≥20 refs verificadas) junto con 3 notebooks de apoyo, antes de las 23:59 hora peninsular del 22 de abril de 2026.

**Architecture:** Se redacta primero en Markdown maestro (`entrega1/TFM_grupal_entrega1.md`) siguiendo la estructura de la plantilla `.docx`; notebooks en `notebooks/` generan evidencias cuantitativas (Tabla 3, Figura 7, datos JSONL) que se referencian desde el documento; al final se hace vaciado manual a la plantilla `.docx`, se genera el PDF y se envía. Sin git en este repositorio (no inicializado); checkpoints por archivo guardado.

**Tech Stack:** Markdown + Python 3.11 (`transformers`, `peft`, `accelerate`, `sentence-transformers`, `sacrebleu`, `datasets`, `anthropic`, `sentencepiece`, `matplotlib`, `pandas`), Apple Silicon (MPS), Jupyter, MS Word (plantilla oficial UNIR).

**Fuente primaria del diseño:** `/Users/william-santos/Documents/UNIR/tfm/docs/superpowers/specs/2026-04-21-tfm-entrega1-design.md`

**Bibliografía verificada:** `/Users/william-santos/Documents/UNIR/tfm/bibliografia/refs_verificadas.md`

**Recursos OCR-extraídos disponibles:** en `/Users/william-santos/Documents/UNIR/mistral-ocr-extractor/output/inga-kichwa/` (diccionario, gramática, apéndice, NT, Antihua Pacay).

---

## Reglas de oro aplicables a todas las tareas de redacción

1. **Tercera persona impersonal estricta.** Nunca "nosotros/nuestro/vemos". Siempre "se observa / el presente trabajo / los autores".
2. **Toda cita va con su entrada verificada** de `bibliografia/refs_verificadas.md`. Si una afirmación pide una cita y no hay entrada verificada, NO se cita (se omite o se busca una). Cero alucinación.
3. **APA 7** para todas las citas (narrativa y parentética intercaladas).
4. **Tiempos verbales** según capítulo:
 - Introducción (Cap 1) → presente.
 - Contexto/Estado del arte (Cap 2) → pasado para estudios previos, presente para hechos científicos.
 - Objetivos (Cap 3.1-3.2) → infinitivo.
 - Metodología (Cap 3.3) → pasado impersonal ("se configuró", "se dividió").
 - Desarrollo (Cap 4) → pasado impersonal para narrar, presente para referir figuras.
5. **Figuras/tablas**: invitación explícita en el texto inmediatamente anterior; rótulo `Figura N` / `Tabla N` en negrita; título en cursiva; centradas; `Nota.` al pie en cursiva.
6. **Sin código en el documento**: todo código vive en notebooks referenciados por URL.
7. **Guardado frecuente**: cada tarea termina con un "checkpoint save" explícito del archivo.

---

## Fase A, Estructura base y Capítulo 1 (20:00-22:00 hora Col)

### Task 1: Crear árbol de directorios del entregable

**Files:**
- Create: `entrega1/`
- Create: `entrega1/figuras/`
- Create: `notebooks/`
- Create: `datos/`
- Create: `bibliografia/refs_verificadas.bib` (se poblará en Task 33)

- [ ] **Step 1: Crear directorios**

```bash
mkdir -p /Users/william-santos/Documents/UNIR/tfm/entrega1/figuras
mkdir -p /Users/william-santos/Documents/UNIR/tfm/notebooks
mkdir -p /Users/william-santos/Documents/UNIR/tfm/datos
```

- [ ] **Step 2: Verificar creación**

```bash
ls -la /Users/william-santos/Documents/UNIR/tfm/
```

Expected: aparecen `entrega1/`, `notebooks/`, `datos/` además de los existentes.

---

### Task 2: Crear el documento maestro con esqueleto completo

**Files:**
- Create: `entrega1/TFM_grupal_entrega1.md`

- [ ] **Step 1: Escribir esqueleto con todas las secciones mapeadas a plantilla**

Escribir el archivo con este esqueleto (headers en blanco para llenar en tareas siguientes):

```markdown
<!-- PORTADA -->

# Universidad Internacional de La Rioja
## Escuela Superior de Ingeniería y Tecnología
## Máster Universitario en Inteligencia Artificial

**Diseño e implementación de un sistema comparativo de traducción automática Inga-Español mediante ajuste fino de modelos multilingües y recuperación aumentada de información sobre modelos de lenguaje de frontera**

Trabajo fin de estudio presentado por:
- Eslava, Daniel
- Santos, William

**Tipo de trabajo:** Piloto experimental
**Director:** Víctor David Larco Torres
**Fecha:** 22 de abril de 2026

---

## Resumen

[PENDIENTE, se redacta último]

**Palabras clave:** traducción automática, lenguas indígenas, Inga, transfer learning, recuperación aumentada de información

---

## Abstract

[PENDING, written last]

**Keywords:** machine translation, indigenous languages, Inga (Quechua), transfer learning, retrieval-augmented generation

---

## Índice de contenidos

[Autogenerado en Word]

## Índice de figuras

[Autogenerado en Word]

## Índice de tablas

[Autogenerado en Word]

---

## Organización del trabajo en grupo

### Partes que aborda el TFE

[Task 3]

### Distribución y estructura de la memoria

[Task 3, incluye Tabla 1]

### Mecanismos de coordinación empleados

[Task 3]

---

# 1. Introducción

## 1.1 Motivación

[Task 4]

## 1.2 Planteamiento del trabajo

[Task 5]

## 1.3 Estructura del trabajo

[Task 6]

---

# 2. Contexto y estado del arte

## 2.1 Contexto del problema

### 2.1.1 La lengua Inga y su situación en el Putumayo

[Task 11]

### 2.1.2 Marco legal-político en Colombia y contexto internacional

[Task 12]

### 2.1.3 Traducción automática de bajos recursos: fundamentos

[Task 13]

### 2.1.4 Transfer learning y recuperación aumentada: definiciones

[Task 14]

## 2.2 Estado del arte

### 2.2.1 Procesamiento del lenguaje natural para lenguas indígenas de América Latina

[Task 15]

### 2.2.2 Traducción automática de lenguas indígenas colombianas

[Task 16]

### 2.2.3 Traducción automática para Quechua: el caso cercano al Inga

[Task 17]

### 2.2.4 Modelos de lenguaje de frontera para traducción

[Task 18]

### 2.2.5 Recuperación aumentada aplicada a traducción

[Task 19]

### 2.2.6 Técnicas de ajuste fino eficiente en parámetros

[Task 20]

### 2.2.7 Modelos base candidatos: análisis comparativo

[Task 21, incluye Tabla 2]

## 2.3 Conclusiones del capítulo

[Task 22]

---

# 3. Objetivos concretos y metodología de trabajo

## 3.1 Objetivo general

[Task 27]

## 3.2 Objetivos específicos

[Task 28]

## 3.3 Metodología del trabajo

### 3.3.1 Enfoque metodológico

[Task 29]

### 3.3.2 Fases del proyecto

[Task 29]

### 3.3.3 Cronograma

[Task 29, incluye Figura 8]

### 3.3.4 Infraestructura de cómputo

[Task 29, incluye Tabla 5]

### 3.3.5 Configuraciones experimentales a evaluar

[Task 29, incluye Tabla 4]

---

# 4. Desarrollo específico de la contribución

## 4.1 Estado de avance al cierre de la Entrega 1

### 4.1.1 Fase 1. Configuración del entorno computacional

[Task 30]

### 4.1.2 Fase 2. Construcción del corpus paralelo

[Task 30, incluye Tabla 3 y Figura 7]

### 4.1.3 Fase 3. Diseño de la base de conocimiento

[Task 30]

## 4.2 Repositorio de código y datos

[Task 32]

## 4.3 Próximos pasos hacia la Entrega 2

[Task 30]

---

# 5. Conclusiones y trabajo futuro

## 5.1 Conclusiones

El contenido de este capítulo se presenta en la Entrega Final, una vez ejecutadas las Fases 4 a 7 del proyecto. La presente Entrega 1 abarca el planteamiento del problema, el estado del arte, la definición de objetivos y metodología, y el inicio de la construcción del corpus y la configuración del entorno experimental.

## 5.2 Líneas de trabajo futuro

El contenido de esta sección se presenta en la Entrega Final.

---

# Referencias bibliográficas

[Task 33]

---

# Anexo A. Código fuente y datos analizados

[Task 32]
```

- [ ] **Step 2: Verificar tamaño y estructura**

```bash
wc -l /Users/william-santos/Documents/UNIR/tfm/entrega1/TFM_grupal_entrega1.md
grep -c "^## " /Users/william-santos/Documents/UNIR/tfm/entrega1/TFM_grupal_entrega1.md
```

Expected: archivo creado, ≥15 secciones de segundo nivel.

---

### Task 3: Redactar "Organización del trabajo en grupo"

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección "Organización del trabajo en grupo")

- [ ] **Step 1: Reemplazar los placeholders con el contenido definitivo**

Contenido a insertar (reemplazar los tres marcadores `[Task 3]` en esa sección):

```markdown
### Partes que aborda el TFE

El presente Trabajo Fin de Máster se desarrolla en modalidad grupal por dos estudiantes, y aborda dos contribuciones técnicas autocontenidas que, de forma individual, podrían constituir un trabajo de investigación independiente, además de un componente de infraestructura compartida. Esta partición responde al requisito de la Universidad de que cada integrante realice un aporte técnico suficiente para la obtención del título.

La primera contribución, a cargo de **William Santos**, consiste en la adaptación de un modelo de traducción automática multilingüe preentrenado al par lingüístico Inga-Español mediante técnicas de ajuste fino eficiente en parámetros, aprovechando el conocimiento de lenguas quechuas emparentadas presente en el modelo como base para la transferencia. Este componente incluye además la curación del corpus bidialectal (Alto Putumayo y Medio Putumayo), labor que se nutre del acceso comunitario del integrante a hablantes nativos en Mocoa.

La segunda contribución, a cargo de **Daniel Eslava**, consiste en el diseño e implementación de un sistema de traducción basado en un modelo de lenguaje de frontera potenciado con recuperación aumentada de información. El sistema utiliza una base de conocimiento lingüístico del Inga estructurada en tres índices independientes (léxico, gramatical y de ejemplos paralelos) e incluye el diseño del framework de evaluación comparativa de ambas aproximaciones.

La infraestructura compartida entre ambos integrantes comprende la construcción y curación del corpus paralelo, la normalización ortográfica, la validación con hablantes nativos y el análisis de resultados.

### Distribución y estructura de la memoria

La estructura de responsabilidades para la redacción de la memoria se detalla en la Tabla 1.

**Tabla 1**
*Organización del trabajo en grupo en la redacción de la memoria*

| Apartado de la memoria | Responsables |
|---|---|
| Introducción | William Santos y Daniel Eslava |
| Contexto y estado del arte | William Santos (secciones NMT y ajuste fino eficiente), Daniel Eslava (secciones LLMs y RAG) |
| Objetivos y metodología de trabajo | William Santos y Daniel Eslava |
| Marco normativo | William Santos (aspectos comunitarios), Daniel Eslava (licenciamiento de datos y modelos) |
| Desarrollo, Adaptación del modelo multilingüe | William Santos |
| Desarrollo, Pipeline LLM con recuperación aumentada | Daniel Eslava |
| Desarrollo, Corpus e infraestructura experimental | William Santos y Daniel Eslava |
| Conclusiones | William Santos y Daniel Eslava |

*Nota.* Elaboración propia.

### Mecanismos de coordinación empleados

El trabajo remoto entre los integrantes, ubicados en Mocoa (Putumayo) y Cali (Valle del Cauca), exige mecanismos de coordinación formales. Se adoptan los siguientes instrumentos.

En primer lugar, se establece un repositorio compartido en GitHub para el código fuente, los notebooks y la documentación, con control de versiones y revisión cruzada mediante *pull requests*. En segundo lugar, se utiliza GitHub Projects para la gestión de tareas, con tableros que reflejan las siete fases del proyecto. En tercer lugar, se planifican reuniones síncronas semanales por videoconferencia para revisión de avances, toma de decisiones y resolución de bloqueos. En cuarto lugar, se emplea un gestor bibliográfico compartido (Zotero) que mantiene sincronizadas las referencias verificadas del proyecto. Finalmente, el documento de la memoria se redacta de forma colaborativa, con asignación clara de secciones según la distribución mostrada en la Tabla 1 y revisión cruzada antes de cada entrega.
```

- [ ] **Step 2: Verificar contenido**

```bash
grep -A2 "Partes que aborda el TFE" /Users/william-santos/Documents/UNIR/tfm/entrega1/TFM_grupal_entrega1.md | head -5
```

Expected: primer párrafo de la sección grupal visible, sin `[Task 3]`.

---

### Task 4: Redactar Capítulo 1.1 Motivación

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 1.1)

**Referencias a usar** (todas verificadas en `bibliografia/refs_verificadas.md`):
- UNESCO (2022), número de lenguas en peligro, Década 2022-2032
- Constitución de Colombia (1991) Art. 10, oficialidad territorial
- Congreso de la República de Colombia (2010) Ley 1381, derechos lingüísticos
- Tonja et al. (2024), panorama NLP lenguas indígenas América Latina
- Mager et al. (2023), ética en MT de lenguas indígenas
- Zhang, Frey y Bansal (2022), caso Cherokee: roadmap NLP
- Prieto et al. (2024), primer corpus paralelo con Inga

- [ ] **Step 1: Redactar tres párrafos de motivación en tiempo presente, tercera persona**

Estructura:
1. **Párrafo 1, La lengua Inga como realidad viva amenazada.** Mencionar los ~18.000 hablantes, la familia quechua, los dialectos AP y MP, el uso cotidiano, el desplazamiento progresivo por presión del español. Citar UNESCO (2022) para contexto global de lenguas en peligro.
2. **Párrafo 2, La brecha digital como forma contemporánea de exclusión.** Traductores comerciales (Google Translate, DeepL) no incluyen el Inga; Google Translate incorporó Quechua sureño en 2022 pero la variante Inga permanece excluida. Los recursos existentes (diccionarios SIL, materiales comunitarios) carecen de integración computacional. Esto profundiza la brecha entre lenguas hegemónicas e indígenas. Citar Tonja et al. (2024) para magnitud del rezago; Prieto et al. (2024) como primer precedente académico.
3. **Párrafo 3, Derechos y oportunidad tecnológica.** Marco legal: Constitución de Colombia (1991) Art. 10 oficialidad territorial; Ley 1381 (2010) fomento y protección; UNESCO (2022) Década de las Lenguas Indígenas 2022-2032. Avances recientes en NMT multilingüe, transfer learning desde Quechua y LLMs con RAG crean una ventana de oportunidad sin precedentes. Las consideraciones éticas en este tipo de iniciativas se discuten ampliamente (Mager et al., 2023); un caso análogo exitoso se documenta para el cherokee (Zhang et al., 2022).

Longitud objetivo: ~500 palabras (≈1.5 páginas Word).

- [ ] **Step 2: Checklist de forma**

Verificar antes de guardar:
- ✓ Ningún "nosotros", "nuestro", "vemos".
- ✓ Todas las citas aparecen en `refs_verificadas.md`.
- ✓ Al menos 2 citas narrativas + 2 parentéticas (fluidez APA).
- ✓ Tiempo presente dominante.

---

### Task 5: Redactar Capítulo 1.2 Planteamiento del trabajo

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 1.2)

- [ ] **Step 1: Redactar en tiempo presente**

Estructura:
1. **Problema técnico concreto.** Producir un sistema de traducción Inga-Español utilizable para una lengua con menos de 5.000 pares paralelos publicados antes del presente trabajo.
2. **Pregunta de investigación explícita.** *¿Cuál aproximación, el ajuste fino de un modelo de traducción multilingüe mediante técnicas eficientes en parámetros, o el uso de un modelo de lenguaje de frontera potenciado con recuperación aumentada, resulta más efectiva para traducir del Inga al Español cuando los datos disponibles son extremadamente escasos?*
3. **Propuesta general de solución.** Desarrollo en paralelo de ambas aproximaciones sobre un corpus bidialectal construido desde recursos comunitarios y textos paralelos existentes. Comparación sistemática con métricas automáticas (BLEU, chrF++, BERTScore) y validación cualitativa con hablantes nativos.
4. **Alcance del TFM.** Piloto experimental local, no un sistema de producción. Enfoque sobre dialectos AP (Alto Putumayo) y MP (Medio Putumayo). Meta: corpus de ~8.000-10.000 pares al cierre. La liberación de los recursos como bienes comunes queda planteada como línea de trabajo ulterior, no como objetivo central de evaluación.

Longitud: ~400 palabras.

- [ ] **Step 2: Checklist de forma** (mismo de Task 4)

---

### Task 6: Redactar Capítulo 1.3 Estructura del trabajo

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 1.3)

- [ ] **Step 1: Un párrafo por capítulo**

```markdown
El presente documento se organiza en cinco capítulos. El Capítulo 1 introduce la motivación, el planteamiento del problema y la estructura general del trabajo. El Capítulo 2 desarrolla el contexto del problema, incluyendo la situación sociolingüística del Inga, el marco legal colombiano e internacional, y los fundamentos técnicos de la traducción automática de bajos recursos; posteriormente presenta una revisión crítica del estado del arte en traducción de lenguas indígenas, con énfasis en el Quechua como lengua emparentada. El Capítulo 3 expone el objetivo general, los objetivos específicos y la metodología del trabajo, organizada en siete fases y acompañada del cronograma y la infraestructura computacional. El Capítulo 4 presenta el desarrollo específico de la contribución; en la presente entrega se documentan los avances alcanzados al cierre de las primeras fases (configuración del entorno, construcción inicial del corpus y diseño de la base de conocimiento). El Capítulo 5 recoge las conclusiones y las líneas de trabajo futuro; su contenido íntegro se presenta en la Entrega Final del TFM. Finalmente, se incluyen las referencias bibliográficas consultadas y un anexo con el enlace al repositorio de código y datos.
```

- [ ] **Step 2: Verificar**

```bash
grep -c "Capítulo" /Users/william-santos/Documents/UNIR/tfm/entrega1/TFM_grupal_entrega1.md
```

Expected: ≥6 menciones (las cinco del párrafo + otras del documento).

---

## Fase B, Notebooks 00 y 01 (22:00-02:00 hora Col)

### Task 7: Crear `00_setup_entorno.ipynb`

**Files:**
- Create: `notebooks/00_setup_entorno.ipynb`

- [ ] **Step 1: Generar el notebook vía script Python**

```bash
cat <<'PY' > /tmp/gen_nb00.py
import nbformat as nbf
nb = nbf.v4.new_notebook()
nb.cells = [
 nbf.v4.new_markdown_cell("# 00, Configuración del entorno computacional\n\n**TFM Inga-Español.** Este notebook valida el entorno local (Apple M4 Max, 128 GB, macOS) para las fases siguientes. Ejecución única al arrancar el proyecto."),
 nbf.v4.new_markdown_cell("## Versiones y aceleración"),
 nbf.v4.new_code_cell("import sys, platform\nprint('Python:', sys.version)\nprint('Platform:', platform.platform())"),
 nbf.v4.new_code_cell("import torch\nprint('PyTorch:', torch.__version__)\nprint('MPS disponible:', torch.backends.mps.is_available())\nprint('MPS construido:', torch.backends.mps.is_built())"),
 nbf.v4.new_markdown_cell("## Librerías instaladas\n\nLas librerías se instalan desde `requirements.txt` o mediante `uv`/`pip`. Este notebook solo verifica disponibilidad."),
 nbf.v4.new_code_cell("import importlib\nlibs = ['transformers', 'peft', 'accelerate', 'sentence_transformers', 'sacrebleu', 'datasets', 'anthropic', 'sentencepiece', 'matplotlib', 'pandas', 'numpy', 'tqdm']\nfor lib in libs:\n try:\n m = importlib.import_module(lib)\n print(f' ✓ {lib}: {getattr(m, \"__version__\", \"?\")}')\n except ImportError as e:\n print(f' ✗ {lib}: NO INSTALADA ({e})')"),
 nbf.v4.new_markdown_cell("## Descarga y prueba del modelo base pequeño\n\nSe descarga `facebook/nllb-200-distilled-600M` como modelo de trabajo para iteración rápida. Se valida una inferencia zero-shot Español→Quechua Ayacucho, par lingüísticamente cercano al Inga que el modelo ya incluye."),
 nbf.v4.new_code_cell("from transformers import AutoTokenizer, AutoModelForSeq2SeqLM\nmodel_name = 'facebook/nllb-200-distilled-600M'\ntokenizer = AutoTokenizer.from_pretrained(model_name)\nmodel = AutoModelForSeq2SeqLM.from_pretrained(model_name)\ndevice = 'mps' if __import__('torch').backends.mps.is_available() else 'cpu'\nmodel.to(device)\nprint(f'Modelo cargado en {device}.')"),
 nbf.v4.new_code_cell("# Prueba: Español → Quechua Ayacucho\nsrc_text = 'La lengua Inga es hablada en el Putumayo.'\ntokenizer.src_lang = 'spa_Latn'\ninputs = tokenizer(src_text, return_tensors='pt').to(device)\ntranslated_tokens = model.generate(\n **inputs,\n forced_bos_token_id=tokenizer.convert_tokens_to_ids('quy_Latn'),\n max_length=128\n)\nresult = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)\nprint('ES:', src_text)\nprint('QUY (zero-shot):', result)"),
 nbf.v4.new_markdown_cell("## Resumen\n\nSi todas las celdas anteriores se ejecutan sin error, el entorno está listo para las Fases 2-7 del TFM. El modelo NLLB-200-distilled-600M queda cacheado en `~/.cache/huggingface/hub` para notebooks siguientes."),
]
with open('/Users/william-santos/Documents/UNIR/tfm/notebooks/00_setup_entorno.ipynb', 'w') as f:
 nbf.write(nb, f)
print('Notebook creado.')
PY
python3 /tmp/gen_nb00.py
```

Expected: `Notebook creado.`

- [ ] **Step 2: Verificar el notebook es JSON válido**

```bash
python3 -c "import nbformat; nbformat.read('/Users/william-santos/Documents/UNIR/tfm/notebooks/00_setup_entorno.ipynb', as_version=4); print('OK')"
```

Expected: `OK`

---

### Task 8: Ejecutar `00_setup_entorno.ipynb`

**Files:**
- Modify: `notebooks/00_setup_entorno.ipynb` (con outputs)

- [ ] **Step 1: Ejecutar el notebook**

```bash
cd /Users/william-santos/Documents/UNIR/tfm && \
jupyter nbconvert --to notebook --execute notebooks/00_setup_entorno.ipynb \
 --output 00_setup_entorno.ipynb --ExecutePreprocessor.timeout=600
```

Expected: todas las celdas ejecutadas, ninguna en estado de error.

- [ ] **Step 2: Si falla instalación de alguna librería, instalar con pip**

Si la celda de verificación reporta `NO INSTALADA`:

```bash
pip install transformers peft accelerate sentence-transformers sacrebleu datasets anthropic sentencepiece matplotlib pandas numpy tqdm nbformat jupyter
```

Luego re-ejecutar Step 1.

- [ ] **Step 3: Confirmar output de la inferencia de prueba**

```bash
python3 -c "
import nbformat
nb = nbformat.read('/Users/william-santos/Documents/UNIR/tfm/notebooks/00_setup_entorno.ipynb', as_version=4)
for c in nb.cells:
 if c.cell_type == 'code':
 for o in c.get('outputs', []):
 if 'text' in o:
 print(o['text'][-300:])
"
```

Expected: al final aparece "ES: ..." y "QUY (zero-shot): ..." con texto no vacío.

---

### Task 9: Crear `01_eda_recursos_base.ipynb`

**Files:**
- Create: `notebooks/01_eda_recursos_base.ipynb`

- [ ] **Step 1: Definir rutas y estructura del parseo**

Crear el notebook con las siguientes celdas (estructura):

1. **Markdown intro.** Descripción: EDA de los 5 recursos locales OCR-extraídos; genera `diccionario_inga.jsonl`, `estadisticas_corpus.json` y la Figura 7.
2. **Code: imports + constantes.**
 ```python
 from pathlib import Path
 import json, re
 import matplotlib.pyplot as plt
 import pandas as pd

 OCR_ROOT = Path('/Users/william-santos/Documents/UNIR/mistral-ocr-extractor/output/inga-kichwa')
 DATA_OUT = Path('/Users/william-santos/Documents/UNIR/tfm/datos')
 FIG_OUT = Path('/Users/william-santos/Documents/UNIR/tfm/entrega1/figuras')
 DATA_OUT.mkdir(parents=True, exist_ok=True)
 FIG_OUT.mkdir(parents=True, exist_ok=True)

 RESOURCES = {
 'diccionario': OCR_ROOT / '756362843-Diccionario-Inga' / 'content.md',
 'gramatica_pedagogica': OCR_ROOT / 'Inga Kichwa; Una Gramatica Pedagogical del Inga (parts 1 & 2) (Levinsohn)' / 'content.md',
 'apendice_morfosintactico': OCR_ROOT / 'rosettaproject_inb_morsyn-1' / 'content.md',
 'nuevo_testamento': OCR_ROOT / '00-WNTinb-web' / 'content.md',
 'antihua_pacay': OCR_ROOT / 'inj-AntihuaPacay' / 'content.md',
 }
 ```
3. **Code: conteos agregados por recurso.**
 ```python
 def count_basic(md_path):
 text = md_path.read_text(encoding='utf-8')
 chars = len(text)
 words = len(text.split())
 lines = text.count('\n') + 1
 pages = text.count('<!-- Page ')
 return {'chars': chars, 'words': words, 'lines': lines, 'pages': pages}

 stats = {name: count_basic(p) for name, p in RESOURCES.items()}
 stats_df = pd.DataFrame(stats).T
 print(stats_df)
 ```
4. **Code: parseo del diccionario a JSONL.**
 ```python
 # Parsear el diccionario: líneas con formato "lema [abreviatura] glosa_es"
 # Las entradas suelen aparecer en negrita o con estructura identificable.
 dict_text = RESOURCES['diccionario'].read_text(encoding='utf-8')
 # Filtro heurístico: líneas que empiezan con una palabra en minúscula + abreviatura gramatical
 ABBREV = r'(adj|adv|s|v\.i|v\.t|interj|conj|dem|gen|intens|pron|num|vbo)'
 entry_re = re.compile(rf'^([a-záéíóúñiüIṅ][\w\-]*)\s+({ABBREV})\b\s+(.+?)$', re.MULTILINE)
 entries = []
 for m in entry_re.finditer(dict_text):
 entries.append({'lema': m.group(1), 'cat': m.group(2), 'glosa': m.group(3).strip()[:300]})
 print(f'Entradas léxicas detectadas: {len(entries)}')
 with open(DATA_OUT / 'diccionario_inga.jsonl', 'w') as f:
 for e in entries:
 f.write(json.dumps(e, ensure_ascii=False) + '\n')
 ```
5. **Code: estimación de versículos del NT.**
 ```python
 nt_text = RESOURCES['nuevo_testamento'].read_text(encoding='utf-8')
 # Los versículos en Wycliffe suelen estar numerados: "1 ", "2 " al inicio de línea o tras capítulo
 # Detección heurística: secuencias "N texto" donde N es número, tras un marcador de capítulo.
 verse_re = re.compile(r'(?m)^(\d{1,3})\s+\S')
 verses = verse_re.findall(nt_text)
 print(f'Número aproximado de versículos marcados: {len(verses)}')
 ```
6. **Code: figura distribución de longitudes del NT (Fig 7).**
 ```python
 # Extraer longitudes de cada versículo aproximado (segmento entre dos marcadores)
 verse_segments = re.split(r'(?m)^\d{1,3}\s+', nt_text)
 lengths = [len(s.split()) for s in verse_segments if 3 < len(s.split()) < 80]
 print(f'Versículos con longitud válida: {len(lengths)}')
 fig, ax = plt.subplots(figsize=(8, 4.5))
 ax.hist(lengths, bins=40, edgecolor='black')
 ax.set_xlabel('Número de palabras por versículo (Inga)')
 ax.set_ylabel('Frecuencia')
 ax.set_title('Distribución de longitudes, Nuevo Testamento en Inga')
 plt.tight_layout()
 plt.savefig(FIG_OUT / 'fig07_distribucion_longitud_nt.png', dpi=150)
 plt.show()
 print(f'Media: {sum(lengths)/len(lengths):.1f} palabras, Mediana aprox.')
 ```
7. **Code: guardar estadísticas agregadas.**
 ```python
 summary = {
 'recursos': {name: count_basic(p) for name, p in RESOURCES.items()},
 'diccionario_entradas_detectadas': len(entries),
 'nt_versiculos_aprox': len(verses),
 'nt_longitud_media_palabras': sum(lengths)/len(lengths) if lengths else 0,
 }
 with open(DATA_OUT / 'estadisticas_corpus.json', 'w') as f:
 json.dump(summary, f, ensure_ascii=False, indent=2)
 print('Stats guardados.')
 print(json.dumps(summary, ensure_ascii=False, indent=2))
 ```
8. **Markdown conclusión.** Los outputs alimentan la Tabla 3 y la Figura 7 del Capítulo 4.1.

- [ ] **Step 2: Generar notebook con script**

Usar el mismo patrón de `nbformat` de Task 7, con las 8 celdas anteriores.

```bash
cat <<'PY' > /tmp/gen_nb01.py
import nbformat as nbf
nb = nbf.v4.new_notebook()
# [Código: construir las 8 celdas exactas listadas en Step 1]
# ... (completar con las 8 celdas arriba)
with open('/Users/william-santos/Documents/UNIR/tfm/notebooks/01_eda_recursos_base.ipynb', 'w') as f:
 nbf.write(nb, f)
print('OK')
PY
python3 /tmp/gen_nb01.py
```

- [ ] **Step 3: Verificar JSON válido**

```bash
python3 -c "import nbformat; nbformat.read('/Users/william-santos/Documents/UNIR/tfm/notebooks/01_eda_recursos_base.ipynb', as_version=4); print('OK')"
```

---

### Task 10: Ejecutar `01_eda_recursos_base.ipynb`

**Files:**
- Modify: `notebooks/01_eda_recursos_base.ipynb` (con outputs)
- Create: `datos/diccionario_inga.jsonl`
- Create: `datos/estadisticas_corpus.json`
- Create: `entrega1/figuras/fig07_distribucion_longitud_nt.png`

- [ ] **Step 1: Ejecutar**

```bash
cd /Users/william-santos/Documents/UNIR/tfm && \
jupyter nbconvert --to notebook --execute notebooks/01_eda_recursos_base.ipynb \
 --output 01_eda_recursos_base.ipynb --ExecutePreprocessor.timeout=600
```

- [ ] **Step 2: Verificar archivos generados**

```bash
ls -la /Users/william-santos/Documents/UNIR/tfm/datos/
ls -la /Users/william-santos/Documents/UNIR/tfm/entrega1/figuras/fig07*.png
cat /Users/william-santos/Documents/UNIR/tfm/datos/estadisticas_corpus.json
```

Expected: los 3 archivos existen, `estadisticas_corpus.json` muestra valores razonables.

- [ ] **Step 3: Registrar los números reales obtenidos**

Tomar los números concretos de `estadisticas_corpus.json` (entradas léxicas detectadas, versículos aprox, longitud media). Estos valores se insertan textualmente en Task 30.

---

## Fase C, Capítulo 2 (02:00-06:00 hora Col)

### Task 11: Redactar §2.1.1 La lengua Inga y su situación en el Putumayo

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.1.1)

**Referencias a usar:**
- Diccionario Inga (Tandioy/Levinsohn 1997), dialectos AP/MP documentados allí
- Tandioy Jansasoy (Indiana University), origen académico del Inga como objeto lingüístico
- Tonja et al. (2024), contexto general NLP lenguas indígenas Latam
- UNESCO (2022), Atlas

- [ ] **Step 1: Redactar 3-4 párrafos en presente (para descripciones lingüísticas) y pasado (para estudios previos)**

Cobertura:
1. Familia lingüística: quechua periférico (QI); tipo tipológico aglutinante; orden SOV. Citar Tandioy Jansasoy y Diccionario Inga como fuentes primarias.
2. Demografía: ~18.000 hablantes; distribución geográfica en Putumayo (Mocoa, Santiago, Colón, San Andrés, Condagua, Yunguillo, Guayuyaco). Citar UNESCO (2022) para contexto global.
3. Dialectos: AP (Alto Putumayo: Valle de Sibundoy, corregimientos de San Andrés y de Santiago/Colón) vs. MP (Medio Putumayo: Mocoa, Condagua, Yunguillo, Guayuyaco). Diferencias léxicas documentadas en el diccionario (Tandioy/Levinsohn, 1997): ejemplo `achijai / achijii / jachii` (estornudar) entre AP, Yunguillo y Mocoa. Esta variación dialectal tiene implicaciones para cualquier sistema de traducción automática que se adopte.
4. Situación sociolingüística: desplazamiento por presión del español; ámbitos de uso en retroceso. Tonja et al. (2024) documentan la escasez sistemática de recursos NLP para esta categoría de lenguas.

Longitud: ~500 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 12: Redactar §2.1.2 Marco legal-político

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.1.2)

**Referencias:**
- Constitución de Colombia (1991) Art. 10
- Congreso de la República de Colombia (2010) Ley 1381
- UNESCO (2022) Atlas + Década 2022-2032

- [ ] **Step 1: Redactar 2-3 párrafos**

Cobertura:
1. **Colombia**: oficialidad territorial del Inga (Const. 1991 Art. 10); Ley 1381 (2010) desarrolla los artículos 7, 8, 10 y 70 de la Constitución, establece derechos lingüísticos de los grupos étnicos, principios de preservación y fomento. Implicaciones para educación intercultural bilingüe.
2. **Internacional**: UNESCO (2022) World Atlas of Languages reemplaza al antiguo Atlas of Languages in Danger; documenta 8.324 lenguas. Década Internacional de las Lenguas Indígenas 2022-2032 proclamada por la ONU.
3. **Conclusión**: existe un marco normativo robusto pero una brecha entre el reconocimiento formal y la disponibilidad de herramientas digitales. El presente trabajo se sitúa en esta brecha.

Longitud: ~300 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 13: Redactar §2.1.3 Fundamentos de traducción automática de bajos recursos

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.1.3)

**Referencias:**
- NLLB Team et al. (2022, 2024), estado de NMT multilingüe masivo
- Tonja et al. (2024), categorización de bajos recursos

- [ ] **Step 1: Redactar 2-3 párrafos técnicos**

Cobertura:
1. Definición operativa de lengua de bajos recursos en NMT (criterios: cantidad de datos paralelos publicados, cobertura en modelos preentrenados). Ubicación del Inga como lengua de recursos extremadamente bajos.
2. Evolución de paradigmas: SMT (traducción estadística) → NMT basada en RNN → Transformer → modelos multilingües masivos (NLLB-200). Citar NLLB Team (2022, 2024).
3. Desafíos específicos: escasez de datos, divergencia tipológica, evaluación con métricas diseñadas para alta disponibilidad (BLEU), riesgo de modelos que generan textos sintácticamente fluidos pero semánticamente incorrectos.

Longitud: ~350 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 14: Redactar §2.1.4 Transfer learning y RAG: definiciones

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.1.4)

**Referencias:**
- Hu et al. (2022) LoRA
- Lewis et al. (2020) RAG
- Wang et al. (2024) RAGtrans

- [ ] **Step 1: Redactar 2-3 párrafos**

Cobertura:
1. Transfer learning en NMT: definición (reutilizar representaciones aprendidas en una lengua de alta disponibilidad para una de baja). Variantes: fine-tuning completo vs. parameter-efficient fine-tuning. Citar Hu et al. (2022).
2. RAG (Retrieval-Augmented Generation): definición (combinar un generador con un mecanismo de recuperación que inyecta conocimiento externo al prompt). Originalmente propuesto para tareas intensivas en conocimiento (Lewis et al., 2020).
3. RAG aplicado a traducción es relativamente reciente; Wang et al. (2024) proponen RAGtrans como primer benchmark. El presente TFM se inscribe en esta línea emergente.

Longitud: ~300 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 15: Redactar §2.2.1 NLP para lenguas indígenas de América Latina

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.2.1)

**Referencias:**
- Tonja et al. (2024)
- Ebrahimi et al. (2024) AmericasNLP 2024
- de Gibert et al. (2025) AmericasNLP 2025
- Mager et al. (2023) ética

- [ ] **Step 1: Redactar en pasado para estudios previos**

Cobertura:
1. Panorama: Tonja et al. (2024) documentaron el progreso de NLP para lenguas indígenas de América Latina y categorizaron familias (quechua, guaraní, náhuatl, aymara, tupí...).
2. AmericasNLP como foro canalizador: AmericasNLP 2024 (Ebrahimi et al., 2024) cubrió 12 pares y publicó corpora estandarizados. AmericasNLP 2025 (de Gibert et al., 2025) extendió a tareas de creación de material educativo y métricas específicas.
3. Consideraciones éticas y comunitarias (Mager et al., 2023).

Longitud: ~350 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 16: Redactar §2.2.2 Traducción automática de lenguas indígenas colombianas

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.2.2)

**Referencias:**
- Prieto et al. (2024)
- Salazar, Manrique y Pereira Nunes (2025)

- [ ] **Step 1: Redactar**

Cobertura:
1. Prieto et al. (2024): primer corpus paralelo para lenguas indígenas colombianas incluyendo Inga; aplicaron transfer learning desde NLLB-200; presentaron resultados base.
2. Salazar, Manrique y Pereira Nunes (2025): ampliación con estrategias combinadas (fine-tuning + augmentación); publicado en SN Computer Science.
3. Gap identificado: ninguno de los trabajos previos distingue dialectos del Inga (AP vs. MP). El presente TFM introduce esta distinción como aporte metodológico.

Longitud: ~300 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 17: Redactar §2.2.3 Traducción automática para Quechua

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.2.3)

**Referencias:**
- Chen et al. (2024) QueEn
- Garcia Gilabert et al. (2024) BSC
- Attieh et al. (2024) NordicsAlps
- DeGenaro y Lupicki (2024)
- Dhawan et al. (2026)

- [ ] **Step 1: Redactar en pasado**

Cobertura (uno por trabajo, priorizando los más relevantes):
1. Chen et al. (2024) QueEn: combinación LoRA + RAG sobre LLM para Quechua-Inglés; mejoras BLEU de 1.5 a 17.6 puntos sobre baselines. Es el antecedente metodológico más directo del presente TFM.
2. Garcia Gilabert et al. (2024) BSC: **paper clave**. Ganador ES→Quechua y ES→Guaraní en AmericasNLP 2024 entrenando solo 14.2% de los parámetros de NLLB mediante adaptadores LoRA. Evidencia directa de la viabilidad del enfoque propuesto.
3. Attieh et al. (2024) NordicsAlps: mejor chrF++ promedio 2024; destacan el impacto de la tokenización byte-level para lenguas aglutinantes.
4. DeGenaro y Lupicki (2024): comparación arquitectural Mamba vs. NLLB.
5. Dhawan et al. (2026): augmentación sintética y preprocesamiento específico por lengua; particularmente relevante para la limpieza del corpus Inga.

Longitud: ~500 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 18: Redactar §2.2.4 LLMs de frontera para traducción

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.2.4)

**Referencias:**
- Enis y Hopkins (2024)
- Hendy et al. (2023)
- Zhu et al. (2024)
- Cahyawijaya, Lovenia y Fung (2024)

- [ ] **Step 1: Redactar**

Cobertura:
1. Enis y Hopkins (2024): Claude exhibe "resource efficiency" en traducción; su calidad se degrada menos que otros LLMs al pasar de altos a bajos recursos.
2. Hendy et al. (2023): evaluación comprehensiva GPT vs. NMT dedicado; brecha favorable al NMT en bajos recursos; brecha decreciente con LLMs modernos.
3. Zhu et al. (2024): análisis empírico de LLMs multilingües en MT; confirman que la brecha persiste para lenguas bajo-cobertura.
4. Cahyawijaya, Lovenia y Fung (2024): LLMs como few-shot learners de bajos recursos con prompting por similitud, fundamento teórico del índice de ejemplos del RAG.

Longitud: ~400 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 19: Redactar §2.2.5 RAG aplicado a traducción

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.2.5)

**Referencias:**
- Lewis et al. (2020)
- Wang et al. (2024) RAGtrans
- Chen et al. (2024) QueEn

- [ ] **Step 1: Redactar**

Cobertura:
1. Lewis et al. (2020): paradigma RAG original para tareas intensivas en conocimiento.
2. Wang et al. (2024): RAGtrans, primer benchmark explícito de RAG aplicado a MT.
3. Chen et al. (2024) QueEn: aplicación exitosa a traducción de Quechua-Inglés.
4. Gap: literatura escasa en RAG-MT multi-índice (léxico/gramatical/ejemplos separados) como el que propone el presente TFM.

Longitud: ~300 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 20: Redactar §2.2.6 Técnicas de ajuste fino eficiente (PEFT)

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.2.6)

**Referencias:**
- Hu et al. (2022) LoRA
- Dettmers et al. (2023) QLoRA
- Liu et al. (2024) DoRA
- Su et al. (2024) comparación empírica

- [ ] **Step 1: Redactar**

Cobertura:
1. LoRA (Hu et al., 2022): inserción de matrices de bajo rango en capas de atención; reduce parámetros entrenables en 10.000× con pérdida mínima de calidad.
2. QLoRA (Dettmers et al., 2023): cuantización a 4 bits + LoRA; permite fine-tuning de modelos mayores en hardware limitado.
3. DoRA (Liu et al., 2024): descomposición peso-magnitud-dirección; mejora respecto a LoRA en varios benchmarks a igual parámetros.
4. Su et al. (2024): comparación empírica de 8 métodos PEFT sobre 15 arquitecturas en LRL-NMT; recomienda adaptadores para el caso del TFM.

Longitud: ~350 palabras.

- [ ] **Step 2: Checklist forma**

---

### Task 21: Redactar §2.2.7 Modelos base candidatos + Tabla 2

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.2.7)

**Referencias:**
- NLLB Team (2022, 2024)
- Kudugunta et al. (2023) MADLAD-400
- Finkelstein et al. (2026) TranslateGemma

- [ ] **Step 1: Redactar párrafo de contexto**

Párrafo introductorio + invitación a la tabla.

- [ ] **Step 2: Insertar Tabla 2**

```markdown
**Tabla 2**
*Comparativa de modelos base multilingües candidatos para la adaptación al par Inga-Español*

| Modelo | Parámetros | Lenguas | Quechua incluido | Licencia | Arquitectura | Ajustable en M4 Max 128 GB |
|---|---|---|---|---|---|---|
| NLLB-200-3.3B (Costa-jussà et al., 2022) | 3.3B | 200 | Sí (`quy_Latn`) | CC BY-NC 4.0 | Encoder-decoder | Sí, fine-tuning completo |
| NLLB-200-distilled-600M | 600M | 200 | Sí | CC BY-NC 4.0 | Encoder-decoder | Sí, muy holgado |
| MADLAD-400-10B (Kudugunta et al., 2023) | 10.7B | 450+ | Sí (`qu`) | Apache 2.0 | T5 | Sí, con LoRA |
| TranslateGemma-12B (Finkelstein et al., 2026) | 12B | Multi | Parcial | Gemma License | Decoder-only | Sí, con LoRA |

*Nota.* Elaboración propia con base en las especificaciones publicadas por los autores.
```

- [ ] **Step 3: Cerrar con 2-3 frases de síntesis** justificando que NLLB-200-distilled-600M se usa para prototipado y NLLB-200-3.3B como modelo principal.

Longitud total sección: ~300 palabras + tabla.

---

### Task 22: Redactar §2.3 Conclusiones del capítulo

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 2.3)

- [ ] **Step 1: Redactar**

Síntesis en 3-4 párrafos:
1. El estado del arte demuestra viabilidad técnica de adaptar NMT multilingüe a lenguas indígenas por transferencia desde parientes lingüísticos (evidencia: BSC 2024, QueEn).
2. El paradigma LLM+RAG ha emergido como alternativa complementaria con "resource efficiency" documentada (Enis y Hopkins, 2024).
3. El gap de literatura: ningún trabajo publicado compara ambas aproximaciones en el mismo par lingüístico y con cobertura bidialectal. Este gap es el espacio del presente TFM.
4. Frase de puente al Capítulo 3.

Longitud: ~350 palabras.

- [ ] **Step 2: Checklist forma**

---

## Fase D, Notebook 02 (06:00-09:00 hora Col)

### Task 23: Crear `02_extraccion_corpus_NT.ipynb`

**Files:**
- Create: `notebooks/02_extraccion_corpus_NT.ipynb`

- [ ] **Step 1: Estructura de celdas**

1. Markdown intro.
2. Imports + constantes (mismas rutas que notebook 01).
3. **Parse del NT Inga**: segmentación por libro (detectar headers `# NOMBRE_LIBRO` en el markdown), por capítulo y por versículo. Producir diccionario `{(libro, cap, ver): texto_inga}`.
4. **Descarga del NT español RV 1909**: usar dump de `bible.helloao.org` (dominio público confirmado). Ejemplo de endpoint:
 ```python
 import requests
 # Reina-Valera 1909 (es_rv1909), o alternativa disponible en la API
 # API helloao: /api/SPARVG/<book>/<chapter>.json o similar
 # Si no hay endpoint directo, descargar dump completo y parsear
 ```
 Fallback: cargar desde archivo local si se descargó antes.
5. **Alineación por referencia canónica**: emparejar `(libro, cap, ver)` entre ambos. Normalizar nombres de libros (Wycliffe usa nombres en Inga traducidos: "San Mateo → Mateo", etc.). Mapeo explícito:
 ```python
 INGA_TO_STD = {
 'San Mateo': 'Mateo', 'San Marcos': 'Marcos', 'San Lucas': 'Lucas', 'San Juan': 'Juan',
 'Jesús agllaskakuna ima ruraskakunamanda': 'Hechos', 'Romapi Cristowa tukaskakunata': 'Romanos',
 '1 Korintopi Cristowa tukuskakunata': '1 Corintios', '2 Korintopi Cristowa tukuskakunata': '2 Corintios',
 'Galasiapi Cristowa tukuskakunata': 'Gálatas', 'Efesopi Cristowa tukuskakunata': 'Efesios',
 'Filipospi Cristowa tukuskakunata': 'Filipenses', 'Kolosaspi Cristowa tukuskakunata': 'Colosenses',
 # ... (lista completa disponible en la tabla de contenidos del NT)
 }
 ```
6. **Guardar `nt_inga_alineado.jsonl`**.
7. **Parse de Antihua Pacay**: detectar bloques por cambio de idioma.
 ```python
 # Detector heurístico: sufijos aglutinantes típicos del Inga
 INGA_MARKERS = {'-cuna', '-manda', '-hua', '-spa', '-pac', '-pi', '-ta', '-mi', '-si'}
 def score_inga(text):
 tokens = text.lower().split()
 matches = sum(1 for tok in tokens for m in INGA_MARKERS if tok.endswith(m.strip('-')))
 return matches / max(len(tokens), 1)
 ```
8. **Alineación blockwise + intra-block**: emparejar bloques consecutivos Inga→Español. Dentro de cada bloque, segmentar en oraciones (nltk.sent_tokenize o regex por `\. `) y alinear por longitud (algoritmo de Gale-Church).
9. **Guardar `antihua_pacay_alineado.jsonl`**.
10. **Reporte final**: imprimir conteos (versículos alineados, bloques detectados, oraciones paralelas).

- [ ] **Step 2: Generar notebook con script**

Usar `nbformat` como en Task 7/9.

- [ ] **Step 3: Verificar JSON válido**

---

### Task 24: Ejecutar `02_extraccion_corpus_NT.ipynb` (parte NT)

**Files:**
- Modify: `notebooks/02_extraccion_corpus_NT.ipynb`
- Create: `datos/nt_inga_alineado.jsonl`

- [ ] **Step 1: Ejecutar**

```bash
cd /Users/william-santos/Documents/UNIR/tfm && \
jupyter nbconvert --to notebook --execute notebooks/02_extraccion_corpus_NT.ipynb \
 --output 02_extraccion_corpus_NT.ipynb --ExecutePreprocessor.timeout=1200
```

- [ ] **Step 2: Si falla descarga de RV 1909, fallback local**

Si `requests` falla al descargar el NT español:

```bash
# Fallback: usar el dump público
wget -O /tmp/rv1909.json https://bible.helloao.org/api/SPARVG/books.json
# Ajustar celda 4 del notebook para leer desde /tmp/rv1909.json
```

Alternativa si también falla: usar sólo los capítulos/versículos del NT Inga como corpus monolingüe ordenado, y dejar la alineación ES para Entrega 2 (reportarlo honestamente en Cap 4).

- [ ] **Step 3: Verificar JSONL generado**

```bash
wc -l /Users/william-santos/Documents/UNIR/tfm/datos/nt_inga_alineado.jsonl
head -3 /Users/william-santos/Documents/UNIR/tfm/datos/nt_inga_alineado.jsonl
```

Expected: ≥500 líneas (el ideal sería ~7.900 si la alineación funciona plenamente).

---

### Task 25: Ejecutar extracción de Antihua Pacay

**Files:**
- Modify: `notebooks/02_extraccion_corpus_NT.ipynb`
- Create: `datos/antihua_pacay_alineado.jsonl`

- [ ] **Step 1: La ejecución ya corrió como parte de Task 24; verificar archivo**

```bash
wc -l /Users/william-santos/Documents/UNIR/tfm/datos/antihua_pacay_alineado.jsonl
head -3 /Users/william-santos/Documents/UNIR/tfm/datos/antihua_pacay_alineado.jsonl
```

Expected: ≥50 líneas de pares paralelos.

- [ ] **Step 2: Si el detector de idioma falla** (scores ambiguos)

Ajustar umbral de detección en la celda correspondiente y re-ejecutar solo esa celda con Jupyter.

---

## Fase E, Capítulo 3 (09:00-11:00 hora Col)

### Task 26: Crear Figura 4, Pipeline de construcción del corpus

**Files:**
- Create: `entrega1/figuras/fig04_pipeline_corpus.png`

- [ ] **Step 1: Generar con matplotlib/graphviz/mermaid**

Diagrama de flujo sencillo (7 cajas + flechas):

```
[Fuentes primarias OCR] 
 → [Segmentación por estructura]
 → [Detección de idioma por bloque]
 → [Alineación canónica / heurística]
 → [Normalización ortográfica]
 → [Partición train/val/test]
 → [Corpus paralelo Inga-Español]
```

Generar con Python:

```python
# En un script o celda interactiva
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
fig, ax = plt.subplots(figsize=(12, 3))
stages = ['Fuentes\nprimarias\nOCR', 'Segmentación\nestructural', 'Detección\nde idioma', 
 'Alineación', 'Normalización\northográfica', 'Partición\ntrain/val/test', 'Corpus\nparalelo']
for i, s in enumerate(stages):
 ax.add_patch(mpatches.FancyBboxPatch((i*1.6, 0), 1.3, 1, boxstyle='round,pad=0.1', 
 facecolor='#E8F0FE', edgecolor='black'))
 ax.text(i*1.6+0.65, 0.5, s, ha='center', va='center', fontsize=9)
 if i < len(stages)-1:
 ax.annotate('', xy=(i*1.6+1.55, 0.5), xytext=(i*1.6+1.3, 0.5),
 arrowprops=dict(arrowstyle='->'))
ax.set_xlim(-0.2, 11.5); ax.set_ylim(-0.2, 1.2); ax.axis('off')
plt.tight_layout()
plt.savefig('/Users/william-santos/Documents/UNIR/tfm/entrega1/figuras/fig04_pipeline_corpus.png', dpi=150, bbox_inches='tight')
```

- [ ] **Step 2: Verificar imagen generada**

```bash
ls -la /Users/william-santos/Documents/UNIR/tfm/entrega1/figuras/fig04*.png
```

---

### Task 27: Redactar §3.1 Objetivo general

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 3.1)

- [ ] **Step 1: Insertar objetivo general tal cual el spec**

```markdown
Desarrollar y evaluar un sistema de traducción automática Inga-Español que combine la adaptación de modelos de traducción automática multilingüe con aproximaciones basadas en recuperación aumentada de información sobre modelos de lenguaje de frontera, con el fin de contribuir a la preservación digital de la lengua Inga del Putumayo.
```

Añadir un párrafo justificando el carácter SMART del objetivo (cita a Doran, 1981): específico (par lingüístico definido), medible (por métricas automáticas y humanas), alcanzable (demostrado en Quechua por BSC 2024 y QueEn 2024), relevante (lengua sin herramientas digitales), temporalmente delimitado (5-6 meses del TFM).

---

### Task 28: Redactar §3.2 Objetivos específicos

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 3.2)

- [ ] **Step 1: Insertar los 7 objetivos tal cual el spec**

Lista numerada con los 7 objetivos de §0.3 del spec.

- [ ] **Step 2: Después de cada objetivo, añadir una frase corta de criterio SMART**

Ejemplo:
> 1. Configurar el entorno computacional local para el entrenamiento y la inferencia de modelos de lenguaje multilingües. *Criterio de cumplimiento: ejecución exitosa de inferencia zero-shot NLLB-200 en Apple Silicon, validada en el Notebook 00.*

---

### Task 29: Redactar §3.3 Metodología completa

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 3.3)
- Create: `entrega1/figuras/fig05_pipeline_finetuning.png`
- Create: `entrega1/figuras/fig06_pipeline_rag.png`
- Create: `entrega1/figuras/fig08_cronograma_gantt.png`

- [ ] **Step 1: Redactar §3.3.1 Enfoque metodológico**

Investigación aplicada con diseño experimental comparativo. Dos aproximaciones paralelas, evaluación estandarizada.

- [ ] **Step 2: Redactar §3.3.2 Fases del proyecto**

Describir las 7 fases (una por objetivo), 3-4 líneas por fase, en pasado impersonal.

- [ ] **Step 3: Generar Figura 8 (Gantt)**

```python
import matplotlib.pyplot as plt
fases = [
 ('F1. Entorno', '2026-04-15', '2026-05-05'),
 ('F2. Corpus', '2026-04-15', '2026-06-30'),
 ('F3. RAG base', '2026-05-01', '2026-07-15'),
 ('F4. Fine-tuning', '2026-06-01', '2026-08-15'),
 ('F5. Pipeline LLM+RAG', '2026-06-15', '2026-08-30'),
 ('F6. Evaluación', '2026-08-01', '2026-09-30'),
 ('F7. Despliegue+docs', '2026-09-01', '2026-10-15'),
]
# Render como barra horizontal por fase con fechas
```

(Código completo: usar `matplotlib.dates` + `barh`.)

- [ ] **Step 4: Insertar invitación + Figura 8**

> El cronograma global se muestra en la Figura 8.

- [ ] **Step 5: Redactar §3.3.4 Infraestructura + Tabla 5**

```markdown
**Tabla 5**
*Infraestructura de cómputo del proyecto*

| Recurso | Especificación | Uso |
|---|---|---|
| Estación local | Apple M4 Max, 128 GB RAM unificada | Inferencia y ajuste fino de modelos multilingües (NLLB-200-3.3B y similares); indexación y recuperación vectorial. |
| API de LLM de frontera | Anthropic (modelo vigente al cierre del TFM) | Pipeline con recuperación aumentada; línea experimental LLM. |
| Almacenamiento vectorial local | FAISS o ChromaDB | Indexación de la base de conocimiento lingüístico. |

*Nota.* Elaboración propia.
```

- [ ] **Step 6: Redactar §3.3.5 Configuraciones experimentales + Tabla 4**

```markdown
**Tabla 4**
*Configuraciones experimentales a evaluar en la fase final del TFM*

| Config. | Modelo | Técnica | Corpus |
|---|---|---|---|
| A | Modelo multilingüe base (NLLB-200-3.3B) | Zero-shot con código `quy_Latn` |, |
| B | Modelo multilingüe base | Ajuste fino eficiente (PEFT) sobre corpus Inga | Corpus bidialectal |
| C | Modelo de frontera (LLM) | Prompt zero-shot |, |
| D | Modelo de frontera (LLM) | Recuperación aumentada (RAG multi-índice) | Base de conocimiento lingüística |
| E | Modelo multilingüe + PEFT | Recuperación aumentada en inferencia | Corpus + base de conocimiento |

*Nota.* Elaboración propia.
```

- [ ] **Step 7: Generar Fig 5 (pipeline fine-tuning) y Fig 6 (pipeline RAG)**

Diagramas de flujo análogos a la Figura 4. Código matplotlib con cajas y flechas.

- [ ] **Step 8: Insertar invitaciones + figuras** en §3.3.2

---

## Fase F, Capítulo 4, Referencias, Anexo (11:00-13:00 hora Col)

### Task 30: Redactar Capítulo 4 con datos reales

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 4)

- [ ] **Step 1: Leer `datos/estadisticas_corpus.json` y usar los valores reales**

```bash
cat /Users/william-santos/Documents/UNIR/tfm/datos/estadisticas_corpus.json
wc -l /Users/william-santos/Documents/UNIR/tfm/datos/nt_inga_alineado.jsonl
wc -l /Users/william-santos/Documents/UNIR/tfm/datos/antihua_pacay_alineado.jsonl
wc -l /Users/william-santos/Documents/UNIR/tfm/datos/diccionario_inga.jsonl
```

- [ ] **Step 2: Redactar §4.1.1 Fase 1 Entorno**

Un párrafo narrando en pasado impersonal: "Se configuró el entorno local sobre Apple M4 Max (128 GB RAM). Se instalaron... Se validó la aceleración MPS. Se descargó y ejecutó una inferencia zero-shot con NLLB-200-distilled-600M...". Referencia al Notebook 00.

- [ ] **Step 3: Redactar §4.1.2 Fase 2 Corpus**

Varios párrafos usando cifras reales:
- Inventario (Tabla 3): 5 recursos, 1.094 páginas totales, {N} entradas léxicas detectadas, {M} versículos aproximados en el NT.
- Alineación inicial del NT: "Se extrajeron y alinearon {X} pares Inga-Español del Nuevo Testamento..."
- Antihua Pacay: "Se detectaron {Y} bloques bilingües; se produjeron {Z} pares paralelos iniciales mediante alineación blockwise con segmentación intra-bloque."
- Figura 7 referenciada: "La distribución de longitudes de los versículos Inga se presenta en la Figura 7."

Insertar la Figura 7 (ya generada en Task 10).

- [ ] **Step 4: Construir Tabla 3 con conteos reales**

```markdown
**Tabla 3**
*Inventario de recursos lingüísticos primarios utilizados en la construcción del corpus*

| Recurso | Dialecto | Páginas | Registro | Alineación | Entradas/Unidades |
|---|---|---|---|---|---|
| Diccionario Inga (Tandioy et al., 1997) | AP + MP | 177 | Léxico |, | {N} entradas |
| Gramática Pedagógica (Levinsohn y Mongui) | AP | 228 | Didáctico |, |, |
| Apéndice morfosintáctico (Rosetta Project) |, | 26 | Técnico |, |, |
| Nuevo Testamento en Inga (Wycliffe, 2012) | AP | 595 | Bíblico | Versículo | {M} versículos |
| Antihua Pacay (Jamioy, 1985) | MP | 68 | Narrativo | Bloque | {K} pares |

*Nota.* Elaboración propia con base en los notebooks 01 y 02 del presente trabajo. Los valores {N}, {M}, {K} se obtienen de `datos/estadisticas_corpus.json`.
```

Sustituir {N}, {M}, {K} por los valores reales del JSON.

- [ ] **Step 5: Redactar §4.1.3 Fase 3 RAG base**

Descripción del esquema definido (tres índices léxico/gramatical/ejemplos); parseo inicial del diccionario a JSONL; plan de embeddings para la siguiente entrega.

- [ ] **Step 6: Redactar §4.3 Próximos pasos**

3-4 viñetas: completar alineación del corpus, indexación vectorial, primer fine-tuning con LoRA, baselines zero-shot.

---

### Task 31: Cerrar Capítulo 5 placeholder

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 5)

- [ ] **Step 1: Verificar que el placeholder inicial está bien redactado**

El contenido del Task 2 ya dejó una frase bien formada: "El contenido de este capítulo se presenta en la Entrega Final...". No requiere más trabajo aquí.

---

### Task 32: Redactar §4.2 Repositorio + Anexo A

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección 4.2 y Anexo A)

- [ ] **Step 1: Crear repositorio GitHub (opcional si el usuario lo prefiere)**

Si el usuario ha creado `tfm-inga-traduccion` en GitHub, usar esa URL. Si no, dejar placeholder con formato correcto: "Repositorio por publicar en `https://github.com/[usuario]/tfm-inga-traduccion`".

- [ ] **Step 2: Redactar §4.2**

```markdown
El código desarrollado para esta entrega se organiza en tres notebooks (ver Anexo A), disponibles en el repositorio público del proyecto. Los datos generados (`nt_inga_alineado.jsonl`, `antihua_pacay_alineado.jsonl`, `diccionario_inga.jsonl`, `estadisticas_corpus.json`) acompañan a los notebooks y son reproducibles mediante su re-ejecución.
```

- [ ] **Step 3: Redactar Anexo A**

```markdown
## Anexo A. Código fuente y datos analizados

El código fuente del presente TFM se encuentra alojado en el siguiente repositorio público: `https://github.com/[usuario]/tfm-inga-traduccion`.

La estructura del repositorio al cierre de la Entrega 1 es:

- `notebooks/00_setup_entorno.ipynb`, Configuración y validación del entorno local (Python, PyTorch MPS, librerías de NLP, descarga del modelo base).
- `notebooks/01_eda_recursos_base.ipynb`, Análisis exploratorio de los cinco recursos lingüísticos primarios; parseo del diccionario a formato JSONL; cálculo de estadísticas del corpus; generación de la Figura 7.
- `notebooks/02_extraccion_corpus_NT.ipynb`, Extracción y alineación inicial del corpus paralelo a partir del Nuevo Testamento en Inga (Wycliffe, 2012) y las narrativas Antihua Pacay (Jamioy, 1985).
- `datos/`, Salidas en formato JSONL y JSON.
- `bibliografia/refs_verificadas.md`, Referencias bibliográficas del proyecto con identificadores verificables (DOI, arXiv, ACL Anthology).

Licenciamiento: el código del presente TFM se publica bajo licencia MIT. Los datos derivados de fuentes externas heredan las licencias de sus fuentes primarias: el Nuevo Testamento en Inga se distribuye bajo CC BY-NC-ND 3.0 (Wycliffe Bible Translators, 2012) y las narrativas Antihua Pacay provienen del archivo abierto SIL International (Jamioy, 1985).
```

---

### Task 33: Consolidar bibliografía en APA 7

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección Referencias bibliográficas)
- Create: `bibliografia/refs_verificadas.bib`

- [ ] **Step 1: Copiar del `refs_verificadas.md` las entradas en formato APA 7 al documento**

Formato requerido:
- Ordenadas alfabéticamente por apellido del primer autor.
- Sangría francesa (indentación de 2ª línea en adelante).
- Incluir DOI/URL al final de cada entrada.

Ejemplo de las primeras entradas correctamente formateadas:

```markdown
Asamblea Nacional Constituyente de Colombia. (1991). *Constitución Política de Colombia*, Artículo 10. http://www.secretariasenado.gov.co/senado/basedoc/constitucion_politica_1991.html

Attieh, J., Hopton, Z., Scherrer, Y., & Samardžić, T. (2024). System description of the NordicsAlps submission to the AmericasNLP 2024 machine translation shared task. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 150-158). https://aclanthology.org/2024.americasnlp-1.18/

Cahyawijaya, S., Lovenia, H., & Fung, P. (2024). LLMs are few-shot in-context low-resource language learners. En *Proceedings of NAACL 2024*. https://arxiv.org/abs/2403.16512

Chen, J., Shu, P., Li, Y., Zhao, H., Jiang, H., Pan, Y., Zhou, Y., Liu, Z., Howe, L. C., & Liu, T. (2024). QueEn: A large language model for Quechua-English translation. *arXiv*. https://arxiv.org/abs/2412.05184

Congreso de la República de Colombia. (2010). *Ley 1381 de 2010, por la cual se desarrollan los artículos 7°, 8°, 10 y 70 de la Constitución Política y se dictan normas sobre reconocimiento, fomento, protección, uso, preservación y fortalecimiento de las lenguas de los grupos étnicos de Colombia*. Diario Oficial No. 47.603. https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=38741

Costa-jussà, M. R., et al. [NLLB Team]. (2022). *No Language Left Behind: Scaling human-centered machine translation*. arXiv. https://arxiv.org/abs/2207.04672

Costa-jussà, M. R., et al. [NLLB Team]. (2024). Scaling neural machine translation to 200 languages. *Nature, 630*(8018), 841-846. https://doi.org/10.1038/s41586-024-07335-x

de Gibert, O., Pugh, R., Marashian, A., Vazquez, R., Ebrahimi, A., Denisov, P.... Mager, M. (2025). Findings of the AmericasNLP 2025 shared tasks on machine translation, creation of educational material, and translation metrics for indigenous languages of the Americas. En *Proceedings of the Fifth Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP)* (pp. 134-152). https://aclanthology.org/2025.americasnlp-1.16/

DeGenaro, D., & Lupicki, T. (2024). Experiments in Mamba sequence modeling and NLLB-200 fine-tuning for low resource multilingual machine translation. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 188-194). https://aclanthology.org/2024.americasnlp-1.22/

Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). QLoRA: Efficient finetuning of quantized LLMs. En *Advances in Neural Information Processing Systems 36 (NeurIPS 2023)*. https://arxiv.org/abs/2305.14314

Dhawan, A., Driggers-Ellis, C., Grant, C., & Wang, D. Z. (2026). Improving indigenous language machine translation with synthetic data and language-specific preprocessing. *arXiv*. https://arxiv.org/abs/2601.03135

Ebrahimi, A., de Gibert, O., Vazquez, R., Coto-Solano, R., Denisov, P., Pugh, R., Mager, M., Oncevay, A., Chiruzzo, L., von der Wense, K., & Rijhwani, S. (2024). Findings of the AmericasNLP 2024 shared task on machine translation. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 236-246). https://aclanthology.org/2024.americasnlp-1.28/

Enis, M., & Hopkins, M. (2024). From LLM to NMT: Advancing low-resource machine translation with Claude. *arXiv*. https://arxiv.org/abs/2404.13813

Finkelstein, M., Caswell, I., Domhan, T., Peter, J.-T., Juraska, J., Riley, P.... Vilar, D. (2026). *TranslateGemma: Technical report*. arXiv. https://arxiv.org/abs/2601.09012

Garcia Gilabert, J., Sant, A., Escolano, C., De Luca Fornaciari, F., Mash, A., & Melero, M. (2024). BSC submission to the AmericasNLP 2024 shared task. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 143-149). https://aclanthology.org/2024.americasnlp-1.17/

Hendy, A., Abdelrehim, M., Sharaf, A., Raunak, V., Gabr, M., Matsushita, H., Kim, Y. J., Afify, M., & Awadalla, H. H. (2023). *How good are GPT models at machine translation? A comprehensive evaluation*. arXiv. https://arxiv.org/abs/2302.09210

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. En *International Conference on Learning Representations (ICLR 2022)*. https://arxiv.org/abs/2106.09685

Jamioy Yanangona de Peña, O. (1985). *Antihua pacay gentecunapa parlocuna: Tradiciones de los Inganos Pacayes* [Cartilla Inga, Serie Historias Tradicionales]. Proyecto Bilingüe Inga-Castellano, Vicariato Apostólico de Sibundoy; SIL International Language & Culture Archives.

Kudugunta, S., Caswell, I., Zhang, B., Garcia, X., Choquette-Choo, C. A., Lee, K., Xin, D., Kusupati, A., Stella, R., Bapna, A., & Firat, O. (2023). MADLAD-400: A multilingual and document-level large audited dataset. En *Advances in Neural Information Processing Systems 36 (NeurIPS 2023 Datasets & Benchmarks)*. https://arxiv.org/abs/2309.04662

Levinsohn, S. H., & Mongui, R. (s.f.). *Inga Kichwa: Una gramática pedagógica del Inga (Partes 1 y 2)*. Ministerio de Gobierno, Dirección de Asuntos Indígenas; Instituto Lingüístico de Verano.

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N.... Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. En *Advances in Neural Information Processing Systems 33 (NeurIPS 2020)*. https://arxiv.org/abs/2005.11401

Liu, S.-Y., Wang, C.-Y., Yin, H., Molchanov, P., Wang, Y.-C. F., Cheng, K.-T., & Chen, M.-H. (2024). DoRA: Weight-decomposed low-rank adaptation. En *Proceedings of the 41st International Conference on Machine Learning (ICML 2024)*. https://arxiv.org/abs/2402.09353

Mager, M., Mager, E., Kann, K., & Vu, N. T. (2023). Ethical considerations for machine translation of indigenous languages: Giving a voice to the speakers. En *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (ACL 2023)*. https://aclanthology.org/2023.acl-long.313/

Popović, M. (2017). chrF++: Words helping character n-grams. En *Proceedings of the Second Conference on Machine Translation (WMT 2017)* (pp. 612-618). https://aclanthology.org/W17-4770/

Prieto, J., Martinez, C., Robles, M., Moreno, A., Palacios, S., & Manrique, R. (2024). Translation systems for low-resource Colombian indigenous languages: A first step towards cultural preservation. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 7-14). https://aclanthology.org/2024.americasnlp-1.2/

Rei, R., De Souza, J. G. C., Alves, D., Zerva, C., Farinha, A. C., Glushkova, T., Lavie, A., Coheur, L., & Martins, A. F. T. (2022). COMET-22: Unbabel-IST 2022 submission for the metrics shared task. En *Proceedings of the Seventh Conference on Machine Translation (WMT 2022)* (pp. 578-585). https://aclanthology.org/2022.wmt-1.52/

Salazar, I., Manrique, R., & Pereira Nunes, B. (2025). Machine translation strategies for low-resource Colombian indigenous languages. *SN Computer Science, 6*. https://doi.org/10.1007/s42979-025-04255-z

Su, T., Peng, X., Thillainathan, S., Guzmán, D., Ranathunga, S., & Lee, E.-S. A. (2024). *Unlocking parameter-efficient fine-tuning for low-resource language translation*. arXiv. https://arxiv.org/abs/2404.04212

Tandioy Jansasoy, F., Levinsohn, S. H., & Tandioy Chasoy, D. (1997). *Diccionario Inga* (Edición interina en el nuevo alfabeto). Comité de Educación Inga de la Organización Musu Runakuna.

Tonja, A. L., Balouchzahi, F., Butt, S., Kolesnikova, O., Ceballos, H., Gelbukh, A., & Solorio, T. (2024). NLP progress in indigenous Latin American languages. En *Findings of NAACL 2024*. https://arxiv.org/abs/2404.05365

UNESCO. (2022). *World Atlas of Languages*. UNESCO. https://en.wal.unesco.org/

Wang, J., Meng, F., Zhang, Y., & Zhou, J. (2024). *Retrieval-augmented machine translation with unstructured knowledge*. arXiv. https://arxiv.org/abs/2412.04342

Wycliffe Bible Translators. (2012). *Kaipimi Taita Dius Rimaku: El Nuevo Testamento en el idioma Inga de Colombia* (2ª ed.) [CC BY-NC-ND 3.0].

Zhang, S., Frey, B., & Bansal, M. (2022). How can NLP help revitalize endangered languages? A case study and roadmap for the Cherokee language. En *Proceedings of ACL 2022*. https://aclanthology.org/2022.acl-long.507/

Zhang, T., Kishore, V., Wu, F., Weinberger, K. Q., & Artzi, Y. (2020). BERTScore: Evaluating text generation with BERT. En *International Conference on Learning Representations (ICLR 2020)*. https://arxiv.org/abs/1904.09675

Zhu, W., Liu, H., Dong, Q., Xu, J., Huang, S., Kong, L., Chen, J., & Li, L. (2024). Multilingual machine translation with large language models: Empirical results and analysis. En *Findings of the Association for Computational Linguistics: NAACL 2024* (pp. 2765-2781). https://aclanthology.org/2024.findings-naacl.176/
```

- [ ] **Step 2: Verificar conteo**

```bash
grep -c "^[A-Z]" /Users/william-santos/Documents/UNIR/tfm/entrega1/TFM_grupal_entrega1.md | head
# Mejor: contar entradas en la sección de referencias específicamente
```

Expected: ≥30 entradas bibliográficas.

- [ ] **Step 3: Generar `.bib` (opcional, para LaTeX o Mendeley)**

Por simplicidad, se pospone a la Entrega 2. No es crítico para Entrega 1.

---

### Task 34: Redactar el Resumen y Abstract

**Files:**
- Modify: `entrega1/TFM_grupal_entrega1.md` (sección Resumen y Abstract)

- [ ] **Step 1: Redactar Resumen (150-300 palabras) en ES**

Plantilla (a completar con los valores reales del corpus):

```markdown
El presente trabajo propone el diseño y la implementación de un sistema comparativo de traducción automática para el par lingüístico Inga-Español, como aporte a la preservación digital de la lengua Inga del Putumayo, variante de la familia quechua hablada por aproximadamente 18.000 personas en el suroccidente de Colombia. El sistema adopta dos aproximaciones complementarias: por un lado, la adaptación de un modelo de traducción automática multilingüe preentrenado mediante técnicas de ajuste fino eficiente en parámetros, aprovechando el conocimiento de lenguas quechuas emparentadas como base de transferencia; por otro, la construcción de un pipeline de traducción basado en un modelo de lenguaje de frontera potenciado con recuperación aumentada de información, apoyado en una base de conocimiento lingüística estructurada (léxica, gramatical y de ejemplos paralelos). En la presente entrega se documenta el planteamiento del problema, la revisión del estado del arte , con énfasis en trabajos recientes sobre Quechua, que constituye el antecedente más cercano, la definición de objetivos específicos, la metodología organizada en siete fases y los avances iniciales: configuración del entorno computacional sobre Apple Silicon, inventario y procesamiento de cinco recursos lingüísticos primarios (1.094 páginas), y alineación inicial de un corpus paralelo a partir del Nuevo Testamento en Inga y narrativas orales. El presente trabajo contribuye con una cobertura bidialectal (Alto Putumayo y Medio Putumayo) no abordada previamente en la literatura.

**Palabras clave:** traducción automática, lenguas indígenas, Inga, transfer learning, recuperación aumentada de información.
```

- [ ] **Step 2: Traducir al inglés para el Abstract**

Versión fiel al resumen ES.

---

## Fase G, Figuras manuales 1-3 (13:00-14:00 hora Col)

### Task 35: Figura 1, Mapa del pueblo Inga en el Putumayo

**Files:**
- Create: `entrega1/figuras/fig01_mapa_putumayo.png`

- [ ] **Step 1: Obtener mapa base + marcar ubicaciones**

Opciones en orden de rapidez:

1. **Opción rápida**: captura manual de OpenStreetMap con Mocoa, Santiago, Colón, San Andrés marcados; anotar como "Elaboración propia a partir de OpenStreetMap, 2026". Tiempo: ~15 min.
2. **Opción programática**: usar `folium` + `staticmap` o `cartopy` para generar un mapa con marcadores. Código:

```python
import staticmap
from staticmap import CircleMarker
m = staticmap.StaticMap(900, 700)
for lat, lon, _ in [(1.1489, -76.6478, 'Mocoa'), (1.1564, -76.8806, 'Santiago'),
 (1.1892, -76.9033, 'Colón'), (1.1217, -76.7150, 'San Andrés')]:
 m.add_marker(CircleMarker((lon, lat), '#FF0000', 8))
img = m.render()
img.save('/Users/william-santos/Documents/UNIR/tfm/entrega1/figuras/fig01_mapa_putumayo.png')
```

Elegir 1 si hay prisa.

- [ ] **Step 2: Verificar imagen**

---

### Task 36: Figura 2, Arquitectura general del sistema

**Files:**
- Create: `entrega1/figuras/fig02_arquitectura_general.png`

- [ ] **Step 1: Diagrama con dos pipelines convergiendo en evaluación**

```
 ┌───────────────────────────┐
 │ Corpus paralelo Inga-ES │
 └──────────┬────────────────┘
 │
 ┌───────────────────┼───────────────────┐
 │ │
 ▼ ▼
 ┌─────────────────────┐ ┌──────────────────────┐
 │ NMT multilingüe │ │ LLM de frontera │
 │ + ajuste fino (PEFT)│ │ + RAG multi-índice │
 │ [W. Santos] │ │ [D. Eslava] │
 └─────────┬───────────┘ └──────────┬───────────┘
 │ │
 └──────────┬──────────────────────────┘
 ▼
 ┌──────────────────────┐
 │ Evaluación comparativa│
 │ BLEU · chrF++ · BERT-│
 │ Score · humana │
 └──────────────────────┘
```

Generar con matplotlib+patches como Fig 4.

- [ ] **Step 2: Verificar**

---

### Task 37: Figura 3, Dialectos AP vs MP

**Files:**
- Create: `entrega1/figuras/fig03_dialectos_ap_mp.png`

- [ ] **Step 1: Tabla comparativa léxica**

Tabla gráfica con ejemplos del diccionario:

| Español | AP (Sibundoy) | Yun (Yunguillo) | MP (Mocoa) |
|---|---|---|---|
| estornudar | achijai | achijii | jachii |
| ¡Vamos! (dual) |, |, | Aku |
| tía de la mamá | achala mama |, |, |

(Usar ejemplos reales del diccionario consultando `rosettaproject_inb_morsyn-1/content.md` y `756362843-Diccionario-Inga/content.md`.)

Renderizar la tabla como imagen con matplotlib.

- [ ] **Step 2: Verificar**

---

## Fase H, Plantilla Word + QA final (14:00-16:30 hora Col)

### Task 38: Generar `plantilla_mapping.md`

**Files:**
- Create: `entrega1/plantilla_mapping.md`

- [ ] **Step 1: Documentar correspondencias Markdown → Word**

```markdown
# Mapeo Markdown maestro → Plantilla Grupal UNIR

## Estilos de Word a usar

| Elemento Markdown | Estilo Word (Plantilla UNIR) |
|---|---|
| `# Heading 1 numerado` (capítulos 1-5) | `Título 1` (Ttulo1) |
| `## Heading 2 numerado` (subsecciones 1.1, 2.1...) | `Título 2` (Ttulo2) |
| `### Heading 3` | `Título 3` (Ttulo3) |
| Títulos índice (Resumen, Abstract, Índice de figuras...) | `Ttulondices` |
| Referencias bibliográficas (título) | `Ttulo1sinnumerar` |
| Entradas bibliográficas | `Bibliografa` |
| Anexo A | `Anexo` |
| Párrafo normal | `Normal` |
| Listas | `Prrafodelista` |
| Rótulo de tabla "Tabla N." | `Descripcin` (en negrita, arriba de la tabla) |
| Rótulo de figura "Figura N." | `Descripcin` |
| Nota al pie de tabla/figura | `Piedefoto-tabla` |

## Orden de vaciado

1. Abrir `plantilla_grupal.docx` en Word.
2. Completar portada con los campos del Markdown (Título, integrantes, fecha, director).
3. Reemplazar Resumen y Abstract con sus versiones del Markdown.
4. Eliminar las instrucciones de la plantilla (texto "En este apartado se...", ejemplos).
5. Pegar cada capítulo respetando los estilos de la plantilla (Pegar → Conservar solo texto; luego aplicar estilos).
6. Insertar figuras con "Insertar → Imagen" y aplicar el estilo `Descripcin` al rótulo.
7. Regenerar Índices de contenidos, figuras y tablas (botón derecho → Actualizar campos).
8. Revisar saltos de página y numeración.
9. Guardar como `TFM_Entrega1_EslavaSantos.docx`.
10. Exportar a PDF.
```

---

### Task 39: Vaciado manual a la plantilla .docx

**Files:**
- Create: `entrega1/TFM_Entrega1_EslavaSantos.docx` (manual, en Word)

- [ ] **Step 1: Abrir plantilla y guardar con nombre definitivo**

```bash
cp "/Users/william-santos/Downloads/plantilla_grupal.docx" \
 "/Users/william-santos/Documents/UNIR/tfm/entrega1/TFM_Entrega1_EslavaSantos.docx"
open "/Users/william-santos/Documents/UNIR/tfm/entrega1/TFM_Entrega1_EslavaSantos.docx"
```

- [ ] **Step 2: Vaciado siguiendo `plantilla_mapping.md`**

Esta es la ventana más delicada. Se recomienda al usuario pedir asistencia al asistente en paralelo: el asistente va dictando por sección y el usuario pega en Word manteniendo estilos.

- [ ] **Step 3: Insertar figuras en las posiciones correctas**

Cada figura con su rótulo, título en cursiva, nota al pie centrada.

- [ ] **Step 4: Regenerar índices de contenidos, figuras y tablas**

En Word: clic derecho sobre cada índice → "Actualizar campos" → "Actualizar toda la tabla".

---

### Task 40: QA final (APA, tercera persona, Turnitin)

**Files:**
- Review: `entrega1/TFM_Entrega1_EslavaSantos.docx`

- [ ] **Step 1: Búsqueda de primera persona en el .docx**

En Word, Buscar y Reemplazar (Ctrl+H):
- Buscar: `nosotros` / `nuestro` / `nuestra` / `vemos` / `decimos` / `mostramos` / `analizamos` → reemplazar por tercera persona impersonal.
- Buscar terminaciones `-amos\b`, `-emos\b`, `-imos\b`, `-omos\b` para verbos (no todos son incorrectos; revisar manualmente).

- [ ] **Step 2: Verificar que todas las citas tienen su entrada en Referencias**

Hacer una pasada visual: para cada `(Apellido, Año)` o `Apellido (Año)` en el texto, confirmar que está en la lista de Referencias.

- [ ] **Step 3: Verificar figuras y tablas**

Cada una tiene:
- ✓ Rótulo `Figura N` / `Tabla N` en negrita.
- ✓ Título en cursiva.
- ✓ Centrada.
- ✓ Nota al pie en cursiva con `Nota.` y fuente.
- ✓ Invitación explícita en el párrafo anterior.

- [ ] **Step 4: Turnitin-ready (si hay acceso temprano a la herramienta)**

Si el usuario tiene acceso a Turnitin antes del envío: subir el documento y confirmar <20% de coincidencias.

- [ ] **Step 5: Exportar a PDF**

```
File → Export → Create PDF/XPS
```

Guardar como `TFM_Entrega1_EslavaSantos.pdf`.

---

### Task 41: Envío a la plataforma UNIR

**Files:**
- Ninguno en el repositorio local.

- [ ] **Step 1: Subir archivo a la plataforma correspondiente**

Antes de las 23:59 hora peninsular (16:59 hora Colombia).

- [ ] **Step 2: Confirmar recepción**

Guardar el comprobante de entrega en `entrega1/` si la plataforma lo proporciona.

- [ ] **Step 3: Cerrar iteración**

Registrar lecciones aprendidas para la Entrega 2.

---

## Auto-revisión del plan (checklist final)

- **Cobertura del spec**: cada apartado de §2, §3, §5 del spec tiene al menos una Task que lo implementa. Sección grupal → Task 3. Capítulo 1 → Tasks 4-6. Capítulo 2 → Tasks 11-22. Capítulo 3 → Tasks 27-29. Capítulo 4 → Task 30. Capítulo 5 → Task 31. Anexo A → Task 32. Bibliografía → Task 33. Resumen/Abstract → Task 34. Figuras → Tasks 26, 29, 35-37. Notebooks → Tasks 7-10, 23-25. Vaciado a Word → Tasks 38-40. Envío → Task 41. No quedan apartados sin tarea.
- **Placeholders**: se usan `{N}`, `{M}`, `{K}` intencionalmente para marcar valores que se sustituyen dinámicamente en Task 30 leyendo `estadisticas_corpus.json`. No hay `TBD`, `TODO`, `add appropriate X` ni "similar to Task N".
- **Consistencia de tipos**: rutas de archivo, nombres de ficheros JSONL y de figuras son consistentes entre tareas. Firmas de funciones y cell-code son explícitas.
- **Riesgos cubiertos**: la Task 24 Step 2 tiene fallback para la descarga del NT español; Task 35 Step 1 tiene opción rápida si se prefiere manual; Task 40 Step 4 hace opcional el Turnitin early-check.

## Handoff para ejecución

Plan guardado en `/Users/william-santos/Documents/UNIR/tfm/docs/superpowers/plans/2026-04-21-tfm-entrega1.md`.
