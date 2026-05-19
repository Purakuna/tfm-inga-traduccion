"""Setup de NLLB-200 con adaptadores LoRA via peft para fine-tuning Inga<->espanol.

Se elige `facebook/nllb-200-distilled-600M` por su tamano compacto (600M
parametros) que cabe holgado en Apple M4 Max con MPS y entrena un epoch
sobre el corpus paralelo en pocos minutos.

NLLB usa codigos de lengua tipo FLORES-200. Para Inga aprovechamos
`quy_Latn` (Quechua Ayacucho) que ya esta presente en el modelo y comparte
familia linguistica.
"""
from __future__ import annotations

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

NLLB_MODEL_NAME = "facebook/nllb-200-distilled-600M"

# Codigos NLLB (FLORES-200)
LANG_CODE_INGA = "quy_Latn"  # quechua Ayacucho (transferencia desde lengua quechua)
LANG_CODE_ES = "spa_Latn"


def get_device() -> str:
    """Devuelve el device preferido: MPS (Apple Silicon) > CUDA > CPU."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_model_and_tokenizer(
    model_name: str = NLLB_MODEL_NAME,
    src_lang: str = LANG_CODE_INGA,
    tgt_lang: str = LANG_CODE_ES,
    device: str | None = None,
):
    """Carga modelo + tokenizer NLLB con los codigos src/tgt fijados."""
    device = device or get_device()
    tokenizer = AutoTokenizer.from_pretrained(
        model_name, src_lang=src_lang, tgt_lang=tgt_lang
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model = model.to(device)
    return model, tokenizer


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
    """Devuelve un string con el conteo de parametros entrenables vs total."""
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return (
        f"Parametros entrenables: {trainable:,} ({100*trainable/total:.3f}% de {total:,} totales)"
    )
