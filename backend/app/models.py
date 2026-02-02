from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

EMBEDDING_DIM = 384


class Offer(Base):
    """Offre d'emploi réelle, sourcée depuis un site tiers (lien vers l'original conservé)."""

    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("source", "source_ref", name="uq_offer_source_ref"),
        Index("ix_offers_fingerprint", "fingerprint"),
        Index("ix_offers_region_sector", "region", "sector"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    source_ref: Mapped[str] = mapped_column(String(128))
    url: Mapped[str] = mapped_column(Text)

    title: Mapped[str] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(64), index=True)
    sector: Mapped[str | None] = mapped_column(Text)
    contract_type: Mapped[str | None] = mapped_column(String(32), index=True)
    contract_raw: Mapped[str | None] = mapped_column(Text)
    education: Mapped[str | None] = mapped_column(Text)
    experience: Mapped[str | None] = mapped_column(Text)
    salary: Mapped[str | None] = mapped_column(Text)
    occupation: Mapped[str | None] = mapped_column(Text)  # intitulé métier du référentiel de la source
    skills: Mapped[list | None] = mapped_column(JSON)  # identifiants du référentiel app.matching.skills
    job_function: Mapped[str | None] = mapped_column(String(24), index=True)  # app.sourcing.taxonomy.FUNCTIONS
    sector_group: Mapped[str | None] = mapped_column(String(24), index=True)  # app.sourcing.taxonomy.SECTORS
    experience_level: Mapped[str | None] = mapped_column(String(8), index=True)
    languages: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    positions: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(2), default="fr")  # langue d'origine de l'offre
    posted_at: Mapped[date | None] = mapped_column(Date, index=True)
    start_date: Mapped[date | None] = mapped_column(Date)

    fingerprint: Mapped[str] = mapped_column(String(40))  # détection des doublons inter-sites
    duplicate_of: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | expired
    detail_fetched: Mapped[bool] = mapped_column(default=False)

    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """Compte. role : seeker | counselor | admin. is_demo : données de démonstration (synthétiques)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    role: Mapped[str] = mapped_column(String(16), default="seeker", index=True)
    preferred_language: Mapped[str] = mapped_column(String(2), default="fr")
    city: Mapped[str | None] = mapped_column(String(128))
    region: Mapped[str | None] = mapped_column(String(64), index=True)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    anapec_registered: Mapped[bool] = mapped_column(default=False)
    email_verified: Mapped[bool] = mapped_column(default=False)
    phone_verified: Mapped[bool] = mapped_column(default=False)
    # Cycle de vie anti-« profils fantômes » : active | to_remind | dormant | ghost | duplicate
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    ghost_reasons: Mapped[list | None] = mapped_column(JSON)
    counselor_id: Mapped[int | None] = mapped_column(Integer, index=True)
    employed: Mapped[bool] = mapped_column(default=False)
    hired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Profile(Base):
    """Profil structuré extrait du CV de base (une ligne par utilisateur, versionnée)."""

    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)  # clé de cache des documents générés
    headline: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list | None] = mapped_column(JSON)  # identifiants du référentiel
    extra_skills: Mapped[list | None] = mapped_column(JSON)  # compétences libres hors référentiel
    experiences: Mapped[list | None] = mapped_column(JSON)  # [{title, company, city, start, end, bullets[]}]
    education: Mapped[list | None] = mapped_column(JSON)  # [{degree, school, year}]
    languages: Mapped[list | None] = mapped_column(JSON)  # [{name, level}]
    education_level: Mapped[str | None] = mapped_column(String(32))  # none | bac | bac+2 | bac+3 | bac+5
    years_experience: Mapped[float | None] = mapped_column()
    desired_contracts: Mapped[list | None] = mapped_column(JSON)
    cv_text: Mapped[str | None] = mapped_column(Text)
    cv_language: Mapped[str | None] = mapped_column(String(2))
    cv_filename: Mapped[str | None] = mapped_column(String(255))
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GeneratedDocument(Base):
    """CV / lettre générés pour une offre. Cache : (utilisateur, offre, type, version du profil)."""

    __tablename__ = "generated_documents"
    __table_args__ = (UniqueConstraint("user_id", "offer_id", "kind", "profile_version", name="uq_generated_doc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    offer_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(16))  # cv | letter
    language: Mapped[str] = mapped_column(String(2))
    profile_version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSON)
    provider: Mapped[str] = mapped_column(String(32))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Application(Base):
    """Suivi des candidatures (« j'ai postulé ») — sert aussi au taux de placement de l'Observatoire."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "offer_id", name="uq_application"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    offer_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16), default="applied")  # generated | applied | interview | hired
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OfferTranslation(Base):
    """Cache de traduction d'une offre dans une langue d'affichage (une seule traduction par offre et langue)."""

    __tablename__ = "offer_translations"
    __table_args__ = (UniqueConstraint("offer_id", "lang", name="uq_offer_translation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(Integer, index=True)
    lang: Mapped[str] = mapped_column(String(2))
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    education: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
