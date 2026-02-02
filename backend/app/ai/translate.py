"""Traduction des offres pour l'affichage, avec cache en base (zéro token si déjà traduit).

- Liste : seuls les TITRES manquants de la page sont traduits, en un seul appel groupé.
- Fiche : titre + description + formation + secteur, traduits une fois à la première ouverture.
Sans LLM (mode simulé), rien n'est traduit et l'interface affiche l'original.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import get_provider
from app.models import Offer, OfferTranslation


def _cached(session: Session, ids: list[int], lang: str) -> dict[int, OfferTranslation]:
    rows = session.scalars(select(OfferTranslation).where(OfferTranslation.offer_id.in_(ids), OfferTranslation.lang == lang))
    return {r.offer_id: r for r in rows}


def translate_titles(session: Session, offers: list[Offer], lang: str) -> dict[int, str]:
    todo = [o for o in offers if o.language != lang]
    if not todo:
        return {}
    cache = _cached(session, [o.id for o in todo], lang)
    missing = [o for o in todo if o.id not in cache or not cache[o.id].title]
    if missing:
        provider = get_provider()
        texts, usage = provider.translate_texts([o.title for o in missing], lang)
        if texts:
            for o, t in zip(missing, texts):
                row = cache.get(o.id) or OfferTranslation(offer_id=o.id, lang=lang, provider=provider.name)
                row.title = t
                row.tokens_in += usage.tokens_in // len(missing)
                row.tokens_out += usage.tokens_out // len(missing)
                session.add(row)
                cache[o.id] = row
            session.commit()
    return {oid: r.title for oid, r in cache.items() if r.title}


def translate_offer(session: Session, o: Offer, lang: str) -> OfferTranslation | None:
    if o.language == lang:
        return None
    row = _cached(session, [o.id], lang).get(o.id)
    if row and row.description is not None:
        return row
    provider = get_provider()
    fields = [o.title, o.description or "", o.education or "", o.sector or ""]
    texts, usage = provider.translate_texts(fields, lang)
    if not texts:
        return row  # éventuellement le titre seul, déjà traduit depuis la liste
    row = row or OfferTranslation(offer_id=o.id, lang=lang, provider=provider.name)
    row.title, row.description, row.education, row.sector = (t or None for t in texts)
    row.tokens_in += usage.tokens_in
    row.tokens_out += usage.tokens_out
    session.add(row)
    session.commit()
    return row
