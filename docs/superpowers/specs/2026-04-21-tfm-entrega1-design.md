# TFM Entrega 1, Diseño del documento (spec)

**Proyecto**: Trabajo Fin de Máster en Inteligencia Artificial (UNIR), Traducción automática Inga-Español.
**Fecha de elaboración del spec**: 2026-04-21.
**Fecha límite de entrega**: 2026-04-22, 23:59 hora peninsular (≈16:59 hora Colombia).
**Estado**: aprobado por el usuario tras brainstorming interactivo; listo para `writing-plans`.

---

## 0. Antecedentes y decisiones ya tomadas

Antes de esta entrega existe una propuesta aprobada con retroalimentación del director de TFM (Víctor David Larco Torres). Del brainstorming con el usuario se consolidaron las siguientes decisiones:

### 0.1 Equipo y asignación

El TFM es grupal de **dos integrantes** (se descartó el tercero):

- **William Santos (Mocoa, Putumayo)**, `william@veleiro.ai`. Contribución técnica: adaptación de modelos de traducción multilingüe mediante ajuste fino eficiente en parámetros. Rol adicional: acceso comunitario y curación del corpus (infraestructura compartida).
- **Daniel Eslava (Cali)**, contribución técnica: sistema de traducción basado en LLM de frontera con recuperación aumentada.

Director del TFM: **Víctor David Larco Torres**. Tipo de trabajo (según plantilla grupal UNIR): **Tipo 1, Piloto experimental**.

> **Restricción del director citada en memoria**: el trabajo comunitario/corpus por sí solo NO es contribución técnica válida. Cada integrante debe tener una contribución que, individualmente, podría constituir un TFM independiente (requisito literal de la plantilla UNIR). Por eso la partición: cada quien es "dueño" de un modelo/técnica; el corpus es infraestructura distribuida.

### 0.2 Alcance de la Entrega 1

Se adopta la **Opción C (máximo-pragmática, ≈35% de avance)** decidida en la Pregunta 2 del brainstorming:

- Capítulos 1, 2, 3 completos y sólidos.
- Capítulo 4 como **esqueleto redactado con evidencias reales** de avance.
- Notebook paralelo "A-extendido" (setup + EDA + extracción/alineación de corpus inicial).
- Cero código pegado en el documento; el código vive en notebooks referenciados.

Se descartó Opción A (estricta, sólo 25%) y Opción B (ambiciosa, 50% con fine-tuning real). Motivo: el tiempo disponible (~20 h efectivas) no permite llegar a B sin comprometer calidad de capítulos 1-3; A deja un punto ciego ante la pregunta del director "¿avanzaron en lo técnico?".

### 0.3 Objetivos del TFM (reescritos neutros de tecnología)

Los objetivos de la propuesta original amarraban la redacción a nombres comerciales (Claude Opus 4.5, NLLB-200, LoRA) que envejecen mal (Claude ya va en 4.7 al momento del brainstorming). Decisión firme: los objetivos se formulan con lenguaje abstracto; los modelos concretos viven en la sección de metodología y en el capítulo de desarrollo. Si un modelo cambia, sólo se actualizan esas secciones, los objetivos sobreviven.

**Objetivo general**
> Desarrollar y evaluar un sistema de traducción automática Inga-Español que combine la adaptación de modelos de traducción automática multilingüe con aproximaciones basadas en recuperación aumentada de información sobre modelos de lenguaje de frontera, con el fin de contribuir a la preservación digital de la lengua Inga del Putumayo.

**Objetivos específicos** (siete, en orden técnico: entorno → datos → conocimiento → modelos → evaluación → implementación)

1. Configurar el entorno computacional local para el entrenamiento y la inferencia de modelos de lenguaje multilingües.
2. Construir un corpus paralelo Inga-Español a partir de fuentes orales, textuales y recursos de lenguas quechuas emparentadas.
3. Diseñar e implementar una base de conocimiento lingüístico del Inga (léxica, gramatical y de ejemplos paralelos) con técnicas de recuperación híbrida.
4. Adaptar un modelo de traducción automática multilingüe preentrenado mediante técnicas de ajuste fino eficiente en parámetros.
5. Implementar un pipeline de traducción basado en un modelo de lenguaje de frontera con recuperación aumentada de información.
6. Evaluar comparativamente ambas aproximaciones mediante métricas automáticas estándar y validación cualitativa con hablantes nativos.
7. Desplegar el sistema resultante en un entorno local replicable y documentar el marco metodológico como aporte reutilizable para otras lenguas indígenas.

### 0.4 Bibliografía verificada

Fruto del agente de investigación despachado durante el brainstorming, se detectaron **5 referencias con autores alucinados en la propuesta original** (papers reales, autores inventados): QueEn (autor real Chen et al., no "Llerena"); Springer 2025 (Salazar et al., no "Prieto"); arXiv:2601.03135 (Dhawan et al. 2026, no "Ortega 2025"); TranslateGemma (Finkelstein et al., no "Jara-Roa"); Mali-Claude (Dembele et al., no "Diagne"). Se corrigieron todas y se complementaron con 19 referencias nuevas verificadas por DOI/arXiv/ACL. Lista completa en `bibliografia/refs_verificadas.md`.

**Regla operativa desde este spec**: ninguna cita entra al documento sin URL verificable abierta al momento de escribirse.

### 0.5 Recursos locales OCR-extraídos (corpus primario)

El usuario confirmó cinco recursos extraídos a Markdown mediante `mistral-ocr-extractor` en `/Users/william-santos/Documents/UNIR/mistral-ocr-extractor/output/inga-kichwa/`:

| Recurso | Dialecto | Páginas | Registro | Alineación |
|---|---|---|---|---|
| Diccionario Inga (Tandioy/Levinsohn/Tandioy/Maffla, 1997) | AP + MP (marcado) | 177 | Léxico |, |
| Gramática Pedagógica del Inga (Levinsohn & Mongui) | AP principal | 228 | Didáctico |, |
| Apéndice morfosintáctico (Rosetta Project) |, | 26 | Técnico |, |
| Nuevo Testamento en Inga (Wycliffe 2012, CC BY-NC-ND 3.0) | AP (probable) | 595 | Bíblico | Versículo |
| Antihua Pacay Gentecunapa Parlocuna (Jamioy 1985, SIL) | **MP (Mocoa)** | 68 | **Narrativo oral** | Bloque |

**Total: 1.094 páginas** de material primario. Este inventario permite que el TFM arranque sin depender de conseguir corpus externos, punto fuerte documentable en el Capítulo 4.

**Cobertura dialectal bidialectal (AP + MP)**: el proyecto tiene cobertura explícita de ambos dialectos principales del Inga. Punto original sobre Prieto et al. (2024), que no distingue dialectos.

---

## 1. Arquitectura de archivos del entregable

```
/Users/william-santos/Documents/UNIR/tfm/
├── entrega1/
│ ├── TFM_grupal_entrega1.md # documento maestro en Markdown
│ ├── plantilla_mapping.md # mapeo de estilos Markdown → Word
│ └── figuras/ # PNG/SVG finales numeradas
├── notebooks/
│ ├── 00_setup_entorno.ipynb
│ ├── 01_eda_recursos_base.ipynb
│ └── 02_extraccion_corpus_NT.ipynb
├── bibliografia/
│ ├── refs_verificadas.md # ya existe (33 entradas)
│ └── refs_verificadas.bib # por generar
├── datos/
│ ├── nt_inga_alineado.jsonl
│ ├── antihua_pacay_alineado.jsonl
│ ├── diccionario_inga.jsonl
│ └── estadisticas_corpus.json
├── docs/superpowers/specs/
│ └── 2026-04-21-tfm-entrega1-design.md # este archivo
├── propuesta_tfm.md # existente, no modificar
├── propuesta_formulario.md # existente
└── latex/ # existente, referencia
```

Salida final al entregar: el usuario vacía el Markdown en la plantilla oficial `.docx` (guiado por `plantilla_mapping.md`) y genera el PDF.

---

## 2. Estructura del documento (mapeo a Plantilla Grupal UNIR)

La plantilla oficial en `/Users/william-santos/Downloads/plantilla_grupal.docx` exige:

```
Portada
Resumen (ES, 150-300 palabras) + Palabras clave (3-5)
Abstract (EN, 150-300 palabras) + Keywords (3-5)
Índice de contenidos
Índice de figuras
Índice de tablas
Organización del trabajo en grupo
 - Partes que aborda el TFE
 - Distribución y estructura de la memoria (Tabla 1)
 - Mecanismos de coordinación empleados
1. Introducción
 1.1 Motivación
 1.2 Planteamiento del trabajo
 1.3 Estructura del trabajo
2. Contexto y estado del arte
 2.1 Contexto del problema
 2.2 Estado del arte
 2.3 Conclusiones
3. Objetivos concretos y metodología de trabajo
 3.1 Objetivo general
 3.2 Objetivos específicos
 3.3 Metodología del trabajo
4. Desarrollo específico de la contribución
5. Conclusiones y trabajo futuro
 5.1 Conclusiones
 5.2 Líneas de trabajo futuro
Referencias bibliográficas
Anexo A. Código fuente y datos analizados
```

Meta de longitud para Entrega 1: ~25 páginas (excluyendo portada, índices, anexos).

---

## 3. Plan de contenido detallado por sección

### 3.1 Front matter

- **Portada** con los campos de la plantilla: UNIR / Escuela Superior de Ingeniería y Tecnología / Máster Universitario en Inteligencia Artificial / Título / "Trabajo fin de estudio presentado por:" Daniel Eslava y William Santos (orden alfabético por apellido) / Tipo de trabajo: Piloto experimental / Director: Víctor David Larco Torres / Fecha: 22 de abril de 2026.
- **Título provisional** propuesto (SMART, neutro de tecnología):
 > *"Diseño e implementación de un sistema comparativo de traducción automática Inga-Español mediante ajuste fino de modelos multilingües y recuperación aumentada de información sobre modelos de lenguaje de frontera"*
- **Resumen ES** (150-300 palabras): síntesis del qué, cómo y para qué. Se redacta al final (cuando los demás capítulos estén congelados). Plantilla de borrador:
 - ¿Qué? Sistema comparativo de traducción Inga-Español.
 - ¿Cómo? Dos aproximaciones: fine-tuning de NMT multilingüe con transferencia desde Quechua; y LLM de frontera con RAG lingüístico.
 - ¿Para qué? Preservación digital; evidencia metodológica para lenguas indígenas de muy bajos recursos.
- **Abstract EN**: traducción fiel del resumen.
- **Palabras clave**: traducción automática, lenguas indígenas, Inga, transfer learning, recuperación aumentada de información.
- **Keywords**: machine translation, indigenous languages, Inga (Quechua), transfer learning, retrieval-augmented generation.

### 3.2 Organización del trabajo en grupo (~2 páginas)

**Partes que aborda el TFE**, dos contribuciones técnicas autocontenidas + infraestructura compartida:

1. **William Santos (Mocoa)**, Adaptación de un modelo de traducción automática multilingüe preentrenado al par Inga-Español mediante técnicas de ajuste fino eficiente en parámetros, aprovechando el conocimiento de lenguas quechuas emparentadas como puente de transferencia. Incluye la curación del corpus bidialectal AP/MP.
2. **Daniel Eslava (Cali)**, Diseño e implementación de un sistema de traducción basado en un modelo de lenguaje de frontera potenciado con aumentación por recuperación de información, utilizando una base de conocimiento lingüístico del Inga estructurada en índices (léxico, gramatical, ejemplos paralelos). Incluye el framework de evaluación comparativa.
3. **Infraestructura compartida**, construcción y curación del corpus paralelo, normalización ortográfica, validación con hablantes nativos.

**Tabla 1, Distribución y estructura de la memoria**

| Apartado | Responsables |
|---|---|
| Introducción | William Santos, Daniel Eslava |
| Contexto y estado del arte | William Santos (NMT + PEFT), Daniel Eslava (LLMs + RAG) |
| Objetivos y metodología | William Santos, Daniel Eslava |
| Marco normativo | William Santos (comunitario), Daniel Eslava (licencias de datos) |
| Desarrollo, Fine-tuning NMT | William Santos |
| Desarrollo, Pipeline LLM+RAG | Daniel Eslava |
| Desarrollo, Corpus e infraestructura | William Santos, Daniel Eslava |
| Conclusiones | William Santos, Daniel Eslava |

**Mecanismos de coordinación**
- Repositorio Git compartido en GitHub (`tfm-inga-traduccion`, por crear).
- Gestión de tareas mediante GitHub Projects.
- Reuniones síncronas semanales por videoconferencia.
- Gestor bibliográfico compartido (Zotero o Mendeley) con entradas verificadas.
- Revisión cruzada por pull requests.

### 3.3 Capítulo 1, Introducción (~4 páginas)

**1.1 Motivación** (tiempo presente)
Tres ejes argumentales:
- Lengua Inga como sistema cultural vivo en Putumayo (~18.000 hablantes, dialectos AP y MP), en desplazamiento progresivo frente al español.
- Brecha digital: ausencia de traductores automáticos; ausencia en Google Translate, DeepL; recursos digitales escasos y sin integración computacional.
- Oportunidad tecnológica: avances recientes (2022-2026) en NMT multilingüe, transfer learning desde Quechua, LLMs con habilidades zero-shot y RAG.

Citas obligatorias: UNESCO Atlas (2022), Constitución de Colombia (1991) Art. 10, Ley 1381 (2010), Tonja et al. (2024), Mager et al. (2023), Zhang et al. (2022) Cherokee, Prieto et al. (2024).

**1.2 Planteamiento del trabajo** (tiempo presente)
- Problema técnico: producir un sistema de traducción Inga-Español utilizable para una lengua con < 5.000 pares paralelos publicados antes de este TFM.
- Pregunta de investigación: *¿cuál aproximación, ajuste fino de un modelo NMT multilingüe vs. uso de un LLM de frontera con recuperación aumentada, es más efectiva para traducir Inga-Español cuando los datos son extremadamente escasos?*
- Propuesta de solución: desarrollar ambas aproximaciones en paralelo, evaluarlas con métricas automáticas y humanas, identificar trade-offs.
- Alcance: piloto experimental local (no sistema de producción). Dos dialectos (AP y MP). Corpus ~8-10K pares al cierre del TFM.

**1.3 Estructura del trabajo** (tiempo presente)
Un párrafo por capítulo describiendo brevemente su contenido.

### 3.4 Capítulo 2, Contexto y estado del arte (~7 páginas, el más denso)

**2.1 Contexto del problema** (presente para hechos científicos; pasado para estudios previos)

- 2.1.1 **La lengua Inga y su situación en el Putumayo**. Familia quechua (QI; quechua periférico), aglutinante, orden SOV. Dialectos: AP (Alto Putumayo, Valle de Sibundoy: San Andrés, Santiago, Colón) y MP (Medio Putumayo, Mocoa, Condagua, Yunguillo, Guayuyaco). Datos demográficos. Fuentes: Diccionario Inga (1997) como testimonio primario; Tandioy Jansasoy (IU).
- 2.1.2 **Marco legal-político en Colombia y contexto internacional**. Constitución 1991 Art. 10 (oficialidad de lenguas de grupos étnicos en sus territorios). Ley 1381 de 2010 (protección, fomento y derechos lingüísticos). UNESCO World Atlas of Languages (2022) y Década Internacional de las Lenguas Indígenas 2022-2032.
- 2.1.3 **NMT de bajos recursos: fundamentos**. Definición. Taxonomía de enfoques (zero-shot, few-shot, transfer learning, data augmentation). Breve referencia a evolución (SMT → NMT → Transformer → LLMs). Citas: NLLB Team (2022, 2024), Costa-jussà et al. (2022).
- 2.1.4 **Transfer learning y RAG: definiciones**. Transfer learning en NMT: cross-lingual transfer, parameter-efficient fine-tuning. RAG: arquitectura clásica (Lewis et al., 2020) y aplicación a traducción (Wang et al., 2024 RAGtrans).

**2.2 Estado del arte** (pasado para estudios previos)

- 2.2.1 **NLP para lenguas indígenas de América Latina**. Panorama general: Tonja et al. (2024). Shared tasks: AmericasNLP 2024 (Ebrahimi et al.), AmericasNLP 2025 (de Gibert et al.). Progresos y retos.
- 2.2.2 **Traducción de lenguas colombianas**. Prieto et al. (2024), primer corpus paralelo Inga documentado. Salazar, Manrique y Pereira Nunes (2025).
- 2.2.3 **NMT para Quechua: el caso cercano al Inga**. Chen et al. (2024) QueEn, LoRA + RAG sobre LLM para Quechua-Inglés, +1.5 a +17.6 BLEU. Garcia Gilabert et al. (2024) BSC, ganador ES→Quechua y ES→Guaraní en AmericasNLP 2024 usando LoRA sobre NLLB con 14.2% de parámetros entrenados (pieza fundamental para justificar la metodología del TFM). Attieh et al. (2024) NordicsAlps, mejor chrF++ con tokenización byte-level. DeGenaro y Lupicki (2024), Mamba vs. NLLB fine-tuning. Dhawan et al. (2026), augmentación sintética y preprocesamiento específico por lengua.
- 2.2.4 **LLMs de frontera para traducción**. Enis y Hopkins (2024), "resource efficiency" de Claude para lenguas de bajos recursos. Hendy et al. (2023), GPT vs. NMT dedicado. Zhu et al. (2024), brecha LLM vs. NLLB en bajos recursos. Cahyawijaya, Lovenia y Fung (2024), few-shot ICL para bajos recursos.
- 2.2.5 **RAG aplicado a traducción**. Lewis et al. (2020), RAG original. Wang et al. (2024), RAGtrans, primer benchmark RAG-MT. Chen et al. (2024), RAG + LoRA.
- 2.2.6 **Técnicas PEFT**. Hu et al. (2022) LoRA. Dettmers et al. (2023) QLoRA. Liu et al. (2024) DoRA. Su et al. (2024), comparación empírica de 8 métodos PEFT para LRL-NMT.
- 2.2.7 **Modelos base candidatos**, **Tabla 2**: comparativa de NLLB-200 (Costa-jussà et al. 2022/2024), MADLAD-400 (Kudugunta et al. 2023) y TranslateGemma (Finkelstein et al. 2026). Columnas: parámetros, lenguas cubiertas, soporte de quechua, licencia, arquitectura, tamaño ejecutable en M4 Max 128GB.

**2.3 Conclusiones del capítulo**
Síntesis: combinación fine-tuning eficiente + RAG es la estrategia más prometedora dada (a) la evidencia acumulada en Quechua, (b) los ~5-10K pares disponibles tras la construcción del corpus bidialectal, y (c) las restricciones del hardware local (M4 Max). Justificación técnica de las elecciones que se detallarán en Capítulo 3.

### 3.5 Capítulo 3, Objetivos concretos y metodología (~5 páginas)

**3.1 Objetivo general**, el reescrito en § 0.3.

**3.2 Objetivos específicos**, los siete de § 0.3 con una justificación breve SMART para cada uno (específico, medible, alcanzable, relevante, tempotalmente delimitado). Mencionar a Doran (1981) como respalda la plantilla.

**3.3 Metodología del trabajo** (pasado impersonal al describir qué se hará)

- 3.3.1 Enfoque metodológico: investigación aplicada con diseño experimental comparativo.
- 3.3.2 **Siete fases** (correspondencia 1:1 con los objetivos específicos de §3.2):
 - Fase 1, Configuración del entorno computacional.
 - Fase 2, Construcción del corpus paralelo Inga-Español.
 - Fase 3, Diseño e implementación de la base de conocimiento para RAG.
 - Fase 4, Adaptación del modelo de traducción multilingüe (ajuste fino eficiente).
 - Fase 5, Implementación del pipeline LLM + RAG.
 - Fase 6, Evaluación comparativa (automática + humana).
 - Fase 7, Despliegue local + documentación metodológica.
- 3.3.3 Cronograma, **Figura 8** (Gantt) distribuyendo las seis fases entre abril y la entrega final.
- 3.3.4 Infraestructura de cómputo, **Tabla 5** (M4 Max 128GB para modelos locales + API Anthropic para la línea LLM).
- 3.3.5 **Tabla 4**, Configuraciones experimentales a evaluar (4-6 configuraciones comparativas).

### 3.6 Capítulo 4, Desarrollo específico (~3 páginas, esqueleto con avances)

**4.1 Estado de avance al cierre de la Entrega 1**

- 4.1.1 Fase 1 (Entorno), entorno local preparado con Transformers/PEFT/Accelerate; NLLB-200-distilled-600M validado en Apple Silicon (MPS); validación de viabilidad computacional.
- 4.1.2 Fase 2 (Corpus), inventario cuantificado (Tabla 3, 1.094 páginas); EDA preliminar (Figura 7: distribución de longitudes del NT Inga); primera alineación del Nuevo Testamento (N versículos Inga-Español producidos por el notebook 02); alineación blockwise inicial de Antihua Pacay (M pares).
- 4.1.3 Fase 3 (RAG base), esquema de tres índices definido; primer parseo del diccionario como entradas léxicas estructuradas (generado por notebook 01).

**4.2 Anexos de código**
Referencia al repositorio GitHub (URL) y al listado de notebooks con su propósito.

**4.3 Próximos pasos hacia la Entrega 2**
Completar las Fases 1 y 2; iniciar Fase 3 experimental (primer fine-tuning con LoRA sobre el corpus disponible); baselines zero-shot de NLLB y Claude.

### 3.7 Capítulo 5, Conclusiones y trabajo futuro (~0.5 página)

Placeholder breve: *"El contenido de este capítulo se presenta en la Entrega Final, una vez ejecutadas las Fases 4 y 5."*

### 3.8 Referencias bibliográficas

33 entradas en APA 7 según `bibliografia/refs_verificadas.md`, ordenadas alfabéticamente por apellido del primer autor, con sangría francesa.

### 3.9 Anexo A, Código fuente y datos

URL del repositorio GitHub del proyecto (a crear). Listado de notebooks y su función. Declaración de licenciamiento (MIT para el código; los datos heredan licencias de fuentes primarias).

---

## 4. Plan de figuras y tablas

### Figuras (8)

| Nº | Título | Capítulo | Origen |
|---|---|---|---|
| 1 | Ubicación del pueblo Inga en el departamento del Putumayo | 1.1 | Mapa base OpenStreetMap + edición |
| 2 | Arquitectura general del sistema propuesto | 1.2 | Diagrama con Mermaid/draw.io |
| 3 | Variantes dialectales del Inga: Alto Putumayo vs. Medio Putumayo | 2.1.1 | Mapa + tabla de diferencias léxicas (del diccionario) |
| 4 | Pipeline de construcción del corpus | 3.3 | Diagrama de flujo |
| 5 | Pipeline de fine-tuning de NMT con adaptación eficiente | 3.3 | Diagrama (contribución W. Santos) |
| 6 | Pipeline de traducción LLM + RAG multi-índice | 3.3 | Diagrama (contribución D. Eslava) |
| 7 | Distribución de longitudes de oración en el Nuevo Testamento Inga | 4.1 | Notebook 02 (matplotlib) |
| 8 | Cronograma Gantt del TFM | 3.3.3 | Plantuml o matplotlib |

### Tablas (5)

| Nº | Título | Capítulo |
|---|---|---|
| 1 | Organización del trabajo en grupo | Sección grupal |
| 2 | Comparativa de modelos base multilingües candidatos | 2.2.7 |
| 3 | Inventario de recursos locales disponibles para el corpus | 4.1.1 |
| 4 | Configuraciones experimentales a evaluar | 3.3.5 |
| 5 | Infraestructura de cómputo del proyecto | 3.3.4 |

Todas las figuras y tablas siguen norma APA 7: identificador en negrita (`Figura N` / `Tabla N`), título en cursiva debajo, centradas, `Nota.` al pie en cursiva con fuente o "Elaboración propia".

---

## 5. Plan de notebooks (alcance "A-extendido")

### 5.1 `00_setup_entorno.ipynb`

- Verifica Python 3.11, crea entorno `uv` o `venv`.
- Instala: `transformers>=4.40`, `peft`, `accelerate`, `sentence-transformers`, `sacrebleu`, `datasets`, `anthropic`, `sentencepiece`, `protobuf`, `matplotlib`, `pandas`, `numpy`, `tqdm`.
- Valida MPS (PyTorch + Apple Silicon).
- Descarga `facebook/nllb-200-distilled-600M` como modelo pequeño para primeras pruebas.
- Prueba una inferencia de muestra (texto en Español → Quechua Ayacucho `quy_Latn`) para validar que todo funciona end-to-end.

### 5.2 `01_eda_recursos_base.ipynb`

- Parsea los 5 recursos OCR-extraídos (reads Markdown con frontmatter).
- Cuenta para cada recurso: páginas, tokens estimados, oraciones estimadas, caracteres.
- Para el diccionario: extrae entradas parseando el formato SIL (lema + abreviatura gramatical + glosa ES + dialecto); produce `datos/diccionario_inga.jsonl`.
- Para la gramática y apéndice morfosintáctico: extrae reglas como fragmentos atómicos (por sufijo, por caso gramatical, por patrón).
- Genera Tabla 3 (inventario) y Figura 7 (distribución de longitudes del NT).
- Guarda `datos/estadisticas_corpus.json`.

### 5.3 `02_extraccion_corpus_NT.ipynb`

- **Parte A (NT)**: parsea el Markdown de `00-WNTinb-web/content.md` segmentando por libro/capítulo/versículo (los delimitadores son visibles en el Markdown). Alinea con un Nuevo Testamento en español **efectivamente de dominio público**: opciones viables son **Reina-Valera 1909** (globalmente en dominio público), Reina-Valera 1865, o la Biblia del Oso (1569/1602). Se descarta RV 1960 (aún protegida por Sociedades Bíblicas Unidas). Salida: `datos/nt_inga_alineado.jsonl` (una entrada por versículo con `{libro, capitulo, versiculo, texto_inga, texto_es}`).
- **Parte B (Antihua Pacay)**: parsea `inj-AntihuaPacay/content.md`. Detecta bloques por idioma (heurística: densidad de sufijos aglutinantes típicos del Inga: `-cuna`, `-manda`, `-hua`, `-spa`, `-pac`, `-pi`, `-ta`; vs. palabras comunes del español). Empareja bloque Inga N con bloque Español N. Para cada par, segmenta en oraciones y alinea intra-bloque con heurística Gale-Church (alineación por longitud). Salida: `datos/antihua_pacay_alineado.jsonl`.
- Reporta: número de versículos alineados, número de bloques detectados, número de oraciones paralelas aproximadas, longitud media en tokens.

**Entregables tangibles que se citan en el Capítulo 4.1.1**, los conteos concretos generados por estos notebooks se insertan textualmente en el documento el 22 de abril antes de cerrar.

---

## 6. Cronograma de ejecución 24 horas (hora Colombia UTC-5)

La entrega debe llegar a las 23:59 hora peninsular española (UTC+2), equivalente a **16:59 Colombia**.

| Ventana Col | Bloque | Qué se produce | Responsable |
|---|---|---|---|
| 20:00-22:00 (21 abr) | Spec aprobado + writing-plans + Cap 1 Introducción + Front matter base | Borrador Cap 1 en Markdown | Asistente |
| 22:00-00:00 | Cap 2 parte I (Contexto 2.1) | Borrador 2.1.1-2.1.4 | Asistente |
| 00:00-02:00 | Notebooks 00 y 01 | Entorno validado; diccionario parseado; Tabla 3 y Fig 7 listas | Asistente |
| 02:00-06:00 | Cap 2 parte II (Estado del arte 2.2 + Conclusiones 2.3) | Borrador 2.2.1-2.2.7 + 2.3 completo; Tabla 2 | Asistente |
| 06:00-09:00 | Notebook 02 completo (NT + Antihua Pacay) | `nt_inga_alineado.jsonl`, `antihua_pacay_alineado.jsonl`, cifras para Cap 4 | Asistente |
| 09:00-11:00 | Cap 3 completo + Figuras 4, 5, 6, 8 + Tablas 4, 5 | Borrador Cap 3 cerrado | Asistente |
| 11:00-13:00 | Cap 4 esqueleto + Sección grupal + Tabla 1 + Bibliografía final | Documento Markdown completo | Asistente |
| 13:00-15:00 | Vaciado a Plantilla Grupal `.docx` + Figuras 1, 2, 3 (diagramas manuales) | Documento Word final | Usuario + asistencia |
| 15:00-16:30 | QA final: norma APA, tercera persona, Turnitin-ready | Entregable firmado | Ambos |
| **16:30 Col (23:30 peninsular)** | **Envío** |, |, |

Holgura neta: ~30 minutos. **Punto crítico**: 13:00, si el Markdown maestro no está congelado a esa hora, el vaciado a Word se complica.

**Principio de priorización ante retrasos**: si algo se sacrifica, se sacrifica primero el *completeness* del Capítulo 4 (se deja más esquelético), segundo la riqueza visual de las figuras 1-3 (se sustituyen por descripciones textuales si es necesario), nunca se sacrifica Capítulo 2 ni Referencias.

---

## 7. Normas de forma aplicables (checklist Turnitin-ready)

- **Redacción estrictamente en tercera persona impersonal.** Prohibido: "nosotros", "nuestro", "-amos/-emos/-imos/-omos". Usar "se observa", "se analiza", "el presente trabajo", "los autores del presente TFM".
- **APA 7 para todas las citas y la bibliografía.** Intercalar cita narrativa y parentética para fluidez.
- **Figuras y tablas** con identificador en negrita, título en cursiva, centradas, `Nota.` al pie en cursiva con fuente.
- **Invitación explícita al lector antes de cada figura/tabla** ("...como se muestra en la Figura 3").
- **Mínimo 20 referencias** (se supera con 30+ en este spec).
- **Referencias recientes** para Estado del Arte (≤5 años, prioridad 2022-2026).
- **Sin código pegado** en el documento; el código vive en notebooks.
- **Tiempos verbales**:
 - Introducción → presente.
 - Contexto y Estado del Arte → pasado para estudios previos, presente para verdades científicas aceptadas.
 - Objetivos → infinitivo.
 - Metodología → pasado impersonal ("se configuró", "se dividió").
 - Desarrollo (Cap 4) → pasado impersonal para narrar; presente para referir figuras.
 - Resumen → pasado (lo hecho) + presente (implicaciones).
- **Originalidad (Turnitin) < 20%**: contenido redactado desde cero, ninguna copia directa de fuentes; las citas van entrecomilladas y atribuidas.

---

## 8. Criterios de "terminado" para la Entrega 1

1. Documento Markdown `entrega1/TFM_grupal_entrega1.md` completo en las secciones definidas en §2.
2. 8 figuras y 5 tablas integradas o referenciadas.
3. 3 notebooks ejecutados al menos una vez con sus salidas guardadas; archivos JSONL generados en `datos/`.
4. ≥20 referencias en APA 7, todas verificables por URL/DOI/arXiv.
5. Vaciado exitoso a la plantilla oficial `.docx`.
6. PDF final generado.
7. QA de forma pasado (tercera persona, APA, figuras con nota al pie).
8. Entregado por la plataforma UNIR antes de las 23:59 hora peninsular del 22 de abril.

---

## 9. Riesgos identificados y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| OCR del NT con errores que dificulten la alineación por versículo | Media | Alto | Fallback: usar alineación por capítulo (más gruesa) si la de versículo falla; reportar N de parsing exitoso en Cap 4. |
| RV 1909 no disponible por API o con errores de OCR | Baja | Medio | Alternativas: RV 1865, Biblia del Oso 1569/1602, API `getbible.net`, dump local de `bible.helloao.org`. Nunca usar RV 1960 (copyright vigente). |
| Diagramas de las Figuras 1-3 consumen más de 2 h | Media | Medio | Sustituir por descripciones textuales detalladas en primera versión si hay retraso; elevar a figuras en siguiente iteración. |
| Vaciado Markdown → Word pierde formato | Media | Alto | Preparar `plantilla_mapping.md` desde el inicio con correspondencias de estilos; hacer pasada de prueba temprano (~13:00). |
| Plantilla exige estilos de Word propietarios no reproducibles desde Markdown | Media | Medio | Estrategia de copiar-pegar manual a la plantilla manteniendo sus estilos nativos. |
| Alguna referencia "verificada" no se confirma en el momento de la última comprobación | Baja | Medio | Tener ≥25 refs en el pool (buffer sobre el mínimo de 20); si alguna cae, descartar. |

---

## 10. Paso siguiente

Invocar `superpowers:writing-plans` con este spec como insumo para generar el plan de ejecución detallado (tareas con dependencias y estimaciones por bloque horario). El plan de ejecución concreta qué archivos se editan, en qué orden, con qué validaciones intermedias.
