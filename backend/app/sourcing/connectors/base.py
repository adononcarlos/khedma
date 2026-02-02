import asyncio
import time
from dataclasses import dataclass, field
from datetime import date
from typing import AsyncIterator

import httpx

from app.config import settings


@dataclass
class RawOffer:
    """Offre telle que lue sur la source, avant normalisation."""

    source: str
    source_ref: str
    url: str
    title: str
    company: str | None = None
    city: str | None = None
    sector: str | None = None
    contract_raw: str | None = None
    education: str | None = None
    languages: dict | None = None
    description: str | None = None
    positions: int | None = None
    posted_at: date | None = None
    start_date: date | None = None
    extra: dict = field(default_factory=dict)


class Connector:
    """Un connecteur par source : liste paginée + fiche détail. Rythme limité par source."""

    key: str = ""
    name: str = ""
    base_url: str = ""
    verify_ssl: bool = True
    detail_concurrency: int = 2

    def __init__(self, delay_s: float | None = None):
        self.delay_s = settings.crawl_delay_s if delay_s is None else delay_s
        self._last = 0.0
        self._lock = asyncio.Lock()
        self.client = httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent, "Accept-Language": "fr-FR,fr;q=0.9"},
            timeout=30,
            follow_redirects=True,
            verify=self.verify_ssl,
        )

    async def get(self, url: str, **kw) -> httpx.Response:
        async with self._lock:  # politesse : une requête à la fois, espacées de delay_s
            wait = self._last + self.delay_s - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()
        for attempt in range(3):
            try:
                r = await self.client.get(url, **kw)
                r.raise_for_status()
                return r
            except (httpx.TransportError, httpx.HTTPStatusError):
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError("unreachable")

    def list_offers(self, max_pages: int) -> AsyncIterator[RawOffer]:
        raise NotImplementedError

    async def fetch_detail(self, offer: RawOffer) -> RawOffer:
        return offer

    async def aclose(self):
        await self.client.aclose()
