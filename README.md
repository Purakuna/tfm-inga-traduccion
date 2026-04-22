# TFM: Traduccion automatica Inga-Espanol

Trabajo Fin de Master del **Master Universitario en Inteligencia Artificial** de la Universidad Internacional de La Rioja (UNIR), desarrollado por **Daniel Eslava** y **William Santos** bajo la direccion de **Victor David Larco Torres**.

## Resumen del proyecto

La lengua Inga, variante quechua hablada por cerca de 18.000 personas en el Putumayo (Colombia), no cuenta con herramientas digitales de traduccion automatica. Este trabajo aborda esa brecha construyendo un sistema comparativo Inga-Espanol sobre dos aproximaciones complementarias:

1. **Adaptacion de un modelo de traduccion multilingue preentrenado** al par Inga-Espanol mediante ajuste fino eficiente en parametros, aprovechando las lenguas quechuas emparentadas que el modelo ya cubre como base de transferencia.
2. **Pipeline basado en un modelo de lenguaje de frontera con recuperacion aumentada de informacion**, sustentado en una base de conocimiento linguistica estructurada en tres indices independientes: lexico, gramatical y de ejemplos paralelos.

Ambas aproximaciones se evaluan comparativamente con metricas automaticas estandar (BLEU, chrF++, BERTScore) y validacion cualitativa con hablantes nativos.

La contribucion original del proyecto reside en la cobertura bidialectal, Alto y Medio Putumayo, y en la comparacion sistematica de ambas aproximaciones sobre el mismo par linguistico.

## Estructura del repositorio

```
entrega1/                 Documento de la primera entrega del TFM
  TFM_grupal_entrega1.md  Documento maestro en Markdown
  figuras/                Figuras del documento (PNG)
notebooks/                Notebooks de Jupyter del proyecto
  00_setup_entorno.ipynb           Configuracion y validacion del entorno
  01_eda_recursos_base.ipynb       Analisis exploratorio de los recursos primarios
  02_extraccion_corpus_NT.ipynb    Extraccion y alineacion inicial del corpus
datos/                    Salidas estructuradas de los notebooks
  diccionario_inga.jsonl           Entradas lexicas estructuradas
  nt_inga_alineado.jsonl           Segmentos del Nuevo Testamento en Inga
  antihua_pacay_alineado.jsonl     Pares paralelos de las narrativas MP
  estadisticas_corpus.json         Estadisticas agregadas
bibliografia/
  refs_verificadas.md     Referencias bibliograficas con DOI/arXiv/ACL verificados
docs/superpowers/
  specs/                  Especificaciones de diseno
  plans/                  Planes de ejecucion
propuesta_tfm.md          Propuesta inicial del TFM
propuesta_formulario.md   Version resumida para el formulario UNIR
```

## Recursos linguisticos primarios

El proyecto se apoya en cinco fuentes primarias que totalizan 1.094 paginas de material linguistico sobre la lengua Inga. Estas fuentes no se redistribuyen en este repositorio; cada una hereda la licencia de su fuente primaria:

- **Diccionario Inga** (Tandioy Jansasoy, Levinsohn y Tandioy Chasoy, 1997) - dominio publico/academico, Comite de Educacion Inga.
- **Gramatica pedagogica del Inga** (Levinsohn y Mongui, s.f.) - Instituto Linguistico de Verano.
- **Apendice morfosintactico** (Rosetta Project).
- **El Nuevo Testamento en Inga de Colombia** (Wycliffe Bible Translators, 2012) - licencia CC BY-NC-ND 3.0.
- **Antihua Pacay Gentecunapa parlocuna** (Jamioy Yanangona de Pena, 1985) - archivos abiertos SIL International.

## Estado del proyecto

**Entrega 1** (abril 2026): planteamiento del problema, estado del arte, objetivos, metodologia y avances iniciales (configuracion del entorno, inventario y procesamiento del corpus, primera extraccion del Nuevo Testamento).

**Entrega Final** (octubre 2026, tentativa): ejecucion de las fases 3 a 7, incluyendo el ajuste fino de modelos, la implementacion del pipeline LLM+RAG, la evaluacion comparativa completa y el despliegue local.

## Licencia

El codigo del presente trabajo se publica bajo licencia MIT (ver `LICENSE`).

Los datos derivados de fuentes externas heredan las licencias de sus fuentes primarias.

## Reproducibilidad

Los notebooks se desarrollaron sobre Python 3.11 en macOS con aceleracion Apple Silicon (MPS). Para reproducir:

```
pip install transformers peft accelerate sentence-transformers sacrebleu \
            datasets anthropic sentencepiece matplotlib pandas numpy tqdm \
            nbformat jupyter staticmap requests Pillow
```

Luego ejecutar los notebooks en orden: `00`, `01`, `02`.
