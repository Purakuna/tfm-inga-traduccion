"""Generador del notebook 09: fine-tuning LoRA bidireccional sobre NLLB-200-distilled-600M."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "09_finetuning_lora.ipynb"

nb = nbf.v4.new_notebook()
nb.cells = []


def md(t): nb.cells.append(nbf.v4.new_markdown_cell(t))
def code(t): nb.cells.append(nbf.v4.new_code_cell(t))


md(
    """# Notebook 09 - Fine-tuning LoRA bidireccional sobre NLLB-200

**Entrega 2.** Entrena adaptadores LoRA sobre `facebook/nllb-200-distilled-600M`
con el corpus paralelo Inga-espanol duplicado en ambas direcciones
(Inga -> espanol y espanol -> Inga). El mismo adapter puede servir luego
para inferir en cualquiera de las dos direcciones segun los codigos
NLLB src/tgt que se le pasen al tokenizer en tiempo de inferencia.

## Configuracion

- **Modelo base**: NLLB-200-distilled-600M (~600M params)
- **Codigos NLLB**: `quy_Latn` para Inga (transferencia desde Quechua Ayacucho)
  y `spa_Latn` para espanol
- **LoRA**: r=16, alpha=32, dropout=0.1, target=q_proj+v_proj. Entrena ~0.2%
  de los parametros totales
- **Optimizador**: AdamW, lr=3e-4, warmup 100 steps
- **Batch**: 8 ejemplos por device, 3 epochs
- **Device**: MPS (Apple Silicon) o CUDA si esta disponible
- **Tiempo estimado**: 1-3 horas en M4 Max segun particion

## Corpus duplicado

Cada par (inga, es) del train se replica como dos ejemplos:
- direccion=`inga2es`: source=inga, target=es, prepend quy_Latn
- direccion=`es2inga`: source=es, target=inga, prepend spa_Latn

El tokenizer se reconfigura sample-a-sample durante la tokenizacion.
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
import numpy as np
import matplotlib.pyplot as plt
from datasets import Dataset
import torch

from src.models.nllb_lora import (
    NLLB_MODEL_NAME, LANG_CODE_INGA, LANG_CODE_ES, get_device,
    load_model_and_tokenizer, wrap_with_lora, trainable_params_summary,
)

OUT_DIR = ROOT / "models" / "nllb-inga-lora-v1"
OUT_FIG = ROOT / "entrega2" / "figuras" / "fig11_lora_loss.png"
OUT_HIST = ROOT / "models" / "nllb-inga-lora-v1" / "training_history.json"

DEVICE = get_device()
print(f"Device: {DEVICE}")
"""
)

md(
    """## Cargar datos y duplicar direccion

Cada par del train aparece dos veces en el dataset de entrenamiento:
una con direccion `inga2es` y otra con `es2inga`. El dataset resultante
es 2x el corpus original.
"""
)

code(
    """train = pd.read_json(ROOT / "datos" / "splits" / "train.jsonl", lines=True)
val = pd.read_json(ROOT / "datos" / "splits" / "val.jsonl", lines=True)
print(f"Train: {len(train):,} pares -> {len(train)*2:,} ejemplos bidireccionales")
print(f"Val:   {len(val):,} pares -> {len(val)*2:,} ejemplos bidireccionales")

def duplicar_bidireccional(df: pd.DataFrame) -> Dataset:
    \"\"\"Duplica cada par como direccion inga2es y direccion es2inga.\"\"\"
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "src_lang": LANG_CODE_INGA,
            "tgt_lang": LANG_CODE_ES,
            "src_text": row["texto_inga"],
            "tgt_text": row["texto_es"],
        })
        rows.append({
            "src_lang": LANG_CODE_ES,
            "tgt_lang": LANG_CODE_INGA,
            "src_text": row["texto_es"],
            "tgt_text": row["texto_inga"],
        })
    return Dataset.from_list(rows)

ds_train = duplicar_bidireccional(train).shuffle(seed=42)
ds_val = duplicar_bidireccional(val).shuffle(seed=42)
print(f"Dataset train (bidireccional): {len(ds_train):,}")
print(f"Dataset val (bidireccional): {len(ds_val):,}")
"""
)

md(
    """## Cargar modelo + tokenizer y aplicar LoRA"""
)

code(
    """model, tokenizer = load_model_and_tokenizer(direccion="inga2es", device=DEVICE)
model = wrap_with_lora(model, r=16, alpha=32, dropout=0.1)
print(trainable_params_summary(model))
"""
)

md(
    """## Tokenizar

Para cada ejemplo se reconfigura el tokenizer con los codigos src/tgt
correspondientes. Esto inyecta el token de lengua correcto al inicio
del input.
"""
)

code(
    r'''MAX_LEN = 128

def tokenize_example(example):
    """Tokeniza un ejemplo con src/tgt segun direccion del par.

    En transformers v5, as_target_tokenizer() fue removido. Se usa el
    parametro text_target del tokenizer para procesar source y target
    en una sola llamada.
    """
    tokenizer.src_lang = example["src_lang"]
    tokenizer.tgt_lang = example["tgt_lang"]
    out = tokenizer(
        text=example["src_text"],
        text_target=example["tgt_text"],
        truncation=True,
        padding="max_length",
        max_length=MAX_LEN,
        return_tensors=None,
    )
    return out


# Tokenizacion sample-by-sample (la batch tokenization mezclaria src_lang)
ds_train_tok = ds_train.map(tokenize_example, remove_columns=ds_train.column_names)
ds_val_tok = ds_val.map(tokenize_example, remove_columns=ds_val.column_names)
print(f"Train tokenizado: {len(ds_train_tok):,}")
print(f"Val tokenizado: {len(ds_val_tok):,}")
'''
)

md("## Trainer y entrenamiento")

code(
    """from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer, DataCollatorForSeq2Seq

OUT_DIR.mkdir(parents=True, exist_ok=True)

args = Seq2SeqTrainingArguments(
    output_dir=str(OUT_DIR),
    num_train_epochs=3,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    learning_rate=3e-4,
    warmup_steps=100,
    logging_steps=20,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=1,
    predict_with_generate=False,
    report_to=[],
    fp16=False,
    bf16=False,
    use_cpu=(DEVICE == "cpu"),
)

trainer = Seq2SeqTrainer(
    model=model,
    args=args,
    train_dataset=ds_train_tok,
    eval_dataset=ds_val_tok,
    data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
)

train_result = trainer.train()
trainer.save_model(str(OUT_DIR))
print(f"Modelo guardado en: {OUT_DIR}")
"""
)

md("## Persistir history + figura 11 (curva de loss)")

code(
    """import json

hist = trainer.state.log_history
with open(OUT_HIST, "w") as f:
    json.dump(hist, f, indent=2)
print(f"History guardada: {OUT_HIST}")

# Curva de loss de training
train_loss = [(h["step"], h["loss"]) for h in hist if "loss" in h]
eval_loss = [(h["step"], h["eval_loss"]) for h in hist if "eval_loss" in h]

fig, ax = plt.subplots(figsize=(9, 5))
if train_loss:
    s, l = zip(*train_loss)
    ax.plot(s, l, label="train loss", color="#3b82f6", alpha=0.85)
if eval_loss:
    s, l = zip(*eval_loss)
    ax.plot(s, l, label="val loss", color="#ef4444", marker="o", linestyle="--")
ax.set_xlabel("Step")
ax.set_ylabel("Loss")
ax.set_title("Entrenamiento LoRA bidireccional sobre NLLB-200-distilled-600M")
ax.legend()
ax.grid(alpha=0.3)
OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_FIG, dpi=150, bbox_inches="tight")
plt.show()
print(f"Figura: {OUT_FIG}")
"""
)

md("## Smoke test de inferencia en ambas direcciones")

code(
    r'''from src.models.nllb_lora import set_direction

ejemplos_smoke = val.head(2)
for _, row in ejemplos_smoke.iterrows():
    # Inga -> ES
    set_direction(tokenizer, "inga2es")
    inp = tokenizer(row["texto_inga"], return_tensors="pt", truncation=True, max_length=MAX_LEN).to(DEVICE)
    out = model.generate(
        **inp,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids(LANG_CODE_ES),
        max_new_tokens=MAX_LEN,
    )
    pred_es = tokenizer.batch_decode(out, skip_special_tokens=True)[0]

    # ES -> Inga
    set_direction(tokenizer, "es2inga")
    inp = tokenizer(row["texto_es"], return_tensors="pt", truncation=True, max_length=MAX_LEN).to(DEVICE)
    out = model.generate(
        **inp,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids(LANG_CODE_INGA),
        max_new_tokens=MAX_LEN,
    )
    pred_inga = tokenizer.batch_decode(out, skip_special_tokens=True)[0]

    print(f"INGA orig:  {row['texto_inga'][:120]}")
    print(f"ES gold:    {row['texto_es'][:120]}")
    print(f"-> ES pred: {pred_es[:120]}")
    print(f"-> INGA pred (de ES gold): {pred_inga[:120]}")
    print("-" * 80)
'''
)

nbf.write(nb, OUT)
print(f"Notebook escrito en: {OUT}")
