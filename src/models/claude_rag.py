"""Pipeline de traduccion Inga<->espanol con Claude y RAG multi-indice.

Soporta ambas direcciones:
- 'inga2es': Inga -> espanol (mas natural para Claude, tiene mas datos)
- 'es2inga': espanol -> Inga (mas desafiante; Claude apenas conoce Inga)

Para cada direccion se construye un prompt estructurado distinto y se
consulta el indice de ejemplos apropiado (indexado por Inga o por espanol
segun corresponda).
"""
from __future__ import annotations

import os
from typing import Literal

import anthropic
from dotenv import load_dotenv

from src.rag.retriever import RetrievedContext, retrieve

load_dotenv()

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_MAX_TOKENS = 256

Direccion = Literal["inga2es", "es2inga"]

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


SYSTEM_PROMPT_INGA2ES = """Eres un sistema de traduccion automatica especializado en la lengua Inga, una variante quechua hablada en el departamento del Putumayo (Colombia) por aproximadamente 18.000 personas.

Tu tarea es traducir una oracion del Inga al espanol con maxima fidelidad semantica y naturalidad linguistica. El Inga es una lengua aglutinante con sufijos para casos gramaticales, similar al Quechua sureno; comparte rasgos morfosintacticos con el Quechua Ayacucho.

Responde unicamente con la traduccion al espanol, sin explicaciones, sin comentarios y sin reformular la pregunta."""

SYSTEM_PROMPT_ES2INGA = """Eres un sistema de traduccion automatica especializado en la lengua Inga, una variante quechua hablada en el departamento del Putumayo (Colombia) por aproximadamente 18.000 personas.

Tu tarea es traducir una oracion del espanol al Inga (variante del Putumayo) usando estricta fidelidad gramatical. El Inga es una lengua aglutinante con sufijos para casos gramaticales y orden basico SOV; comparte rasgos morfosintacticos con el Quechua Ayacucho.

Usa el vocabulario, las notas gramaticales y los ejemplos paralelos provistos como referencia. Si el contexto recuperado no cubre una palabra del espanol, intenta construir una forma plausible siguiendo las reglas aglutinantes del Inga, pero da prioridad a aprovechar el vocabulario suministrado.

Responde unicamente con la traduccion al Inga, sin explicaciones, sin comentarios y sin reformular la pregunta."""


def _formato_ejemplos(ctx_ejemplos: list[dict], direccion: Direccion) -> str:
    """Formatea ejemplos paralelos segun la direccion de traduccion."""
    if not ctx_ejemplos:
        return ""
    lineas = []
    for r in ctx_ejemplos[:5]:
        inga = r.get("texto_inga", "")
        es = r.get("texto_es", "")
        if direccion == "inga2es":
            lineas.append(f"- INGA: {inga}\n  ESPANOL: {es}")
        else:
            lineas.append(f"- ESPANOL: {es}\n  INGA: {inga}")
    return "Ejemplos paralelos similares (traducciones de referencia):\n" + "\n".join(lineas)


def build_prompt(sentence: str, ctx: RetrievedContext | None, direccion: Direccion) -> str:
    """Construye el prompt de usuario con el contexto RAG opcional."""
    if direccion == "inga2es":
        cabecera = "Traduce esta oracion del Inga al espanol"
    else:
        cabecera = "Traduce esta oracion del espanol al Inga"

    if ctx is None:
        return f"{cabecera}:\n\n{sentence}"

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
    ejemplos = _formato_ejemplos(ctx.ejemplos, direccion)
    if ejemplos:
        secciones.append(ejemplos)

    contexto = "\n\n".join(secciones)
    return f"{contexto}\n\n{cabecera}:\n\n{sentence}"


def translate(
    sentence: str,
    direccion: Direccion = "inga2es",
    use_rag: bool = True,
    top_k: int = 5,
    model: str = DEFAULT_MODEL,
) -> str:
    """Traduce una oracion en la direccion indicada con o sin RAG.

    Para 'es2inga' usa el indice 'ejemplos_es' (que se construye en el
    notebook 08 indexando por texto_es); para 'inga2es' usa 'ejemplos'.
    """
    ctx = None
    if use_rag:
        # El retriever consulta los tres indices estandar; para es2inga
        # el indice de ejemplos se cambia via un alias temporal en el
        # notebook 11 (overrides el nombre "ejemplos" -> "ejemplos_es").
        ctx = retrieve(sentence, top_k_per_index=top_k)
    prompt = build_prompt(sentence, ctx, direccion)
    system = SYSTEM_PROMPT_INGA2ES if direccion == "inga2es" else SYSTEM_PROMPT_ES2INGA
    client = _get_client()
    resp = client.messages.create(
        model=model,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()
