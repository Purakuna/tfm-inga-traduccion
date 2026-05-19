# TFM Entrega 2, Diseno del documento y de los experimentos (spec)

**Fecha de elaboracion del spec**: 2026-05-18.
**Fecha limite de entrega**: 2026-05-24, 23:59 hora peninsular (~16:59 Colombia). Submision el 25-mayo si se requiere margen.
**Calificacion objetivo**: 75% de la memoria (Entrega 2 UNIR).
**Autor**: William Santos + Daniel Eslava (la asignacion nominal de las contribuciones permanece como en Entrega 1; en el repo el trabajo se ejecuta de forma asistida).

---

## 0. Contexto y decisiones previas

### 0.1 Feedback recibido de Entrega 1 (relevante para Entrega 2)

Del documento `project_entrega1_feedback_director.md` y de la lectura del PDF entregado:

1. **Calificacion "No apto"** explicitamente normal en primeras entregas.
2. **Contenido sobresaliente**: objetivos SMART, metodologia, comparativa novedosa fine-tuning vs RAG.
3. **Formato de captions NO cumple**: usar "Figura"/"Tabla" en espanol Y separar en dos lineas con titulo en cursiva debajo.
4. **Indicios fuertes de IA generativa**: hay que romper deliberadamente los patrones (varianza de parrafos, evitar SMART canonico, eliminar artefactos en ingles).
5. **Cap 5 vacio aceptado** como normal en Entrega 1; en Entrega 2 debe estar redactado al menos parcialmente con resultados preliminares.

### 0.2 Decisiones estrategicas de Entrega 2

Acordadas en sesion del 2026-05-18:

- **Estrategia**: Camino 1 (Breadth) - cubrir las 6 fases con experimento minimo en cada una, sacrificando ablations completas (esas van para Entrega Final).
- **NT espanol**: Biblia Torres Amat (1832), catolica, dominio publico. Se procesa via `mistral-ocr-extractor`.
- **Embeddings**: Gemini `text-embedding-004` (multilingue, 768-dim, presupuesto cubierto).
- **Vector DB**: LanceDB (embedded, columnar).
- **LLM de frontera**: Claude via `ANTHROPIC_API_KEY` existente. Val set acotado a ~100 ejemplos para controlar costo.
- **Modelo base para fine-tuning**: NLLB-200-distilled-600M (cabe holgado en M4 Max, entrena en pocas horas).
- **Reparto del trabajo**: ejecutado integramente en esta sesion. En el documento se preserva la asignacion declarada en Entrega 1 (William = adaptacion NMT + corpus; Daniel = pipeline LLM+RAG).

### 0.3 Restriccion temporal

7 dias de calendario (18-mayo a 24-mayo). El plan asume ~6-8h productivas diarias. Una jornada se reserva para QA + generacion final del docx.

### 0.4 Flujo de generacion del entregable (CRITICO)

Mismo pipeline que Entrega 1, sin excepciones:

1. **Trabajo asistido (este flujo)** opera unicamente sobre:
   - `entrega2/TFM_grupal_entrega2.md` (documento maestro en Markdown)
   - `entrega2/build_docx.py` (script Python con python-docx)
   - Notebooks y codigo bajo `notebooks/` y `src/`
2. **build_docx.py** genera un `.docx` borrador (`TFM_Entrega2_EslavaSantos.docx`) a partir del Markdown maestro y de la plantilla UNIR.
3. **El usuario** hace los ajustes finales en Microsoft Word sobre el .docx generado (portada, header, retoques manuales, ajustes de formato que python-docx no cubre limpiamente).
4. Esas ediciones manuales se documentan en `entrega2/CHANGES_IN_WORD_E2.md` (siguiendo el patron de Entrega 1), para preservar la trazabilidad md/py/docx en la siguiente iteracion.
5. El usuario exporta el `.pdf` final desde Word y lo entrega a UNIR.

**Prohibido en este flujo:** modificar directamente el `.docx` o el `.pdf` mediante herramientas distintas a `build_docx.py`. Cualquier edicion de Word la realiza el usuario.

---

## 1. Alcance de Entrega 2

### 1.1 Que SI entra en Entrega 2

**Tecnico:**
- Cierre de Fase 2 (corpus paralelo completo, ~7-10K pares)
- Cierre de Fase 3 (RAG operativo con 3 indices + Gemini embeddings + LanceDB)
- Fase 4 con UN run de LoRA sobre NLLB-200-distilled-600M
- Fase 5 con UN run de pipeline Claude+RAG sobre val set
- Fase 6 con comparativa preliminar de las 5 configs A-E

**Documental:**
- Cap 4 expandido a ~12-15 paginas con todos los nuevos resultados
- Cap 5 redactado con conclusiones preliminares + lineas para Entrega Final
- Nuevas figuras (minimo 4): curvas de loss, matriz de comparacion configs, arquitectura RAG implementada, distribucion del corpus completo
- Nuevas tablas (minimo 2): metricas comparativas, distribucion train/val/test
- Reescritura del estilo de captions en `build_docx.py`
- Aplicacion de los 5 cosmeticos del backlog
- Verificacion (o reemplazo) de las 2 referencias 2026 sospechosas

**Calidad:**
- Sweep anti-LLM sobre TODO el contenido nuevo y revision del contenido viejo

### 1.2 Que NO entra en Entrega 2 (queda para Entrega Final)

- Ablations de LoRA (dimensionalidad, learning rate, augmentation)
- Backtranslation para data augmentation
- Fine-tuning sobre NLLB-200-3.3B
- Validacion humana con hablantes nativos (logisticamente lenta)
- Despliegue local empaquetado
- Reranking con cross-encoder en el RAG

### 1.3 Meta cuantitativa

- Corpus: 5.000+ pares paralelos (meta minima) / 10.000+ (deseable)
- Configuraciones evaluadas: 5 (A-E de la Tabla 4)
- Metricas reportadas: BLEU, chrF++, BERTScore
- Paginas del documento: ~50-55 (vs 49 actuales)

---

## 2. Arquitectura tecnica

### 2.1 Pipeline de datos

```
[Fuentes OCR raw]                          [Fuentes nuevas]
  - 00-WNTinb-web.md (NT Inga, 595p)       - torres-amat-1832.pdf (NT espanol)
  - antihua-pacay.md (narrativas, 68p)
  - diccionario-inga.md (177p)
  - gramatica-pedagogica-levinsohn.md
  - rosetta-morfosintactico.md
            |
            v
   [Notebook 03: extraccion NT estructurada]
            |
            v
   [Notebook 04: alineacion NT Inga <-> Torres Amat]
            |
            v
   [Notebook 05: refinamiento Antihua Pacay con sliding window]
            |
            v
   [Notebook 06: normalizacion + particiones train/val/test]
            |
            v
   [datos/corpus_paralelo.jsonl + train.jsonl + val.jsonl + test.jsonl]
```

### 2.2 Pipeline RAG

```
[diccionario_inga.jsonl] -> indice lexico (LanceDB)
[gramatica + rosetta]   -> indice gramatical (LanceDB)
[train.jsonl]            -> indice de ejemplos (LanceDB)
            |
            v
   [Notebook 07: indexacion vectorial Gemini text-embedding-004]
            |
            v
   [src/rag/retriever.py: API uniforme de retrieval top-k]
```

### 2.3 Pipeline fine-tuning (Fase 4)

```
NLLB-200-distilled-600M
            +
LoRA adaptors (peft) r=16, alpha=32, dropout=0.1
            +
[train.jsonl] tokenizado con SentencePiece NLLB
            |
            v
   [Notebook 08: entrenamiento LoRA] -- 3-5 epochs
            |
            v
   [models/nllb-inga-lora-v1/] (checkpoint + adapter weights)
            |
            v
   [Notebook 09: inferencia + evaluacion config A (zero-shot) y B (LoRA)]
```

### 2.4 Pipeline LLM+RAG (Fase 5)

```
[oracion en Inga]
       |
       v
[retriever.query()] -> top-k del indice lexico + gramatical + ejemplos
       |
       v
[prompt structured]
  - system: descripcion del Inga + tarea de traduccion
  - context: knowledge recuperado
  - examples: pares paralelos similares (few-shot)
  - input: oracion a traducir
       |
       v
[Claude API call]
       |
       v
[traduccion al espanol]
       |
       v
   [Notebook 10: evaluacion configs C (zero-shot Claude), D (Claude+RAG), E (LoRA+RAG)]
```

### 2.5 Pipeline evaluacion (Fase 6)

```
[val.jsonl, ~100-200 ejemplos]
       |
       v
[5 configs ejecutadas en paralelo]
       |
       v
[scripts/eval.py]
  - BLEU (sacrebleu)
  - chrF++ (sacrebleu)
  - BERTScore (bert-score con XLM-RoBERTa multilingual)
       |
       v
   [datos/metricas_entrega2.json + figura comparativa]
```

---

## 3. Plan de archivos

### 3.1 Archivos nuevos (a crear)

```
notebooks/
  03_extraccion_NT_estructurada.ipynb     # parseo book+chapter+verse
  04_alineacion_NT_torres_amat.ipynb      # alineacion canonica
  05_refinamiento_antihua_pacay.ipynb     # sliding window + langdetect
  06_corpus_particiones.ipynb             # normalizacion + train/val/test
  07_indexacion_vectorial.ipynb           # Gemini embeddings + LanceDB
  08_finetuning_lora.ipynb                # entrenamiento LoRA
  09_eval_nllb_configs.ipynb              # configs A, B
  10_eval_llm_rag.ipynb                   # configs C, D, E

src/
  __init__.py
  rag/
    __init__.py
    retriever.py                          # API uniforme de retrieval
    embeddings.py                         # wrapper Gemini text-embedding-004
    indexes.py                            # gestores de los 3 indices LanceDB
  models/
    __init__.py
    nllb_lora.py                          # setup LoRA + forward pass
    claude_rag.py                         # pipeline prompts + API call
  eval/
    __init__.py
    metrics.py                            # BLEU / chrF++ / BERTScore wrappers
    runner.py                             # ejecutor de configs

datos/
  torres_amat_nt.jsonl                    # NT Torres Amat estructurado
  nt_inga_estructurado.jsonl              # reextraccion de NT Inga limpia
  corpus_paralelo.jsonl                   # corpus unificado
  splits/
    train.jsonl
    val.jsonl
    test.jsonl
  metricas_entrega2.json                  # resultados de Fase 6

datos/ocr/
  torres-amat-1832/                       # OCR del PDF descargado
    00-torres-amat-NT.md

models/
  nllb-inga-lora-v1/                      # checkpoint + adapter (gitignored si pesa)

entrega2/
  TFM_grupal_entrega2.md                  # documento maestro de la Entrega 2
  build_docx.py                           # generador docx (refactor del de Entrega 1)
  figuras/
    fig01.png ... fig12.png               # ~12 figuras en total
  TFM_Entrega2_EslavaSantos.docx          # output final
```

### 3.2 Archivos a modificar

```
README.md                                  # actualizar estado del proyecto + estructura
bibliografia/refs_verificadas.md          # eliminar/reemplazar refs 2026 no verificadas
datos/ocr/README.md                       # documentar la licencia de Torres Amat
.gitignore                                # excluir models/ pesados, datos/cache/
```

### 3.3 Archivos heredados de Entrega 1

```
entrega1/                                  # se conserva intacto como referencia historica
notebooks/00, 01, 02                       # se conservan intactos
docs/superpowers/specs/2026-04-21-...     # historico
docs/superpowers/plans/2026-04-21-...     # historico
```

---

## 4. Estructura del documento (entrega2/TFM_grupal_entrega2.md)

Misma estructura general que Entrega 1, con expansiones:

- **Portada**: fecha actualizada (24-mayo-2026), titulo y nombres consistentes con el feedback del director
- **Resumen** (~250 palabras): actualizar mencionando resultados preliminares de las dos contribuciones
- **Abstract**: traduccion fiel del resumen actualizado
- **Indices**: regenerar con nueva numeracion (mas figuras y tablas)
- **Organizacion del trabajo**: actualizar Tabla 1 si hay matices nuevos
- **Cap 1**: cambios minimos (algun ajuste de estructura para reflejar nuevos capitulos)
- **Cap 2**: cambios minimos (anadir 1-2 referencias nuevas si emergen del trabajo)
- **Cap 3**: revisar SMART para romper estructura demasiado canonica (sin perder rigor)
- **Cap 4 EXPANDIDO** (~12-15 paginas):
  - 4.1 Estado de avance (Fases 1-3 ya documentadas)
  - 4.2 **Construccion del corpus paralelo completo** (Fase 2 cerrada)
  - 4.3 **Base de conocimiento e indexacion vectorial** (Fase 3 cerrada)
  - 4.4 **Adaptacion de NLLB-200 mediante LoRA** (Fase 4, contribucion William)
  - 4.5 **Pipeline LLM + RAG con Claude** (Fase 5, contribucion Daniel)
  - 4.6 **Evaluacion comparativa preliminar** (Fase 6 parcial)
  - 4.7 Repositorio actualizado
- **Cap 5 NUEVO** (~3 paginas):
  - 5.1 Conclusiones preliminares
  - 5.2 Discusion de hallazgos
  - 5.3 Lineas de trabajo para Entrega Final (ablations, validacion humana, despliegue)
- **Referencias**: 37+ (mantener las 33 verificadas + nuevas que aparezcan)
- **Anexo A**: actualizar listado de notebooks (00-10) y datos generados

---

## 5. Plan de figuras y tablas

### 5.1 Figuras (12 totales, 4 nuevas)

| N | Titulo | Origen | Estado |
|---|---|---|---|
| 1 | Ubicacion del pueblo Inga en el Putumayo | OpenStreetMap | Heredada de Entrega 1 |
| 2 | Arquitectura general del sistema comparativo | Diagrama | Heredada de Entrega 1 |
| 3 | Variantes dialectales del Inga | Diccionario | Heredada de Entrega 1 |
| 4 | Pipeline de construccion del corpus | Diagrama | Heredada de Entrega 1 |
| 5 | Pipeline de ajuste fino del modelo multilingue | Diagrama | Heredada de Entrega 1 |
| 6 | Pipeline LLM + RAG multi-indice | Diagrama | Heredada de Entrega 1 |
| 7 | Cronograma del proyecto | Matplotlib | Heredada (revisar fechas) |
| 8 | Distribucion de longitudes del NT Inga | Notebook 01 | Heredada de Entrega 1 |
| 9 | **Distribucion del corpus paralelo final por dialecto y fuente** | Notebook 06 | NUEVA |
| 10 | **Arquitectura RAG implementada con LanceDB y Gemini** | Diagrama | NUEVA |
| 11 | **Curva de loss del entrenamiento LoRA** | Notebook 08 | NUEVA |
| 12 | **Comparativa de metricas entre las 5 configuraciones** | Notebook 10 | NUEVA |

### 5.2 Tablas (8 totales, 3 nuevas)

| N | Titulo | Estado |
|---|---|---|
| 1 | Organizacion del trabajo en grupo | Heredada |
| 2 | Comparativa de modelos multilingues candidatos | Heredada |
| 3 | Inventario de recursos linguisticos primarios | Heredada (corregir numeracion) |
| 4 | Configuraciones experimentales a evaluar | Heredada |
| 5 | Infraestructura de computo | Heredada |
| 6 | **Distribucion del corpus paralelo: train/val/test por dialecto** | NUEVA |
| 7 | **Hiperparametros del entrenamiento LoRA** | NUEVA |
| 8 | **Metricas comparativas por configuracion: BLEU, chrF++, BERTScore** | NUEVA |

### 5.3 Formato APA-UNIR (NUEVO requerimiento del director)

Captions en DOS LINEAS:
```
Figura N
*Titulo descriptivo en cursiva sin punto final*
```

Implementado via `add_caption()` reescrito en `entrega2/build_docx.py`.

---

## 6. Cronograma diario

| Dia | Fecha | Foco | Deliverables |
|---|---|---|---|
| D1 | Lun 18-may | Fundamentos + corpus NT | Plan aprobado, Torres Amat descargado, Notebook 03 listo, refs verificadas |
| D2 | Mar 19-may | Alineacion + Antihua | Notebooks 04, 05, 06 funcionando; corpus_paralelo.jsonl con ~5K+ pares |
| D3 | Mie 20-may | RAG infrastructure | Notebook 07; src/rag/ completo; tests basicos pasando |
| D4 | Jue 21-may | Fine-tuning LoRA | Notebook 08; checkpoint en models/; primer eval config A+B |
| D5 | Vie 22-may | LLM+RAG + Eval | Notebook 09, 10; metricas_entrega2.json con las 5 configs |
| D6 | Sab 23-may | Documento + figuras | Cap 4 expandido, Cap 5 redactado, 4 figuras nuevas generadas |
| D7 | Dom 24-may | QA + docx final | Sweep anti-LLM, build_docx.py refactorizado, .docx + .pdf finales |

Buffer: si algo se atrasa, los Notebooks 09-10 son los mas comprimibles (val set se puede recortar a 50 ejemplos).

---

## 7. Criterios de "hecho" para Entrega 2

Para considerar la Entrega 2 lista para enviar, deben cumplirse:

**Tecnico:**
- [ ] `datos/corpus_paralelo.jsonl` tiene ≥5.000 pares con campos {idx, libro, capitulo, versiculo, texto_inga, texto_es, dialecto, fuente}
- [ ] `datos/splits/train.jsonl|val.jsonl|test.jsonl` existen con ratio ~80/10/10
- [ ] LanceDB `lance_indexes/{lexico,gramatical,ejemplos}.lance` indexados
- [ ] `models/nllb-inga-lora-v1/` contiene adapter_config.json + adapter_model.safetensors
- [ ] `datos/metricas_entrega2.json` tiene las 5 configs (A-E) con sus 3 metricas
- [ ] Todos los notebooks 03-10 se ejecutan end-to-end sin errores

**Documental:**
- [ ] `entrega2/TFM_grupal_entrega2.md` cubre Caps 1-5 completos
- [ ] `entrega2/build_docx.py` produce captions en 2 lineas con cursiva
- [ ] `entrega2/TFM_Entrega2_EslavaSantos.docx` generado sin warnings
- [ ] `entrega2/TFM_Entrega2_EslavaSantos.pdf` exportado limpio
- [ ] 5 cosmeticos del backlog Entrega 1 corregidos
- [ ] Refs 2026 (Dhawan, Finkelstein) verificadas o reemplazadas
- [ ] Ningun "Figure"/"Table" en el documento final

**Calidad:**
- [ ] Sweep anti-LLM aplicado: parrafos de longitud variada, SMART menos canonico, cero artefactos de markdown ingles
- [ ] `git status` limpio antes de la build final
- [ ] Commit final con tag `entrega2-final-v1`

---

## 8. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|---|---|---|---|
| OCR de Torres Amat tarda o falla | Media | Alto | Plan B: usar `bible-api.com` o `ebible.org` que tienen Torres Amat como texto | 
| Alineacion NT Inga <-> Torres Amat tiene pocos matches | Media | Alto | Plan B: usar fuzzy matching + alineacion por capitulo en lugar de versiculo |
| LoRA no converge en 1 run | Baja | Alto | Plan B: documentar el run como baseline; reportar metricas de la mejor checkpoint |
| Cuota Anthropic insuficiente para 100 ejemplos | Baja | Medio | Reducir val set a 50; documentar como limitacion explicita |
| Cuota Gemini insuficiente para todos los embeddings | Baja | Medio | Reducir batch o usar LaBSE local como fallback |
| LanceDB tiene bugs en macOS ARM | Baja | Alto | Plan B: FAISS (mas maduro, mismo perfil) |
| Mi sweep anti-LLM se nota como artificial | Media | Medio | Pedir a Daniel review humano si esta disponible |
| Generacion del docx final falla | Media | Alto | Reservar D7 entero para QA + iteracion del docx |

---

## 9. Self-review checklist

- [x] Spec cubre todas las decisiones tomadas en sesion del 2026-05-18
- [x] Riesgos identificados con mitigaciones concretas
- [x] Cronograma cabe en los 7 dias disponibles
- [x] Criterios de "hecho" son binarios y verificables
- [x] Las 6 fases del proyecto original estan representadas
- [x] El nuevo requerimiento de captions del director esta abordado
- [x] La estrategia de reducir rastros LLM esta integrada en el plan
