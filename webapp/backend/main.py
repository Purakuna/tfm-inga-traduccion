"""API HTTP del agente wiki Inga (seccion 5 del contrato).

Puerto por defecto de este backend: 8010 (en esta maquina el 8000 lo ocupa un
contenedor Docker ajeno). El proxy /api del frontend debe apuntar a el.

Arranque: PYTHONPATH=. uv run uvicorn webapp.backend.main:app --port 8010
Base de datos alternativa (pruebas e2e sobre una copia): INGA_WIKI_DB=/ruta/wiki.db
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.agent import core, llm
from src.agent.review import ReviewError, feedback_facts, review_feedback
from webapp.backend.sse import sse_response

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

app = FastAPI(title="Inga Wiki Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_store: Any = None


def get_store() -> Any:
    """WikiStore compartido (abre una conexion por llamada, seguro entre hilos).

    Los tests lo sustituyen con `main.set_store(fake)`.
    """
    global _store
    if _store is None:
        from src.wiki.store import WikiStore

        _store = WikiStore()
    return _store


def set_store(store: Any) -> None:
    global _store
    _store = store


# Oraciones de muestra. Ninguna sale de val/test: son saludos y frases
# ilustrativas del diccionario, o frases cotidianas escritas a mano.
EXAMPLES = [
    {"direccion": "inga2es", "text": "Achka yukangapa, sinchi tuku yuyangapa.",
     "label": "Ortografía quechua que hay que normalizar"},
    {"direccion": "inga2es", "text": "Iapa sinchi wairami asutiwakurka.",
     "label": "Frase ilustrativa del diccionario"},
    {"direccion": "inga2es", "text": "Alli mas pakaripuangi.", "label": "Saludo de la mañana"},
    {"direccion": "inga2es", "text": "Nuka wasipi kani.", "label": "Oración cotidiana corta"},
    {"direccion": "es2inga", "text": "Yo estoy en mi casa", "label": "Oración cotidiana corta"},
    {"direccion": "es2inga", "text": "Mañana voy a trabajar en la chagra con mi padre",
     "label": "Vida diaria, sin registro bíblico"},
    {"direccion": "es2inga", "text": "El niño tiene hambre y quiere comer maíz",
     "label": "Vocabulario básico"},
    {"direccion": "es2inga", "text": "El que cree en el Hijo tiene vida eterna",
     "label": "Registro bíblico (dominio del corpus)"},
]


class TranslateBody(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    direccion: Literal["inga2es", "es2inga"]
    mode: Literal["fast", "agent"] = "fast"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskBody(BaseModel):
    translation_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=1200)
    history: list[ChatTurn] = []


class FeedbackBody(BaseModel):
    translation_id: str | None = None
    direccion: Literal["inga2es", "es2inga"]
    source_text: str = Field(min_length=1, max_length=1200)
    model_output: str = Field(default="", max_length=2000)
    correction: str = Field(min_length=1, max_length=2000)
    comment: str = Field(default="", max_length=2000)
    author: str = Field(default="anonimo", max_length=120)


class ReviewBody(BaseModel):
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=2000)


def _feedback_row(row: dict, store: Any) -> dict:
    out = dict(row)
    facts = feedback_facts(row, store)
    out["facts"] = [{**f, "id": f["fact_id"]} for f in facts]
    return out


# --- endpoints -------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": llm.model_name(), "wiki": get_store().stats()}


@app.get("/api/examples")
def examples() -> list[dict]:
    return EXAMPLES


@app.post("/api/translate")
def translate(body: TranslateBody):
    store = get_store()
    return sse_response(lambda: core.translate(body.text, body.direccion, body.mode, store=store))


@app.post("/api/ask")
def ask(body: AskBody):
    store = get_store()
    history = [h.model_dump() for h in body.history]
    return sse_response(lambda: core.ask(body.translation_id, body.question, history, store=store))


@app.post("/api/feedback")
def create_feedback(body: FeedbackBody):
    store = get_store()
    feedback_id = store.create_feedback(
        author=body.author.strip() or "anonimo",
        direccion=body.direccion,
        source_text=body.source_text.strip(),
        model_output=body.model_output.strip(),
        correction=body.correction.strip(),
        comment=body.comment.strip(),
        translation_id=(body.translation_id or None),
        status="new",
    )
    return sse_response(lambda: core.triage_feedback(feedback_id, store=store))


@app.get("/api/feedback")
def list_feedback(status: str | None = Query(default=None)) -> list[dict]:
    store = get_store()
    if status and status not in ("new", "auto_applied", "pending_review", "approved", "rejected"):
        raise HTTPException(status_code=422, detail="status de feedback desconocido")
    return [_feedback_row(r, store) for r in store.list_feedback(status=status or None)]


@app.post("/api/feedback/{feedback_id}/review")
def review(feedback_id: int, body: ReviewBody) -> dict:
    store = get_store()
    if store.get_feedback(feedback_id) is None:
        raise HTTPException(status_code=404, detail=f"No existe el feedback {feedback_id}.")
    try:
        row = review_feedback(feedback_id, body.decision, body.reviewer, body.note, store=store)
    except ReviewError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _feedback_row(row, store)


@app.get("/api/wiki/stats")
def wiki_stats() -> dict:
    return get_store().stats()


@app.get("/api/wiki/pages")
def wiki_pages(
    kind: str | None = Query(default=None),
    q: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    store = get_store()
    kind = (kind or "").strip() or None
    if kind and kind not in core.KINDS:
        raise HTTPException(status_code=422, detail="kind desconocido")
    q = (q or "").strip()
    if q:
        # find_pages no pagina: se pide una ventana amplia y se corta aqui.
        found = store.find_pages(q, kind=kind, limit=500)
        return {"items": found[offset: offset + limit], "total": len(found)}
    items = store.list_pages(kind=kind, offset=offset, limit=limit)
    return {"items": items, "total": _count_pages(store, kind, offset, len(items))}


def _count_pages(store: Any, kind: str | None, offset: int, n_items: int) -> int:
    if hasattr(store, "count_pages"):
        return int(store.count_pages(kind))
    pages = (store.stats() or {}).get("pages") or {}
    if kind:
        return int(pages.get(kind, offset + n_items))
    return int(pages.get("total", sum(v for k, v in pages.items() if k != "total")))


@app.get("/api/wiki/pages/{page_id:path}")
def wiki_page(page_id: str) -> dict:
    page = get_store().get_page(page_id, include_inactive=True)
    if page is None:
        raise HTTPException(status_code=404, detail=f"No existe la pagina {page_id}.")
    return page


# --- frontend estatico (solo si existe el build) ----------------------------------
# La ruta se registra siempre y mira el disco en cada peticion, asi un build del
# frontend hecho despues de arrancar el servidor se sirve sin reiniciar.

@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/") or not FRONTEND_DIST.is_dir():
        raise HTTPException(status_code=404, detail="No existe esa ruta.")
    candidate = (FRONTEND_DIST / full_path).resolve()
    if full_path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
        return FileResponse(candidate)
    return FileResponse(FRONTEND_DIST / "index.html")
