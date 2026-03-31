"""Moteur de matching profil <-> offres, en deux étages (zéro token LLM).

1. Rappel : k plus proches voisins sur l'index HNSW pgvector (profil vs offres).
2. Classement : score hybride explicable (sémantique, compétences, région, contrat, fraîcheur, niveau).

À grande échelle, l'étage 1 reste en O(log n) et l'étage 2 ne touche que k offres.
"""
import math
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.cv_parser import education_level
from app.config import settings
from app.matching.embeddings import embed
from app.matching.skills import SKILLS, label
from app.models import Offer, Profile, User

SOFT = {"equipe", "communication", "organisation", "autonomie"}
LANGS = {"francais", "anglais", "arabe", "espagnol", "allemand"}
LEVELS = {"none": 0, "bac": 1, "bac+2": 2, "bac+3": 3, "bac+5": 4}
WEIGHTS = {"semantic": 0.45, "skills": 0.30, "region": 0.12, "contract": 0.05, "freshness": 0.08}


@dataclass
class Match:
    offer: Offer
    score: float
    breakdown: dict
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)


def profile_text(p: Profile, lang: str = "fr") -> str:
    exps = " ; ".join(f"{e.get('title', '')} {' '.join(e.get('bullets', [])[:3])}" for e in (p.experiences or []))
    skills = ", ".join(label(s, lang) for s in (p.skills or []) if s in SKILLS)
    edu = " ; ".join(e.get("degree", "") for e in (p.education or []))
    return "\n".join(filter(None, [p.headline, p.headline, skills, " ".join(p.extra_skills or []), exps, edu]))


def refresh_profile_embedding(p: Profile) -> None:
    p.embedding = embed([profile_text(p)], task="RETRIEVAL_QUERY")[0]


def _hard(skills: list[str] | None) -> set[str]:
    return {s for s in (skills or []) if s not in SOFT and s not in LANGS}


def score_offer(o: Offer, p: Profile, u: User, distance: float) -> Match:
    # Similarité cosinus ramenée sur [0, 1] selon la plage utile du modèle d'embeddings (réglable)
    sem = max(0.0, min(1.0, (1 - distance - settings.sim_low) / (settings.sim_high - settings.sim_low)))
    offer_hard, prof = _hard(o.skills), set(p.skills or [])
    matched = sorted(offer_hard & prof)
    missing = sorted(offer_hard - prof)
    # Couverture des compétences demandées, pondérée par le nombre de preuves (1 seule compétence = signal faible)
    skills = (len(matched) / len(offer_hard)) * min(1.0, len(matched) / 3) ** 0.5 if offer_hard else 0.3
    region = 1.0 if (u.region and o.region == u.region) else (0.5 if not o.region or not u.region else 0.0)
    contract = 1.0 if not p.desired_contracts or o.contract_type in p.desired_contracts else 0.3
    days = (date.today() - o.posted_at).days if o.posted_at else 60
    fresh = math.exp(-max(days, 0) / 30)
    parts = {"semantic": sem, "skills": skills, "region": region, "contract": contract, "freshness": fresh}
    total = sum(WEIGHTS[k] * v for k, v in parts.items())
    required = LEVELS.get(education_level(o.education or ""), 0) if o.education else 0
    if required > LEVELS.get(p.education_level or "none", 0) + 1:
        total -= 0.15
        parts["education_gap"] = True
    return Match(o, round(max(0.0, total) * 100), parts, matched, missing)


def match_offers(session: Session, u: User, p: Profile, limit: int = 20, k: int = 300,
                 region: str | None = None, contract: str | None = None) -> list[Match]:
    if p.embedding is None:
        return []
    dist = Offer.embedding.cosine_distance(p.embedding).label("d")
    stmt = (select(Offer, dist)
            .where(Offer.status == "active", Offer.duplicate_of.is_(None), Offer.embedding.is_not(None))
            .order_by(dist).limit(k))
    if region:
        stmt = stmt.where(Offer.region == region)
    if contract:
        stmt = stmt.where(Offer.contract_type == contract)
    matches = [score_offer(o, p, u, d) for o, d in session.execute(stmt).all()]
    matches.sort(key=lambda m: -m.score)
    return matches[:limit]
