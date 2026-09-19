"""Mide Gemini sobre el mismo val sample (n=100, seed 42) del notebook 11.

Configs: C (zero-shot) y D (RAG), ambas direcciones. Guarda predicciones en
datos/predicciones_val_gemini.jsonl (reanudable) y metricas en
datos/metricas_gemini.json.

Uso: PYTHONPATH=. uv run python notebooks/scripts/eval_gemini_rag.py [--configs D] [--n 100]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.eval.metrics import all_metrics
from src.models import gemini_rag

ROOT = Path(__file__).resolve().parents[2]
PRED_PATH = ROOT / "datos" / "predicciones_val_gemini.jsonl"
METRICS_PATH = ROOT / "datos" / "metricas_gemini.json"
WORKERS = 6


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="D", help="Subconjunto de 'CD'")
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()

    val = pd.read_json(ROOT / "datos" / "splits" / "val.jsonl", lines=True)
    sample = val.sample(100, random_state=42).reset_index(drop=True).head(args.n)

    if PRED_PATH.exists():
        pred = pd.read_json(PRED_PATH, lines=True)
        if len(pred) != len(sample) or pred.texto_inga.tolist() != sample.texto_inga.tolist():
            pred = sample[["texto_inga", "texto_es"]].copy()
    else:
        pred = sample[["texto_inga", "texto_es"]].copy()

    metrics = json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}
    metrics["_model"] = gemini_rag.DEFAULT_MODEL
    metrics["_n"] = len(sample)

    for cfg in args.configs:
        use_rag = cfg == "D"
        for direccion, src_col, ref_col in (
            ("inga2es", "texto_inga", "texto_es"),
            ("es2inga", "texto_es", "texto_inga"),
        ):
            col = f"hyp_{cfg}_{direccion}"
            if col not in pred.columns:
                pred[col] = None
            pendientes = [i for i in pred.index if not pred.at[i, col]]
            fuentes = pred[src_col].tolist()

            # El retrieval va en serie (LanceDB + embeddings); solo el LLM en paralelo.
            ctxs = {}
            if use_rag:
                for i in tqdm(pendientes, desc=f"{cfg} {direccion} retrieval"):
                    ctxs[i] = gemini_rag.retrieve(fuentes[i], direccion)

            def run(i: int) -> tuple[int, str]:
                try:
                    return i, gemini_rag.translate(
                        fuentes[i], direccion, use_rag=use_rag, ctx=ctxs.get(i)
                    )
                except Exception as e:  # se deja vacio para reintentar en la proxima corrida
                    print(f"[{col} #{i}] {type(e).__name__}: {str(e)[:200]}")
                    return i, ""

            with ThreadPoolExecutor(WORKERS) as pool:
                for i, hyp in tqdm(pool.map(run, pendientes), total=len(pendientes), desc=f"{cfg} {direccion} LLM"):
                    pred.at[i, col] = hyp or None
            pred.to_json(PRED_PATH, orient="records", lines=True, force_ascii=False)

            faltan = int(pred[col].isna().sum())
            if faltan:
                print(f"{col}: faltan {faltan} predicciones; vuelve a correr para completarlas.")
                continue
            m = all_metrics(pred[ref_col].tolist(), pred[col].tolist())
            metrics[f"config_{cfg}_gemini_{'rag' if use_rag else 'zeroshot'}_{direccion}"] = m
            print(col, m)
            METRICS_PATH.write_text(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
