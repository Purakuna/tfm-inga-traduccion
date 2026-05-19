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


# ---- Bloque 1: Resumen ----
add_block_header('Sustituir la seccion "Resumen" en tu .docx final')
add_paragraph('Resumen', style=S_H1U)
emit_section(extract_section(md_text, r'^## Resumen\s*$'), drop_heading=True)
add_page_break()

# ---- Bloque 2: Abstract ----
add_block_header('Sustituir la seccion "Abstract" en tu .docx final')
add_paragraph('Abstract', style=S_H1U)
emit_section(extract_section(md_text, r'^## Abstract\s*$'), drop_heading=True)
add_page_break()

# ---- Bloque 3: Capitulo 3 - Objetivos especificos y Fases (anti-LLM rewrite) ----
add_block_header('Sustituir Capitulo 3.1 (Objetivo general), 3.2 (Objetivos especificos) y 3.3.2 (Fases) - reescritos para reducir senales de IA generativa')
emit_section(extract_section(md_text, r'^## 3\.1 Objetivo general\s*$'))
add_paragraph('')
emit_section(extract_section(md_text, r'^## 3\.2 Objetivos específicos\s*$'))
add_paragraph('')
emit_section(extract_section(md_text, r'^### 3\.3\.2 Fases del proyecto\s*$'))
add_page_break()

# ---- Bloque 4: Capitulo 4 completo (Desarrollo especifico) ----
add_block_header('Sustituir todo el Capitulo 4 en tu .docx final (4.1 a 4.7)')
emit_section(extract_section(md_text, r'^# 4\. Desarrollo específico'))
add_page_break()

# ---- Bloque 5: Capitulo 5 completo (Conclusiones) ----
add_block_header('Sustituir todo el Capitulo 5 en tu .docx final (5.1 a 5.3)')
emit_section(extract_section(md_text, r'^# 5\. Conclusiones'))
add_page_break()

# ---- Bloque 6: Anexo A actualizado ----
add_block_header('Sustituir Anexo A en tu .docx final (estructura del repositorio expandida)')
emit_section(extract_section(md_text, r'^# Anexo A\.'))
add_page_break()

# ---- Bloque 7: Nueva referencia bibliografica (Finkelstein 2026 TranslateGemma) ----
add_block_header('Anadir esta entrada nueva en la seccion "Referencias bibliograficas" (orden alfabetico - va despues de Ebrahimi et al.)')
add_rich_paragraph(
    'Finkelstein, M., Caswell, I., Domhan, T., Peter, J.-T., Juraska, J., Riley, P., Deutsch, D., '
    'Kovacs, G., Dilanni, C., Cherry, C., Briakou, E., Nielsen, E., Luo, J., Black, K., Mullins, R., '
    'Agrawal, S., Xu, W., Kats, E., Jaskiewicz, S., Freitag, M., y Vilar, D. (2026). '
    '*TranslateGemma: Technical Report* [arXiv preprint]. https://arxiv.org/abs/2601.09012',
    style=S_BIB,
)


# ============================================================================
# Guardar
# ============================================================================
OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
doc.save(str(OUTPUT_DOCX))
print(f'Generado: {OUTPUT_DOCX}')
print('Bloques nuevos listos para copiar y pegar a TFM_Entrega2_EslavaSantos.docx.')
