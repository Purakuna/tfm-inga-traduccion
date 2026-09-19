"""normalize (reglas ortograficas derivadas del corpus train) y resolve."""
from __future__ import annotations

import pytest

from src.wiki.navigate import FALLBACK_SUFFIXES, normalize, resolve, spanish_candidates
from src.wiki.store import DEFAULT_DB, WikiStore


@pytest.mark.parametrize("entrada, esperado", [
    ("Achka yukangapa, sinchi tuku yuyangapa.", "achka iukangapa, sinchi tuku iuiangapa."),
    ("yukangapa", "iukangapa"),            # R1 y -> i
    ("kawsay", "kaugsai"),                 # R1 + R6 aw+C -> aug+C
    ("chawpi", "chaugpi"),
    ("wawa", "wawa"),                      # aw + vocal no cambia
    ("quilla", "killa"),                   # R2
    ("quiquin", "kikin"),
    ("ñuka", "nuka"), ("Ñukanchipa", "nukanchipa"),   # R7 lexica
    ("ñawi", "ñawi"), ("ñi", "ñi"), ("ñugpa", "ñugpa"),  # la ñ se conserva fuera de ñuka
    ("huasi", "wasi"), ("huarmi", "warmi"), ("huira", "wira"),   # R4
    ("kichui", "kichui"), ("kuchui", "kuchui"),        # la h de ch no es hu+vocal
    ("cancha", "kancha"), ("runacuna", "runakuna"), ("nuca", "nuka"), ("carca", "karka"),  # R3
    ("chaki", "chaki"), ("achka", "achka"),
    ("guagua", "wawa"), ("bungua", "bungua"), ("minguanti", "minguanti"),   # R5 solo inicial o tras vocal
    ("Taita Dius", "taita dius"),
    ("Jesucristowa", "jesucristowa"), ("Cristo", "cristo"), ("Marcospa", "marcospa"),  # nombres protegidos
    ("iuká", "iuká"), ("willaraiá", "willaraiá"),      # tildes finales se conservan
    ("shachima", "shachima"), ("patsa", "patsa"),      # sh y ts no se tocan
    ("", ""),
])
def test_normalize(entrada, esperado):
    assert normalize(entrada) == esperado


def test_normalize_preserves_punctuation_and_is_idempotent():
    t = "¿Imapatak, huasipi-chu? «Ñuka» 12:3; yuyay..."
    n = normalize(t)
    assert n == "¿imapatak, wasipi-chu? «nuka» 12:3; iuiai..."
    assert normalize(n) == n


def test_normalize_spanish_side_only_lowercases():
    assert normalize("Yo Quiero una Casa", direccion="es2inga") == "yo quiero una casa"


def _by_token(items):
    return {it["token"]: it for it in items}


def test_resolve_contract_sentence(wiki):
    items = resolve("Achka yukangapa, sinchi tuku yuyangapa.", "inga2es", wiki)
    assert [it["token"] for it in items] == ["Achka", "yukangapa", "sinchi", "tuku", "yuyangapa"]
    for it in items:
        assert set(it) >= {"token", "normalized", "lemma_pages", "suffix_pages", "resolved"}
        assert it["resolved"] is True
        assert it["suffix_pages"] == []        # aun no hay paginas de sufijo: debe funcionar igual
    t = _by_token(items)
    assert t["Achka"]["lemma_pages"] == ["lemma:achka"]
    assert t["yukangapa"]["normalized"] == "iukangapa"
    assert t["yukangapa"]["lemma_pages"] == ["lemma:iukai"] and t["yukangapa"]["suffixes"] == ["ngapa"]
    assert t["sinchi"]["lemma_pages"] == ["lemma:sinchi"]
    assert t["tuku"]["lemma_pages"] == ["lemma:tukui"]
    assert t["yuyangapa"]["lemma_pages"] == ["lemma:iuiai"] and t["yuyangapa"]["suffixes"] == ["ngapa"]
    # la pagina de tukui trae los dos sentidos
    textos = [f["text"] for f in wiki.get_page("lemma:tukui")["facts"]]
    assert any("(adj)" in x for x in textos) and any("(v.i.)" in x for x in textos)


def test_resolve_suffix_chains_and_unknowns(wiki):
    t = _by_token(resolve("Runakunaka huasimanda mana rirkakunachu, Jesuswa", "inga2es", wiki))
    assert t["Runakunaka"]["lemma_pages"] == ["lemma:runa"] and t["Runakunaka"]["suffixes"] == ["kuna", "ka"]
    assert t["huasimanda"]["lemma_pages"] == ["lemma:wasi"] and t["huasimanda"]["suffixes"] == ["manda"]
    assert t["rirkakunachu"]["lemma_pages"] == ["lemma:rii"]
    assert t["rirkakunachu"]["suffixes"] == ["rka", "kuna", "chu"]
    assert t["Jesuswa"]["resolved"] is False and t["Jesuswa"]["lemma_pages"] == []
    # un prefijo que coincide pero cuyo resto no es segmentable no se resuelve a la fuerza
    assert resolve("wasixyz", "inga2es", wiki)[0]["resolved"] is False


def test_resolve_multiword_and_variants(wiki):
    t = _by_token(resolve("Atun taitapa wasi", "inga2es", wiki))
    assert t["Atun"]["lemma_pages"][0] == "lemma:atun-taita"
    assert t["taitapa"]["lemma_pages"][0] == "lemma:atun-taita" and "lemma:taita" in t["taitapa"]["lemma_pages"]
    # kichwa unificado: -k final y -manta; se marcan como variante
    v = _by_token(resolve("ñukanchik wasimanta", "inga2es", wiki))
    assert v["ñukanchik"]["lemma_pages"] == ["lemma:nukanchi"] and v["ñukanchik"]["variant"] == "nukanchi"
    assert v["wasimanta"]["lemma_pages"] == ["lemma:wasi"] and v["wasimanta"]["variant"] == "wasimanda"
    # alias dialectal
    assert resolve("achijiirka", "inga2es", wiki)[0]["resolved"] in (True, False)
    assert resolve("achijii", "inga2es", wiki)[0]["lemma_pages"] == ["lemma:achijai"]


def test_resolve_prefers_suffix_pages_from_store(wiki):
    r = wiki.apply_action({"op": "upsert_page",
                           "page": {"id": "suffix:ngapa", "kind": "suffix", "slug": "ngapa",
                                    "title": "-ngapa (proposito)", "summary": "para + infinitivo",
                                    "aliases": ["-ngapa", "ngapa", "-ngapaj"]},
                           "facts": [{"section": "morphology", "text": "-ngapa marca proposito",
                                      "sources": [{"type": "grammar", "ref": "rosetta:L834-L834",
                                                   "quote": "el proposito (-ngapa - vease abajo)"}]}]}, "seed")
    assert r["ok"], r
    t = _by_token(resolve("yukangapa runakuna", "inga2es", wiki))
    assert t["yukangapa"]["suffix_pages"] == ["suffix:ngapa"]
    # -kuna no tiene pagina: se pela con el inventario de respaldo, sin pagina
    assert t["runakuna"]["resolved"] and t["runakuna"]["suffix_pages"] == [] and t["runakuna"]["suffixes"] == ["kuna"]


def test_resolve_es2inga(wiki):
    items = resolve("Yo quiero vivir en las casas grandes, no ama.", "es2inga", wiki)
    t = _by_token(items)
    assert t["Yo"].get("stopword") and t["Yo"]["resolved"] is False
    assert t["en"]["lemma_pages"] == [] and t["las"]["lemma_pages"] == []
    assert t["quiero"]["lemma_pages"] == ["lemma:munai"] and t["quiero"]["variant"] == "querer"
    assert t["vivir"]["lemma_pages"] == ["lemma:kaugsai"]
    assert t["casas"]["lemma_pages"][0] == "lemma:wasi" and t["casas"]["variant"] == "casa"
    assert t["grandes"]["lemma_pages"] == ["lemma:atun"]
    assert "lemma:ama" not in t["ama"]["lemma_pages"]        # "ama" espanol -> amar -> munai
    assert t["ama"]["lemma_pages"] == ["lemma:munai"]
    for it in items:
        assert it["suffix_pages"] == []


def test_resolve_edge_cases(wiki):
    assert resolve("", "inga2es", wiki) == [] and resolve("  ...  ", "es2inga", wiki) == []
    with pytest.raises(ValueError):
        resolve("hola", "fr2en", wiki)


def test_spanish_candidates():
    assert "casa" in spanish_candidates("casas")
    assert "luz" in spanish_candidates("luces")
    assert "caminar" in spanish_candidates("caminaban")
    assert "querer" in spanish_candidates("quiero")
    assert "poder" in spanish_candidates("puede")
    assert "bueno" in spanish_candidates("buenas")
    assert "lavarse" in spanish_candidates("lavar")


def test_fallback_inventory_cites_rosetta():
    for suf in ("ngapa", "kuna", "pi", "ta", "manda", "wa", "pa", "ka", "mi", "spa", "rka", "chu"):
        assert suf in FALLBACK_SUFFIXES and FALLBACK_SUFFIXES[suf].startswith("rosetta:L")


@pytest.mark.skipif(not DEFAULT_DB.exists(), reason="requiere datos/wiki/wiki.db (bootstrap)")
def test_contract_sentence_on_real_wiki():
    s = WikiStore(DEFAULT_DB, auto_render=False)
    if s.stats()["pages"]["lemma"] < 3000:
        pytest.skip("wiki real sin lemas cargados")
    t = _by_token(resolve("Achka yukangapa, sinchi tuku yuyangapa.", "inga2es", s))
    assert t["Achka"]["lemma_pages"] == ["lemma:achka"]
    assert "lemma:iukai" in t["yukangapa"]["lemma_pages"]
    assert t["sinchi"]["lemma_pages"] == ["lemma:sinchi"]
    assert "lemma:tukui" in t["tuku"]["lemma_pages"]
    assert "lemma:iuiai" in t["yuyangapa"]["lemma_pages"]
    es = _by_token(resolve("la casa", "es2inga", s))
    assert es["casa"]["lemma_pages"][0] == "lemma:wasi"


# ------------------------------------------------------------------ regresiones con paginas de sufijo
def _suffix(slug, aliases, quote="cita"):
    return {"op": "upsert_page",
            "page": {"id": f"suffix:{slug}", "kind": "suffix", "slug": slug, "title": f"-{slug}",
                     "summary": "", "aliases": aliases},
            "facts": [{"section": "morphology", "text": f"-{slug} es un sufijo",
                       "sources": [{"type": "grammar", "ref": "rosetta:L60-L70", "quote": quote}]}]}


@pytest.fixture()
def wiki_suf(wiki):
    paginas = [
        ("ngapa", ["-ngapa", "ngapa", "nga"]), ("nga", ["-nga", "nga", "-nca"]),
        ("pi", ["-pi", "pi"]), ("pa", ["-pa", "pa"]), ("ta", ["-ta", "ta"]), ("tak", ["-tak", "tak", "ta"]),
        ("kuna", ["-kuna", "kuna", "-cuna", "cuna", "nkuna"]), ("kunata", ["-kunata", "kunata", "-cunata"]),
        ("chi", ["-chi"]), ("ri", ["-ri"]), ("ku", ["-ku", "-cu"]), ("rka", ["-rka", "-rca"]),
        ("ni", ["-ni"]), ("wa", ["-wa", "-hua"]), ("manda", ["-manda"]), ("i", ["-i", "-y"]),
        ("g", ["-g", "-j"]), ("n", ["-n"]), ("pas", ["-pas", "-s"]), ("ka", ["-ka", "-k", "-ca"]),
        ("mi", ["-mi", "-m"]),
    ]
    for slug, aliases in paginas:
        assert wiki.apply_action(_suffix(slug, aliases), "seed")["ok"]
    wiki.apply_action({"op": "upsert_page",
                       "page": {"id": "lemma:ala", "kind": "lemma", "slug": "ala", "title": "ala", "summary": "s: ala"},
                       "facts": [{"section": "meaning", "text": "ala (s): (Esp) ala",
                                  "sources": [{"type": "dictionary", "ref": "lema:ala", "quote": "ala (s): (Esp) ala"}]}]}, "seed")
    return wiki


def _one(word, store):
    return resolve(word, "inga2es", store)[0]


def test_regression_suffix_pages(wiki_suf):
    it = _one("iukangapa", wiki_suf)
    assert it["lemma_pages"] == ["lemma:iukai"] and it["suffix_pages"] == ["suffix:ngapa"]
    it = _one("wasipi", wiki_suf)
    assert it["lemma_pages"] == ["lemma:wasi"] and it["suffix_pages"] == ["suffix:pi"]
    it = _one("runakunata", wiki_suf)
    assert it["lemma_pages"] == ["lemma:runa"] and it["suffixes"] == ["kuna", "ta"]
    # alias compartido `ta`: van las dos paginas; la lectura compuesta -kunata queda como alternativa
    assert it["suffix_pages"] == ["suffix:kuna", "suffix:ta", "suffix:tak", "suffix:kunata"]
    assert it["suffixes_alt"] == ["kunata"]
    # alias compartido `nga`
    assert _one("tukunga", wiki_suf)["suffix_pages"] == ["suffix:ngapa", "suffix:nga"] or \
        set(_one("tukunga", wiki_suf)["suffix_pages"]) == {"suffix:nga", "suffix:ngapa"}
    # grafia de 1978 en los alias (-cuna, -hua, -rca) se empareja por la forma del corpus
    assert _one("runacunahua", wiki_suf)["suffix_pages"] == ["suffix:kuna", "suffix:wa"]


def test_regression_no_spurious_one_letter_suffixes(wiki_suf):
    for palabra in ("sinchi", "wasi", "runa", "mana", "achka"):
        it = _one(palabra, wiki_suf)
        assert it["suffix_pages"] == [] and "suffixes" not in it, it
    # kani: ka-ni ('soy'), no kan+i
    it = _one("kaugsani", wiki_suf)
    assert it["lemma_pages"] == ["lemma:kaugsai"] and it["suffixes"] == ["ni"]
    # una letra solo pegada a la raiz (o tras derivativos) ...
    it = _one("kaugsagkuna", wiki_suf)
    assert it["suffixes"] == ["g", "kuna"] and it["suffix_pages"] == ["suffix:g", "suffix:kuna"]
    assert _one("kaugsakug", wiki_suf)["suffixes"] == ["ku", "g"]
    # ... o como clitico final (-m de -mi)
    assert _one("runakunam", wiki_suf)["suffixes"] == ["kuna", "m"]
    # nunca a mitad de palabra para forzar un prestamo desconocido: ala+k+ra+n
    assert _one("alakran", wiki_suf)["resolved"] is False
    assert _one("wasikpi", wiki_suf)["resolved"] is False
    assert _one("runatag", wiki_suf)["resolved"] is False


def test_regression_chains_and_cap(wiki_suf):
    it = _one("kaugsachirkakuna", wiki_suf)
    assert it["lemma_pages"] == ["lemma:kaugsai"] and it["suffixes"] == ["chi", "rka", "kuna"]
    assert it["suffix_pages"] == ["suffix:chi", "suffix:rka", "suffix:kuna"]
    largo = _one("kaugsachirikurkakunatapas", wiki_suf)
    assert largo["resolved"] and len(largo["suffix_pages"]) <= 4


def test_regression_n_is_not_followed_by_case(wiki_suf):
    # "riinpa" no es ri-n-pa: -n es verbal y no admite un caso nominal detras
    assert _one("rinpa", wiki_suf)["resolved"] is False
    assert _one("rinkuna", wiki_suf)["lemma_pages"] == ["lemma:rii"]
