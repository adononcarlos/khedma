"""Fixtures communes des tests de bout en bout.

Lancer (serveurs démarrés : API sur 8010, site sur 3010) :
  .venv/bin/pytest e2e                                  # invisible, rapide
  .venv/bin/pytest e2e -m tour --headed --slowmo 400    # parcours visible à l'écran, avec vidéo
Captures et vidéos : e2e/artefacts/
"""
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import httpx
import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "e2e" / "artefacts"
SHOTS = ART / "captures"
# Cible configurable : local par défaut, ou site en ligne (E2E_SITE, E2E_API, E2E_DB_URL)
API = os.environ.get("E2E_API", "http://localhost:8010/api")
SITE = os.environ.get("E2E_SITE", "http://localhost:3010")
TEST_DOMAIN = "test.khedma.ma"  # comptes créés par les tests, supprimés à la fin
DEMO_PASSWORD = "demo12345"


def _db_url() -> str:
    if os.environ.get("E2E_DB_URL"):
        return os.environ["E2E_DB_URL"]
    env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
    return env["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")


def pytest_configure(config):
    config.addinivalue_line("markers", "tour: parcours complet destiné au mode visible (--headed)")
    SHOTS.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def base_url():
    return SITE


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1366, "height": 900}, "locale": "fr-FR",
            "accept_downloads": True, "record_video_dir": str(ART / "videos")}


@pytest.fixture(scope="session")
def api():
    with httpx.Client(base_url=API, timeout=180) as c:
        assert c.get("/health").json() == {"status": "ok"}, "API non démarrée sur le port 8010"
        yield c


@pytest.fixture(scope="session")
def facets(api):
    return api.get("/offers/facets").json()


@pytest.fixture(scope="session")
def cvs():
    out = ART / "cv"
    subprocess.run([sys.executable, str(ROOT / "e2e" / "cv_factory.py"), str(out)], check=True)
    return json.loads((out / "manifest.json").read_text())


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_accounts():
    yield
    with psycopg.connect(_db_url()) as conn:
        ids = [r[0] for r in conn.execute("select id from users where email like %s", (f"%@{TEST_DOMAIN}",))]
        if ids:
            for table in ("applications", "generated_documents", "profiles"):
                conn.execute(f"delete from {table} where user_id = any(%s)", (ids,))
            conn.execute("delete from users where id = any(%s)", (ids,))


@pytest.fixture
def new_user(api):
    """Crée un compte candidat jetable ; renvoie (identifiants, en-têtes d'authentification)."""
    def make(**extra):
        email = f"e2e.{uuid.uuid4().hex[:10]}@{TEST_DOMAIN}"
        body = {"email": email, "password": "motdepasse123", "full_name": "Test E2E", "city": "Casablanca", **extra}
        r = api.post("/auth/register", json=body)
        assert r.status_code == 200, r.text
        return body, {"Authorization": f"Bearer {r.json()['token']}"}
    return make


def token_for(api, email: str, password: str = DEMO_PASSWORD) -> dict:
    r = api.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture
def console_errors(page):
    """Collecte les erreurs et avertissements de la console ; le test échoue s'il en reste."""
    errors = []
    page.on("console", lambda m: errors.append(f"{m.type}: {m.text[:200]}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {str(e)[:200]}"))
    yield errors
    assert not errors, "Erreurs console :\n" + "\n".join(errors)


def shot(page, name: str, full_page: bool = True):
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full_page)


def ui_login(page, email: str, password: str = DEMO_PASSWORD, lang: str = "fr"):
    page.context.clear_cookies()  # déconnexion préalable (la page de connexion redirige si déjà connecté)
    page.goto(f"/{lang}/connexion")
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", password)
    page.locator("form button[type=submit], form button").first.click()
    page.wait_for_url(f"**/{lang}/espace*")


def count_from_text(text: str) -> int:
    """« 1 804 offres » / « 1,804 offers » / chiffres arabes -> entier."""
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return int(re.sub(r"\D", "", text) or 0)


def wait_param(page, key: str, value: str, timeout_ms: int = 15000):
    """Attend que l'URL porte key=value (valeur décodée), puis que la page ait fini de se mettre à jour."""
    from urllib.parse import parse_qs, urlparse

    waited = 0
    while parse_qs(urlparse(page.url).query).get(key) != [value]:
        assert waited < timeout_ms, f"l'URL n'a pas reçu {key}={value} : {page.url}"
        page.wait_for_timeout(100)
        waited += 100
    page.wait_for_load_state("networkidle")


def filter_select(page, label: str):
    """Liste déroulante d'un filtre, repérée par son libellé EXACT (« Source » ≠ « Ressources humaines »)."""
    import re as _re

    return page.locator("label").filter(has=page.locator("span", has_text=_re.compile(f"^{_re.escape(label)}$"))).locator("select")
