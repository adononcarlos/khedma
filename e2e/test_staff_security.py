"""Espace conseiller, observatoire, contrôle d'accès et échappement des contenus."""
import pytest
from playwright.sync_api import expect

from conftest import count_from_text, shot, token_for, ui_login


@pytest.mark.parametrize("lang", ["fr", "ar", "en"])
def test_counselor_caseload_and_suggestions(page, console_errors, lang):
    ui_login(page, "conseiller6@demo.khedma.ma")
    page.goto(f"/{lang}/conseiller", wait_until="networkidle")
    rows = page.locator("main li.rounded-2xl")
    assert rows.count() > 10
    btn = page.locator("main li button").first
    btn.click()
    expect(page.locator("main li a[href*='/offres/']").first).to_be_visible(timeout=30000)
    shot(page, f"conseiller_{lang}")


def test_counselor_sees_only_own_region(api):
    h = token_for(api, "conseiller6@demo.khedma.ma")
    data = api.get("/counselor/caseload", headers=h).json()
    assert data["counselor"]["region"] == "Casablanca-Settat"
    other = token_for(api, "conseiller1@demo.khedma.ma")
    foreign = api.get("/counselor/caseload", headers=other).json()["items"][0]["id"]
    assert api.get(f"/counselor/seekers/{foreign}/suggestions", headers=h).status_code == 404


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_observatory(page, console_errors, api, scheme):
    page.emulate_media(color_scheme=scheme)
    ui_login(page, "admin@demo.khedma.ma")
    page.goto("/fr/observatoire", wait_until="networkidle")
    total = api.get("/offers", params={"size": 1}).json()["total"]
    tile = page.get_by_text("Offres actives", exact=True).locator("..")
    assert count_from_text(tile.inner_text()) == total
    expect(page.get_by_text("Tension par métier")).to_be_visible()
    page.get_by_text("Voir les données").first.click()
    expect(page.locator("details[open] table")).to_be_visible()
    page.locator("main li[tabindex='0']").first.focus()  # infobulle au clavier
    shot(page, f"observatoire_{scheme}")


def test_seeker_cannot_open_staff_pages(page, console_errors):
    ui_login(page, "yassine.demo@example.com")
    for path in ("/fr/conseiller", "/fr/observatoire"):
        page.goto(path, wait_until="networkidle")
        expect(page.get_by_text("Espace réservé aux conseillers")).to_be_visible()


def test_api_access_control(api, new_user):
    _, seeker = new_user()
    assert api.get("/me").status_code == 401
    assert api.get("/me", headers={"Authorization": "Bearer faux.jeton"}).status_code == 401
    assert api.get("/admin/observatory", headers=seeker).status_code == 403
    assert api.get("/counselor/caseload", headers=seeker).status_code == 403
    assert api.post("/admin/ghosts/recompute", headers=token_for(api, "conseiller6@demo.khedma.ma")).status_code == 403


def test_documents_are_private(api, new_user):
    yassine = token_for(api, "yassine.demo@example.com")
    offer_id = api.get("/me/matches", headers=yassine, params={"limit": 1}).json()["items"][0]["offer"]["id"]
    doc_id = api.post(f"/me/offers/{offer_id}/documents", headers=yassine).json()["cv"]["id"]
    _, stranger = new_user()
    assert api.get(f"/me/documents/{doc_id}.pdf", headers=stranger).status_code == 404
    assert api.get(f"/me/documents/{doc_id}.pdf", headers=yassine).status_code == 200


def test_html_in_user_content_is_escaped(page, api, new_user):
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    creds, _ = new_user(full_name="<img src=x onerror=alert(1)>Zed")
    ui_login(page, creds["email"], creds["password"])
    expect(page.get_by_role("heading", name="Bonjour <img")).to_be_visible()
    assert not dialogs, "du HTML injecté a été exécuté"
