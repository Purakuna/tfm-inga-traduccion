"""Wrapper de Gemini text-embedding-004 para indexacion vectorial del TFM.

Lee GOOGLE_API_KEY desde el entorno (cargado por python-dotenv si hay .env).
Batch por defecto de 100 textos (limite documentado de la API). Devuelve
embeddings de 768 dimensiones, compatibles con LanceDB.
"""
from __future__ import annotations

import os
import time
from typing import Sequence

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

load_dotenv()

_MODEL = "gemini-embedding-001"
_DIM = 768  # reduced from default 3072 via output_dimensionality
_BATCH = 50  # menor para evitar rate limit per-text
_SLEEP_BETWEEN_BATCHES = 1.2  # ~50 req/s baseline, bajo del limite 3000/min
_MAX_RETRIES = 5

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta GOOGLE_API_KEY (o GEMINI_API_KEY) en el entorno. "
                "Copia .env.example a .env y rellena la clave."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def embed_texts(texts: Sequence[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Devuelve embeddings de 768 dimensiones para una lista de textos.

    task_type acepta RETRIEVAL_DOCUMENT (default, para indexar) o
    RETRIEVAL_QUERY (para queries de busqueda). Otros valores aceptados
    por la API: SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING.
    """
    client = _get_client()
    out: list[list[float]] = []
    total_batches = (len(texts) + _BATCH - 1) // _BATCH
    for batch_idx, i in enumerate(range(0, len(texts), _BATCH)):
        batch = list(texts[i:i + _BATCH])
        resp = _embed_with_retry(client, batch, task_type)
        out.extend([e.values for e in resp.embeddings])
        # Throttle entre batches (excepto el ultimo)
        if batch_idx + 1 < total_batches:
            time.sleep(_SLEEP_BETWEEN_BATCHES)
    return out


def _embed_with_retry(client: genai.Client, batch: list[str], task_type: str):
    """Llama a embed_content con reintento exponencial ante 429 (rate limit)."""
    delay = 5.0
    for attempt in range(_MAX_RETRIES):
        try:
            return client.models.embed_content(
                model=_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=_DIM,
                ),
            )
        except genai_errors.ClientError as exc:
            if "429" not in str(exc) and "RESOURCE_EXHAUSTED" not in str(exc):
                raise
            if attempt == _MAX_RETRIES - 1:
                raise
            # Parse retryDelay si lo trae el error; sino exponencial
            wait = delay * (2 ** attempt)
            print(f"[embeddings] rate limit, esperando {wait:.0f}s (intento {attempt+1}/{_MAX_RETRIES})")
            time.sleep(wait)
    raise RuntimeError("Reintentos de embed_content agotados")


def embed_query(text: str) -> list[float]:
    """Embedding para una query de retrieval (task_type RETRIEVAL_QUERY)."""
    return embed_texts([text], task_type="RETRIEVAL_QUERY")[0]


EMBEDDING_DIM = _DIM
MODEL_NAME = _MODEL
