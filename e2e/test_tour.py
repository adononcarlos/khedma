"""Parcours complet à regarder à l'écran : .venv/bin/pytest e2e -m tour --headed --slowmo 400"""
import pytest
from playwright.sync_api import expect

from conftest import ROOT, filter_select, shot, ui_login, wait_param


@pytest.mark.tour
def test_guided_tour(page, console_errors, cvs):
    # 1. Accueil puis recherche
    page.goto("/fr", wait_until="networkidle")
    page.fill("main input[name=q]", "technicien")
    page.get_by_role("button", name="Rechercher").click()
    page.wait_for_url("**/fr/offres?q=technicien")
    # 2. Filtres combinés
    filter_select(page, "Métier").select_option("production")
    wait_param(page, "function", "production")
    filter_select(page, "Région").select_option("Casablanca-Settat")
    wait_param(page, "region", "Casablanca-Settat")
    shot(page, "tour_1_filtres", full_page=False)
    # 3. Connexion candidat, nouveau CV
    ui_login(page, "yassine.demo@example.com")
    page.set_input_files("input[name=cv]", str(ROOT / "backend/tests/fixtures/cv_exemple.txt"))  # CV d'origine du compte démo
    page.get_by_role("button", name="Remplacer mon CV").click()
    page.wait_for_url("**/espace?cv=ok")
    shot(page, "tour_2_espace", full_page=False)
    # 4. Offre recommandée, génération et téléchargement
    page.locator("main a[href*='/fr/offres/']").first.click()
    page.get_by_role("button", name="Générer mon CV + lettre").click()
    expect(page.get_by_text("CV et lettre prêts")).to_be_visible(timeout=120000)
    with page.expect_download():
        page.get_by_role("link", name="Télécharger le CV").click()
    shot(page, "tour_3_generation", full_page=False)
    # 5. Langue arabe, mode sombre
    page.get_by_role("link", name="ع", exact=True).click()
    page.wait_for_url("**/ar/**")
    page.get_by_role("button", name="الوضع الداكن").click()
    shot(page, "tour_4_arabe_sombre", full_page=False)
    # 6. Conseiller puis observatoire
    ui_login(page, "conseiller6@demo.khedma.ma")
    page.goto("/fr/conseiller", wait_until="networkidle")
    page.locator("main li button").first.click()
    expect(page.locator("main li a[href*='/offres/']").first).to_be_visible(timeout=30000)
    ui_login(page, "admin@demo.khedma.ma")
    page.goto("/fr/observatoire", wait_until="networkidle")
    page.mouse.wheel(0, 1500)
    shot(page, "tour_5_observatoire", full_page=False)
