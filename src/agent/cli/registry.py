"""Registro de recursos y acciones de `inga_cli`, y ejecucion de un comando.

Cada accion declara un modelo pydantic de entrada (extra="forbid"); `get-schema`
devuelve su JSON schema y `execute-action` valida antes de llamar al handler.
`Registry.run` nunca lanza: todo error vuelve como texto accionable. Lleva la
cuenta de fallos por comando (maximo 2 reintentos).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from src.agent.cli.parser import USAGE, CliError, Command, parse

MAX_RETRIES = 2
MAX_OUTPUT = 3500


class ActionError(ValueError):
    """Fallo de negocio de una accion (pagina inexistente, fuente no verificable...)."""


@dataclass
class Action:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[Any, BaseModel], dict]
    kind: str = "read"  # read | write


@dataclass
class Resource:
    name: str
    description: str
    actions: dict[str, Action] = field(default_factory=dict)

    def add(self, action: Action) -> None:
        self.actions[action.name] = action


def _dump(obj: Any) -> str:
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    if len(text) > MAX_OUTPUT:
        text = text[: MAX_OUTPUT - 40] + "\n[... salida recortada ...]"
    return text


def _validation_message(e: ValidationError, resource: str, action: str) -> str:
    lineas = []
    for err in e.errors()[:8]:
        campo = ".".join(str(x) for x in err["loc"]) or "(raiz)"
        if err["type"] == "extra_forbidden":
            lineas.append(f"- {campo}: campo no permitido (quitalo)")
        elif err["type"] == "missing":
            lineas.append(f"- {campo}: falta este campo obligatorio")
        else:
            lineas.append(f"- {campo}: {err['msg']}")
    return (
        f"Error: --input no cumple el esquema de {resource} {action}:\n" + "\n".join(lineas)
        + f"\nConsulta el esquema con: resource {resource} get-schema --action {action}"
    )


class Registry:
    def __init__(self, resources: list[Resource], ctx: Any = None):
        self.resources = {r.name: r for r in resources}
        self.ctx = ctx
        self.failures: dict[tuple, int] = {}

    # --- descripcion --------------------------------------------------------------
    def describe(self) -> str:
        """Texto para la descripcion de la herramienta: gramatica + recursos + acciones."""
        lineas = [
            "CLI tipada para consultar y ESCRIBIR en la wiki (unica via de escritura). "
            "Un comando por llamada.",
            USAGE,
            "Recursos y acciones:",
        ]
        for r in self.resources.values():
            lineas.append(f"- {r.name}: {r.description}")
            for a in r.actions.values():
                lineas.append(f"    {a.name} ({'escritura' if a.kind == 'write' else 'lectura'}): {a.description}")
        lineas.append(
            "El --input es un objeto JSON entre comillas simples. Si dudas de los campos, pide el "
            "esquema con get-schema antes de ejecutar. Los errores explican como corregir el comando."
        )
        return "\n".join(lineas)

    def _resource(self, name: str | None) -> Resource:
        r = self.resources.get(name or "")
        if r is None:
            # tolera mayusculas distintas: wiki -> Wiki
            r = next((x for x in self.resources.values() if x.name.lower() == (name or "").lower()), None)
        if r is None:
            raise CliError(f"Error: recurso desconocido '{name}'. Recursos: {', '.join(self.resources)}.")
        return r

    def _action(self, r: Resource, name: str | None) -> Action:
        a = r.actions.get((name or "").replace("_", "-"))
        if a is None:
            raise CliError(f"Error: la accion '{name}' no existe en {r.name}. Acciones: {', '.join(r.actions)}.")
        return a

    # --- ejecucion ------------------------------------------------------------------
    def run(self, cmd: str) -> str:
        clave: tuple = ("parse",)
        try:
            command = parse(cmd)
            clave = (command.verb, (command.resource or "").lower(), command.action or "")
            if self.failures.get(clave, 0) > MAX_RETRIES:
                return (f"Error: limite de {MAX_RETRIES} reintentos alcanzado para este comando. No lo repitas: "
                        "sigue con otra accion o termina con lo que ya tienes.")
            out = self._dispatch(command)
            self.failures.pop(clave, None)
            return out
        except (CliError, ActionError) as e:
            msg = str(e)
        except ValidationError as e:  # por si un handler valida algo mas
            msg = f"Error: datos invalidos: {e.errors()[:3]}"
        except Exception as e:
            msg = f"Error interno en inga_cli: {type(e).__name__}: {str(e)[:200]}"
        n = self.failures.get(clave, 0) + 1
        self.failures[clave] = n
        restantes = MAX_RETRIES + 1 - n
        if restantes > 0:
            msg += f"\n(Puedes corregir y reintentar: te quedan {restantes} intento(s) para este comando.)"
        else:
            msg += "\n(Sin reintentos para este comando: no lo repitas.)"
        return msg

    def _dispatch(self, c: Command) -> str:
        if c.verb == "list-resources":
            return "\n".join(f"{r.name}: {r.description}" for r in self.resources.values())
        if c.verb == "help":
            if c.resource is None:
                return self.describe()
            r = self._resource(c.resource)
            return f"{r.name}: {r.description}\n" + "\n".join(
                f"  {a.name} ({a.kind}): {a.description}" for a in r.actions.values())
        r = self._resource(c.resource)
        if c.verb == "list-actions":
            return "\n".join(f"{a.name} ({a.kind}): {a.description}" for a in r.actions.values())
        a = self._action(r, c.action)
        if c.verb == "get-schema":
            return _dump(a.input_model.model_json_schema())
        try:
            data = a.input_model.model_validate(c.input)
        except ValidationError as e:
            raise CliError(_validation_message(e, r.name, a.name))
        return _dump(a.handler(self.ctx, data))
