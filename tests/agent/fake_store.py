"""Almacen falso en memoria con la interfaz de la seccion 3 del contrato.

Sirve para probar el agente y la API sin depender de `src/wiki/` ni de SQLite.
Implementa lo justo de cada operacion, con las mismas formas de retorno.
"""
from __future__ import annotations

import copy
import json
import unicodedata
import uuid
from pathlib import Path


def _fold(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


class FakeStore:
    def __init__(self, pages_root: Path | str | None = None):
        # Con pages_root materializa un arbol markdown minimo (seccion 8.1) para las fs tools.
        self.pages_root = Path(pages_root) if pages_root else None
        self.pages: dict[str, dict] = {}
        self.feedback: dict[int, dict] = {}
        self.translations: dict[str, dict] = {}
        self.actions: list[tuple[dict, str]] = []
        self._n = 0

    # --- utilidades de los tests ---
    def add_page(self, page_id: str, title: str, summary: str = "", facts: list[dict] | None = None,
                 aliases: list[str] | None = None) -> None:
        kind, slug = page_id.split(":", 1)
        self.pages[page_id] = {
            "id": page_id, "kind": kind, "slug": slug, "title": title, "summary": summary,
            "status": "active", "version": 1, "updated_at": "2026-01-01T00:00:00+00:00",
            "aliases": aliases or [slug], "facts": [],
        }
        for f in facts or []:
            self._insert(page_id, f, f.get("status", "active"), "seed")
        self.render(page_id)

    # --- arbol markdown (seccion 8.1, version minima) ---
    def path_for(self, page_id: str) -> str | None:
        p = self.pages.get(page_id)
        return f"{p['kind']}/{p['slug']}.md" if p else None

    def page_id_for_path(self, path: str) -> str | None:
        partes = [x for x in str(path).replace("\\", "/").split("/") if x]
        if ".." in partes or len(partes) < 2 or not partes[-1].endswith(".md"):
            return None
        pid = f"{partes[-2]}:{partes[-1][:-3]}"
        return pid if pid in self.pages else None

    def render(self, page_id: str) -> None:
        if self.pages_root is None:
            return
        p = self.pages[page_id]
        lines = ["---", f"id: {p['id']}", f"kind: {p['kind']}", f"title: \"{p['title']}\"", "---", "",
                 f"# {p['title']}", "", p["summary"], ""]
        vivos = [f for f in p["facts"] if f["status"] in ("active", "pending")]
        for f in vivos:
            estado = " (estado: pendiente)" if f["status"] == "pending" else ""
            lines.append(f"- [{f['id']}] {f['text']}{estado}")
            lines += [f"  - fuente: {s['type']} {s['ref']} \"{s.get('quote', '')}\"" for s in f["sources"]]
        archivo = self.pages_root / self.path_for(page_id)
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("\n".join(lines) + "\n", encoding="utf-8")
        for kind in {q["kind"] for q in self.pages.values()}:
            idx = [f"# {kind}", ""] + [f"- [{q['title']}]({q['slug']}.md) - {q['summary']}"
                                       for q in sorted(self.pages.values(), key=lambda q: q["slug"])
                                       if q["kind"] == kind]
            (self.pages_root / kind / "index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
        (self.pages_root / "index.md").write_text("# Wiki Inga\n\nIndice para ELEGIR pagina.\n", encoding="utf-8")

    def _insert(self, page_id: str, fact: dict, status: str, actor: str) -> str:
        self._n += 1
        fid = f"f_{self._n:08x}"
        self.pages[page_id]["facts"].append({
            "id": fid, "section": fact["section"], "text": fact["text"], "status": status,
            "created_by": actor, "created_at": "2026-01-01T00:00:00+00:00", "superseded_by": None,
            "sources": [dict(s) for s in fact.get("sources", [])],
        })
        return fid

    def _fact(self, fact_id: str):
        for p in self.pages.values():
            for f in p["facts"]:
                if f["id"] == fact_id:
                    return p, f
        return None, None

    # --- lectura ---
    def get_page(self, page_id, include_inactive=False):
        p = self.pages.get(page_id)
        if p is None:
            return None
        out = copy.deepcopy(p)
        if not include_inactive:
            out["facts"] = [f for f in out["facts"] if f["status"] in ("active", "pending")]
        return out

    def _summary(self, p: dict) -> dict:
        n = sum(1 for f in p["facts"] if f["status"] in ("active", "pending"))
        return {"id": p["id"], "kind": p["kind"], "title": p["title"], "summary": p["summary"], "n_facts": n}

    def find_pages(self, query, kind=None, limit=20):
        q = _fold(query).lstrip("-")
        if not q:
            return []
        out = []
        for p in self.pages.values():
            if kind and p["kind"] != kind:
                continue
            texto = _fold(" ".join([p["slug"], p["title"], p["summary"], *p["aliases"],
                                    *(f["text"] for f in p["facts"])]))
            if q in texto:
                out.append(self._summary(p))
        return out[:limit]

    def find_by_gloss(self, spanish_word, limit=10):
        q = _fold(spanish_word)
        out = []
        for p in self.pages.values():
            if p["kind"] != "lemma":
                continue
            if any(f["section"] == "meaning" and q in _fold(f["text"]).replace(";", " ").split()
                   for f in p["facts"]):
                out.append(self._summary(p))
        return out[:limit]

    def list_pages(self, kind=None, offset=0, limit=50):
        ps = [self._summary(p) for p in sorted(self.pages.values(), key=lambda p: p["id"])
              if not kind or p["kind"] == kind]
        return ps[offset: offset + limit]

    def stats(self):
        pages: dict[str, int] = {}
        facts: dict[str, int] = {}
        for p in self.pages.values():
            pages[p["kind"]] = pages.get(p["kind"], 0) + 1
            for f in p["facts"]:
                facts[f["status"]] = facts.get(f["status"], 0) + 1
        fb: dict[str, int] = {}
        for r in self.feedback.values():
            fb[r["status"]] = fb.get(r["status"], 0) + 1
        return {"pages": {**pages, "total": len(self.pages)}, "facts": facts, "feedback": fb}

    def render_markdown(self, page_id):
        p = self.get_page(page_id)
        if p is None:
            return f"(no existe la pagina {page_id})"
        lines = [f"# {p['title']}", f"`{p['id']}`", "", p["summary"], ""]
        for f in p["facts"]:
            refs = ", ".join(s["ref"] for s in f["sources"])
            lines.append(f"- {f['text']} [{refs}]")
        return "\n".join(lines)

    # --- escritura ---
    def apply_action(self, action, actor):
        self.actions.append((copy.deepcopy(action), actor))
        res = {"ok": False, "error": None, "page_id": action.get("page_id"), "fact_ids": [], "version": None}
        op = action.get("op")
        try:
            if op == "add_fact":
                page = self.pages.get(action["page_id"])
                if page is None:
                    raise ValueError(f"la pagina {action['page_id']!r} no existe")
                self._check(action["fact"])
                res["fact_ids"] = [self._insert(page["id"], action["fact"], action.get("status", "active"), actor)]
            elif op == "supersede_fact":
                page, old = self._fact(action["fact_id"])
                if old is None:
                    raise ValueError("el hecho no existe")
                self._check(action["new_fact"])
                status = action.get("status", "active")
                fid = self._insert(page["id"], action["new_fact"], status, actor)
                old["superseded_by"] = fid
                if status == "active":
                    old["status"] = "superseded"
                res["fact_ids"] = [fid]
            elif op == "upsert_page":
                pg = action["page"]
                pid = pg.get("id") or f"{pg['kind']}:{pg['slug']}"
                if pid not in self.pages:
                    self.add_page(pid, pg["title"], pg.get("summary", ""), aliases=pg.get("aliases"))
                page = self.pages[pid]
                for f in action.get("facts", []):
                    self._check(f)
                    res["fact_ids"].append(self._insert(pid, f, f.get("status", "active"), actor))
            elif op in ("approve_fact", "reject_fact"):
                page, f = self._fact(action["fact_id"])
                if f is None:
                    raise ValueError("el hecho no existe")
                if op == "approve_fact":
                    if f["status"] != "pending":
                        raise ValueError("solo se aprueban hechos pendientes")
                    f["status"] = "active"
                    for other in page["facts"]:
                        if other.get("superseded_by") == f["id"]:
                            other["status"] = "superseded"
                else:
                    f["status"] = "rejected"
                res["fact_ids"] = [f["id"]]
            else:
                raise ValueError(f"op desconocida: {op!r}")
            page["version"] += 1
            res.update(ok=True, page_id=page["id"], version=page["version"])
            self.render(page["id"])
        except (ValueError, KeyError) as e:
            res["error"] = str(e)
        return res

    def _check(self, fact: dict) -> None:
        if not fact.get("sources"):
            raise ValueError("cada hecho necesita al menos una fuente")
        if len(fact.get("text", "")) > 400:
            raise ValueError("fact.text demasiado largo")
        for s in fact["sources"]:
            if s["type"] == "feedback" and int(s["ref"].split(":")[1]) not in self.feedback:
                raise ValueError(f"la fuente {s['ref']} no existe")

    # --- feedback y traducciones ---
    def create_feedback(self, **fields) -> int:
        fid = len(self.feedback) + 1
        row = {"id": fid, "created_at": "2026-01-01T00:00:00+00:00", "author": None, "direccion": None,
               "source_text": None, "model_output": None, "correction": None, "comment": None,
               "translation_id": None, "status": "new", "triage_json": None, "reviewer": None,
               "reviewed_at": None, "review_note": None}
        row.update(fields)
        self.feedback[fid] = row
        return fid

    def get_feedback(self, feedback_id):
        r = self.feedback.get(int(feedback_id))
        return dict(r) if r else None

    def list_feedback(self, status=None, limit=100):
        rows = [dict(r) for r in self.feedback.values() if not status or r["status"] == status]
        return sorted(rows, key=lambda r: -r["id"])[:limit]

    def update_feedback(self, feedback_id, **fields):
        self.feedback[int(feedback_id)].update(fields)

    def save_translation(self, record):
        rec = dict(record)
        tid = rec.get("id") or uuid.uuid4().hex
        rec["id"] = tid
        if not isinstance(rec.get("trace_json"), str):
            rec["trace_json"] = json.dumps(rec.get("trace_json"), ensure_ascii=False)
        self.translations[tid] = rec
        return tid

    def get_translation(self, translation_id):
        r = self.translations.get(translation_id)
        return dict(r) if r else None


def sample_store(pages_root: Path | str | None = None) -> FakeStore:
    """Wiki minima con las paginas del caso 'sinchi tuku'."""
    st = FakeStore(pages_root)
    st.add_page("lemma:sinchi", "sinchi", "adj: fuerte; duro", facts=[
        {"section": "meaning", "text": "sinchi (adj): fuerte; duro",
         "sources": [{"type": "dictionary", "ref": "lema:sinchi", "quote": "sinchi adj fuerte"}]}])
    st.add_page("lemma:tukui", "tukui", "v: llegar a ser; adj: todo", facts=[
        {"section": "meaning", "text": "tukui (v): llegar a ser",
         "sources": [{"type": "dictionary", "ref": "lema:tukui", "quote": "tukui v llegar a ser"}]},
        {"section": "meaning", "text": "tukui (adj): todo",
         "sources": [{"type": "dictionary", "ref": "lema:tukui", "quote": "tukui adj todo"}]}])
    st.add_page("lemma:wasi", "wasi", "s: casa", facts=[
        {"section": "meaning", "text": "wasi (s): casa",
         "sources": [{"type": "dictionary", "ref": "lema:wasi", "quote": "wasi s casa"}]}])
    st.add_page("suffix:ngapa", "-ngapa (proposito)", "Sufijo verbal de proposito", aliases=["-ngapa", "ngapa"], facts=[
        {"section": "morphology", "text": "-ngapa marca proposito: para + infinitivo",
         "sources": [{"type": "grammar", "ref": "levinsohn:L477-L481", "quote": "El infinitivo de proposicion -ngapa"}]}])
    return st
