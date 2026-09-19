"""Mide los sistemas sobre frases cotidianas (no biblicas) escritas por un hablante.

Lee datos/prueba_cotidiana/frases.csv (solo las filas con texto_inga Y texto_es),
traduce en ambas direcciones con tres configuraciones y deja:
- datos/prueba_cotidiana/resultados.csv: lado a lado, con columnas vacias para que
  el hablante puntue cada salida de 1 a 5 (con 30 frases el juicio humano pesa mas
  que BLEU).
- datos/prueba_cotidiana/metricas.json: BLEU, chrF y BERTScore por configuracion.

Configs: D (Gemini + RAG por chunks), F (wiki, modo rapido), G (wiki, modo agente).
Nada de esto se guarda en la wiki (save=False): estas frases son un conjunto de
prueba y NO deben entrar como feedback ni como ejemplos, o la medicion deja de valer.

En es2inga la referencia se compara tambien tras normalizar la ortografia de ambos
lados con navigate.normalize, para no castigar 'yuyay' frente a 'iuiai'.

Uso: PYTHONPATH=. uv run python notebooks/scripts/eval_cotidiana.py [--configs DFG]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.agent import core
from src.eval.metrics import all_metrics, chrf
from src.models import gemini_rag
from src.wiki import navigate
from src.wiki.store import WikiStore

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "datos" / "prueba_cotidiana"
WORKERS = 4
NOMBRES = {"D": "rag", "F": "wiki_rapido", "G": "wiki_agente"}


def traducir(cfg: str, texto: str, direccion: str, store: WikiStore) -> str:
    if cfg == "D":
        return gemini_rag.translate(texto, direccion)
    modo = "fast" if cfg == "F" else "agent"
    for e in core.translate(texto, direccion, modo, store=store, save=False):
        if e["event"] == "result":
            return e["data"]["translation"]
        if e["event"] == "error":
            raise RuntimeError(e["data"]["message"])
    raise RuntimeError("el agente termino sin resultado")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="DFG")
    args = ap.parse_args()

    frases = pd.read_csv(DIR / "frases.csv", dtype=str, encoding="utf-8-sig").fillna("")
    frases = frases[(frases.texto_inga.str.strip() != "") & (frases.texto_es.str.strip() != "")].reset_index(drop=True)
    if frases.empty:
        raise SystemExit("No hay filas completas en frases.csv (hacen falta texto_inga y texto_es).")
    print(f"{len(frases)} frases completas")

    store = WikiStore()
    out = frases[["id", "categoria", "texto_inga", "texto_es"]].copy()
    metricas: dict = {"_n": len(frases), "_model": gemini_rag.DEFAULT_MODEL}

    for cfg in args.configs:
        for direccion, src, ref in (("inga2es", "texto_inga", "texto_es"), ("es2inga", "texto_es", "texto_inga")):
            col = f"{NOMBRES[cfg]}_{direccion}"

            def run(texto: str) -> str:
                try:
                    return traducir(cfg, texto, direccion, store)
                except Exception as e:
                    print(f"[{col}] {type(e).__name__}: {str(e)[:160]}")
                    return ""

            with ThreadPoolExecutor(WORKERS) as pool:
                out[col] = list(tqdm(pool.map(run, frases[src].tolist()), total=len(frases), desc=col))
            out[f"nota_{col}"] = ""  # 1 a 5, la llena el hablante

            refs, hyps = frases[ref].tolist(), out[col].tolist()
            # BERTScore falla con hipotesis vacias: una salida vacia puntua como "-" (y se cuenta aparte).
            hyps = [h or "-" for h in hyps]
            m = all_metrics(refs, hyps)
            if direccion == "es2inga":
                m["chrf_ortografia_normalizada"] = chrf(
                    [navigate.normalize(r) for r in refs], [navigate.normalize(h) for h in hyps]
                )
            m["vacias"] = sum(1 for h in out[col].tolist() if not h)
            metricas[f"config_{cfg}_{col}"] = m
            print(col, m)
            out.to_csv(DIR / "resultados.csv", index=False, encoding="utf-8-sig")
            (DIR / "metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
