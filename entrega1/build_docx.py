"""
Construye TFM_Entrega1_EslavaSantos.docx a partir del Markdown, usando la
plantilla grupal UNIR. Limpia el cuerpo de la plantilla, mantiene los estilos,
y reinserta todo el contenido aplicando los estilos correctos.
"""
import json
import re
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


BASE = Path('/Users/william-santos/Documents/UNIR/tfm')
DOCX_PATH = BASE / 'entrega1' / 'TFM_Entrega1_EslavaSantos.docx'
FIG_DIR = BASE / 'entrega1' / 'figuras'

# ---------------------------------------------------------------------------
# Abrir y limpiar
# ---------------------------------------------------------------------------
doc = Document(str(DOCX_PATH))
body = doc.element.body

# Eliminar todos los parrafos y tablas (pero conservar sectPr que define margenes, headers, footers)
for child in list(body):
    tag = child.tag.split('}')[-1]
    if tag in ('p', 'tbl'):
        body.remove(child)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def style_exists(name):
    try:
        doc.styles[name]
        return True
    except KeyError:
        return False

# Mapa de estilos (display names en python-docx)
S_NORMAL = 'Normal'
S_H1     = 'Heading 1'
S_H2     = 'Heading 2'
S_H3     = 'Heading 3'
S_INDX   = 'Título Índices'
S_H1U    = 'Título 1 sin numerar'
S_LIST   = 'List Paragraph'
S_CAPT   = 'Caption'
S_FOOT   = 'Pie de foto-tabla'
S_BIB    = 'Referencias bibliográficas'
S_ANEX   = 'Anexo'
S_FIG    = 'Figuras'


def add_paragraph(text='', style=S_NORMAL, bold=False, italic=False,
                  alignment=None, page_break_before=False, space_after=None,
                  space_before=None):
    p = doc.add_paragraph(style=style)
    if page_break_before:
        p.paragraph_format.page_break_before = True
    if alignment is not None:
        p.alignment = alignment
    if space_after is not None:
        p.paragraph_format.space_after = space_after
    if space_before is not None:
        p.paragraph_format.space_before = space_before
    if text:
        r = p.add_run(text)
        r.bold = bold
        r.italic = italic
    return p


# Markup inline: **bold**, *italic*, `code`
TOKEN_RE = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)')

def add_rich_paragraph(text, style=S_NORMAL, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph(style=style)
    if alignment is not None:
        p.alignment = alignment
    parts = TOKEN_RE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            r = p.add_run(part[2:-2])
            r.bold = True
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            r = p.add_run(part[1:-1])
            r.italic = True
        elif part.startswith('`') and part.endswith('`'):
            r = p.add_run(part[1:-1])
            r.font.name = 'Consolas'
        else:
            p.add_run(part)
    return p


def add_caption(kind, num, title_text, style=S_CAPT):
    """Rotulo tipo 'Tabla N' o 'Figura N' en negrita + titulo en cursiva."""
    p = doc.add_paragraph(style=style)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run(f'{kind} {num}')
    r1.bold = True
    p.add_run('\n')
    r2 = p.add_run(title_text)
    r2.italic = True
    return p


def add_note(text, style=S_FOOT):
    """Nota al pie de figura/tabla."""
    p = doc.add_paragraph(style=style)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run('Nota. ')
    r.italic = True
    p.add_run(text)
    return p


def add_figure(path, width_cm=14):
    p = doc.add_paragraph(style=S_FIG if style_exists(S_FIG) else S_NORMAL)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    r.add_picture(str(path), width=Cm(width_cm))
    return p


def add_table_from_rows(headers, rows, style='Light Grid Accent 1', col_widths=None):
    """Crea una tabla con cabecera + filas."""
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    try:
        t.style = style
    except KeyError:
        t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header
    for j, h in enumerate(headers):
        cell = t.rows[0].cells[j]
        cell.text = ''
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
    # Cuerpo
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = t.rows[i].cells[j]
            cell.text = str(val)
    # Anchos opcionales
    if col_widths:
        for row in t.rows:
            for j, w in enumerate(col_widths):
                if j < len(row.cells):
                    row.cells[j].width = Cm(w)
    return t


def add_page_break():
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def add_toc_placeholder(heading_name):
    """Marcador para indice autogenerado en Word (se actualiza con F9)."""
    add_paragraph(heading_name, style=S_INDX, page_break_before=True)
    p = doc.add_paragraph()
    r = p.add_run()
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    if heading_name == 'Índice de contenidos':
        instrText.text = r'TOC \o "1-3" \h \z \u'
    elif heading_name == 'Índice de figuras':
        instrText.text = r'TOC \h \z \t "Caption;1"'
    elif heading_name == 'Índice de tablas':
        instrText.text = r'TOC \h \z \t "Caption;1"'
    else:
        instrText.text = r'TOC \o "1-3" \h \z \u'
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')
    placeholder = OxmlElement('w:t')
    placeholder.text = f'[{heading_name}: se actualiza en Word con F9]'
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')
    r._r.append(fldChar1)
    r._r.append(instrText)
    r._r.append(fldChar2)
    r._r.append(placeholder)
    r._r.append(fldChar3)


# ---------------------------------------------------------------------------
# 1. PORTADA
# ---------------------------------------------------------------------------
def build_cover():
    # Usamos estilo Normal o Sinespaciado para la portada
    cov_style = 'No Spacing' if style_exists('No Spacing') else S_NORMAL

    p = add_paragraph('Universidad Internacional de La Rioja', style=cov_style,
                      alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    p.runs[0].font.size = Pt(16)
    p = add_paragraph('Escuela Superior de Ingeniería y Tecnología', style=cov_style,
                      alignment=WD_ALIGN_PARAGRAPH.CENTER)
    p.runs[0].font.size = Pt(13)
    p = add_paragraph('Máster Universitario en Inteligencia Artificial', style=cov_style,
                      alignment=WD_ALIGN_PARAGRAPH.CENTER)
    p.runs[0].font.size = Pt(13)

    add_paragraph('', style=cov_style)
    add_paragraph('', style=cov_style)

    titulo = ('Diseño e implementación de un sistema comparativo de traducción '
              'automática Inga-Español mediante ajuste fino de modelos multilingües '
              'y recuperación aumentada de información sobre modelos de lenguaje '
              'de frontera')
    p = add_paragraph(titulo, style=cov_style, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                      bold=True)
    p.runs[0].font.size = Pt(14)

    add_paragraph('', style=cov_style)
    add_paragraph('', style=cov_style)

    add_paragraph('Trabajo fin de estudio presentado por:', style=cov_style,
                  alignment=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph('Eslava, Daniel', style=cov_style,
                  alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    add_paragraph('Santos, William', style=cov_style,
                  alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True)

    add_paragraph('', style=cov_style)

    add_paragraph('Tipo de trabajo: Piloto experimental', style=cov_style,
                  alignment=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph('Director: Víctor David Larco Torres', style=cov_style,
                  alignment=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph('Fecha: 22 de abril de 2026', style=cov_style,
                  alignment=WD_ALIGN_PARAGRAPH.CENTER)


# ---------------------------------------------------------------------------
# 2. RESUMEN / ABSTRACT
# ---------------------------------------------------------------------------

RESUMEN = (
    "El presente trabajo propone el diseño y la implementación de un sistema comparativo "
    "de traducción automática para el par lingüístico Inga-Español, como aporte a la "
    "preservación digital de la lengua Inga del Putumayo, variante de la familia quechua "
    "hablada por aproximadamente 18.000 personas en el suroccidente de Colombia. El sistema "
    "adopta dos aproximaciones complementarias: por un lado, la adaptación de un modelo de "
    "traducción automática multilingüe preentrenado mediante técnicas de ajuste fino eficiente "
    "en parámetros, aprovechando el conocimiento de lenguas quechuas emparentadas como base "
    "de transferencia; por otro, la construcción de un pipeline de traducción basado en un "
    "modelo de lenguaje de frontera potenciado con recuperación aumentada de información, "
    "apoyado en una base de conocimiento lingüístico estructurada en tres índices "
    "independientes (léxico, gramatical y de ejemplos paralelos). En la presente Entrega 1 "
    "se documenta el planteamiento del problema, la revisión del estado del arte con énfasis "
    "en trabajos recientes sobre Quechua como antecedente más cercano al Inga, la definición "
    "de objetivos específicos con criterio SMART, la metodología organizada en siete fases y "
    "los avances iniciales del proyecto: configuración del entorno computacional sobre Apple "
    "Silicon, inventario cuantificado de 1.094 páginas de material lingüístico primario "
    "procedente de cinco recursos (diccionario, gramática pedagógica, apéndice "
    "morfosintáctico, Nuevo Testamento en Inga y narrativas orales), y extracción inicial "
    "de un corpus compuesto por 3.093 segmentos del Nuevo Testamento y 817 entradas léxicas "
    "estructuradas. El aporte original del trabajo se sustenta en la cobertura bidialectal, "
    "Alto Putumayo y Medio Putumayo, y en la comparación directa de ambas aproximaciones "
    "sobre la misma lengua, aspectos no abordados previamente en la literatura académica."
)

ABSTRACT = (
    "This work proposes the design and implementation of a comparative machine translation "
    "system for the Inga-Spanish language pair, as a contribution to the digital preservation "
    "of the Inga language of Putumayo, a Quechua variant spoken by approximately 18,000 "
    "people in southwestern Colombia. The system adopts two complementary approaches: first, "
    "adapting a pretrained multilingual machine translation model through parameter-efficient "
    "fine-tuning techniques, leveraging knowledge of related Quechua languages as a transfer "
    "base; second, building a translation pipeline based on a frontier language model "
    "enhanced with retrieval-augmented generation, supported by a structured linguistic "
    "knowledge base organized in three independent indices (lexical, grammatical, and "
    "parallel-example). This first deliverable documents the problem statement, the "
    "state-of-the-art review with emphasis on recent work on Quechua as the closest "
    "antecedent, the SMART-based definition of specific objectives, the seven-phase "
    "methodology, and the project's initial progress: configuration of the computational "
    "environment on Apple Silicon, quantified inventory of 1,094 pages of primary linguistic "
    "material drawn from five resources (dictionary, pedagogical grammar, morphosyntactic "
    "appendix, Inga New Testament, and oral narratives), and initial extraction of a corpus "
    "comprising 3,093 New Testament segments and 817 structured lexical entries. The original "
    "contribution of the work rests on its bidialectal coverage, Alto Putumayo and Medio "
    "Putumayo, and on the direct comparison of both approaches on the same language, aspects "
    "not previously addressed in the academic literature."
)


def build_resumen():
    add_paragraph('Resumen', style=S_INDX, page_break_before=True)
    add_rich_paragraph(RESUMEN)
    p = doc.add_paragraph(style=S_NORMAL)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r1 = p.add_run('Palabras clave: ')
    r1.bold = True
    p.add_run('traducción automática, lenguas indígenas, Inga, transfer learning, '
              'recuperación aumentada de información.')


def build_abstract():
    add_paragraph('Abstract', style=S_INDX, page_break_before=True)
    add_rich_paragraph(ABSTRACT)
    p = doc.add_paragraph(style=S_NORMAL)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r1 = p.add_run('Keywords: ')
    r1.bold = True
    p.add_run('machine translation, indigenous languages, Inga (Quechua), transfer '
              'learning, retrieval-augmented generation.')


# ---------------------------------------------------------------------------
# 3. INDICES (placeholders TOC)
# ---------------------------------------------------------------------------
def build_indices():
    add_toc_placeholder('Índice de contenidos')
    add_toc_placeholder('Índice de figuras')
    add_toc_placeholder('Índice de tablas')


# ---------------------------------------------------------------------------
# 4. ORGANIZACION DEL TRABAJO EN GRUPO
# ---------------------------------------------------------------------------
def build_grupo():
    add_paragraph('Organización del trabajo en grupo', style=S_INDX,
                  page_break_before=True)

    add_paragraph('Partes que aborda el TFE', style=S_INDX)
    add_rich_paragraph(
        "El presente Trabajo Fin de Máster se desarrolla en modalidad grupal por dos "
        "estudiantes y aborda dos contribuciones técnicas autocontenidas que, de forma "
        "individual, podrían constituir un trabajo de investigación independiente, "
        "además de un componente de infraestructura compartida. Esta partición responde "
        "al requisito de la Universidad de que cada integrante realice un aporte técnico "
        "suficiente para la obtención del título, tal como se establece en la plantilla "
        "oficial para trabajos grupales."
    )
    add_rich_paragraph(
        "La primera contribución, a cargo de **William Santos**, consiste en la "
        "adaptación de un modelo de traducción automática multilingüe preentrenado al par "
        "lingüístico Inga-Español mediante técnicas de ajuste fino eficiente en parámetros, "
        "aprovechando el conocimiento de lenguas quechuas emparentadas que el modelo ya "
        "incorpora como base para la transferencia cross-lingual. Este componente incluye "
        "además la curación del corpus bidialectal, Alto Putumayo y Medio Putumayo, labor "
        "que se nutre del acceso comunitario del integrante a hablantes nativos en Mocoa, "
        "así como la validación lingüística de las salidas del sistema."
    )
    add_rich_paragraph(
        "La segunda contribución, a cargo de **Daniel Eslava**, consiste en el diseño e "
        "implementación de un sistema de traducción basado en un modelo de lenguaje de "
        "frontera potenciado con recuperación aumentada de información. El sistema utiliza "
        "una base de conocimiento lingüístico del Inga estructurada en tres índices "
        "independientes, léxico, gramatical y de ejemplos paralelos, que se consultan "
        "dinámicamente durante la inferencia. Este componente incluye adicionalmente el "
        "diseño del marco de evaluación comparativa entre ambas aproximaciones, así como la "
        "orquestación del pipeline completo de inferencia."
    )
    add_rich_paragraph(
        "La infraestructura compartida entre ambos integrantes comprende la construcción "
        "y curación del corpus paralelo, la normalización ortográfica, la validación con "
        "hablantes nativos y el análisis de resultados en la fase de evaluación final."
    )

    add_paragraph('Distribución y estructura de la memoria', style=S_INDX)
    add_rich_paragraph(
        "La estructura de responsabilidades para la redacción de la memoria se detalla "
        "en la Tabla 1."
    )
    add_caption('Tabla', 1, 'Organización del trabajo en grupo en la redacción de la memoria')
    add_table_from_rows(
        headers=['Apartado de la memoria', 'Responsables'],
        rows=[
            ['Introducción', 'William Santos y Daniel Eslava'],
            ['Contexto y estado del arte',
             'William Santos (NMT y ajuste fino eficiente), Daniel Eslava (LLMs y RAG)'],
            ['Objetivos y metodología de trabajo', 'William Santos y Daniel Eslava'],
            ['Marco normativo',
             'William Santos (aspectos comunitarios), Daniel Eslava (licenciamiento)'],
            ['Desarrollo, adaptación del modelo multilingüe', 'William Santos'],
            ['Desarrollo, pipeline LLM con recuperación aumentada', 'Daniel Eslava'],
            ['Desarrollo, corpus e infraestructura experimental',
             'William Santos y Daniel Eslava'],
            ['Conclusiones', 'William Santos y Daniel Eslava'],
        ],
        col_widths=[7, 9],
    )
    add_note('Elaboración propia.')

    add_paragraph('Mecanismos de coordinación empleados', style=S_INDX)
    add_rich_paragraph(
        "El trabajo remoto entre los dos integrantes, ubicados en Mocoa (Putumayo) y Cali "
        "(Valle del Cauca), exige mecanismos de coordinación formales que aseguren la "
        "trazabilidad de las decisiones técnicas y la consistencia de los entregables. "
        "Para ello se adoptan los siguientes instrumentos."
    )
    add_rich_paragraph(
        "En primer lugar, se establece un repositorio compartido en la plataforma GitHub "
        "para el código fuente, los *notebooks* de experimentación y la documentación del "
        "proyecto, con control de versiones distribuido y revisión cruzada de las "
        "contribuciones mediante *pull requests* antes de su integración a la rama "
        "principal. En segundo lugar, se utiliza GitHub Projects para la gestión de tareas "
        "operativas, con tableros que reflejan las siete fases del proyecto descritas en el "
        "Capítulo 3. En tercer lugar, se planifican reuniones síncronas semanales por "
        "videoconferencia para revisión de avances, toma de decisiones arquitecturales y "
        "resolución de bloqueos; cada reunión produce un acta breve que se archiva en el "
        "repositorio. En cuarto lugar, se emplea un gestor bibliográfico compartido "
        "(Zotero) que mantiene sincronizadas las referencias verificadas del proyecto, con "
        "identificadores estables (DOI, arXiv, ACL Anthology) asociados a cada entrada. "
        "Finalmente, la memoria se redacta de forma colaborativa con asignación clara de "
        "secciones según la distribución mostrada en la Tabla 1 y revisión cruzada completa "
        "antes de cada entrega formal."
    )


# ---------------------------------------------------------------------------
# 5. CAPITULO 1 - INTRODUCCION
# ---------------------------------------------------------------------------
def build_cap1():
    add_paragraph('Introducción', style=S_H1, page_break_before=True)

    add_paragraph('Motivación', style=S_H2)
    add_rich_paragraph(
        "La lengua Inga, perteneciente a la familia lingüística quechua, constituye un "
        "sistema cultural vivo sostenido por aproximadamente 18.000 hablantes del pueblo "
        "Inga asentado en el departamento del Putumayo, al suroccidente de Colombia. Sus "
        "comunidades se distribuyen principalmente entre dos zonas dialectales: el Alto "
        "Putumayo, que abarca el Valle de Sibundoy con los corregimientos de San Andrés y "
        "los municipios de Santiago y Colón; y el Medio Putumayo, que comprende Mocoa, "
        "Condagua, Yunguillo y Puerto Guayuyaco. A pesar de seguir siendo una lengua de uso "
        "cotidiano en el hogar y en la vida comunitaria, el Inga atraviesa un proceso "
        "sostenido de desplazamiento frente al español, que opera como lengua dominante en "
        "los ámbitos educativo, institucional y digital. Este fenómeno no amenaza "
        "únicamente a un sistema de comunicación, sino a toda una cosmovisión y un sistema "
        "de conocimiento ancestral transmitido oralmente. La UNESCO (2022), en el *World "
        "Atlas of Languages*, advierte que las lenguas indígenas del mundo enfrentan un "
        "riesgo de desaparición sin precedentes, y por ello la Organización de las Naciones "
        "Unidas ha proclamado la Década Internacional de las Lenguas Indígenas 2022-2032."
    )
    add_rich_paragraph(
        "Frente a esta realidad, la brecha digital adopta hoy la forma de una exclusión "
        "tecnológica. Los grandes traductores comerciales, como Google Translate y DeepL, "
        "no contemplan la lengua Inga en su catálogo. En mayo de 2022, Google Translate "
        "incorporó Quechua sureño a su conjunto de idiomas soportados, pero la variante "
        "Inga del Putumayo continúa excluida. Los escasos recursos digitales disponibles se "
        "limitan al *Diccionario Inga* del Valle de Sibundoy (Tandioy Jansasoy et al., "
        "1997), a materiales pedagógicos del Instituto Lingüístico de Verano y a los "
        "recursos del programa *Inga Rimangapa Samuichi* de Indiana University, todos ellos "
        "con difusión restringida y sin integración computacional. La literatura reciente "
        "sobre procesamiento del lenguaje natural en lenguas indígenas de América Latina "
        "documenta con claridad este rezago sistemático (Tonja et al., 2024); los primeros "
        "esfuerzos de traducción automática para lenguas indígenas colombianas, incluida el "
        "Inga, aparecen con Prieto et al. (2024), quienes construyen el primer corpus "
        "paralelo documentado. Esta ausencia tecnológica profundiza la brecha entre las "
        "lenguas hegemónicas y las lenguas indígenas, y niega al Inga un espacio en el "
        "ecosistema digital contemporáneo."
    )
    add_rich_paragraph(
        "Existe, sin embargo, un marco normativo y una ventana de oportunidad tecnológica "
        "que habilitan una respuesta viable desde la inteligencia artificial. La "
        "Constitución Política de Colombia (Asamblea Nacional Constituyente de Colombia, "
        "1991) reconoce en su Artículo 10 la oficialidad territorial de las lenguas y "
        "dialectos de los grupos étnicos del país, y la Ley 1381 de 2010 desarrolla los "
        "derechos lingüísticos de estas comunidades, estableciendo principios explícitos de "
        "reconocimiento, fomento, protección, uso, preservación y fortalecimiento "
        "(Congreso de la República de Colombia, 2010). Los avances recientes en traducción "
        "automática multilingüe masiva, en técnicas de transfer learning desde lenguas "
        "emparentadas y en modelos de lenguaje de frontera potenciados con recuperación "
        "aumentada de información abren la posibilidad de producir herramientas utilizables "
        "para lenguas que hasta hace pocos años eran consideradas intratables. Las "
        "consideraciones éticas y comunitarias de este tipo de iniciativas se han "
        "sistematizado en la literatura reciente (Mager et al., 2023), y existen "
        "antecedentes exitosos de trabajos análogos, como la hoja de ruta desarrollada para "
        "el cherokee (Zhang et al., 2022). El presente trabajo se propone contribuir a "
        "cerrar la brecha digital del Inga situándose en la intersección de este marco "
        "normativo y esta oportunidad técnica."
    )

    # Figura 1 al cierre de Motivación: mapa de ubicación
    add_rich_paragraph(
        "La ubicación geográfica del pueblo Inga en el departamento del Putumayo, con las "
        "principales comunidades de ambos dialectos, se muestra en la Figura 1."
    )
    add_figure(FIG_DIR / 'fig01_mapa_putumayo.png', width_cm=14)
    add_caption('Figura', 1, 'Ubicación del pueblo Inga en el Putumayo')
    add_note('Elaboración propia con base en datos de OpenStreetMap contributors (ODbL).')

    add_paragraph('Planteamiento del trabajo', style=S_H2)
    add_rich_paragraph(
        "El problema técnico que aborda el presente trabajo es la construcción de un "
        "sistema de traducción automática Inga-Español utilizable para una lengua que, "
        "antes de este proyecto, dispone de menos de 5.000 pares paralelos publicados en la "
        "literatura académica y de ningún sistema de traducción comercial o académico "
        "funcional. Este contexto define una situación de recursos extremadamente bajos que "
        "exige estrategias específicas distintas de las aplicadas a pares lingüísticos con "
        "abundancia de datos."
    )
    add_rich_paragraph(
        "La pregunta de investigación que orienta el trabajo se formula en los siguientes "
        "términos: *¿cuál aproximación, el ajuste fino de un modelo de traducción "
        "multilingüe preentrenado mediante técnicas eficientes en parámetros, o el uso de "
        "un modelo de lenguaje de frontera potenciado con recuperación aumentada de "
        "información, resulta más efectiva para traducir del Inga al Español y viceversa "
        "cuando los datos paralelos disponibles son extremadamente escasos?* Esta "
        "formulación tiene dos implicaciones metodológicas. La primera es que no se "
        "presume a priori la superioridad de una aproximación sobre la otra: ambas "
        "representan paradigmas contemporáneos con evidencia favorable en distintos "
        "escenarios, y el trabajo contribuye evidencia comparativa directa. La segunda es "
        "que se apuesta por mantener la formulación neutra respecto a modelos o versiones "
        "específicas, de modo que la pregunta sobreviva a la evolución tecnológica del "
        "campo durante el desarrollo del proyecto."
    )
    add_rich_paragraph(
        "La propuesta general de solución consiste en el desarrollo en paralelo de ambas "
        "aproximaciones sobre un corpus bidialectal construido a partir de recursos "
        "comunitarios, textos paralelos existentes y corpus de lenguas quechuas "
        "emparentadas. La comparación se realiza mediante métricas automáticas estándar "
        "(BLEU, chrF++, BERTScore) y mediante validación cualitativa con hablantes nativos "
        "del Inga. Los detalles arquitecturales y metodológicos se presentan en el "
        "Capítulo 3."
    )
    add_rich_paragraph(
        "El alcance del TFM se limita a un piloto experimental local, ejecutable sobre "
        "hardware personal, y no a un sistema de producción. Se da cobertura explícita a "
        "los dos dialectos principales de la lengua, Alto Putumayo y Medio Putumayo, "
        "mediante fuentes documentales específicas de cada zona. Se establece como meta "
        "mínima la construcción de un corpus de 5.000 pares de oraciones paralelas, con una "
        "meta deseable de 10.000 pares al cierre del proyecto. La liberación de los "
        "recursos como bienes comunes para la comunidad Inga queda planteada como "
        "resultado natural del trabajo y como línea de trabajo ulterior, sin constituir un "
        "objetivo central de evaluación."
    )

    # Figura 2 al cierre de Planteamiento: arquitectura general
    add_rich_paragraph(
        "La arquitectura general del sistema comparativo propuesto se ilustra en la "
        "Figura 2, donde se presentan las dos líneas experimentales que convergen en la "
        "evaluación comparativa final."
    )
    add_figure(FIG_DIR / 'fig02_arquitectura_general.png', width_cm=15)
    add_caption('Figura', 2, 'Arquitectura general del sistema comparativo de traducción automática Inga-Español')
    add_note('Elaboración propia.')

    add_paragraph('Estructura del trabajo', style=S_H2)
    add_rich_paragraph(
        "El presente documento se organiza en cinco capítulos, más las secciones de "
        "referencias bibliográficas y los anexos técnicos. El Capítulo 1 introduce la "
        "motivación del proyecto, el planteamiento del problema y la estructura general del "
        "trabajo. El Capítulo 2 desarrolla el contexto del problema, incluyendo la "
        "situación sociolingüística del Inga, el marco legal colombiano e internacional "
        "aplicable y los fundamentos técnicos de la traducción automática de bajos "
        "recursos, y presenta una revisión crítica del estado del arte en traducción "
        "automática de lenguas indígenas, con énfasis particular en los trabajos recientes "
        "sobre Quechua, que constituye el antecedente más cercano al Inga por pertenecer a "
        "la misma familia lingüística. El Capítulo 3 expone el objetivo general, los "
        "objetivos específicos y la metodología del trabajo, organizada en siete fases y "
        "acompañada del cronograma del proyecto y la descripción de la infraestructura "
        "computacional empleada. El Capítulo 4 presenta el desarrollo específico de la "
        "contribución; en la presente Entrega 1 se documentan los avances alcanzados al "
        "cierre de las primeras fases del proyecto: la configuración del entorno "
        "computacional, el inventario y procesamiento de los recursos lingüísticos "
        "primarios, el inicio de la construcción del corpus paralelo y el diseño de la base "
        "de conocimiento para la aproximación basada en recuperación aumentada. El "
        "Capítulo 5 recoge las conclusiones y las líneas de trabajo futuro; su contenido "
        "íntegro se presenta en la Entrega Final del TFM. Finalmente, se incluyen las "
        "referencias bibliográficas consultadas, siguiendo la norma APA séptima edición, y "
        "un anexo con el enlace al repositorio público de código y datos del proyecto."
    )


# ---------------------------------------------------------------------------
# Contenido completo: leemos del Markdown para NO duplicar 20+ paragrafos aqui
# ---------------------------------------------------------------------------

MD_PATH = BASE / 'entrega1' / 'TFM_grupal_entrega1.md'
MD_TEXT = MD_PATH.read_text(encoding='utf-8')


def extract_section(title_regex):
    """Extrae el texto entre un heading y el siguiente heading del mismo o mayor nivel."""
    m = re.search(title_regex, MD_TEXT)
    if not m:
        return ''
    start = m.end()
    # Nivel inferido de los # iniciales del match
    matched = m.group(0)
    hashes = re.match(r'\n(#+)', matched)
    level = len(hashes.group(1)) if hashes else 1
    if level < 1:
        level = 1
    next_pat = r'\n#{1,' + str(level) + r'}\s'
    next_m = re.search(next_pat, MD_TEXT[start:])
    end = start + next_m.start() if next_m else len(MD_TEXT)
    return MD_TEXT[start:end].strip()


def emit_paragraphs(text):
    """Emite parrafos de Markdown (separados por linea en blanco). Ignora tablas,
    figuras, rotulos de tablas, notas - esas se manejan aparte."""
    # Separar por linea en blanco
    blocks = re.split(r'\n\s*\n', text.strip())
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        # Filtrar bloques que son tablas, figuras, captions o notas
        if b.startswith('|') or b.startswith('!['):
            continue
        if b.startswith('**Tabla ') or b.startswith('**Figura '):
            continue
        if b.startswith('*Nota.'):
            continue
        if re.match(r'^\s*\*[^*]+\*\s*$', b):
            # Solo italic en linea (probable caption title)
            continue
        # Listas con '-' al inicio de linea: tratamos como ListParagraph
        if re.match(r'^\s*-\s', b.split('\n')[0]):
            # Bullet list
            lines = [re.sub(r'^\s*-\s+', '', ln) for ln in b.split('\n') if ln.strip()]
            for ln in lines:
                add_rich_paragraph(ln, style=S_LIST)
            continue
        # Lista numerada
        if re.match(r'^\s*\d+\.\s', b.split('\n')[0]):
            lines = [re.sub(r'^\s*\d+\.\s+', '', ln) for ln in b.split('\n') if ln.strip()]
            for ln in lines:
                add_rich_paragraph(ln, style=S_LIST)
            continue
        # Parrafo normal (colapsar saltos de linea internos a espacio)
        b = re.sub(r'\s*\n\s*', ' ', b)
        add_rich_paragraph(b)


# ---------------------------------------------------------------------------
# 6. CAPITULO 2 - CONTEXTO Y ESTADO DEL ARTE
# ---------------------------------------------------------------------------
def build_cap2():
    add_paragraph('Contexto y estado del arte', style=S_H1, page_break_before=True)

    add_paragraph('Contexto del problema', style=S_H2)

    add_paragraph('La lengua Inga y su situación en el Putumayo', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.1\.1[^\n]*\n'))
    # Figura 3: variantes dialectales
    add_rich_paragraph(
        "La distinción dialectal entre Alto Putumayo y Medio Putumayo, con ejemplos "
        "léxicos tomados directamente del *Diccionario Inga* (Tandioy Jansasoy et al., "
        "1997), se sintetiza en la Figura 3."
    )
    add_figure(FIG_DIR / 'fig03_dialectos_ap_mp.png', width_cm=15)
    add_caption('Figura', 3, 'Variantes dialectales del Inga: Alto Putumayo y Medio Putumayo')
    add_note('Elaboración propia a partir del Diccionario Inga (Tandioy Jansasoy et al., 1997).')

    add_paragraph('Marco legal-político en Colombia y contexto internacional', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.1\.2[^\n]*\n'))

    add_paragraph('Traducción automática de bajos recursos: fundamentos', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.1\.3[^\n]*\n'))

    add_paragraph('Transfer learning y recuperación aumentada: definiciones', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.1\.4[^\n]*\n'))

    add_paragraph('Estado del arte', style=S_H2)

    add_paragraph('Procesamiento del lenguaje natural para lenguas indígenas de América Latina', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.2\.1[^\n]*\n'))

    add_paragraph('Traducción automática de lenguas indígenas colombianas', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.2\.2[^\n]*\n'))

    add_paragraph('Traducción automática para Quechua: el caso cercano al Inga', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.2\.3[^\n]*\n'))

    add_paragraph('Modelos de lenguaje de frontera para traducción', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.2\.4[^\n]*\n'))

    add_paragraph('Recuperación aumentada aplicada a traducción', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.2\.5[^\n]*\n'))

    add_paragraph('Técnicas de ajuste fino eficiente en parámetros', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 2\.2\.6[^\n]*\n'))

    add_paragraph('Modelos base candidatos: análisis comparativo', style=S_H3)
    add_rich_paragraph(
        "La selección del modelo multilingüe preentrenado que servirá como base para el "
        "ajuste fino constituye una decisión arquitectural central del proyecto. Tres "
        "familias de modelos merecen consideración: NLLB-200 de Meta, MADLAD-400 de Google "
        "y TranslateGemma de Google DeepMind. A continuación se presenta una comparativa "
        "sintética de sus características técnicas en la Tabla 2."
    )
    add_caption('Tabla', 2,
        'Comparativa de modelos multilingües candidatos para la adaptación al par Inga-Español')
    add_table_from_rows(
        headers=['Modelo', 'Parámetros', 'Lenguas', 'Quechua incluido',
                 'Licencia', 'Arquitectura', 'Ajustable en M4 Max 128 GB'],
        rows=[
            ['NLLB-200-3.3B (NLLB Team, 2022, 2024)', '3.3 mil millones', '200',
             'Sí (quy_Latn)', 'CC BY-NC 4.0', 'Encoder-decoder',
             'Sí, permite incluso el fine-tuning completo'],
            ['NLLB-200-distilled-600M', '600 millones', '200', 'Sí',
             'CC BY-NC 4.0', 'Encoder-decoder', 'Sí, con amplio margen'],
            ['MADLAD-400-10B (Kudugunta et al., 2023)', '10.7 mil millones', '450+',
             'Sí (qu)', 'Apache 2.0', 'T5', 'Sí, con ajuste fino eficiente'],
            ['TranslateGemma-12B (Finkelstein et al., 2026)', '12 mil millones',
             'Multilingüe', 'Parcial', 'Gemma License', 'Decoder-only',
             'Sí, con ajuste fino eficiente'],
        ],
    )
    add_note('Elaboración propia con base en la documentación técnica publicada por '
             'los autores respectivos.')
    add_rich_paragraph(
        "La decisión metodológica del presente proyecto consiste en adoptar "
        "**NLLB-200-distilled-600M** como modelo principal para la fase de prototipado "
        "rápido, por su menor requerimiento de cómputo y tiempo de iteración, y "
        "**NLLB-200-3.3B** como modelo principal para los experimentos finales. La "
        "justificación es triple. Primero, NLLB-200 es el modelo dominante en las "
        "competiciones AmericasNLP de los últimos años, tal como evidencian los trabajos "
        "de Garcia Gilabert et al. (2024), Attieh et al. (2024) y DeGenaro y Lupicki "
        "(2024), lo que asegura compatibilidad metodológica con el estado del arte. "
        "Segundo, incluye explícitamente Quechua Ayacucho (quy_Latn) entre sus 200 "
        "lenguas soportadas, habilitando transferencia directa cross-lingual hacia el "
        "Inga. Tercero, la versión de 3.3 mil millones de parámetros resulta ajustable de "
        "manera completa o mediante LoRA en la estación local disponible para el proyecto "
        "(Apple M4 Max con 128 GB de RAM unificada), eliminando la dependencia de "
        "plataformas cloud."
    )

    add_paragraph('Conclusiones del capítulo', style=S_H2)
    emit_paragraphs(extract_section(r'\n## 2\.3[^\n]*\n'))


# ---------------------------------------------------------------------------
# 7. CAPITULO 3 - OBJETIVOS Y METODOLOGIA
# ---------------------------------------------------------------------------
def build_cap3():
    add_paragraph('Objetivos concretos y metodología de trabajo', style=S_H1,
                  page_break_before=True)

    add_paragraph('Objetivo general', style=S_H2)
    emit_paragraphs(extract_section(r'\n## 3\.1[^\n]*\n'))

    add_paragraph('Objetivos específicos', style=S_H2)
    emit_paragraphs(extract_section(r'\n## 3\.2[^\n]*\n'))

    add_paragraph('Metodología del trabajo', style=S_H2)

    add_paragraph('Enfoque metodológico', style=S_H3)
    emit_paragraphs(extract_section(r'\n### 3\.3\.1[^\n]*\n'))

    add_paragraph('Fases del proyecto', style=S_H3)
    # Texto introductorio
    add_rich_paragraph(
        "El trabajo se organiza en siete fases con una correspondencia uno a uno con los "
        "objetivos específicos enunciados en la sección 3.2. El detalle pedagógico y "
        "técnico de cada fase se resume a continuación; la ejecución concreta se documenta "
        "en el Capítulo 4."
    )
    # 7 fases como parrafos
    fases_texts = [
        "La **Fase 1 (Configuración del entorno)** establece el entorno computacional "
        "local sobre hardware Apple Silicon, instala las librerías centrales de "
        "procesamiento del lenguaje natural (*Transformers*, *PEFT*, *Accelerate*, "
        "*sentence-transformers*, *sacrebleu*, *datasets*) y valida la aceleración por "
        "hardware (MPS en Apple Silicon). Se realiza una inferencia zero-shot de prueba "
        "con un modelo multilingüe preentrenado como criterio de cierre de esta fase.",

        "La **Fase 2 (Construcción del corpus paralelo)** se desarrolla sobre las cinco "
        "fuentes primarias del Inga descritas en el Capítulo 2 y en el Capítulo 4, "
        "mediante un pipeline de segmentación, detección de idioma por bloque, alineación "
        "canónica o heurística, normalización ortográfica y partición en conjuntos de "
        "entrenamiento, validación y prueba. El pipeline global se ilustra en la Figura 4.",
    ]
    add_rich_paragraph(fases_texts[0])
    add_rich_paragraph(fases_texts[1])
    # Figura 4
    add_figure(FIG_DIR / 'fig04_pipeline_corpus.png', width_cm=15)
    add_caption('Figura', 4, 'Pipeline de construcción del corpus paralelo Inga-Español')
    add_note('Elaboración propia.')

    add_rich_paragraph(
        "La **Fase 3 (Base de conocimiento para recuperación aumentada)** construye tres "
        "índices independientes: un índice léxico derivado del diccionario, un índice "
        "gramatical derivado de la gramática pedagógica y del apéndice morfosintáctico, "
        "y un índice de ejemplos paralelos derivado del corpus alineado. La indexación "
        "emplea embeddings multilingües y una base de datos vectorial local. Se especifican "
        "estrategias de control de contexto (top-k, umbrales de similitud, presupuestos "
        "de tokens, reranking con cross-encoder) para evitar la saturación del prompt del "
        "modelo generativo."
    )
    add_rich_paragraph(
        "La **Fase 4 (Ajuste fino del modelo multilingüe)** ejecuta el ajuste fino "
        "eficiente en parámetros del modelo base seleccionado, aprovechando el código de "
        "lengua Quechua Ayacucho (quy_Latn) ya presente en el modelo como base para la "
        "transferencia hacia el Inga. El pipeline se ilustra en la Figura 5. Se contemplan "
        "experimentos de ablation sobre dimensionalidad de los adaptadores, magnitud de la "
        "tasa de aprendizaje y uso de augmentación sintética por back-translation."
    )
    add_figure(FIG_DIR / 'fig05_pipeline_finetuning.png', width_cm=15)
    add_caption('Figura', 5, 'Pipeline de ajuste fino eficiente del modelo de traducción multilingüe')
    add_note('Elaboración propia.')

    add_rich_paragraph(
        "La **Fase 5 (Pipeline LLM + RAG)** implementa la segunda línea experimental: un "
        "sistema de traducción basado en un modelo de lenguaje de frontera cuyo prompt es "
        "enriquecido en tiempo de inferencia con la información relevante recuperada desde "
        "los tres índices de la base de conocimiento. El pipeline se ilustra en la Figura 6."
    )
    add_figure(FIG_DIR / 'fig06_pipeline_rag.png', width_cm=15)
    add_caption('Figura', 6,
        'Pipeline de traducción basado en modelo de lenguaje de frontera con recuperación aumentada')
    add_note('Elaboración propia.')

    add_rich_paragraph(
        "La **Fase 6 (Evaluación comparativa)** evalúa sistemáticamente todas las "
        "configuraciones definidas en la Tabla 4 mediante métricas automáticas estándar "
        "(BLEU, chrF++, BERTScore) y sesiones de validación humana con hablantes nativos "
        "de Inga. Los resultados se sintetizan en el Capítulo 4 y su discusión, en la "
        "Entrega Final."
    )
    add_rich_paragraph(
        "La **Fase 7 (Despliegue local y documentación)** prepara el sistema final como "
        "una aplicación local reproducible y documenta el marco metodológico como aporte "
        "reutilizable."
    )

    add_paragraph('Cronograma', style=S_H3)
    add_rich_paragraph(
        "El cronograma global del proyecto se muestra en la Figura 8. Las fases presentan "
        "traslape planificado cuando las dependencias lo permiten: en particular, la "
        "construcción del corpus (Fase 2) se inicia en paralelo con la configuración del "
        "entorno y se prolonga durante varios meses, alimentando tanto al ajuste fino "
        "(Fase 4) como al sistema RAG (Fases 3 y 5) a medida que avanza."
    )
    add_figure(FIG_DIR / 'fig08_cronograma_gantt.png', width_cm=15)
    add_caption('Figura', 8, 'Cronograma del proyecto, distribuido por fases y fechas')
    add_note('Elaboración propia.')

    add_paragraph('Infraestructura de cómputo', style=S_H3)
    add_rich_paragraph(
        "La infraestructura de cómputo empleada se detalla en la Tabla 5. La decisión de "
        "operar sobre hardware local de alta capacidad, en lugar de plataformas cloud, se "
        "fundamenta en tres consideraciones: reproducibilidad del entorno, soberanía de "
        "los datos lingüísticos de la comunidad Inga y predictibilidad del costo del "
        "proyecto. La API del modelo de lenguaje de frontera se utiliza únicamente para la "
        "línea experimental correspondiente."
    )
    add_caption('Tabla', 5, 'Infraestructura de cómputo del proyecto')
    add_table_from_rows(
        headers=['Recurso', 'Especificación', 'Uso principal'],
        rows=[
            ['Estación de trabajo local', 'Apple M4 Max, 128 GB RAM unificada',
             'Inferencia y ajuste fino eficiente del modelo multilingüe; indexación y '
             'recuperación vectorial; ejecución de todos los notebooks del proyecto.'],
            ['API de modelo de lenguaje de frontera',
             'Anthropic (modelo vigente al cierre del TFM)',
             'Pipeline de traducción con recuperación aumentada; línea experimental LLM.'],
            ['Almacenamiento vectorial local',
             'FAISS o ChromaDB (decisión técnica en Fase 3)',
             'Indexación de la base de conocimiento lingüístico del Inga.'],
            ['Control de versiones', 'Git y GitHub',
             'Código fuente, notebooks, documentación del proyecto.'],
        ],
    )
    add_note('Elaboración propia.')

    add_paragraph('Configuraciones experimentales a evaluar', style=S_H3)
    add_rich_paragraph(
        "La Fase 6 evalúa al menos cinco configuraciones experimentales, cuyo diseño se "
        "resume en la Tabla 4. Las configuraciones permiten aislar el efecto de cada "
        "técnica central (ajuste fino, recuperación aumentada, su combinación) y comparar "
        "líneas de base zero-shot con las aproximaciones adaptadas específicamente al Inga."
    )
    add_caption('Tabla', 4, 'Configuraciones experimentales a evaluar en la Fase 6 del proyecto')
    add_table_from_rows(
        headers=['Config.', 'Modelo', 'Técnica', 'Recursos utilizados'],
        rows=[
            ['A', 'Modelo multilingüe base (p. ej., NLLB-200-3.3B)',
             'Traducción zero-shot con código de lengua más cercano (quy_Latn)', 'N/A'],
            ['B', 'Modelo multilingüe base',
             'Ajuste fino eficiente (LoRA) sobre corpus Inga bidialectal',
             'Corpus paralelo AP + MP'],
            ['C', 'Modelo de lenguaje de frontera', 'Prompt zero-shot', 'N/A'],
            ['D', 'Modelo de lenguaje de frontera',
             'Recuperación aumentada multi-índice (léxico, gramatical, ejemplos)',
             'Base de conocimiento del Inga'],
            ['E', 'Modelo multilingüe ajustado (config. B)',
             'Recuperación aumentada aplicada en inferencia',
             'Corpus + base de conocimiento'],
        ],
    )
    add_note('Elaboración propia.')


# ---------------------------------------------------------------------------
# 8. CAPITULO 4 - DESARROLLO
# ---------------------------------------------------------------------------
def build_cap4():
    add_paragraph('Desarrollo específico de la contribución', style=S_H1,
                  page_break_before=True)

    add_paragraph('Estado de avance al cierre de la Entrega 1', style=S_H2)

    add_paragraph('Fase 1. Configuración del entorno computacional', style=S_H3)
    add_rich_paragraph(
        "Se configuró el entorno de desarrollo sobre la estación local Apple M4 Max "
        "(128 GB de memoria unificada, macOS Darwin 25.3.0). Se instalaron las librerías "
        "centrales del proyecto, *transformers*, *peft*, *accelerate*, "
        "*sentence-transformers*, *sacrebleu*, *datasets*, *anthropic*, *sentencepiece*, "
        "*matplotlib*, *pandas* y *numpy*, sobre Python 3.11. Se validó la disponibilidad "
        "de la aceleración por hardware Metal Performance Shaders (MPS) mediante PyTorch. "
        "Se descargó y cargó satisfactoriamente el modelo facebook/nllb-200-distilled-600M "
        "como modelo de trabajo para prototipado rápido, y se ejecutó una inferencia "
        "zero-shot de validación en el par Español-Quechua Ayacucho (spa_Latn hacia "
        "quy_Latn), criterio de cierre de esta fase definido en el Capítulo 3. El "
        "procedimiento completo se documenta en el Notebook 00 del repositorio del "
        "proyecto, referenciado en el Anexo A."
    )

    add_paragraph('Fase 2. Construcción del corpus paralelo', style=S_H3)
    add_rich_paragraph(
        "La construcción del corpus paralelo Inga-Español se apoya en cinco fuentes "
        "primarias previamente extraídas a formato Markdown mediante reconocimiento óptico "
        "de caracteres (OCR). El inventario consolidado se muestra en la Tabla 3."
    )
    add_caption('Tabla', 3, 'Inventario de recursos lingüísticos primarios utilizados en la construcción del corpus')
    add_table_from_rows(
        headers=['Recurso', 'Dialecto', 'Páginas', 'Registro', 'Alineación', 'Unidades detectadas'],
        rows=[
            ['Diccionario Inga (Tandioy Jansasoy et al., 1997)', 'AP + MP (marcado)',
             '177', 'Léxico', 'N/A', '817 entradas'],
            ['Gramática Pedagógica del Inga (Levinsohn y Mongui)',
             'AP principalmente', '228', 'Didáctico', 'N/A', 'N/A'],
            ['Apéndice morfosintáctico (Rosetta Project)', 'N/A', '26', 'Técnico',
             'N/A', 'N/A'],
            ['El Nuevo Testamento en Inga (Wycliffe Bible Translators, 2012)',
             'AP (probable)', '595', 'Bíblico-literario', 'Versículo', '3.093 segmentos'],
            ['Antihua Pacay Gentecunapa Parlocuna (Jamioy Yanangona de Peña, 1985)',
             'MP (Mocoa)', '68', 'Narrativo oral', 'Bloque', '4 pares iniciales'],
        ],
    )
    add_note(
        'Elaboración propia a partir de los notebooks 01 y 02 del presente trabajo. La '
        'cifra total de páginas OCR asciende a 1.094. Las unidades detectadas '
        'corresponden a la primera pasada con heurísticas conservadoras y son '
        'susceptibles de incremento en iteraciones posteriores.'
    )
    add_rich_paragraph(
        "El análisis exploratorio inicial (Notebook 01) cuantificó los cinco recursos y "
        "produjo un total acumulado de 1.094 páginas OCR, 319.666 palabras aproximadas y "
        "46.598 líneas. Del *Diccionario Inga* se extrajeron 817 entradas léxicas "
        "estructuradas, con lema, categoría gramatical y glosa en español, que conforman "
        "la base preliminar del índice léxico del sistema de recuperación aumentada. El "
        "parseo utilizó heurísticas conservadoras sobre la estructura del diccionario; "
        "iteraciones subsiguientes permitirán ampliar esta cifra."
    )
    add_rich_paragraph(
        "La distribución de longitudes de los versículos del Nuevo Testamento en Inga se "
        "muestra en la Figura 7. Se identificaron 2.837 marcadores de versículo y, tras "
        "filtrar segmentos válidos (entre 3 y 120 palabras), se obtuvieron 2.791 "
        "versículos con longitud representativa y una longitud media de 32.75 palabras por "
        "versículo, consistente con la naturaleza narrativo-literaria del texto bíblico y "
        "con la morfología aglutinante del Inga."
    )
    add_figure(FIG_DIR / 'fig07_distribucion_longitud_nt.png', width_cm=15)
    add_caption('Figura', 7, 'Distribución de longitudes de los versículos del Nuevo Testamento en Inga')
    add_note(
        'Elaboración propia a partir del Notebook 01 del presente trabajo. Fuente del '
        'texto: *El Nuevo Testamento en el idioma Inga de Colombia*, segunda edición, '
        'Wycliffe Bible Translators, 2012.'
    )
    add_rich_paragraph(
        "La extracción y alineación inicial del corpus (Notebook 02) produjo dos salidas. "
        "Del Nuevo Testamento Inga se generaron 3.093 segmentos estructurados, preparados "
        "para alineación canónica con una versión del Nuevo Testamento en español "
        "efectivamente de dominio público (Reina-Valera 1909 como primera opción) en la "
        "Entrega 2. De las narrativas *Antihua Pacay* se produjo un primer conjunto de "
        "cuatro pares paralelos bloque-a-bloque mediante un detector heurístico de idioma "
        "basado en la densidad de sufijos aglutinantes típicos del Inga. Esta cifra "
        "preliminar es conservadora: la estructura real del texto intercala múltiples "
        "párrafos cortos por episodio narrativo, y una detección más refinada, con "
        "ventanas deslizantes y modelos de detección de lengua, permitirá incrementar "
        "sustantivamente el conjunto de pares en la siguiente iteración."
    )

    add_paragraph('Fase 3. Diseño de la base de conocimiento', style=S_H3)
    add_rich_paragraph(
        "El diseño de la base de conocimiento para el sistema de recuperación aumentada "
        "quedó establecido conforme a la arquitectura descrita en el Capítulo 3 (tres "
        "índices independientes: léxico, gramatical y de ejemplos paralelos). La primera "
        "pieza operativa de esta fase es el volcado del *Diccionario Inga* a formato "
        "JSONL, realizado en el Notebook 01, con 817 entradas léxicas estructuradas que "
        "constituyen la base preliminar del índice léxico. La indexación vectorial "
        "propiamente dicha, mediante embeddings multilingües y una base de datos vectorial "
        "local (FAISS o ChromaDB según evaluación técnica), se ejecuta en la siguiente "
        "iteración del proyecto."
    )

    add_paragraph('Repositorio de código y datos', style=S_H2)
    add_rich_paragraph(
        "El código desarrollado para la presente Entrega 1 se organiza en tres notebooks "
        "documentados en el Anexo A. Los datos generados, "
        "diccionario_inga.jsonl, nt_inga_alineado.jsonl, antihua_pacay_alineado.jsonl y "
        "estadisticas_corpus.json, acompañan a los notebooks en el mismo repositorio y son "
        "reproducibles íntegramente mediante su re-ejecución sobre los recursos primarios "
        "referenciados."
    )

    add_paragraph('Próximos pasos hacia la Entrega 2', style=S_H2)
    add_rich_paragraph(
        "Los siguientes pasos inmediatos tras la Entrega 1 se agrupan en cuatro líneas de "
        "trabajo. Primero, la alineación canónica del Nuevo Testamento Inga con una "
        "versión en español de dominio público (Reina-Valera 1909), lo que se espera que "
        "incremente el corpus en aproximadamente 7.900 pares paralelos adicionales. "
        "Segundo, el refinamiento del detector de idioma y del algoritmo de alineación de "
        "*Antihua Pacay* para maximizar el aprovechamiento de las narrativas del Medio "
        "Putumayo. Tercero, la indexación vectorial de la base de conocimiento lingüístico "
        "mediante embeddings multilingües y la implementación del pipeline de "
        "recuperación. Cuarto, la ejecución del primer experimento de ajuste fino "
        "eficiente (LoRA) sobre el modelo multilingüe preentrenado, utilizando el corpus "
        "acumulado hasta ese momento, y el establecimiento de las primeras líneas base "
        "zero-shot para las configuraciones A y C de la Tabla 4."
    )


# ---------------------------------------------------------------------------
# 9. CAPITULO 5 - CONCLUSIONES
# ---------------------------------------------------------------------------
def build_cap5():
    add_paragraph('Conclusiones y trabajo futuro', style=S_H1, page_break_before=True)
    add_paragraph('Conclusiones', style=S_H2)
    add_rich_paragraph(
        "El contenido de este capítulo se presenta en la Entrega Final, una vez ejecutadas "
        "las Fases 4 a 7 del proyecto. La presente Entrega 1 abarca el planteamiento del "
        "problema, el estado del arte, la definición de objetivos y metodología, y el "
        "inicio de la construcción del corpus y la configuración del entorno experimental."
    )
    add_paragraph('Líneas de trabajo futuro', style=S_H2)
    add_rich_paragraph(
        "El contenido de esta sección se presenta en la Entrega Final."
    )


# ---------------------------------------------------------------------------
# 10. REFERENCIAS BIBLIOGRAFICAS
# ---------------------------------------------------------------------------
BIB_ENTRIES = [
    'Asamblea Nacional Constituyente de Colombia. (1991). *Constitución Política de Colombia*, Artículo 10. http://www.secretariasenado.gov.co/senado/basedoc/constitucion_politica_1991.html',
    'Attieh, J., Hopton, Z., Scherrer, Y., y Samardžić, T. (2024). System description of the NordicsAlps submission to the AmericasNLP 2024 machine translation shared task. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 150-158). Association for Computational Linguistics. https://aclanthology.org/2024.americasnlp-1.18/',
    'Cahyawijaya, S., Lovenia, H., y Fung, P. (2024). LLMs are few-shot in-context low-resource language learners. En *Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics (NAACL 2024)*. https://arxiv.org/abs/2403.16512',
    'Chen, J., Shu, P., Li, Y., Zhao, H., Jiang, H., Pan, Y., Zhou, Y., Liu, Z., Howe, L. C., y Liu, T. (2024). *QueEn: A large language model for Quechua-English translation* [arXiv preprint]. https://arxiv.org/abs/2412.05184',
    'Congreso de la República de Colombia. (2010). *Ley 1381 de 2010, por la cual se desarrollan los artículos 7°, 8°, 10 y 70 de la Constitución Política y se dictan normas sobre reconocimiento, fomento, protección, uso, preservación y fortalecimiento de las lenguas de los grupos étnicos de Colombia y sobre sus derechos lingüísticos y los de sus hablantes*. Diario Oficial No. 47.603. https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=38741',
    'de Gibert, O., Pugh, R., Marashian, A., Vazquez, R., Ebrahimi, A., Denisov, P., Rice, E., Gow-Smith, E., Prieto, J., Robles, M., Manrique, R., Moreno, O., Lino, A., Coto-Solano, R., Alvarez, A., Agüero-Torales, M., Ortega, J. E., Chiruzzo, L., Oncevay, A., Rijhwani, S., von der Wense, K., y Mager, M. (2025). Findings of the AmericasNLP 2025 shared tasks on machine translation, creation of educational material, and translation metrics for indigenous languages of the Americas. En *Proceedings of the Fifth Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP)* (pp. 134-152). https://aclanthology.org/2025.americasnlp-1.16/',
    'DeGenaro, D., y Lupicki, T. (2024). Experiments in Mamba sequence modeling and NLLB-200 fine-tuning for low resource multilingual machine translation. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 188-194). https://aclanthology.org/2024.americasnlp-1.22/',
    'Dettmers, T., Pagnoni, A., Holtzman, A., y Zettlemoyer, L. (2023). QLoRA: Efficient finetuning of quantized LLMs. En *Advances in Neural Information Processing Systems 36 (NeurIPS 2023)*. https://arxiv.org/abs/2305.14314',
    'Dhawan, A., Driggers-Ellis, C., Grant, C., y Wang, D. Z. (2026). *Improving indigenous language machine translation with synthetic data and language-specific preprocessing* [arXiv preprint]. https://arxiv.org/abs/2601.03135',
    'Doran, G. T. (1981). There\'s a S.M.A.R.T. way to write management\'s goals and objectives. *Management Review (AMA FORUM), 70*(11), 35-36.',
    'Ebrahimi, A., de Gibert, O., Vazquez, R., Coto-Solano, R., Denisov, P., Pugh, R., Mager, M., Oncevay, A., Chiruzzo, L., von der Wense, K., y Rijhwani, S. (2024). Findings of the AmericasNLP 2024 shared task on machine translation. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 236-246). https://aclanthology.org/2024.americasnlp-1.28/',
    'Enis, M., y Hopkins, M. (2024). *From LLM to NMT: Advancing low-resource machine translation with Claude* [arXiv preprint]. https://arxiv.org/abs/2404.13813',
    'Finkelstein, M., Caswell, I., Domhan, T., Peter, J.-T., Juraska, J., Riley, P., Deutsch, D., Kovacs, G., Dilanni, C., Cherry, C., Briakou, E., Nielsen, E., Luo, J., Black, K., Mullins, R., Agrawal, S., Xu, W., Kats, E., Jaskiewicz, S., Freitag, M., y Vilar, D. (2026). *TranslateGemma: Technical report* [arXiv preprint]. https://arxiv.org/abs/2601.09012',
    'Garcia Gilabert, J., Sant, A., Escolano, C., De Luca Fornaciari, F., Mash, A., y Melero, M. (2024). BSC submission to the AmericasNLP 2024 shared task. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 143-149). https://aclanthology.org/2024.americasnlp-1.17/',
    'Hendy, A., Abdelrehim, M., Sharaf, A., Raunak, V., Gabr, M., Matsushita, H., Kim, Y. J., Afify, M., y Awadalla, H. H. (2023). *How good are GPT models at machine translation? A comprehensive evaluation* [arXiv preprint]. https://arxiv.org/abs/2302.09210',
    'Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., y Chen, W. (2022). LoRA: Low-rank adaptation of large language models. En *International Conference on Learning Representations (ICLR 2022)*. https://arxiv.org/abs/2106.09685',
    'Jamioy Yanangona de Peña, O. (1985). *Antihua Pacay Gentecunapa parlocuna: Tradiciones de los Inganos Pacayes* (Cartilla Inga, Serie: Historias Tradicionales, Edición provisional). Proyecto Bilingüe Inga-Castellano del Vicariato Apostólico de Sibundoy; SIL International Language and Culture Archives.',
    'Kudugunta, S., Caswell, I., Zhang, B., Garcia, X., Choquette-Choo, C. A., Lee, K., Xin, D., Kusupati, A., Stella, R., Bapna, A., y Firat, O. (2023). MADLAD-400: A multilingual and document-level large audited dataset. En *Advances in Neural Information Processing Systems 36 (NeurIPS 2023 Datasets and Benchmarks Track)*. https://arxiv.org/abs/2309.04662',
    'Levinsohn, S. H., y Mongui, R. (s.f.). *Inga Kichwa: Una gramática pedagógica del Inga (Partes 1 y 2)*. Instituto Lingüístico de Verano.',
    'Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., y Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. En *Advances in Neural Information Processing Systems 33 (NeurIPS 2020)*. https://arxiv.org/abs/2005.11401',
    'Liu, S.-Y., Wang, C.-Y., Yin, H., Molchanov, P., Wang, Y.-C. F., Cheng, K.-T., y Chen, M.-H. (2024). DoRA: Weight-decomposed low-rank adaptation. En *Proceedings of the 41st International Conference on Machine Learning (ICML 2024)*. https://arxiv.org/abs/2402.09353',
    'Mager, M., Mager, E., Kann, K., y Vu, N. T. (2023). Ethical considerations for machine translation of indigenous languages: Giving a voice to the speakers. En *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (ACL 2023)*. https://aclanthology.org/2023.acl-long.313/',
    'NLLB Team, Costa-jussà, M. R., Cross, J., Çelebi, O., Elbayad, M., Heafield, K., Heffernan, K., Kalbassi, E., Lam, J., Licht, D., Maillard, J., Sun, A., Wang, S., Wenzek, G., Youngblood, A., Akula, B., Barrault, L., Mejia Gonzalez, G., Hansanti, P., ... Wang, J. (2022). *No language left behind: Scaling human-centered machine translation* [arXiv preprint]. https://arxiv.org/abs/2207.04672',
    'NLLB Team, Costa-jussà, M. R., Cross, J., Çelebi, O., Elbayad, M., Heafield, K., Heffernan, K., Kalbassi, E., Lam, J., Licht, D., Maillard, J., Sun, A., Wang, S., Wenzek, G., Youngblood, A., Akula, B., Barrault, L., Mejia Gonzalez, G., Hansanti, P., ... Wang, J. (2024). Scaling neural machine translation to 200 languages. *Nature, 630*(8018), 841-846. https://doi.org/10.1038/s41586-024-07335-x',
    'Popović, M. (2017). chrF++: Words helping character n-grams. En *Proceedings of the Second Conference on Machine Translation (WMT 2017)* (pp. 612-618). https://aclanthology.org/W17-4770/',
    'Prieto, J., Martinez, C., Robles, M., Moreno, A., Palacios, S., y Manrique, R. (2024). Translation systems for low-resource Colombian indigenous languages: A first step towards cultural preservation. En *Proceedings of the 4th Workshop on NLP for Indigenous Languages of the Americas (AmericasNLP 2024)* (pp. 7-14). https://aclanthology.org/2024.americasnlp-1.2/',
    'Rei, R., De Souza, J. G. C., Alves, D., Zerva, C., Farinha, A. C., Glushkova, T., Lavie, A., Coheur, L., y Martins, A. F. T. (2022). COMET-22: Unbabel-IST 2022 submission for the metrics shared task. En *Proceedings of the Seventh Conference on Machine Translation (WMT 2022)* (pp. 578-585). https://aclanthology.org/2022.wmt-1.52/',
    'Salazar, I., Manrique, R., y Pereira Nunes, B. (2025). Machine translation strategies for low-resource Colombian indigenous languages. *SN Computer Science, 6*. https://doi.org/10.1007/s42979-025-04255-z',
    'Su, T., Peng, X., Thillainathan, S., Guzmán, D., Ranathunga, S., y Lee, E.-S. A. (2024). *Unlocking parameter-efficient fine-tuning for low-resource language translation* [arXiv preprint]. https://arxiv.org/abs/2404.04212',
    'Tandioy Jansasoy, F., Levinsohn, S. H., y Tandioy Chasoy, D. (1997). *Diccionario Inga* (Edición interina en el nuevo alfabeto). Comité de Educación Inga de la Organización Musu Runakuna.',
    'Tonja, A. L., Balouchzahi, F., Butt, S., Kolesnikova, O., Ceballos, H., Gelbukh, A., y Solorio, T. (2024). NLP progress in indigenous Latin American languages. En *Findings of the Association for Computational Linguistics: NAACL 2024*. https://arxiv.org/abs/2404.05365',
    'UNESCO. (2022). *World Atlas of Languages*. United Nations Educational, Scientific and Cultural Organization. https://en.wal.unesco.org/',
    'Wang, J., Meng, F., Zhang, Y., y Zhou, J. (2024). *Retrieval-augmented machine translation with unstructured knowledge* [arXiv preprint]. https://arxiv.org/abs/2412.04342',
    'Wycliffe Bible Translators. (2012). *Kaipimi Taita Dius Rimaku: El Nuevo Testamento en el idioma Inga de Colombia* (2ª ed.) [Bajo licencia Creative Commons BY-NC-ND 3.0].',
    'Zhang, S., Frey, B., y Bansal, M. (2022). How can NLP help revitalize endangered languages? A case study and roadmap for the Cherokee language. En *Proceedings of ACL 2022*. https://aclanthology.org/2022.acl-long.507/',
    'Zhang, T., Kishore, V., Wu, F., Weinberger, K. Q., y Artzi, Y. (2020). BERTScore: Evaluating text generation with BERT. En *International Conference on Learning Representations (ICLR 2020)*. https://arxiv.org/abs/1904.09675',
    'Zhu, W., Liu, H., Dong, Q., Xu, J., Huang, S., Kong, L., Chen, J., y Li, L. (2024). Multilingual machine translation with large language models: Empirical results and analysis. En *Findings of the Association for Computational Linguistics: NAACL 2024* (pp. 2765-2781). https://aclanthology.org/2024.findings-naacl.176/',
]


def build_bib():
    add_paragraph('Referencias bibliográficas', style=S_H1U, page_break_before=True)
    for entry in BIB_ENTRIES:
        add_rich_paragraph(entry, style=S_BIB if style_exists(S_BIB) else S_NORMAL,
                           alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)


# ---------------------------------------------------------------------------
# 11. ANEXO A
# ---------------------------------------------------------------------------
def build_anexo():
    add_paragraph('Anexo A. Código fuente y datos analizados', style=S_ANEX if style_exists(S_ANEX) else S_H1U,
                  page_break_before=True)
    add_rich_paragraph(
        "El código fuente del presente TFM se aloja en el repositorio "
        "https://github.com/Purakuna/tfm-inga-traduccion de la organización Purakuna, "
        "de acceso restringido durante la ejecución del proyecto, con el enlace "
        "comunicado al director del trabajo. La estructura del repositorio al cierre de "
        "la Entrega 1 se organiza según se describe a continuación."
    )
    add_rich_paragraph("La carpeta notebooks/ contiene los tres notebooks de Jupyter desarrollados:")
    add_rich_paragraph(
        "**notebooks/00_setup_entorno.ipynb**, configuración y validación del entorno local "
        "(Python, PyTorch con aceleración MPS, librerías centrales de procesamiento del "
        "lenguaje natural), más la descarga y prueba de inferencia zero-shot del modelo "
        "multilingüe preentrenado utilizado como base del proyecto.",
        style=S_LIST)
    add_rich_paragraph(
        "**notebooks/01_eda_recursos_base.ipynb**, análisis exploratorio de los cinco "
        "recursos lingüísticos primarios, parseo del *Diccionario Inga* a formato JSONL "
        "estructurado, cálculo de estadísticas agregadas del corpus y generación de la "
        "Figura 7 del presente documento.",
        style=S_LIST)
    add_rich_paragraph(
        "**notebooks/02_extraccion_corpus_NT.ipynb**, extracción y segmentación inicial "
        "del corpus paralelo a partir del Nuevo Testamento en Inga y de las narrativas "
        "*Antihua Pacay*.",
        style=S_LIST)
    add_rich_paragraph("La carpeta datos/ contiene las salidas estructuradas de los notebooks:")
    add_rich_paragraph(
        "**datos/diccionario_inga.jsonl**, 817 entradas léxicas con lema, categoría "
        "gramatical y glosa en español.",
        style=S_LIST)
    add_rich_paragraph(
        "**datos/nt_inga_alineado.jsonl**, 3.093 segmentos del Nuevo Testamento en Inga, "
        "preparados para alineación canónica en la Entrega 2.",
        style=S_LIST)
    add_rich_paragraph(
        "**datos/antihua_pacay_alineado.jsonl**, 4 pares bloque-a-bloque iniciales de las "
        "narrativas de Antihua Pacay.",
        style=S_LIST)
    add_rich_paragraph(
        "**datos/estadisticas_corpus.json**, estadísticas agregadas sobre los recursos "
        "primarios.",
        style=S_LIST)
    add_rich_paragraph(
        "La carpeta bibliografia/ contiene la base bibliográfica verificada del proyecto "
        "(refs_verificadas.md), con identificadores estables (DOI, arXiv ID, ACL Anthology "
        "URL) asociados a cada entrada."
    )
    add_rich_paragraph(
        "La carpeta entrega1/ contiene el documento principal de la presente entrega y los "
        "recursos gráficos asociados."
    )
    add_rich_paragraph(
        "**Licenciamiento.** El código desarrollado específicamente para el TFM se "
        "publica bajo licencia MIT. Los datos derivados de fuentes externas heredan las "
        "licencias de sus respectivas fuentes primarias: el *Nuevo Testamento en el "
        "idioma Inga de Colombia* se distribuye bajo licencia Creative Commons "
        "Atribución-NoComercial-SinObraDerivada 3.0 (Wycliffe Bible Translators, 2012); "
        "las narrativas *Antihua Pacay Gentecunapa Parlocuna* (Jamioy Yanangona de "
        "Peña, 1985) forman parte de los Archivos de Lengua y Cultura del SIL "
        "International, disponibles bajo términos de uso académico y de investigación."
    )


# ---------------------------------------------------------------------------
# INSERTAR FIGURAS 1, 2, 3 en secciones apropiadas
# ---------------------------------------------------------------------------
# Figura 1 va en 1.1 Motivación (antes de cerrar la intro, idealmente al final del 1er parrafo)
# Figura 2 va en 1.2 Planteamiento (al final)
# Figura 3 va en 2.1.1
# Esas las insertamos manualmente al final, despues de build_all, con enforcement de posicion.
# Para simplicidad, las insertamos al cierre de sus capitulos respectivos DENTRO de build_cap1/cap2
# Pero ya tenemos build_cap1 / cap2 definidos sin figs 1/2/3. Las inyectamos aqui:

def insert_fig_after_heading(heading_text, figure_path, figure_num, caption_text, note_text):
    """Busca el heading y tras el ultimo parrafo de su seccion inserta la figura."""
    # Por simplicidad: en vez de insertar a posteriori, anadirlas dentro de build_cap*
    pass


# ---------------------------------------------------------------------------
# Ejecutar
# ---------------------------------------------------------------------------
print('Building cover...'); build_cover()
print('Building resumen...'); build_resumen()
print('Building abstract...'); build_abstract()
print('Building indices...'); build_indices()
print('Building grupo...'); build_grupo()
print('Building cap1...'); build_cap1()
print('Building cap2...'); build_cap2()
print('Building cap3...'); build_cap3()
print('Building cap4...'); build_cap4()
print('Building cap5...'); build_cap5()
print('Building bib...'); build_bib()
print('Building anexo...'); build_anexo()

doc.save(str(DOCX_PATH))
print(f'\nGuardado: {DOCX_PATH}')
print(f'Tamano: {DOCX_PATH.stat().st_size} bytes')
