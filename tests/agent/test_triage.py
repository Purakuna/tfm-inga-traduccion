"""Regla de corroboracion: el codigo, no el LLM, decide si el feedback se aplica solo.

Desde la seccion 8.2 la regla vive en el camino de escritura (inga_cli); aqui se prueba la
verificacion de fuentes y el triage completo con Gemini guionizado.
"""
from __future__ import annotations

import json

import pytest
from conftest import by_type, resp_calls, resp_text

from src.agent import core, verify
from src.agent.review import ReviewError, review_feedback

QUOTE_GRAM = "-ngapa se realiza con las raices verbales, y las modifica en el infinitivo futuro"


def _train_row() -> dict:
    with verify.TRAIN_PATH.open(encoding="utf-8") as fh:
        return json.loads(fh.readline())


# --- verify_source -------------------------------------------------------------

def test_dictionary_lema_en_lexico_y_cita():
    assert verify.verify_source({"type": "dictionary", "ref": "lema:sinchiai", "quote": "ponerse fuerte"})[0]
    assert verify.verify_source({"type": "dictionary", "ref": "lema:Sinchiai", "quote": ""})[0]
    ok, motivo = verify.verify_source({"type": "dictionary", "ref": "lema:sinchiai", "quote": "volar muy alto"})
    assert not ok and "cita" in motivo
    assert not verify.verify_source({"type": "dictionary", "ref": "lema:inventadu", "quote": "x"})[0]


def test_dictionary_lema_solo_en_la_wiki(store):
    assert verify.verify_source({"type": "dictionary", "ref": "lema:wasi", "quote": "casa"}, store)[0]
    assert not verify.verify_source({"type": "dictionary", "ref": "lema:wasi", "quote": "casa"}, None)[0]


def test_grammar_rango_y_cita_aproximada():
    ok, _ = verify.verify_source({"type": "grammar", "ref": "levinsohn:L479-L479", "quote": QUOTE_GRAM})
    assert ok
    # tolera ref sin la segunda L y unas lineas de desfase
    assert verify.verify_source({"type": "grammar", "ref": "levinsohn:L477-481", "quote": QUOTE_GRAM})[0]
    assert not verify.verify_source({"type": "grammar", "ref": "levinsohn:L3000-L3005", "quote": QUOTE_GRAM})[0]
    assert not verify.verify_source({"type": "grammar", "ref": "levinsohn:L479-L479", "quote": ""})[0]
    assert not verify.verify_source({"type": "grammar", "ref": "levinsohn:L999999-L999999", "quote": QUOTE_GRAM})[0]
    assert not verify.verify_source({"type": "grammar", "ref": "levinsohn:L1-L7000", "quote": QUOTE_GRAM})[0]
    assert not verify.verify_source({"type": "grammar", "ref": "cusihuaman:L1-L2", "quote": QUOTE_GRAM})[0]


def test_corpus_versiculo_en_train():
    r = _train_row()
    ref = f"{r['libro']} {r['capitulo']}:{r['versiculo']}"
    assert verify.verify_source({"type": "corpus", "ref": ref, "quote": r["texto_inga"][:60]})[0]
    assert not verify.verify_source({"type": "corpus", "ref": ref, "quote": "zzz qqq xxx www"})[0]
    assert not verify.verify_source({"type": "corpus", "ref": "Genesis 1:1", "quote": ""})[0]
    assert not verify.verify_source({"type": "corpus", "ref": "sin formato", "quote": ""})[0]


def test_feedback_nunca_corrobora():
    evs = verify.verify_evidence([{"type": "feedback", "ref": "feedback:1", "quote": "lo digo yo"},
                                  {"type": "wikipedia", "ref": "x", "quote": "y"}, "basura"])
    assert len(evs) == 2 and not verify.is_corroborated(evs)
    assert verify.normalize_ref("grammar", "Levinsohn: L12 - 15") == "levinsohn:L12-L15"
    assert verify.normalize_ref("dictionary", "sinchi") == "lema:sinchi"


def test_agente_no_lee_val_ni_test():
    from pathlib import Path

    root = Path(verify.__file__).resolve().parent
    fuentes = list(root.glob("*.py")) + list((root.parents[1] / "webapp" / "backend").glob("*.py"))
    assert fuentes
    for f in fuentes:
        texto = f.read_text(encoding="utf-8")
        assert "val.jsonl" not in texto and "test.jsonl" not in texto, f.name


# --- triage_feedback: el veredicto se deriva de lo ESCRITO por inga_cli -----------------

def _feedback(store) -> int:
    return store.create_feedback(author="ana", direccion="inga2es", source_text="sinchi tuku",
                                 model_output="todo fuerte", correction="hacerse fuerte",
                                 comment="sinchi tuku es hacerse fuerte", status="new")


def _cli(action: str, data: dict) -> tuple[str, dict]:
    return ("inga_cli", {"cmd": f"resource Wiki execute-action {action} --input '{json.dumps(data)}'"})


def _add(sources: list[dict], page_id: str = "lemma:sinchi", text: str = "sinchi tukui: hacerse fuerte.") -> tuple:
    return _cli("add-fact", {"page_id": page_id, "fact": {"section": "usage", "text": text, "sources": sources}})


CIERRE = json.dumps({"rationale": "Porque si.", "verdict": "supported"})
EV_OK = [{"type": "dictionary", "ref": "lema:sinchiai", "quote": "ponerse fuerte"}]
EV_FALSA = [{"type": "dictionary", "ref": "lema:inventadu", "quote": "hacerse fuerte"}]


def _run(store, script, *turnos):
    fid = _feedback(store)
    fake = script(list(turnos))
    evs = list(core.triage_feedback(fid, store=store))
    return fid, fake, evs, by_type(evs, "triage")[0]


def test_hecho_con_fuente_verificada_se_aplica_solo(store, script):
    fid, fake, evs, tri = _run(
        store, script,
        resp_calls(("fs_grep", {"patron": "sinchiai", "ruta": "fuentes/diccionario.md"})),
        resp_calls(_add(EV_OK)), resp_text(CIERRE))
    assert set(tri) == {"feedback_id", "verdict", "status", "rationale", "evidence", "facts"}
    assert (tri["verdict"], tri["status"], tri["rationale"]) == ("supported", "auto_applied", "Porque si.")
    assert tri["evidence"][0]["verified"] is True
    assert [f["status"] for f in tri["facts"]] == ["active"]
    assert set(tri["facts"][0]) == {"fact_id", "page_id", "text", "status"}

    fact = [f for f in store.get_page("lemma:sinchi")["facts"] if f["id"] == tri["facts"][0]["fact_id"]][0]
    refs = [(s["type"], s["ref"]) for s in fact["sources"]]
    assert fact["status"] == "active"
    assert ("feedback", f"feedback:{fid}") in refs and ("dictionary", "lema:sinchiai") in refs
    assert store.actions[0][1] == f"agent:feedback:{fid}"
    assert store.get_feedback(fid)["status"] == "auto_applied"
    assert [c["name"] for c in by_type(evs, "tool_call")] == ["fs_grep", "inga_cli"] and evs[-1]["event"] == "done"
    # inga_cli solo se declara aqui, con la lista de recursos en su descripcion
    decl = [d for d in fake.calls[0][1].tools[0].function_declarations if d.name == "inga_cli"][0]
    assert "Wiki" in decl.description and "Feedback" in decl.description and "execute-action" in decl.description
    # las paginas precargadas del triage vienen del arbol, con ids de hecho
    assert "- [f_0000000" in fake.calls[0][0][0].parts[0].text


def test_el_modelo_no_decide_el_estado(store, script):
    # dice "supported" pero escribe sin fuentes: el codigo lo deja pendiente
    fid, _, _, tri = _run(store, script, resp_calls(_add([])), resp_text(CIERRE))
    assert (tri["verdict"], tri["status"]) == ("needs_review", "pending_review")
    assert [f["status"] for f in tri["facts"]] == ["pending"]
    fact = [f for f in store.get_page("lemma:sinchi")["facts"] if f["id"] == tri["facts"][0]["fact_id"]][0]
    assert [s["type"] for s in fact["sources"]] == ["feedback"]
    assert json.loads(store.get_feedback(fid)["triage_json"])["llm_verdict"] == "supported"


def test_fuente_inventada_da_error_y_el_reintento_sin_fuentes_queda_pendiente(store, script):
    fid, fake, _, tri = _run(store, script, resp_calls(_add(EV_FALSA)), resp_calls(_add([])), resp_text(CIERRE))
    primera = fake.calls[1][0][-1].parts[0].function_response.response["result"]
    assert primera.startswith("Error: ninguna fuente pudo verificarse")
    assert (tri["status"], [f["status"] for f in tri["facts"]]) == ("pending_review", ["pending"])
    assert tri["evidence"][0]["verified"] is False and len(store.actions) == 1


def test_un_pendiente_entre_activos_manda_a_revision(store, script):
    _, _, _, tri = _run(store, script,
                        resp_calls(_add(EV_OK), _add([], text="tuku es raiz de tukui.")), resp_text(CIERRE))
    assert sorted(f["status"] for f in tri["facts"]) == ["active", "pending"]
    assert (tri["verdict"], tri["status"]) == ("needs_review", "pending_review")


def test_solo_no_change_rechaza_con_motivo(store, script):
    motivo = "El diccionario registra tukui (adj) todo; la correccion no tiene respaldo."
    fid, _, _, tri = _run(store, script,
                          resp_calls(_cli("no-change", {"reason": motivo, "evidence": EV_OK})), resp_text(CIERRE))
    assert (tri["verdict"], tri["status"], tri["facts"]) == ("contradicted", "rejected", [])
    assert motivo in tri["rationale"] and store.actions == []
    fb = store.get_feedback(fid)
    assert (fb["status"], fb["reviewer"]) == ("rejected", "agent") and motivo in fb["review_note"]
    assert json.loads(fb["triage_json"])["no_change"] == [motivo]


def test_sin_escrituras_pasa_a_revision_humana(store, script):
    # ni siquiera cuando se le exige escribir (segundo turno) llama a inga_cli
    _, fake, _, tri = _run(store, script, resp_text("no pude decidir, perdon"), resp_text(""), resp_text(""))
    assert len(fake.calls) == 3  # turno normal + exigencia + un ultimo empujon por respuesta vacia
    assert (tri["verdict"], tri["status"], tri["facts"]) == ("needs_review", "pending_review", [])
    assert "no pude decidir" in tri["rationale"] and "revision humana" in tri["rationale"]


def test_accion_sobre_pagina_inexistente_no_cuenta(store, script):
    _, fake, _, tri = _run(store, script, resp_calls(_add(EV_OK, page_id="lemma:noexiste")), resp_text(CIERRE),
                           resp_text(CIERRE))
    assert "no existe" in fake.calls[1][0][-1].parts[0].function_response.response["result"]
    assert (tri["status"], tri["facts"]) == ("pending_review", [])


def test_no_hay_via_para_aprobar_ni_rechazar_hechos(store, script):
    _, fake, _, tri = _run(
        store, script,
        resp_calls(_cli("approve-fact", {"fact_id": "f_00000001"}), _cli("reject-fact", {"fact_id": "f_00000001"})),
        resp_text(CIERRE), resp_text(CIERRE))
    outs = [p.function_response.response["result"] for p in fake.calls[1][0][-1].parts]
    assert all(o.startswith("Error: la accion") for o in outs) and store.actions == []
    assert tri["status"] == "pending_review"


def test_supersede_pendiente_y_revision_humana(store, script):
    viejo = store.get_page("lemma:tukui")["facts"][1]["id"]
    fid, _, _, tri = _run(store, script, resp_calls(_cli("supersede-fact", {"fact_id": viejo, "new_fact": {
        "section": "meaning", "text": "tukui (adj): todo; todos", "sources": []}})), resp_text(CIERRE))
    nuevo = tri["facts"][0]["fact_id"]
    estados = {f["id"]: f["status"] for f in store.get_page("lemma:tukui", include_inactive=True)["facts"]}
    assert estados[viejo] == "active" and estados[nuevo] == "pending"

    with pytest.raises(ReviewError):
        review_feedback(fid, "maybe", "rev", store=store)
    with pytest.raises(ReviewError):
        review_feedback(fid, "approve", "  ", store=store)
    row = review_feedback(fid, "approve", "Daniel", "ok", store=store)
    assert (row["status"], row["reviewer"], row["review_note"]) == ("approved", "Daniel", "ok")
    estados = {f["id"]: f["status"] for f in store.get_page("lemma:tukui", include_inactive=True)["facts"]}
    assert estados[viejo] == "superseded" and estados[nuevo] == "active"
    with pytest.raises(ReviewError):  # ya no esta pending_review
        review_feedback(fid, "reject", "Daniel", store=store)


def test_revision_rechaza(store, script):
    fid, _, _, tri = _run(store, script, resp_calls(_add([])), resp_text(CIERRE))
    row = review_feedback(fid, "reject", "Daniel", "no aplica", store=store)
    assert row["status"] == "rejected"
    page = store.get_page("lemma:sinchi", include_inactive=True)
    assert [f["status"] for f in page["facts"] if f["id"] == tri["facts"][0]["fact_id"]] == ["rejected"]


def test_feedback_inexistente(store, script):
    script([])
    assert [e["event"] for e in core.triage_feedback(99, store=store)] == ["error", "done"]


def test_dictionary_cita_solo_en_el_ocr(monkeypatch):
    monkeypatch.setattr(verify, "_lexico", lambda: {"sinchi": ["sinchi (s): medico tradicional; curandero"]})
    # El lexico (falso) de sinchi no trae la acepcion de adjetivo; el diccionario escaneado si.
    src = {"type": "dictionary", "ref": "lema:sinchi", "quote": "sinchi adj, adv duro; fuerte(mente)"}
    ok, motivo = verify.verify_source(src)
    assert ok and "escaneado" in motivo
    assert not verify.verify_source({**src, "quote": "sinchi adj volador; aeronave"})[0]


def test_si_cierra_sin_escribir_se_le_exige_inga_cli(store, script):
    fid, fake, evs, tri = _run(store, script,
                               resp_text(json.dumps({"rationale": "Se anadio un hecho."})),  # mentira: no llamo a nada
                               resp_calls(_add(EV_OK)), resp_text(CIERRE))
    assert (tri["status"], [f["status"] for f in tri["facts"]]) == ("auto_applied", ["active"])
    # el turno de exigencia obliga a llamar a inga_cli y lleva el recordatorio como mensaje de usuario
    cfg = fake.calls[1][1].tool_config.function_calling_config
    assert str(cfg.mode).endswith("ANY") and cfg.allowed_function_names == ["inga_cli"]
    assert "inga_cli" in fake.calls[1][0][-1].parts[0].text and fake.calls[1][0][-2].role == "model"


def test_leer_no_se_gasta_el_presupuesto_de_escribir(store, script, monkeypatch):
    monkeypatch.setattr(core, "TRIAGE_READ_CALLS", 6)  # freno de seguridad bajado para probarlo
    lecturas = [("fs_grep", {"patron": f"q{i}"}) for i in range(4)]
    fid, fake, evs, tri = _run(store, script, resp_calls(*lecturas), resp_calls(*lecturas),
                               resp_calls(_add(EV_OK)), resp_text(CIERRE))
    nombres = [c["name"] for c in by_type(evs, "tool_call")]
    assert nombres.count("fs_grep") == core.TRIAGE_READ_CALLS and nombres[-1] == "inga_cli"
    vetadas = [p.function_response.response["result"] for p in fake.calls[2][0][-1].parts]
    assert sum("Presupuesto de lectura agotado" in v for v in vetadas) == 2
    assert tri["status"] == "auto_applied"
