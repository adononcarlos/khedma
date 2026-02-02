"""Espace conseiller (file de suivi priorisée) et Observatoire (pilotage du marché et de la plateforme)."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.offers import _card
from app.auth import require_role
from app.db import get_session
from app.matching.engine import match_offers
from app.matching.ghosts import detect
from app.matching.skills import label
from app.models import Application, GeneratedDocument, Offer, Profile, User

router = APIRouter(prefix="/api", tags=["conseiller et observatoire"])

# Références officielles (HCP, enquête emploi EMO 2026, T2 2026) : affichées telles quelles, non simulées
HCP = {"period": "T2 2026", "unemployment": 9.5, "urban": 11.9, "rural": 5.4, "youth_15_24": 27.2,
       "previous_period": "T1 2026", "previous_unemployment": 10.8,
       "source": "https://www.hcp.ma/Situation-du-marche-du-travail-au-Maroc-au-deuxieme-trimestre-de-2026-a-partir-de-la-nouvelle-enquete-sur-la-main-d_a4342.html"}
STATUS_WEIGHT = {"dormant": 40, "to_remind": 30, "active": 0, "ghost": -50, "duplicate": -60}


def _priority(u: User, apps: int, now: datetime) -> int:
    idle = (now - u.last_active_at).days
    return STATUS_WEIGHT.get(u.status, 0) + min(idle, 60) // 2 + (15 if apps == 0 else 0) - (100 if u.employed else 0)


@router.get("/counselor/caseload")
def caseload(me: User = Depends(require_role("counselor", "admin")), session: Session = Depends(get_session)):
    now = datetime.now(timezone.utc)
    q = select(User).where(User.role == "seeker", User.employed.is_(False))
    if me.role == "counselor":
        q = q.where(User.counselor_id == me.id)
    seekers = session.scalars(q).all()
    ids = [u.id for u in seekers]
    apps = dict(session.execute(select(Application.user_id, func.count()).where(Application.user_id.in_(ids))
                                .group_by(Application.user_id)).all())
    profiles = {p.user_id: p for p in session.scalars(select(Profile).where(Profile.user_id.in_(ids)))}
    rows = sorted(seekers, key=lambda u: -_priority(u, apps.get(u.id, 0), now))
    return {
        "counselor": {"name": me.full_name, "region": me.region},
        "totals": dict(Counter(u.status for u in seekers)),
        "items": [{
            "id": u.id, "name": u.full_name, "city": u.city, "status": u.status, "reasons": u.ghost_reasons,
            "headline": profiles[u.id].headline if u.id in profiles else None,
            "has_cv": u.id in profiles, "applications": apps.get(u.id, 0),
            "idle_days": (now - u.last_active_at).days, "priority": _priority(u, apps.get(u.id, 0), now),
            "anapec_registered": u.anapec_registered,
        } for u in rows[:60]],
    }


@router.get("/counselor/seekers/{user_id}/suggestions")
def suggestions(user_id: int, me: User = Depends(require_role("counselor", "admin")), session: Session = Depends(get_session)):
    u = session.get(User, user_id)
    if u is None or u.role != "seeker" or (me.role == "counselor" and u.counselor_id != me.id):
        raise HTTPException(404, "Candidat introuvable dans votre portefeuille")
    p = session.get(Profile, user_id)
    if p is None:
        return {"items": [], "reason": "no_cv"}
    return {"items": [{"offer": _card(m.offer).model_dump(), "score": m.score,
                       "matched": [label(s) for s in m.matched_skills], "missing": [label(s) for s in m.missing_skills]}
                      for m in match_offers(session, u, p, limit=5)]}


@router.post("/admin/ghosts/recompute")
def recompute(_: User = Depends(require_role("admin")), session: Session = Depends(get_session)):
    return detect(session)


def _months(start: date, end: date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


@router.get("/admin/observatory")
def observatory(_: User = Depends(require_role("admin", "counselor")), session: Session = Depends(get_session)):
    offers = select(Offer).where(Offer.status == "active", Offer.duplicate_of.is_(None)).subquery()

    def by(col):
        return [{"value": v, "count": c} for v, c in session.execute(
            select(getattr(offers.c, col), func.count()).group_by(getattr(offers.c, col)).order_by(func.count().desc())).all() if v]

    skill_counts = Counter(s for (sk,) in session.execute(select(offers.c.skills)) for s in (sk or [])
                           if s not in {"francais", "arabe", "anglais", "equipe", "communication", "organisation", "autonomie"})
    since = date.today() - timedelta(days=30)
    daily = dict(session.execute(select(offers.c.posted_at, func.count()).where(offers.c.posted_at >= since)
                                 .group_by(offers.c.posted_at)).all())

    seekers = session.scalars(select(User).where(User.role == "seeker")).all()
    status = Counter(u.status for u in seekers)
    ghosts_reasons = Counter(r for u in seekers if u.status in ("ghost", "duplicate") for r in (u.ghost_reasons or []))
    months = _months(date(2025, 11, 1), date.today())
    signups = Counter(u.created_at.strftime("%Y-%m") for u in seekers)
    hires = Counter(u.hired_at.strftime("%Y-%m") for u in seekers if u.hired_at)
    cum, acc = [], 0
    for m in months:
        acc += signups.get(m, 0)
        cum.append(acc)

    # Tension par métier : offres actives / candidats actifs (le profil donne le métier)
    fn_by_user = {}
    from app.sourcing.taxonomy import job_function
    for p in session.scalars(select(Profile)):
        fn_by_user[p.user_id] = job_function(p.headline)
    active_ids = {u.id for u in seekers if u.status == "active" and not u.employed}
    seekers_by_fn = Counter(fn for uid, fn in fn_by_user.items() if uid in active_ids)
    offers_by_fn = {r["value"]: r["count"] for r in by("job_function")}
    tension = sorted(({"function": f, "offers": offers_by_fn.get(f, 0), "seekers": seekers_by_fn.get(f, 0),
                       "ratio": round(offers_by_fn.get(f, 0) / max(1, seekers_by_fn.get(f, 0)), 2)}
                      for f in set(offers_by_fn) | set(seekers_by_fn) if f != "other"), key=lambda r: -r["ratio"])

    docs = session.execute(select(func.count(), func.coalesce(func.sum(GeneratedDocument.tokens_in + GeneratedDocument.tokens_out), 0))).one()
    apps = Counter(s for (s,) in session.execute(select(Application.status)))
    return {
        "hcp": HCP,
        "offers": {"total": sum(r["count"] for r in by("source")), "by_source": by("source"), "by_function": by("job_function"),
                   "by_region": by("region"), "by_sector": by("sector_group"), "by_contract": by("contract_type"),
                   "by_experience": by("experience_level"),
                   "top_skills": [{"skill": s, "label": label(s), "count": c} for s, c in skill_counts.most_common(12)],
                   "daily": [{"date": (since + timedelta(days=i)).isoformat(), "count": daily.get(since + timedelta(days=i), 0)}
                             for i in range(31)]},
        "users": {"registered": len(seekers), "status": dict(status),
                  "verified_active": sum(1 for u in seekers if u.status == "active" and u.email_verified),
                  "employed": sum(1 for u in seekers if u.employed), "ghost_reasons": dict(ghosts_reasons.most_common(6)),
                  "timeline": [{"month": m, "signups": signups.get(m, 0), "cumulative": c, "hires": hires.get(m, 0)}
                               for m, c in zip(months, cum)],
                  "by_region": [{"value": v, "count": c} for v, c in Counter(u.region for u in seekers if u.region).most_common()]},
        "tension": tension,
        "activity": {"applications": dict(apps), "documents": docs[0], "tokens": int(docs[1])},
        "demo_data": True,  # comptes, candidatures et placements simulés ; offres et chiffres HCP réels
    }
