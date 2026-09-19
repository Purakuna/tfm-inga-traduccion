"""Puente entre los generadores sincronos del agente y una respuesta SSE.

El generador completo corre en UN hilo del pool (no bloquea el event loop y no
salta de hilo entre eventos); los eventos cruzan al loop por una cola asyncio.
Garantias: las excepciones salen como evento `error`, `done` es siempre el
ultimo mensaje, y se envian comentarios ": ping" mientras el modelo piensa para
que ningun proxy cierre la conexion por inactividad.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Callable, Iterator

from fastapi.responses import StreamingResponse

PING_SECONDS = 10.0
_END = object()


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def event_stream(make_gen: Callable[[], Iterator[dict]]) -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def put(item) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, item)
        except RuntimeError:  # loop cerrado (servidor apagandose)
            pass

    def worker() -> None:
        try:
            for item in make_gen():
                put(item)
        except Exception as e:  # los generadores ya lo capturan; esto es el ultimo seguro
            put({"event": "error", "data": {"message": f"{type(e).__name__}: {str(e)[:300]}"}})
        finally:
            put(_END)

    loop.run_in_executor(None, worker)
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=PING_SECONDS)
        except asyncio.TimeoutError:
            yield ": ping\n\n"
            continue
        if item is _END:
            break
        if item.get("event") == "done":
            continue  # se emite una sola vez, al final
        yield format_sse(item["event"], item.get("data") or {})
    yield format_sse("done", {})


def sse_response(make_gen: Callable[[], Iterator[dict]]) -> StreamingResponse:
    return StreamingResponse(
        event_stream(make_gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
