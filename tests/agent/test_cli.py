"""inga_cli: gramatica, registro, esquemas y la regla de corroboracion en el camino de escritura."""
from __future__ import annotations

import json

import pytest

from src.agent.cli.parser import CliError, parse
from src.agent.cli.resources import CliContext, build_registry


# --- parser -----------------------------------------------------------------------

def test_parse_gramatica_completa():
    assert parse("list-resources").verb == "list-resources"
    assert parse("help").resource is None and parse("help Wiki").resource == "Wiki"
    c = parse("resource Wiki list-actions")
    assert (c.verb, c.resource) == ("list-actions", "Wiki")
    for cmd in ("resource Wiki get-schema --action add-fact", "resource Wiki get-schema --action=add-fact"):
        c = parse(cmd)
        assert (c.verb, c.resource, c.action) == ("get-schema", "Wiki", "add-fact")
    for cmd in ("resource Wiki execute-action no-change --input '{\"reason\": \"x y\"}'",
                "resource Wiki execute-action no-change --input='{\"reason\": \"x y\"}'",
                "inga_cli resource Wiki execute-action no-change --input '{\"reason\": \"x y\"}'"):
        c = parse(cmd)
        assert (c.verb, c.action, c.input) == ("execute-action", "no-change", {"reason": "x y"})
    assert parse("resource Feedback execute-action get").input == {}


def test_parse_json_con_apostrofo_y_comillas_dobles_exteriores():
    c = parse("resource Wiki execute-action no-change --input '{\"reason\": \"ri 'fue' no aplica\"}'")
    assert c.input == {"reason": "ri 'fue' no aplica"}
    c = parse('resource Wiki execute-action no-change --input "{"reason": "texto largo"}"')
    assert c.input == {"reason": "texto largo"}


@pytest.mark.parametrize("cmd,pista", [
    ("", "comando vacio"), ("borrar todo", "comando desconocido"), ("resource Wiki", "faltan argumentos"),
    ("resource Wiki destroy", "subcomando desconocido"), ("resource Wiki get-schema", "--action"),
    ("resource Wiki get-schema --accion x", "opcion desconocida"),
    ("resource Wiki execute-action --input '{}'", "un solo nombre de accion"),
    ("resource Wiki execute-action add-fact --input '{roto'", "no es JSON valido"),
    ("resource Wiki execute-action add-fact --input '[1]'", "objeto JSON"),
    ("resource Wiki execute-action add-fact --input", "necesita un valor"),
    ("list-resources ya", "no lleva argumentos"),
])
def test_parse_errores_accionables(cmd, pista):
    with pytest.raises(CliError) as e:
        parse(cmd)
    assert str(e.value).startswith("Error:") and pista in str(e.value)


# --- registro ---------------------------------------------------------------------

@pytest.fixture
def cli(store):
    fid = store.create_feedback(author="ana", direccion="inga2es", source_text="sinchi tuku",
                                model_output="todo fuerte", correction="hacerse fuerte", comment="")
    ctx = CliContext(store=store, feedback_id=fid, actor="agent:test")
    return build_registry(ctx), ctx, fid


def _exec(reg, resource: str, action: str, data: dict) -> str:
    return reg.run(f"resource {resource} execute-action {action} --input '{json.dumps(data)}'")


def test_descubrimiento(cli):
    reg, _, _ = cli
    assert reg.run("list-resources").splitlines() == [
        "Wiki: paginas y hechos citados de la wiki inga", "Feedback: correcciones enviadas por usuarios"]
    acciones = reg.run("resource Wiki list-actions")
    for a in ("upsert-page", "add-fact", "supersede-fact", "no-change", "get-page", "find-pages"):
        assert a in acciones
    assert "get (read)" in reg.run("resource Feedback list-actions")
    desc = reg.describe()
    assert "Wiki" in desc and "Feedback" in desc and "execute-action" in desc  # la descripcion basta para arrancar
    assert "add-fact" in reg.run("help Wiki") and "Recursos" in reg.run("help")


def test_get_schema_es_json_schema_cerrado(cli):
    reg, _, _ = cli
    schema = json.loads(reg.run("resource Wiki get-schema --action add-fact"))
    assert schema["additionalProperties"] is False and set(schema["required"]) == {"page_id", "fact"}
    assert schema["$defs"]["FactIn"]["additionalProperties"] is False
    assert json.loads(reg.run("resource Wiki get-schema --action no-change"))["required"] == ["reason"]
    assert reg.run("resource Wiki get-schema --action volar").startswith("Error: la accion 'volar' no existe")
    assert reg.run("resource Biblia list-actions").startswith("Error: recurso desconocido")


def test_validacion_extra_forbid_y_mensaje_accionable(cli):
    reg, ctx, _ = cli
    out = _exec(reg, "Wiki", "add-fact", {"page_id": "lemma:sinchi", "status": "active",
                                          "fact": {"section": "raro", "text": "x"}})
    assert out.startswith("Error: --input no cumple el esquema de Wiki add-fact")
    assert "status: campo no permitido" in out and "fact.section" in out and "get-schema --action add-fact" in out
    assert "te quedan 2 intento(s)" in out and ctx.facts == []
    # una fuente feedback no se acepta del modelo: la pone el codigo
    out = _exec(reg, "Wiki", "add-fact", {"page_id": "lemma:sinchi", "fact": {
        "section": "usage", "text": "algo cierto", "sources": [{"type": "feedback", "ref": "feedback:1", "quote": "yo"}]}})
    assert out.startswith("Error") and "sources.0.type" in out


def test_maximo_dos_reintentos_por_comando(cli):
    reg, _, _ = cli
    malo = "resource Wiki execute-action add-fact --input '{}'"
    assert "te quedan 2" in reg.run(malo)
    assert "te quedan 1" in reg.run(malo)
    assert "Sin reintentos" in reg.run(malo)
    assert "limite de 2 reintentos" in reg.run(malo)
    # otros comandos siguen funcionando
    assert reg.run("resource Wiki list-actions").startswith("upsert-page") or "add-fact" in reg.run("resource Wiki list-actions")


def test_lecturas(cli):
    reg, _, fid = cli
    page = json.loads(_exec(reg, "Wiki", "get-page", {"page_id": "wiki/lemma/tukui.md"}))
    assert page["id"] == "lemma:tukui" and len(page["facts"]) == 2
    assert _exec(reg, "Wiki", "get-page", {"page_id": "lemma:nada"}).startswith("Error: la pagina lemma:nada no existe")
    found = json.loads(_exec(reg, "Wiki", "find-pages", {"query": "ngapa", "kind": "suffix"}))
    assert [p["id"] for p in found["pages"]] == ["suffix:ngapa"]
    fb = json.loads(reg.run("resource Feedback execute-action get"))
    assert fb["id"] == fid and fb["correction"] == "hacerse fuerte" and "triage_json" not in fb
    assert len(json.loads(_exec(reg, "Feedback", "list", {"status": "new"}))["feedback"]) == 1


# --- regla de corroboracion en el camino de escritura ---------------------------------

FACT = {"section": "usage", "text": "sinchi tukui: hacerse fuerte."}
SRC_OK = {"type": "dictionary", "ref": "lema:sinchiai", "quote": "ponerse fuerte"}
SRC_MALA = {"type": "dictionary", "ref": "lema:inventadu", "quote": "hacerse fuerte"}


def _fact_en_store(store, fact_id):
    return [f for f in store.get_page("lemma:sinchi", include_inactive=True)["facts"] if f["id"] == fact_id][0]


def test_fuente_verificada_deja_el_hecho_activo_y_cita_feedback(cli, store):
    reg, ctx, fid = cli
    out = json.loads(_exec(reg, "Wiki", "add-fact", {"page_id": "lemma:sinchi", "fact": {**FACT, "sources": [SRC_OK]}}))
    assert out["ok"] and out["status"] == "active"
    f = _fact_en_store(store, out["fact_ids"][0])
    assert f["status"] == "active"
    assert [(s["type"], s["ref"]) for s in f["sources"]] == [("dictionary", "lema:sinchiai"), ("feedback", f"feedback:{fid}")]
    assert ctx.facts == [{"fact_id": f["id"], "page_id": "lemma:sinchi", "text": FACT["text"], "status": "active"}]
    assert ctx.evidence[0]["verified"] is True


def test_sin_fuentes_queda_pendiente(cli, store):
    reg, ctx, fid = cli
    out = json.loads(_exec(reg, "Wiki", "add-fact", {"page_id": "lemma:sinchi", "fact": {**FACT, "sources": []}}))
    assert out["status"] == "pending" and "pendiente" in out["nota"]
    f = _fact_en_store(store, out["fact_ids"][0])
    assert f["status"] == "pending" and [s["ref"] for s in f["sources"]] == [f"feedback:{fid}"]


def test_fuente_inventada_primero_error_y_al_tercer_intento_pendiente(cli, store):
    reg, ctx, fid = cli
    data = {"page_id": "lemma:sinchi", "fact": {**FACT, "sources": [SRC_MALA]}}
    for _ in range(2):
        out = _exec(reg, "Wiki", "add-fact", data)
        assert out.startswith("Error: ninguna fuente pudo verificarse") and "lema:inventadu" in out
        assert '"sources": []' in out and store.actions == []
    out = json.loads(_exec(reg, "Wiki", "add-fact", data))
    assert out["status"] == "pending" and out["fuentes_descartadas"][0]["ref"] == "lema:inventadu"
    f = _fact_en_store(store, out["fact_ids"][0])
    assert [s["type"] for s in f["sources"]] == ["feedback"]  # la cita inventada nunca llega a la wiki
    assert ctx.evidence[0]["verified"] is False


def test_mezcla_de_fuentes_conserva_solo_las_verificadas(cli, store):
    reg, _, _ = cli
    out = json.loads(_exec(reg, "Wiki", "add-fact", {"page_id": "lemma:sinchi",
                                                     "fact": {**FACT, "sources": [SRC_MALA, SRC_OK]}}))
    assert out["status"] == "active" and [m["ref"] for m in out["fuentes_descartadas"]] == ["lema:inventadu"]
    refs = [s["ref"] for s in _fact_en_store(store, out["fact_ids"][0])["sources"]]
    assert "lema:inventadu" not in refs and "lema:sinchiai" in refs


def test_supersede_y_upsert(cli, store):
    reg, ctx, _ = cli
    viejo = store.get_page("lemma:tukui")["facts"][1]["id"]
    out = json.loads(_exec(reg, "Wiki", "supersede-fact", {"fact_id": viejo, "new_fact": {
        "section": "meaning", "text": "tukui (adj): todo; todos", "sources": []}}))
    estados = {f["id"]: f["status"] for f in store.get_page("lemma:tukui", include_inactive=True)["facts"]}
    assert estados[viejo] == "active" and estados[out["fact_ids"][0]] == "pending"

    existe = _exec(reg, "Wiki", "upsert-page", {"kind": "lemma", "slug": "sinchi", "title": "PISADO",
                                                "facts": [{**FACT, "sources": [SRC_OK]}]})
    assert existe.startswith("Error: la pagina lemma:sinchi ya existe") and store.get_page("lemma:sinchi")["title"] == "sinchi"
    nueva = json.loads(_exec(reg, "Wiki", "upsert-page", {
        "kind": "case", "slug": "sinchi-tukui", "title": "sinchi tukui", "summary": "hacerse fuerte",
        "facts": [{**FACT, "sources": [SRC_OK]}, {"section": "note", "text": "Visto en feedback.", "sources": []}]}))
    assert nueva["status"] == ["active", "pending"]
    assert (store.pages_root / "case" / "sinchi-tukui.md").is_file()
    assert _exec(reg, "Wiki", "upsert-page", {"kind": "lemma", "slug": "Con Espacio", "title": "x",
                                              "facts": [FACT]}).startswith("Error")


def test_no_change_exige_motivo_y_no_escribe(cli, store):
    reg, ctx, _ = cli
    assert _exec(reg, "Wiki", "no-change", {}).startswith("Error") and ctx.no_change == []
    assert _exec(reg, "Wiki", "no-change", {"reason": "corto"}).startswith("Error")
    out = json.loads(_exec(reg, "Wiki", "no-change", {"reason": "El diccionario dice claramente otra cosa.",
                                                      "evidence": [SRC_OK]}))
    assert out["ok"] and ctx.no_change == ["El diccionario dice claramente otra cosa."]
    assert store.actions == [] and ctx.evidence[0]["verified"] is True


def test_no_existen_acciones_de_aprobacion_ni_borrado(cli):
    reg, _, _ = cli
    for a in ("approve-fact", "reject-fact", "delete-page", "approve_fact"):
        assert _exec(reg, "Wiki", a, {"fact_id": "f_00000001"}).startswith("Error: la accion")
