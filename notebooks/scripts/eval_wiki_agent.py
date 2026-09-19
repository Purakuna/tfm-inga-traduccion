"""Mide el agente wiki sobre el mismo val sample (n=100, seed 42) de eval_gemini_rag.py.

Configs: F (wiki fast: paginas precargadas, una llamada) y G (wiki agent: bucle
de herramientas), ambas direcciones. Guarda predicciones en
datos/predicciones_val_wiki.jsonl (reanudable) y metricas en
datos/metricas_wiki.json. Las traducciones NO se guardan en la wiki (save=False)
para que ninguna oracion de val entre en datos/wiki/wiki.db.

Este script es el UNICO lugar del agente que lee datos/splits/val.jsonl.

Uso: PYTHONPATH=. uv run python notebooks/scripts/eval_wiki_agent.py [--configs FG] [--n 100]
Humo: ... --n 3 --out-dir /ruta/temporal   (no toca los archivos reales)
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.agent import core, llm
from src.eval.metrics import all_metrics
from src.wiki.store import WikiStore

ROOT = Path(__file__).resolve().parents[2]
PRED_NAME = "predicciones_val_wiki.jsonl"
METRICS_NAME = "metricas_wiki.json"
WORKERS = 6
MODES = {"F": "fast", "G": "agent"}


def run_one(text: str, direccion: str, mode: str, store: WikiStore) -> dict:
    """Consume el generador de translate y devuelve el resultado (o el error)."""
    out = {"hyp": "", "confidence": None, "n_tools": 0, "elapsed_s": None, "error": None}
    for e in core.translate(text, direccion, mode, store=store, save=False):
        if e["event"] == "result":
            out.update(hyp=e["data"]["translation"], confidence=e["data"]["confidence"],
                       elapsed_s=e["data"]["elapsed_s"])
        elif e["event"] == "tool_call":
            out["n_tools"] += 1
        elif e["event"] == "error":
            out["error"] = e["data"]["message"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="FG", help="Subconjunto de 'FG'")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out-dir", default=str(ROOT / "datos"),
                    help="Carpeta de salida (usar una temporal para pruebas de humo)")
    ap.add_argument("--workers", type=int, default=WORKERS)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path, metrics_path = out_dir / PRED_NAME, out_dir / METRICS_NAME

    val = pd.read_json(ROOT / "datos" / "splits" / "val.jsonl", lines=True)
    sample = val.sample(100, random_state=42).reset_index(drop=True).head(args.n)

    if pred_path.exists():
        pred = pd.read_json(pred_path, lines=True)
        if len(pred) != len(sample) or pred.texto_inga.tolist() != sample.texto_inga.tolist():
            pred = sample[["texto_inga", "texto_es"]].copy()
    else:
        pred = sample[["texto_inga", "texto_es"]].copy()

    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    metrics["_model"] = llm.model_name()
    metrics["_n"] = len(sample)

    store = WikiStore()  # una conexion por llamada: se comparte entre hilos sin problema
    metrics["_wiki"] = store.stats().get("pages")

    for cfg in args.configs:
        mode = MODES[cfg]
        for direccion, src_col, ref_col in (
            ("inga2es", "texto_inga", "texto_es"),
            ("es2inga", "texto_es", "texto_inga"),
        ):
            col = f"hyp_{cfg}_{direccion}"
            for extra in (col, f"conf_{cfg}_{direccion}", f"tools_{cfg}_{direccion}", f"secs_{cfg}_{direccion}"):
                if extra not in pred.columns:
                    pred[extra] = None
            pendientes = [i for i in pred.index if not pred.at[i, col]]
            fuentes = pred[src_col].tolist()

            def run(i: int) -> tuple[int, dict]:
                try:
                    r = run_one(fuentes[i], direccion, mode, store)
                except Exception as e:  # se deja vacio para reintentar en la proxima corrida
                    r = {"hyp": "", "error": f"{type(e).__name__}: {str(e)[:200]}"}
                if r.get("error"):
                    print(f"[{col} #{i}] {r['error'][:200]}")
                return i, r

            t0 = time.time()
            with ThreadPoolExecutor(args.workers) as pool:
                for i, r in tqdm(pool.map(run, pendientes), total=len(pendientes), desc=f"{cfg} {direccion}"):
                    pred.at[i, col] = r.get("hyp") or None
                    pred.at[i, f"conf_{cfg}_{direccion}"] = r.get("confidence")
                    pred.at[i, f"tools_{cfg}_{direccion}"] = r.get("n_tools")
                    pred.at[i, f"secs_{cfg}_{direccion}"] = r.get("elapsed_s")
            pred.to_json(pred_path, orient="records", lines=True, force_ascii=False)

            faltan = int(pred[col].isna().sum())
            if faltan:
                print(f"{col}: faltan {faltan} predicciones; vuelve a correr para completarlas.")
                continue
            m = all_metrics(pred[ref_col].tolist(), pred[col].tolist())
            secs = pd.to_numeric(pred[f"secs_{cfg}_{direccion}"], errors="coerce")
            tools = pd.to_numeric(pred[f"tools_{cfg}_{direccion}"], errors="coerce")
            m["latency_mean_s"] = round(float(secs.mean()), 2)
            m["latency_p50_s"] = round(float(secs.median()), 2)
            m["tool_calls_mean"] = round(float(tools.mean()), 2)
            m["confidence_counts"] = pred[f"conf_{cfg}_{direccion}"].value_counts().to_dict()
            if pendientes:
                m["wall_s_last_run"] = round(time.time() - t0, 1)
            metrics[f"config_{cfg}_wiki_{mode}_{direccion}"] = m
            print(col, m)
            metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
