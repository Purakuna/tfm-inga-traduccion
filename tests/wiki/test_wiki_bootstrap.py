"""Carga de semillas: idempotente, tolerante y sin perder correcciones de feedback."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from wiki_helpers import LEMAS, lemma_action

from src.wiki.bootstrap import bootstrap
from src.wiki.store import REPO_ROOT, WikiStore


def _seed_line(action: dict) -> str:
    return json.dumps({**action["page"], "facts": action["facts"]}, ensure_ascii=False)


def _write_seeds(seed_dir: Path, extra_lines=()):
    seed_dir.mkdir(parents=True, exist_ok=True)
    lineas = [_seed_line(lemma_action(l, s, a, e)) for l, s, a, e in LEMAS]
    (seed_dir / "lemmas.jsonl").write_text("\n".join(lineas + list(extra_lines)) + "\n", encoding="utf-8")


def test_bootstrap_idempotent_and_tolerant(tmp_path):
    seeds, db = tmp_path / "seed", tmp_path / "wiki.db"
    _write_seeds(seeds)
    out1 = bootstrap(db, seeds, verbose=False)      # grammar.jsonl y suffixes.jsonl aun no existen
    out2 = bootstrap(db, seeds, verbose=False)
    assert out1["stats"]["pages"]["lemma"] == len(LEMAS)
    assert out1["stats"] == out2["stats"]
    assert out2["files"][0]["new_facts"] == 0 and out2["files"][0]["errors"] == 0
    s = WikiStore(db)
    assert s.get_page("lemma:wasi")["version"] == 1            # recargar sin cambios no sube version
    assert s.get_page("lemma:wasi")["facts"][0]["created_by"] == "seed"
    assert (tmp_path / "pages" / "lemma" / "wasi.md").is_file()  # termina con render_all
    assert bootstrap(tmp_path / "vacia.db", tmp_path / "no-hay-semillas", verbose=False)["stats"]["pages"]["total"] == 0


def test_bootstrap_preserves_feedback_and_retires_old_seed_facts(tmp_path):
    seeds, db = tmp_path / "seed", tmp_path / "wiki.db"
    _write_seeds(seeds)
    bootstrap(db, seeds, verbose=False)
    s = WikiStore(db)
    fid = s.create_feedback(author="ana", direccion="inga2es", correction="vivienda")
    viejo = s.get_page("lemma:wasi")["facts"][0]
    r = s.apply_action({"op": "supersede_fact", "fact_id": viejo["id"], "status": "active",
                        "new_fact": {"section": "meaning", "text": "wasi (s): casa; hogar; vivienda",
                                     "sources": [{"type": "feedback", "ref": f"feedback:{fid}", "quote": "vivienda"}]}}, "rev")
    assert r["ok"]
    bootstrap(db, seeds, verbose=False)
    estados = {f["text"]: f["status"] for f in s.get_page("lemma:wasi", include_inactive=True)["facts"]}
    assert estados["wasi (s): casa; hogar"] == "superseded"           # el hecho corregido no revive
    assert estados["wasi (s): casa; hogar; vivienda"] == "active"
    assert s.get_feedback(fid) is not None
    # la semilla cambia: el hecho de semilla que desaparece se retira, no se borra
    nuevas = [(l, [("s", "luna; mes del calendario")] if l == "killa" else se, a, e) for l, se, a, e in LEMAS]
    (seeds / "lemmas.jsonl").write_text(
        "\n".join(_seed_line(lemma_action(*x)) for x in nuevas) + "\n", encoding="utf-8")
    bootstrap(db, seeds, verbose=False)
    estados = {f["text"]: f["status"] for f in s.get_page("lemma:killa", include_inactive=True)["facts"]}
    assert estados == {"killa (s): luna; mes": "superseded", "killa (s): luna; mes del calendario": "active"}
    # --reset borra tambien el feedback
    out = bootstrap(db, seeds, reset=True, verbose=False)
    assert out["stats"]["feedback"]["total"] == 0 and out["stats"]["facts"]["superseded"] == 0


def test_bootstrap_skips_bad_lines_and_clips_quotes(tmp_path):
    seeds, db = tmp_path / "seed", tmp_path / "wiki.db"
    larga = {"id": "grammar:orden-sov", "kind": "grammar", "slug": "orden-sov", "title": "Orden SOV",
             "summary": "x" * 350,
             "facts": [{"section": "usage", "text": "El verbo va al final.",
                        "sources": [{"type": "grammar", "ref": "levinsohn:L10-L20", "quote": "q" * 500}]},
                       {"section": "usage", "text": "hecho sin fuente", "sources": []}]}
    _write_seeds(seeds, extra_lines=["{json roto", json.dumps(larga),
                                     json.dumps({"id": "poema:x", "kind": "poema", "slug": "x", "title": "x"})])
    out = bootstrap(db, seeds, verbose=False)
    res = out["files"][0]
    assert out["stats"]["pages"]["grammar"] == 1 and res["errors"] == 1
    assert any("JSON invalido" in w for w in res["warnings"]) and any("hecho saltado" in w for w in res["warnings"])
    p = WikiStore(db).get_page("grammar:orden-sov")
    assert len(p["summary"]) <= 300 and len(p["facts"]) == 1 and len(p["facts"][0]["sources"][0]["quote"]) <= 300


# ------------------------------------------------------------------ funciones puras del generador de lemas
def _build_module():
    spec = importlib.util.spec_from_file_location("build_wiki_lemmas", REPO_ROOT / "scripts" / "build_wiki_lemmas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_lemmas_rules():
    b = _build_module()
    filas = [
        {"lema": "achijai", "cat": "v.i.", "glosa": "estornudar (AP, achijii - Yun, jachii - Mocoa)"},
        {"lema": "jachii", "cat": "v.i.", "glosa": "estornudar (Mocoa, véase achijai)"},
        {"lema": "tukui", "cat": "adj", "glosa": "todo; todos"},
        {"lema": "tukui", "cat": "v.i.", "glosa": "llegar a ser; pretender ser; resultar; hacerse"},
        {"lema": "Achalai", "cat": "interj", "glosa": "¡Que bonito! (también Chalai)"},
        {"lema": "agchaiai", "cat": "v.i.", "glosa": "llegar a tener pelo (también agcha wiñai)"},
        {"lema": "samai pagta", "cat": "s", "glosa": "médico tradicional (véase sinchi)"},
        {"lema": "sinchi", "cat": "s", "glosa": "médico tradicional; curandero; brujo (véanse samai pagta, iacha)"},
        {"lema": "kusma", "cat": "s", "glosa": "túnica del varón indígena"},
        {"lema": "irkiai", "cat": "v.i.", "glosa": "empalidecerse; turbarse"},
        {"lema": "lluspichii", "cat": "v.t.", "glosa": "despajar"},
        {"lema": "zapato", "cat": "s", "glosa": "relleno para que la senal por letras tenga contraste"},
    ]
    es = [
        {"lema": "brujo", "cat": "s", "glosa": "millaipa iacha, samai pagta, sinchi"},
        {"lema": "kusma turbarse", "cat": "v.i.", "glosa": "irkiai"},
        {"lema": "despajar", "cat": "v.t.", "glosa": "Iluspichii"},
        {"lema": "estornudar", "cat": "v.i.", "glosa": "achijai/achijii/jachii"},
        {"lema": "desconocido", "cat": "s", "glosa": "palabra ausente"},
    ]
    for r in filas + es:
        r["text"] = f"{r['lema']} ({r['cat']}): {r['glosa']}"
    corte, rep = b.find_boundary(filas[:-1] + es)
    assert corte == len(filas) - 1 and rep["n_es"] == len(es)

    pages = b.build_pages(filas[:-1])
    notas = b.add_notes(pages)
    cnt, sin_destino = b.attach_es_rows(pages, es)
    out, _ = b.finalize(pages)
    por_id = {p["id"]: p for p in out}

    assert len(por_id["lemma:tukui"]["facts"]) == 2                       # homografos: una pagina, dos hechos
    assert "lemma:samai-pagta" in por_id                                  # lema de varias palabras
    assert not any(pid.startswith("lemma:brujo") for pid in por_id)       # lema espanol: sin pagina propia
    sinchi = [f["text"] for f in por_id["lemma:sinchi"]["facts"]]
    assert "brujo (s): millaipa iacha, samai pagta, sinchi [entrada espanol-inga del diccionario]" in sinchi
    assert any(t.startswith("Remisiones del diccionario desde sinchi") and "[lemma:samai-pagta]" in t for t in sinchi)
    ach = por_id["lemma:achijai"]
    assert "achijii" in ach["aliases"]                 # variante ortografica clara -> alias
    assert "jachii" not in ach["aliases"]              # tiene pagina propia: no se secuestra como alias
    assert any(f["section"] == "note" and "(AP, achijii - Yun, jachii - Mocoa)" in f["text"]
               and "Yun = Yunguillo" in f["text"] for f in ach["facts"])
    assert "Chalai" in por_id["lemma:achalai"]["aliases"]
    assert "agcha wiñai" not in por_id["lemma:agchaiai"]["aliases"]      # sinonimo, no grafia
    irkiai = [f for f in por_id["lemma:irkiai"]["facts"] if "entrada espanol-inga" in f["text"]]
    assert irkiai[0]["text"].startswith("turbarse (v.i.): irkiai")       # lema limpiado del salto de linea OCR
    assert irkiai[0]["sources"][0]["quote"] == "kusma turbarse (v.i.): irkiai"   # la cita conserva la fila literal
    assert any("despajar" in f["text"] for f in por_id["lemma:lluspichii"]["facts"])  # OCR Il -> ll
    assert [r["lema"] for r in sin_destino] == ["desconocido"] and cnt["es_sin_destino"] == 1
    for p in out:                                                        # todo hecho cita su fila
        for f in p["facts"]:
            assert f["sources"] and all(s["quote"] and s["ref"].startswith("lema:") for s in f["sources"])
            assert len(f["text"]) <= 400 and all(len(s["quote"]) <= 300 for s in f["sources"])
    assert notas["note_dialectal"] >= 2


def test_real_seed_file_is_valid_if_present():
    path = REPO_ROOT / "datos" / "wiki" / "seed" / "lemmas.jsonl"
    if not path.exists():
        import pytest
        pytest.skip("aun no se ha generado lemmas.jsonl")
    from src.wiki.validation import validate_fact, validate_page
    n = 0
    ids = set()
    with path.open(encoding="utf-8") as fh:
        for linea in fh:
            p = json.loads(linea)
            validate_page(p)
            assert p["id"] not in ids and p["facts"]
            ids.add(p["id"])
            for f in p["facts"]:
                validate_fact(f)
                assert all(s["type"] == "dictionary" for s in f["sources"])
            n += 1
    assert n > 3000 and "lemma:tukui" in ids and "lemma:sinchi" in ids


def test_md_parser_recovers_senses_and_is_conservative(tmp_path, monkeypatch):
    b = _build_module()
    md = tmp_path / "dicc.md"
    md.write_text("\n".join([
        "Diccionario Inga-Español", "",
        "sinchi adj, adv duro; fuerte(mente) (véanse fuirti, kaugsa)",
        "Sinchimi samurkanchi.", "Venimos a marchas forzadas.", "",
        "sinchi s médico tradicional; curandero", "",
        "alli maki adj que tiene buena mano para las", "siembras, para curar, etc. (también suma", "maki)", "",
        "killa s luna; mes (véase wawa killa)", "iskai killa dos meses", "",
        "masa adv rel cuanto(s) (véase machka)", "",
        "kakudur/-a s partera (también kakug)", "",
        "Ilugsii v.i. salir", "",
        "nukanchi pron poses nuestro (también", "", "nukanchipa - Sant)", "",
        "zapato s esto no es inga", "Una oracion de ejemplo s con mayuscula y e.", "",
        "Español - Inga", "", "abajo adv urapi",
    ]), encoding="utf-8")
    monkeypatch.setattr(b, "DICC_MD", md)
    ent = {(e["lema"], e["cat"]): e for e in b.parse_md_entries({"killa", "iskai", "maki", "alli"})}
    assert set(ent) == {("sinchi", "adj, adv"), ("sinchi", "s"), ("alli maki", "adj"), ("killa", "s"),
                        ("masa", "adv, rel"), ("kakudur", "s"), ("llugsii", "v.i."), ("nukanchi", "pron, poses")}
    assert ent[("alli maki", "adj")]["glosa"].endswith("(también suma maki)")       # glosa partida por el OCR
    assert ent[("killa", "s")]["glosa"] == "luna; mes (véase wawa killa)"            # la frase de ejemplo queda fuera
    assert ent[("kakudur", "s")]["formas"] == ["kakudur", "kakudura"]
    assert ent[("nukanchi", "pron, poses")]["glosa"] == "nuestro (también nukanchipa - Sant)"
    assert ent[("sinchi", "adj, adv")]["text"] == "sinchi adj, adv duro; fuerte(mente) (véanse fuirti, kaugsa)"

    tabla = [{"lema": "sinchi", "cat": "s", "glosa": "médico tradicional; curandero", "text": "sinchi (s): médico tradicional; curandero"},
             {"lema": "alli maki", "cat": "adj", "glosa": "que tiene buena mano para las", "text": "alli maki (adj): que tiene buena mano para las"},
             {"lema": b.fix_ocr_lema("Ilugsii"), "cat": "v.i.", "glosa": "salir", "text": "Ilugsii (v.i.): salir"}]
    todas, c, nuevos = b.merge_md_entries(tabla, list(ent.values()))
    assert c["sentidos_nuevos"] == 1 and c["glosas_extendidas"] == 1 and c["lemas_nuevos"] == 4
    pages = b.build_pages(todas)
    sinchi = [f["text"] for f in pages["sinchi"]["facts"]]
    assert "sinchi (adj, adv): duro; fuerte(mente) (véanse fuirti, kaugsa)" in sinchi and len(sinchi) == 2
    assert "llugsii" in pages and "ilugsii" not in pages                           # errata OCR Il -> ll
    assert pages["llugsii"]["facts"][0]["sources"][0]["quote"] == "Ilugsii (v.i.): salir"   # la cita sigue literal
    assert pages["alli-maki"]["facts"][0]["text"].endswith("(también suma maki)")


def test_bootstrap_retires_seed_pages_that_left_the_seed(tmp_path):
    seeds, db = tmp_path / "seed", tmp_path / "wiki.db"
    _write_seeds(seeds)
    bootstrap(db, seeds, verbose=False)
    s = WikiStore(db)
    s.apply_action({"op": "add_fact", "page_id": "lemma:runa", "status": "active",
                    "fact": {"section": "note", "text": "nota humana",
                             "sources": [{"type": "corpus", "ref": "Juan 1:1", "quote": "runa"}]}}, "ana")
    quedan = [x for x in LEMAS if x[0] not in ("killa", "runa")]
    (seeds / "lemmas.jsonl").write_text(
        "\n".join(_seed_line(lemma_action(*x)) for x in quedan) + "\n", encoding="utf-8")
    bootstrap(db, seeds, verbose=False)
    assert s.get_page("lemma:killa")["status"] == "superseded"          # retirada, no borrada
    assert s.get_page("lemma:killa", include_inactive=True)["facts"]
    assert s.get_page("lemma:runa")["status"] == "active"               # tiene un hecho que no es de semilla
    assert "lemma:killa" not in [p["id"] for p in s.find_pages("killa")]
    assert not (tmp_path / "pages" / "lemma" / "killa.md").exists()
    _write_seeds(seeds)
    bootstrap(db, seeds, verbose=False)
    assert s.get_page("lemma:killa")["status"] == "active"              # vuelve con la semilla
    assert (tmp_path / "pages" / "lemma" / "killa.md").is_file()
