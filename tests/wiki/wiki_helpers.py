"""Datos de prueba: unas pocas paginas de lema tomadas del diccionario."""
from __future__ import annotations



def dict_src(lema: str, quote: str) -> list[dict]:
    return [{"type": "dictionary", "ref": f"lema:{lema}", "quote": quote}]


def lemma_action(lema: str, senses: list[tuple[str, str]], aliases=None, es_rows=()) -> dict:
    """upsert_page de un lema con hechos 'lema (cat): glosa' y entradas espanol-inga."""
    slug = lema.lower().replace(" ", "-")
    facts = [{"section": "meaning", "text": f"{lema} ({cat}): {glosa}",
              "sources": dict_src(lema, f"{lema} ({cat}): {glosa}")} for cat, glosa in senses]
    for es, cat, glosa in es_rows:
        facts.append({"section": "meaning",
                      "text": f"{es} ({cat}): {glosa} [entrada espanol-inga del diccionario]",
                      "sources": dict_src(es, f"{es} ({cat}): {glosa}")})
    return {"op": "upsert_page",
            "page": {"id": f"lemma:{slug}", "kind": "lemma", "slug": slug, "title": lema,
                     "summary": " | ".join(f"{c}: {g}" for c, g in senses),
                     "aliases": list(aliases or [])},
            "facts": facts}


LEMAS = [
    ("achka", [("adj", "bastante; mucho; varios (gen. con más énfasis que ajai, véase machka)")], None, ()),
    ("iukai", [("v.t.", "tener; poseer")], None, [("tener", "v.t.", "iukai, charii")]),
    ("sinchi", [("s", "médico tradicional; curandero; yerbatero; brujo")], None,
     [("brujo", "s", "millaipa iacha, samai pagta, sinchi")]),
    ("tukui", [("adj", "todo; todos"), ("v.i.", "llegar a ser; pretender ser; resultar; hacerse")], None, ()),
    ("iuiai", [("s", "pensamiento; inteligencia"), ("v.t.", "pensar; acordarse")], None, ()),
    ("wasi", [("s", "casa; hogar")], None, [("casa", "s", "wasi")]),
    ("chanchala wasi", [("s", "casa de palos no raspados")], None, ()),
    ("nuka", [("pron", "yo")], None, [("yo", "pron", "nuka")]),
    ("nukanchi", [("pron", "nosotros")], None, ()),
    ("killa", [("s", "luna; mes")], None, ()),
    ("kaugsai", [("s", "vida"), ("v.i.", "vivir")], None, [("vivir", "v.i.", "kaugsai, tiakui/tianakui")]),
    ("runa", [("s", "persona; gente; hombre")], None, ()),
    ("rii", [("v.i.", "ir")], None, ()),
    ("mana", [("adv", "no")], None, ()),
    ("ama", [("adv", "no (en prohibiciones)")], None, ()),
    ("munai", [("v.t.", "querer; amar; desear")], None, [("querer", "v.t.", "kuiai, munai")]),
    ("atun", [("adj", "grande")], None, ()),
    ("achijai", [("v.i.", "estornudar (AP, achijii - Yun, jachii - Mocoa)")], ["achijii"], ()),
    ("taita", [("s", "papá; padre; señor")], None, ()),
    ("atun taita", [("s", "abuelo")], None, ()),
    ("ñi", [("conj", "(Esp) ni (AP, ni - MP)")], None, ()),
    ("ni", [("conj", "(Esp) ni (MP, ñi - AP)")], None, ()),
]
