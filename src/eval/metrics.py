"""Wrappers de metricas estandar de traduccion automatica.

Implementa BLEU, chrF++ y BERTScore con valores por defecto consistentes
con AmericasNLP y la literatura reciente sobre MT de bajos recursos
(Ebrahimi 2024, de Gibert 2025).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import sacrebleu


def bleu(refs: Sequence[str], hyps: Sequence[str]) -> float:
    """BLEU corpus-level (sacrebleu)."""
    return sacrebleu.corpus_bleu(list(hyps), [list(refs)]).score


def chrf(refs: Sequence[str], hyps: Sequence[str], word_order: int = 2) -> float:
    """chrF++ corpus-level (word_order=2 anade bigramas de palabra)."""
    return sacrebleu.corpus_chrf(list(hyps), [list(refs)], word_order=word_order).score


@lru_cache(maxsize=1)
def _load_bert_scorer():
    """Carga perezosamente el modelo de BERTScore (XLM-RoBERTa multilingual)."""
    from bert_score import BERTScorer
    return BERTScorer(lang="es", rescale_with_baseline=False)


def bertscore(refs: Sequence[str], hyps: Sequence[str]) -> float:
    """BERTScore F1 promedio sobre el corpus."""
    scorer = _load_bert_scorer()
    _, _, f1 = scorer.score(list(hyps), list(refs))
    return float(f1.mean().item())


def all_metrics(refs: Sequence[str], hyps: Sequence[str]) -> dict[str, float]:
    """Devuelve dict con BLEU, chrF++ y BERTScore para una corrida."""
    return {
        "bleu": round(bleu(refs, hyps), 4),
        "chrf": round(chrf(refs, hyps), 4),
        "bertscore": round(bertscore(refs, hyps), 4),
    }
