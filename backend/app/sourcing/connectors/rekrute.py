"""Connecteur ReKrute (cadres, IT, ingénierie). Liste HTML riche + fiche détail."""
import re
from typing import AsyncIterator

from selectolax.parser import HTMLParser

from app.sourcing.connectors.base import Connector, RawOffer
from app.sourcing.markdown import tidy
from app.sourcing.normalize import parse_date

BASE = "https://www.rekrute.com"
LIST_URL = BASE + "/offres.html?p={page}&s=1&o=1"


def _field(text: str, label: str) -> str | None:
    m = re.search(re.escape(label) + r"\s*:\s*\|\s*([^|]+)", text)
    return m.group(1).strip() if m else None


class RekruteConnector(Connector):
    key = "rekrute"
    name = "ReKrute"
    base_url = BASE

    async def list_offers(self, max_pages: int = 10) -> AsyncIterator[RawOffer]:
        for page in range(1, max_pages + 1):
            tree = HTMLParser((await self.get(LIST_URL.format(page=page))).text)
            items = tree.css("li.post-id")
            if not items:
                return
            for it in items:
                a = next((x for x in it.css("a.titreJob") or it.css("a") if "offre-emploi" in (x.attributes.get("href") or "")
                          and x.text(strip=True) and "4K" not in x.text()), None)
                if a is None:
                    continue
                text = re.sub(r"(\s*\|\s*)+", " | ", it.text(separator=" | "))
                head = a.text(strip=True)
                title, _, city = head.rpartition("|") if "|" in head else (head, "", "")
                pub = re.search(r"Publication : du \| (\d\d/\d\d/\d{4})", text)
                summary = next((p.text(strip=True) for p in it.css("div.info span, div.holder div.info")), None)
                yield RawOffer(
                    source=self.key, source_ref=it.attributes.get("id") or a.attributes["href"],
                    url=BASE + a.attributes["href"].split("?")[0], title=title.strip() or head,
                    city=re.sub(r"\s*\(Maroc\)\s*", "", city).strip() or None,
                    sector=_field(text, "Secteur d'activité"), contract_raw=_field(text, "Type de contrat proposé"),
                    education=_field(text, "Niveau d'étude demandé"), description=summary,
                    posted_at=parse_date(pub.group(1)) if pub else None,
                    positions=int(p) if (p := _field(text, "Postes proposés") or "").isdigit() else None,
                    extra={"experience": _field(text, "Expérience requise"), "occupation": _field(text, "Fonction")},
                )

    async def fetch_detail(self, offer: RawOffer) -> RawOffer:
        tree = HTMLParser((await self.get(offer.url)).text)
        sections = []
        for blc in tree.css("div.col-md-12.blc"):
            h = blc.css_first("h2")
            label = h.text(strip=True).rstrip(" :") if h else ""
            if label not in ("Entreprise", "Poste", "Profil recherché", "Traits de personnalité souhaités"):
                continue
            body = blc.text(separator="\n").replace(h.text(), "", 1).strip()
            parts = [p.strip(" .;\n") for p in re.split(r"\s*;\s*|\n+", body) if len(p.strip()) > 2]
            name = {"Poste": "Missions", "Traits de personnalité souhaités": "Qualités recherchées"}.get(label, label)
            if label == "Entreprise":
                sections.append(f"**{name} :**\n" + " ".join(parts))
            else:
                sections.append(f"**{name} :**\n" + "\n".join(f"- {p}" for p in parts))
        if sections:
            offer.description = tidy("\n\n".join(sections))
        return offer
