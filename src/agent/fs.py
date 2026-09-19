"""Sistema de archivos virtual de SOLO LECTURA para el agente (seccion 8.2).

Dos montajes:
- `wiki/`    -> arbol markdown materializado de la wiki (pages_root del store)
- `fuentes/` -> los tres documentos OCR: diccionario.md, gramatica.md, rosetta.md

No existe ninguna operacion de escritura. Toda ruta pasa por `resolve`, que
rechaza rutas absolutas, `..`, `~`, barras invertidas y enlaces simbolicos, y
comprueba que el destino real quede dentro del montaje.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OCR_DIR = ROOT / "datos" / "ocr" / "inga-kichwa"
FUENTES = {
    "diccionario.md": OCR_DIR / "diccionario-inga.md",
    "gramatica.md": OCR_DIR / "gramatica-pedagogica-levinsohn.md",
    "rosetta.md": OCR_DIR / "rosetta-morfosintactico.md",
}
DEFAULT_WIKI_ROOT = ROOT / "datos" / "wiki" / "pages"

MAX_CHARS = 2500        # fs_ls y fs_grep
MAX_READ_CHARS = 4000   # fs_leer: una pagina de la wiki entra completa
MAX_LINE = 400          # las lineas OCR de la gramatica pueden ser parrafos enteros
MAX_GREP_TEXT = 200
MAX_LS = 60
PER_FILE_HITS = 4       # al buscar en un directorio, para que un archivo no agote el cupo


class FsError(ValueError):
    """Ruta invalida o inexistente; el mensaje va tal cual al modelo."""


def strip_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def fold(text: str) -> str:
    """Minusculas sin acentos ni diacriticos, para comparar texto OCR."""
    return strip_accents(text).lower()


# (ruta real) -> (mtime_ns, size, lineas, lineas sin acentos)
_cache: dict[str, tuple[int, int, tuple[str, ...], tuple[str, ...]]] = {}


def _lines(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    st = path.stat()
    key = str(path)
    hit = _cache.get(key)
    if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
        return hit[2], hit[3]
    lines = tuple(path.read_text(encoding="utf-8", errors="replace").splitlines())
    plain = tuple(strip_accents(l) for l in lines)
    _cache[key] = (st.st_mtime_ns, st.st_size, lines, plain)
    return lines, plain


class VirtualFS:
    def __init__(self, wiki_root: Path | str | None = None):
        self.wiki_root = Path(wiki_root) if wiki_root else DEFAULT_WIKI_ROOT

    # --- rutas -----------------------------------------------------------------
    @staticmethod
    def _parts(ruta: str) -> list[str]:
        if not isinstance(ruta, str):
            raise FsError("Error: la ruta debe ser texto.")
        r = ruta.strip()
        if "\x00" in r or "\\" in r:
            raise FsError("Error: ruta con caracteres no permitidos.")
        if r.startswith("/") or re.match(r"^[A-Za-z]:", r):
            raise FsError("Error: no se aceptan rutas absolutas. Usa rutas como wiki/lemma/sinchi.md o fuentes/diccionario.md.")
        if r.startswith("~"):
            raise FsError("Error: no se acepta '~'. Usa rutas como wiki/... o fuentes/...")
        parts = [p for p in r.split("/") if p not in ("", ".")]
        if any(p == ".." for p in parts):
            raise FsError("Error: no se acepta '..' en la ruta.")
        return parts

    def resolve(self, ruta: str) -> tuple[str, Path | None]:
        """Devuelve (ruta virtual normalizada, ruta real). Real es None para la raiz y `fuentes/`."""
        parts = self._parts(ruta)
        if not parts:
            return "", None
        mount, resto = parts[0], parts[1:]
        if mount == "fuentes":
            if not resto:
                return "fuentes", None
            if len(resto) != 1 or resto[0] not in FUENTES:
                raise FsError("Error: en fuentes/ solo existen diccionario.md, gramatica.md y rosetta.md.")
            return "fuentes/" + resto[0], FUENTES[resto[0]]
        if mount != "wiki":
            raise FsError("Error: la ruta debe empezar por wiki/ o fuentes/.")
        real = self.wiki_root
        for p in resto:
            real = real / p
            if real.is_symlink():
                raise FsError("Error: no se siguen enlaces simbolicos.")
        if not real.exists():
            raise FsError(f"Error: no existe {'/'.join(parts)}. Usa fs_ls para ver que hay.")
        raiz = self.wiki_root.resolve()
        final = real.resolve()
        if final != raiz and raiz not in final.parents:
            raise FsError("Error: la ruta sale del montaje wiki/.")
        return "/".join(parts), real

    # --- operaciones -------------------------------------------------------------
    def ls(self, ruta: str = "") -> str:
        virt, real = self.resolve(ruta)
        if virt == "":
            return "wiki/      paginas markdown de la wiki (empieza por wiki/index.md)\nfuentes/   documentos fuente escaneados"
        if virt == "fuentes":
            return "\n".join(f"fuentes/{n}  ({len(_lines(p)[0])} lineas)" for n, p in FUENTES.items())
        if real.is_file():
            return f"{virt}  ({len(_lines(real)[0])} lineas)"
        entradas = sorted((e for e in os.scandir(real) if not e.is_symlink() and not e.name.startswith(".")),
                          key=lambda e: e.name)
        dirs = [e.name + "/" for e in entradas if e.is_dir()]
        files = [e.name for e in entradas if e.is_file()]
        # index.md primero: es la puerta de entrada de cada carpeta
        files.sort(key=lambda n: (n != "index.md", n))
        nombres = dirs + files
        out = [f"{virt}/ ({len(dirs)} carpetas, {len(files)} archivos)"] + nombres[:MAX_LS]
        if len(nombres) > MAX_LS:
            out.append(f"[... {len(nombres) - MAX_LS} mas. No listes: usa fs_grep(patron, \"{virt}/index.md\") "
                       f"para hallar una pagina por palabra]")
        return _cap("\n".join(out), MAX_CHARS)

    def leer(self, ruta: str, linea: int = 1, n: int = 120) -> str:
        virt, real = self.resolve(ruta)
        if real is None or real.is_dir():
            raise FsError(f"Error: {virt or 'la raiz'} es una carpeta; usa fs_ls.")
        try:
            linea, n = int(linea), int(n)
        except (TypeError, ValueError):
            raise FsError("Error: linea y n deben ser enteros.")
        lines, _ = _lines(real)
        if linea < 1 or linea > max(len(lines), 1):
            raise FsError(f"Error: {virt} tiene {len(lines)} lineas.")
        n = max(1, min(n, 200))
        fin = min(len(lines), linea - 1 + n)
        out, usados, ultima = [], 0, linea - 1
        for j in range(linea - 1, fin):
            if not lines[j].strip():
                ultima = j + 1
                continue
            txt = f"{j + 1}: {lines[j][:MAX_LINE]}"
            if usados + len(txt) > MAX_READ_CHARS and out:
                break
            out.append(txt)
            usados += len(txt) + 1
            ultima = j + 1
        cab = f"{virt} lineas {linea}-{ultima} de {len(lines)}"
        if ultima < len(lines):
            cab += f" (sigue con linea={ultima + 1})"
        return cab + ":\n" + "\n".join(out)

    def grep(self, patron: str, ruta: str = "wiki/", max: int = 30) -> str:  # noqa: A002 (nombre del contrato)
        virt, real = self.resolve(ruta)
        p = strip_accents((patron or "").strip())
        if not p:
            raise FsError("Error: patron vacio.")
        # El modelo escribe a veces texto con parentesis o puntos ("fuerte(mente)") y a veces
        # regex: se aceptan las dos lecturas a la vez (literal O regex).
        literal = re.escape(p)
        try:
            rx = re.compile(literal if literal == p else f"(?:{literal})|(?:{p})", re.I)
        except re.error:
            rx = re.compile(literal, re.I)
        try:
            tope = int(max)
        except (TypeError, ValueError):
            tope = 30
        tope = min(tope if tope > 0 else 30, 60)

        if virt == "":
            raise FsError("Error: indica donde buscar: wiki/ (o una subcarpeta o archivo) o fuentes/.")
        if virt == "fuentes":
            archivos = [("fuentes/" + n, fp) for n, fp in FUENTES.items()]
        elif real.is_file():
            archivos = [(virt, real)]
        else:
            archivos = []
            for base, dirs, files in os.walk(real, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                for f in sorted(files):
                    fp = Path(base) / f
                    if f.endswith(".md") and not fp.is_symlink():
                        rel = fp.relative_to(real).as_posix()
                        archivos.append((f"{virt}/{rel}", fp))
        un_archivo = len(archivos) == 1

        def buscar(rx: re.Pattern) -> tuple[list[str], int, int]:
            if not un_archivo:
                # Primero los archivos cuyo nombre ya coincide (la pagina de la palabra),
                # despues los indices, al final el resto.
                def orden(a: tuple[str, Path]) -> tuple:
                    stem = Path(a[0]).stem.replace("-", " ")
                    return (not rx.fullmatch(stem), not rx.search(stem), not a[0].endswith("index.md"), a[0])

                archivos.sort(key=orden)
            hits: list[str] = []
            total = n_files = 0
            for vpath, fp in archivos:
                lines, plain = _lines(fp)
                idx = [i for i, l in enumerate(plain) if rx.search(l)]
                if not idx:
                    continue
                total += len(idx)
                n_files += 1
                if un_archivo:
                    # En un documento (p. ej. el diccionario) interesa primero la linea que
                    # EMPIEZA por el patron, y antes las que empiezan en minuscula: en el
                    # diccionario esa es la entrada propia; en mayuscula van las frases de ejemplo.
                    def rango(i: int) -> tuple:
                        txt = plain[i].lstrip("#*- ")
                        empieza = bool(rx.match(txt))
                        return (not (empieza and txt[:1].islower()), not empieza, i)

                    idx.sort(key=rango)
                else:
                    idx = _sin_cabecera(lines, idx)[:PER_FILE_HITS]
                for i in idx:
                    if len(hits) < tope:
                        hits.append(f"{vpath}:{i + 1}:{lines[i].strip()[:MAX_GREP_TEXT]}")
            return hits, total, n_files

        hits, total, n_files = buscar(rx)
        if not hits:
            return f"Sin coincidencias de '{patron}' en {virt}."
        cab = f"{total} lineas coinciden en {n_files} archivo(s); se muestran {len(hits)}"
        if un_archivo and total > len(hits):
            cab += " (primero las lineas que empiezan por el patron; afina el patron para ver menos)"
        return _cap(cab + ":\n" + "\n".join(hits), MAX_CHARS)


def _sin_cabecera(lines: tuple[str, ...], idx: list[int]) -> list[int]:
    """Quita los aciertos del front matter y del H1 de una pagina (repiten el titulo).

    Si el archivo solo coincide ahi, deja una unica linea (la del titulo).
    """
    if not lines or lines[0].strip() != "---":
        return idx
    fin = next((j for j in range(1, min(len(lines), 40)) if lines[j].strip() == "---"), 0)
    cuerpo = [i for i in idx if i > fin and not lines[i].startswith("# ")]
    if cuerpo:
        # las lineas "- fuente:" suelen repetir el hecho que citan: solo si no hay otra cosa
        return [i for i in cuerpo if not lines[i].lstrip().startswith("- fuente:")] or cuerpo
    titulo = [i for i in idx if lines[i].startswith(("title:", "# "))]
    return (titulo or idx)[:1]


def _cap(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    corte = text.rfind("\n", 0, limit - 40)
    return text[: corte if corte > 0 else limit - 40].rstrip() + "\n[... salida recortada ...]"
