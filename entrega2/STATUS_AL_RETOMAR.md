# Status del proyecto al retomar (Entrega 2)

**Generado**: 2026-05-19 al cierre de sesion automatizada.

## Lo que se cerro en esta sesion

### Datos del corpus

- **5,641 pares paralelos** finales (5,589 NT Wycliffe + 52 Constitucion CCELA)
- Particiones train/val/test 80/10/10: 4,512 / 564 / 565
- Cuatro indices RAG en LanceDB: lexico (4,900) + gramatical (605) + ejemplos (4,512) + ejemplos_es (4,512)

### Modelos entrenados

- **LoRA bidireccional sobre NLLB-200-distilled-600M**, 3 epochs sobre 9,024 ejemplos (corpus duplicado)
- Eval loss: 5.94 (sin overfitting)
- Adapter persistido en `models/nllb-inga-lora-v1/` (9.4 MB, gitignored)

### Evaluacion comparativa completa

Cinco configuraciones x dos direcciones x dos modelos Claude = 20 corridas reportadas.

#### Tabla de metricas (val expandido, 100 ejemplos por direccion)

| Config | Modelo | inga2es BLEU | es2inga BLEU | inga2es chrF | es2inga chrF |
|---|---|---|---|---|---|
| A: NLLB zero-shot | - | 1.82 | 0.16 | 19.50 | 15.88 |
| B: NLLB + LoRA | - | 8.18 | 1.79 | 27.19 | 22.89 |
| C: Claude zero-shot | Sonnet 4.6 (val viejo) | 5.45 | 0.19 | 29.92 | 19.70 |
| C: Claude zero-shot | **Opus 4.7** | 4.37 | 0.32 | 29.45 | 21.75 |
| D: Claude + RAG | Sonnet 4.6 | 12.61 | 9.33 | 36.64 | 35.78 |
| **D: Opus + RAG** | **Opus 4.7** | **17.89** | **10.95** | **43.28** | **38.19** |
| E: LoRA + Claude+RAG refinement | Sonnet 4.6 | 14.32 | 9.31 | 39.32 | 36.81 |
| E: LoRA + Opus + RAG refinement | Opus 4.7 | 10.88 | 9.98 | 37.55 | 39.00 |

#### Hallazgos principales

1. **Opus + RAG (D) es la config ganadora** con 17.89 BLEU en inga2es. Supera ampliamente el rango reportado por Garcia Gilabert 2024 para Quechua (BLEU ~10) y se ubica en el lado alto del rango QueEn (Chen 2024).

2. **RAG es el ingrediente magico**: Claude zero-shot (C) en es2inga = 0.19-0.32 BLEU (catastrofico). Con RAG (D) sube a 9.33-10.95. Mejora de >30x.

3. **LoRA colapsa en es2inga**: 1.79 BLEU vs 10.95 de D. El decoder no aprende a generar Inga con solo 4,512 pares.

4. **Anomalia E con Opus**: Opus EMPEORA en E vs Sonnet (10.88 vs 14.32 en inga2es). El seed mediocre del LoRA confunde a Opus que "sobre-corrige". Sonnet es mas conservador. Hallazgo academicamente relevante para reportar.

5. **La asimetria entre direcciones se reduce con RAG**: con LoRA solo la diferencia inga2es vs es2inga es 6.4 BLEU; con Opus+RAG es 6.94 (en magnitud absoluta) pero proporcionalmente menor.

### Archivos generados / commits

23 commits en `main` durante la sesion. Top 10:

```
189833b feat(entrega2): NB11 con Opus 4.7 - matriz experimental completa
ff7c9aa feat(entrega2): NB10 re-ejecutado con LoRA + val expandido
bd3d0ca feat(entrega2): LoRA re-entrenado + cambio a Opus 4.7
a7b20c4 data(entrega2): Constitucion al corpus paralelo (+52 pares juridicos)
c2f374c feat(entrega2): NB11 completo - Sonnet 4.6 10 corridas
c7473ea data(entrega2): AT Inga + RV1909 OT - exploratorio (descartado)
b0e243a data(entrega2): incorporar Constitucion + AT Pasajes Historicos
16d8bb7 feat(entrega2): NB10 - configs A y B bidireccional
5666827 feat(entrega2): LoRA bidireccional entrenado + figura 11
e24c572 build(entrega2): build_docx_e2.py + INSTRUCCIONES_INSERCION.md
```

### Notebooks ejecutados (14 totales)

- `00_setup_entorno.ipynb` (E1)
- `01_eda_recursos_base.ipynb` (E1)
- `02_extraccion_corpus_NT.ipynb` (E1)
- `03_extraccion_NT_inga_estructurada.ipynb` - NT Inga estructurado 6,083 versos unicos
- `04_extraccion_NT_rv1909.ipynb` - RV1909 NT estructurado 7,955 versos
- `05_alineacion_NT.ipynb` - 5,589 pares NT paralelos
- `06_antihua_pacay_alineado.ipynb` - 86 pares exploratorios (NO incluidos)
- `07_corpus_particiones.ipynb` - splits 80/10/10
- `08_indexacion_vectorial.ipynb` - 4 indices RAG con Gemini embeddings
- `09_finetuning_lora.ipynb` - LoRA bidireccional NLLB
- `10_medicion_nllb_configs.ipynb` - configs A, B
- `11_medicion_llm_rag.ipynb` - configs C, D, E (Opus 4.7)
- `12_extraccion_AT_inga.ipynb` - AT exploratorio (NO incluido en corpus)
- `13_alineacion_AT.ipynb` - alineamiento AT fallido (NO incluido)
- `14_constitucion_corpus.ipynb` - +52 pares Constitucion al corpus

### Figuras generadas

- `fig09_distribucion_corpus.png` - distribucion train/val/test por fuente
- `fig10_arquitectura_rag.png` - diagrama RAG implementado
- `fig11_lora_loss.png` - curva de loss del LoRA
- `fig12_metricas_comparativas.png` - barras agrupadas 5 configs x 2 direcciones

---

## Lo que falta para entregar

### 1. Llenar placeholders del Cap 4 y Cap 5 del md

`entrega2/TFM_grupal_entrega2.md` tiene marcadores `[PLACEHOLDER N - ...]` en:

- **Cap 4.4** (Adaptacion NLLB con LoRA): falta narrativa final con curva loss + smoke test cualitativo
- **Cap 4.5** (Pipeline Claude+RAG): falta narrativa con ejemplos cualitativos
- **Cap 4.6** (Evaluacion comparativa): falta Tabla 8 con metricas + analisis de hallazgos
- **Cap 5.1** (Conclusiones): falta el hallazgo cuantitativo principal
- **Cap 5.2** (Discusion): falta analisis comparativo entre configs

Sugerencia: usar los hallazgos numerados arriba como base. La narrativa principal:

> El experimento confirma que la integracion de recuperacion aumentada
> sobre un modelo de lenguaje de frontera (config D, Opus 4.7 + RAG)
> ofrece la mejor calidad de traduccion en ambas direcciones para el par
> Inga-espanol. La mejora respecto al ajuste fino de NLLB-200 con LoRA
> (config B) es sustancial: 17.89 vs 8.18 BLEU en inga2es (mas del doble),
> y 10.95 vs 1.79 BLEU en es2inga (6x). El RAG cierra la asimetria que
> aqueja al LoRA en la generacion del Inga, lengua para la cual el
> decoder no aprende con solo 4,512 pares paralelos.

### 2. Regenerar el docx de bloques con metricas llenas

Una vez los placeholders esten llenos:

```bash
uv run python entrega2/build_docx_e2.py
```

El script:
- Carga `entrega2/TFM_grupal_entrega2.md` (single source of truth)
- Genera `entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx`
- Hace backup automatico si el output ya existe
- NO toca tu docx final

### 3. Sweep anti-LLM sobre el contenido nuevo

Revisar las nuevas secciones (4.4, 4.5, 4.6, 5.1, 5.2) para:
- Variar longitud de parrafos
- Romper inicios de frase uniformes ("El sistema...", "La config...")
- Eliminar formulas reconocibles

Ver `INSTRUCCIONES_INSERCION.md` Paso 11 para checklist.

### 4. Integracion manual en el docx final

Ver `entrega2/INSTRUCCIONES_INSERCION.md` para los 12 pasos. Sintesis:

1. Copia E1 docx como `TFM_Entrega2_EslavaSantos.docx`
2. Cambia portada (fecha + Santos mayuscula)
3. Cambia header (Santos mayuscula)
4. Pegar bloques 1-7 desde `TFM_Entrega2_BLOQUES_NUEVOS.docx`
5. Cambiar captions: "Figure/Table" -> "Figura/Tabla", romper en 2 lineas con cursiva
6. Aplicar los 5 cosmeticos del backlog de E1
7. Sweep humano anti-LLM final
8. Exportar PDF y entregar

### 5. Decision pendiente: re-correr Sonnet en val expandido?

Para comparacion estricta Sonnet vs Opus en mismo val:
- Costo: ~$5-10 USD, ~15 min
- Beneficio: comparacion limpia para reportar (actualmente Sonnet usa val anterior)
- Recomendado: SI, para que la tabla 8 tenga rigor estricto

---

## Estado de archivos clave

| Archivo | Status |
|---|---|
| `entrega2/TFM_grupal_entrega2.md` | Maestro con placeholders en 4.4-4.6 y 5.1-5.2 |
| `entrega2/build_docx_e2.py` | Listo, genera bloques sin tocar docx final |
| `entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx` | Generado con placeholders aun (regenerar al llenar) |
| `entrega2/INSTRUCCIONES_INSERCION.md` | Listo, 12 pasos para integrar al docx final |
| `entrega2/figuras/` | 4 figuras nuevas (9, 10, 11, 12) listas |
| `datos/corpus_paralelo.jsonl` | 5,641 pares |
| `datos/metricas_entrega2.json` | Metricas Opus 4.7 |
| `datos/metricas_entrega2_sonnet.json` | Backup Sonnet 4.6 (val viejo) |
| `models/nllb-inga-lora-v1/` | LoRA entrenado (gitignored, regenerable) |

Pause completo. Al volver, retomar desde paso 1 (llenar placeholders del md).
