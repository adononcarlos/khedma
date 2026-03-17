"""Pages publiques : 3 langues x 2 thèmes, mobile, bascule de thème et de langue."""
import re

import pytest
from playwright.sync_api import expect

from conftest import count_from_text, shot

LANGS = ["fr", "ar", "en"]


@pytest.fixture(scope="module")
def sample_offer(api):
    return api.get("/offers", params={"source": "rekrute", "size": 1}).json()["items"][0]["id"]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_pages_render(page, console_errors, lang, scheme, sample_offer):
    page.emulate_media(color_scheme=scheme)
    for path, name in [("", "accueil"), ("/offres", "offres"), (f"/offres/{sample_offer}", "offre")]:
        page.goto(f"/{lang}{path}", wait_until="networkidle")
        expect(page.locator("html")).to_have_attribute("dir", "rtl" if lang == "ar" else "ltr")
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert bg == ("rgb(15, 13, 23)" if scheme == "dark" else "rgb(248, 247, 252)"), f"fond {bg} en mode {scheme}"
        shot(page, f"public_{name}_{lang}_{scheme}")
    expect(page.get_by_role("link", name=r"↗")).to_have_attribute("href", re.compile(r"^https?://.+"))


def test_home_shows_only_offer_count(page, console_errors, api):
    page.goto("/fr", wait_until="networkidle")
    total = api.get("/offers", params={"size": 1}).json()["total"]
    stats = page.locator("dl dt")
    expect(stats).to_have_count(1)
    assert count_from_text(stats.first.inner_text()) == total
    expect(page.get_by_text("Démo")).to_have_count(0)  # plus de mention en pied de page


@pytest.mark.parametrize("lang", LANGS)
def test_mobile(page, console_errors, lang):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"/{lang}/offres", wait_until="networkidle")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= 390, f"défilement horizontal sur mobile ({width}px)"
    shot(page, f"mobile_offres_{lang}")


def test_theme_toggle_persists(page, console_errors):
    page.emulate_media(color_scheme="light")
    page.goto("/fr", wait_until="networkidle")
    page.get_by_role("button", name="Mode sombre").click()
    expect(page.locator("html")).to_have_class(re.compile(r"\bdark\b"))
    page.reload(wait_until="networkidle")
    expect(page.locator("html")).to_have_class(re.compile(r"\bdark\b"))
    shot(page, "theme_sombre_apres_rechargement", full_page=False)


def test_language_switch_keeps_filters(page, console_errors):
    page.goto("/fr/offres?contract=CDI&function=it", wait_until="networkidle")
    page.get_by_role("link", name="EN", exact=True).click()
    page.wait_for_url("**/en/offres?**")
    assert "contract=CDI" in page.url and "function=it" in page.url
    expect(page.get_by_role("heading", name="Job offers")).to_be_visible()


@pytest.mark.parametrize("lang,forbidden", [("en", ["Si l’employeur", "Si l'employeur", "Entreprise :", "Profil recherché :"]),
                                            ("ar", ["Si l’employeur", "Si l'employeur", "Entreprise :", "Profil recherché :"])])
def test_offer_page_has_no_french_ui_text(page, console_errors, sample_offer, lang, forbidden):
    """Titres de sections et textes d'éligibilité traduits (dictionnaire, zéro token)."""
    page.goto(f"/{lang}/offres/{sample_offer}", wait_until="networkidle")
    body = page.locator("main").inner_text()
    for text in forbidden:
        assert text not in body, f"texte français « {text} » sur la page {lang}"
    shot(page, f"offre_sans_francais_{lang}")
