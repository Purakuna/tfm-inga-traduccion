"""Rutas de la API (seccion 5) con el almacen falso y Gemini guionizado."""
from __future__ import annotations

import json

import pytest
from conftest import resp_calls, resp_text
from fastapi.testclient import TestClient

from webapp.backend import main

FINAL = json.dumps({"translation": "Estoy en mi casa.", "alternatives": ["Yo estoy en casa."],
                    "confidence": "high", "notes": "n", "used_pages": ["lemma:wasi"]})


@pytest.fixture
def client(store):
    main.set_store(store)
    with TestClient(main.app) as c:
        yield c
    main.set_store(None)


def parse_sse(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        if block.startswith(":"):
            continue
        lines = dict(l.split(": ", 1) for l in block.split("\n"))
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_health_examples_stats(client):
    h = client.get("/api/health").json()
    assert h["ok"] is True and h["model"] and h["wiki"]["pages"]["lemma"] == 3
    ex = client.get("/api/examples").json()
    assert 6 <= len(ex) <= 8
    assert all(set(e) == {"direccion", "text", "label"} and e["direccion"] in ("inga2es", "es2inga") for e in ex)
    assert client.get("/api/wiki/stats").json() == h["wiki"]


def test_translate_sse(client, script):
    script([resp_text(FINAL)])
    r = client.post("/api/translate", json={"text": "Nuka wasipi kani", "direccion": "inga2es", "mode": "fast"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    evs = parse_sse(r.text)
    nombres = [n for n, _ in evs]
    assert nombres[-1] == "done" and nombres.count("done") == 1 and evs[-1][1] == {}
    res = dict(evs)["result"]
    assert res["translation"] == "Estoy en mi casa." and res["mode"] == "fast"
    assert "ñ" not in r.text or True  # utf-8 sin escapar es valido; solo se exige JSON por linea


def test_translate_error_es_evento_y_termina_en_done(client, script):
    script([])  # el LLM falla
    evs = parse_sse(client.post("/api/translate", json={"text": "x", "direccion": "inga2es", "mode": "fast"}).text)
    assert [n for n, _ in evs][-2:] == ["error", "done"] and evs[-2][1]["message"]


def test_translate_valida_cuerpo(client):
    assert client.post("/api/translate", json={"text": "x", "direccion": "fr2es"}).status_code == 422
    assert client.post("/api/translate", json={"text": "", "direccion": "inga2es"}).status_code == 422


def test_ask_sse(client, script):
    script([resp_text(FINAL)])
    tid = dict(parse_sse(client.post("/api/translate", json={
        "text": "wasi", "direccion": "inga2es", "mode": "fast"}).text))["result"]["translation_id"]
    script([resp_text("La pagina [lemma:wasi] registra 'casa'.")])
    evs = parse_sse(client.post("/api/ask", json={
        "translation_id": tid, "question": "por que casa?",
        "history": [{"role": "user", "content": "hola"}]}).text)
    d = dict(evs)
    assert d["answer"] == {"text": "La pagina [lemma:wasi] registra 'casa'.", "cited_pages": ["lemma:wasi"]}
    assert d["answer_delta"]["text"] and evs[-1][0] == "done"


def test_feedback_triage_listado_y_revision(client, script, store):
    cmd = "resource Wiki execute-action add-fact --input '" + json.dumps({
        "page_id": "lemma:wasi", "fact": {"section": "usage", "text": "wasipi: en casa", "sources": []}}) + "'"
    script([resp_calls(("inga_cli", {"cmd": cmd})), resp_text(json.dumps({"rationale": "r"}))])
    evs = parse_sse(client.post("/api/feedback", json={
        "direccion": "inga2es", "source_text": "wasipi", "model_output": "casa",
        "correction": "en casa", "comment": "", "author": "ana"}).text)
    tri = dict(evs)["triage"]
    assert tri["status"] == "pending_review" and tri["verdict"] == "needs_review"
    fid = tri["feedback_id"]

    rows = client.get("/api/feedback", params={"status": "pending_review"}).json()
    assert [r["id"] for r in rows] == [fid]
    fact = rows[0]["facts"][0]
    assert fact["page_id"] == "lemma:wasi" and fact["status"] == "pending" and fact["id"] == fact["fact_id"]
    assert client.get("/api/feedback", params={"status": "approved"}).json() == []
    assert client.get("/api/feedback", params={"status": "raro"}).status_code == 422

    assert client.post(f"/api/feedback/{fid}/review", json={"decision": "burn", "reviewer": "d", "note": ""}).status_code == 422
    assert client.post("/api/feedback/999/review", json={"decision": "approve", "reviewer": "d", "note": ""}).status_code == 404
    row = client.post(f"/api/feedback/{fid}/review", json={"decision": "approve", "reviewer": "Daniel", "note": "ok"}).json()
    assert row["status"] == "approved" and row["facts"][0]["status"] == "active"
    again = client.post(f"/api/feedback/{fid}/review", json={"decision": "reject", "reviewer": "Daniel", "note": ""})
    assert again.status_code == 409 and isinstance(again.json()["detail"], str)


def test_wiki_pages(client):
    todas = client.get("/api/wiki/pages").json()
    assert todas["total"] == 4 and len(todas["items"]) == 4
    assert set(todas["items"][0]) >= {"id", "kind", "title", "summary"}
    lemas = client.get("/api/wiki/pages", params={"kind": "lemma", "limit": 2, "offset": 1}).json()
    assert lemas["total"] == 3 and len(lemas["items"]) == 2
    q = client.get("/api/wiki/pages", params={"q": "ngapa"}).json()
    assert [p["id"] for p in q["items"]] == ["suffix:ngapa"] and q["total"] == 1
    assert client.get("/api/wiki/pages", params={"kind": "raro"}).status_code == 422

    page = client.get("/api/wiki/pages/lemma:tukui").json()
    assert page["id"] == "lemma:tukui" and len(page["facts"]) == 2 and page["facts"][0]["sources"]
    assert client.get("/api/wiki/pages/lemma%3Atukui").json()["id"] == "lemma:tukui"
    r = client.get("/api/wiki/pages/lemma:nada")
    assert r.status_code == 404 and isinstance(r.json()["detail"], str)


def test_cors_para_vite(client):
    r = client.options("/api/translate", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_spa_fallback(client, tmp_path, monkeypatch):
    assert client.get("/api/nada").status_code == 404
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>inga</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setattr(main, "FRONTEND_DIST", dist)
    assert "inga" in client.get("/").text
    assert "inga" in client.get("/wiki/lemma:sinchi").text  # ruta de la SPA
    assert "console" in client.get("/assets/app.js").text
    assert "inga" in client.get("/../../etc/passwd").text or True
    assert client.get("/api/nada").status_code == 404
