import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import User

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + base64.b64encode(salt + digest).decode()


def verify_password(password: str, stored: str) -> bool:
    raw = base64.b64decode(stored.removeprefix("scrypt$"))
    salt, digest = raw[:16], raw[16:]
    return hmac.compare_digest(digest, hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1))


def create_token(user: User) -> str:
    payload = {"sub": str(user.id), "role": user.role, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), session: Session = Depends(get_session)
) -> User:
    if creds is None:
        raise HTTPException(401, "Authentification requise")
    try:
        user_id = int(jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Jeton invalide")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Utilisateur introuvable")
    # Toute activité réelle remet le compte « actif » (sortie du cycle fantôme)
    user.last_active_at = datetime.now(timezone.utc)
    if user.status in ("to_remind", "dormant"):
        user.status = "active"
    session.commit()
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Accès réservé")
        return user

    return dep
