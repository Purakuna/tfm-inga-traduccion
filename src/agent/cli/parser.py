"""Parser de la gramatica de `inga_cli` (estilo veleiro), escrito a mano sobre shlex.

    list-resources
    help [<Resource>]
    resource <Resource> list-actions
    resource <Resource> get-schema --action <action-name>
    resource <Resource> execute-action <action-name> --input '<json>'

Acepta `--key value` y `--key=value`. Los errores son mensajes accionables: dicen
que fallo y como se escribe bien, para que el modelo pueda reintentar.
"""
from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field

USAGE = (
    "Gramatica:\n"
    "  list-resources\n"
    "  help [<Resource>]\n"
    "  resource <Resource> list-actions\n"
    "  resource <Resource> get-schema --action <action-name>\n"
    "  resource <Resource> execute-action <action-name> --input '<json>'"
)

_RE_INPUT = re.compile(r"--input(?:=|\s+)(.*)$", re.S)


class CliError(ValueError):
    """Error de uso de la CLI; el mensaje se devuelve tal cual al modelo."""


@dataclass
class Command:
    verb: str  # list-resources | help | list-actions | get-schema | execute-action
    resource: str | None = None
    action: str | None = None
    input: dict = field(default_factory=dict)


def _options(tokens: list[str], permitidas: tuple[str, ...]) -> tuple[list[str], dict[str, str]]:
    """Separa posicionales y opciones `--key value` / `--key=value`."""
    pos: list[str] = []
    opts: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.startswith("--"):
            if "=" in t:
                key, value = t[2:].split("=", 1)
            else:
                key = t[2:]
                if i + 1 >= len(tokens):
                    raise CliError(f"Error: la opcion --{key} necesita un valor.\n{USAGE}")
                i += 1
                value = tokens[i]
            if key not in permitidas:
                validas = ", ".join("--" + p for p in permitidas) or "ninguna"
                raise CliError(f"Error: opcion desconocida --{key}. Opciones validas aqui: {validas}.")
            if key in opts:
                raise CliError(f"Error: la opcion --{key} esta repetida.")
            opts[key] = value
        else:
            pos.append(t)
        i += 1
    return pos, opts


def _load_json(raw: str) -> dict:
    try:
        obj = json.loads(raw)
    except ValueError as e:
        raise CliError(
            f"Error: --input no es JSON valido ({e}). Escribe el objeto entre comillas simples, con "
            "comillas dobles dentro: --input '{\"clave\": \"valor\"}'. Si un texto lleva comilla simple, "
            "escribela como \\u0027."
        )
    if not isinstance(obj, dict):
        raise CliError("Error: --input debe ser un objeto JSON ({...}), no una lista ni un valor suelto.")
    return obj


def _raw_input(cmd: str) -> str | None:
    """Todo lo que sigue a --input, sin el par de comillas exterior (None si no hay --input)."""
    m = _RE_INPUT.search(cmd)
    if not m:
        return None
    raw = m.group(1).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        raw = raw[1:-1]
    return raw


def parse(cmd: str) -> Command:
    if not isinstance(cmd, str) or not cmd.strip():
        raise CliError(f"Error: comando vacio.\n{USAGE}")
    cmd = cmd.strip()
    if cmd.startswith("inga_cli "):
        cmd = cmd[len("inga_cli "):].strip()
    # --input es siempre la ultima opcion y su valor es JSON: se separa ANTES de shlex y se toma
    # crudo, porque shlex se come los apostrofos de una cita (ri 'fue') y parte el JSON si el
    # modelo lo envolvio en comillas dobles.
    crudo = _raw_input(cmd)
    cabeza = _RE_INPUT.sub("", cmd) if crudo is not None else cmd
    try:
        tokens = shlex.split(cabeza)
    except ValueError as e:
        raise CliError(f"Error: comillas sin cerrar en el comando ({e}).\n{USAGE}")
    if crudo is not None:
        if not crudo:
            raise CliError(f"Error: la opcion --input necesita un valor.\n{USAGE}")
        tokens += ["--input", crudo]
    if not tokens:
        raise CliError(f"Error: comando vacio.\n{USAGE}")

    verbo = tokens[0]
    if verbo == "list-resources":
        if len(tokens) > 1:
            raise CliError("Error: list-resources no lleva argumentos.")
        return Command("list-resources")
    if verbo == "help":
        pos, _ = _options(tokens[1:], ())
        if len(pos) > 1:
            raise CliError("Error: uso: help [<Resource>]")
        return Command("help", resource=pos[0] if pos else None)
    if verbo != "resource":
        raise CliError(f"Error: comando desconocido '{verbo}'.\n{USAGE}")
    if len(tokens) < 3:
        raise CliError(f"Error: faltan argumentos despues de 'resource'.\n{USAGE}")
    resource, sub, resto = tokens[1], tokens[2], tokens[3:]
    if sub == "list-actions":
        if resto:
            raise CliError("Error: list-actions no lleva argumentos.")
        return Command("list-actions", resource=resource)
    if sub == "get-schema":
        pos, opts = _options(resto, ("action",))
        if pos or "action" not in opts:
            raise CliError(f"Error: uso: resource {resource} get-schema --action <action-name>")
        return Command("get-schema", resource=resource, action=opts["action"])
    if sub == "execute-action":
        pos, opts = _options(resto, ("input",))
        if len(pos) != 1:
            raise CliError(
                f"Error: uso: resource {resource} execute-action <action-name> --input '<json>' "
                "(un solo nombre de accion, y el JSON entero entre comillas simples)."
            )
        data = _load_json(opts.get("input", "{}"))
        return Command("execute-action", resource=resource, action=pos[0], input=data)
    raise CliError(
        f"Error: subcomando desconocido '{sub}'. Validos: list-actions, get-schema, execute-action.\n{USAGE}"
    )
