"""Genera las imagenes de la webapp Inga-Espanol con el modelo de imagen de Google.

Uso:
    PYTHONPATH=. uv run python scripts/generate_images.py            # genera candidatos
    PYTHONPATH=. uv run python scripts/generate_images.py --only hero
    PYTHONPATH=. uv run python scripts/generate_images.py --finalize hero=a montana=b ...

Flujo: primero se generan 2 candidatos por archivo en `_candidatos/`, se revisan
a ojo, y luego `--finalize` post-procesa el elegido y borra los descartados.
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
from pathlib import Path

from google.genai import types
from PIL import Image

from src.models.gemini_rag import _get_client

OUT = Path(__file__).resolve().parents[1] / "webapp" / "frontend" / "public" / "img"
CAND = OUT / "_candidatos"
MODELS = ["gemini-3-pro-image", "gemini-3.1-flash-image"]

RULES = (
    " Strictly no people, no human figures, no faces, no buildings with signs, no ceremonies,"
    " no religious or sacred objects, no text, no letters, no logos, no watermarks, no borders."
)
PHOTO = (
    " Real documentary landscape photograph, full-frame camera, natural color grading,"
    " realistic detail, not fantasy art, not a painting, not oversaturated."
)

PROMPTS: dict[str, dict] = {
    "hero": {
        "aspect": "16:9",
        "variants": {
            "a": (
                "Wide cinematic landscape photograph of the Sibundoy valley in the Andean-Amazonian"
                " piedmont of Putumayo, Colombia, at dawn. Layered deep green mountain ridges receding"
                " into low mist, a winding river on the right side of the frame catching warm golden"
                " light. Composition: the left half of the frame is calm, darker and low in detail"
                " (shadowed forested slope and soft mist) to leave room for overlaid headline text;"
                " the brightest light and the river are on the right half. Rich deep greens, warm low sun."
            ),
            "b": (
                "Dawn over a high green valley in the upper Putumayo, southern Colombia, seen from a"
                " hillside: overlapping forested Andean ridges fading into blue-green haze, bands of"
                " low fog on the valley floor, a small river glinting with first sunlight in the right"
                " third. The left half of the image stays in deep shadow, dark green and uncluttered,"
                " smooth tonal area suitable for placing text over it. Warm rim light on the ridges,"
                " moody, cinematic, 35mm lens."
            ),
        },
    },
    "montana": {
        "aspect": "16:9",
        "variants": {
            "a": (
                "Cloud forest slopes of the upper Putumayo, Colombian Andes: steep mountainsides covered"
                " in dense montane forest with tree ferns and moss-laden trees, thick mist drifting"
                " between the ridges, overcast diffuse light, moody and quiet, muted deep greens and greys."
            ),
            "b": (
                "Telephoto photograph of misty Andean cloud forest ridges in southern Colombia, layers of"
                " steep forested slopes disappearing into low cloud, wet dark green canopy, a few pale"
                " cecropia trees, soft rain atmosphere, moody low-contrast light."
            ),
        },
    },
    "selva": {
        "aspect": "16:9",
        "variants": {
            "a": (
                "Aerial drone photograph of Amazon foothill rainforest in Putumayo, Colombia: a"
                " clay-colored, reddish-brown muddy river meandering through unbroken dense green canopy,"
                " seen from above at an oblique angle, sandbars on the bends, soft morning light,"
                " thin mist over the trees, low hills toward the horizon."
            ),
            "b": (
                "Top-down aerial photograph of a winding ochre, sediment-rich river cutting through"
                " lowland tropical rainforest at the foot of the Andes in southern Colombia, dense varied"
                " canopy texture, pale sand beaches on the inner bends, natural even light."
            ),
        },
    },
    "paramo": {
        "aspect": "16:9",
        "variants": {
            "a": (
                "High Andean paramo in southern Colombia under soft fog: a field of frailejones"
                " (Espeletia) with silvery-green rosettes of hairy leaves on thick trunks, tussock grasses,"
                " a small dark tarn in the distance, diffuse cold light, muted greens, ochres and greys."
            ),
            "b": (
                "Foggy paramo landscape at 3500 m in the Colombian Andes: many Espeletia frailejon plants"
                " of different heights scattered across rolling golden-green grassland, the farthest"
                " ones dissolving into mist, dew on the leaves, quiet overcast morning."
            ),
        },
    },
    "patron-chumbe": {
        "aspect": "1:1",
        "photo": False,
        "variants": {
            "a": (
                "Seamless tileable flat geometric textile pattern, vector illustration style. Repeating"
                " rows of woven diamonds and concentric rhombi alternating with horizontal zigzag bands,"
                " inspired by the geometry of Andean woven belts. Exactly four flat colors: deep green"
                " #1f4d3a, clay red #a5482f, cream #f1e6d0, charcoal #2a2a28. Crisp edges, perfectly"
                " regular grid, even spacing, edges of the image match so it tiles seamlessly, no"
                " shading, no gradients, no fabric texture, no figures, purely abstract geometry."
            ),
            "b": (
                "Abstract geometric repeat pattern, flat vector, symmetric and seamless on all four"
                " sides: a lattice of stepped rhombi with smaller diamonds inside, separated by chevron"
                " zigzag stripes, in the manner of backstrap-loom woven bands from the Andes. Palette"
                " limited to deep forest green, terracotta clay red, cream and charcoal. Solid flat"
                " fills, clean lines, no symbols, no animals, no figures, no gradients."
            ),
        },
    },
}


def generate(client, prompt: str, aspect: str) -> tuple[bytes, str]:
    last_err: Exception | None = None
    for model in MODELS:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect, image_size="2K"),
                ),
            )
            for cand in resp.candidates or []:
                for part in (cand.content.parts if cand.content else []) or []:
                    if part.inline_data and part.inline_data.data:
                        return part.inline_data.data, model
            last_err = RuntimeError(f"{model}: respuesta sin imagen ({resp.prompt_feedback})")
        except Exception as exc:  # noqa: BLE001 - se prueba el siguiente modelo
            last_err = exc
        print(f"  ! fallo {model}: {type(last_err).__name__}: {str(last_err)[:200]}")
    raise RuntimeError(f"ningun modelo genero imagen: {last_err}")


def run_generate(only: list[str] | None, variants: list[str] | None) -> None:
    client = _get_client()
    CAND.mkdir(parents=True, exist_ok=True)
    for name, spec in PROMPTS.items():
        if only and name not in only:
            continue
        for var, text in spec["variants"].items():
            if variants and var not in variants:
                continue
            prompt = text + (PHOTO if spec.get("photo", True) else "") + RULES
            print(f"{name}-{var} ...")
            data, model = generate(client, prompt, spec["aspect"])
            img = Image.open(io.BytesIO(data))
            dest = CAND / f"{name}-{var}.png"
            img.save(dest)
            # vista previa liviana para revision visual
            prev = img.convert("RGB")
            prev.thumbnail((1400, 1400))
            prev.save(CAND / f"{name}-{var}.preview.jpg", quality=80)
            print(f"  ok {model} {img.size} -> {dest.name}")


def save_jpeg(img: Image.Image, dest: Path, width: int, max_kb: int = 600) -> None:
    # el modelo entrega 2752x1536 (algo mas ancho que 16:9): recorte centrado exacto
    cw = min(img.width, round(img.height * 16 / 9))
    ch = min(img.height, round(cw * 9 / 16))
    left, top = (img.width - cw) // 2, (img.height - ch) // 2
    img = img.crop((left, top, left + cw, top + ch))
    h = round(width * 9 / 16)
    out = img.convert("RGB").resize((width, h), Image.LANCZOS)
    for q in (82, 78, 74, 70, 66):
        out.save(dest, "JPEG", quality=q, progressive=True, optimize=True)
        if dest.stat().st_size <= max_kb * 1024:
            break
    print(f"  {dest.name}: {out.size} q={q} {dest.stat().st_size / 1024:.0f} KB")


# El modelo no devuelve un mosaico realmente continuo. Se recorta una celda entre
# ejes de simetria medidos sobre el candidato (x cada 128 px; y en los centros de
# dos filas de rombos) y se refleja 2x2: los bordes coinciden por construccion.
PATTERN_CROP = {"a": (256, 1024, 512, 1283)}


def seamless_tile(img: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    cell = img.crop(box)
    w, h = cell.size
    tile = Image.new("RGB", (2 * w, 2 * h))
    tile.paste(cell, (0, 0))
    tile.paste(cell.transpose(Image.FLIP_LEFT_RIGHT), (w, 0))
    tile.paste(cell.transpose(Image.FLIP_TOP_BOTTOM), (0, h))
    tile.paste(cell.transpose(Image.ROTATE_180), (w, h))
    return tile


def run_finalize(choices: list[str]) -> None:
    for item in choices:
        name, var = item.split("=")
        img = Image.open(CAND / f"{name}-{var}.png")
        if name == "patron-chumbe":
            dest = OUT / "patron-chumbe.png"
            out = seamless_tile(img.convert("RGB"), PATTERN_CROP[var]).resize(
                (1024, 1024), Image.LANCZOS
            )
            out = out.quantize(colors=32, dither=Image.Dither.NONE)
            out.save(dest, "PNG", optimize=True)
            print(f"  {dest.name}: {out.size} {dest.stat().st_size / 1024:.0f} KB")
        else:
            save_jpeg(img, OUT / f"{name}.jpg", 2400)
            if name == "hero":
                save_jpeg(img, OUT / "hero-sm.jpg", 1200, max_kb=250)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--variants", nargs="*")
    ap.add_argument("--finalize", nargs="*", help="pares nombre=variante")
    ap.add_argument("--clean", action="store_true", help="borra la carpeta de candidatos")
    args = ap.parse_args()
    if args.finalize:
        run_finalize(args.finalize)
    elif not args.clean:
        run_generate(args.only, args.variants)
    if args.clean and CAND.exists():
        shutil.rmtree(CAND)
        print("candidatos borrados")


if __name__ == "__main__":
    sys.exit(main())
