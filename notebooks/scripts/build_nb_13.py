"""Generador del notebook 13: extraccion RV1909 OT + alineacion canonica AT."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "13_alineacion_AT.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(t): nb.cells.append(nbf.v4.new_markdown_cell(t))
def code(t): nb.cells.append(nbf.v4.new_code_cell(t))


md(
    """# Notebook 13 - Extraccion RV1909 OT + Alineacion canonica con AT Inga

**Entrega 2 - Expansion del corpus.**

Procesa los 39 archivos USFM del AT Reina-Valera 1909 (descargados en
`datos/ocr/reina-valera-1909/OT/`) y produce el corpus paralelo paralelo
AT a partir del join con `datos/at_inga_estructurado.jsonl`.

Reutiliza el parser USFM del Notebook 04.
"""
)

code(
    """import json, re
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OT_DIR = ROOT / "datos" / "ocr" / "reina-valera-1909" / "OT"
INGA = ROOT / "datos" / "at_inga_estructurado.jsonl"
OUT = ROOT / "datos" / "at_paralelo.jsonl"

USFM_TO_CANONICO = {
    "GEN": "Genesis", "EXO": "Exodo", "LEV": "Levitico", "NUM": "Numeros", "DEU": "Deuteronomio",
    "JOS": "Josue", "JDG": "Jueces", "RUT": "Rut",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Reyes", "2KI": "2 Reyes",
    "1CH": "1 Cronicas", "2CH": "2 Cronicas", "EZR": "Esdras", "NEH": "Nehemias", "EST": "Ester",
    "JOB": "Job", "PSA": "Salmos", "PRO": "Proverbios", "ECC": "Eclesiastes", "SNG": "Cantares",
    "ISA": "Isaias", "JER": "Jeremias", "LAM": "Lamentaciones", "EZK": "Ezequiel", "DAN": "Daniel",
    "HOS": "Oseas", "JOL": "Joel", "AMO": "Amos", "OBA": "Abdias", "JON": "Jonas",
    "MIC": "Miqueas", "NAM": "Nahum", "HAB": "Habacuc", "ZEP": "Sofonias", "HAG": "Hageo",
    "ZEC": "Zacarias", "MAL": "Malaquias",
}
print(f"Libros AT canonicos esperados: {len(USFM_TO_CANONICO)}")
"""
)

md("## Parser USFM (reusado de NB04)")

code(
    r'''def limpiar_marcado_usfm(texto: str) -> str:
    texto = re.sub(r"\\f\s.*?\\f\*", "", texto, flags=re.DOTALL)
    texto = re.sub(r"\\x\s.*?\\x\*", "", texto, flags=re.DOTALL)
    texto = re.sub(r"\\w\s+([^|\\]+)(?:\|[^\\]*)?\\w\*", r"\1", texto)
    texto = re.sub(r"\\add\s+(.+?)\\add\*", r"\1", texto)
    texto = re.sub(r"\\[a-z0-9]+\*?", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def parsear_usfm(path: Path, libro_canonico: str):
    registros = []
    contenido = path.read_text(encoding="utf-8")
    partes_capitulo = re.split(r"(\\c\s+\d+)", contenido)
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
                registros.append({"libro": libro_canonico, "capitulo": cap, "versiculo": verso, "texto_es": texto})
    return registros


registros_es = []
for usfm_path in sorted(OT_DIR.glob("*.usfm")):
    match = re.match(r"\d+-(\w+)spaRV1909\.usfm", usfm_path.name)
    if not match:
        continue
    usfm_id = match.group(1)
    canonico = USFM_TO_CANONICO.get(usfm_id)
    if canonico is None:
        print(f"Saltando libro no mapeado: {usfm_id}")
        continue
    registros_es.extend(parsear_usfm(usfm_path, canonico))

df_es = pd.DataFrame(registros_es)
print(f"Versiculos AT RV1909 extraidos: {len(df_es):,}")
print(f"Libros AT cubiertos: {df_es.libro.nunique()}")
'''
)

md("## JOIN con AT Inga + filtros de calidad")

code(
    """df_inga = pd.read_json(INGA, lines=True)
print(f"AT Inga registros: {len(df_inga):,}")

paralelo = df_inga.drop_duplicates(subset=["libro", "capitulo", "versiculo"], keep="first").merge(
    df_es, on=["libro", "capitulo", "versiculo"], how="inner"
)
print(f"Pares paralelos AT tras JOIN: {len(paralelo):,}")
print(f"Tasa vs AT Inga: {len(paralelo)/len(df_inga)*100:.1f}%")
"""
)

code(
    """def es_valido(t):
    if not isinstance(t, str): return False
    palabras = t.split()
    if len(palabras) < 5: return False
    return True

paralelo["len_inga"] = paralelo.texto_inga.str.split().str.len()
paralelo["len_es"] = paralelo.texto_es.str.split().str.len()
paralelo["ratio"] = paralelo[["len_inga","len_es"]].max(axis=1) / paralelo[["len_inga","len_es"]].min(axis=1)

mask = (
    paralelo.texto_inga.apply(es_valido)
    & paralelo.texto_es.apply(es_valido)
    & (paralelo.ratio <= 5.0)
)
filtrado = paralelo[mask].copy()
print(f"Tras filtros de calidad: {len(filtrado):,} pares")
print(f"Distribucion AT por libro:")
print(filtrado.groupby("libro").size().sort_values(ascending=False).to_string())
"""
)

md("## Persistir")

code(
    """salida = filtrado[["libro","capitulo","versiculo","texto_inga","texto_es"]].copy()
salida["dialecto"] = "AP"
salida["fuente"] = "AT-Wycliffe-RV1909"
salida = salida.reset_index(drop=True)
salida.insert(0, "idx", salida.index)

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as f:
    for _, row in salida.iterrows():
        f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\\n")
print(f"Escrito: {OUT.relative_to(ROOT)}  ({len(salida):,} pares)")
"""
)

md("## Muestra cualitativa")

code(
    """import random
random.seed(42)
for _, row in salida.sample(min(5, len(salida)), random_state=42).iterrows():
    print(f"{row.libro} {row.capitulo}:{row.versiculo}")
    print(f"  INGA: {row.texto_inga[:200]}")
    print(f"  ES:   {row.texto_es[:200]}")
    print()
"""
)

nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
