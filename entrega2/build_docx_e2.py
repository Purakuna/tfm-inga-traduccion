"""Genera entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx con SOLO los bloques que
cambian respecto a Entrega 1, formateados con los estilos UNIR para que
copiar y pegar al .docx final preserve el formato.

Diseno consciente:
- INPUT (read-only): plantilla UNIR original en /Users/william-santos/Downloads/plantilla_grupal.docx
- OUTPUT: entrega2/TFM_Entrega2_BLOQUES_NUEVOS.docx
- Si el OUTPUT existe, hace backup con timestamp antes de sobreescribir.
- NO toca el .docx de Entrega 1 (TFM_Entrega1_EslavaSantos.docx queda intacto).
- NO genera el documento completo: solo emite los bloques que cambian.
- Cada bloque comienza con un separador visible "INSERTAR EN: <ubicacion>"
  para que el usuario sepa donde pegarlo.

Captions con formato APA correcto (dos parrafos):
  Figura N            <- en su propia linea, negrita
  Titulo en cursiva   <- linea siguiente, italica, sin punto al final

Esto resuelve el feedback del director sobre el formato de figuras y tablas
de Entrega 1, que tenia identificador y titulo en una misma linea sin cursiva.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT


# Rutas
BASE = Path(__file__).resolve().parents[1]
INPUT_TEMPLATE = Path('/Users/william-santos/Downloads/plantilla_grupal.docx')
MD_PATH = BASE / 'entrega2' / 'TFM_grupal_entrega2.md'
OUTPUT_DOCX = BASE / 'entrega2' / 'TFM_Entrega2_BLOQUES_NUEVOS.docx'
FIG_DIR = BASE / 'entrega2' / 'figuras'

# Estilos UNIR (nombre tal como aparece en la plantilla)
S_NORMAL = 'Normal'
S_H1 = 'Heading 1'
S_H2 = 'Heading 2'
S_H3 = 'Heading 3'
S_H1U = 'Título 1 sin numerar'
S_INDX = 'Título Índices'
S_CAPT = 'Caption'
S_FOOT = 'Pie de foto-tabla'
S_BIB = 'Referencias bibliográficas'
S_ANEX = 'Anexo'
S_FIG = 'Figuras'


# ============================================================================
# Backup si el output existe
# ============================================================================
def backup_si_existe(path: Path) -> Path | None:
    if not path.exists():
        return None
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = path.with_name(f'{path.stem}.backup_{ts}.docx')
    shutil.copy2(path, backup)
    return backup


backup = backup_si_existe(OUTPUT_DOCX)
if backup is not None:
    print(f'Backup creado: {backup.name}')

# ============================================================================
# Cargar plantilla y limpiar body
# ============================================================================
if not INPUT_TEMPLATE.exists():
    raise FileNotFoundError(
        f'Plantilla UNIR no encontrada en {INPUT_TEMPLATE}. '
        'Confirma la ruta o copia tu plantilla a /Users/william-santos/Downloads/plantilla_grupal.docx.'
    )

doc = Document(str(INPUT_TEMPLATE))
body = doc.element.body
for child in list(body):
    tag = child.tag.split('}')[-1]
    if tag in ('p', 'tbl'):
        body.remove(child)

styles_disponibles = {s.name for s in doc.styles}


def safe_style(name: str, fallback: str = S_NORMAL) -> str:
    """Devuelve `name` si el estilo existe, sino `fallback`."""
    return name if name in styles_disponibles else fallback


# ============================================================================
# Helpers
# ============================================================================
TOKEN_RE = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)')


def add_paragraph(text='', style=S_NORMAL, bold=False, italic=False,
                  alignment=None, page_break_before=False):
    p = doc.add_paragraph(style=safe_style(style))
    if page_break_before:
        p.paragraph_format.page_break_before = True
    if alignment is not None:
        p.alignment = alignment
    if text:
        r = p.add_run(text)
        r.bold = bold
        r.italic = italic
    return p


def add_rich_paragraph(text, style=S_NORMAL, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY):
    """Soporta markdown inline simple: **bold**, *italic*, `code`."""
    p = doc.add_paragraph(style=safe_style(style))
    if alignment is not None:
        p.alignment = alignment
    for part in TOKEN_RE.split(text):
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


def add_caption(kind: str, num: int, title_text: str):
    """Caption APA correcto en dos parrafos:
       Linea 1: identificador en negrita (estilo Caption)
       Linea 2: titulo en cursiva (estilo Normal)
    """
    # Linea 1: identificador
    p1 = doc.add_paragraph(style=safe_style(S_CAPT))
    p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r1 = p1.add_run(f'{kind} {num}')
    r1.bold = True
    # Linea 2: titulo en cursiva
    p2 = doc.add_paragraph(style=safe_style(S_NORMAL))
    p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r2 = p2.add_run(title_text)
    r2.italic = True


def add_note(text: str):
    p = doc.add_paragraph(style=safe_style(S_FOOT))
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run('Nota. ')
    r.italic = True
    p.add_run(text)


def add_figure(path: Path, width_cm: int = 14):
    if not path.exists():
        add_paragraph(f'[FIGURA NO ENCONTRADA: {path.name}]', style=S_NORMAL, italic=True)
        return
    p = doc.add_paragraph(style=safe_style(S_FIG))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    r.add_picture(str(path), width=Cm(width_cm))


def add_table_from_rows(headers, rows, col_widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    try:
        t.style = 'Light Grid Accent 1'
    except KeyError:
        t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        cell = t.rows[0].cells[j]
        cell.text = ''
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            t.rows[i].cells[j].text = str(val)
    if col_widths:
        for row in t.rows:
            for j, w in enumerate(col_widths):
                if j < len(row.cells):
                    row.cells[j].width = Cm(w)
    return t


def add_page_break():
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def add_block_header(instruction: str):
    """Separador visible que indica donde insertar el bloque en el docx final."""
    sep = '=' * 70
    add_paragraph(sep, style=S_NORMAL)
    add_paragraph(f'INSERTAR EN: {instruction}', style=S_NORMAL, bold=True)
    add_paragraph(sep, style=S_NORMAL)
    add_paragraph('', style=S_NORMAL)  # espacio


# ============================================================================
# Parser markdown simple - extrae secciones por heading
# ============================================================================
def extract_section(md_text: str, heading_regex: str) -> str:
    """Devuelve el contenido de una seccion identificada por su heading.

    `heading_regex` debe matchear una linea tipo '## 3.2 Objetivos especificos'
    o '# 4. Desarrollo...'. La seccion se delimita por el siguiente heading
    del mismo nivel o superior, o por el final del documento.
    """
    lines = md_text.splitlines()
    start_idx = None
    start_level = None
    pattern = re.compile(heading_regex)
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            start_idx = i
            # Detectar nivel del heading capturado
            m_level = re.match(r'^(#+)', line)
            start_level = len(m_level.group(1)) if m_level else 1
            break
    if start_idx is None:
        return ''
    # Buscar el siguiente heading del mismo nivel o superior
    end_idx = len(lines)
    next_heading = re.compile(r'^(#+)\s')
    for i in range(start_idx + 1, len(lines)):
        m = next_heading.match(lines[i])
        if m and len(m.group(1)) <= start_level:
            end_idx = i
            break
    return '\n'.join(lines[start_idx:end_idx])


# ============================================================================
# Emisores: convierten un bloque de markdown a parrafos docx con estilos UNIR
# ============================================================================
HEADING_RE = re.compile(r'^(#+)\s+(.+?)\s*$')
TABLE_ROW_RE = re.compile(r'^\|.+\|\s*$')
TABLE_SEP_RE = re.compile(r'^\|[\s\-:|]+\|\s*$')
FIG_MD_RE = re.compile(r'^!\[.*?\]\((.+?)\)\s*$')
CAPTION_TABLA_RE = re.compile(r'^\*\*Tabla\s+(\d+)\*\*\s*$')
CAPTION_FIGURA_RE = re.compile(r'^\*\*Figura\s+(\d+)\*\*\s*$')
NOTE_RE = re.compile(r'^\*Nota\.\*\s*(.+)$')
ITALIC_TITLE_RE = re.compile(r'^\*(.+?)\*\s*$')
LIST_ITEM_RE = re.compile(r'^[-*]\s+(.+)$')


def emit_section(md_block: str, drop_heading: bool = False):
    """Procesa un bloque markdown emitiendo parrafos con estilos UNIR.

    Soporta:
      - Headings #, ##, ###
      - Parrafos planos
      - Tablas con caption "**Tabla N**" + "*titulo en cursiva*" en lineas adyacentes
      - Figuras con caption "**Figura N**" + titulo + ![alt](path)
      - Notas "*Nota.* texto"
      - Listas con bullet '-' o '*'
    """
    lines = md_block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Saltar lineas vacias
        if not line:
            i += 1
            continue

        # Heading
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2)
            # El heading numerado tipo "4.1 Configuracion..." mantiene su numero
            if drop_heading and i == 0:
                i += 1
                continue
            if level == 1:
                add_paragraph(title, style=S_H1, page_break_before=True)
            elif level == 2:
                add_paragraph(title, style=S_H2)
            elif level == 3:
                add_paragraph(title, style=S_H3)
            else:
                add_paragraph(title, style=S_NORMAL, bold=True)
            i += 1
            continue

        # Caption Tabla N + titulo en cursiva (dos lineas)
        m = CAPTION_TABLA_RE.match(line)
        if m:
            num = int(m.group(1))
            # Buscar titulo en cursiva en la linea siguiente no vacia
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            title = ''
            if j < len(lines):
                tm = ITALIC_TITLE_RE.match(lines[j].strip())
                if tm:
                    title = tm.group(1)
                    j += 1
            add_caption('Tabla', num, title)
            i = j
            continue

        # Caption Figura N
        m = CAPTION_FIGURA_RE.match(line)
        if m:
            num = int(m.group(1))
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            title = ''
            if j < len(lines):
                tm = ITALIC_TITLE_RE.match(lines[j].strip())
                if tm:
                    title = tm.group(1)
                    j += 1
            add_caption('Figura', num, title)
            i = j
            continue

        # Figura embebida ![alt](path)
        m = FIG_MD_RE.match(line)
        if m:
            ruta = m.group(1)
            if not ruta.startswith('/'):
                # Resolver relativa al directorio entrega2/
                ruta_path = BASE / 'entrega2' / ruta
            else:
                ruta_path = Path(ruta)
            add_figure(ruta_path)
            i += 1
            continue

        # Nota al pie de tabla/figura
        m = NOTE_RE.match(line)
        if m:
            add_note(m.group(1))
            i += 1
            continue

        # Tabla markdown
        if TABLE_ROW_RE.match(line):
            # Recolectar todas las lineas consecutivas que parecen tabla
            j = i
            tabla_lines = []
            while j < len(lines) and (TABLE_ROW_RE.match(lines[j]) or TABLE_SEP_RE.match(lines[j])):
                tabla_lines.append(lines[j])
                j += 1
            if len(tabla_lines) >= 2:
                # Saltar el separador (segunda linea)
                headers = [c.strip() for c in tabla_lines[0].strip('|').split('|')]
                rows = []
                for raw in tabla_lines[2:]:
                    cells = [c.strip() for c in raw.strip('|').split('|')]
                    rows.append(cells)
                add_table_from_rows(headers, rows)
            i = j
            continue

        # Lista
        m = LIST_ITEM_RE.match(line)
        if m:
            # Procesar consecutivos
            while i < len(lines) and LIST_ITEM_RE.match(lines[i].rstrip()):
                item = LIST_ITEM_RE.match(lines[i].rstrip()).group(1)
                add_rich_paragraph(item, style='List Paragraph')
                i += 1
            continue

        # Parrafo normal con markup inline
        add_rich_paragraph(line, style=S_NORMAL)
        i += 1


# ============================================================================
# Construccion del documento de bloques
# ============================================================================
md_text = MD_PATH.read_text(encoding='utf-8')


# =========================================================================
# Portada del docx de bloques: contexto del feedback de E1
# =========================================================================
add_paragraph('Bloques de actualizacion del TFM', style=S_H1U)
add_paragraph(
    'Este documento contiene UNICAMENTE el contenido nuevo y las correcciones '
    'derivadas del feedback formal de la primera version del trabajo. No '
    'reproduce capitulos que ya estan correctos en el docx existente. Cada '
    'bloque va precedido por un separador con la instruccion exacta de donde '
    'insertarlo. Hay diez bloques en total.',
    style=S_NORMAL,
)
add_paragraph('')
add_paragraph('Mapeo bloques <-> feedback de la primera entrega:', style=S_NORMAL, bold=True)
add_rich_paragraph(
    '- Bloques 1 y 2 (Resumen y Abstract): actualizan las cifras del corpus, '
    'el inventario de la base de conocimiento y el hallazgo experimental '
    'principal. Sustituyen las versiones previas.',
    style=S_NORMAL,
)
add_rich_paragraph(
    '- Bloques 3 y 4 (Cap 3.2 y Cap 3.3.2): reescriben los siete objetivos '
    'SMART y la descripcion de las fases en prosa fluida, atendiendo el indicio '
    'de IA generativa que el director marco sobre la estructura demasiado '
    'canonica de la version previa.',
    style=S_NORMAL,
)
add_rich_paragraph(
    '- Bloque 5 (Capitulo 4 completo): sustituye el Capitulo 4 en su totalidad. '
    'La estructura cambia respecto a la version previa: pasa de tres subsecciones '
    '(Fase 1, Fase 2, Fase 3 inicial) a siete subsecciones que cubren las Fases '
    '1 a 6 con resultados experimentales reales. Las cifras del corpus, los '
    'indices RAG, el adaptador LoRA y la tabla comparativa de configuraciones '
    'son contenido nuevo.',
    style=S_NORMAL,
)
add_rich_paragraph(
    '- Bloque 6 (Capitulo 5): sustituye la estructura vacia heredada de la '
    'plantilla por el contenido completo: conclusiones, discusion y lineas '
    'futuras.',
    style=S_NORMAL,
)
add_rich_paragraph(
    '- Bloque 7 (Anexo A): sustituye el listado de tres notebooks por la '
    'estructura completa del repositorio actual (doce notebooks numerados, '
    'paquete src/ con tres subpaquetes, datos generados, licenciamiento '
    'ampliado).',
    style=S_NORMAL,
)
add_rich_paragraph(
    '- Bloque 8 (Referencia nueva): anade una entrada bibliografica que cita '
    'Finkelstein et al. (2026) sobre TranslateGemma. Va en orden alfabetico, '
    'inmediatamente despues de Ebrahimi et al. (2024).',
    style=S_NORMAL,
)
add_rich_paragraph(
    '- Bloque 9 (Ejemplo de pie de tabla y figura en formato APA correcto): '
    'modelo visual para aplicar al rotulado de TODAS las tablas y figuras del '
    'documento, incluidas las heredadas (Tabla 1 a 5, Figura 1 a 8). Atiende '
    'el fallo de formato senalado por el director: identificador en negrita '
    'en linea propia, titulo en cursiva debajo, eliminacion del literal '
    '"Figure"/"Table" en ingles.',
    style=S_NORMAL,
)
add_paragraph('')
add_rich_paragraph(
    'Los capitulos 1 y 2 del docx existente no requieren cambios y no se '
    'reproducen aqui. La portada y el header del documento conservan los '
    'datos correctos de la version previa salvo la fecha, que debe '
    'actualizarse manualmente.',
    style=S_NORMAL,
)
add_page_break()

# ---- Bloque 1: Resumen ----
add_block_header(
    'Bloque 1 de 9. SUSTITUIR el contenido actual de la seccion "Resumen". '
    'Las cifras del corpus (5.641 pares), de los indices (4.900 lexicas, 605 '
    'gramaticales, 9.024 ejemplos) y el resultado experimental (17,89 BLEU) '
    'son nuevos respecto a la version previa.'
)
add_paragraph('Resumen', style=S_H1U)
emit_section(extract_section(md_text, r'^## Resumen\s*$'), drop_heading=True)
add_page_break()

# ---- Bloque 2: Abstract ----
add_block_header(
    'Bloque 2 de 9. SUSTITUIR el contenido actual de la seccion "Abstract". '
    'Traduccion exacta del Resumen actualizado.'
)
add_paragraph('Abstract', style=S_H1U)
emit_section(extract_section(md_text, r'^## Abstract\s*$'), drop_heading=True)
add_page_break()

# ---- Bloque 3: Capitulo 3.2 Objetivos especificos (anti-LLM) ----
add_block_header(
    'Bloque 3 de 9. SUSTITUIR el contenido actual de la seccion "3.2 Objetivos '
    'especificos". La nueva version presenta los siete objetivos como prosa '
    'fluida en lugar de una lista canonica de bullets con criterio SMART '
    'estampado al final de cada uno. Aborda el indicio de IA generativa '
    'senalado por el director.'
)
emit_section(extract_section(md_text, r'^## 3\.2 Objetivos específicos\s*$'))
add_page_break()

# ---- Bloque 4: Capitulo 3.3.2 Fases (anti-LLM) ----
add_block_header(
    'Bloque 4 de 9. SUSTITUIR el contenido actual de la seccion "3.3.2 Fases '
    'del proyecto". La nueva version rompe el patron repetitivo "La Fase N '
    '(X) ejecuta Y" variando los inicios de parrafo y las longitudes.'
)
emit_section(extract_section(md_text, r'^### 3\.3\.2 Fases del proyecto\s*$'))
add_page_break()

# ---- Bloque 5: Capitulo 4 completo (Desarrollo especifico) ----
add_block_header(
    'Bloque 5 de 9. SUSTITUIR todo el Capitulo 4 en el docx final. La '
    'estructura cambia respecto a la version previa: las tres subsecciones '
    'originales (Fase 1, Fase 2, Fase 3 inicial, mas Repositorio, mas Proximos '
    'pasos hacia la siguiente entrega) se reemplazan por siete subsecciones '
    'que cubren las Fases 1 a 6 con resultados experimentales. Las Tablas 6, '
    '7 y 8 y las Figuras 9, 10, 11 y 12 son nuevas y siguen el formato APA '
    'correcto (Bloque 9 muestra el patron a replicar).'
)
emit_section(extract_section(md_text, r'^# 4\. Desarrollo específico'))
add_page_break()

# ---- Bloque 6: Capitulo 5 completo (Conclusiones) ----
add_block_header(
    'Bloque 6 de 9. SUSTITUIR el Capitulo 5 vacio por el contenido completo: '
    'conclusiones, discusion analitica con cuatro observaciones y tres '
    'limitaciones, mas cinco lineas de trabajo futuras.'
)
emit_section(extract_section(md_text, r'^# 5\. Conclusiones'))
add_page_break()

# ---- Bloque 7: Anexo A actualizado ----
add_block_header(
    'Bloque 7 de 9. SUSTITUIR el Anexo A del docx final. La nueva version '
    'lista los doce notebooks ejecutables (00 a 11), los modulos src/, los '
    'archivos del corpus, los splits y el licenciamiento ampliado (incluye '
    'Reina-Valera 1909 de dominio publico).'
)
emit_section(extract_section(md_text, r'^# Anexo A\.'))
add_page_break()

# ---- Bloque 8: Nueva referencia bibliografica ----
add_block_header(
    'Bloque 8 de 9. ANADIR esta entrada nueva en la seccion "Referencias '
    'bibliograficas", en orden alfabetico (va inmediatamente despues de '
    'Ebrahimi et al., 2024).'
)
add_rich_paragraph(
    'Finkelstein, M., Caswell, I., Domhan, T., Peter, J.-T., Juraska, J., Riley, P., Deutsch, D., '
    'Kovacs, G., Dilanni, C., Cherry, C., Briakou, E., Nielsen, E., Luo, J., Black, K., Mullins, R., '
    'Agrawal, S., Xu, W., Kats, E., Jaskiewicz, S., Freitag, M., y Vilar, D. (2026). '
    '*TranslateGemma: Technical Report* [arXiv preprint]. https://arxiv.org/abs/2601.09012',
    style=S_BIB,
)
add_page_break()

# ---- Bloque 9: Ejemplo de formato APA correcto para captions ----
add_block_header(
    'Bloque 9 de 9. REFERENCIA VISUAL. Modelo del formato APA correcto para '
    'tablas y figuras, a aplicar manualmente al rotulado de TODAS las que '
    'aparecen en el documento, incluidas las heredadas (Tabla 1 a 5, Figura '
    '1 a 8). El formato exige tres reglas conjuntas: etiqueta en castellano '
    '(Tabla / Figura, NO Table / Figure), identificador en negrita en linea '
    'propia, titulo en cursiva sin punto en la linea siguiente. Los rotulos '
    'de las Tablas 6, 7 y 8 y de las Figuras 9, 10, 11 y 12 incluidos en el '
    'Bloque 5 ya cumplen este patron y pueden copiarse como plantilla.'
)
add_paragraph('Ejemplo correcto para una figura:', style=S_NORMAL, bold=True)
add_paragraph('')
add_caption('Figura', 1, 'Ubicación del pueblo Inga en el departamento del Putumayo')
add_paragraph('(aqui iria la figura)', style=S_NORMAL, italic=True, alignment=WD_ALIGN_PARAGRAPH.CENTER)
add_note('Elaboracion propia con base en datos de OpenStreetMap contributors (ODbL).')
add_paragraph('')
add_paragraph('Ejemplo correcto para una tabla:', style=S_NORMAL, bold=True)
add_paragraph('')
add_caption('Tabla', 3, 'Inventario de recursos lingüísticos primarios utilizados en la construcción del corpus')
add_paragraph('(aqui iria la tabla)', style=S_NORMAL, italic=True, alignment=WD_ALIGN_PARAGRAPH.CENTER)
add_note('Elaboracion propia. La cifra total de paginas OCR asciende a 1.094.')


# ============================================================================
# Guardar
# ============================================================================
OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
doc.save(str(OUTPUT_DOCX))
print(f'Generado: {OUTPUT_DOCX}')
print('Bloques nuevos listos para copiar y pegar a TFM_Entrega2_EslavaSantos.docx.')
