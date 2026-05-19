"""Generador del notebook 05: alineacion canonica NT Inga <-> Reina-Valera 1909."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "05_alineacion_NT.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(t): nb.cells.append(nbf.v4.new_markdown_cell(t))
def code(t): nb.cells.append(nbf.v4.new_code_cell(t))


md(
    """# Notebook 05 - Alineacion canonica NT Inga vs Reina-Valera 1909

**Entrega 2.** Junta los dos jsonl estructurados por la tupla
`(libro, capitulo, versiculo)` y produce `datos/nt_paralelo.jsonl`
con los pares paralelos Inga-espanol listos para entrenamiento.

## Estrategia

INNER JOIN exacto por `(libro, capitulo, versiculo)`. La RV1909 actua como
fuente de verdad sobre la cantidad y orden canonico; los versiculos del NT
Inga que no matcheen contra RV1909 se descartan (probablemente sean falsos
positivos del parser OCR).

Filtros de calidad post-join:
- Eliminar pares con texto_inga o texto_es de menos de 5 palabras
- Eliminar pares donde la relacion de longitudes sea > 5x (probable mismatch)
- Eliminar pares duplicados (mismo verso combinado en NT Inga)
"""
)

code(
    """import json
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
INGA = ROOT / "datos" / "nt_inga_estructurado.jsonl"
ES = ROOT / "datos" / "nt_rv1909_estructurado.jsonl"
OUT = ROOT / "datos" / "nt_paralelo.jsonl"

inga = pd.read_json(INGA, lines=True)
es = pd.read_json(ES, lines=True)
print(f"NT Inga: {len(inga):,} registros (unicos: {len(inga.drop_duplicates(subset=['libro','capitulo','versiculo'])):,})")
print(f"NT RV1909: {len(es):,} versiculos")
"""
)

md(
    """## Join exacto

Se hace INNER JOIN. Los versiculos Inga "verso_combinado" se duplican en el
Notebook 03 con el mismo texto para verso N y N+1, asi que naturalmente
aparecen con dos matches contra RV1909 que tienen versiculos N y N+1
separados. El resultado es que ambos versos quedan con el mismo texto_inga
pero diferente texto_es, lo cual es valido para entrenamiento.
"""
)

code(
    """# Deduplicar por seguridad: si el parser Inga produjo el mismo (libro, cap, vers)
# multiples veces (no deberia, pero por si acaso), nos quedamos con el primero.
inga_dedup = inga.drop_duplicates(subset=["libro", "capitulo", "versiculo"], keep="first")
print(f"NT Inga deduplicado: {len(inga_dedup):,}")

paralelo = inga_dedup.merge(es, on=["libro", "capitulo", "versiculo"], how="inner")
print(f"Pares paralelos (join exacto): {len(paralelo):,}")
print(f"Tasa de alineacion vs Inga: {len(paralelo)/len(inga_dedup)*100:.1f}%")
print(f"Tasa de alineacion vs RV1909: {len(paralelo)/len(es)*100:.1f}%")
"""
)

md(
    """## Filtros de calidad

- **Longitud minima**: ambos textos deben tener >= 5 palabras
- **Relacion de longitudes**: max/min <= 5.0 (descarta mismatches obvios)
- **Texto vacio o ruidoso**: descartar texto que sea principalmente digitos
"""
)

code(
    """def es_texto_valido(t: str) -> bool:
    if not isinstance(t, str):
        return False
    palabras = t.split()
    if len(palabras) < 5:
        return False
    # Descartar si > 50% son digitos
    if sum(1 for p in palabras if p.replace(",","").replace(".","").isdigit()) > len(palabras) * 0.5:
        return False
    return True

paralelo["len_inga"] = paralelo.texto_inga.str.split().str.len()
paralelo["len_es"] = paralelo.texto_es.str.split().str.len()
paralelo["ratio"] = paralelo[["len_inga", "len_es"]].max(axis=1) / paralelo[["len_inga", "len_es"]].min(axis=1)

mask = (
    paralelo.texto_inga.apply(es_texto_valido)
    & paralelo.texto_es.apply(es_texto_valido)
    & (paralelo.ratio <= 5.0)
)
filtrado = paralelo[mask].copy()
print(f"Tras filtros de calidad: {len(filtrado):,} pares")
print(f"  Descartados por longitud minima o digitos: {(~paralelo.texto_inga.apply(es_texto_valido) | ~paralelo.texto_es.apply(es_texto_valido)).sum()}")
print(f"  Descartados por ratio > 5x: {(paralelo.ratio > 5.0).sum()}")
"""
)

md("## Estadisticas del corpus paralelo final")

code(
    """print(f"Longitud media Inga: {filtrado.len_inga.mean():.1f} palabras")
print(f"Longitud media RV1909: {filtrado.len_es.mean():.1f} palabras")
print(f"Ratio medio: {filtrado.ratio.mean():.2f}")
print()
print("Distribucion por libro:")
print(filtrado.groupby("libro").size().sort_values(ascending=False).head(10).to_string())
"""
)

md("## Inspeccion: 5 pares aleatorios")

code(
    """muestra = filtrado.sample(5, random_state=42)
for _, row in muestra.iterrows():
    print(f"=== {row.libro} {row.capitulo}:{row.versiculo} ===")
    print(f"  INGA:  {row.texto_inga[:200]}")
    print(f"  ES:    {row.texto_es[:200]}")
    print()
"""
)

md("## Persistir a JSONL")

code(
    """# Campos finales: idx, libro, capitulo, versiculo, texto_inga, texto_es,
# dialecto (AP - el NT Wycliffe esta principalmente en Alto Putumayo), fuente
salida = filtrado[["libro", "capitulo", "versiculo", "texto_inga", "texto_es"]].copy()
salida["dialecto"] = "AP"
salida["fuente"] = "NT-Wycliffe-RV1909"
salida = salida.reset_index(drop=True)
salida.insert(0, "idx", salida.index)

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as f:
    for _, row in salida.iterrows():
        f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\\n")
print(f"Escrito: {OUT.relative_to(ROOT)}  ({len(salida):,} pares)")
"""
)

nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
