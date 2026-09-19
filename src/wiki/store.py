"""Almacen SQLite de la wiki Inga (paginas, hechos citados, versiones, feedback).

Contrato: docs/superpowers/specs/2026-09-19-inga-wiki-agent-design.md, secciones 2 y 3.

Decisiones:
- stdlib sqlite3, SQL siempre parametrizado, modo WAL.
- Una conexion por llamada (seguro desde los hilos de FastAPI) y un candado de
  escritura por archivo para serializar las transacciones de este proceso.
- Los hechos nunca se borran: solo pasan a superseded o rejected.
- Cada accion que cambia una pagina sube su version y guarda un snapshot JSON.
- Tras cada accion aplicada se regenera el archivo markdown de la pagina en
  <carpeta de la db>/pages/ (seccion 8.1 del contrato, ver render.py) y se agrega
  una linea a log.md. Las filas siguen siendo la fuente de verdad.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src.wiki import render as _render
from src.wiki.validation import (
    DIRECCIONES,
    FEEDBACK_STATUSES,
    KINDS,
    MAX_ACTIVE_FACTS,
    SECTIONS,
    ValidationError,
    feedback_id_from_ref,
    fold,
    validate_fact,
    validate_page,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = Path(os.environ.get("INGA_WIKI_DB") or REPO_ROOT / "datos" / "wiki" / "wiki.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pages(
    id TEXT PRIMARY KEY, kind TEXT NOT NULL, slug TEXT NOT NULL, title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
    search_fold TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS ix_pages_kind ON pages(kind, slug);
CREATE TABLE IF NOT EXISTS page_aliases(
    page_id TEXT NOT NULL, alias TEXT NOT NULL, alias_fold TEXT NOT NULL,
    PRIMARY KEY(page_id, alias));
CREATE INDEX IF NOT EXISTS ix_alias_fold ON page_aliases(alias_fold);
CREATE TABLE IF NOT EXISTS page_paths(
    page_id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS facts(
    id TEXT PRIMARY KEY, page_id TEXT NOT NULL, section TEXT NOT NULL, text TEXT NOT NULL,
    status TEXT NOT NULL, superseded_by TEXT NULL, created_at TEXT NOT NULL,
    created_by TEXT NOT NULL, text_fold TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS ix_facts_page ON facts(page_id, status);
CREATE TABLE IF NOT EXISTS fact_sources(
    fact_id TEXT NOT NULL, source_type TEXT NOT NULL, source_ref TEXT NOT NULL,
    quote TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS ix_sources_fact ON fact_sources(fact_id);
CREATE INDEX IF NOT EXISTS ix_sources_ref ON fact_sources(source_type, source_ref);
CREATE TABLE IF NOT EXISTS gloss_index(
    token TEXT NOT NULL, page_id TEXT NOT NULL, fact_id TEXT NOT NULL, rank INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS ix_gloss_token ON gloss_index(token);
CREATE TABLE IF NOT EXISTS page_versions(
    page_id TEXT NOT NULL, version INTEGER NOT NULL, snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS ix_versions_page ON page_versions(page_id, version);
CREATE TABLE IF NOT EXISTS feedback(
    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, author TEXT,
    direccion TEXT, source_text TEXT, model_output TEXT, correction TEXT, comment TEXT,
    translation_id TEXT NULL, status TEXT NOT NULL DEFAULT 'new', triage_json TEXT,
    reviewer TEXT NULL, reviewed_at TEXT NULL, review_note TEXT NULL);
CREATE INDEX IF NOT EXISTS ix_feedback_status ON feedback(status);
CREATE TABLE IF NOT EXISTS translations(
    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, direccion TEXT, source_text TEXT,
    normalized_text TEXT, output TEXT, mode TEXT, trace_json TEXT);
"""

_FEEDBACK_COLS = (
    "created_at", "author", "direccion", "source_text", "model_output", "correction",
    "comment", "translation_id", "status", "triage_json", "reviewer", "reviewed_at",
    "review_note",
)
_SECTION_ORDER = {s: i for i, s in enumerate(SECTIONS)}
_SECTION_TITULO = {
    "meaning": "Significado", "morphology": "Morfologia", "usage": "Uso",
    "example": "Ejemplos", "note": "Notas",
}
_STATUS_ETIQUETA = {"pending": "pendiente de revision", "superseded": "reemplazado",
                    "rejected": "rechazado"}

_locks: dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()

_RE_TOKEN = re.compile(r"[a-zñü]+")
_RE_PAREN = re.compile(r"\([^()]*\)")
_RE_SENSE = re.compile(r"\(\d+\)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_RE_ENTRADA = re.compile(r"^(.{1,80}?) \(([^()]{1,40})\):\s*(.*)$", re.S)


def gloss_tokens(text: str, page_title: str | None = None) -> dict[str, int]:
    """Tokens plegados de un hecho de significado con su rango de coincidencia.

    3 = el token es un segmento completo de la glosa ("casa" en "casa; hogar"),
    2 = primera palabra de un segmento ("casa de paja"), 1 = otra posicion,
    0 = solo aparece dentro de un parentesis (notas dialectales, remisiones).

    Si el hecho tiene forma de entrada "<cabeza> (<cat>): <resto>" solo se indexa el
    lado en espanol: el resto cuando la cabeza es el lema de la pagina, o la cabeza
    cuando es una entrada espanol-inga. Asi "ama" (espanol) no cae en el lema inga ama.
    """
    m = _RE_ENTRADA.match(text or "")
    if m and page_title is not None:
        cabeza, _cat, resto = m.groups()
        text = resto if fold(cabeza) == fold(page_title) else cabeza
    plano = fold(text)
    plano = re.sub(r"\[[^\]]*\]", " ", plano)  # marcas editoriales, p. ej. [entrada espanol-inga ...]
    plano = _RE_SENSE.sub(" ; ", plano)
    dentro = " ".join(_RE_PAREN.findall(plano))
    fuera = plano
    # quita parentesis anidados de forma iterativa
    for _ in range(3):
        fuera = _RE_PAREN.sub(" ", fuera)
    ranks: dict[str, int] = {}
    for seg in re.split(r"[;,:!?¡¿]|->|\.\s", fuera):
        toks = _RE_TOKEN.findall(seg)
        for i, t in enumerate(toks):
            r = 3 if len(toks) == 1 else (2 if i == 0 else 1)
            if r > ranks.get(t, -1):
                ranks[t] = r
    for t in _RE_TOKEN.findall(dentro):
        ranks.setdefault(t, 0)
    return ranks


class WikiStore:
    """Acceso a la wiki. Todas las llamadas abren y cierran su propia conexion."""

    def __init__(self, db_path: Path | str = DEFAULT_DB, pages_root: Path | str | None = None,
                 auto_render: bool = True):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.pages_root = Path(pages_root) if pages_root else self.db_path.parent / "pages"
        self.auto_render = auto_render
        clave = str(self.db_path.resolve())
        with _locks_guard:
            self._lock = _locks.setdefault(clave, threading.RLock())
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(_SCHEMA)
            finally:
                conn.close()
            self._backfill_paths()

    # ------------------------------------------------------------------ conexiones
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @contextmanager
    def _read(self):
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _write(self):
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------ rutas markdown
    def _assign_path(self, conn, page_id: str, kind: str, slug: str) -> str:
        row = conn.execute("SELECT path FROM page_paths WHERE page_id = ?", (page_id,)).fetchone()
        if row is not None:
            return row["path"]
        base = f"{kind}/{_render.ascii_slug(slug)}"
        tomados = {r["path"] for r in conn.execute(
            "SELECT path FROM page_paths WHERE path LIKE ? ESCAPE '\\'",
            (_like_escape(base) + "%",))}
        path = _render.relative_path(kind, slug, tomados)
        conn.execute("INSERT INTO page_paths(page_id, path) VALUES (?,?)", (page_id, path))
        return path

    def _backfill_paths(self) -> None:
        """Da ruta a las paginas de una db creada antes de existir page_paths."""
        with self._read() as conn:
            faltan = conn.execute(
                "SELECT COUNT(*) FROM pages p LEFT JOIN page_paths pp ON pp.page_id = p.id "
                "WHERE pp.page_id IS NULL").fetchone()[0]
        if not faltan:
            return
        with self._write() as conn:
            for r in conn.execute(
                    "SELECT p.id, p.kind, p.slug FROM pages p LEFT JOIN page_paths pp "
                    "ON pp.page_id = p.id WHERE pp.page_id IS NULL ORDER BY p.kind, p.slug").fetchall():
                self._assign_path(conn, r["id"], r["kind"], r["slug"])

    def path_for(self, page_id: str) -> str | None:
        """Ruta del archivo markdown relativa a la raiz de paginas, p. ej. 'lemma/sinchi.md'."""
        with self._read() as conn:
            row = conn.execute("SELECT path FROM page_paths WHERE page_id = ?", (page_id,)).fetchone()
            return row["path"] if row else None

    def page_id_for_path(self, path: str) -> str | None:
        """Inverso de path_for. Acepta 'lemma/x.md', 'wiki/lemma/x.md' o una ruta bajo pages_root."""
        if not isinstance(path, str) or not path.strip():
            return None
        rel = path.strip().replace("\\", "/")
        raiz = str(self.pages_root.resolve()).replace("\\", "/")
        raiz_cruda = str(self.pages_root).replace("\\", "/")
        for pref in (raiz + "/", raiz_cruda + "/"):
            if rel.startswith(pref):
                rel = rel[len(pref):]
        rel = rel.lstrip("./")
        partes = [x for x in rel.split("/") if x]
        if ".." in partes:
            return None
        # quita montajes o carpetas previas: wiki/, datos/wiki/pages/
        while partes and partes[0] not in KINDS:
            partes.pop(0)
        if len(partes) != 2:
            return None
        with self._read() as conn:
            row = conn.execute(
                "SELECT page_id FROM page_paths WHERE path = ?", ("/".join(partes),)).fetchone()
            return row["page_id"] if row else None

    def page_rows(self, kind: str, include_inactive: bool = False) -> list[dict]:
        """Filas {id,title,summary,path} de un tipo, ordenadas por slug (para los indices)."""
        with self._read() as conn:
            sql = ("SELECT p.id, p.title, p.summary, pp.path FROM pages p JOIN page_paths pp "
                   "ON pp.page_id = p.id WHERE p.kind = ?")
            if not include_inactive:
                sql += " AND p.status = 'active'"
            return [dict(r) for r in conn.execute(sql + " ORDER BY p.slug", (kind,))]

    def render_all(self) -> dict:
        """Reconstruye el arbol markdown completo desde las filas."""
        with self._lock:
            return _render.render_all(self)

    def _after_apply(self, action: dict, actor: str, res: dict, meta: dict) -> None:
        """Vista markdown + bitacora tras una accion ya confirmada en la db."""
        if not self.auto_render or not meta.get("changed"):
            return
        try:
            with self._lock:
                _render.write_page(self, res["page_id"])
                if meta.get("index_dirty"):
                    _render.write_kind_index(self, res["page_id"].split(":", 1)[0])
                if meta.get("created"):
                    _render.write_root_index(self)
                _render.append_log(self, actor, action.get("op"), res["page_id"],
                                   res.get("fact_ids") or [], str(action.get("reason") or ""))
        except OSError as exc:
            res["render_error"] = str(exc)

    # ------------------------------------------------------------------ lectura
    def _facts_for(self, conn, page_id: str, include_inactive: bool) -> list[dict]:
        if include_inactive:
            rows = conn.execute(
                "SELECT rowid AS rid, * FROM facts WHERE page_id = ?", (page_id,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT rowid AS rid, * FROM facts WHERE page_id = ? "
                "AND status IN ('active','pending')", (page_id,)).fetchall()
        rows = sorted(rows, key=lambda r: (_SECTION_ORDER.get(r["section"], 99), r["rid"]))
        facts = []
        for r in rows:
            srcs = conn.execute(
                "SELECT source_type, source_ref, quote FROM fact_sources "
                "WHERE fact_id = ? ORDER BY rowid", (r["id"],)).fetchall()
            facts.append({
                "id": r["id"], "section": r["section"], "text": r["text"],
                "status": r["status"], "created_by": r["created_by"],
                "created_at": r["created_at"], "superseded_by": r["superseded_by"],
                "sources": [{"type": s["source_type"], "ref": s["source_ref"],
                             "quote": s["quote"]} for s in srcs],
            })
        return facts

    def _get_page(self, conn, page_id: str, include_inactive: bool = False) -> dict | None:
        p = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        if p is None:
            return None
        aliases = [r["alias"] for r in conn.execute(
            "SELECT alias FROM page_aliases WHERE page_id = ? ORDER BY rowid", (page_id,))]
        return {
            "id": p["id"], "kind": p["kind"], "slug": p["slug"], "title": p["title"],
            "summary": p["summary"], "status": p["status"], "version": p["version"],
            "updated_at": p["updated_at"], "aliases": aliases,
            "facts": self._facts_for(conn, page_id, include_inactive),
        }

    def get_page(self, page_id: str, include_inactive: bool = False) -> dict | None:
        """Pagina completa con hechos y fuentes; None si no existe."""
        with self._read() as conn:
            return self._get_page(conn, page_id, include_inactive)

    def _summaries(self, conn, ids: list[str]) -> list[dict]:
        out = []
        for pid in ids:
            p = conn.execute(
                "SELECT id, kind, title, summary FROM pages WHERE id = ?", (pid,)).fetchone()
            if p is None:
                continue
            n = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE page_id = ? AND status IN ('active','pending')",
                (pid,)).fetchone()[0]
            out.append({"id": p["id"], "kind": p["kind"], "title": p["title"],
                        "summary": p["summary"], "n_facts": n})
        return out

    def find_pages(self, query: str, kind: str | None = None, limit: int = 20) -> list[dict]:
        """Busca paginas: alias/slug exacto, luego prefijo, luego subcadena en texto."""
        q = fold((query or "").strip())
        if not q:
            return []
        q_slug = q.lstrip("-")
        limit = max(1, int(limit))
        kind_sql = " AND p.kind = ?" if kind else ""
        kind_arg = (kind,) if kind else ()
        ids: list[str] = []

        def _add(rows):
            for r in rows:
                if r[0] not in ids:
                    ids.append(r[0])

        with self._read() as conn:
            base = ("SELECT DISTINCT p.id FROM pages p JOIN page_aliases a ON a.page_id = p.id "
                    "WHERE p.status = 'active'" + kind_sql)
            _add(conn.execute(
                base + " AND (a.alias_fold = ? OR a.alias_fold = ?) ORDER BY length(p.slug), p.slug "
                "LIMIT ?", kind_arg + (q, q_slug, limit)))
            if len(ids) < limit:
                _add(conn.execute(
                    base + " AND (a.alias_fold LIKE ? ESCAPE '\\' OR a.alias_fold LIKE ? ESCAPE '\\') "
                    "ORDER BY length(p.slug), p.slug LIMIT ?",
                    kind_arg + (_like_escape(q) + "%", _like_escape(q_slug) + "%", limit)))
            if len(ids) < limit:
                _add(conn.execute(
                    "SELECT p.id FROM pages p WHERE p.status = 'active'" + kind_sql +
                    " AND p.search_fold LIKE ? ESCAPE '\\' ORDER BY length(p.slug), p.slug LIMIT ?",
                    kind_arg + ("%" + _like_escape(q) + "%", limit)))
            if len(ids) < limit:
                _add(conn.execute(
                    "SELECT DISTINCT p.id FROM pages p JOIN facts f ON f.page_id = p.id "
                    "WHERE p.status = 'active'" + kind_sql +
                    " AND f.status IN ('active','pending') AND f.text_fold LIKE ? ESCAPE '\\' "
                    "ORDER BY length(p.slug), p.slug LIMIT ?",
                    kind_arg + ("%" + _like_escape(q) + "%", limit)))
            return self._summaries(conn, ids[:limit])

    def find_by_gloss(self, spanish_word: str, limit: int = 10) -> list[dict]:
        """Paginas de lema cuyos hechos de significado mencionan la palabra en espanol.

        Coincidencia por token completo, plegado (sin tildes ni mayusculas).
        Orden: mejor rango de coincidencia, lemas de una palabra antes que frases,
        mas hechos coincidentes, slug. Cada item trae ademas "rank" y "match".
        """
        toks = _RE_TOKEN.findall(fold(spanish_word or ""))
        if not toks:
            return []
        limit = max(1, int(limit))
        with self._read() as conn:
            if len(toks) == 1:
                rows = conn.execute(
                    "SELECT g.page_id, g.rank, f.text, p.slug FROM gloss_index g "
                    "JOIN facts f ON f.id = g.fact_id JOIN pages p ON p.id = g.page_id "
                    "WHERE g.token = ? AND f.status = 'active' AND p.status = 'active'",
                    (toks[0],)).fetchall()
                cands = [(r["page_id"], r["rank"], r["text"], r["slug"]) for r in rows]
            else:
                # frase: subcadena plegada en el texto del hecho
                frase = " ".join(toks)
                rows = conn.execute(
                    "SELECT f.page_id, f.text, f.text_fold, p.slug FROM facts f "
                    "JOIN pages p ON p.id = f.page_id WHERE p.kind = 'lemma' "
                    "AND p.status = 'active' AND f.section = 'meaning' AND f.status = 'active' "
                    "AND f.text_fold LIKE ? ESCAPE '\\'",
                    ("%" + _like_escape(frase) + "%",)).fetchall()
                cands = []
                for r in rows:
                    segs = [" ".join(_RE_TOKEN.findall(s))
                            for s in re.split(r"[;,:]|->", _RE_PAREN.sub(" ", r["text_fold"]))]
                    rank = 3 if frase in segs else (2 if any(s.startswith(frase) for s in segs) else 1)
                    cands.append((r["page_id"], rank, r["text"], r["slug"]))
            mejor: dict[str, dict] = {}
            for pid, rank, text, slug in cands:
                m = mejor.get(pid)
                if m is None:
                    mejor[pid] = {"rank": rank, "match": text, "n": 1, "slug": slug}
                else:
                    m["n"] += 1
                    if rank > m["rank"]:
                        m["rank"], m["match"] = rank, text
            orden = sorted(mejor.items(), key=lambda kv: (
                -kv[1]["rank"], kv[1]["slug"].count("-"), -kv[1]["n"], kv[1]["slug"]))[:limit]
            out = []
            for pid, m in orden:
                s = self._summaries(conn, [pid])
                if s:
                    s[0]["rank"] = m["rank"]
                    s[0]["match"] = m["match"]
                    out.append(s[0])
            return out

    def list_pages(self, kind: str | None = None, offset: int = 0, limit: int = 50) -> list[dict]:
        """Resumenes de paginas activas ordenadas por tipo y slug."""
        with self._read() as conn:
            if kind:
                rows = conn.execute(
                    "SELECT id FROM pages WHERE status = 'active' AND kind = ? "
                    "ORDER BY slug LIMIT ? OFFSET ?", (kind, int(limit), int(offset))).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id FROM pages WHERE status = 'active' "
                    "ORDER BY kind, slug LIMIT ? OFFSET ?", (int(limit), int(offset))).fetchall()
            return self._summaries(conn, [r["id"] for r in rows])

    def count_pages(self, kind: str | None = None) -> int:
        """Total de paginas activas (para paginar list_pages)."""
        with self._read() as conn:
            if kind:
                return conn.execute(
                    "SELECT COUNT(*) FROM pages WHERE status = 'active' AND kind = ?",
                    (kind,)).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM pages WHERE status = 'active'").fetchone()[0]

    def stats(self) -> dict:
        """Paginas por tipo, hechos por estado, feedback por estado, traducciones."""
        with self._read() as conn:
            pages = {k: 0 for k in KINDS}
            for r in conn.execute(
                    "SELECT kind, COUNT(*) AS n FROM pages WHERE status = 'active' GROUP BY kind"):
                pages[r["kind"]] = r["n"]
            facts = {"active": 0, "pending": 0, "superseded": 0, "rejected": 0}
            for r in conn.execute("SELECT status, COUNT(*) AS n FROM facts GROUP BY status"):
                facts[r["status"]] = r["n"]
            fb = {s: 0 for s in FEEDBACK_STATUSES}
            for r in conn.execute("SELECT status, COUNT(*) AS n FROM feedback GROUP BY status"):
                fb[r["status"]] = r["n"]
            n_tr = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
            n_al = conn.execute("SELECT COUNT(*) FROM page_aliases").fetchone()[0]
        return {
            "pages": {**pages, "total": sum(pages.values())},
            "facts": {**facts, "total": sum(facts.values())},
            "feedback": {**fb, "total": sum(fb.values())},
            "aliases": n_al,
            "translations": n_tr,
        }

    def get_fact(self, fact_id: str) -> dict | None:
        """Un hecho con su page_id y fuentes; None si no existe."""
        with self._read() as conn:
            r = conn.execute("SELECT page_id FROM facts WHERE id = ?", (fact_id,)).fetchone()
            if r is None:
                return None
            for f in self._facts_for(conn, r["page_id"], True):
                if f["id"] == fact_id:
                    return {**f, "page_id": r["page_id"]}
        return None

    def facts_by_source(self, source_type: str, source_ref: str) -> list[dict]:
        """Hechos (cualquier estado) que citan una fuente, p. ej. ('feedback','feedback:3')."""
        with self._read() as conn:
            ids = [r["fact_id"] for r in conn.execute(
                "SELECT DISTINCT fact_id FROM fact_sources WHERE source_type = ? AND source_ref = ?",
                (source_type, source_ref))]
        out = []
        for fid in ids:
            f = self.get_fact(fid)
            if f:
                out.append(f)
        return out

    def lemma_keys(self) -> list[tuple[str, str]]:
        """Pares (alias plegado, page_id) de todas las paginas de lema activas."""
        with self._read() as conn:
            return [(r["alias_fold"], r["page_id"]) for r in conn.execute(
                "SELECT a.alias_fold, a.page_id FROM page_aliases a JOIN pages p "
                "ON p.id = a.page_id WHERE p.kind = 'lemma' AND p.status = 'active'")]

    def lemma_index(self) -> list[tuple[str, str, bool]]:
        """Trios (alias plegado, page_id, es_verbo) de las paginas de lema activas.

        es_verbo: la pagina tiene un hecho de significado activo cuyo texto empieza
        con "<lema> (v." o "<lema> (s, v." (categorias v.t., v.i., v.r., v.impers.).
        """
        with self._read() as conn:
            verbos = {r["page_id"] for r in conn.execute(
                "SELECT DISTINCT f.page_id FROM facts f JOIN pages p ON p.id = f.page_id "
                "WHERE p.kind = 'lemma' AND f.section = 'meaning' AND f.status = 'active' "
                "AND (lower(f.text) LIKE lower(p.title) || ' (v.%' "
                "OR lower(f.text) LIKE lower(p.title) || ' (%, v.%')")}
            return [(r["alias_fold"], r["page_id"], r["page_id"] in verbos) for r in conn.execute(
                "SELECT a.alias_fold, a.page_id FROM page_aliases a JOIN pages p "
                "ON p.id = a.page_id WHERE p.kind = 'lemma' AND p.status = 'active'")]

    def suffix_keys(self) -> list[tuple[str, str]]:
        """Pares (alias plegado sin guion, page_id) de las paginas de sufijo activas."""
        with self._read() as conn:
            return [(r["alias_fold"].strip("-"), r["page_id"]) for r in conn.execute(
                "SELECT a.alias_fold, a.page_id FROM page_aliases a JOIN pages p "
                "ON p.id = a.page_id WHERE p.kind = 'suffix' AND p.status = 'active'")]

    def reindex_gloss(self) -> int:
        """Reconstruye gloss_index desde los hechos de significado de paginas de lema."""
        with self._write() as conn:
            conn.execute("DELETE FROM gloss_index")
            filas = conn.execute(
                "SELECT f.id, f.page_id, f.text, p.title FROM facts f JOIN pages p "
                "ON p.id = f.page_id WHERE p.kind = 'lemma' AND f.section = 'meaning'").fetchall()
            datos = [(t, r["page_id"], r["id"], rank) for r in filas
                     for t, rank in gloss_tokens(r["text"], r["title"]).items()]
            conn.executemany(
                "INSERT INTO gloss_index(token, page_id, fact_id, rank) VALUES (?,?,?,?)", datos)
            return len(datos)

    def data_version(self) -> int:
        """Contador barato para invalidar caches: suma de versiones de pagina."""
        with self._read() as conn:
            r = conn.execute("SELECT COALESCE(SUM(version),0) + COUNT(*) FROM pages").fetchone()
            return int(r[0])

    # ------------------------------------------------------------------ escritura
    def _new_fact_id(self, conn) -> str:
        while True:
            fid = "f_" + uuid.uuid4().hex[:8]
            if conn.execute("SELECT 1 FROM facts WHERE id = ?", (fid,)).fetchone() is None:
                return fid

    def _check_feedback_refs(self, conn, fact: dict) -> None:
        for s in fact["sources"]:
            if s["type"] == "feedback":
                fb_id = feedback_id_from_ref(s["ref"])
                if conn.execute("SELECT 1 FROM feedback WHERE id = ?", (fb_id,)).fetchone() is None:
                    raise ValidationError(f"la fuente {s['ref']} no existe en la tabla feedback")

    def _count_active(self, conn, page_id: str) -> int:
        return conn.execute(
            "SELECT COUNT(*) FROM facts WHERE page_id = ? AND status = 'active'",
            (page_id,)).fetchone()[0]

    def _insert_fact(self, conn, page: sqlite3.Row | dict, fact: dict, actor: str) -> str:
        self._check_feedback_refs(conn, fact)
        if fact["status"] == "active" and self._count_active(conn, page["id"]) >= MAX_ACTIVE_FACTS:
            raise ValidationError(
                f"la pagina {page['id']} ya tiene {MAX_ACTIVE_FACTS} hechos activos")
        fid = self._new_fact_id(conn)
        conn.execute(
            "INSERT INTO facts(id, page_id, section, text, status, superseded_by, created_at, "
            "created_by, text_fold) VALUES (?,?,?,?,?,NULL,?,?,?)",
            (fid, page["id"], fact["section"], fact["text"], fact["status"], _now(), actor,
             fold(fact["text"])))
        conn.executemany(
            "INSERT INTO fact_sources(fact_id, source_type, source_ref, quote) VALUES (?,?,?,?)",
            [(fid, s["type"], s["ref"], s["quote"]) for s in fact["sources"]])
        if page["kind"] == "lemma" and fact["section"] == "meaning":
            conn.executemany(
                "INSERT INTO gloss_index(token, page_id, fact_id, rank) VALUES (?,?,?,?)",
                [(t, page["id"], fid, r)
                 for t, r in gloss_tokens(fact["text"], page["title"]).items()])
        return fid

    def _bump(self, conn, page_id: str, reason: str) -> int:
        conn.execute("UPDATE pages SET version = version + 1, updated_at = ? WHERE id = ?",
                     (_now(), page_id))
        snap = self._get_page(conn, page_id, include_inactive=True)
        conn.execute(
            "INSERT INTO page_versions(page_id, version, snapshot_json, created_at, reason) "
            "VALUES (?,?,?,?,?)",
            (page_id, snap["version"], json.dumps(snap, ensure_ascii=False), _now(), reason[:500]))
        return snap["version"]

    def _set_aliases(self, conn, page: dict) -> bool:
        """Alias = los pedidos + slug + titulo. Devuelve True si cambio algo."""
        pedidos = list(page["aliases"])
        for extra in (page["slug"], page["slug"].replace("-", " ")):
            if extra not in pedidos:
                pedidos.append(extra)
        previos = [r["alias"] for r in conn.execute(
            "SELECT alias FROM page_aliases WHERE page_id = ? ORDER BY rowid", (page["id"],))]
        nuevos = [a for a in pedidos if a not in previos]
        conn.executemany(
            "INSERT OR IGNORE INTO page_aliases(page_id, alias, alias_fold) VALUES (?,?,?)",
            [(page["id"], a, fold(a)) for a in nuevos])
        return bool(nuevos)

    def retire_page(self, page_id: str, actor: str, reason: str = "") -> dict:
        """Marca una pagina como superseded (no se borra nada; un upsert posterior la reactiva).

        La usa el bootstrap para paginas de semilla que ya no estan en ninguna semilla,
        p. ej. un lema cuyo id cambio al corregir una errata del OCR.
        """
        res = {"ok": False, "error": None, "page_id": page_id, "fact_ids": [], "version": None}
        try:
            with self._write() as conn:
                row = self._page_row(conn, page_id)
                if row["status"] != "superseded":
                    conn.execute("UPDATE pages SET status = 'superseded' WHERE id = ?", (page_id,))
                    res["version"] = self._bump(conn, page_id, reason or f"retire_page por {actor}")
                else:
                    res["version"] = row["version"]
            res["ok"] = True
        except ValidationError as exc:
            res["error"] = str(exc)
            return res
        if self.auto_render and res["ok"]:
            try:
                with self._lock:
                    rel = self.path_for(page_id)
                    if rel:
                        (self.pages_root / rel).unlink(missing_ok=True)
                    _render.write_kind_index(self, page_id.split(":", 1)[0])
                    _render.append_log(self, actor, "retire_page", page_id, [], reason)
            except OSError as exc:
                res["render_error"] = str(exc)
        return res

    def seed_only_pages(self) -> list[tuple[str, str]]:
        """(page_id, kind) de paginas activas cuyos hechos son todos de semilla."""
        with self._read() as conn:
            return [(r["id"], r["kind"]) for r in conn.execute(
                "SELECT p.id, p.kind FROM pages p WHERE p.status = 'active' AND NOT EXISTS ("
                "SELECT 1 FROM facts f WHERE f.page_id = p.id AND f.created_by != 'seed')")]

    def _op_upsert_page(self, conn, action: dict, actor: str) -> dict:
        page = validate_page(action.get("page") or {})
        facts = [validate_fact(f) for f in (action.get("facts") or [])]
        row = conn.execute("SELECT * FROM pages WHERE id = ?", (page["id"],)).fetchone()
        changed = header_changed = created = False
        search_fold = fold(page["title"] + " " + page["summary"])
        if row is None:
            conn.execute(
                "INSERT INTO pages(id, kind, slug, title, summary, status, version, updated_at, "
                "search_fold) VALUES (?,?,?,?,?,'active',0,?,?)",
                (page["id"], page["kind"], page["slug"], page["title"], page["summary"], _now(),
                 search_fold))
            self._assign_path(conn, page["id"], page["kind"], page["slug"])
            changed = True
            header_changed = created = True
        elif (row["title"], row["summary"], row["status"]) != (page["title"], page["summary"], "active"):
            conn.execute(
                "UPDATE pages SET title = ?, summary = ?, status = 'active', search_fold = ? "
                "WHERE id = ?", (page["title"], page["summary"], search_fold, page["id"]))
            changed = header_changed = True
        if self._set_aliases(conn, page):
            changed = True
        # idempotencia: un hecho con la misma seccion y texto (en cualquier estado) no se repite;
        # asi un hecho de semilla ya corregido por feedback no revive al recargar
        existentes = {(r["section"], r["text"]) for r in conn.execute(
            "SELECT section, text FROM facts WHERE page_id = ?", (page["id"],))}
        fact_ids = []
        for f in facts:
            if (f["section"], f["text"]) in existentes:
                continue
            fact_ids.append(self._insert_fact(conn, page, f, actor))
            existentes.add((f["section"], f["text"]))
            changed = True
        if action.get("retire_missing_seed"):
            # solo bootstrap: hechos de semilla activos que ya no estan en la semilla
            vigentes = {(f["section"], f["text"]) for f in facts}
            for r in conn.execute(
                    "SELECT id, section, text FROM facts WHERE page_id = ? AND created_by = 'seed' "
                    "AND status = 'active'", (page["id"],)).fetchall():
                if (r["section"], r["text"]) not in vigentes:
                    conn.execute("UPDATE facts SET status = 'superseded' WHERE id = ?", (r["id"],))
                    changed = True
        if changed:
            version = self._bump(conn, page["id"], action.get("reason") or f"upsert_page por {actor}")
        else:
            version = conn.execute(
                "SELECT version FROM pages WHERE id = ?", (page["id"],)).fetchone()[0]
        return {"page_id": page["id"], "fact_ids": fact_ids, "version": version,
                "_meta": {"changed": changed, "index_dirty": header_changed, "created": created}}

    def _page_row(self, conn, page_id) -> sqlite3.Row:
        if not isinstance(page_id, str) or not page_id:
            raise ValidationError("page_id: requerido")
        row = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        if row is None:
            raise ValidationError(f"la pagina {page_id!r} no existe")
        return row

    def _fact_row(self, conn, fact_id) -> sqlite3.Row:
        if not isinstance(fact_id, str) or not fact_id:
            raise ValidationError("fact_id: requerido")
        row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
        if row is None:
            raise ValidationError(f"el hecho {fact_id!r} no existe")
        return row

    def _op_add_fact(self, conn, action: dict, actor: str) -> dict:
        page = self._page_row(conn, action.get("page_id"))
        fact = validate_fact(action.get("fact") or {}, status=action.get("status"))
        dup = conn.execute(
            "SELECT id FROM facts WHERE page_id = ? AND section = ? AND text = ? "
            "AND status IN ('active','pending')",
            (page["id"], fact["section"], fact["text"])).fetchone()
        if dup is not None:
            raise ValidationError(f"ya existe un hecho igual en la pagina: {dup['id']}")
        fid = self._insert_fact(conn, page, fact, actor)
        version = self._bump(conn, page["id"], action.get("reason") or f"add_fact {fid} por {actor}")
        return {"page_id": page["id"], "fact_ids": [fid], "version": version}

    def _op_supersede_fact(self, conn, action: dict, actor: str) -> dict:
        old = self._fact_row(conn, action.get("fact_id"))
        if old["status"] != "active":
            raise ValidationError(
                f"solo se reemplazan hechos activos; {old['id']} esta {old['status']}")
        page = self._page_row(conn, old["page_id"])
        fact = validate_fact(action.get("new_fact") or {}, status=action.get("status"))
        if fact["status"] == "active":
            # el viejo sale primero para no chocar con el tope de hechos activos
            conn.execute("UPDATE facts SET status = 'superseded' WHERE id = ?", (old["id"],))
        fid = self._insert_fact(conn, page, fact, actor)
        conn.execute("UPDATE facts SET superseded_by = ? WHERE id = ?", (fid, old["id"]))
        version = self._bump(
            conn, page["id"],
            action.get("reason") or f"supersede_fact {old['id']} -> {fid} ({fact['status']}) por {actor}")
        return {"page_id": page["id"], "fact_ids": [fid], "version": version}

    def _op_approve_fact(self, conn, action: dict, actor: str) -> dict:
        f = self._fact_row(conn, action.get("fact_id"))
        if f["status"] != "pending":
            raise ValidationError(f"solo se aprueban hechos pendientes; {f['id']} esta {f['status']}")
        # los hechos que este reemplaza pasan a superseded antes de contar el tope
        conn.execute(
            "UPDATE facts SET status = 'superseded' WHERE superseded_by = ? AND status = 'active'",
            (f["id"],))
        if self._count_active(conn, f["page_id"]) >= MAX_ACTIVE_FACTS:
            raise ValidationError(
                f"la pagina {f['page_id']} ya tiene {MAX_ACTIVE_FACTS} hechos activos")
        conn.execute("UPDATE facts SET status = 'active' WHERE id = ?", (f["id"],))
        version = self._bump(conn, f["page_id"],
                             action.get("reason") or f"approve_fact {f['id']} por {actor}")
        return {"page_id": f["page_id"], "fact_ids": [f["id"]], "version": version}

    def _op_reject_fact(self, conn, action: dict, actor: str) -> dict:
        f = self._fact_row(conn, action.get("fact_id"))
        if f["status"] not in ("pending", "active"):
            raise ValidationError(
                f"solo se rechazan hechos pendientes o activos; {f['id']} esta {f['status']}")
        conn.execute("UPDATE facts SET status = 'rejected' WHERE id = ?", (f["id"],))
        # si era un reemplazo pendiente, el hecho original queda libre
        conn.execute(
            "UPDATE facts SET superseded_by = NULL WHERE superseded_by = ? AND status = 'active'",
            (f["id"],))
        motivo = str(action.get("reason") or "").strip()
        version = self._bump(conn, f["page_id"],
                             f"reject_fact {f['id']} por {actor}" + (f": {motivo}" if motivo else ""))
        return {"page_id": f["page_id"], "fact_ids": [f["id"]], "version": version}

    _OPS = {
        "upsert_page": _op_upsert_page, "add_fact": _op_add_fact,
        "supersede_fact": _op_supersede_fact, "approve_fact": _op_approve_fact,
        "reject_fact": _op_reject_fact,
    }

    def _apply(self, conn, action: dict, actor: str) -> dict:
        if not isinstance(action, dict):
            raise ValidationError("action: se esperaba un objeto con 'op'")
        op = self._OPS.get(action.get("op"))
        if op is None:
            raise ValidationError(
                f"op desconocida: {action.get('op')!r} (validas: {', '.join(self._OPS)})")
        return op(self, conn, action, actor or "anon")

    def apply_action(self, action: dict, actor: str) -> dict:
        """Aplica una accion validada en su propia transaccion. Nunca lanza por datos malos."""
        res = {"ok": False, "error": None, "page_id": None, "fact_ids": [], "version": None}
        if isinstance(action, dict):
            res["page_id"] = action.get("page_id") or (action.get("page") or {}).get("id")
        meta = None
        try:
            with self._write() as conn:
                out = self._apply(conn, action, actor)
                meta = out.pop("_meta", {"changed": True})
                res.update(out)
            res["ok"] = True
        except ValidationError as exc:
            res["error"] = str(exc)
        except sqlite3.Error as exc:
            res["error"] = f"error de base de datos: {exc}"
        if res["ok"] and meta is not None:
            self._after_apply(action, actor, res, meta)
        return res

    def apply_actions(self, actions: list[dict], actor: str) -> list[dict]:
        """Varias acciones en UNA transaccion (carga de semillas). Las invalidas se saltan.

        No regenera markdown ni escribe la bitacora: quien la usa llama a render_all().
        """
        out = []
        with self._write() as conn:
            for i, action in enumerate(actions):
                res = {"ok": False, "error": None, "page_id": None, "fact_ids": [], "version": None}
                conn.execute(f"SAVEPOINT a{i}")
                try:
                    hecho = self._apply(conn, action, actor)
                    hecho.pop("_meta", None)
                    res.update(hecho)
                    res["ok"] = True
                    conn.execute(f"RELEASE a{i}")
                except ValidationError as exc:
                    conn.execute(f"ROLLBACK TO a{i}")
                    conn.execute(f"RELEASE a{i}")
                    res["error"] = str(exc)
                    if isinstance(action, dict):
                        res["page_id"] = action.get("page_id") or (action.get("page") or {}).get("id")
                out.append(res)
        return out

    # ------------------------------------------------------------------ markdown
    def render_markdown(self, page_id: str) -> str:
        """El mismo texto que se escribe en el archivo markdown de la pagina."""
        page = self.get_page(page_id, include_inactive=True)
        if page is None:
            return f"(no existe la pagina {page_id})"
        return _render.render_page(page)

    # ------------------------------------------------------------------ feedback
    @staticmethod
    def _feedback_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        try:
            d["triage"] = json.loads(d["triage_json"]) if d.get("triage_json") else None
        except (TypeError, ValueError):
            d["triage"] = None
        return d

    @staticmethod
    def _clean_feedback_fields(fields: dict) -> dict:
        if "triage" in fields and "triage_json" not in fields:
            fields["triage_json"] = fields.pop("triage")
        desconocidos = [k for k in fields if k not in _FEEDBACK_COLS]
        if desconocidos:
            raise ValueError(f"campos de feedback desconocidos: {desconocidos}")
        if "status" in fields and fields["status"] not in FEEDBACK_STATUSES:
            raise ValueError(f"status de feedback desconocido: {fields['status']!r}")
        if fields.get("direccion") is not None and fields["direccion"] not in DIRECCIONES:
            raise ValueError(f"direccion desconocida: {fields['direccion']!r}")
        tj = fields.get("triage_json")
        if tj is not None and not isinstance(tj, str):
            fields["triage_json"] = json.dumps(tj, ensure_ascii=False)
        return fields

    def create_feedback(self, **fields) -> int:
        """Crea una fila de feedback (status 'new' por defecto) y devuelve su id."""
        fields = self._clean_feedback_fields(dict(fields))
        fields.setdefault("created_at", _now())
        fields.setdefault("status", "new")
        cols = list(fields)
        sql = (f"INSERT INTO feedback({', '.join(cols)}) "
               f"VALUES ({', '.join('?' for _ in cols)})")  # columnas de lista blanca
        with self._write() as conn:
            cur = conn.execute(sql, [fields[c] for c in cols])
            return int(cur.lastrowid)

    def get_feedback(self, feedback_id: int) -> dict | None:
        with self._read() as conn:
            row = conn.execute("SELECT * FROM feedback WHERE id = ?", (int(feedback_id),)).fetchone()
            return self._feedback_dict(row) if row else None

    def list_feedback(self, status: str | None = None, limit: int = 100) -> list[dict]:
        with self._read() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM feedback WHERE status = ? ORDER BY id DESC LIMIT ?",
                    (status, int(limit))).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
            return [self._feedback_dict(r) for r in rows]

    def update_feedback(self, feedback_id: int, **fields) -> None:
        fields = self._clean_feedback_fields(dict(fields))
        if not fields:
            return
        cols = list(fields)
        sql = f"UPDATE feedback SET {', '.join(c + ' = ?' for c in cols)} WHERE id = ?"
        with self._write() as conn:
            cur = conn.execute(sql, [fields[c] for c in cols] + [int(feedback_id)])
            if cur.rowcount == 0:
                raise KeyError(f"feedback {feedback_id} no existe")

    # ------------------------------------------------------------------ traducciones
    def save_translation(self, record: dict) -> str:
        """Guarda una traduccion; acepta 'trace' (dict) o 'trace_json' (dict o str)."""
        rec = dict(record or {})
        tid = rec.get("id") or uuid.uuid4().hex
        trace = rec.get("trace_json", rec.get("trace"))
        if trace is not None and not isinstance(trace, str):
            trace = json.dumps(trace, ensure_ascii=False)
        with self._write() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO translations(id, created_at, direccion, source_text, "
                "normalized_text, output, mode, trace_json) VALUES (?,?,?,?,?,?,?,?)",
                (tid, rec.get("created_at") or _now(), rec.get("direccion"),
                 rec.get("source_text"), rec.get("normalized_text"), rec.get("output"),
                 rec.get("mode"), trace))
        return tid

    def get_translation(self, translation_id: str) -> dict | None:
        with self._read() as conn:
            row = conn.execute(
                "SELECT * FROM translations WHERE id = ?", (translation_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        try:
            d["trace"] = json.loads(d["trace_json"]) if d.get("trace_json") else None
        except (TypeError, ValueError):
            d["trace"] = None
        return d
