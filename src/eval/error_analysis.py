"""Analisis de errores reproducible sobre las predicciones del conjunto de validacion.

Produce el recuento por tipo de error y configuracion que se reporta en el Capitulo 4.
Los criterios son deliberadamente simples y deterministas: la tabla del documento debe
poder regenerarse desde el fichero de predicciones sin intervencion manual.

Tipos de error:

  repeticion    La salida contiene un n-grama (n de 1 a 4) repetido tres o mas veces de
                forma consecutiva. Es el patron de bucle del decodificador.

  desbordamiento La salida supera 2,5 veces la longitud en palabras de la referencia.

  grafia_ajena  (solo direccion es2inga) La salida contiene las letras 'q' o 'y'. Ambos
                grafemas estan practicamente ausentes del Inga del Putumayo tal como lo
                escribe el corpus: sobre los 823.744 caracteres del texto Inga de
                entrenamiento, 'y' no aparece ni una sola vez e 'q' aparece 6 veces
                (0,001 %). El Inga escribe iuiai, no yuyay; kan, no qan. Su presencia
                senala por tanto una variante quechua distinta (quechua sureno, que usa
                q de forma sistematica, o kichwa ecuatoriano, que usa y).

  vocab_inga    (solo direccion es2inga) Fraccion de tokens de la salida presentes en el
                vocabulario Inga del conjunto de entrenamiento. Se marca la salida como
                anclada al Inga cuando esa fraccion alcanza 0,5.

  vacia         Salida vacia o de menos de tres palabras.

Uso:
    python -m src.eval.error_analysis                      # corrida principal (Opus 4.7)
    python -m src.eval.error_analysis --pred otro.jsonl    # cualquier fichero de predicciones
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PRED_POR_DEFECTO = RAIZ / "datos" / "predicciones_val_completo.jsonl"
TRAIN = RAIZ / "datos" / "splits" / "train.jsonl"

CONFIGS = ["A", "B", "C", "D", "E"]
DIRECCIONES = ["inga2es", "es2inga"]

UMBRAL_DESBORDAMIENTO = 2.5
UMBRAL_VOCAB_INGA = 0.5
REPETICIONES_MINIMAS = 3
N_MAX = 4


def tokenizar(texto: str) -> list[str]:
    return re.findall(r"\w+", texto.lower())


def tiene_repeticion(texto: str) -> bool:
    """True si algun n-grama (n de 1 a 4) se repite 3 o mas veces consecutivas."""
    tokens = tokenizar(texto)
    for n in range(1, N_MAX + 1):
        for i in range(len(tokens) - n * REPETICIONES_MINIMAS + 1):
            bloque = tokens[i : i + n]
            repeticiones = 1
            j = i + n
            while tokens[j : j + n] == bloque:
                repeticiones += 1
                j += n
            if repeticiones >= REPETICIONES_MINIMAS:
                return True
    return False


def desborda(hyp: str, ref: str) -> bool:
    n_ref = len(tokenizar(ref))
    return n_ref > 0 and len(tokenizar(hyp)) > UMBRAL_DESBORDAMIENTO * n_ref


def grafia_ajena(hyp: str) -> bool:
    return bool(re.search(r"[qy]", hyp, re.IGNORECASE))


def cobertura_vocab(hyp: str, vocab: set[str]) -> float:
    tokens = tokenizar(hyp)
    if not tokens:
        return 0.0
    return sum(t in vocab for t in tokens) / len(tokens)


def vacia(hyp: str) -> bool:
    return len(tokenizar(hyp)) < 3


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred", type=Path, default=PRED_POR_DEFECTO)
    args = parser.parse_args()

    preds = [json.loads(l) for l in args.pred.read_text(encoding="utf-8").splitlines() if l.strip()]
    vocab = {
        t
        for l in TRAIN.read_text(encoding="utf-8").splitlines()
        if l.strip()
        for t in tokenizar(json.loads(l)["texto_inga"])
    }

    print(f"Predicciones: {args.pred.name}  (n={len(preds)})")
    print(f"Vocabulario Inga del train: {len(vocab)} tipos\n")

    filas: list[tuple[str, str, dict[str, int]]] = []
    for direccion in DIRECCIONES:
        campo_ref = "texto_es" if direccion == "inga2es" else "texto_inga"
        for cfg in CONFIGS:
            clave = f"hyp_{cfg}_{direccion}"
            hyps = [r[clave] for r in preds]
            refs = [r[campo_ref] for r in preds]
            conteo = {
                "repeticion": sum(tiene_repeticion(h) for h in hyps),
                "desbordamiento": sum(desborda(h, r) for h, r in zip(hyps, refs)),
                "vacia": sum(vacia(h) for h in hyps),
                "long_media": round(sum(len(tokenizar(h)) for h in hyps) / len(hyps), 1),
            }
            if direccion == "es2inga":
                conteo["grafia_ajena"] = sum(grafia_ajena(h) for h in hyps)
                conteo["anclada_inga"] = sum(
                    cobertura_vocab(h, vocab) >= UMBRAL_VOCAB_INGA for h in hyps
                )
            filas.append((cfg, direccion, conteo))

    campos = ["repeticion", "desbordamiento", "grafia_ajena", "anclada_inga", "vacia", "long_media"]
    print(f"{'cfg':4s} {'direccion':10s} " + " ".join(f"{c:>15s}" for c in campos))
    for cfg, direccion, conteo in filas:
        print(
            f"{cfg:4s} {direccion:10s} "
            + " ".join(f"{conteo.get(c, '-'):>15}" for c in campos)
        )

    refs_inga = [r["texto_inga"] for r in preds]
    print(f"\nLongitud media de la referencia Inga: "
          f"{sum(len(tokenizar(r)) for r in refs_inga) / len(refs_inga):.1f} palabras")
    refs_es = [r["texto_es"] for r in preds]
    print(f"Longitud media de la referencia espanola: "
          f"{sum(len(tokenizar(r)) for r in refs_es) / len(refs_es):.1f} palabras")


if __name__ == "__main__":
    main()
