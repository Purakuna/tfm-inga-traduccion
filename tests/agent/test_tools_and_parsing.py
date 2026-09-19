"""Herramientas, parseo tolerante del JSON final y seleccion de paginas."""
from __future__ import annotations

from src.agent import core, tools


# --- sistema de archivos de solo lectura (seccion 8.2) ---

import os

import pytest

from src.agent.fs import FsError, VirtualFS


def test_fs_ls_montajes_y_carpetas(store):
    tb = tools.Toolbox(store)
    assert "wiki/" in tb.fs_ls("") and "fuentes/" in tb.fs_ls("")
    fuentes = tb.fs_ls("fuentes/")
    assert all(n in fuentes for n in ("diccionario.md", "gramatica.md", "rosetta.md"))
    lemas = tb.fs_ls("wiki/lemma").splitlines()
    assert lemas[1] == "index.md" and "sinchi.md" in lemas  # el indice primero
    assert "lemma/" in tb.fs_ls("wiki/")


def test_fs_ls_recorta_carpetas_grandes(tmp_path):
    (tmp_path / "lemma").mkdir()
    for i in range(200):
        (tmp_path / "lemma" / f"p{i:03}.md").write_text("x")
    out = VirtualFS(tmp_path).ls("wiki/lemma")
    assert "140 mas" in out and "fs_grep" in out and len(out) <= 2500


def test_fs_leer_pagina_con_ids_de_hecho_y_registro(store):
    tb = tools.Toolbox(store)
    out = tb.fs_leer("wiki/lemma/tukui.md")
    assert out.startswith("wiki/lemma/tukui.md lineas 1-")
    assert "- [f_0000000" in out and "fuente: dictionary lema:tukui" in out
    assert tb.pages_read == ["lemma:tukui"]


def test_fs_leer_fuentes_numeradas_y_limites(store):
    tb = tools.Toolbox(store)
    out = tb.fs_leer("fuentes/gramatica.md", 477, 5)
    assert out.startswith("fuentes/gramatica.md lineas 477-481 de") and "sigue con linea=482" in out
    assert "479: -ngapa se realiza" in out
    assert len(tb.fs_leer("fuentes/diccionario.md", 1, 5000)) <= 4000 + 400
    assert tb.call("fs_leer", {"ruta": "fuentes/gramatica.md", "linea": 10 ** 7}).startswith("Error")
    assert tb.call("fs_leer", {"ruta": "fuentes/gramatica.md", "linea": "x"}).startswith("Error")
    assert tb.call("fs_leer", {"ruta": "wiki/lemma"}).startswith("Error")


@pytest.mark.parametrize("ruta", ["/etc/passwd", "../secreto", "wiki/../../etc/passwd", "wiki/lemma/../../x",
                                  "~/.ssh/id_rsa", "wiki\\lemma", "C:/x", "otro/x.md", "fuentes/otro.md",
                                  "fuentes/../wiki", "wiki/lemma/nada.md"])
def test_fs_rechaza_rutas_peligrosas(store, ruta):
    tb = tools.Toolbox(store)
    for nombre in ("fs_leer", "fs_ls"):
        assert tb.call(nombre, {"ruta": ruta}).startswith("Error"), (nombre, ruta)
    assert tb.call("fs_grep", {"patron": "a", "ruta": ruta}).startswith("Error")


def test_fs_no_sigue_symlinks(store, tmp_path):
    secreto = tmp_path / "secreto.md"
    secreto.write_text("clave sinchi secreta")
    os.symlink(secreto, store.pages_root / "lemma" / "enlace.md")
    os.symlink(tmp_path, store.pages_root / "fuera")
    fs = VirtualFS(store.pages_root)
    for ruta in ("wiki/lemma/enlace.md", "wiki/fuera", "wiki/fuera/secreto.md"):
        with pytest.raises(FsError):
            fs.leer(ruta)
    assert "enlace.md" not in fs.ls("wiki/lemma") and "fuera" not in fs.ls("wiki/")
    assert "secreta" not in fs.grep("sinchi", "wiki/")


def test_fs_no_hay_escritura(store):
    tb = tools.Toolbox(store)
    assert not [n for n in tb.names if "escrib" in n or "write" in n]
    assert tools.CLI_TOOL not in tb.names  # sin cli, solo lectura
    assert tb.call("inga_cli", {"cmd": "list-resources"}).startswith("Error: herramienta desconocida")


def test_fs_grep_wiki_pliega_acentos_y_prioriza_la_pagina(store):
    out = tools.Toolbox(store).fs_grep("SÍNCHI")
    lineas = out.splitlines()
    assert "coinciden" in lineas[0]
    assert lineas[1].startswith("wiki/lemma/sinchi.md:") and "[f_" in lineas[1]
    assert not any(":id: " in l or "title:" in l for l in lineas)  # sin ruido de front matter
    assert all(l.count(":") >= 2 for l in lineas[1:])


def test_fs_grep_diccionario_entrada_primero_y_regex():
    fs = VirtualFS()
    out = fs.grep("sinchiai", "fuentes/diccionario.md", 3).splitlines()
    assert out[1].startswith("fuentes/diccionario.md:9588:sinchiai v.i. ponerse fuerte")
    assert "fuentes/gramatica.md:479:" in fs.grep("^-ngapa se", "fuentes/gramatica.md")
    # un patron con parentesis que como regex no da nada se reintenta literal
    assert "fuerte(mente)" in fs.grep("fuerte(mente)", "fuentes/diccionario.md")
    assert fs.grep("zzzxqj", "fuentes/").startswith("Sin coincidencias")
    assert len(fs.grep("a", "fuentes/gramatica.md", 60)) <= 2500
    with pytest.raises(FsError):
        fs.grep("  ", "fuentes/")


def test_corpus_buscar_valida_direccion():
    assert tools.corpus_buscar("hola", "fr2es").startswith("Error")
    assert tools.corpus_buscar("", "inga2es").startswith("Error")


def test_buscar_por_glosa_da_ruta(store):
    tb = tools.Toolbox(store)
    assert "lemma:wasi | wiki/lemma/wasi.md" in tb.buscar_por_glosa("casa")
    assert tb.buscar_por_glosa("helicoptero").startswith("Ningun")


def test_call_nunca_lanza(store):
    tb = tools.Toolbox(store)
    assert tb.call("wiki_leer", {}).startswith("Error: herramienta desconocida")
    assert tb.call("fs_leer", {"pagina": "x"}).startswith("Error de argumentos")
    assert tb.call("fs_leer", None).startswith("Error de argumentos")


def test_summarize_result():
    s = tools.summarize_result("buscar_por_glosa", {}, "- lemma:a | wiki/lemma/a.md | x\n- lemma:b | wiki/lemma/b.md | y")
    assert s.startswith("2 lemas: lemma:a, lemma:b")
    assert tools.summarize_result("fs_leer", {}, "Error: no existe wiki/x.md.").startswith("Error")
    assert "(1 hechos)" in tools.summarize_result("fs_leer", {}, "wiki/lemma/a.md lineas 1-9 de 9:\n7: - [f_00000001] a")
    cli = tools.summarize_result("inga_cli", {"cmd": "resource Wiki execute-action add-fact --input '{\"a\": 1}'"},
                                 '{\n "ok": true,\n "fact_ids": ["f_1"],\n "status": "pending"\n}')
    assert cli == "resource Wiki execute-action add-fact -> escrito, estado pending"


def test_declaraciones_solo_lectura():
    nombres = [d.name for d in tools.declarations()]
    assert nombres == ["fs_ls", "fs_leer", "fs_grep", "corpus_buscar", "buscar_por_glosa"]
    cli = tools.cli_declaration("desc")
    assert cli.name == "inga_cli" and cli.parameters.required == ["cmd"]


# --- parseo tolerante ---

def test_parse_json_limpio():
    r = core.parse_translation(
        '{"translation": "Para tener mucho", "alternatives": ["a", "b", "c"], "confidence": "HIGH",'
        ' "notes": "n", "used_pages": ["lemma:sinchi", "no-es-id"]}')
    assert r["translation"] == "Para tener mucho"
    assert r["alternatives"] == ["a", "b"]
    assert r["confidence"] == "high"
    assert r["used_pages"] == ["lemma:sinchi"]


def test_parse_json_con_cerca_y_texto_alrededor():
    raw = 'Claro, aqui va:\n```json\n{"translation": "hola", "confidence": "medium",}\n```\nListo.'
    r = core.parse_translation(raw)
    assert r["translation"] == "hola" and r["confidence"] == "medium"


def test_parse_json_truncado_rescata_la_traduccion():
    r = core.parse_translation('{"translation": "Nuka \\"wasi\\" pi kani", "alternatives": ["x')
    assert r["translation"] == 'Nuka "wasi" pi kani'
    assert r["confidence"] == "low"


def test_parse_texto_plano_baja_confianza():
    r = core.parse_translation("Estoy en mi casa.")
    assert r["translation"] == "Estoy en mi casa." and r["confidence"] == "low" and r["notes"]


def test_parse_tipos_raros():
    r = core.parse_translation('{"translation": ["a", "b"], "alternatives": "otra", "confidence": 7, "used_pages": "lemma:x"}')
    assert r == {"translation": "a b", "alternatives": ["otra"], "confidence": "low", "notes": "",
                 "used_pages": ["lemma:x"]}


def test_parse_json_object_lista():
    assert core.parse_json_object('[{"verdict": "supported"}]') == {"verdict": "supported"}
    assert core.parse_json_object("nada") is None


# --- seleccion y carga de paginas ---

def test_select_pages_por_rondas_y_cupo_de_sufijos():
    tokens = [
        {"lemma_pages": [f"lemma:a{i}" for i in range(10)], "suffix_pages": ["suffix:x"]},
        {"lemma_pages": ["lemma:b0", "lemma:b1"], "suffix_pages": ["suffix:y", "suffix:x"]},
    ]
    sel = core.select_pages(tokens)
    assert len(sel) == core.MAX_PAGES
    assert sel[:4] == ["lemma:a0", "lemma:b0", "lemma:a1", "lemma:b1"]
    assert sel[-2:] == ["suffix:x", "suffix:y"]
    assert [p for p in sel if p.startswith("suffix:")] == sel[-2:]


def test_load_pages_respeta_tope_de_caracteres(store):
    meta, md = core.load_pages(store, ["lemma:sinchi", "lemma:nada", "lemma:tukui", "lemma:wasi"], max_chars=200)
    assert [m["id"] for m in meta] == list(md)
    assert "lemma:nada" not in md
    assert 1 <= len(md) < 3
    assert set(meta[0]) == {"id", "kind", "title", "summary"}


def test_load_pages_indica_el_archivo_y_trae_ids_desde_el_arbol(store):
    _, md = core.load_pages(store, ["lemma:tukui"])
    assert md["lemma:tukui"].startswith("[archivo: wiki/lemma/tukui.md]") and "[f_" not in md["lemma:tukui"]
    _, md = core.load_pages(store, ["lemma:tukui"], from_files=True)
    assert "- [f_0000000" in md["lemma:tukui"]


def test_candidate_paths_solo_las_no_cargadas(store):
    tokens = [{"lemma_pages": ["lemma:sinchi", "lemma:tukui"], "suffix_pages": ["suffix:ngapa"]}]
    assert core.candidate_paths(store, tokens, {"lemma:sinchi"}) == {
        "lemma:tukui": "wiki/lemma/tukui.md", "suffix:ngapa": "wiki/suffix/ngapa.md"}
