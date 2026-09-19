"""Herramientas que el agente expone a Gemini (seccion 8.2 del contrato).

Lectura: un sistema de archivos virtual de solo lectura (`fs_ls`, `fs_leer`,
`fs_grep`) sobre `wiki/` y `fuentes/`, mas dos busquedas que no son archivos
(`corpus_buscar`, vectorial sobre TRAIN, y `buscar_por_glosa`).
Escritura: una sola herramienta, `inga_cli`, que solo se ofrece en el triage de
feedback. No existe ninguna herramienta que escriba archivos.

Cada herramienta es una funcion Python simple con docstring en espanol; las
declaraciones para function calling se derivan de esas firmas. `Toolbox` liga
las herramientas a un WikiStore concreto y despacha por nombre, con salida
siempre acotada para no inflar el contexto.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Callable

from src.agent.fs import FUENTES, ROOT, FsError, VirtualFS, _lines, fold  # noqa: F401 (fold, ROOT: reexport)

# Prefijo de las refs de fuente (seccion 1 del contrato) -> archivo de fuentes/.
REF_DOCUMENTO = {"levinsohn": "gramatica", "rosetta": "rosetta", "diccionario": "diccionario"}

MAX_CHARS = 2500
READ_TOOLS = ("fs_ls", "fs_leer", "fs_grep", "corpus_buscar", "buscar_por_glosa")
CLI_TOOL = "inga_cli"


def cap(text: str, limit: int = MAX_CHARS) -> str:
    """Recorta un texto al limite de caracteres."""
    if len(text) <= limit:
        return text
    return text[: limit - 40].rstrip() + "\n[... salida recortada ...]"


def doc_lines(documento: str) -> tuple[str, ...]:
    """Lineas de un documento fuente (diccionario | gramatica | rosetta), cacheadas."""
    return _lines(FUENTES[documento + ".md"])[0]


def wiki_path(store: Any, page_id: str) -> str | None:
    """Ruta virtual (wiki/<kind>/<archivo>.md) de una pagina, si el store la conoce."""
    path_for = getattr(store, "path_for", None)
    rel = path_for(page_id) if path_for else None
    return f"wiki/{rel}" if rel else None


# --- busquedas que no son archivos --------------------------------------------

def search_examples(texto: str, direccion: str, k: int = 3) -> list[dict]:
    """Ejemplos paralelos de TRAIN desde LanceDB ({"inga","es","ref"}); unico acceso al corpus."""
    from src.rag.indexes import search

    indice = "ejemplos" if direccion == "inga2es" else "ejemplos_es"
    out = []
    for r in search(indice, texto, max(1, min(int(k), 8))):
        out.append(
            {
                "inga": r.get("texto_inga", ""),
                "es": r.get("texto_es", ""),
                "ref": f"{r.get('libro', '?')} {r.get('capitulo', '?')}:{r.get('versiculo', '?')}",
            }
        )
    return out


def corpus_buscar(texto: str, direccion: str, k: int = 3) -> str:
    """Busca oraciones paralelas parecidas en el corpus de entrenamiento (registro biblico).

    Sirve para ver palabras en contexto y la ortografia real del corpus. La ref
    de cada ejemplo (libro cap:vers) se puede citar como fuente de tipo corpus.

    Args:
        texto: oracion o frase a buscar.
        direccion: inga2es si el texto esta en inga, es2inga si esta en espanol.
        k: numero de ejemplos (1 a 8).
    """
    if direccion not in ("inga2es", "es2inga"):
        return "Error: direccion debe ser inga2es o es2inga."
    if not (texto or "").strip():
        return "Error: texto vacio."
    ejemplos = search_examples(texto, direccion, k)
    if not ejemplos:
        return "Sin ejemplos."
    return cap("\n".join(f"[{e['ref']}] INGA: {e['inga']}\n  ES: {e['es']}" for e in ejemplos))


class Toolbox:
    """Herramientas ligadas a un WikiStore, con despacho por nombre.

    `cli` (un src.agent.cli.registry.Registry ya ligado a su contexto) activa la
    herramienta de escritura `inga_cli`; sin el, el agente solo puede leer.
    """

    def __init__(self, store: Any, cli: Any = None, wiki_root: Any = None):
        self.store = store
        self.cli = cli
        self.fs = VirtualFS(wiki_root or getattr(store, "pages_root", None))
        self.pages_read: list[str] = []

    @property
    def names(self) -> tuple[str, ...]:
        return READ_TOOLS + ((CLI_TOOL,) if self.cli is not None else ())

    # --- sistema de archivos de solo lectura ---
    def fs_ls(self, ruta: str = "") -> str:
        """Lista una carpeta del sistema de archivos de solo lectura.

        Montajes: wiki/ (paginas markdown de la wiki: wiki/index.md explica la organizacion;
        wiki/<tipo>/index.md lista las paginas de cada tipo) y fuentes/ (diccionario.md,
        gramatica.md, rosetta.md escaneados). Las carpetas grandes se recortan: para hallar
        una pagina usa fs_grep sobre el index.md de la carpeta.

        Args:
            ruta: carpeta relativa, por ejemplo wiki/ o wiki/suffix/ o fuentes/. Vacio lista los montajes.
        """
        return self.fs.ls(ruta or "")

    def fs_leer(self, ruta: str, linea: int = 1, n: int = 120) -> str:
        """Lee un archivo con numeros de linea (paginas de la wiki o documentos fuente).

        En una pagina de la wiki cada hecho es una vineta `- [f_xxxxxxxx] texto` seguida de sus
        fuentes. En fuentes/ los numeros de linea sirven para citar: levinsohn:L<ini>-L<fin>
        (gramatica.md) o rosetta:L<ini>-L<fin> (rosetta.md).

        Args:
            ruta: archivo relativo, por ejemplo wiki/lemma/sinchi.md o fuentes/gramatica.md.
            linea: primera linea a leer (desde 1).
            n: cuantas lineas leer (maximo 200).
        """
        out = self.fs.leer(ruta, linea, n)
        to_id = getattr(self.store, "page_id_for_path", None)
        pid = to_id(ruta) if to_id and str(ruta).strip().startswith("wiki/") else None
        if pid and pid not in self.pages_read:
            self.pages_read.append(pid)
        return out

    def fs_grep(self, patron: str, ruta: str = "wiki/", max: int = 30) -> str:  # noqa: A002
        """Busca un patron (texto o regex) sin distinguir mayusculas ni acentos; devuelve ruta:linea:texto.

        Usos tipicos: hallar la pagina de una palabra -> fs_grep("sinchi", "wiki/lemma/index.md");
        ver que dice la wiki de algo -> fs_grep("hacerse", "wiki/"); ir a la fuente primaria ->
        fs_grep("sinchi", "fuentes/diccionario.md") (salen primero las entradas que empiezan por
        el patron) o fs_grep("-ngapa", "fuentes/gramatica.md"). Luego fs_leer en la linea hallada.

        Args:
            patron: palabra, sufijo, frase corta o expresion regular.
            ruta: archivo o carpeta donde buscar (por defecto toda la wiki).
            max: maximo de lineas a devolver (hasta 60).
        """
        return self.fs.grep(patron, ruta or "wiki/", max)

    # --- busquedas que no son archivos ---
    def buscar_por_glosa(self, palabra_es: str) -> str:
        """Busca lemas inga cuyo significado registrado menciona una palabra en espanol.

        Devuelve id de pagina, archivo en wiki/ y el significado que coincide.

        Args:
            palabra_es: una sola palabra en espanol (forma de diccionario: infinitivo, singular).
        """
        pages = self.store.find_by_gloss((palabra_es or "").strip(), limit=10)
        if not pages:
            return f"Ningun lema con glosa '{palabra_es}'."
        lineas = []
        for p in pages:
            ruta = wiki_path(self.store, p["id"]) or ""
            detalle = p.get("match") or p.get("summary", "")
            lineas.append(f"- {p['id']} | {ruta} | {str(detalle)[:160]}")
        return cap("\n".join(lineas))

    corpus_buscar = staticmethod(corpus_buscar)

    # --- escritura (solo en triage) ---
    def inga_cli(self, cmd: str) -> str:
        """Ver `inga_cli` a nivel de modulo: la descripcion real la arma cli_declaration()."""
        if self.cli is None:
            return "Error: inga_cli no esta disponible en esta tarea (solo lectura)."
        return self.cli.run(cmd)

    def callables(self) -> list[Callable]:
        return [getattr(self, n) for n in self.names]

    def call(self, name: str, args: dict | None) -> str:
        """Ejecuta una herramienta por nombre; nunca lanza, devuelve el error como texto."""
        if name not in self.names:
            return (f"Error: herramienta desconocida o no disponible '{name}'. "
                    f"Disponibles: {', '.join(self.names)}.")
        try:
            out = str(getattr(self, name)(**dict(args or {})))
        except FsError as e:
            return str(e)
        except TypeError as e:
            return f"Error de argumentos en {name}: {e}"
        except Exception as e:  # la herramienta falla, el agente sigue
            return f"Error en {name}: {type(e).__name__}: {str(e)[:200]}"
        # fs_leer y inga_cli ya acotan su salida con un limite propio (paginas completas, esquemas)
        return out if name in ("fs_leer", CLI_TOOL) else cap(out)


def summarize_result(name: str, args: dict, output: str) -> str:
    """Resumen corto y legible de un resultado, para el evento tool_result."""
    primera = output.splitlines()[0][:160] if output else ""
    if output.startswith(("Error", "Sin ", "Ningun")):
        return primera
    if name == "fs_leer":
        n = len(re.findall(r"^\d+: - \[f_", output, flags=re.M))
        return primera.rstrip(":") + (f" ({n} hechos)" if n else "")
    if name in ("fs_grep", "fs_ls"):
        return primera.rstrip(":")
    if name == "buscar_por_glosa":
        ids = re.findall(r"^- (\S+) \|", output, flags=re.M)
        return f"{len(ids)} lemas: " + ", ".join(ids[:4]) + ("..." if len(ids) > 4 else "")
    if name == "corpus_buscar":
        refs = re.findall(r"^\[([^\]]+)\]", output, flags=re.M)
        return f"{len(refs)} ejemplos: " + ", ".join(refs)
    if name == CLI_TOOL:
        cmd = re.sub(r"\s*--input.*$", "", str(args.get("cmd", "")), flags=re.S)[:80]
        plano = " ".join(output.split())
        m = re.search(r'"status": (\[[^\]]*\]|"[a-z]+")', plano)
        if '"ok": true' in plano and m:
            return f"{cmd} -> escrito, estado {m.group(1)}".replace('"', "")
        return f"{cmd} -> {plano[:100]}"
    return output[:120]


# --- declaraciones para function calling ----------------------------------------

def _from_callable(f: Callable):
    from google.genai import types

    from src.models.gemini_rag import _get_client

    try:
        return types.FunctionDeclaration.from_callable(client=_get_client(), callable=f)
    except RuntimeError:  # sin clave (tests): el esquema no depende del backend
        return types.FunctionDeclaration.from_callable_with_api_option(callable=f)


@lru_cache(maxsize=1)
def declarations() -> tuple:
    """FunctionDeclaration de las herramientas de LECTURA, derivadas de firma y docstring."""
    tb = Toolbox(store=None)
    return tuple(_from_callable(getattr(tb, n)) for n in READ_TOOLS)


def cli_declaration(description: str):
    """Declaracion de `inga_cli`; la descripcion la arma el registro (lista de recursos incluida)."""
    from google.genai import types

    return types.FunctionDeclaration(
        name=CLI_TOOL,
        description=description,
        parameters=types.Schema(
            type="OBJECT",
            properties={"cmd": types.Schema(type="STRING", description="Linea de comando completa.")},
            required=["cmd"],
        ),
    )
