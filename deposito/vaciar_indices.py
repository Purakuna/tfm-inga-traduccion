#!/usr/bin/env python3
"""Vacia el resultado cacheado de los tres campos TOC del deposito.

Word para Mac, al recibir 'update field' por AppleScript sobre un campo TOC que ya tiene
resultado, se limita a refrescar los numeros de pagina y conserva las entradas viejas (el
equivalente de 'actualizar solo los numeros de pagina'). Eso deja fuera del indice cualquier
titulo nuevo. Si el campo no tiene resultado que conservar, Word no tiene mas remedio que
reconstruirlo entero.

Este script colapsa cada campo TOC a su forma minima (begin + instruccion + separate + end,
sin resultado) y lo marca como dirty. Despues hay que abrir el documento en Word y actualizar
los tres campos, que ya se regeneran completos.

Detalle que importa: cada entrada del indice lleva dentro un campo PAGEREF con sus propios
fldChar begin y end. El end que cierra el TOC es, por tanto, el que devuelve la profundidad de
anidamiento a cero, no el primero que aparece. Buscar el primero rompe el campo y deja las
entradas huerfanas fuera de el.
"""
from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path

DEPOSITO = Path(__file__).parent
DOCX = DEPOSITO / "TFM_Deposito_EslavaSantos.docx"
WORK = Path("/private/tmp/claude-501/-Users-william-santos-Documents-UNIR-tfm/"
            "d67907b7-ef9d-476c-b184-805e0cee9345/scratchpad/build_vaciar")

FLDCHAR = re.compile(r'<w:fldChar w:fldCharType="(begin|end)"[^>]*/>')
P_RE = re.compile(r"<w:p(?: [^>]*)?>.*?</w:p>", re.S)


def die(msg: str):
    sys.exit(f"ABORT: {msg}")


def fin_del_campo(xml: str, ini_begin: int) -> int:
    """Offset del final del fldChar end que cierra el campo abierto en ini_begin."""
    profundidad = 0
    for m in FLDCHAR.finditer(xml, ini_begin):
        profundidad += 1 if m.group(1) == "begin" else -1
        if profundidad == 0:
            return m.end()
    die("campo sin fldChar end de cierre")


def main() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    with zipfile.ZipFile(DOCX) as z:
        nombres = z.namelist()
        z.extractall(WORK)

    ruta = WORK / "word/document.xml"
    xml = ruta.read_text(encoding="utf-8")

    campos = []
    for m in re.finditer(r'<w:instrText[^>]*>(\s*TOC [^<]*)</w:instrText>', xml):
        instr = m.group(1)
        # el fldChar begin del campo es el ultimo que precede a la instruccion
        ini_begin = xml.rfind('<w:fldChar w:fldCharType="begin"', 0, m.start())
        if ini_begin == -1:
            die("campo TOC sin fldChar begin")
        fin_end = fin_del_campo(xml, ini_begin)
        # el campo abarca parrafos completos: desde el <w:p> que abre el begin hasta el
        # </w:p> que cierra el parrafo donde vive el end
        ini_p = xml.rfind("<w:p ", 0, ini_begin)
        ini_p2 = xml.rfind("<w:p>", 0, ini_begin)
        ini_p = max(ini_p, ini_p2)
        fin_p = xml.find("</w:p>", fin_end) + len("</w:p>")
        campos.append((ini_p, fin_p, instr))

    if len(campos) != 3:
        die(f"esperaba 3 campos TOC, encontre {len(campos)}")

    for ini_p, fin_p, instr in reversed(campos):
        bloque = xml[ini_p:fin_p]
        ppr = re.search(r"<w:pPr>.*?</w:pPr>", bloque, re.S)
        ppr = ppr.group(0) if ppr else ""
        n_paras = len(P_RE.findall(bloque))
        vacio = (
            "<w:p>" + ppr
            + '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
            + f'<w:r><w:instrText xml:space="preserve">{instr}</w:instrText></w:r>'
            + '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            + '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
            + "</w:p>"
        )
        xml = xml[:ini_p] + vacio + xml[fin_p:]
        print(f"  vaciado {instr.strip()[:32]!r}: {n_paras} parrafos de resultado -> campo vacio")

    # Los 3 parrafos que albergan los campos conservan su estilo de indice; cualquier otro
    # parrafo con estilo de indice seria una entrada huerfana que Word no regeneraria.
    huerfanas = [
        p for p in P_RE.findall(xml)
        if re.search(r'<w:pStyle w:val="(TOC[123]|TableofFigures)"', p)
        and not re.search(r"<w:instrText[^>]*>\s*TOC ", p)
    ]
    if huerfanas:
        die(f"quedan {len(huerfanas)} entradas de indice fuera de los campos: el vaciado no fue limpio")

    ruta.write_text(xml, encoding="utf-8")
    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre in nombres:
            z.write(WORK / nombre, nombre)
    print(f"\nIndices vaciados en {DOCX.name}. Abrir en Word y actualizar los 3 campos.")


if __name__ == "__main__":
    main()
