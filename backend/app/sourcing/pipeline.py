"""Ingestion : liste -> upsert -> détail (nouvelles offres seulement) -> normalisation -> dédoublonnage."""
import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.matching.skills import extract_skills
from app.sourcing.markdown import bulletize, reflow, structure_plain, tidy
from app.sourcing.taxonomy import experience_level, job_function, sector_group
from app.models import Offer
from app.sourcing.connectors.base import Connector, RawOffer
from app.sourcing.normalize import (
    city_to_region,
    clean_city,
    detect_language,
    fingerprint,
    normalize_contract,
)

log = logging.getLogger("khedma.pipeline")


def _apply(offer: Offer, raw: RawOffer) -> None:
    offer.url = raw.url
    offer.title = raw.title
    offer.company = raw.company
    offer.city = clean_city(raw.city)
    offer.region = city_to_region(raw.city) or city_to_region((raw.extra or {}).get("agence"))
    offer.sector = raw.sector
    offer.contract_raw = raw.contract_raw
    offer.contract_type = normalize_contract(raw.contract_raw)
    offer.education = raw.education
    extra = raw.extra or {}
    offer.experience = extra.get("experience")
    offer.salary = extra.get("salary")
    offer.occupation = extra.get("occupation")
    offer.languages = raw.languages
    # Descriptions ANAPEC en texte à libellés -> Markdown structuré ; les autres sont déjà en Markdown
    offer.description = bulletize(structure_plain(raw.description)) if raw.source == "anapec" and raw.description else (reflow(tidy(raw.description)) if raw.description else None)
    offer.positions = raw.positions
    offer.posted_at = raw.posted_at
    offer.start_date = raw.start_date
    offer.language = detect_language(f"{raw.title}\n{raw.description or ''}")
    offer.fingerprint = fingerprint(raw.title, raw.company, offer.city)
    offer.job_function = job_function(raw.title, extra.get("occupation"), offer.description)
    offer.sector_group = sector_group(raw.sector, raw.title)
    offer.experience_level = experience_level(offer.experience, offer.description)
    offer.skills = extract_skills("\n".join(filter(None, [raw.title, extra.get("occupation"), raw.education, raw.description])))
    offer.raw = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in asdict(raw).items()}


def _mark_duplicate(session: Session, offer: Offer) -> None:
    """Si la même offre existe déjà sur une autre source, on la rattache à l'offre canonique."""
    canonical = session.scalar(
        select(Offer.id)
        .where(Offer.fingerprint == offer.fingerprint, Offer.source != offer.source, Offer.duplicate_of.is_(None))
        .order_by(Offer.id)
        .limit(1)
    )
    offer.duplicate_of = canonical


async def ingest(connector: Connector, max_pages: int = 3, detail_concurrency: int | None = None) -> dict:
    stats = {"seen": 0, "new": 0, "updated": 0, "details": 0, "errors": 0}
    now = datetime.now(timezone.utc)
    to_detail: list[tuple[int, RawOffer]] = []

    with SessionLocal() as session:
        async for raw in connector.list_offers(max_pages=max_pages):
            stats["seen"] += 1
            offer = session.scalar(
                select(Offer).where(Offer.source == raw.source, Offer.source_ref == raw.source_ref)
            )
            if offer is None:
                offer = Offer(source=raw.source, source_ref=raw.source_ref)
                _apply(offer, raw)
                session.add(offer)
                session.flush()
                stats["new"] += 1
            else:
                offer.last_seen = now
                offer.status = "active"
                stats["updated"] += 1
            if not offer.detail_fetched:
                to_detail.append((offer.id, raw))
            if stats["seen"] % 15 == 0:  # un commit par page de liste
                session.commit()
        session.commit()

    sem = asyncio.Semaphore(detail_concurrency or connector.detail_concurrency)

    async def one(offer_id: int, raw: RawOffer):
        async with sem:
            try:
                raw = await connector.fetch_detail(raw)
            except Exception as e:  # une fiche en erreur ne bloque pas l'ingestion
                log.warning("détail %s/%s en échec : %s", raw.source, raw.source_ref, e)
                stats["errors"] += 1
                return
        with SessionLocal() as session:
            offer = session.get(Offer, offer_id)
            _apply(offer, raw)
            offer.detail_fetched = True
            _mark_duplicate(session, offer)
            session.commit()
            stats["details"] += 1

    await asyncio.gather(*(one(i, r) for i, r in to_detail))
    await connector.aclose()
    return stats


async def refetch_details(connector: Connector, limit: int = 500) -> dict:
    """Récupère les fiches détail manquantes (échecs précédents) sans relire les listes."""
    with SessionLocal() as session:
        rows = session.scalars(
            select(Offer).where(Offer.source == connector.key, Offer.detail_fetched.is_(False)).limit(limit)
        ).all()
        pending = [(o.id, RawOffer(source=o.source, source_ref=o.source_ref, url=o.url, title=o.title,
                                   company=o.company, city=o.city, description=o.description,
                                   posted_at=o.posted_at)) for o in rows]
    stats = {"pending": len(pending), "details": 0, "errors": 0}
    sem = asyncio.Semaphore(connector.detail_concurrency)

    async def one(offer_id: int, raw: RawOffer):
        async with sem:
            try:
                raw = await connector.fetch_detail(raw)
            except Exception as e:
                log.warning("détail %s/%s en échec : %s", raw.source, raw.source_ref, e)
                stats["errors"] += 1
                return
        with SessionLocal() as session:
            offer = session.get(Offer, offer_id)
            _apply(offer, raw)
            offer.detail_fetched = True
            _mark_duplicate(session, offer)
            session.commit()
            stats["details"] += 1

    await asyncio.gather(*(one(i, r) for i, r in pending))
    await connector.aclose()
    return stats
