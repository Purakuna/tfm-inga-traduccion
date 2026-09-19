"""Fixtures comunes: una wiki temporal con unas pocas paginas de lema."""
from __future__ import annotations

import pytest
from wiki_helpers import LEMAS, lemma_action

from src.wiki.store import WikiStore


@pytest.fixture()
def store(tmp_path) -> WikiStore:
    return WikiStore(tmp_path / "wiki.db")


@pytest.fixture()
def wiki(store) -> WikiStore:
    for lema, senses, aliases, es_rows in LEMAS:
        res = store.apply_action(lemma_action(lema, senses, aliases, es_rows), actor="seed")
        assert res["ok"], res
    return store
