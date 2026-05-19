"""Generador del notebook 04: extraccion del NT Reina-Valera 1909 (USFM)."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "04_extraccion_NT_rv1909.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(t): nb.cells.append(nbf.v4.new_markdown_cell(t))
def code(t): nb.cells.append(nbf.v4.new_code_cell(t))


md(
    """# Notebook 04 - Extraccion estructurada del NT Reina-Valera 1909

**Entrega 2.** Procesa los 27 archivos USFM en
`datos/ocr/reina-valera-1909/` y produce
`datos/nt_rv1909_estructurado.jsonl` con la tupla canonica
`(libro, capitulo, versiculo, texto_es)`.

## Marcado USFM relevante

- `\\id MAT` ... codigo de tres letras del libro (en ingles, p.ej. MAT, MRK, ACT)
- `\\c N` ... numero de capitulo
- `\\v N` ... numero de versiculo seguido del texto
- `\\w palabra|strong="GNNNN"\\w*` ... palabra con anotacion Strong (se filtra)
- `\\add ... \\add*` ... palabras anadidas por el traductor (se conservan sin markers)
- `\\f ... \\f*` ... footnote (se elimina completa)
- `\\x ... \\x*` ... cross-reference (se elimina completa)
- `\\p`, `\\q`, `\\m`, `\\b` ... parrafo/poesia (se ignoran como saltos)

## Mapeo USFM ID -> nombre canonico espanol
"""
)

code(
    """import json
import re
from collections import defaultdict
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
SRC_DIR = ROOT / "datos" / "ocr" / "reina-valera-1909"
OUT = ROOT / "datos" / "nt_rv1909_estructurado.jsonl"

# USFM book ID -> canonical Spanish name (alineado con Notebook 03)
USFM_TO_CANONICO = {
    "MAT": "Mateo", "MRK": "Marcos", "LUK": "Lucas", "JHN": "Juan", "ACT": "Hechos",
    "ROM": "Romanos", "1CO": "1 Corintios", "2CO": "2 Corintios",
    "GAL": "Galatas", "EPH": "Efesios", "PHP": "Filipenses", "COL": "Colosenses",
    "1TH": "1 Tesalonicenses", "2TH": "2 Tesalonicenses",
    "1TI": "1 Timoteo", "2TI": "2 Timoteo", "TIT": "Tito", "PHM": "Filemon",
    "HEB": "Hebreos", "JAS": "Santiago",
    "1PE": "1 Pedro", "2PE": "2 Pedro",
    "1JN": "1 Juan", "2JN": "2 Juan", "3JN": "3 Juan", "JUD": "Judas",
    "REV": "Apocalipsis",
}
print(f"Libros NT canonicos: {len(USFM_TO_CANONICO)}")
"""
)

md(
    """## Parser USFM

Cada archivo `NN-XXXspaRV1909.usfm` se procesa secuencialmente. Se eliminan
los marcadores Strong y de palabras anotadas para obtener texto plano,
manteniendo la estructura libro/capitulo/versiculo intacta.
"""
)

code(
    r'''def limpiar_marcado_usfm(texto: str) -> str:
    """Quita anotaciones USFM dejando el texto plano del versiculo."""
    # Eliminar footnotes y cross-references completas
    texto = re.sub(r"\\f\s.*?\\f\*", "", texto, flags=re.DOTALL)
    texto = re.sub(r"\\x\s.*?\\x\*", "", texto, flags=re.DOTALL)
    # Convertir \w palabra|strong="GNNNN"\w* -> palabra
    texto = re.sub(r"\\w\s+([^|\\]+)(?:\|[^\\]*)?\\w\*", r"\1", texto)
    # Mantener \add ... \add* (palabras añadidas) sin marcadores
    texto = re.sub(r"\\add\s+(.+?)\\add\*", r"\1", texto)
    # Eliminar otros marcadores residuales: \p, \q, \m, \b, etc.
    texto = re.sub(r"\\[a-z0-9]+\*?", "", texto)
    # Normalizar espacios
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def parsear_usfm(path: Path, libro_canonico: str):
    """Devuelve lista de dicts (libro, capitulo, versiculo, texto_es) para un archivo USFM."""
    registros = []
    capitulo = None
    contenido = path.read_text(encoding="utf-8")

    # Estrategia: dividir por `\c N` para procesar capitulo por capitulo, luego
    # dividir cada capitulo por `\v N` para extraer versiculos.
    partes_capitulo = re.split(r"(\\c\s+\d+)", contenido)
    # partes_capitulo es [pre, "\c 1", contenido_cap1, "\c 2", contenido_cap2, ...]
    for i in range(1, len(partes_capitulo), 2):
        marker = partes_capitulo[i]
        contenido_cap = partes_capitulo[i + 1] if i + 1 < len(partes_capitulo) else ""
        m = re.match(r"\\c\s+(\d+)", marker)
        if not m:
            continue
        cap = int(m.group(1))

        partes_verso = re.split(r"(\\v\s+\d+)", contenido_cap)
        for j in range(1, len(partes_verso), 2):
            marker_v = partes_verso[j]
            contenido_v = partes_verso[j + 1] if j + 1 < len(partes_verso) else ""
            mv = re.match(r"\\v\s+(\d+)", marker_v)
            if not mv:
                continue
            verso = int(mv.group(1))
            texto = limpiar_marcado_usfm(contenido_v)
            if texto:
                registros.append({
                    "libro": libro_canonico,
                    "capitulo": cap,
                    "versiculo": verso,
                    "texto_es": texto,
                })
    return registros


registros = []
for usfm_path in sorted(SRC_DIR.glob("*.usfm")):
    # Extract USFM ID from filename pattern "NN-XXXspaRV1909.usfm"
    match = re.match(r"\d+-(\w+)spaRV1909\.usfm", usfm_path.name)
    if not match:
        print(f"Saltando archivo con nombre inesperado: {usfm_path.name}")
        continue
    usfm_id = match.group(1)
    canonico = USFM_TO_CANONICO.get(usfm_id)
    if canonico is None:
        print(f"Saltando libro no mapeado: {usfm_id}")
        continue
    libro_registros = parsear_usfm(usfm_path, canonico)
    registros.extend(libro_registros)

df = pd.DataFrame(registros)
print(f"Total versiculos extraidos: {len(df):,}")
print(f"Libros: {df.libro.nunique()}")
'''
)

md(
    """## Validacion: cobertura por libro vs canon

El canon NT tiene 7.957 versiculos. La RV1909 estructurada deberia llegar a
~7.957 con tasa cercana a 100% (es texto digital, no OCR).
"""
)

code(
    """CONTEO_CANONICO = {
    "Mateo": 1071, "Marcos": 678, "Lucas": 1151, "Juan": 879, "Hechos": 1007,
    "Romanos": 433, "1 Corintios": 437, "2 Corintios": 257, "Galatas": 149,
    "Efesios": 155, "Filipenses": 104, "Colosenses": 95,
    "1 Tesalonicenses": 89, "2 Tesalonicenses": 47,
    "1 Timoteo": 113, "2 Timoteo": 83, "Tito": 46, "Filemon": 25,
    "Hebreos": 303, "Santiago": 108,
    "1 Pedro": 105, "2 Pedro": 61,
    "1 Juan": 105, "2 Juan": 13, "3 Juan": 15, "Judas": 25,
    "Apocalipsis": 404,
}
conteo_extraido = df.groupby("libro").size().to_dict()
print(f"{'Libro':<22}{'Canonico':>10}{'Extraido':>10}{'Cobertura':>12}")
print("-" * 54)
total_ext = 0
for libro, canon in CONTEO_CANONICO.items():
    ext = conteo_extraido.get(libro, 0)
    cov = (ext / canon * 100) if canon else 0
    total_ext += ext
    flag = " " if cov >= 95 else "!"
    print(f"{libro:<22}{canon:>10}{ext:>10}{cov:>11.1f}% {flag}")
print("-" * 54)
print(f"{'TOTAL':<22}{sum(CONTEO_CANONICO.values()):>10}{total_ext:>10}{total_ext/sum(CONTEO_CANONICO.values())*100:>11.1f}%")
"""
)

md(
    """## Inspeccion: 5 versiculos aleatorios

Verifica que el texto extraido este limpio (sin tags USFM ni Strong).
"""
)

code(
    """muestra = df.sample(5, random_state=42)
for _, row in muestra.iterrows():
    print(f"{row.libro} {row.capitulo}:{row.versiculo}")
    print(f"  {row.texto_es[:200]}")
    print()
"""
)

md("## Persistir a JSONL")

code(
    """OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as f:
    for _, row in df.iterrows():
        f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\\n")
print(f"Escrito: {OUT.relative_to(ROOT)}  ({len(df):,} versiculos)")
"""
)

nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
