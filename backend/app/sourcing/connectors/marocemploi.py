"""Connecteur MarocEmploi.net (WordPress, 20 offres / page)."""
import re
from datetime import date
from typing import AsyncIterator

from selectolax.parser import HTMLParser

from app.sourcing.connectors.base import Connector, RawOffer
from app.sourcing.markdown import html_to_markdown, tidy

LIST_URL = "https://marocemploi.net/offre/?job_page={page}"
_MONTHS = {m: i for i, m in enumerate(["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
                                        "septembre", "octobre", "novembre", "décembre"], 1)}


def _fr_date(s: str | None) -> date | None:
    m = re.search(r"(\d{1,2})\s+([a-zéû]+)\s+(\d{4})", s or "")
    if m and m.group(2) in _MONTHS:
        return date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    return None


class MarocEmploiConnector(Connector):
    key = "marocemploi"
    name = "MarocEmploi"
    base_url = "https://marocemploi.net"

    async def list_offers(self, max_pages: int = 5) -> AsyncIterator[RawOffer]:
        seen: set[str] = set()
        for page in range(1, max_pages + 1):
            tree = HTMLParser((await self.get(LIST_URL.format(page=page))).text)
            links = [a for a in tree.css("a[href^='https://marocemploi.net/offre/']")
                     if re.fullmatch(r"https://marocemploi\.net/offre/[a-z0-9-]+/", a.attributes["href"])]
            new = [a for a in links if a.attributes["href"] not in seen]
            if not new:
                return
            for a in new:
                href = a.attributes["href"]
                seen.add(href)
                yield RawOffer(source=self.key, source_ref=href.rstrip("/").rsplit("/", 1)[-1], url=href,
                               title=a.text(strip=True) or href.rstrip("/").rsplit("/", 1)[-1].replace("-", " "))

    async def fetch_detail(self, offer: RawOffer) -> RawOffer:
        tree = HTMLParser((await self.get(offer.url)).text)
        art = tree.css_first("article")
        if art is None:
            return offer
        h1 = art.css_first("h1")
        if h1:
            offer.title = h1.text(strip=True)
        lines = [l.strip() for l in art.text(separator="\n").splitlines() if l.strip()]
        after = lambda k: next((lines[i + 1] for i, l in enumerate(lines[:-1]) if l == k), None)  # noqa: E731
        offer.contract_raw, offer.sector = after("Contrat"), after("Secteur")
        offer.city = (after("Localisation") or "").split(",")[0].strip() or None
        offer.posted_at = _fr_date(after("Publication"))
        if offer.title in lines:  # le titre apparaît dans le fil d'Ariane puis en h1 : l'entreprise suit le h1
            last = len(lines) - 1 - lines[::-1].index(offer.title)
            nxt = lines[last + 1] if last + 1 < len(lines) else ""
            offer.company = nxt if nxt and len(nxt) < 60 and not nxt.startswith("Publiée") else None
        # Sections utiles : missions, profil, compétences (on s'arrête avant « Prêt à envoyer »)
        parts = []
        for block in art.css(".me-job-description__content"):
            parts.append(html_to_markdown(block.html))
        if parts:
            offer.description = tidy("\n\n".join(parts).split("**Prêt à envoyer")[0])
        return offer
