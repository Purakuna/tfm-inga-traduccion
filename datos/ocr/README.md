# Recursos linguisticos primarios (OCR extraidos)

Este directorio contiene las extracciones en formato Markdown de los cinco recursos linguisticos primarios del Inga utilizados en el presente TFM. Las extracciones se realizaron con `mistral-ocr-extractor` sobre los PDF originales de cada fuente.

## Contenido

| Archivo | Fuente primaria | Dialecto | Paginas | Licencia de la fuente |
|---|---|---|---|---|
| `inga-kichwa/00-WNTinb-web.md` | *Kaipimi Taita Dius Rimaku: El Nuevo Testamento en el idioma Inga de Colombia* (Wycliffe Bible Translators, 2012, 2a ed.) | AP (probable) | 595 | CC BY-NC-ND 3.0 |
| `inga-kichwa/diccionario-inga.md` | *Diccionario Inga* (Tandioy Jansasoy, Levinsohn, & Tandioy Chasoy, 1997; edicion interina, Comite de Educacion Inga de la Organizacion Musu Runakuna) | AP + MP (marcado) | 177 | Academico con atribucion |
| `inga-kichwa/gramatica-pedagogica-levinsohn.md` | *Inga Kichwa: Una gramatica pedagogica del Inga (Partes 1 y 2)* (Levinsohn & Mongui, s.f., traduccion de Raul Mongui sobre base de Ross) | AP | 228 | Archivos SIL, uso academico |
| `inga-kichwa/rosetta-morfosintactico.md` | Apendice B morfosintactico (publicado como parte del *Diccionario Inga*, Rosetta Project archive) | - | 26 | Archivos SIL, uso academico |
| `inga-kichwa/antihua-pacay.md` | *Antihua Pacay Gentecunapa parlocuna: Tradiciones de los Inganos Pacayes* (Jamioy Yanangona de Pena, 1985, Proyecto Bilingue Inga-Castellano, Vicariato Apostolico de Sibundoy; SIL International Language and Culture Archives) | MP (Mocoa) | 68 | SIL, uso academico |

Total: 1.094 paginas de material linguistico primario.

## Consideraciones sobre redistribucion

Estas extracciones se incluyen en el presente repositorio, que es **privado**, exclusivamente para garantizar la reproducibilidad tecnica de los notebooks (`01_eda_recursos_base.ipynb` y `02_extraccion_corpus_NT.ipynb`) durante la ejecucion del TFM.

**Si el repositorio se hace publico en algun momento, es imprescindible revisar previamente las condiciones de cada licencia.** En particular:

- El Nuevo Testamento de Wycliffe se distribuye bajo **CC BY-NC-ND 3.0**; la clausula "NoDerivatives" (ND) hace cuestionable la redistribucion publica de una extraccion OCR. En ese escenario, reemplazar este archivo por un enlace al recurso original en las paginas oficiales de Wycliffe y un script que lo descargue y procese localmente.
- Los archivos de SIL International estan catalogados en su Language and Culture Archives con terminos de uso academico y cita obligatoria. Se recomienda reemplazar por enlaces al repositorio oficial de SIL si se publica el repo.
- El Diccionario Inga se publico originalmente por el Comite de Educacion Inga de la Organizacion Musu Runakuna; su redistribucion exige autorizacion explicita del comite. El presente TFM lo utiliza con fines estrictamente academicos y de investigacion.

## Como se obtuvieron

Los PDF originales se procesaron con la herramienta `mistral-ocr-extractor`, que produce un `content.md` por PDF con frontmatter de metadatos y marcadores de pagina `<!-- Page N -->`. Los archivos aqui depositados son las salidas directas de esa herramienta, sin edicion manual.
