"""Pipeline de traduccion Inga<->espanol con Gemini y RAG multi-indice.

Reutiliza los prompts y el formato de contexto de claude_rag para que la
comparacion entre proveedores sea sobre el mismo prompt. A diferencia de
claude_rag.translate, aqui el indice de ejemplos se elige segun la direccion
('ejemplos' para inga2es, 'ejemplos_es' para es2inga).
"""
from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from src.models.claude_rag import (
    SYSTEM_PROMPT_ES2INGA,
    SYSTEM_PROMPT_INGA2ES,
    Direccion,
    build_prompt,
)
from src.rag.indexes import search
from src.rag.retriever import RetrievedContext

load_dotenv()

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
# Gemini Pro razona antes de responder y ese razonamiento cuenta contra el
# limite de salida, asi que debe cubrir razonamiento + traduccion.
DEFAULT_MAX_TOKENS = 8192
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


def retrieve(sentence: str, direccion: Direccion, top_k: int = 5) -> RetrievedContext:
    """Recupera contexto RAG usando el indice de ejemplos de la direccion."""
    indice_ejemplos = "ejemplos" if direccion == "inga2es" else "ejemplos_es"
    return RetrievedContext(
        query=sentence,
        lexico=search("lexico", sentence, top_k),
        gramatical=search("gramatical", sentence, top_k),
        ejemplos=search(indice_ejemplos, sentence, top_k),
    )


def complete(system: str, prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Llama a Gemini y devuelve solo el texto de la respuesta."""
    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=DEFAULT_MAX_TOKENS,
    )
    for intento in range(_MAX_RETRIES):
        try:
            resp = client.models.generate_content(model=model, contents=prompt, config=config)
            break
        except genai_errors.APIError as e:
            # 429 (cuota) y 5xx son transitorios; el resto se propaga.
            if e.code not in (429, 500, 503) or intento == _MAX_RETRIES - 1:
                raise
            time.sleep(2 ** intento * 5)
    if not resp.text:
        motivo = resp.candidates[0].finish_reason if resp.candidates else resp.prompt_feedback
        raise RuntimeError(f"Gemini no devolvio texto: {motivo}")
    return resp.text.strip()


def translate(
    sentence: str,
    direccion: Direccion = "inga2es",
    use_rag: bool = True,
    top_k: int = 5,
    model: str = DEFAULT_MODEL,
    ctx: RetrievedContext | None = None,
) -> str:
    """Traduce una oracion en la direccion indicada con o sin RAG.

    Si se pasa `ctx` se usa ese contexto ya recuperado en vez de consultar
    los indices de nuevo.
    """
    if use_rag and ctx is None:
        ctx = retrieve(sentence, direccion, top_k=top_k)
    prompt = build_prompt(sentence, ctx if use_rag else None, direccion)
    system = SYSTEM_PROMPT_INGA2ES if direccion == "inga2es" else SYSTEM_PROMPT_ES2INGA
    return complete(system, prompt, model=model)
