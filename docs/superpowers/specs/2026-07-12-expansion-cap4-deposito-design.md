# Expansion del Capitulo 4 para el deposito del TFM

Fecha: 2026-07-12
Documento objetivo: `deposito/TFM_Deposito_EslavaSantos.docx`

## Problema

El revisor de la Entrega 3 conto 63 paginas de cuerpo (Cap 1 en p.12, Referencias en
p.75). El minimo para TFE grupal es 75. Faltan ~12 paginas, es decir 5.500-6.000
palabras. El Capitulo 4 tiene hoy 6.908 palabras y es donde vive la contribucion
tecnica, asi que es donde el documento crece de forma natural.

Restriccion dura: no se inventa nada. Cada cifra nueva sale de un fichero del repo.

## Hallazgos previos (inventario de evidencia)

El inventario de datos reales encontro discrepancias entre el docx y el repo:

| Afirmacion en el docx | Cifra real | Fuente |
|---|---|---|
| Splits 4.471 / 558 / 560 | 4.512 / 564 / 565 | `datos/splits/*.jsonl` |
| Entrenamiento LoRA ~47 min | 26,8 min (1.606,04 s) | `models/nllb-inga-lora-v1/training_history.json` |
| Repeticion patologica B es2inga >40% | 33% con umbral declarado | recalculado sobre `datos/predicciones_val_completo.jsonl` |
| Tabla 10 ilustra la corrida de Opus | Los ejemplos son salidas de Sonnet 4.6 | verificado literal; el commit `d42a992` sobrescribio el jsonl |

Las predicciones de Opus siguen recuperables: `git show 189833b:datos/predicciones_val_completo.jsonl`.
Recalculando BLEU sobre ellas salen exactamente las cifras de la Tabla 8 (C 4,3746 /
D 17,8908 / E 10,8828 en inga2es), lo que confirma que ese fichero es la corrida principal.

## Decisiones tomadas

1. La Tabla 10 pasa a mostrar las salidas de Opus 4.7 y de Sonnet 4.6 lado a lado por
   ejemplo. Asi el capitulo deja de reportar metricas de una corrida e ilustrar con otra,
   y de paso refuerza la comparacion intra-Claude de la Tabla 9.
2. Todas las cifras del capitulo se alinean con los ficheros del repo (corpus, splits,
   tiempo de entrenamiento, conteo de degeneracion).
3. El contenido nuevo va al Capitulo 4. El Capitulo 5 ya tiene discusion, tres
   limitaciones y trabajo futuro; no se duplica. Lo que entra en el Cap 4 es protocolo y
   evidencia, no interpretacion.

## Contenido nuevo (~5.900 palabras)

| Seccion | Palabras | Evidencia que la sostiene |
|---|---|---|
| 4.3.1 Validacion cualitativa del retriever | ~700 | Outputs ejecutados del NB08: 3 consultas (`wasi`, `imasa parlangapa`, `Taita Diuska runakunata kuianmi`) con top-3 real por indice |
| 4.4.1 Configuracion e interpretacion del entrenamiento LoRA | ~750 | `adapter_config.json` (r=16, alpha=32, dropout 0,1, q_proj/v_proj), `trainer_state.json` (3 epocas, 3.384 pasos, LR 3e-4, warmup 100), `training_history.json` (loss 10,71 -> 6,01; eval 6,05 / 5,97 / 5,94; 1.606 s) |
| 4.5.3 Presupuesto de contexto del prompt | ~600 | `src/models/claude_rag.py`: 5 entradas lexicas, 3 bloques gramaticales truncados a 400 caracteres, 5 ejemplos, max_tokens=256 |
| 4.6.1 Protocolo de evaluacion y validez de las metricas | ~900 | `src/eval/metrics.py`: sacrebleu corpus-level, chrF++ word_order=2, BERTScore F1 XLM-R con `lang="es"` en ambas direcciones. Muestra n=100, random_state=42, 99 versiculos + 1 articulo constitucional |
| 4.6.2 Analisis cualitativo ampliado | ~1.000 | Longitud media de salida por config y direccion, calculada sobre el jsonl. Gold Inga = 21,1 palabras |
| 4.6.3 Taxonomia de errores operacional + tabla nueva | ~800 | Criterio reproducible de degeneracion (token modal >=30% de los tokens) y conteo por config: B es2inga 33/100, D 1/100, E 0/100 |
| 4.6.4 Comparacion intra-Claude ampliada + Tabla 10 doble | ~800 | `datos/metricas_entrega2.json` y `_sonnet.json`; predicciones de Opus recuperadas de git |
| 4.6.5 Amenazas a la validez | ~350 | Muestra pequena, sin bootstrap ni intervalos, sin test set, referencia unica |

La limitacion mas seria y mas honesta que se declara: BERTScore se calcula con `lang="es"`
tambien en la direccion espanol-Inga, donde la referencia es Inga. Eso explica por que la
metrica se mueve poco entre configuraciones y debe decirse en vez de ocultarse.

## Fuera de alcance

- No se amplia el marco teorico (decision del 2026-06-24).
- No se corre nada nuevo: ni test set, ni ablations, ni bootstrap, ni anotacion humana.
  Lo que no existe se declara como limitacion, no se fabrica.
- No se tocan los tres indices: se regeneran con el mismo procedimiento AppleScript ya
  verificado (`update field` sobre los campos TOC, en tandas de 40).

## Implementacion

Un script reproducible `deposito/expandir_cap4.py`, en la linea de
`aplicar_correcciones_deposito.py`: opera sobre el XML interno, valida precondiciones y
aborta en voz alta si la estructura cambio. Parte del docx ya corregido (no de la base
original) e inserta el contenido nuevo clonando parrafos del propio documento para
heredar formato, tecnica que ya funciono en `insertar_contenido_en_docx.py`.

Reglas de redaccion del proyecto que aplican: solo ASCII en la puntuacion (sin em dash ni
comillas curvas), sin cohesion artificialmente perfecta entre parrafos, sin cifras sin
respaldo, y toda cita con DOI/arXiv verificado.

## Verificacion

1. Recuento de palabras del Cap 4 antes y despues.
2. Render a PDF y conteo de paginas de cuerpo (objetivo: >=75 entre Cap 1 y Referencias).
3. Cada cifra nueva del texto se contrasta contra el fichero que la respalda.
4. Inspeccion visual del PDF: captions en dos lineas, notas, tablas nuevas.
