# Backend del agente wiki Inga

FastAPI + SSE. Implementa la seccion 5 del contrato
(`docs/superpowers/specs/2026-09-19-inga-wiki-agent-design.md`); el agente vive en `src/agent/`.

## Arranque

Puerto por defecto: **8010**. En esta maquina el 8000 lo ocupa un contenedor Docker ajeno,
asi que el proxy `/api` del frontend (Vite, 5173) debe apuntar a `http://localhost:8010`.

```
PYTHONPATH=. uv run uvicorn webapp.backend.main:app --port 8010
```

Necesita `GOOGLE_API_KEY` en `.env`. Variables opcionales: `GEMINI_MODEL` (por defecto
`gemini-3.1-pro-preview`), `GEMINI_THINKING_LEVEL` (por defecto `LOW`), `INGA_WIKI_DB`.
Si existe `webapp/frontend/dist`, se sirve en `/` con fallback de SPA.

## Pruebas de extremo a extremo sin tocar la wiki real

El feedback escribe en la wiki. Para probar, se trabaja sobre una copia: el arbol markdown
(`pages/`) se crea junto a la copia de la base de datos.

```
mkdir -p /tmp/inga-e2e
PYTHONPATH=. uv run python -c "
import sqlite3
src = sqlite3.connect('datos/wiki/wiki.db'); dst = sqlite3.connect('/tmp/inga-e2e/wiki.db')
src.backup(dst); dst.close(); src.close()
from src.wiki.store import WikiStore
WikiStore('/tmp/inga-e2e/wiki.db').render_all()"
INGA_WIKI_DB=/tmp/inga-e2e/wiki.db PYTHONPATH=. uv run uvicorn webapp.backend.main:app --port 8010
```

## Herramientas del agente (seccion 8.2)

- Lectura: `fs_ls`, `fs_leer`, `fs_grep` sobre un sistema de archivos virtual de solo lectura
  (`wiki/` -> arbol markdown del store, `fuentes/` -> los tres documentos OCR), mas
  `corpus_buscar` y `buscar_por_glosa`. Rutas absolutas, `..`, `~` y symlinks se rechazan.
- Escritura: solo `inga_cli` (`src/agent/cli/`), y solo durante el triage de feedback. El codigo
  decide el estado de cada hecho en el camino de escritura: activo si trae una fuente no-feedback
  re-verificada, pendiente si no. El veredicto del triage se deriva de lo escrito.

## Tests

```
PYTHONPATH=. uv run pytest tests/agent -q
```
