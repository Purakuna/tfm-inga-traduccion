"""API unificada de retrieval multi-indice para el RAG del TFM.

Consulta los tres indices del sistema (lexico, gramatical, ejemplos) en
paralelo y devuelve los top-k de cada uno. El reranking con cross-encoder
queda fuera de scope para Entrega 2 (Entrega Final).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .indexes import search


@dataclass
class RetrievedContext:
    """Bundle del contexto recuperado por el RAG para una query."""

    query: str
    lexico: list[dict] = field(default_factory=list)
    gramatical: list[dict] = field(default_factory=list)
    ejemplos: list[dict] = field(default_factory=list)

    def total(self) -> int:
        return len(self.lexico) + len(self.gramatical) + len(self.ejemplos)


def retrieve(query: str, top_k_per_index: int = 5) -> RetrievedContext:
    """Recupera top-k del indice lexico, gramatical y de ejemplos."""
    return RetrievedContext(
        query=query,
        lexico=search("lexico", query, top_k_per_index),
        gramatical=search("gramatical", query, top_k_per_index),
        ejemplos=search("ejemplos", query, top_k_per_index),
    )
