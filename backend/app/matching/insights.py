"""Éligibilité aux dispositifs publics (loi 51.25) et compétences manquantes -> formations.

Règles déterministes, indicatives (le conseiller ANAPEC valide). Sources :
loi 51.25 adoptée le 7 juillet 2026 (contrat de formation-insertion : 12 mois max, non-diplômés
inclus, obligation d'embauche en CDI d'au moins 60 % des stagiaires) ; anapec.ma (TAHFIZ, TADAROJ).
"""
from app.matching.skills import label
from app.models import Offer, Profile, User

ANAPEC_TRAININGS = "https://anapec.ma/chercheurs/offres_formation"
OFPPT = "https://www.ofppt.ma"

# Compétence -> (organisme, lien). Liens vers les pages officielles d'offres de formation.
TRAINING_PROVIDERS = {
    "digital": ("ANAPEC × ADD : formations en ligne gratuites", ANAPEC_TRAININGS),
    "langues": ("ANAPEC : plateforme de langues (7 langues)", ANAPEC_TRAININGS),
    "soft": ("ANAPEC : ateliers soft skills", ANAPEC_TRAININGS),
    "metier": ("ANAPEC : formations qualifiantes (TAEHIL) / OFPPT", OFPPT),
}
DIGITAL = {"excel", "word", "powerpoint", "office", "saisie", "sap", "erp", "crm", "python", "java", "javascript",
           "php", "sql", "dev_web", "reseaux", "support_it", "data", "cao", "digital_marketing", "design"}
LANGS = {"francais", "anglais", "arabe", "espagnol", "allemand"}
SOFT = {"equipe", "communication", "organisation", "autonomie"}


def training_for(skill: str) -> tuple[str, str]:
    kind = "digital" if skill in DIGITAL else "langues" if skill in LANGS else "soft" if skill in SOFT else "metier"
    return TRAINING_PROVIDERS[kind]


def skill_gaps(missing_by_offer: list[list[str]], lang: str = "fr", top: int = 5) -> list[dict]:
    """Compétences qui manquent le plus souvent dans les offres correspondant au profil."""
    n = len(missing_by_offer) or 1
    counts: dict[str, int] = {}
    for missing in missing_by_offer:
        for s in set(missing):
            counts[s] = counts.get(s, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:top]
    out = []
    for s, c in ranked:
        provider, url = training_for(s)
        out.append({"skill": s, "label": label(s, lang), "share": round(100 * c / n), "provider": provider, "url": url})
    return out


def offer_eligibility(o: Offer) -> list[dict]:
    badges = []
    if o.contract_type == "IDMAJ":
        badges.append({"program": "IDMAJ", "tone": "brand",
                       "text": "Contrat de formation-insertion (loi 51.25) : 12 mois max, indemnité 1 600–6 000 DH, "
                               "ouvert aux diplômés et non-diplômés inscrits à l’ANAPEC."})
    if o.contract_type == "CDI":
        badges.append({"program": "TAHFIZ", "tone": "green",
                       "text": "Si l’employeur a moins de 2 ans : exonérations TAHFIZ possibles (jusqu’à 10 CDI, 24 mois)."})
    return badges


def profile_eligibility(u: User, p: Profile | None) -> list[dict]:
    out = []
    level = (p.education_level if p else None) or "none"
    if not u.anapec_registered:
        out.append({"program": "ANAPEC", "status": "action",
                    "text": "Inscrivez-vous à l’ANAPEC : c’est la condition pour bénéficier des contrats IDMAJ."})
    out.append({"program": "IDMAJ", "status": "eligible" if u.anapec_registered else "possible",
                "text": "Contrat de formation-insertion de 12 mois, y compris sans diplôme depuis la loi 51.25."})
    if level == "none":
        out.append({"program": "TADAROJ", "status": "eligible",
                    "text": "Formation par apprentissage (200+ métiers) avec bourse de 5 000 DH/an."})
    return out
