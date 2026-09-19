"""Capa fina sobre google-genai para el agente: reintentos y configuracion.

Todo el acceso a Gemini del agente pasa por `generate` y `generate_stream`,
asi los tests pueden sustituirlos sin tocar la red.
"""
from __future__ import annotations

import os
import time
from typing import Iterator

from google.genai import errors as genai_errors
from google.genai import types

from src.models.gemini_rag import _get_client

# Gemini Pro razona antes de responder y ese razonamiento cuenta contra el
# limite de salida, asi que debe cubrir razonamiento + respuesta.
MAX_OUTPUT_TOKENS = 12288
_MAX_RETRIES = 4
_TRANSITORIOS = (429, 500, 503)


def model_name() -> str:
    """Modelo activo (GEMINI_MODEL lo sobreescribe)."""
    return os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")


def build_config(
    system: str,
    tools: list[types.FunctionDeclaration] | None = None,
    thinking_level: str | None = "LOW",
    json_output: bool = False,
    allow_tools: bool = True,
    force_tool: str | None = None,
) -> types.GenerateContentConfig:
    """Arma la configuracion de una llamada.

    `thinking_level` LOW fue verificado contra gemini-3.1-pro-preview (MINIMAL
    no esta soportado por ese modelo). Con `tools` se desactiva el function
    calling automatico del SDK porque el bucle es manual.
    """
    kwargs: dict = {
        "system_instruction": system,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }
    nivel = os.environ.get("GEMINI_THINKING_LEVEL", thinking_level or "")
    if nivel:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=nivel)
    if json_output:
        kwargs["response_mime_type"] = "application/json"
    if tools:
        kwargs["tools"] = [types.Tool(function_declarations=tools)]
        kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
        if force_tool and allow_tools:
            # Obliga a llamar a ESA herramienta en este turno (el triage debe dejar algo escrito).
            kwargs["tool_config"] = types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
                mode="ANY", allowed_function_names=[force_tool]))
        elif not allow_tools:
            # Se mantienen las declaraciones (el historial tiene llamadas) pero
            # se prohibe llamar mas herramientas: toca responder.
            kwargs["tool_config"] = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="NONE")
            )
    return types.GenerateContentConfig(**kwargs)


def _reintentable(e: Exception, intento: int) -> bool:
    return (
        isinstance(e, genai_errors.APIError)
        and e.code in _TRANSITORIOS
        and intento < _MAX_RETRIES - 1
    )


def generate(contents, config: types.GenerateContentConfig) -> types.GenerateContentResponse:
    """generate_content con reintentos ante 429 y 5xx."""
    client = _get_client()
    for intento in range(_MAX_RETRIES):
        try:
            return client.models.generate_content(
                model=model_name(), contents=contents, config=config
            )
        except Exception as e:
            if not _reintentable(e, intento):
                raise
            time.sleep(2 ** intento * 3)
    raise RuntimeError("inalcanzable")


def generate_stream(
    contents, config: types.GenerateContentConfig
) -> Iterator[types.GenerateContentResponse]:
    """generate_content_stream con reintentos solo si falla antes del primer chunk."""
    client = _get_client()
    for intento in range(_MAX_RETRIES):
        emitido = False
        try:
            for chunk in client.models.generate_content_stream(
                model=model_name(), contents=contents, config=config
            ):
                emitido = True
                yield chunk
            return
        except Exception as e:
            if emitido or not _reintentable(e, intento):
                raise
            time.sleep(2 ** intento * 3)


def response_parts(resp: types.GenerateContentResponse) -> list[types.Part]:
    """Partes del primer candidato (lista vacia si no hay contenido)."""
    if not resp.candidates:
        return []
    content = resp.candidates[0].content
    return list(content.parts or []) if content else []


def parts_text(parts: list[types.Part]) -> str:
    """Texto visible de una lista de partes (sin los pensamientos)."""
    return "".join(p.text for p in parts if p.text and not p.thought)


def finish_reason(resp: types.GenerateContentResponse) -> str:
    if resp.candidates:
        return str(resp.candidates[0].finish_reason)
    return str(resp.prompt_feedback)
