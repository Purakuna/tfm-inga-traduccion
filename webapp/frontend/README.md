# Inga Wiki - frontend

Vite + React + TypeScript + Tailwind v4 + motion. Interfaz en espanol del
traductor inga - espanol. Habla con el backend solo por la API HTTP/SSE de la
seccion 5 de `docs/superpowers/specs/2026-09-19-inga-wiki-agent-design.md`.

## Comandos

```bash
cd webapp/frontend
npm install

npm run dev:mock   # demo sin backend (VITE_MOCK=1), http://localhost:5173
npm run dev        # contra el backend real; /api -> http://localhost:8010
npm run build      # tsc + vite build -> dist/ (el backend lo sirve en /)
npm run preview    # sirve dist/ en local
```

Backend real (desde la raiz del repo):
`PYTHONPATH=. uv run uvicorn webapp.backend.main:app --port 8010`

## Modo demostracion

`VITE_MOCK=1` reemplaza `fetch` por un backend simulado en el navegador
(`src/api/mock/`). Devuelve las mismas formas que la API, y los streams salen
como bytes SSE con `\r\n` y cortes de chunk aleatorios, asi que el parser real
se ejercita igual. Los datos son simulados, no la wiki real.

- `VITE_MOCK_SPEED=3` acelera las pausas (3x).
- Escribir solo `error` fuerza el estado de error del traductor.
- Una correccion que contenga "todo/todos/entero" termina en `auto_applied`;
  cualquier otra, en `pending_review`.
- El estado del mock (cola de revision, hechos nuevos) vive en memoria y se
  pierde al recargar.

## Estructura

- `src/api/types.ts` tipos de todos los payloads (espejo de la seccion 5).
- `src/api/sse.ts` lector SSE sobre POST (fetch + ReadableStream).
- `src/api/client.ts` un metodo por endpoint.
- `src/lib/useTranslate.ts` reductor que convierte eventos en estado de la vista.
- `src/components/` telar de tokens, bitacora, cajon de pagina, chat, veredicto.
- `src/views/` Traducir, Wiki, Revision, Acerca.

Las imagenes viven en `public/img/` (workstream E). Si falta alguna, el hueco
muestra un degradado disenado (`ImageSlot`).
