"""Revision humana del feedback que el triage dejo en `pending_review`."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

DECISIONS = ("approve", "reject")


class ReviewError(ValueError):
    """La revision no se puede aplicar (feedback inexistente, estado o decision invalidos)."""


def feedback_facts(feedback: dict, store: Any) -> list[dict]:
    """Hechos escritos por el triage de un feedback, con su estado ACTUAL en la wiki.

    Forma: [{"fact_id","page_id","text","status"}]. Parte de lo que guardo el
    triage y refresca el estado leyendo la pagina (los hechos nunca se borran).
    """
    triage = feedback.get("triage")
    if triage is None and feedback.get("triage_json"):
        try:
            triage = json.loads(feedback["triage_json"])
        except (TypeError, ValueError):
            triage = None
    out = []
    for f in (triage or {}).get("facts") or []:
        item = {"fact_id": f.get("fact_id"), "page_id": f.get("page_id"),
                "text": f.get("text", ""), "status": f.get("status", "")}
        page = store.get_page(item["page_id"], include_inactive=True) if item["page_id"] else None
        for pf in (page or {}).get("facts", []):
            if pf.get("id") == item["fact_id"]:
                item["status"], item["text"] = pf.get("status", item["status"]), pf.get("text", item["text"])
                break
        out.append(item)
    return out


def review_feedback(
    feedback_id: int, decision: str, reviewer: str, note: str = "", store: Any = None
) -> dict:
    """Aplica la decision humana y devuelve la fila de feedback actualizada.

    approve -> approve_fact sobre sus hechos pendientes, feedback `approved`.
    reject  -> reject_fact sobre sus hechos pendientes, feedback `rejected`.
    """
    if store is None:
        from src.wiki.store import WikiStore

        store = WikiStore()
    if decision not in DECISIONS:
        raise ReviewError("decision debe ser approve o reject")
    reviewer = (reviewer or "").strip()
    if not reviewer:
        raise ReviewError("falta el nombre de quien revisa")
    feedback = store.get_feedback(int(feedback_id))
    if feedback is None:
        raise ReviewError(f"no existe el feedback {feedback_id}")
    if feedback.get("status") != "pending_review":
        raise ReviewError(f"el feedback {feedback_id} esta '{feedback.get('status')}', no pending_review")

    note = (note or "").strip()
    errores = []
    for f in feedback_facts(feedback, store):
        if f["status"] != "pending":
            continue
        if decision == "approve":
            action = {"op": "approve_fact", "fact_id": f["fact_id"]}
        else:
            action = {"op": "reject_fact", "fact_id": f["fact_id"], "reason": note or "rechazado en revision"}
        res = store.apply_action(action, actor=f"reviewer:{reviewer}")
        if not res.get("ok"):
            errores.append(f"{f['fact_id']}: {res.get('error')}")
    if errores and decision == "approve":
        # Aprobar a medias dejaria la wiki y el feedback desalineados: se informa y no se cierra.
        raise ReviewError("no se pudieron aprobar todos los hechos: " + "; ".join(errores))

    store.update_feedback(
        int(feedback_id),
        status="approved" if decision == "approve" else "rejected",
        reviewer=reviewer,
        reviewed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        review_note=note,
    )
    return store.get_feedback(int(feedback_id))
