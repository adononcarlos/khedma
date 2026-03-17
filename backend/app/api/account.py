from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import documents
from app.ai.cv_parser import extract_text, structure_cv
from app.ai.provider import get_provider
from app.api.offers import _card
from app.auth import create_token, current_user, hash_password, verify_password
from app.db import get_session
from app.matching.engine import match_offers, refresh_profile_embedding, score_offer
from app.matching.insights import profile_eligibility, skill_gaps
from app.matching.skills import label
from app.models import Application, GeneratedDocument, Offer, Profile, User
from app.sourcing.normalize import city_to_region

router = APIRouter(prefix="/api", tags=["compte"])
MAX_CV_BYTES = 5 * 1024 * 1024


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    city: str | None = None
    preferred_language: str = "fr"
    anapec_registered: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "city": u.city,
            "region": u.region, "phone": u.phone, "preferred_language": u.preferred_language,
            "anapec_registered": u.anapec_registered, "status": u.status}


@router.post("/auth/register")
def register(body: RegisterIn, session: Session = Depends(get_session)):
    if len(body.password) < 8:
        raise HTTPException(422, "Mot de passe : 8 caractères minimum")
    email = body.email.lower()
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Un compte existe déjà avec cet email")
    # Anti-doublon : même téléphone qu'un compte existant = doublon potentiel (profil fantôme)
    dup = body.phone and session.scalar(select(User).where(User.phone == body.phone))
    u = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name.strip(),
             phone=body.phone, city=body.city, region=city_to_region(body.city),
             preferred_language=body.preferred_language, anapec_registered=body.anapec_registered,
             ghost_reasons=["téléphone déjà utilisé"] if dup else None)
    session.add(u)
    session.commit()
    return {"token": create_token(u), "user": _user_out(u)}


@router.post("/auth/login")
def login(body: LoginIn, session: Session = Depends(get_session)):
    u = session.scalar(select(User).where(User.email == body.email.lower()))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    return {"token": create_token(u), "user": _user_out(u)}


LANG = Query(None, pattern="^(fr|ar|en)$")


@router.get("/me")
def me(lang: str | None = LANG, u: User = Depends(current_user), session: Session = Depends(get_session)):
    p = session.get(Profile, u.id)
    return {"user": _user_out(u), "profile": _profile_out(p, lang or u.preferred_language),
            "eligibility": profile_eligibility(u, p)}


def _profile_out(p: Profile | None, lang: str) -> dict | None:
    if p is None:
        return None
    return {"version": p.version, "headline": p.headline, "summary": p.summary,
            "skills": [{"id": s, "label": label(s, lang)} for s in (p.skills or [])],
            "extra_skills": p.extra_skills, "experiences": p.experiences, "education": p.education,
            "languages": p.languages, "education_level": p.education_level,
            "years_experience": p.years_experience, "cv_filename": p.cv_filename, "cv_language": p.cv_language}


@router.post("/me/cv")
async def upload_cv(file: UploadFile = File(...), u: User = Depends(current_user),
                    session: Session = Depends(get_session)):
    """Dépôt du CV de base -> profil structuré (1 seul traitement par CV, jamais par offre)."""
    data = await file.read()
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(413, "CV trop volumineux (5 Mo max)")
    if not file.filename.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(415, "Formats acceptés : PDF, DOCX, TXT")
    text = extract_text(file.filename, data)
    if len(text.strip()) < 80:
        raise HTTPException(422, "Impossible de lire le texte du CV (PDF scanné ?)")
    s = structure_cv(text)
    p = session.get(Profile, u.id) or Profile(user_id=u.id, version=0)
    p.version += 1  # invalide le cache des documents générés
    for k in ("headline", "summary", "skills", "extra_skills", "experiences", "education", "languages",
              "education_level", "years_experience", "cv_language"):
        setattr(p, k, s[k])
    p.cv_text, p.cv_filename = text[:20000], file.filename
    if s.get("phone") and not u.phone:
        u.phone = s["phone"]
    refresh_profile_embedding(p)
    session.add(p)
    session.commit()
    return {"profile": _profile_out(p, u.preferred_language), "provider": get_provider().name}


@router.get("/me/matches")
def my_matches(region: str | None = None, contract: str | None = None, limit: int = 20, lang: str | None = LANG,
               u: User = Depends(current_user), session: Session = Depends(get_session)):
    p = session.get(Profile, u.id)
    if p is None:
        raise HTTPException(409, "Déposez d'abord votre CV")
    matches = match_offers(session, u, p, limit=max(limit, 30), region=region, contract=contract)
    lang = lang or u.preferred_language
    return {
        "items": [{"offer": _card(m.offer).model_dump(), "score": m.score,
                   "matched": [label(s, lang) for s in m.matched_skills],
                   "missing": [label(s, lang) for s in m.missing_skills], "breakdown": m.breakdown}
                  for m in matches[:limit]],
        "skill_gaps": skill_gaps([m.missing_skills for m in matches], lang),
    }


def _match_for(session: Session, u: User, offer_id: int):
    p = session.get(Profile, u.id)
    o = session.get(Offer, offer_id)
    if p is None:
        raise HTTPException(409, "Déposez d'abord votre CV")
    if o is None:
        raise HTTPException(404, "Offre introuvable")
    d = session.scalar(select(Offer.embedding.cosine_distance(p.embedding)).where(Offer.id == o.id)) \
        if o.embedding is not None else 0.6
    return p, o, score_offer(o, p, u, d)


@router.get("/me/offers/{offer_id}/match")
def offer_match(offer_id: int, lang: str | None = LANG, u: User = Depends(current_user),
                session: Session = Depends(get_session)):
    _, _, m = _match_for(session, u, offer_id)
    lang = lang or u.preferred_language
    return {"score": m.score, "matched": [label(s, lang) for s in m.matched_skills],
            "missing": [label(s, lang) for s in m.missing_skills]}


@router.post("/me/offers/{offer_id}/documents")
def generate_documents(offer_id: int, u: User = Depends(current_user), session: Session = Depends(get_session)):
    """Génère CV + lettre pour CETTE offre, dans SA langue. Mis en cache par version de profil."""
    p, o, m = _match_for(session, u, offer_id)
    out, cached = {}, True
    for kind in ("cv", "letter"):
        doc = session.scalar(select(GeneratedDocument).where(
            GeneratedDocument.user_id == u.id, GeneratedDocument.offer_id == o.id,
            GeneratedDocument.kind == kind, GeneratedDocument.profile_version == p.version))
        if doc is None:
            cached = False
            content, usage = (documents.tailor_cv if kind == "cv" else documents.write_letter)(u, p, o, m)
            doc = GeneratedDocument(user_id=u.id, offer_id=o.id, kind=kind, language=o.language,
                                    profile_version=p.version, content=content, provider=get_provider().name,
                                    tokens_in=usage.tokens_in, tokens_out=usage.tokens_out)
            session.add(doc)
            session.flush()
        out[kind] = {"id": doc.id, "content": doc.content}
    if not session.scalar(select(Application).where(Application.user_id == u.id, Application.offer_id == o.id)):
        session.add(Application(user_id=u.id, offer_id=o.id, status="generated"))
    session.commit()
    return {**out, "language": o.language, "cached": cached, "offer_url": o.url,
            "letter_text": documents.letter_text(out["letter"]["content"])}


def _owned_doc(session: Session, u: User, doc_id: int) -> GeneratedDocument:
    doc = session.get(GeneratedDocument, doc_id)
    if doc is None or doc.user_id != u.id:
        raise HTTPException(404, "Document introuvable")
    return doc


@router.get("/me/documents/{doc_id}.html", response_class=HTMLResponse)
def document_html(doc_id: int, u: User = Depends(current_user), session: Session = Depends(get_session)):
    doc = _owned_doc(session, u, doc_id)
    return documents.cv_html(doc.content) if doc.kind == "cv" else documents.letter_html(doc.content)


@router.get("/me/documents/{doc_id}.pdf")
async def document_pdf(doc_id: int, u: User = Depends(current_user), session: Session = Depends(get_session)):
    doc = _owned_doc(session, u, doc_id)
    if doc.kind == "cv":
        pdf = await documents.cv_pdf_one_page(doc.content)
    else:
        pdf = await documents.html_to_pdf(documents.letter_html(doc.content))
    offer = session.get(Offer, doc.offer_id)
    name = documents.safe_filename("CV" if doc.kind == "cv" else "Lettre", u.full_name, offer.title if offer else "")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'})


@router.post("/me/offers/{offer_id}/applied")
def mark_applied(offer_id: int, u: User = Depends(current_user), session: Session = Depends(get_session)):
    app_ = session.scalar(select(Application).where(Application.user_id == u.id, Application.offer_id == offer_id))
    if app_ is None:
        app_ = Application(user_id=u.id, offer_id=offer_id)
        session.add(app_)
    app_.status = "applied"
    session.commit()
    return {"status": "applied"}
