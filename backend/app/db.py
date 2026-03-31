from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# Sans serveur : une connexion par requête (le pooler de Neon mutualise côté base)
engine = (create_engine(settings.database_url, poolclass=NullPool) if settings.serverless
          else create_engine(settings.database_url, pool_pre_ping=True))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import models  # noqa: F401  (enregistre les tables)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    Base.metadata.create_all(engine)


def get_session():
    with SessionLocal() as session:
        yield session
