"""Fixtures comunes: almacen falso, Gemini guionizado y navegacion sin src/wiki."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_store import sample_store  # noqa: E402

from src.agent import core, llm, verify  # noqa: E402


def resp_text(text: str) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=[types.Part(text=text)]))])


def resp_calls(*calls: tuple[str, dict]) -> types.GenerateContentResponse:
    parts = [types.Part(function_call=types.FunctionCall(id=f"call_{i}", name=n, args=a),
                        thought_signature=b"firma" if i == 0 else None)
             for i, (n, a) in enumerate(calls)]
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=parts))])


class ScriptedLLM:
    """Sustituye llm.generate / generate_stream por una lista de respuestas."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple] = []

    def _next(self, contents, config):
        # copia superficial: el bucle sigue mutando la lista de contents
        self.calls.append((list(contents) if isinstance(contents, list) else contents, config))
        if not self.responses:
            raise AssertionError("el guion del LLM se quedo sin respuestas")
        return self.responses.pop(0)

    def generate(self, contents, config):
        return self._next(contents, config)

    def generate_stream(self, contents, config):
        yield self._next(contents, config)


@pytest.fixture
def store(tmp_path):
    """Almacen falso con su arbol markdown en un directorio temporal (montaje wiki/)."""
    return sample_store(tmp_path / "pages")


@pytest.fixture
def script(monkeypatch):
    def install(responses) -> ScriptedLLM:
        fake = ScriptedLLM(responses)
        monkeypatch.setattr(llm, "generate", fake.generate)
        monkeypatch.setattr(llm, "generate_stream", fake.generate_stream)
        return fake

    return install


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Sin red: ni declaraciones (piden cliente), ni embeddings, ni LanceDB."""
    monkeypatch.setattr(core, "declarations", lambda: ())
    monkeypatch.setattr(core, "search_examples", lambda texto, direccion, k=3: [
        {"inga": "Nuka wasipi kani.", "es": "Estoy en mi casa.", "ref": "Juan 1:1"}])
    monkeypatch.setattr(verify, "_lexico", lambda: {
        "sinchi": ["sinchi (adj): fuerte; duro"],
        "sinchiai": ["sinchiai (v.i.): ponerse fuerte; endurecerse; mantenerse fuerte"],
        "tukui": ["tukui (v): llegar a ser", "tukui (adj): todo"],
    })

    def fake_navigate(text, direccion, st):
        tokens = []
        for w in text.replace(",", " ").replace(".", " ").split():
            found = [p["id"] for p in st.find_pages(w.lower()[:5], kind="lemma", limit=3)]
            tokens.append({"token": w, "normalized": w.lower(), "lemma_pages": found,
                           "suffix_pages": ["suffix:ngapa"] if w.lower().endswith("ngapa") else [],
                           "resolved": bool(found)})
        return text.lower(), tokens

    monkeypatch.setattr(core, "navigate", fake_navigate)


def events_of(gen) -> list[dict]:
    return list(gen)


def by_type(events: list[dict], name: str) -> list[dict]:
    return [e["data"] for e in events if e["event"] == name]
