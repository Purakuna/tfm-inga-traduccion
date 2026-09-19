# Inga Wiki Agent - design and build contract (2026-09-19)

Pivot of the chunk-based RAG (config D) into a curated, cited wiki that an agent
reads with tools, plus a feedback loop that improves the wiki. All LLM calls use
Gemini (`gemini-3.1-pro-preview`, override with env `GEMINI_MODEL`). Embeddings
and the LanceDB indexes in `lance_indexes/` stay as they are and are READ ONLY.
No LangChain: the agent loop is hand written on `google-genai` function calling.

This file is the contract between parallel workstreams. Do not change signatures
or payload shapes here without telling the integrator.

## 0. Repo conventions

- Python 3.11, run everything with `PYTHONPATH=. uv run ...` from the repo root.
- Do NOT edit `pyproject.toml`/`uv.lock` (fastapi, uvicorn, sse-starlette, httpx,
  google-genai, lancedb, pandas, pytest are already installed). If you need a
  package, say so in your final report instead.
- Code comments and docstrings in Spanish without accents, ASCII punctuation only
  (no em dashes, curly quotes or unicode ellipsis), matching `src/`. Identifiers
  in the style of the existing code.
- Never print, log or commit API keys. Keys come from `.env` via `load_dotenv()`
  (`GOOGLE_API_KEY`). Reuse `src/models/gemini_rag._get_client()`.
- Do not touch: `datos/splits/`, `lance_indexes/`, `src/models/claude_rag.py`,
  `deposito/`, `entrega*/`, notebooks. Do not run git commit.
- Each workstream owns its directories (section 7). Do not write outside them.

## 1. Sources of truth

| Source | Where | Source type / ref format |
|---|---|---|
| Dictionary (4,900 entries) | LanceDB table `lexico` (fields lema, cat, glosa, text) and `datos/ocr/inga-kichwa/diccionario-inga.md` | `dictionary` / `lema:<lema>` |
| Levinsohn pedagogical grammar | `datos/ocr/inga-kichwa/gramatica-pedagogica-levinsohn.md` | `grammar` / `levinsohn:L<start>-L<end>` (line numbers in that file) |
| Morphosyntactic appendix | `datos/ocr/inga-kichwa/rosetta-morfosintactico.md` | `grammar` / `rosetta:L<start>-L<end>` |
| Parallel corpus, TRAIN ONLY | LanceDB `ejemplos` / `ejemplos_es` (built from `datos/splits/train.jsonl`) | `corpus` / `<libro> <cap>:<vers>` |
| User feedback | SQLite `feedback` table | `feedback` / `feedback:<id>` |

Val/test sentences must never enter the wiki or any seed (evaluation hygiene).

## 2. Wiki data model (SQLite, `datos/wiki/wiki.db`, rebuildable from seeds + feedback)

```
pages(id TEXT PK, kind TEXT, slug TEXT, title TEXT, summary TEXT,
      status TEXT, version INT, updated_at TEXT)
  kind   in lemma | suffix | grammar | convention | case
  id     = "<kind>:<slug>", e.g. "lemma:sinchi", "suffix:ngapa", "grammar:orden-sov"
  status in active | superseded
facts(id TEXT PK, page_id TEXT, section TEXT, text TEXT, status TEXT,
      superseded_by TEXT NULL, created_at TEXT, created_by TEXT)
  id      = "f_<8 hex>"
  section in meaning | morphology | usage | example | note
  status  in active | pending | superseded | rejected
  text    <= 400 chars
fact_sources(fact_id TEXT, source_type TEXT, source_ref TEXT, quote TEXT)
  every fact has >= 1 source (validation rejects otherwise); quote <= 300 chars
page_versions(page_id TEXT, version INT, snapshot_json TEXT, created_at TEXT, reason TEXT)
feedback(id INTEGER PK AUTOINCREMENT, created_at, author, direccion, source_text,
         model_output, correction, comment, translation_id NULL,
         status, triage_json, reviewer NULL, reviewed_at NULL, review_note NULL)
  status in new | auto_applied | pending_review | approved | rejected
translations(id TEXT PK (uuid4 hex), created_at, direccion, source_text,
             normalized_text, output, mode, trace_json)
```

Lemma pages: one page per distinct Inga headword. Dictionary rows whose `lema`
is Spanish (ES-first entries such as `brujo (s): millaipa iacha, samai pagta,
sinchi`) do NOT get their own page: they become `meaning` facts on the Inga
lemma pages they mention (when that lemma exists) and feed the Spanish gloss
lookup. Homographs (two rows with the same lema, e.g. `tukui` adj and v) share
one page with one fact per sense, the `cat` kept in the fact text.

### 2.1 Seed format (`datos/wiki/seed/*.jsonl`, one page per line)

```json
{"id": "suffix:ngapa", "kind": "suffix", "slug": "ngapa", "title": "-ngapa (proposito)",
 "summary": "Sufijo verbal de proposito: 'para + infinitivo'.",
 "aliases": ["-ngapa", "ngapa", "-ngapaj"],
 "facts": [{"section": "morphology", "text": "...",
            "sources": [{"type": "grammar", "ref": "levinsohn:L1201-L1230", "quote": "..."}]}]}
```

`aliases` (optional) are extra lookup keys stored in a `page_aliases(page_id, alias)`
table. Seeds: `lemmas.jsonl` (workstream A, by code, no LLM), `grammar.jsonl` and
`suffixes.jsonl` (workstream B, Gemini pass with citations).
`PYTHONPATH=. uv run python -m src.wiki.bootstrap [--reset]` loads every seed file
idempotently (seed facts get created_by="seed"; feedback facts are preserved unless --reset).

## 3. Python interface (`src/wiki/`, workstream A)

```python
# src/wiki/store.py
class WikiStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB): ...
    def get_page(self, page_id: str, include_inactive: bool = False) -> dict | None
        # {"id","kind","slug","title","summary","status","version","updated_at","aliases":[...],
        #  "facts":[{"id","section","text","status","created_by","created_at",
        #            "sources":[{"type","ref","quote"}]}]}
        # default returns active + pending facts; include_inactive adds superseded/rejected
    def find_pages(self, query: str, kind: str | None = None, limit: int = 20) -> list[dict]
        # page summaries {"id","kind","title","summary","n_facts"}; matches slug/alias prefix
        # first, then title/summary/fact text substring. Parameterized SQL only.
    def find_by_gloss(self, spanish_word: str, limit: int = 10) -> list[dict]
        # lemma pages whose meaning facts mention the Spanish word (accent/case folded)
    def list_pages(self, kind: str | None = None, offset: int = 0, limit: int = 50) -> list[dict]
    def stats(self) -> dict   # pages per kind, facts per status, feedback per status
    def apply_action(self, action: dict, actor: str) -> dict
        # returns {"ok": bool, "error": str|None, "page_id":..., "fact_ids":[...], "version": int}
    def render_markdown(self, page_id: str) -> str   # page as markdown with [n] source refs
    # feedback + translations
    def create_feedback(self, **fields) -> int
    def get_feedback(self, feedback_id: int) -> dict | None
    def list_feedback(self, status: str | None = None, limit: int = 100) -> list[dict]
    def update_feedback(self, feedback_id: int, **fields) -> None
    def save_translation(self, record: dict) -> str      # returns id
    def get_translation(self, translation_id: str) -> dict | None
```

Actions accepted by `apply_action` (dict with "op"); all validated, all bump the
page version and write a `page_versions` snapshot:

- `{"op":"upsert_page","page":{id,kind,slug,title,summary,aliases?},"facts":[{section,text,status?,sources:[...]}]}`
- `{"op":"add_fact","page_id":..., "fact":{section,text,sources}, "status":"active"|"pending"}`
- `{"op":"supersede_fact","fact_id":..., "new_fact":{section,text,sources}, "status":"active"|"pending"}`
  (pending: old fact stays active until `approve_fact` on the new one, which then flips the old to superseded)
- `{"op":"approve_fact","fact_id":...}` / `{"op":"reject_fact","fact_id":..., "reason":...}`

Validation: known kind/section/status, caps (title 120, summary 300, fact 400,
quote 300, <= 40 active facts per page), >= 1 source per fact, source type in the
table of section 1, a `feedback` source ref must exist in the feedback table.
Facts are never deleted, only superseded/rejected.

```python
# src/wiki/navigate.py
def normalize(text: str) -> str
    # maps common Quechua/Kichwa spellings to the corpus orthography (y->i in
    # "yuka"->"iuka", qu/c->k, hu+vowel->w handled conservatively, etc). Derive the
    # rules from the dictionary + train corpus, do not guess; keep it conservative
    # and unit tested. Returns lowercase normalized text, punctuation preserved.
def resolve(sentence: str, direccion: str, store: WikiStore) -> list[dict]
    # one item per token:
    # {"token","normalized","lemma_pages":[page_id...],"suffix_pages":[page_id...],"resolved":bool}
    # inga2es: longest-prefix match of the normalized token against lemma stems
    # (verb citation forms end in -i/-ai: "iukai" -> stem "iuka") then peel the
    # remainder against suffix aliases. es2inga: Spanish token -> find_by_gloss
    # (skip stopwords; try simple Spanish lemmatization: plurals, verb endings).
    # Must work (returning suffix_pages=[]) when no suffix pages are loaded yet.
```

## 4. Agent (`src/agent/`, workstream C)

Tools exposed to Gemini (plain Python callables with Spanish docstrings):
`wiki_leer(page_id)`, `wiki_buscar(consulta, tipo="")`, `buscar_por_glosa(palabra_es)`,
`corpus_buscar(texto, direccion, k=3)` (LanceDB ejemplos / ejemplos_es via
`src.models.gemini_rag.retrieve` or `src.rag.indexes.search`),
`documento_buscar(consulta, documento)` (case/accent-folded grep over the OCR
markdown with 2 lines of context and line numbers; documento in
diccionario|gramatica|rosetta) and `documento_leer(documento, linea, n=40)`.
Tool outputs are capped (~2,500 chars each).

```python
# src/agent/core.py  - all three are generators yielding event dicts (section 5)
def translate(text: str, direccion: str, mode: str = "fast", store=None) -> Iterator[dict]
def ask(translation_id: str, question: str, history: list[dict] | None = None, store=None) -> Iterator[dict]
def triage_feedback(feedback_id: int, store=None) -> Iterator[dict]
```

`translate`: normalize -> resolve -> preload the resolved pages (cap 12 pages /
~9k chars, lemma pages before suffix pages) + top 3 corpus examples -> Gemini.
mode `fast`: one call, no tools. mode `agent`: manual function calling loop, max
6 tool calls, every call/result emitted as an event. Final answer is JSON
(response schema or strict prompt + tolerant parse):
`{"translation","alternatives":[..<=2],"confidence":"low|medium|high","notes","used_pages":[page_id]}`.
Saves a `translations` row whose `trace_json` holds navigation, loaded pages,
examples, tool calls and the final JSON, then emits `result`.

`ask`: loads the trace of `translation_id`, answers "why" questions grounded in
that trace; may use the tools (max 6 calls); must cite page ids / refs and say
what is uncertain. Streams `answer_delta` text chunks.

`triage_feedback`: the agent investigates the correction with the tools and
returns `{"verdict":"supported|needs_review|contradicted","rationale","evidence":[{type,ref,quote}],
"actions":[wiki actions]}`. Code, not the LLM, enforces the rule: a verdict of
`supported` is only honored when `evidence` contains at least one NON-feedback
source (dictionary/grammar/corpus) that the code can re-verify exists (lemma in
`lexico`, line range in the file, verse in train). Then actions are applied with
status `active` and feedback -> `auto_applied`. Otherwise actions are applied
with facts `pending` and feedback -> `pending_review` for a human. Every fact
written from feedback cites `feedback:<id>` (plus the corroborating sources).
Human review (`review_feedback(feedback_id, decision, reviewer, note)` in
`src/agent/review.py`): approve -> `approve_fact` on its pending facts, feedback
`approved`; reject -> `reject_fact`, feedback `rejected`.

Also: `notebooks/scripts/eval_wiki_agent.py`, same 100 val sentences as
`eval_gemini_rag.py` (seed 42), configs F (wiki fast) and G (wiki agent), both
directions, resumable, writes `datos/predicciones_val_wiki.jsonl` and
`datos/metricas_wiki.json`. Do not run the full eval; the integrator will.

## 5. HTTP API (`webapp/backend/main.py`, FastAPI, port 8000, workstream C)

Streams are Server-Sent Events via POST (client uses fetch + ReadableStream).
Each SSE message: `event: <type>` and `data: <json>`.

| Endpoint | Body | Response |
|---|---|---|
| `GET /api/health` | - | `{"ok":true,"model":...,"wiki":stats}` |
| `GET /api/examples` | - | `[{"direccion","text","label"}]` (6-8 sample sentences, none from val/test) |
| `POST /api/translate` | `{"text","direccion":"inga2es"|"es2inga","mode":"fast"|"agent"}` | SSE |
| `POST /api/ask` | `{"translation_id","question","history":[{"role":"user"|"assistant","content"}]}` | SSE |
| `POST /api/feedback` | `{"translation_id"?,"direccion","source_text","model_output","correction","comment","author"}` | SSE |
| `GET /api/feedback?status=` | - | `[feedback rows + "facts":[pending/applied facts with page_id]]` |
| `POST /api/feedback/{id}/review` | `{"decision":"approve"|"reject","reviewer","note"}` | updated feedback row |
| `GET /api/wiki/stats` | - | stats dict |
| `GET /api/wiki/pages?kind=&q=&offset=&limit=` | - | `{"items":[page summaries],"total":int}` |
| `GET /api/wiki/pages/{page_id}` | - | full page dict of `get_page(include_inactive=True)` |

SSE event types and payloads:

- `status` `{"stage":"normalize"|"navigate"|"retrieve"|"think"|"tool"|"write","message":"..."}`
- `navigation` `{"normalized":"...","tokens":[resolve() items]}`
- `pages` `{"pages":[{"id","kind","title","summary"}]}`
- `examples` `{"examples":[{"inga","es","ref"}]}`
- `tool_call` `{"id":n,"name":"wiki_leer","args":{...}}`
- `tool_result` `{"id":n,"name":...,"summary":"short human text","chars":int}`
- `result` `{"translation_id","translation","alternatives":[...],"confidence","notes","used_pages":[...],"mode","elapsed_s"}`
- `answer_delta` `{"text":"chunk"}` and `answer` `{"text":"full answer","cited_pages":[...]}`
- `triage` `{"feedback_id","verdict","status":"auto_applied"|"pending_review","rationale","evidence":[...],"facts":[{"fact_id","page_id","text","status"}]}`
- `error` `{"message":"..."}` then `done` `{}` always last.

CORS open for `http://localhost:5173`. If `webapp/frontend/dist` exists the backend
serves it at `/` (SPA fallback). Run: `PYTHONPATH=. uv run uvicorn webapp.backend.main:app --port 8000`.

## 6. Frontend (`webapp/frontend/`, Vite + React + TypeScript + Tailwind, workstream D)

UI in Spanish. Dev server 5173 with proxy `/api` -> `http://localhost:8000`.
`VITE_MOCK=1` serves a built-in mock of section 5 (same event shapes) so the UI
can be built before the backend exists. Views:

1. **Traducir** (home): hero with image, two panels + swap direction, mode toggle
   (Rapido / Agente), live "pensamiento" timeline fed by status/navigation/pages/
   tool events, result with confidence + alternatives + notes, token chips that
   show which wiki pages each word resolved to (click opens the page drawer),
   "Pregunta por que" chat bound to the translation, "Sugerir correccion" form
   whose triage streams and ends with a verdict card. Example sentences, copy,
   local history.
2. **Wiki**: search + kind filter, page view with facts grouped by section,
   status badges (activo / pendiente / reemplazado / rechazado), sources per fact.
3. **Revision**: queue of `pending_review` feedback with the agent rationale and
   evidence, approve / reject with reviewer name and note; tab with history.
4. **Acerca**: what the project is, the sources, the limits (biblical domain).

Images live in `webapp/frontend/public/img/` (workstream E) with these exact
names: `hero.jpg`, `montana.jpg`, `selva.jpg`, `paramo.jpg`, `patron-chumbe.png`.
The UI must degrade gracefully (gradient) when an image is missing. No images of
people or ceremonies anywhere in the app.

## 7. Ownership

| Workstream | Owns |
|---|---|
| A wiki core | `src/wiki/`, `scripts/build_wiki_lemmas.py`, `datos/wiki/seed/lemmas.jsonl`, `tests/wiki/` |
| B grammar seeds | `scripts/build_wiki_grammar.py`, `datos/wiki/seed/grammar.jsonl`, `datos/wiki/seed/suffixes.jsonl` |
| C agent + API | `src/agent/`, `webapp/backend/`, `tests/agent/`, `notebooks/scripts/eval_wiki_agent.py` |
| D frontend | `webapp/frontend/` except `public/img/` |
| E images | `webapp/frontend/public/img/`, `scripts/generate_images.py` |

## 8. AMENDMENT (supersedes the tool list of section 4): wiki as a markdown filesystem + CLI writes

Mirrors the veleiro preference wiki: rows are the source of truth, the agent READS
markdown files and WRITES only through a typed, self-describing CLI tool.

### 8.1 Materialized markdown tree (workstream A, `src/wiki/render.py`)

`datos/wiki/pages/` is a rendered view of the SQLite rows, never edited by hand:

```
datos/wiki/pages/
  index.md                 # how the tree is organized + counts; "for CHOOSING a page, never for answering"
  log.md                   # append-only: one line per applied action (time, actor, op, page, fact ids)
  lemma/index.md           # one line per page: `- [sinchi](sinchi.md) - summary` (may be split a-z if huge)
  lemma/<slug>.md
  suffix/index.md  suffix/<slug>.md
  grammar/index.md grammar/<slug>.md
  convention/...   case/...
```

Page file = YAML-ish front matter (id, kind, title, status, version, aliases,
updated_at) then summary, then facts grouped by section as bullets
`- [f_ab12cd34] text (estado: pendiente)` each followed by indented source lines
`  - fuente: dictionary lema:sinchi "quote"`. Superseded/rejected facts go under
a final `## Historial` section. File names: slug lowercased, spaces -> `-`,
ASCII-folded, collisions get a numeric suffix; the store keeps `path_for(page_id)`.
`render_all()` rebuilds the tree; `apply_action` re-renders the touched page, the
kind index when title/summary changed, and appends to `log.md`. Bootstrap ends
with `render_all()`. New WikiStore methods: `path_for(page_id) -> str` (relative
to the pages root) and `page_id_for_path(path) -> str | None`.

### 8.2 Agent tools (workstream C) - replaces `wiki_leer`, `wiki_buscar`, `documento_*`

A read-only virtual filesystem with two mounts, path traversal rejected
(no absolute paths, no `..`, no `~`, no symlinks):

- `wiki/`    -> `datos/wiki/pages/`
- `fuentes/` -> the OCR sources: `fuentes/diccionario.md`, `fuentes/gramatica.md`,
  `fuentes/rosetta.md` (map to the files of section 1)

Tools: `fs_ls(ruta)`, `fs_leer(ruta, linea=1, n=120)` (line numbered output),
`fs_grep(patron, ruta="wiki/", max=30)` (case/accent folded, returns path:line:text).
Kept as-is: `corpus_buscar(texto, direccion, k=3)` and `buscar_por_glosa(palabra_es)`
(vector / gloss lookups that are not files). There is NO file write tool.

Writes: a single tool `inga_cli(cmd: str) -> str` with the veleiro grammar
(hand-rolled parser over `shlex.split`; accept both `--key value` and `--key=value`):

```
list-resources
help [<Resource>]
resource <Resource> list-actions
resource <Resource> get-schema --action <action-name>
resource <Resource> execute-action <action-name> --input '<json>'
```

Resources: `Wiki` (actions `upsert-page`, `add-fact`, `supersede-fact`, `no-change`
with a required `reason`; read actions `get-page`, `find-pages`) and `Feedback`
(read actions `get`, `list`). Inputs validated with pydantic models,
`extra="forbid"`; `get-schema` returns the JSON schema; errors come back as an
actionable message the model can retry on (max 2 retries per command). The tool
description embeds the resource list so the model can bootstrap without
`list-resources`. `inga_cli` is only offered in `triage_feedback` (and any future
curation run), never in `translate` or `ask`.

Status is decided by CODE at the write path, not by the model: a fact written
through `inga_cli` always cites `feedback:<id>` of the run; it becomes `active`
only if it also carries at least one non-feedback source that the code verifies
(lemma exists, quoted lines found in the cited range, verse in train); otherwise
it is forced to `pending`. The triage verdict and the feedback status are then
derived from what was written: all facts active -> `auto_applied`; any pending ->
`pending_review`; only `no-change` -> `rejected` by the agent with its reason
(still visible in Revision so a human can overrule). Human approve/reject is
unchanged. SSE events are unchanged: tool names in `tool_call` are just the new ones.
