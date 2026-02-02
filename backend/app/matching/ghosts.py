"""Détection des profils fantômes (règles explicites, auditables par un conseiller).

Statuts : active -> to_remind (30 j sans activité) -> dormant (90 j) ; ghost = compte jamais réellement
utilisé ; duplicate = même téléphone ou même nom + ville qu'un compte plus ancien.
Les statistiques de l'Observatoire ne comptent que les comptes « active » vérifiés.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Profile, User
from app.sourcing.normalize import strip_accents


def _key(u: User) -> str:
    return f"{strip_accents(u.full_name).lower().strip()}|{(u.city or '').lower()}"


def detect(session: Session, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    seekers = session.scalars(select(User).where(User.role == "seeker").order_by(User.created_at)).all()
    has_cv = {uid for (uid,) in session.execute(select(Profile.user_id))}
    by_phone, by_name = defaultdict(list), defaultdict(list)
    for u in seekers:
        if u.phone:
            by_phone[u.phone].append(u)
        by_name[_key(u)].append(u)

    counts: dict[str, int] = defaultdict(int)
    for u in seekers:
        reasons = []
        first_phone = by_phone[u.phone][0] if u.phone else u
        first_name = by_name[_key(u)][0]
        if first_phone.id != u.id:
            reasons.append("même téléphone qu'un autre compte")
        if first_name.id != u.id and len(by_name[_key(u)]) > 1:
            reasons.append("même nom et même ville qu'un autre compte")
        idle = (now - u.last_active_at).days
        age = (now - u.created_at).days
        if reasons:
            status = "duplicate"
        elif not u.email_verified and age > 14 and idle >= age - 1:
            status, reasons = "ghost", ["email jamais vérifié", "aucune activité depuis l'inscription"]
        elif u.id not in has_cv and idle > 60:
            status, reasons = "ghost", ["aucun CV déposé", f"inactif depuis {idle} jours"]
        elif u.employed:
            status = "active"
        elif idle > 90:
            status, reasons = "dormant", [f"inactif depuis {idle} jours"]
        elif idle > 30:
            status, reasons = "to_remind", [f"inactif depuis {idle} jours"]
        else:
            status = "active"
        u.status, u.ghost_reasons = status, reasons or None
        counts[status] += 1
    session.commit()
    return dict(counts)


def reminder_due(u: User, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return u.status in ("to_remind", "dormant") and (now - u.last_active_at) > timedelta(days=30)
