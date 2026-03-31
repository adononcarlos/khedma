"""Avis des utilisateurs : bandeau défilant de l'accueil, page d'avis et ses filtres, dates, mobile."""
from datetime import date

import pytest
from playwright.sync_api import expect

from conftest import count_from_text, shot

LANGS = ["fr", "ar", "en"]
TOTAL, STUDENTS, STUDENTS_EN = 36, 13, 5
LAUNCH = date(2026, 3, 2)


@pytest.mark.parametrize("lang", LANGS)
def test_home_marquee(page, console_errors, lang):
    page.goto(f"/{lang}", wait_until="networkidle")
    section = page.locator("section[aria-labelledby=avis-titre]")
    expect(section).to_be_visible()
    # chaque avis figure deux fois (boucle), la copie est cachée aux lecteurs d'écran
    expect(section.locator("figure")).to_have_count(2 * TOTAL)
    expect(section.locator("[aria-hidden=true] figure")).to_have_count(TOTAL)
    # les avis gardent leur langue et leur sens d'écriture
    for l in LANGS:
        assert section.locator(f"figure[lang={l}]").count() > 0, f"aucun avis en {l}"
    assert section.locator("figure[lang=ar]").count() == section.locator("figure[lang=ar][dir=rtl]").count()
    track = section.locator(".marquee-track").first
    x1 = track.bounding_box()["x"]
    page.wait_for_timeout(1500)
    assert track.bounding_box()["x"] != x1, "le bandeau ne défile pas"
    section.locator(f"a[href='/{lang}/avis']").click()
    page.wait_for_url(f"**/{lang}/avis")
    expect(page.locator("main figure")).to_have_count(TOTAL)
    shot(page, f"avis_{lang}", full_page=False)


def test_marquee_pauses_on_hover(page, console_errors):
    page.goto("/fr", wait_until="networkidle")
    marquee = page.locator(".marquee").first
    marquee.scroll_into_view_if_needed()
    marquee.hover()
    track = marquee.locator(".marquee-track")
    x1 = track.bounding_box()["x"]
    page.wait_for_timeout(800)
    assert track.bounding_box()["x"] == x1, "le bandeau devrait s'arrêter au survol"


def test_reduced_motion(browser, base_url):
    ctx = browser.new_context(base_url=base_url, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto("/fr", wait_until="networkidle")
    assert page.locator(".marquee-track").first.evaluate("e => getComputedStyle(e).animationName") == "none"
    expect(page.locator(".marquee figure:visible")).to_have_count(TOTAL)  # copies masquées
    ctx.close()


def test_filters_and_stats(page, console_errors):
    page.goto("/fr/avis", wait_until="networkidle")
    tiles = page.locator("main .grid").first
    assert count_from_text(tiles.get_by_text("Avis", exact=True).locator("..").inner_text()) == TOTAL
    page.get_by_role("link", name="Étudiants internationaux").click()
    page.wait_for_url("**/fr/avis?profil=student")
    expect(page.locator("main figure")).to_have_count(STUDENTS)
    page.get_by_role("link", name="English").click()
    page.wait_for_url("**/fr/avis?profil=student&langue=en")
    expect(page.locator("main figure")).to_have_count(STUDENTS_EN)
    expect(page.locator("main figure[lang=en]")).to_have_count(STUDENTS_EN)
    assert count_from_text(tiles.get_by_text("Avis", exact=True).locator("..").inner_text()) == STUDENTS_EN
    page.get_by_role("link", name="Toutes les langues").click()
    page.wait_for_url("**/fr/avis?profil=student")
    page.goto("/fr/avis?profil=inconnu&langue=xx", wait_until="networkidle")  # paramètres invalides ignorés
    expect(page.locator("main figure")).to_have_count(TOTAL)


def test_dates_from_launch_to_today(page, console_errors):
    page.goto("/fr/avis", wait_until="networkidle")
    days = [date.fromisoformat(d) for d in page.locator("main figure time").evaluate_all("l => l.map(t => t.dateTime)")]
    assert len(days) == TOTAL
    assert days == sorted(days, reverse=True), "avis non triés du plus récent au plus ancien"
    today = date.today()
    assert LAUNCH <= days[-1] <= date(2026, 3, 31), f"le plus ancien avis devrait dater de mars 2026 ({days[-1]})"
    assert (today - days[0]).days <= 14, f"le plus récent avis devrait être récent ({days[0]})"
    assert all(LAUNCH <= d <= today for d in days)


@pytest.mark.parametrize("path", ["/fr", "/ar/avis", "/en/avis"])
def test_mobile(page, console_errors, path):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(path, wait_until="networkidle")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= 390, f"défilement horizontal sur mobile ({width}px) : {path}"


def test_nav_link_in_three_languages(page, console_errors):
    for lang, label in [("fr", "Avis"), ("ar", "الآراء"), ("en", "Reviews")]:
        page.goto(f"/{lang}/offres", wait_until="networkidle")
        page.locator("header nav").first.get_by_role("link", name=label, exact=True).click()
        page.wait_for_url(f"**/{lang}/avis")
