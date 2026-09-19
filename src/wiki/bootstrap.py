"""Carga idempotente de las semillas de la wiki.

Uso:  PYTHONPATH=. uv run python -m src.wiki.bootstrap [--reset] [--db RUTA] [--seed-dir DIR]

- Lee cada datos/wiki/seed/*.jsonl (una pagina por linea, formato de la seccion 2.1
  del contrato). Si un archivo aun no existe (otra linea de trabajo lo esta
  generando) simplemente no se carga: se puede volver a ejecutar despues.
- Los hechos de semilla quedan con created_by="seed". Recargar no duplica nada:
  un hecho con la misma seccion y texto (en cualquier estado) se salta, asi que
  una correccion hecha por feedback no se deshace al recargar.
- Un hecho de semilla activo que ya no aparece en la semilla pasa a superseded.
- Una pagina con solo hechos de semilla que ya no esta en ninguna semilla se retira
  (status superseded; un upsert posterior la reactiva). Nada se borra.
- --reset borra paginas, hechos, versiones, feedback y traducciones y recarga.
- Al final reconstruye el arbol markdown datos/wiki/pages/ (render_all).
- Tolerancia: citas de mas de 300 caracteres y resumenes de mas de 300 se
  recortan con aviso; un hecho invalido se salta con aviso sin perder la pagina.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.wiki.store import DEFAULT_DB, REPO_ROOT, WikiStore
from src.wiki.validation import (
    MAX_QUOTE,
    MAX_SUMMARY,
    MAX_TITLE,
    ValidationError,
    validate_fact,
)

SEED_DIR = REPO_ROOT / "datos" / "wiki" / "seed"
_LOTE = 400
_TABLAS = ("gloss_index", "fact_sources", "facts", "page_aliases", "page_versions", "page_paths",
           "pages",
           "feedback", "translations")


def _clip(texto: str, n: int) -> str:
    texto = (texto or "").strip()
    return texto if len(texto) <= n else texto[: n - 4].rstrip() + " ..."


def prepare_page(raw: dict, avisos: list[str]) -> dict | None:
    """Convierte una linea de semilla en una accion upsert_page tolerante a excesos."""
    if not isinstance(raw, dict) or not raw.get("kind") or not raw.get("slug"):
        avisos.append(f"linea sin kind/slug: {str(raw)[:80]}")
        return None
    pid = raw.get("id") or f"{raw['kind']}:{raw['slug']}"
    summary = raw.get("summary") or ""
    if len(summary.strip()) > MAX_SUMMARY:
        avisos.append(f"{pid}: resumen recortado a {MAX_SUMMARY}")
    page = {
        "id": pid, "kind": raw["kind"], "slug": raw["slug"],
        "title": _clip(raw.get("title") or raw["slug"], MAX_TITLE),
        "summary": _clip(summary, MAX_SUMMARY),
        "aliases": [a for a in (raw.get("aliases") or []) if isinstance(a, str) and a.strip()],
    }
    facts = []
    for f in raw.get("facts") or []:
        if not isinstance(f, dict):
            avisos.append(f"{pid}: hecho que no es objeto, saltado")
            continue
        f = dict(f)
        fuentes = []
        for s in f.get("sources") or []:
            if isinstance(s, dict):
                s = dict(s)
                if isinstance(s.get("quote"), str) and len(s["quote"].strip()) > MAX_QUOTE:
                    s["quote"] = _clip(s["quote"], MAX_QUOTE)
                    avisos.append(f"{pid}: cita recortada a {MAX_QUOTE}")
                fuentes.append(s)
        f["sources"] = fuentes
        f["status"] = "active"
        try:
            validate_fact(f)
        except ValidationError as exc:
            avisos.append(f"{pid}: hecho saltado ({exc})")
            continue
        facts.append(f)
    return {"op": "upsert_page", "page": page, "facts": facts, "retire_missing_seed": True,
            "reason": "bootstrap de semillas"}


def load_seed_file(store: WikiStore, path: Path) -> dict:
    """Carga un archivo de semillas y devuelve contadores y avisos."""
    avisos: list[str] = []
    acciones = []
    with path.open(encoding="utf-8") as fh:
        for n, linea in enumerate(fh, 1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                raw = json.loads(linea)
            except ValueError as exc:
                avisos.append(f"{path.name}:{n}: JSON invalido ({exc})")
                continue
            accion = prepare_page(raw, avisos)
            if accion:
                acciones.append(accion)
    res = {"file": path.name, "pages": 0, "pages_changed": 0, "new_facts": 0, "errors": 0,
           "warnings": avisos, "ids": {a["page"]["id"] for a in acciones},
           "kinds": {a["page"]["kind"] for a in acciones}}
    for i in range(0, len(acciones), _LOTE):
        lote = acciones[i:i + _LOTE]
        for accion, r in zip(lote, store.apply_actions(lote, actor="seed")):
            if r["ok"]:
                res["pages"] += 1
                res["new_facts"] += len(r["fact_ids"])
            else:
                res["errors"] += 1
                avisos.append(f"{accion['page']['id']}: pagina rechazada ({r['error']})")
    return res


def reset_db(store: WikiStore) -> None:
    with store._write() as conn:  # noqa: SLF001 - operacion administrativa del propio paquete
        for tabla in _TABLAS:
            conn.execute(f"DELETE FROM {tabla}")  # nombres de tabla de lista fija
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'feedback'")


def bootstrap(db_path: Path | str = DEFAULT_DB, seed_dir: Path | str = SEED_DIR,
              reset: bool = False, verbose: bool = True) -> dict:
    store = WikiStore(db_path)
    if reset:
        reset_db(store)
    seed_dir = Path(seed_dir)
    archivos = sorted(seed_dir.glob("*.jsonl")) if seed_dir.is_dir() else []
    # lemas primero: las paginas de gramatica/sufijos pueden remitir a lemas
    archivos.sort(key=lambda p: (p.name != "lemmas.jsonl", p.name))
    resultados = []
    for path in archivos:
        try:
            res = load_seed_file(store, path)
        except OSError as exc:  # archivo a medio escribir o borrado entre glob y open
            res = {"file": path.name, "pages": 0, "new_facts": 0, "errors": 1,
                   "warnings": [f"no se pudo leer: {exc}"]}
        resultados.append(res)
        if verbose:
            print(f"{res['file']}: {res['pages']} paginas, {res['new_facts']} hechos nuevos, "
                  f"{res['errors']} errores, {len(res['warnings'])} avisos")
            for a in res["warnings"][:15]:
                print(f"  aviso: {a}")
            if len(res["warnings"]) > 15:
                print(f"  ... {len(res['warnings']) - 15} avisos mas")
    if verbose:
        for esperado in ("lemmas.jsonl", "grammar.jsonl", "suffixes.jsonl"):
            if not (seed_dir / esperado).exists():
                print(f"(aun no existe {esperado}; vuelve a ejecutar el bootstrap cuando este)")
    # paginas solo-de-semilla que ya no estan en ninguna semilla (p. ej. id corregido): se
    # retiran (status superseded), nunca se borran. Solo para tipos que alguna semilla cargo,
    # y solo si la carga fue limpia, para no retirar nada por un archivo a medio escribir.
    ids_semilla = set().union(*(r.get("ids", set()) for r in resultados)) if resultados else set()
    tipos = set().union(*(r.get("kinds", set()) for r in resultados)) if resultados else set()
    retiradas = 0
    if ids_semilla and not any(r["errors"] for r in resultados):
        viejas = [pid for pid, kind in store.seed_only_pages() if kind in tipos and pid not in ids_semilla]
        if len(viejas) <= max(50, len(ids_semilla) // 10):
            auto = store.auto_render
            store.auto_render = False
            for pid in viejas:
                if store.retire_page(pid, "seed", "ya no esta en las semillas")["ok"]:
                    retiradas += 1
            store.auto_render = auto
        elif verbose:
            print(f"AVISO: {len(viejas)} paginas faltan en las semillas; no se retiran (revisar)")
    if verbose and retiradas:
        print(f"paginas retiradas por no estar ya en las semillas: {retiradas}")
    store.reindex_gloss()
    from src.wiki import render

    for res in resultados:
        if res["new_facts"] or res["errors"]:
            render.append_log(store, "seed", "bootstrap", None,
                              note=f"{res['file']}: {res['pages']} paginas, "
                                   f"{res['new_facts']} hechos nuevos, {res['errors']} errores")
    arbol = store.render_all()
    if verbose:
        print(f"markdown: {arbol['pages']} paginas en {arbol['root']} ({arbol['removed']} archivos viejos borrados)")
    stats = store.stats()
    if verbose:
        print(json.dumps(stats, ensure_ascii=False))
    return {"files": resultados, "stats": stats}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Carga idempotente de semillas de la wiki Inga")
    ap.add_argument("--reset", action="store_true",
                    help="borra TODO (incluido feedback y traducciones) antes de cargar")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--seed-dir", type=Path, default=SEED_DIR)
    args = ap.parse_args(argv)
    out = bootstrap(args.db, args.seed_dir, reset=args.reset)
    return 1 if any(r["errors"] for r in out["files"]) and not out["stats"]["pages"]["total"] else 0


if __name__ == "__main__":
    sys.exit(main())
