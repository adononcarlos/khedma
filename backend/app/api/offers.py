from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.ai.translate import translate_offer, translate_titles
from app.matching.insights import offer_eligibility
from app.models import Offer
from app.sourcing.normalize import REGIONS

router = APIRouter(prefix="/api/offers", tags=["offres"])

SOURCES = {
    "anapec": {"name": "ANAPEC", "url": "https://anapec.ma"},
    "indeed": {"name": "Indeed", "url": "https://ma.indeed.com"},
    "rekrute": {"name": "ReKrute", "url": "https://www.rekrute.com"},
    "dreamjob": {"name": "Dreamjob", "url": "https://www.dreamjob.ma"},
    "marocemploi": {"name": "MarocEmploi", "url": "https://marocemploi.net"},
}


class OfferCard(BaseModel):
    id: int
    source: str
    source_name: str
    title: str
    company: str | None
    city: str | None
    region: str | None
    sector: str | None
    contract_type: str | None
    positions: int | None
    language: str
    posted_at: date | None
    salary: str | None
    job_function: str | None = None
    sector_group: str | None = None
    experience_level: str | None = None
    original_title: str | None = None  # renseigné quand le titre affiché est une traduction


class OfferDetail(OfferCard):
    url: str
    description: str | None
    education: str | None
    experience: str | None
    occupation: str | None
    languages: dict | None
    start_date: date | None
    contract_raw: str | None
    eligibility: list[dict] = []
    translated: bool = False  # la description affichée est une traduction (l'original reste sur le site source)


class OfferPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[OfferCard]


def _card(o: Offer, cls=OfferCard):
    data = {k: getattr(o, k) for k in cls.model_fields
            if k not in ("source_name", "eligibility", "original_title", "translated")}
    if cls is OfferDetail:
        data["eligibility"] = offer_eligibility(o)
    return cls(**data, source_name=SOURCES.get(o.source, {}).get("name", o.source))


@router.get("", response_model=OfferPage)
def search_offers(
    q: str | None = None,
    region: str | None = None,
    contract: str | None = None,
    sector: str | None = None,
    source: str | None = None,
    lang: str | None = Query(None, pattern="^(fr|ar|en)$"),
    function: str | None = None,
    sector_group: str | None = None,
    experience: str | None = None,
    since: int | None = Query(None, ge=1, le=365, description="publiées depuis N jours"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    stmt = select(Offer).where(Offer.status == "active", Offer.duplicate_of.is_(None))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(func.unaccent(Offer.title).ilike(func.unaccent(like)),
                              func.unaccent(Offer.description).ilike(func.unaccent(like)),
                              Offer.company.ilike(like)))
    if region:
        stmt = stmt.where(Offer.region == region)
    if contract:
        stmt = stmt.where(Offer.contract_type == contract)
    if sector:
        stmt = stmt.where(Offer.sector == sector)
    if source:
        stmt = stmt.where(Offer.source == source)
    if function:
        stmt = stmt.where(Offer.job_function == function)
    if sector_group:
        stmt = stmt.where(Offer.sector_group == sector_group)
    if experience:
        stmt = stmt.where(Offer.experience_level == experience)
    if since:
        stmt = stmt.where(Offer.posted_at >= date.today() - timedelta(days=since))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = session.scalars(
        stmt.order_by(Offer.posted_at.desc().nulls_last(), Offer.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    cards = [_card(o) for o in rows]
    if lang:
        titles = translate_titles(session, list(rows), lang)
        for c in cards:
            if c.id in titles:
                c.original_title, c.title = c.title, titles[c.id]
    return OfferPage(total=total, page=page, size=size, items=cards)


@router.get("/facets")
def facets(session: Session = Depends(get_session)):
    """Valeurs de filtres disponibles, avec effectifs (pour l'interface)."""
    base = select(Offer).where(Offer.status == "active", Offer.duplicate_of.is_(None)).subquery()

    def count_by(col):
        rows = session.execute(
            select(getattr(base.c, col), func.count()).group_by(getattr(base.c, col)).order_by(func.count().desc())
        ).all()
        return [{"value": v, "count": c} for v, c in rows if v]

    return {
        "regions": count_by("region"),
        "contracts": count_by("contract_type"),
        "sectors": count_by("sector"),
        "sources": [{**s, "name": SOURCES.get(s["value"], {}).get("name", s["value"])} for s in count_by("source")],
        "functions": count_by("job_function"),
        "sector_groups": count_by("sector_group"),
        "experiences": count_by("experience_level"),
        "all_regions": REGIONS,
    }


@router.get("/{offer_id}", response_model=OfferDetail)
def get_offer(offer_id: int, lang: str | None = Query(None, pattern="^(fr|ar|en)$"),
              session: Session = Depends(get_session)):
    o = session.get(Offer, offer_id)
    if o is None:
        raise HTTPException(404, "Offre introuvable")
    card = _card(o, OfferDetail)
    tr = translate_offer(session, o, lang) if lang else None
    if tr:
        if tr.title:
            card.original_title, card.title = card.title, tr.title
        if tr.description:
            card.description, card.translated = tr.description, True
        card.education = tr.education or card.education
        card.sector = tr.sector or card.sector
    return card
