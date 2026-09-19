"""Arbol markdown (seccion 8.1): archivos de pagina, indices, bitacora y rutas."""
from __future__ import annotations

from pathlib import Path

from wiki_helpers import dict_src, lemma_action

from src.wiki import render
from src.wiki.store import WikiStore


def test_page_file_matches_render_markdown(wiki):
    rel = wiki.path_for("lemma:tukui")
    assert rel == "lemma/tukui.md"
    archivo = Path(wiki.pages_root) / rel
    texto = archivo.read_text(encoding="utf-8")
    assert texto == wiki.render_markdown("lemma:tukui")
    assert texto.startswith("---\nid: lemma:tukui\nkind: lemma\ntitle: \"tukui\"\nstatus: active\nversion: 1\n")
    assert 'aliases: ["tukui"' in texto and "updated_at: " in texto
    assert "\n# tukui\n" in texto and "\n## Significado\n" in texto
    f = wiki.get_page("lemma:tukui")["facts"][0]
    assert f"- [{f['id']}] tukui (adj): todo; todos\n  - fuente: dictionary lema:tukui \"tukui (adj): todo; todos\"" in texto


def test_pending_and_history_sections(wiki):
    old = wiki.get_page("lemma:killa")["facts"][0]
    r = wiki.apply_action({"op": "supersede_fact", "fact_id": old["id"], "status": "pending",
                           "new_fact": {"section": "meaning", "text": "killa (s): luna; mes; menstruacion",
                                        "sources": dict_src("killa", "killa (s): luna; mes")}}, "agent")
    nuevo = r["fact_ids"][0]
    texto = (Path(wiki.pages_root) / "lemma/killa.md").read_text(encoding="utf-8")
    assert f"- [{nuevo}] killa (s): luna; mes; menstruacion (estado: pendiente)" in texto
    assert "## Historial" not in texto and "version: 2" in texto
    wiki.apply_action({"op": "approve_fact", "fact_id": nuevo}, "humano")
    texto = (Path(wiki.pages_root) / "lemma/killa.md").read_text(encoding="utf-8")
    cuerpo, historial = texto.split("## Historial")
    assert f"[{nuevo}]" in cuerpo and "(estado: pendiente)" not in cuerpo
    assert f"- [{old['id']}] killa (s): luna; mes (estado: reemplazado por {nuevo})" in historial
    assert texto == wiki.render_markdown("lemma:killa")


def test_paths_ascii_fold_collisions_and_roundtrip(wiki):
    # ni y ñi chocan al plegar a ASCII: la segunda recibe sufijo numerico
    rutas = {wiki.path_for("lemma:ni"), wiki.path_for("lemma:ñi")}
    assert rutas == {"lemma/ni.md", "lemma/ni-2.md"}
    assert wiki.path_for("lemma:atun-taita") == "lemma/atun-taita.md"
    assert wiki.path_for("lemma:noexiste") is None
    for p in wiki.list_pages(limit=100):
        rel = wiki.path_for(p["id"])
        assert rel.isascii() and rel == rel.lower() and " " not in rel
        assert (Path(wiki.pages_root) / rel).is_file()
        assert wiki.page_id_for_path(rel) == p["id"]
    assert wiki.page_id_for_path("wiki/lemma/ni-2.md") == wiki.page_id_for_path("lemma/ni-2.md")
    assert wiki.page_id_for_path("/lemma/wasi.md") == "lemma:wasi"
    assert wiki.page_id_for_path(str(Path(wiki.pages_root) / "lemma" / "wasi.md")) == "lemma:wasi"
    for malo in ("lemma/index.md", "lemma/../lemma/wasi.md", "../wiki.db", "lemma/nada.md", "", "log.md"):
        assert wiki.page_id_for_path(malo) is None
    # la ruta es estable: un upsert posterior no la cambia
    wiki.apply_action(lemma_action("ñi", [("conj", "(Esp) ni (AP, ni - MP)")]), "seed")
    assert {wiki.path_for("lemma:ni"), wiki.path_for("lemma:ñi")} == rutas


def test_ascii_slug():
    assert render.ascii_slug("Ñawi Kilpaska") == "nawi-kilpaska"
    assert render.ascii_slug("kumpañaí") == "kumpanai"
    assert render.relative_path("lemma", "index", set()) == "lemma/p-index.md"
    assert render.relative_path("lemma", "ñi", {"lemma/ni.md", "lemma/ni-2.md"}) == "lemma/ni-3.md"


def test_indexes_and_log(wiki):
    raiz = Path(wiki.pages_root)
    idx = (raiz / "lemma" / "index.md").read_text(encoding="utf-8")
    assert "- [wasi](wasi.md) - s: casa; hogar" in idx
    assert "ELEGIR" in idx and "nunca para responder" in idx
    root = (raiz / "index.md").read_text(encoding="utf-8")
    assert "nunca para responder" in root and "[lemma/](lemma/index.md)" in root
    log = (raiz / "log.md").read_text(encoding="utf-8")
    n0 = log.count("\n- ")
    assert "| seed | upsert_page | lemma:wasi |" in log
    # accion sin cambios: ni version nueva ni linea de bitacora
    wiki.apply_action(lemma_action("wasi", [("s", "casa; hogar")], None, [("casa", "s", "wasi")]), "seed")
    assert (raiz / "log.md").read_text(encoding="utf-8").count("\n- ") == n0
    # cambiar el resumen re-renderiza el indice del tipo
    a = lemma_action("wasi", [("s", "casa; hogar")])
    a["page"]["summary"] = "s: casa; vivienda"
    wiki.apply_action(a, "rev")
    assert "- [wasi](wasi.md) - s: casa; vivienda" in (raiz / "lemma" / "index.md").read_text(encoding="utf-8")
    # accion rechazada: no deja linea
    n1 = (raiz / "log.md").read_text(encoding="utf-8").count("\n- ")
    assert not wiki.apply_action({"op": "add_fact", "page_id": "lemma:wasi", "fact": {}}, "agent")["ok"]
    assert (raiz / "log.md").read_text(encoding="utf-8").count("\n- ") == n1
    r = wiki.apply_action({"op": "add_fact", "page_id": "lemma:wasi",
                           "fact": {"section": "note", "text": "nota", "sources": dict_src("wasi", "wasi s casa")}}, "ana")
    ultima = (raiz / "log.md").read_text(encoding="utf-8").strip().splitlines()[-1]
    assert f"| ana | add_fact | lemma:wasi | {r['fact_ids'][0]}" in ultima


def test_render_all_rebuilds_and_removes_stale(wiki):
    raiz = Path(wiki.pages_root)
    (raiz / "lemma" / "wasi.md").unlink()
    (raiz / "lemma" / "fantasma.md").write_text("viejo", encoding="utf-8")
    log_antes = (raiz / "log.md").read_text(encoding="utf-8")
    out = wiki.render_all()
    assert out["pages"] == wiki.count_pages() and out["removed"] == 1
    assert (raiz / "lemma" / "wasi.md").is_file() and not (raiz / "lemma" / "fantasma.md").exists()
    assert (raiz / "log.md").read_text(encoding="utf-8") == log_antes      # la bitacora solo se agrega
    for kind in ("lemma", "suffix", "grammar", "convention", "case"):
        assert (raiz / kind / "index.md").is_file()


def test_big_index_is_split_by_letter(wiki, monkeypatch):
    monkeypatch.setattr(render, "MAX_INDEX_BYTES", 300)
    render.write_kind_index(wiki, "lemma")
    raiz = Path(wiki.pages_root) / "lemma"
    principal = (raiz / "index.md").read_text(encoding="utf-8")
    assert "[W](index-w.md)" in principal and "- [wasi](wasi.md)" not in principal
    assert "- [wasi](wasi.md)" in (raiz / "index-w.md").read_text(encoding="utf-8")
    monkeypatch.setattr(render, "MAX_INDEX_BYTES", 400_000)
    render.write_kind_index(wiki, "lemma")
    assert not list(raiz.glob("index-*.md"))


def test_old_db_without_paths_gets_backfilled(tmp_path):
    s = WikiStore(tmp_path / "w.db", auto_render=False)
    s.apply_action(lemma_action("wasi", [("s", "casa")]), "seed")
    import sqlite3
    conn = sqlite3.connect(s.db_path)
    conn.execute("DELETE FROM page_paths")
    conn.commit()
    conn.close()
    assert WikiStore(tmp_path / "w.db").path_for("lemma:wasi") == "lemma/wasi.md"
    assert not (tmp_path / "pages" / "lemma" / "wasi.md").exists()      # auto_render=False no escribe
