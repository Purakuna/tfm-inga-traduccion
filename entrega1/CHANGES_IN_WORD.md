# Cambios manuales aplicados al .docx/PDF final (Entrega 1)

> **Contexto para retomar el proyecto.** El archivo `TFM_Entrega1_EslavaSantos.pdf` enviado a UNIR el 22 de abril de 2026 contiene edits manuales hechos sobre el `.docx` generado por `build_docx.py`. Estos edits NO estan reflejados ni en `TFM_grupal_entrega1.md` ni en `build_docx.py`. Al arrancar la siguiente iteracion, sincronizar los tres artefactos (md, py, docx) antes de seguir escribiendo.

**Fecha de los cambios manuales:** 21-22 abril 2026.
**Artefactos afectados:**
- `entrega1/TFM_Entrega1_EslavaSantos.docx` (version final enviada)
- `entrega1/TFM_Entrega1_EslavaSantos.pdf` (export del docx)

El `.md` y el `.py` quedaron con la version previa a los edits manuales.

---

## A. Cambios aplicados en el docx y que difieren del .md / .py

### A.1 Portada y metadatos

| Campo | En .md / .py | En el .docx enviado |
|---|---|---|
| Nombre del integrante 1 | `Eslava, Daniel` | `Daniel Alejandro Eslava` (nombre completo) |
| Nombre del integrante 2 | `Santos, William` | `William De Jesus santos` (con "santos" en minuscula) |
| Titulo del TFM | "...mediante **ajuste fino** de modelos multilingues y **recuperacion aumentada de informacion** sobre modelos de lenguaje de frontera" | "...mediante **fine-tuning** de modelos multilingues y **RAG** sobre modelos de lenguaje de frontera" |
| Inga-Espanol | `Inga-Espanol` (ambos con mayuscula) | `Inga-espanol` (el segundo con minuscula) |
| "Inteligencia Artificial" | mayuscula en ambas | "Inteligencia artificial" (lowercase en 'artificial', como lo trae la plantilla UNIR) |

### A.2 Resumen

El Resumen del documento Word tiene dos variaciones ortograficas respecto al .md:

| Termino | En .md | En el docx |
|---|---|---|
| Modelo preentrenado | `preentrenado` (una sola palabra) | `pre-entrenado` (con guion) |
| Cobertura bidialectal | `bidialectal` (una sola palabra) | `bi-dialectal` (con guion) |

El resto del Capitulo 2 (donde se usa `bidialectal` varias veces) SI quedo sin guion.

### A.3 Capitulo 4: Desarrollo especifico

El usuario edito las referencias a "Entrega 1" y "Entrega 2" que habian quedado en el texto. En el docx enviado:

| En .md | En el docx |
|---|---|
| `### 4.1 Estado de avance al cierre de la Entrega 1` | `4.1 Estado de avance` |
| Texto: "...al cierre de la Entrega 1..." en parrafos de 4.1.x | Reformulado sin esa referencia |
| Seccion `## 4.3 Próximos pasos hacia la Entrega 2` (con su contenido) | **Eliminada del docx** |
| En Cap 5: "El contenido de este capitulo se presenta en la Entrega Final..." | Verificar si quedo o se reformulo |
| En 4.1.2: "preparados para alineacion canonica con una version del Nuevo Testamento en espanol... en la Entrega 2" | Probablemente reformulado |

**Implicacion:** cuando retomemos el proyecto, todo el Cap 4 del `.md` hay que revisar linea por linea para que refleje la version que quedo en el Word. En particular, considerar si Cap 4.3 "Proximos pasos" se elimina tambien del `.md`/`.py`, o si se reformula como "Trabajo pendiente hacia la evaluacion final" o similar.

### A.4 Header de todas las paginas

El header que aparece en todas las paginas (arriba a la derecha) es el de la plantilla UNIR y contiene tres lineas manualmente llenadas:
```
Daniel Alejandro Eslava
William De Jesus santos
Diseno e implementacion de un sistema comparativo de traduccion automatica Inga-espanol mediante fine-tuning de modelos multilingues y RAG sobre modelos de lenguaje de frontera
```

El `build_docx.py` no toca esos campos del header. Si se regenera, hay que:
- Dejar el header como lo trae la plantilla original (con los placeholders)
- O programaticamente insertar los nombres y el titulo con python-docx usando la API `section.header`

---

## B. Items cosmeticos detectados y dejados en backlog

Cinco issues no corregidos antes de enviar (aceptados por el usuario como backlog):

1. **"William De Jesus santos"** → "santos" deberia ir con mayuscula. Aparece en el header y en la portada.
2. **Resumen**: uniformar "pre-entrenado" -> "preentrenado" y "bi-dialectal" -> "bidialectal" para consistencia con el resto del documento.
3. **Indice de contenidos**: "Anexo A. Anexo A. Codigo fuente..." (doble prefijo). Causa: el estilo `Anexo` auto-prefija "Anexo A." y el titulo manual tambien lo trae. Fix: quitar "Anexo A." del texto del heading.
4. **Indice de figuras**: muestra "Figure N" en vez de "Figura N". Causa: el estilo Caption de Word usa "Figure" (ingles) por defecto. Fix: Referencias > Insertar titulo > Nuevo rotulo > "Figura", reaplicar y regenerar F9.
5. **Indice de tablas**: mismo problema que #4, "Table N" en vez de "Tabla N".

---

## C. Tareas recomendadas al retomar el proyecto

Antes de empezar la Entrega Final:

1. **Reconciliar el .md con el .docx enviado.** Abrir el PDF final + el .md y reescribir en el .md cualquier parrafo que haya quedado distinto tras los edits manuales.
2. **Reconciliar el build_docx.py.** Ajustar el script para que genere:
   - La portada con los nombres completos (o los que se decidan oficiales)
   - El titulo con la version que se va a mantener a lo largo del TFM
   - El header de todas las paginas (llenar via `section.header` en python-docx)
   - El Anexo sin el prefijo manual "Anexo A."
   - La configuracion de idioma del estilo Caption a Spanish para que salga "Figura"/"Tabla"
3. **Decidir el titulo "oficial" del TFM.** La version del docx usa "fine-tuning" y "RAG" (terminos en ingles). La version original de los objetivos del .md usaba "ajuste fino" y "recuperacion aumentada" (espanol). Elegir una forma y aplicarla consistentemente en:
   - Portada
   - Header
   - Abstract (al traducir del resumen)
   - Referencias a la propia memoria dentro del texto
4. **Pasar los cinco fixes cosmeticos del backlog** antes de entrar al contenido nuevo de la siguiente entrega.
5. **Actualizar el README.md del repo** si hubo cambios de portada (nombres, titulo).

---

## D. Estado de los artefactos al cierre de Entrega 1

| Archivo | Ubicacion | Estado |
|---|---|---|
| Markdown maestro | `entrega1/TFM_grupal_entrega1.md` | Refleja la version ANTES de los edits manuales en Word |
| Script de generacion | `entrega1/build_docx.py` | Refleja el build que produjo el `.docx` antes de los edits manuales |
| Word final enviado | `entrega1/TFM_Entrega1_EslavaSantos.docx` | Version con los edits manuales, NO subida a GitHub? (verificar) |
| PDF final enviado | `entrega1/TFM_Entrega1_EslavaSantos.pdf` | Idem, generado desde el docx editado |
| Repo | `Purakuna/tfm-inga-traduccion` | Commits llegan hasta el ajuste del Resumen + Abstract sin referencias a "Entrega 1" |

**Pendiente de decidir:** subir el docx y el PDF finales (con los edits manuales) al repo, o preservar solo el codigo reproducible y regenerarlos desde el `.py` actualizado en la siguiente iteracion.
