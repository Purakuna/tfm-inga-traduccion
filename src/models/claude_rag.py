"""Pipeline de traduccion Inga -> espanol con Claude y RAG multi-indice.

Construye prompts estructurados que inyectan el contexto recuperado del
RAG (lexico, gramatical, ejemplos paralelos) en el mensaje del usuario
a la API de Anthropic.
"""
from __future__ import annotations

import os

import anthropic
from dotenv import load_dotenv

from src.rag.retriever import RetrievedContext, retrieve

load_dotenv()

# Modelo Claude vigente al cierre de la investigacion. Sonnet 4.6 ofrece la
# mejor relacion costo/calidad para tareas de traduccion intensivas.
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 256

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta ANTHROPIC_API_KEY en el entorno. "
                "Copia .env.example a .env y rellena la clave."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = """Eres un sistema de traduccion automatica especializado en la lengua Inga, una variante quechua hablada en el departamento del Putumayo (Colombia) por aproximadamente 18.000 personas.

Tu tarea es traducir una oracion del Inga al espanol con maxima fidelidad semantica y naturalidad linguistica. El Inga es una lengua aglutinante con sufijos para casos gramaticales, similar al Quechua sureno; comparte rasgos morfosintacticos con el Quechua Ayacucho.

Responde unicamente con la traduccion al espanol, sin explicaciones, sin comentarios y sin reformular la pregunta."""


def build_prompt(sentence: str, ctx: RetrievedContext | None) -> str:
    """Construye el prompt de usuario con el contexto RAG opcional."""
    if ctx is None:
        return f"Traduce esta oracion del Inga al espanol:\n\n{sentence}"

    secciones = []
    if ctx.lexico:
        lineas = []
        for r in ctx.lexico[:5]:
            lema = r.get("lema", "?")
            cat = r.get("cat", "?")
            glosa = r.get("glosa", "?")
            lineas.append(f"- {lema} ({cat}): {glosa}")
        secciones.append("Vocabulario Inga relevante:\n" + "\n".join(lineas))
    if ctx.gramatical:
        lineas = []
        for r in ctx.gramatical[:3]:
            fuente = r.get("fuente", "?")
            texto = r.get("text", "")[:400]
            lineas.append(f"- ({fuente}) {texto}")
        secciones.append("Notas gramaticales del Inga:\n" + "\n".join(lineas))
    if ctx.ejemplos:
        lineas = []
        for r in ctx.ejemplos[:5]:
            inga = r.get("texto_inga", "")
            es = r.get("texto_es", "")
            lineas.append(f"- INGA: {inga}\n  ESPANOL: {es}")
        secciones.append("Ejemplos paralelos similares (traducciones de referencia):\n" + "\n".join(lineas))

    contexto = "\n\n".join(secciones)
    return (
        f"{contexto}\n\n"
        f"Traduce esta oracion del Inga al espanol:\n\n{sentence}"
    )


def translate(sentence: str, use_rag: bool = True, top_k: int = 5, model: str = DEFAULT_MODEL) -> str:
    """Traduce una oracion. Si `use_rag` es False, hace zero-shot sin contexto."""
    ctx = retrieve(sentence, top_k_per_index=top_k) if use_rag else None
    prompt = build_prompt(sentence, ctx)
    client = _get_client()
    resp = client.messages.create(
        model=model,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()
