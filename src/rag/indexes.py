"""Gestion de indices vectoriales LanceDB para el RAG multi-indice del TFM.

Tres indices independientes:
- lexico: derivado del Diccionario Inga (entradas lema -> glosa)
- gramatical: derivado de la Gramatica Pedagogica + Rosetta morfosintactico
- ejemplos: derivado del corpus paralelo de train (oracion Inga -> espanol)

LanceDB es embedded y persiste en `lance_indexes/` (gitignored por peso).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import lancedb
import pyarrow as pa

from .embeddings import EMBEDDING_DIM, embed_texts, embed_query

ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "lance_indexes"


def _connect():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(INDEX_DIR)


def build_index(name: str, records: Sequence[dict], text_field: str) -> int:
    """Construye un indice LanceDB a partir de records.

    Cada record debe ser un dict con al menos `text_field`. Se anade el
    campo `vector` con el embedding de Gemini del texto en `text_field`.
    Si el indice existe, se sobrescribe.

    Devuelve el numero de filas escritas.
    """
    if not records:
        raise ValueError(f"No hay records para indexar en '{name}'")

    textos = [r[text_field] for r in records]
    vectors = embed_texts(textos, task_type="RETRIEVAL_DOCUMENT")

    rows = []
    for r, v in zip(records, vectors):
        row = dict(r)
        row["vector"] = v
        rows.append(row)

    db = _connect()
    table = db.create_table(name, data=rows, mode="overwrite")
    return table.count_rows()


def search(name: str, query: str, top_k: int = 5) -> list[dict]:
    """Devuelve los `top_k` registros mas similares a `query` en el indice `name`."""
    db = _connect()
    table = db.open_table(name)
    qv = embed_query(query)
    return table.search(qv).limit(top_k).to_list()


def list_tables() -> list[str]:
    return _connect().table_names()


def count(name: str) -> int:
    return _connect().open_table(name).count_rows()
