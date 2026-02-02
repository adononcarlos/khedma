"""Connecteur Indeed Maroc, via l'API Firecrawl (Indeed bloque les robots classiques).

Coût : 1 crédit Firecrawl par page de liste (~15 offres) et 1 par fiche détail.
Les fiches détail sont donc optionnelles : sans elles, on garde l'extrait de la liste.
"""
import asyncio
import re
from typing import AsyncIterator
from urllib.parse import parse_qs, urlparse

import httpx

from app.config import settings
from app.sourcing.connectors.base import Connector, RawOffer

LIST_URL = "https://ma.indeed.com/jobs?q={q}&l={city}&sort=date"
# Indeed ignore la pagination servie à Firecrawl : on varie la localisation pour couvrir le pays
# Recherches métiers pour diversifier les secteurs (IT, data, IA, ingénierie, finance)
JUNIOR_SEARCHES = [("jeune diplômé", "Maroc"), ("stage", "Maroc"), ("junior", "Maroc"), ("actuaire", "Maroc"),
                   ("finance junior", "Maroc"), ("assistant administratif", "Maroc"), ("agent de sécurité", "Maroc"),
                   ("chargé clientèle", "Maroc")]
SEARCHES = [("développeur", "Maroc"), ("data", "Maroc"), ("intelligence artificielle", "Maroc"), ("ingénieur", "Maroc"),
            ("analyste", "Maroc"), ("marketing digital", "Maroc"), ("comptable", "Maroc")]
CITIES = ["Maroc", "Casablanca", "Rabat", "Tanger", "Marrakech", "Agadir", "Fès", "Meknès", "Oujda",
          "Kénitra", "Tétouan", "El Jadida", "Salé", "Mohammedia", "Nador", "Béni Mellal", "Laâyoune"]
VIEW_URL = "https://ma.indeed.com/viewjob?jk={jk}"
FIRECRAWL = "https://api.firecrawl.dev/v2/scrape"

_BLOCK = re.compile(r"^(?P<title>.+?)\]\((?P<href>https://ma\.indeed\.com/[^)]*jk=[^)]*)\)(?P<meta>[^\n]*)", re.S)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\\", "")).strip(" |-")


def parse_listing(markdown: str) -> list[dict]:
    jobs = []
    for chunk in markdown.split("### [")[1:]:
        m = _BLOCK.match(chunk)
        if not m:
            continue
        jk = parse_qs(urlparse(m.group("href")).query).get("jk", [None])[0]
        meta = [_clean(p) for p in m.group("meta").split("<br>") if _clean(p)]
        body = chunk[m.end():].split("View all")[0]
        snippet = "\n".join(
            _clean(l.lstrip("- ")) for l in body.splitlines()
            if _clean(l.lstrip("- ")) and not l.strip().startswith("|")
        )
        if jk:
            jobs.append({
                "jk": jk,
                "title": _clean(m.group("title")),
                "company": meta[0] if len(meta) >= 2 else None,
                "city": meta[-1] if meta else None,
                "snippet": snippet or None,
            })
    return jobs


class IndeedConnector(Connector):
    key = "indeed"
    name = "Indeed"
    base_url = "https://ma.indeed.com"
    detail_concurrency = 1  # plan Firecrawl gratuit : débit limité

    def __init__(self, with_details: bool = False, it_searches: bool = False, junior: bool = False, **kw):
        super().__init__(**kw)
        self.with_details = with_details
        self.it_searches = it_searches  # recherches par métier (IT, data, IA…) plutôt que par ville
        self.junior = junior  # jeunes diplômés, tous secteurs
        if not settings.firecrawl_api_key:
            raise RuntimeError("FIRECRAWL_API_KEY manquante dans .env")

    async def _scrape(self, url: str) -> str:
        for attempt in range(5):
            r = await self.client.post(
                FIRECRAWL,
                headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                timeout=120,
            )
            if r.status_code == 429 and attempt < 4:  # limite de débit du plan : on attend puis on réessaie
                await asyncio.sleep(float(r.headers.get("retry-after", 0)) or 15 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()["data"]["markdown"]
        raise RuntimeError("Firecrawl : limite de débit persistante")

    async def list_offers(self, max_pages: int = 2) -> AsyncIterator[RawOffer]:
        seen: set[str] = set()
        plan = JUNIOR_SEARCHES if self.junior else SEARCHES if self.it_searches else [("", c) for c in CITIES]
        for q, city in plan[:max_pages]:
            try:
                md = await self._scrape(LIST_URL.format(q=q, city=city))
            except httpx.HTTPError:
                continue
            jobs = [j for j in parse_listing(md) if j["jk"] not in seen]
            for j in jobs:
                seen.add(j["jk"])
                yield RawOffer(
                    source=self.key, source_ref=j["jk"], url=VIEW_URL.format(jk=j["jk"]),
                    title=j["title"], company=j["company"], city=j["city"], description=j["snippet"],
                )

    async def fetch_detail(self, offer: RawOffer) -> RawOffer:
        if not self.with_details:
            return offer
        md = await self._scrape(offer.url)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)  # liens -> texte
        m = re.search(r"#+ Full job description\s*(.+?)(?:\n#+ Company and salary information|\nReport job|$)", text, re.S)
        if m and len(m.group(1).strip()) > 40:
            offer.description = m.group(1).strip()[:8000]
        jt = re.search(r"## Job type\s*(.+?)\n#", text, re.S)
        if jt:
            offer.contract_raw = ", ".join(l.strip() for l in jt.group(1).splitlines() if l.strip())[:120]
        return offer
