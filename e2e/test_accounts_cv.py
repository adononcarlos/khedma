"""Comptes, dépôt de faux CV, recommandations, génération CV + lettre (langue de l'offre, une page, cache)."""
import io
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import expect
from pypdf import PdfReader

from conftest import ART, TEST_DOMAIN, shot, ui_login


def test_register_logout_login_ui(page, console_errors):
    email = f"e2e.ui.{uuid.uuid4().hex[:8]}@{TEST_DOMAIN}"
    page.goto("/fr/connexion")
    page.get_by_role("button", name="Pas encore de compte ? Créer un compte").click()
    page.fill("input[name=full_name]", "Nadia Test")
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", "motdepasse123")
    page.fill("input[name=city]", "Rabat")
    page.check("input[name=anapec]")
    page.get_by_role("button", name="Créer mon compte").click()
    page.wait_for_url("**/fr/espace")
    expect(page.get_by_role("heading", name="Bonjour Nadia")).to_be_visible()
    shot(page, "compte_nouveau_sans_cv")
    page.get_by_role("button", name="Déconnexion").click()
    page.wait_for_url("**/fr")
    ui_login(page, email, "motdepasse123")
    expect(page.get_by_role("heading", name="Bonjour Nadia")).to_be_visible()


@pytest.mark.parametrize("email,password,expected", [
    ("yassine.demo@example.com", "mauvais-mdp", "Email ou mot de passe incorrect"),
    ("inconnu@example.com", "demo12345", "Email ou mot de passe incorrect"),
])
def test_login_errors(page, console_errors, email, password, expected):
    page.goto("/fr/connexion")
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", password)
    page.get_by_role("button", name="Se connecter").click()
    expect(page.get_by_text(expected)).to_be_visible()


def test_register_errors(api):
    assert api.post("/auth/register", json={"email": "yassine.demo@example.com", "password": "motdepasse123",
                                            "full_name": "X"}).status_code == 409
    assert api.post("/auth/register", json={"email": f"court@{TEST_DOMAIN}", "password": "123",
                                            "full_name": "X"}).status_code == 422
    assert api.post("/auth/register", json={"email": "pas-un-email", "password": "motdepasse123",
                                            "full_name": "X"}).status_code == 422


def test_invalid_cv_files(api, new_user, cvs):
    _, headers = new_user()
    for bad in cvs["invalid"]:
        path = Path(bad["path"])
        r = api.post("/me/cv", headers=headers, files={"file": (path.name, path.read_bytes())})
        assert r.status_code == bad["status"], f"{bad['slug']} : {r.status_code} {r.text[:120]}"


def test_invalid_cv_shows_error_in_ui(page, console_errors, new_user, cvs):
    creds, _ = new_user()
    ui_login(page, creds["email"], creds["password"])
    page.set_input_files("input[name=cv]", next(b["path"] for b in cvs["invalid"] if b["slug"] == "scan_sans_texte"))
    page.get_by_role("button", name="Analyser mon CV").click()
    expect(page.get_by_text("Impossible de lire le texte du CV")).to_be_visible()
    shot(page, "cv_invalide_message", full_page=False)


def _pages(pdf: bytes) -> int:
    return len(PdfReader(io.BytesIO(pdf)).pages)


@pytest.mark.parametrize("idx", range(6), ids=lambda i: f"cv{i}")
def test_fake_cv_full_journey(page, console_errors, api, new_user, cvs, idx):
    """Dépôt du CV dans l'interface -> profil -> offres recommandées -> génération -> PDF téléchargés."""
    per = cvs["valid"][idx]
    creds, headers = new_user(city=per["city"])
    ui_login(page, creds["email"], creds["password"])
    page.set_input_files("input[name=cv]", per["path"])
    page.get_by_role("button", name="Analyser mon CV").click()
    page.wait_for_url("**/espace?cv=ok")
    expect(page.get_by_text("CV analysé")).to_be_visible()

    me = api.get("/me", headers=headers).json()
    skills = {s["id"] for s in me["profile"]["skills"]}
    assert skills & set(per["expect_skills"]), f"{per['slug']} : compétences extraites {skills}"
    assert me["profile"]["cv_language"] == per["lang"], f"{per['slug']} : langue détectée {me['profile']['cv_language']}"
    matches = api.get("/me/matches", headers=headers, params={"limit": 5}).json()
    assert matches["items"], f"{per['slug']} : aucune offre recommandée"
    assert all(0 <= m["score"] <= 100 for m in matches["items"])
    shot(page, f"cv_{per['slug']}_espace")

    offer = matches["items"][0]["offer"]
    page.goto(f"/fr/offres/{offer['id']}", wait_until="networkidle")
    page.get_by_role("button", name="Générer mon CV + lettre").click()
    expect(page.get_by_text("CV et lettre prêts")).to_be_visible(timeout=120000)
    shot(page, f"cv_{per['slug']}_genere", full_page=False)
    for label, kind in (("Télécharger le CV", "cv"), ("Télécharger la lettre", "lettre")):
        with page.expect_download() as dl:
            page.get_by_role("link", name=label).click()
        path = ART / "pdf" / f"{per['slug']}_{kind}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        dl.value.save_as(path)
        assert _pages(path.read_bytes()) == 1, f"{per['slug']} : {kind} sur plus d'une page"

    docs = api.post(f"/me/offers/{offer['id']}/documents", headers=headers).json()
    assert docs["cached"] is True, "la deuxième génération doit sortir du cache"
    assert docs["language"] == offer["language"], "les documents doivent être dans la langue de l'offre"
    page.get_by_role("button", name="J'ai postulé").click()
    expect(page.get_by_text("Candidature enregistrée")).to_be_visible()


def test_generate_requires_login_and_cv(page, console_errors, api, new_user):
    offer_id = api.get("/offers", params={"size": 1}).json()["items"][0]["id"]
    page.goto(f"/fr/offres/{offer_id}", wait_until="networkidle")
    expect(page.get_by_role("button", name="Générer mon CV + lettre")).to_be_disabled()
    expect(page.get_by_role("link", name="Connectez-vous pour générer")).to_be_visible()
    creds, headers = new_user()
    ui_login(page, creds["email"], creds["password"])
    page.goto(f"/fr/offres/{offer_id}", wait_until="networkidle")
    page.get_by_role("button", name="Générer mon CV + lettre").click()
    expect(page.get_by_role("link", name="Déposez d'abord votre CV")).to_be_visible()
    assert api.post(f"/me/offers/{offer_id}/documents", headers=headers).status_code == 409
