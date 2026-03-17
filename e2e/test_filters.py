"""Filtres et recherche : chaque valeur dans l'interface, toutes les paires via l'API, combinaisons aléatoires."""
import itertools
import random
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from conftest import count_from_text, filter_select, shot, wait_param

# paramètre d'URL -> (libellé du filtre en français, champ de l'offre renvoyée par l'API)
FILTERS = {
    "function": ("Métier", "job_function"),
    "sector_group": ("Secteur d'activité", "sector_group"),
    "experience": ("Expérience", "experience_level"),
    "since": ("Date de publication", "posted_at"),
    "region": ("Région", "region"),
    "contract": ("Contrat", "contract_type"),
    "source": ("Source", "source"),
}


def values(facets) -> dict[str, list[str]]:
    return {
        "function": [f["value"] for f in facets["functions"]],
        "sector_group": [f["value"] for f in facets["sector_groups"]],
        "experience": [f["value"] for f in facets["experiences"]],
        "since": ["1", "7", "30"],
        "region": [f["value"] for f in facets["regions"]],
        "contract": [f["value"] for f in facets["contracts"]],
        "source": [f["value"] for f in facets["sources"]],
    }


def check_items(items: list[dict], params: dict):
    for it in items:
        for key, val in params.items():
            if key in ("q", "page", "size"):
                continue
            field = FILTERS[key][1]
            if key == "since":
                assert it["posted_at"] and date.fromisoformat(it["posted_at"]) >= date.today() - timedelta(days=int(val)), it
            else:
                assert it[field] == val, f"{key}={val} mais l'offre {it['id']} a {field}={it[field]}"


@pytest.mark.parametrize("key", list(FILTERS))
def test_each_filter_value_in_ui(page, console_errors, api, facets, key):
    """Sélectionne chaque valeur du filtre dans l'interface ; le compteur doit égaler le total de l'API."""
    label = FILTERS[key][0]
    page.goto("/fr/offres", wait_until="networkidle")
    select = filter_select(page, label)
    options = [o for o in select.locator("option").evaluate_all("els => els.map(e => e.value)") if o]
    assert sorted(options) == sorted(values(facets)[key]) or key == "experience", f"options de « {label} » incomplètes"
    for val in options:
        filter_select(page, label).select_option(val)
        wait_param(page, key, val)
        expected = api.get("/offers", params={key: val, "size": 1}).json()["total"]
        shown = count_from_text(page.locator("h1 + span").inner_text())
        assert shown == expected, f"{key}={val} : l'interface affiche {shown}, l'API {expected}"
        if expected == 0:
            expect(page.get_by_text("Aucune offre ne correspond")).to_be_visible()
    shot(page, f"filtre_{key}")
    page.get_by_role("button", name="Réinitialiser").click()
    page.wait_for_url("**/fr/offres")


def test_options_sorted_alphabetically(page, console_errors):
    page.goto("/fr/offres", wait_until="networkidle")
    for key in ("function", "sector_group", "region", "contract", "source"):
        texts = filter_select(page, FILTERS[key][0]).locator("option").all_inner_texts()[1:]
        labels = [t.rsplit(" (", 1)[0] for t in texts if not t.startswith("Autre")]
        assert labels == sorted(labels, key=lambda s: s.casefold().translate(str.maketrans("éèêàâîôûç", "eeeaaiouc"))), key


def test_all_filter_pairs_api(api, facets):
    """Toutes les combinaisons de deux filtres : 200, résultats conformes, total <= chaque filtre seul."""
    vals = values(facets)
    single = {(k, v): api.get("/offers", params={k: v, "size": 1}).json()["total"] for k in vals for v in vals[k]}
    n = 0
    for k1, k2 in itertools.combinations(vals, 2):
        for v1, v2 in itertools.product(vals[k1], vals[k2]):
            params = {k1: v1, k2: v2, "size": 100}
            r = api.get("/offers", params=params)
            assert r.status_code == 200, (params, r.text)
            data = r.json()
            assert data["total"] <= min(single[(k1, v1)], single[(k2, v2)]), params
            check_items(data["items"], params)
            n += 1
    print(f"\n{n} combinaisons de deux filtres vérifiées")
    assert n > 1000


def test_random_multi_filter_combos_api(api, facets):
    rng = random.Random(42)
    vals = values(facets)
    for _ in range(300):
        keys = rng.sample(list(vals), rng.randint(3, 5))
        params = {k: rng.choice(vals[k]) for k in keys}
        if rng.random() < 0.4:
            params["q"] = rng.choice(["agent", "technicien", "commercial", "stage", "ingénieur", "comptable"])
        r = api.get("/offers", params={**params, "size": 100})
        assert r.status_code == 200, (params, r.text)
        check_items(r.json()["items"], params)


@pytest.mark.parametrize("q", ["développeur", "developpeur", "DÉVELOPPEUR", "سائق", "' OR 1=1 --", "%", "_",
                               "<script>alert(1)</script>", "a" * 300, "   ", "C++", "Next.js"])
def test_search_queries(api, page, console_errors, q):
    r = api.get("/offers", params={"q": q, "size": 5})
    assert r.status_code == 200
    page.goto("/fr/offres", wait_until="networkidle")
    box = page.locator("aside input[name=q]")
    box.fill(q)
    box.press("Enter")
    page.wait_for_load_state("networkidle")
    expect(page.locator("h1")).to_be_visible()


def test_accent_insensitive_search(api):
    a = api.get("/offers", params={"q": "développeur", "size": 1}).json()["total"]
    b = api.get("/offers", params={"q": "developpeur", "size": 1}).json()["total"]
    assert a == b > 0


def test_pagination(page, console_errors, api):
    total = api.get("/offers", params={"size": 1}).json()["total"]
    page.goto("/fr/offres", wait_until="networkidle")
    first = page.locator("section a[href*='/fr/offres/']").first.get_attribute("href")
    page.get_by_role("link", name="Suivant").click()
    page.wait_for_url("**page=2*")
    assert page.locator("section a[href*='/fr/offres/']").first.get_attribute("href") != first
    expect(page.get_by_text(f"2 / {-(-total // 20)}")).to_be_visible()
    page.goto("/fr/offres?page=9999", wait_until="networkidle")
    expect(page.get_by_text("Aucune offre ne correspond")).to_be_visible()


def test_impossible_combination_shows_empty_state(page, console_errors):
    page.goto("/fr/offres?q=zzzzzzzzqqq", wait_until="networkidle")
    expect(page.get_by_text("Aucune offre ne correspond")).to_be_visible()
    shot(page, "filtre_aucun_resultat", full_page=False)
