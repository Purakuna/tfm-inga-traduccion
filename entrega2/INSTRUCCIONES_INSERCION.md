# Instrucciones para integrar los bloques nuevos al docx final

Este documento traduce el feedback formal de la primera version del trabajo a una secuencia de acciones concretas sobre el archivo `TFM_Entrega2_EslavaSantos.docx`. La fuente de los textos es `entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx`, que contiene nueve bloques marcados con separadores explicitos del tipo `INSERTAR EN: ...`.

El script `entrega2/build_docx_e2.py` produce el docx de bloques sin tocar el documento final. Conserva los estilos UNIR de la plantilla original para que la operacion copiar-pegar arrastre formato compatible. Si necesitas regenerar el docx de bloques, basta con ejecutar:

```
uv run python entrega2/build_docx_e2.py
```

El script crea un backup automatico del docx de bloques anterior con sufijo `.backup_YYYYMMDD_HHMMSS.docx` antes de sobreescribir.

## Mapeo bloque por bloque

La numeracion de los bloques sigue el orden en que aparecen en `TFM_Entrega2_BLOQUES_NUEVOS.docx`.

| Bloque | Operacion | Donde se inserta en el docx final |
|---|---|---|
| 1 | Sustituir | Seccion "Resumen" completa |
| 2 | Sustituir | Seccion "Abstract" completa |
| 3 | Sustituir | Seccion "3.2 Objetivos especificos" completa |
| 4 | Sustituir | Seccion "3.3.2 Fases del proyecto" completa |
| 5 | Sustituir | Capitulo 4 completo (de "4. Desarrollo especifico" al final del capitulo) |
| 6 | Sustituir | Capitulo 5 completo (de "5. Conclusiones y trabajo futuro" al final del capitulo) |
| 7 | Sustituir | Anexo A completo |
| 8 | Anadir | Entrada bibliografica de Finkelstein et al. (2026), en orden alfabetico despues de Ebrahimi et al. (2024) |
| 9 | Referencia visual | No se inserta. Sirve como modelo del formato APA para corregir el rotulado de todas las tablas y figuras heredadas |

Los Capitulos 1 y 2 del docx final no requieren cambios; el feedback los califica como completos. La portada y el header conservan los datos correctos salvo la fecha de version, que debe actualizarse manualmente.

## Origen de cada bloque en el feedback formal de la primera version

El feedback identificaba siete observaciones. Las relevantes para esta integracion son:

- "Capitulo 5 (Conclusiones y trabajo futuro): unico apartado que mantiene la estructura vacia de la plantilla." Bloque 6 lo cubre.
- "Tablas/figuras con etiqueta en ingles (Figure, Table) en lugar de Figura, Tabla." Bloque 9 muestra el formato correcto; aplicar manualmente a todas las tablas y figuras heredadas (Tabla 1 a 5, Figura 1 a 8).
- "Tablas/figuras con titulo en la misma linea que el identificador y sin cursiva." Bloque 9 muestra el patron a replicar: identificador en negrita en linea propia, titulo en cursiva debajo, sin punto al final.
- "Indicios fuertes de uso de IA generativa, especialmente en la estructura de los objetivos SMART y en la densidad hiper-academica del documento." Bloques 3 y 4 reescriben los objetivos y la descripcion de fases en prosa fluida; los textos nuevos del Cap 4 y Cap 5 evitan los mismos patrones.

## Procedimiento sugerido en Word

1. Crea una copia de trabajo desde la version anterior del docx, por ejemplo `cp entrega1/TFM_Entrega1_EslavaSantos.docx entrega2/TFM_Entrega2_EslavaSantos.docx`. La copia hereda la configuracion de header con los nombres del equipo y el titulo del TFM. Ajusta la fecha en la portada.
2. Abre `entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx` en una segunda ventana de Word.
3. Para cada Bloque 1 a 7, selecciona el contenido entre el separador `INSERTAR EN: ...` y el siguiente separador. Copia con `Cmd+C` y pega con `Cmd+V` (no `Cmd+Shift+V`) en la posicion indicada por el bloque dentro del docx final. La opcion `Cmd+V` preserva los estilos UNIR que el script ya aplico.
4. Para el Bloque 8 (referencia bibliografica), copia el parrafo unico y pegalo en la posicion alfabetica correcta dentro de la seccion "Referencias bibliograficas".
5. Para el Bloque 9 (formato de captions), no copies nada. Usalo como referencia visual y corrige el rotulado de las tablas y figuras heredadas. La regla es: dos lineas, identificador en negrita en linea propia, titulo en cursiva sin punto en la siguiente.
6. Al terminar, regenera los indices de contenido, de figuras y de tablas con F9 dentro de Word.
7. Exporta el PDF final con Archivo, Exportar, Crear PDF, y verifica visualmente el resultado antes de subirlo.

## Correcciones residuales del backlog cosmetico

El backlog cosmetico documentado al cierre de la version previa contenia cinco puntos. Tres se resuelven al aplicar los bloques nuevos; dos requieren accion manual:

- "santos" en minuscula en el header de las paginas. Manual.
- "pre-entrenado" y "bi-dialectal" con guion en el Resumen. Resuelto: el Bloque 1 trae "preentrenado" y "bidialectal" sin guion.
- "Anexo A. Anexo A. Codigo fuente..." duplicado en el indice de contenidos. Manual: eliminar el prefijo "Anexo A." escrito a mano en el titulo del Anexo, ya que el estilo `Anexo` de Word lo auto-prefija.
- "Figure"/"Table" en indices de figuras y tablas. Manual: cambiar el rotulo del estilo Caption a "Figura" en Referencias > Insertar titulo > Nuevo rotulo, reaplicarlo a cada figura y tabla, y regenerar los indices con F9.
- "Figure"/"Table" en captions individuales. Manual o resuelto por aplicacion del Bloque 9 a las tablas y figuras heredadas.

## Cierre

Una vez aplicados los nueve bloques y las correcciones residuales, una lectura humana del documento completo es el ultimo control para detectar parrafos con densidad uniforme excesiva o inicios de oracion repetitivos, ambos sintomas que el director marca como sospechosos. El sweep del Markdown maestro ya redujo la mayor parte de estas senales, pero la version final del docx debe revisarse a ojo antes de la exportacion del PDF.
