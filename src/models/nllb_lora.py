"""Setup de NLLB-200 con adaptadores LoRA via peft para fine-tuning Inga<->espanol.

Se elige `facebook/nllb-200-distilled-600M` por su tamano compacto (600M
parametros) que cabe holgado en Apple M4 Max con MPS y entrena un epoch
sobre el corpus paralelo en pocos minutos.

NLLB usa codigos de lengua tipo FLORES-200. Para Inga aprovechamos
`quy_Latn` (Quechua Ayacucho) que ya esta presente en el modelo y comparte
familia linguistica.

**Bidireccional.** El mismo modelo y el mismo LoRA se entrenan sobre el
corpus duplicado: cada par (inga, es) se replica como (es, inga). Asi un
solo adapter sirve para inferir en ambas direcciones segun los codigos
src_lang / tgt_lang que se le pasen al tokenizer en tiempo de inferencia.
"""
from __future__ import annotations

from typing import Literal

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

NLLB_MODEL_NAME = "facebook/nllb-200-distilled-600M"

# Codigos NLLB (FLORES-200)
LANG_CODE_INGA = "quy_Latn"  # quechua Ayacucho (transferencia desde lengua quechua)
LANG_CODE_ES = "spa_Latn"

Direccion = Literal["inga2es", "es2inga"]


def get_device() -> str:
    """Devuelve el device preferido: MPS (Apple Silicon) > CUDA > CPU."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_model_and_tokenizer(
    model_name: str = NLLB_MODEL_NAME,
    direccion: Direccion = "inga2es",
    device: str | None = None,
):
    """Carga modelo + tokenizer NLLB con src/tgt segun direccion solicitada.

    `direccion`:
      - 'inga2es': src=quy_Latn, tgt=spa_Latn
      - 'es2inga': src=spa_Latn, tgt=quy_Latn
    """
    device = device or get_device()
    if direccion == "inga2es":
        src_lang, tgt_lang = LANG_CODE_INGA, LANG_CODE_ES
    elif direccion == "es2inga":
        src_lang, tgt_lang = LANG_CODE_ES, LANG_CODE_INGA
    else:
        raise ValueError(f"direccion debe ser 'inga2es' o 'es2inga', recibido: {direccion}")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name, src_lang=src_lang, tgt_lang=tgt_lang
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model = model.to(device)
    return model, tokenizer


def set_direction(tokenizer, direccion: Direccion) -> None:
    """Reconfigura un tokenizer ya cargado para una nueva direccion."""
    if direccion == "inga2es":
        tokenizer.src_lang, tokenizer.tgt_lang = LANG_CODE_INGA, LANG_CODE_ES
    elif direccion == "es2inga":
        tokenizer.src_lang, tokenizer.tgt_lang = LANG_CODE_ES, LANG_CODE_INGA
    else:
        raise ValueError(f"direccion debe ser 'inga2es' o 'es2inga'")


def wrap_with_lora(
    model,
    r: int = 16,
    alpha: int = 32,
    dropout: float = 0.1,
    target_modules: tuple[str, ...] = ("q_proj", "v_proj"),
):
    """Envuelve el modelo con adaptadores LoRA configurables."""
    config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=r,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=list(target_modules),
    )
    model = get_peft_model(model, config)
    return model


def trainable_params_summary(model) -> str:
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return (
        f"Parametros entrenables: {trainable:,} ({100*trainable/total:.3f}% de {total:,} totales)"
    )
