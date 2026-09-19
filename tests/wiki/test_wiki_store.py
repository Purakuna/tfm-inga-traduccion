"""Acciones del store, validacion, versionado y ciclo de vida del feedback."""
from __future__ import annotations

import json
import sqlite3
import threading

import pytest

from src.wiki.store import WikiStore, gloss_tokens
from src.wiki.validation import ValidationError, fold, validate_fact, validate_page, validate_source

from wiki_helpers import dict_src, lemma_action


def _fact(text="sinchi tambien se usa como 'fuerte' en el corpus", section="usage", sources=None):
    return {"section": section, "text": text,
            "sources": sources or [{"type": "corpus", "ref": "Lucas 1:80", "quote": "sinchi tukuspa"}]}


# ------------------------------------------------------------------ lectura y forma
def test_get_page_shape(wiki):
    p = wiki.get_page("lemma:tukui")
    assert set(p) >= {"id", "kind", "slug", "title", "summary", "status", "version",
                      "updated_at", "aliases", "facts"}
    assert p["kind"] == "lemma" and p["status"] == "active" and p["version"] == 1
    assert len(p["facts"]) == 2  # homografo: un hecho por sentido, con la categoria en el texto
    assert "(adj)" in p["facts"][0]["text"] and "(v.i.)" in p["facts"][1]["text"]
    f = p["facts"][0]
    assert set(f) >= {"id", "section", "text", "status", "created_by", "created_at", "sources"}
    assert f["id"].startswith("f_") and len(f["id"]) == 10
    assert f["created_by"] == "seed"
    assert f["sources"] == [{"type": "dictionary", "ref": "lema:tukui", "quote": "tukui (adj): todo; todos"}]
    assert wiki.get_page("lemma:noexiste") is None


def test_find_pages_prefix_then_text(wiki):
    ids = [p["id"] for p in wiki.find_pages("was")]
    assert ids[0] == "lemma:wasi"
    assert set(wiki.find_pages("wasi")[0]) == {"id", "kind", "title", "summary", "n_facts"}
    # alias de variante dialectal
    assert [p["id"] for p in wiki.find_pages("achijii")] == ["lemma:achijai"]
    # subcadena en texto de hecho
    assert "lemma:sinchi" in [p["id"] for p in wiki.find_pages("curandero")]
    # filtro por tipo y consulta hostil: SQL parametrizado, comodines escapados
    assert wiki.find_pages("wasi", kind="suffix") == []
    assert wiki.find_pages("'; DROP TABLE pages; --") == []
    assert wiki.find_pages("%") == []
    assert wiki.get_page("lemma:wasi") is not None


def test_find_by_gloss_folds_and_ranks(wiki):
    assert wiki.find_by_gloss("CASA")[0]["id"] == "lemma:wasi"
    # "casa" como glosa completa gana a "casa de palos ..." (lema de varias palabras)
    ids = [p["id"] for p in wiki.find_by_gloss("casa")]
    assert ids.index("lemma:wasi") < ids.index("lemma:chanchala-wasi")
    assert wiki.find_by_gloss("medico")[0]["id"] == "lemma:sinchi"      # sin tilde
    assert wiki.find_by_gloss("brujo")[0]["id"] == "lemma:sinchi"       # entrada espanol-inga
    # la palabra espanola "ama" no debe caer en el lema inga homografo "ama"
    assert "lemma:ama" not in [p["id"] for p in wiki.find_by_gloss("ama")]
    assert wiki.find_by_gloss("") == [] and wiki.find_by_gloss("zzzz") == []


def test_gloss_tokens_ranks():
    r = gloss_tokens("wasi (s): casa; hogar de la familia (véase uku)", "wasi")
    assert r["casa"] == 3 and r["hogar"] == 2 and r["familia"] == 1 and r["uku"] == 0
    assert "wasi" not in r
    r = gloss_tokens("brujo (s): millaipa iacha, sinchi [entrada espanol-inga del diccionario]", "sinchi")
    assert r == {"brujo": 3}


def test_list_pages_and_stats(wiki):
    todas = wiki.list_pages(limit=100)
    assert len(todas) == wiki.count_pages() == wiki.stats()["pages"]["lemma"]
    assert wiki.list_pages(kind="lemma", offset=1, limit=2)[0]["id"] == todas[1]["id"]
    st = wiki.stats()
    assert st["pages"]["total"] == len(todas)
    assert st["facts"]["active"] == st["facts"]["total"] > 0
    assert set(st["feedback"]) >= {"new", "auto_applied", "pending_review", "approved", "rejected"}


# ------------------------------------------------------------------ acciones y versionado
def test_upsert_is_idempotent_and_versions(store):
    a = lemma_action("wasi", [("s", "casa; hogar")])
    r1 = store.apply_action(a, "seed")
    r2 = store.apply_action(a, "seed")
    assert r1["ok"] and r1["version"] == 1 and len(r1["fact_ids"]) == 1
    assert r2["ok"] and r2["version"] == 1 and r2["fact_ids"] == []
    a["page"]["summary"] = "s: casa"
    r3 = store.apply_action(a, "seed")
    assert r3["version"] == 2
    conn = sqlite3.connect(store.db_path)
    snaps = conn.execute("SELECT version, snapshot_json FROM page_versions WHERE page_id = ? "
                         "ORDER BY version", ("lemma:wasi",)).fetchall()
    conn.close()
    assert [v for v, _ in snaps] == [1, 2]
    assert json.loads(snaps[1][1])["summary"] == "s: casa"


def test_add_fact_bumps_version_and_snapshot(wiki):
    r = wiki.apply_action({"op": "add_fact", "page_id": "lemma:sinchi", "fact": _fact(),
                           "status": "active"}, actor="agent")
    assert r["ok"] and r["error"] is None and r["version"] == 2 and r["page_id"] == "lemma:sinchi"
    f = wiki.get_fact(r["fact_ids"][0])
    assert f["status"] == "active" and f["created_by"] == "agent" and f["page_id"] == "lemma:sinchi"
    dup = wiki.apply_action({"op": "add_fact", "page_id": "lemma:sinchi", "fact": _fact()}, "agent")
    assert not dup["ok"] and "ya existe" in dup["error"]


def test_supersede_active(wiki):
    old = wiki.get_page("lemma:wasi")["facts"][0]
    r = wiki.apply_action({"op": "supersede_fact", "fact_id": old["id"], "status": "active",
                           "new_fact": {"section": "meaning", "text": "wasi (s): casa; hogar; vivienda",
                                        "sources": dict_src("wasi", "wasi (s): casa; hogar")}}, "rev")
    assert r["ok"]
    visibles = [f["id"] for f in wiki.get_page("lemma:wasi")["facts"]]
    assert old["id"] not in visibles and r["fact_ids"][0] in visibles
    todos = {f["id"]: f for f in wiki.get_page("lemma:wasi", include_inactive=True)["facts"]}
    assert todos[old["id"]]["status"] == "superseded"
    assert todos[old["id"]]["superseded_by"] == r["fact_ids"][0]


def test_supersede_pending_then_approve(wiki):
    old = wiki.get_page("lemma:killa")["facts"][0]
    r = wiki.apply_action({"op": "supersede_fact", "fact_id": old["id"], "status": "pending",
                           "new_fact": {"section": "meaning", "text": "killa (s): luna; mes; menstruacion",
                                        "sources": dict_src("killa", "killa (s): luna; mes")}}, "agent")
    nuevo = r["fact_ids"][0]
    estados = {f["id"]: f["status"] for f in wiki.get_page("lemma:killa")["facts"]}
    assert estados == {old["id"]: "active", nuevo: "pending"}   # el viejo sigue activo
    ok = wiki.apply_action({"op": "approve_fact", "fact_id": nuevo}, "humano")
    assert ok["ok"]
    estados = {f["id"]: f["status"] for f in wiki.get_page("lemma:killa", include_inactive=True)["facts"]}
    assert estados == {old["id"]: "superseded", nuevo: "active"}
    again = wiki.apply_action({"op": "approve_fact", "fact_id": nuevo}, "humano")
    assert not again["ok"]


def test_supersede_pending_then_reject_keeps_old(wiki):
    old = wiki.get_page("lemma:killa")["facts"][0]
    r = wiki.apply_action({"op": "supersede_fact", "fact_id": old["id"], "status": "pending",
                           "new_fact": {"section": "meaning", "text": "killa (s): sol",
                                        "sources": dict_src("killa", "killa (s): luna; mes")}}, "agent")
    rej = wiki.apply_action({"op": "reject_fact", "fact_id": r["fact_ids"][0], "reason": "contradice"}, "humano")
    assert rej["ok"]
    todos = {f["id"]: f for f in wiki.get_page("lemma:killa", include_inactive=True)["facts"]}
    assert todos[old["id"]]["status"] == "active" and todos[old["id"]]["superseded_by"] is None
    assert todos[r["fact_ids"][0]]["status"] == "rejected"      # nunca se borra
    conn = sqlite3.connect(wiki.db_path)
    razon = conn.execute("SELECT reason FROM page_versions WHERE page_id = 'lemma:killa' "
                         "ORDER BY version DESC LIMIT 1").fetchone()[0]
    conn.close()
    assert "contradice" in razon


@pytest.mark.parametrize("action, fragmento", [
    ({"op": "borrar_todo"}, "op desconocida"),
    ({"op": "add_fact", "page_id": "lemma:nada", "fact": _fact()}, "no existe"),
    ({"op": "add_fact", "page_id": "lemma:wasi", "fact": _fact(section="etimologia")}, "section"),
    ({"op": "add_fact", "page_id": "lemma:wasi", "fact": _fact(text="x" * 401)}, "maximo 400"),
    ({"op": "add_fact", "page_id": "lemma:wasi", "fact": {"section": "note", "text": "sin fuente", "sources": []}},
     "al menos una fuente"),
    ({"op": "add_fact", "page_id": "lemma:wasi",
      "fact": _fact(sources=[{"type": "wikipedia", "ref": "x", "quote": "y"}])}, "source.type"),
    ({"op": "add_fact", "page_id": "lemma:wasi",
      "fact": _fact(sources=[{"type": "corpus", "ref": "Juan 1:1", "quote": "q" * 301}])}, "maximo 300"),
    ({"op": "add_fact", "page_id": "lemma:wasi",
      "fact": _fact(sources=[{"type": "grammar", "ref": "levinsohn:pag 3", "quote": "q"}])}, "grammar"),
    ({"op": "add_fact", "page_id": "lemma:wasi",
      "fact": _fact(sources=[{"type": "feedback", "ref": "feedback:999", "quote": ""}])}, "no existe en la tabla feedback"),
    ({"op": "add_fact", "page_id": "lemma:wasi", "fact": _fact(), "status": "superseded"}, "active o pending"),
    ({"op": "upsert_page", "page": {"id": "lemma:otra", "kind": "lemma", "slug": "wasi", "title": "wasi"}}, "no coincide"),
    ({"op": "upsert_page", "page": {"kind": "poema", "slug": "x", "title": "x"}}, "kind"),
    ({"op": "upsert_page", "page": {"kind": "lemma", "slug": "x", "title": "t" * 121}}, "maximo 120"),
    ({"op": "upsert_page", "page": {"kind": "lemma", "slug": "x", "title": "x", "summary": "s" * 301}}, "maximo 300"),
    ({"op": "approve_fact", "fact_id": "f_00000000"}, "no existe"),
])
def test_validation_rejects(wiki, action, fragmento):
    antes = wiki.stats()
    r = wiki.apply_action(action, "agent")
    assert r["ok"] is False and fragmento in r["error"], r
    assert r["fact_ids"] == []
    assert wiki.stats()["facts"] == antes["facts"]  # nada a medias


def test_max_active_facts_per_page(store):
    store.apply_action(lemma_action("rimai", [("v.t.", "hablar")]), "seed")
    for i in range(39):
        r = store.apply_action({"op": "add_fact", "page_id": "lemma:rimai",
                                "fact": _fact(text=f"uso {i}")}, "agent")
        assert r["ok"], r
    lleno = store.apply_action({"op": "add_fact", "page_id": "lemma:rimai", "fact": _fact(text="uso 40")}, "agent")
    assert not lleno["ok"] and "40 hechos activos" in lleno["error"]
    pend = store.apply_action({"op": "add_fact", "page_id": "lemma:rimai", "fact": _fact(text="uso 41"),
                               "status": "pending"}, "agent")
    assert pend["ok"]  # los pendientes no cuentan hasta aprobarse
    assert not store.apply_action({"op": "approve_fact", "fact_id": pend["fact_ids"][0]}, "h")["ok"]


def test_validators_direct():
    assert validate_source({"source_type": "dictionary", "source_ref": "lema:wasi", "quote": "wasi s casa"}) == \
        {"type": "dictionary", "ref": "lema:wasi", "quote": "wasi s casa"}
    assert validate_source({"type": "grammar", "ref": "rosetta:L10-L20", "quote": "x"})["ref"] == "rosetta:L10-L20"
    with pytest.raises(ValidationError):
        validate_source({"type": "dictionary", "ref": "lema:wasi", "quote": ""})
    with pytest.raises(ValidationError):
        validate_page({"kind": "lemma", "slug": "con espacio", "title": "x"})
    f = validate_fact({"section": "note", "text": " hola ", "sources": dict_src("a", "b") * 2})
    assert f["text"] == "hola" and len(f["sources"]) == 1 and f["status"] == "active"
    assert fold("ÑAWI Día") == "ñawi dia"


# ------------------------------------------------------------------ feedback y traducciones
def test_feedback_lifecycle(wiki):
    fid = wiki.create_feedback(author="ana", direccion="inga2es", source_text="Sinchi tukui.",
                               model_output="El curandero todo.", correction="Hazte fuerte.",
                               comment="sinchi aqui es fuerte")
    fb = wiki.get_feedback(fid)
    assert fb["status"] == "new" and fb["author"] == "ana" and fb["created_at"]
    # hecho pendiente citando el feedback
    r = wiki.apply_action({"op": "add_fact", "page_id": "lemma:sinchi", "status": "pending",
                           "fact": {"section": "usage", "text": "sinchi tukui = hacerse fuerte",
                                    "sources": [{"type": "feedback", "ref": f"feedback:{fid}", "quote": "Hazte fuerte."}]}},
                          actor="agent")
    assert r["ok"], r
    wiki.update_feedback(fid, status="pending_review", triage_json={"verdict": "needs_review"})
    fb = wiki.get_feedback(fid)
    assert fb["status"] == "pending_review" and fb["triage"] == {"verdict": "needs_review"}
    assert json.loads(fb["triage_json"])["verdict"] == "needs_review"
    assert [x["id"] for x in wiki.list_feedback(status="pending_review")] == [fid]
    assert wiki.list_feedback(status="approved") == []
    ligados = wiki.facts_by_source("feedback", f"feedback:{fid}")
    assert [(f["page_id"], f["status"]) for f in ligados] == [("lemma:sinchi", "pending")]
    # revision humana
    assert wiki.apply_action({"op": "approve_fact", "fact_id": ligados[0]["id"]}, "rev")["ok"]
    wiki.update_feedback(fid, status="approved", reviewer="rev", review_note="ok", reviewed_at="2026-09-19")
    assert wiki.get_feedback(fid)["reviewer"] == "rev"
    assert wiki.facts_by_source("feedback", f"feedback:{fid}")[0]["status"] == "active"
    assert wiki.stats()["feedback"]["approved"] == 1
    with pytest.raises(ValueError):
        wiki.update_feedback(fid, status="archivado")
    with pytest.raises(ValueError):
        wiki.create_feedback(autor="x")
    with pytest.raises(KeyError):
        wiki.update_feedback(9999, status="rejected")
    assert wiki.get_feedback(9999) is None


def test_translations_roundtrip(store):
    tid = store.save_translation({"direccion": "inga2es", "source_text": "Alli puncha", "normalized_text": "alli puncha",
                                  "output": "Buen dia", "mode": "fast", "trace_json": {"pages": ["lemma:alli"]}})
    assert len(tid) == 32
    t = store.get_translation(tid)
    assert t["output"] == "Buen dia" and t["trace"] == {"pages": ["lemma:alli"]}
    assert json.loads(t["trace_json"]) == t["trace"]
    assert store.save_translation({"id": "abc", "trace": {"x": 1}}) == "abc"
    assert store.get_translation("abc")["trace"] == {"x": 1}
    assert store.get_translation("nada") is None


def test_threads_can_write(wiki):
    errores = []

    def trabajo(n):
        try:
            s = WikiStore(wiki.db_path)
            for i in range(5):
                r = s.apply_action({"op": "add_fact", "page_id": "lemma:runa",
                                    "fact": _fact(text=f"hilo {n} nota {i}")}, f"hilo{n}")
                assert r["ok"], r
        except Exception as exc:  # noqa: BLE001
            errores.append(exc)

    hilos = [threading.Thread(target=trabajo, args=(n,)) for n in range(4)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert errores == []
    assert len(wiki.get_page("lemma:runa")["facts"]) == 21
    assert wiki.get_page("lemma:runa")["version"] == 21
