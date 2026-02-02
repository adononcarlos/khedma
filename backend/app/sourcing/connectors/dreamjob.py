"""Connecteur Dreamjob.ma via son flux RSS public (poli : 1 requête par page de 30 articles)."""
import re
from email.utils import parsedate_to_datetime
from typing import AsyncIterator

from app.sourcing.connectors.base import Connector, RawOffer
from app.sourcing.markdown import html_to_markdown

FEED = "https://www.dreamjob.ma/feed/?paged={page}"


def _tag(item: str, name: str) -> str | None:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", item, re.S)
    if not m:
        return None
    return re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip()).strip()


class DreamjobConnector(Connector):
    key = "dreamjob"
    name = "Dreamjob"
    base_url = "https://www.dreamjob.ma"

    async def list_offers(self, max_pages: int = 4) -> AsyncIterator[RawOffer]:
        for page in range(1, max_pages + 1):
            xml = (await self.get(FEED.format(page=page))).text
            items = re.findall(r"<item>(.*?)</item>", xml, re.S)
            if not items:
                return
            for it in items:
                link = _tag(it, "link")
                cats = [re.sub(r"^<!\[CDATA\[|\]\]>$", "", c) for c in re.findall(r"<category>(.*?)</category>", it, re.S)]
                city = next((c.split(" à ", 1)[1] for c in cats if c.startswith("Offres d'Emploi à ")), None)
                html = _tag(it, "content:encoded") or _tag(it, "description") or ""
                title = re.sub(r"&#8217;|&rsquo;", "’", _tag(it, "title") or "")
                title = re.sub(r"&#8211;|&#8212;", "-", title).replace("&amp;", "&")
                yield RawOffer(
                    source=self.key, source_ref=link.rstrip("/").rsplit("/", 1)[-1], url=link, title=title,
                    city=city, description=re.split(r"\s*L.article .{5,200} est apparu en premier sur", html_to_markdown(html))[0].replace("[…]", "…")[:6000],
                    contract_raw="Concours" if "Emploi Public" in cats else None,
                    posted_at=parsedate_to_datetime(_tag(it, "pubDate")).date() if _tag(it, "pubDate") else None,
                )
