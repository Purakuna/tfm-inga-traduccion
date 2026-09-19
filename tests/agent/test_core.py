"""translate / ask con Gemini guionizado: eventos, bucle de herramientas y traza."""
from __future__ import annotations

import json

from conftest import by_type, resp_calls, resp_text

from src.agent import core

FINAL = json.dumps({"translation": "Para tener mucho, hazte fuerte para pensar.", "alternatives": [],
                    "confidence": "medium", "notes": "Apoyado en lemma:sinchi.",
                    "used_pages": ["lemma:sinchi", "lemma:inventada"]})


def test_translate_fast_eventos_y_traza(store, script):
    fake = script([resp_text(FINAL)])
    evs = list(core.translate("Achka iukangapa, sinchi tuku.", "inga2es", "fast", store=store))
    tipos = [e["event"] for e in evs]
    assert tipos[-1] == "done" and tipos.count("done") == 1
    assert [t for t in tipos if t != "status"] == ["navigation", "pages", "examples", "result", "done"]
    assert {e["data"]["stage"] for e in evs if e["event"] == "status"} >= {"normalize", "navigate", "retrieve", "think", "write"}

    res = by_type(evs, "result")[0]
    assert set(res) == {"translation_id", "translation", "alternatives", "confidence", "notes",
                        "used_pages", "mode", "elapsed_s"}
    assert res["mode"] == "fast" and res["used_pages"] == ["lemma:sinchi"]  # la inventada se descarta
    assert len(fake.calls) == 1 and fake.calls[0][1].tools is None

    nav = by_type(evs, "navigation")[0]
    assert set(nav["tokens"][0]) == {"token", "normalized", "lemma_pages", "suffix_pages", "resolved"}
    pages = by_type(evs, "pages")[0]["pages"]
    assert pages[0]["id"] == "lemma:sinchi" and pages[-1]["id"] == "suffix:ngapa"  # lemas antes que sufijos

    saved = store.get_translation(res["translation_id"])
    trace = json.loads(saved["trace_json"])
    assert saved["output"] == res["translation"] and saved["mode"] == "fast"
    assert set(trace) >= {"navigation", "pages", "pages_markdown", "examples", "tool_calls", "final"}


def test_translate_save_false_no_escribe(store, script):
    script([resp_text(FINAL)])
    evs = list(core.translate("sinchi", "inga2es", "fast", store=store, save=False))
    assert by_type(evs, "result") and store.translations == {}


def test_translate_agent_llamadas_paralelas_y_firmas(store, script):
    fake = script([
        resp_calls(("fs_leer", {"ruta": "wiki/lemma/wasi.md"}), ("fs_grep", {"patron": "tuku"})),
        resp_text(FINAL),
    ])
    evs = list(core.translate("sinchi tuku", "inga2es", "agent", store=store))
    calls, results = by_type(evs, "tool_call"), by_type(evs, "tool_result")
    assert [c["id"] for c in calls] == [1, 2] and [r["id"] for r in results] == [1, 2]
    assert calls[0] == {"id": 1, "name": "fs_leer", "args": {"ruta": "wiki/lemma/wasi.md"}}
    assert set(results[0]) == {"id", "name", "summary", "chars"}

    # Segundo turno: el contenido del modelo vuelve intacto (con su firma) y las dos
    # respuestas van juntas, con el id de cada llamada.
    contents = fake.calls[1][0]
    assert contents[1].role == "model" and contents[1].parts[0].thought_signature == b"firma"
    frs = [p.function_response for p in contents[2].parts]
    assert [f.id for f in frs] == ["call_0", "call_1"] and "casa" in frs[0].response["result"]

    trace = json.loads(store.get_translation(by_type(evs, "result")[0]["translation_id"])["trace_json"])
    assert [c["name"] for c in trace["tool_calls"]] == ["fs_leer", "fs_grep"]


def test_translate_agent_freno_de_seguridad(store, script, monkeypatch):
    # No hay presupuesto de trabajo; el tope solo es un freno contra bucles. Aqui se baja para probarlo.
    monkeypatch.setattr(core, "MAX_TOOL_CALLS", 6)
    cuatro = [("fs_grep", {"patron": f"q{i}"}) for i in range(4)]
    fake = script([resp_calls(*cuatro), resp_calls(*cuatro), resp_text(FINAL)])
    evs = list(core.translate("sinchi", "inga2es", "agent", store=store))
    assert len(by_type(evs, "tool_call")) == core.MAX_TOOL_CALLS
    # Las llamadas sobrantes reciben respuesta (el historial queda valido) pero no se ejecutan.
    frs = [p.function_response.response["result"] for p in fake.calls[2][0][-1].parts]
    assert len(frs) == 4 and sum("Tope de seguridad" in r for r in frs) == 2
    assert by_type(evs, "result")


def test_translate_errores_terminan_en_done(store, script):
    script([])
    for args in (("", "inga2es", "fast"), ("hola", "fr2es", "fast"), ("hola", "inga2es", "turbo"),
                 ("hola", "inga2es", "fast")):  # el ultimo: el LLM falla
        evs = list(core.translate(*args, store=store))
        assert [e["event"] for e in evs][-2:] == ["error", "done"]
        assert by_type(evs, "error")[0]["message"]


def test_translate_turno_vacio_pide_cierre(store, script):
    fake = script([resp_text(""), resp_text(FINAL)])
    evs = list(core.translate("sinchi", "inga2es", "agent", store=store))
    assert by_type(evs, "result") and len(fake.calls) == 2


def test_ask_streaming_y_paginas_citadas(store, script):
    script([resp_text(FINAL)])
    tid = by_type(list(core.translate("sinchi tuku", "inga2es", "fast", store=store)), "result")[0]["translation_id"]

    fake = script([
        resp_calls(("fs_leer", {"ruta": "wiki/lemma/tukui.md"})),
        resp_text("Segun la traza, [lemma:sinchi] registra 'fuerte' y [lemma:tukui] 'llegar a ser'. "
                  "[lemma:fantasma] no existe."),
    ])
    evs = list(core.ask(tid, "por que sinchi tuku?", [{"role": "user", "content": "hola"},
                                                      {"role": "assistant", "content": "dime"}], store=store))
    deltas = "".join(d["text"] for d in by_type(evs, "answer_delta"))
    ans = by_type(evs, "answer")[0]
    assert ans["text"] == deltas.strip()
    assert ans["cited_pages"] == ["lemma:sinchi", "lemma:tukui"]
    assert len(by_type(evs, "tool_call")) == 1 and evs[-1]["event"] == "done"
    # la traza y el historial llegan al modelo
    primer = fake.calls[0][0]
    assert "TRAZA DE LA TRADUCCION" in primer[0].parts[0].text
    assert [c.role for c in primer] == ["user", "model", "user", "model", "user"]


def test_ask_traduccion_inexistente(store, script):
    script([])
    evs = list(core.ask("noexiste", "por que?", store=store))
    assert [e["event"] for e in evs] == ["error", "done"]


def test_translate_agent_tope_de_turnos(store, script):
    una = [("fs_grep", {"patron": "q"})]
    fake = script([resp_calls(*una), resp_calls(*una), resp_text(FINAL)])
    evs = list(core.translate("sinchi", "inga2es", "agent", store=store))
    assert len(by_type(evs, "tool_call")) == 2 and by_type(evs, "result")
    # tras 2 turnos con herramientas la tercera llamada al modelo ya no puede pedir mas
    assert len(fake.calls) == 3


def test_translate_agent_pagina_leida_por_fs_cuenta_como_usada_y_nunca_hay_cli(store, script):
    final = json.dumps({"translation": "casa", "confidence": "high", "notes": "", "used_pages": ["lemma:wasi"]})
    fake = script([resp_calls(("fs_leer", {"ruta": "wiki/lemma/wasi.md"}),
                              ("inga_cli", {"cmd": "resource Wiki execute-action no-change --input '{}'"})),
                   resp_text(final)])
    evs = list(core.translate("sinchi", "inga2es", "agent", store=store))
    assert by_type(evs, "result")[0]["used_pages"] == ["lemma:wasi"]
    # inga_cli no se declara en translate y, si el modelo la inventa, no se ejecuta
    frs = [p.function_response.response["result"] for p in fake.calls[1][0][-1].parts]
    assert frs[1].startswith("Error: herramienta desconocida") and store.actions == []
    prompt = fake.calls[0][0][0].parts[0].text
    # La pagina ya no va completa: va su pista con el id, y el sistema explica id -> archivo.
    assert "[lemma:sinchi]" in prompt and "Pistas de la wiki" in prompt
