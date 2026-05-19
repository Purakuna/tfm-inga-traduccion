"""Generador del notebook 10: medicion de configs A (NLLB zero-shot) y B (NLLB+LoRA) bidireccional."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "10_medicion_nllb_configs.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(t): nb.cells.append(nbf.v4.new_markdown_cell(t))
def code(t): nb.cells.append(nbf.v4.new_code_cell(t))


md(
    """# Notebook 10 - Medicion configs A y B (NLLB zero-shot vs LoRA) bidireccional

**Entrega 2 - Fase 6 (parcial).**

Mide dos configuraciones del eje NMT multilingue sobre el val set,
en ambas direcciones (inga2es y es2inga):

- **Config A**: NLLB-200-distilled-600M zero-shot usando codigo `quy_Latn`
  (Quechua Ayacucho) como aproximacion al Inga, sin fine-tuning.
- **Config B**: NLLB-200-distilled-600M + adapter LoRA bidireccional
  entrenado en Notebook 09.

Metricas reportadas: BLEU, chrF++, BERTScore.

## Limitacion deliberada

Val set acotado a 100 ejemplos por direccion (200 total) para mantener
tiempos controlados. Los 558 del val set completo se reservan
para Entrega Final.
"""
)

code(
    """import sys
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import pandas as pd
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from peft import PeftModel
from tqdm import tqdm

from src.models.nllb_lora import (
    NLLB_MODEL_NAME, LANG_CODE_INGA, LANG_CODE_ES, get_device, set_direction,
)
from src.eval.metrics import all_metrics

DEVICE = get_device()
LORA_DIR = ROOT / "models" / "nllb-inga-lora-v1"
VAL_N = 100
MAX_LEN = 128

val = pd.read_json(ROOT / "datos" / "splits" / "val.jsonl", lines=True)
val_sample = val.sample(VAL_N, random_state=42).reset_index(drop=True)
print(f"Val sample: {len(val_sample)} pares (mismo subset para inga2es y es2inga)")
print(f"Device: {DEVICE}")
"""
)

md("## Cargar modelo base + modelo LoRA")

code(
    """tokenizer = AutoTokenizer.from_pretrained(
    NLLB_MODEL_NAME, src_lang=LANG_CODE_INGA, tgt_lang=LANG_CODE_ES
)
model_base = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL_NAME).to(DEVICE)
model_base.train(False)
print("Modelo base cargado en modo inferencia")

if LORA_DIR.exists() and (LORA_DIR / "adapter_config.json").exists():
    base_for_lora = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL_NAME).to(DEVICE)
    model_lora = PeftModel.from_pretrained(base_for_lora, str(LORA_DIR)).to(DEVICE)
    model_lora.train(False)
    LORA_DISPONIBLE = True
    print("Modelo LoRA cargado en modo inferencia")
else:
    LORA_DISPONIBLE = False
    print("WARNING: LoRA adapter no encontrado en", LORA_DIR)
    print("Config B no se medira hasta que NB09 termine.")
"""
)

md("## Funcion de inferencia bidireccional")

code(
    r'''def translate_batch(model, tokenizer, sentences, direccion: str, batch_size: int = 8):
    """Traduce un batch de oraciones en la direccion indicada."""
    set_direction(tokenizer, direccion)
    target_code = LANG_CODE_ES if direccion == "inga2es" else LANG_CODE_INGA
    forced_bos = tokenizer.convert_tokens_to_ids(target_code)
    hyps = []
    for i in tqdm(range(0, len(sentences), batch_size), desc=f"{model.__class__.__name__}/{direccion}"):
        batch = sentences[i:i + batch_size]
        inputs = tokenizer(
            batch, return_tensors="pt", truncation=True, padding=True, max_length=MAX_LEN
        ).to(DEVICE)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos,
                max_new_tokens=MAX_LEN,
                num_beams=4,
            )
        hyps.extend(tokenizer.batch_decode(out, skip_special_tokens=True))
    return hyps
'''
)

md("## Medir config A: NLLB zero-shot, ambas direcciones")

code(
    """inga_sents = val_sample.texto_inga.tolist()
es_sents = val_sample.texto_es.tolist()

# Direccion inga2es
hyps_A_inga2es = translate_batch(model_base, tokenizer, inga_sents, "inga2es")
metrics_A_inga2es = all_metrics(es_sents, hyps_A_inga2es)
print(f"Config A inga2es: {metrics_A_inga2es}")

# Direccion es2inga
hyps_A_es2inga = translate_batch(model_base, tokenizer, es_sents, "es2inga")
metrics_A_es2inga = all_metrics(inga_sents, hyps_A_es2inga)
print(f"Config A es2inga: {metrics_A_es2inga}")
"""
)

md("## Medir config B: NLLB + LoRA, ambas direcciones")

code(
    """if LORA_DISPONIBLE:
    hyps_B_inga2es = translate_batch(model_lora, tokenizer, inga_sents, "inga2es")
    metrics_B_inga2es = all_metrics(es_sents, hyps_B_inga2es)
    print(f"Config B inga2es: {metrics_B_inga2es}")

    hyps_B_es2inga = translate_batch(model_lora, tokenizer, es_sents, "es2inga")
    metrics_B_es2inga = all_metrics(inga_sents, hyps_B_es2inga)
    print(f"Config B es2inga: {metrics_B_es2inga}")
else:
    hyps_B_inga2es, hyps_B_es2inga = [None]*len(inga_sents), [None]*len(es_sents)
    metrics_B_inga2es, metrics_B_es2inga = None, None
    print("Config B no medida (LoRA no disponible)")
"""
)

md("## Consolidar metricas + persistir predicciones")

code(
    """resultados = {
    "config_A_nllb_zeroshot_inga2es": metrics_A_inga2es,
    "config_A_nllb_zeroshot_es2inga": metrics_A_es2inga,
    "config_B_nllb_lora_inga2es": metrics_B_inga2es,
    "config_B_nllb_lora_es2inga": metrics_B_es2inga,
}

OUT_METRICS = ROOT / "datos" / "metricas_entrega2.json"
OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
with OUT_METRICS.open("w") as f:
    json.dump(resultados, f, indent=2)
print(f"Metricas: {OUT_METRICS}")
print(json.dumps(resultados, indent=2))

pred = val_sample.copy()
pred["hyp_A_inga2es"] = hyps_A_inga2es
pred["hyp_A_es2inga"] = hyps_A_es2inga
pred["hyp_B_inga2es"] = hyps_B_inga2es
pred["hyp_B_es2inga"] = hyps_B_es2inga
OUT_PRED = ROOT / "datos" / "predicciones_val_AB.jsonl"
pred.to_json(OUT_PRED, orient="records", lines=True, force_ascii=False)
print(f"Predicciones: {OUT_PRED}")
"""
)

md("## Inspeccion cualitativa")

code(
    """import random
random.seed(0)
for i in random.sample(range(len(val_sample)), 3):
    print(f"--- Ejemplo {i} ---")
    print(f"INGA orig: {val_sample.iloc[i].texto_inga[:140]}")
    print(f"ES gold:   {val_sample.iloc[i].texto_es[:140]}")
    print(f"A->ES:     {hyps_A_inga2es[i][:140]}")
    if LORA_DISPONIBLE:
        print(f"B->ES:     {hyps_B_inga2es[i][:140]}")
    print(f"A->INGA:   {hyps_A_es2inga[i][:140]}")
    if LORA_DISPONIBLE:
        print(f"B->INGA:   {hyps_B_es2inga[i][:140]}")
    print()
"""
)

nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
