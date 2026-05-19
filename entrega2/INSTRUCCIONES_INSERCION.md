# Instrucciones para integrar la Entrega 2 sobre el .docx final

Este documento te guia paso a paso para producir `TFM_Entrega2_EslavaSantos.docx` a partir de:

- Tu copia editada de Entrega 1 (`entrega1/TFM_Entrega1_EslavaSantos.docx`)
- Los bloques nuevos generados automaticamente en `entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx`

El script `entrega2/build_docx_e2.py` NO toca el docx final. Solo genera bloques con los estilos UNIR correctos para que copiar y pegar preserve el formato. El control sobre el archivo final queda en tus manos.

---

## Paso 0. Hacer una copia de trabajo

Antes de tocar nada:

```
cp entrega1/TFM_Entrega1_EslavaSantos.docx \
   entrega2/TFM_Entrega2_EslavaSantos.docx
```

Y abre `entrega2/TFM_Entrega2_EslavaSantos.docx` en Word para editarlo. La copia de E1 trae intactos:

- El header configurado con los nombres del equipo y el titulo del TFM
- Los footers
- Los margenes
- Los estilos UNIR (Heading 1-3, Caption, etc.)

Esto evita tener que reconfigurar todo desde la plantilla vacia.

---

## Paso 1. Cambios de portada

En la portada de tu docx final, cambia:

- **Fecha**: `22 de abril de 2026` -> `24 de mayo de 2026`
- **Apellido del integrante 2 en la tabla**: `santos` con minuscula -> `Santos` con mayuscula (issue del backlog cosmetico de Entrega 1)

Verifica los siguientes campos (deberian estar correctos desde Entrega 1, solo confirma):

- Daniel Alejandro Eslava (nombre completo)
- William De Jesús Santos (nombre completo)
- Director: Víctor David Larco Torres
- Titulo: "Diseño e implementación de un sistema comparativo de traducción automática Inga-español mediante fine-tuning de modelos multilingües y RAG sobre modelos de lenguaje de frontera"

---

## Paso 2. Cambios en el header de todas las paginas

Edita el header (Insertar -> Encabezado -> Editar) y cambia:

- `William De Jesús santos` (lowercase) -> `William De Jesús Santos`

El resto del header se mantiene.

---

## Paso 3. Reemplazar Resumen y Abstract

Abre `entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx`. Veras separadores tipo:

```
======================================================================
INSERTAR EN: Sustituir la seccion "Resumen" en tu .docx final
======================================================================
```

Para cada bloque marcado:

1. Selecciona y copia TODO el contenido del bloque (desde el heading "Resumen" hasta antes del siguiente separador)
2. En el docx final, selecciona el bloque equivalente del Resumen actual
3. Pega encima con `Cmd+Shift+V` (pegar sin formato) **NO**, usa `Cmd+V` para mantener los estilos UNIR ya aplicados

Repite con el bloque "Abstract".

Tambien en el Resumen, despues de pegar, asegurate de que estos terminos estan SIN guion (van como una sola palabra):

- `pre-entrenado` -> `preentrenado`
- `bi-dialectal` -> `bidialectal`

Esto era item del backlog cosmetico de Entrega 1; el md del Resumen ya los lleva correctos pero conviene verificar.

---

## Paso 4. Reemplazar secciones del Capitulo 3

El bloque del Capitulo 3 incluye:

- 3.1 Objetivo general (parrafo SMART reescrito)
- 3.2 Objetivos especificos (reescritos como prosa, NO como lista canonica)
- 3.3.2 Fases del proyecto (varianza en los inicios de fase)

**Por que se reescribieron**: el director del TFM detecto en su feedback de Entrega 1 tres senales fuertes de uso de IA generativa, incluyendo "la forma en la que los objetivos estan desglosados y justificados semanticamente, que encaja con la manera en que un LLM estructura las respuestas". Reescribir las secciones en prosa fluida es la accion mas directa para desactivar esa alerta.

Localiza en tu docx la seccion 3.1, 3.2 y 3.3.2, y reemplazalas con los bloques correspondientes del archivo de bloques.

---

## Paso 5. Reemplazar Capitulo 4 completo

El Cap 4 cambia sustancialmente: pasa de documentar las Fases 1-3 a documentar las Fases 1-6 con resultados experimentales reales.

Selecciona en tu docx final TODO el Capitulo 4 (desde "# 4. Desarrollo especifico" hasta el inicio de "# 5. Conclusiones") y reemplazalo por el bloque correspondiente.

El nuevo Cap 4 incluye:

- 4.1 Configuracion del entorno (uv, Gemini, LanceDB, Anthropic)
- 4.2 Construccion del corpus paralelo (con Tabla 6 nueva)
- 4.3 Base de conocimiento e indexacion vectorial (con Figura 10 nueva)
- 4.4 Adaptacion de NLLB-200 mediante LoRA (con Tabla 7 y Figura 11 nuevas)
- 4.5 Pipeline LLM + RAG con Claude
- 4.6 Evaluacion comparativa preliminar (con Tabla 8 y Figura 12 nuevas)
- 4.7 Repositorio de codigo y datos

**Important**: las secciones 4.4, 4.5, 4.6 y partes de 5.1, 5.2 contienen marcadores `[PLACEHOLDER N - ...]` que indican que el contenido cuantitativo (curva de loss, tabla de metricas, hallazgos) se llena cuando los notebooks de entrenamiento y evaluacion terminen. Estos placeholders se sustituiran en un segundo build cuando esten los resultados.

---

## Paso 6. Reemplazar Capitulo 5 completo

El Cap 5 de Entrega 1 estaba vacio (esperado). Ahora trae:

- 5.1 Conclusiones preliminares (cinco resultados concretos)
- 5.2 Discusion (limitaciones reconocidas)
- 5.3 Lineas de trabajo hacia la Entrega Final

Sustituye el Cap 5 vacio por el bloque correspondiente.

---

## Paso 7. Reemplazar Anexo A

El Anexo A se expande con:

- Lista de los 12 notebooks (00 a 11) con su proposito individual
- Estructura del paquete `src/` con sus tres subpaquetes
- Descripcion completa de los archivos en `datos/`
- Mencion del NT Reina-Valera 1909 en dominio publico

Sustituye el Anexo A actual por el bloque correspondiente.

---

## Paso 8. Anadir nueva referencia bibliografica

En la seccion de Referencias bibliograficas, busca la entrada de Ebrahimi et al. (2024) y anade INMEDIATAMENTE DESPUES la nueva referencia:

```
Finkelstein, M., Caswell, I., Domhan, T., Peter, J.-T., Juraska, J., Riley, P.,
Deutsch, D., Kovacs, G., Dilanni, C., Cherry, C., Briakou, E., Nielsen, E.,
Luo, J., Black, K., Mullins, R., Agrawal, S., Xu, W., Kats, E., Jaskiewicz, S.,
Freitag, M., y Vilar, D. (2026). *TranslateGemma: Technical Report*
[arXiv preprint]. https://arxiv.org/abs/2601.09012
```

Aparece como ultimo bloque en `TFM_Entrega2_BLOQUES_NUEVOS.docx` y puede copiarse directamente.

---

## Paso 9. Correcciones de formato de FIGURAS y TABLAS (critico)

El director senalo en el feedback de Entrega 1 que el formato de captions NO cumplia la normativa APA/UNIR. Hay dos problemas:

### 9.1 Etiquetas "Figure" y "Table" en ingles

En Word: Referencias -> Insertar titulo -> Nuevo rotulo -> Anadir `Figura` y `Tabla`. Luego para CADA caption que diga "Figure N" o "Table N":

1. Seleccionar el caption
2. Cambiarlo manualmente a "Figura N" / "Tabla N"
3. Verificar que el TOC de figuras y tablas se regenere correctamente (F9)

### 9.2 Identificador y titulo en una sola linea sin cursiva

El formato actual es:

```
Figure 1. Ubicacion del pueblo Inga en el Putumayo
```

El formato correcto APA/UNIR es:

```
Figura 1
*Ubicacion del pueblo Inga en el Putumayo*
```

(identificador en su propia linea, titulo en cursiva debajo en linea separada)

Para arreglarlo:

1. Para cada figura y tabla del documento (Figuras 1-12, Tablas 1-8):
2. Romper el caption en dos lineas
3. La primera linea queda como "Figura N" o "Tabla N" en negrita (estilo Caption)
4. La segunda linea con el titulo en cursiva (estilo Normal)
5. Eliminar el punto que iba entre el identificador y el titulo

Los captions de los bloques nuevos (Tablas 6-8, Figuras 9-12) ya vienen con el formato correcto desde `TFM_Entrega2_BLOQUES_NUEVOS.docx`. Solo hay que aplicar el cambio a los captions heredados de Entrega 1 (Figuras 1-8, Tablas 1-5).

---

## Paso 10. Backlog cosmetico de Entrega 1 (pendientes menores)

Confirma que estos cinco items quedan limpios en el docx final:

1. Header de todas las paginas: `William De Jesús Santos` (con S mayuscula) -- ya cubierto en Paso 2
2. Resumen: `preentrenado` y `bidialectal` sin guion -- ya cubierto en Paso 3
3. TOC: la entrada del Anexo aparece como `Anexo A. Codigo fuente...`, no como `Anexo A. Anexo A. Codigo fuente...`. Si el doble prefijo aparece, quita el "Anexo A." del titulo manual del Anexo y regenera el TOC con F9.
4. Indice de figuras: dice "Figura N" no "Figure N" -- ya cubierto en Paso 9.1
5. Indice de tablas: dice "Tabla N" no "Table N" -- ya cubierto en Paso 9.1

---

## Paso 11. Sweep anti-LLM final (lectura humana)

Despues de tener el docx final integrado, dedica una pasada humana de revision con foco especifico en las tres senales que el director marco:

### 11.1 Densidad y cohesion hiper-academica

Lee de corrido cada capitulo y busca pasajes donde los parrafos tienen longitud uniforme (todos de 5-6 lineas). Si encuentras una secuencia asi, rompe alguno en dos parrafos cortos y une dos otros adyacentes en uno mas largo. La variacion visible de longitudes humaniza la lectura.

### 11.2 Cohesion sintactica impecable

Busca secuencias de oraciones que empiezan con "El", "La", "Los", "Este". Reescribe alguna comenzando con una subordinada o un complemento circunstancial. Ejemplo:

- Antes: "El sistema implementado consiste en dos pipelines."
- Despues: "Detras del sistema implementado conviven dos pipelines."

### 11.3 Cualquier formula reconocible de LLM

Busca y reescribe (o elimina) estas frases si aparecen:

- "aspectos no abordados previamente"
- "es importante notar que"
- "vale la pena destacar"
- "en este contexto"
- "Por otro lado" como conector de oraciones cortas
- "En primer lugar... En segundo lugar..." como estructura argumentativa cerrada
- "Es relevante mencionar que"

Estas no aparecen frecuentemente en el documento actual, pero conviene un *grep* visual.

---

## Paso 12. Exportar PDF y entregar

Cuando termines:

1. Word: Archivo -> Exportar -> Crear PDF
2. Verifica que el PDF se ve correcto (paginacion, captions, TOC actualizado)
3. Subir a UNIR antes del deadline

---

## Comportamiento del script

Si necesitas regenerar `TFM_Entrega2_BLOQUES_NUEVOS.docx`:

```
uv run python entrega2/build_docx_e2.py
```

El script:

- Carga la plantilla UNIR original (`/Users/william-santos/Downloads/plantilla_grupal.docx`) en modo solo lectura
- Si `entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx` ya existe, hace backup automatico con timestamp antes de sobreescribir
- Tu trabajo manual sobre `TFM_Entrega2_EslavaSantos.docx` NUNCA se ve afectado por el script

---

## Resumen de archivos

| Archivo | Estado | Que hace |
|---|---|---|
| `plantilla_grupal.docx` (en Downloads) | Solo lectura | Plantilla UNIR original |
| `entrega1/TFM_Entrega1_EslavaSantos.docx` | Intacto | Referencia historica |
| `entrega2/TFM_grupal_entrega2.md` | Generado por md | Source of truth del contenido |
| `entrega2/build_docx_e2.py` | Script Python | Genera bloques nuevos con estilos UNIR |
| `entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx` | Build artifact | Solo los bloques que cambian |
| `entrega2/TFM_Entrega2_EslavaSantos.docx` | **Editado por ti** | El documento final que entregas |

El docx final lo controlas exclusivamente tu.
