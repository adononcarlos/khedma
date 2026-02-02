"""Taxonomies communes à toutes les sources (déterministe, zéro token).

Calquées sur les filtres des sites marocains :
- FONCTION (métier du poste), sur le modèle des « Fonctions » de ReKrute : déduite du titre du poste.
- SECTEUR (activité de l'employeur), regroupant les 61 secteurs ANAPEC (nomenclature NAF) et ceux de ReKrute.
- Tranche d'EXPÉRIENCE, sur le modèle ReKrute (débutant, intermédiaire, confirmé, expert).
"""
import re

from app.sourcing.normalize import strip_accents

# Fonction -> mots-clés cherchés dans le TITRE (puis fonction de la source, puis début de description). Ordre = priorité.
FUNCTIONS: list[tuple[str, list[str]]] = [
    ("it", ["developpeur", "developer", "developpement", "logiciel", "software", "data", "intelligence artificielle",
            " ia ", " ai ", "machine learning", "devops", "cloud", "cyber", "reseau", "systeme", "informatique",
            "full stack", "fullstack", "frontend", "backend", " web ", "java", "python", " php ", "odoo", " sap ",
            " erp ", "integrateur", "telecom", " it ", " qa ", "testeur", "scrum", "product owner"]),
    ("finance", ["comptab", "finance", "financier", "audit", "controleur de gestion", "controle de gestion", "fiscal",
                 "tresor", "actuair", "actuari", "credit", "banque", "bancaire", "caissier", "recouvrement",
                 "assurance", " paie "]),
    ("sales", ["commercial", "vente", "vendeur", "vendeuse", "business developer", "account manager", "prospect",
               "chef de rayon", "delegue medical", "category manager"]),
    ("marketing", ["marketing", "communication", "community manager", "social media", "media", "publicite",
                   "graphiste", "designer", "infograph", "video", "contenu", " seo ", "brand"]),
    ("hr", ["ressources humaines", " rh ", "recrutement", "recruteur", "talent", "formateur", "gestionnaire rh"]),
    ("admin", ["assistant", "assistante", "secretaire", "administratif", "administrative", "office manager",
               "saisie", "archiv", "juridique", "juriste", "acheteur", "achats", "gestionnaire"]),
    ("customer", ["teleconseil", "teleoperat", "conseiller client", "charge clientele", "charge de clientele",
                  "service client", "relation client", "centre d appel", "call center", "hotline", "agent d accueil",
                  "hotesse", "receptionniste"]),
    ("engineering", ["ingenieur", "engineer", " r d ", "bureau d etudes", "chef de projet", "methodes", " cao ",
                     " dao ", "dessinateur", "conception"]),
    ("production", ["maintenance", "technicien", "operateur", "operatrice", "production", "qualite", " hse ",
                    "electricien", "electromecan", "automatisme", "mecanicien", "soudeur", "cablage", "monteur",
                    "regleur", "usinage", "chef d equipe"]),
    ("construction", ["btp", "chantier", "genie civil", "conducteur de travaux", "macon", "architecte", "topograph",
                      "plombier", "peintre", "menuisier", "carreleur", "coffreur", "ferrailleur", "batiment"]),
    ("logistics", ["logistique", "supply chain", "magasinier", "chauffeur", "conducteur", "livreur", "cariste",
                   "transport", "transit", "dispatcher", "approvisionnement", "entrepot", "inventaire"]),
    ("health", ["infirmier", "infirmiere", "medecin", "pharmac", "aide soignant", "sage femme", "kinesi",
                "laborantin", "soins", "dentiste", "radiolog", "sante"]),
    ("education", ["enseignant", "professeur", "educat", "prescolaire", "institut", "creche", "maternelle",
                   "animat", "tuteur", "moniteur"]),
    ("hospitality", ["cuisinier", "cuisine", "chef de partie", "commis", "serveur", "serveuse", "barman",
                     "patissier", "boulanger", "hebergement", "hotel", "gouvernante", "femme de chambre", "tourisme",
                     "guide", "restauration", "boucher", "charcutier"]),
    ("security", ["agent de securite", "securite", "surveillance", "gardien", "vigile", "gardiennage"]),
    ("services", ["nettoyage", "entretien des locaux", "estheticien", "coiffeu", "couturi", "menage",
                  "aide a domicile", "jardinier"]),
    ("agriculture", ["agricole", "agriculture", "agronome", "elevage", "veterinaire", "peche"]),
    ("public", ["concours", "fonctionnaire", "administrateur", "3eme grade", "ingenieur d etat"]),
]

# Secteur de l'employeur -> mots-clés cherchés dans le SECTEUR fourni par la source
SECTORS: list[tuple[str, list[str]]] = [
    ("tech", ["informatique", "telecom", "postes et telecommunications", "conseil en systemes", "offshoring",
              "internet", "multimedia", "recherche et developpement"]),
    ("finance", ["banque", "finance", "assurance", "intermediation financiere", "auxiliaires financiers", "credit",
                 "micro"]),
    ("agrifood", ["agriculture", "agro", "alimentaire", "peche", "aquaculture", "sylviculture", "chasse"]),
    ("industry", ["industrie", "automobile", "aeronautique", "chimie", "plastique", "caoutchouc", "papier", "metallurg",
                  "travail des metaux", "machines", "electrique", "electronique", "textile", "habillement", "cuir",
                  "bois", "meubles", "edition", "imprimerie", "fabrication", "tabac", "raffinage", "recuperation"]),
    ("construction", ["construction", "btp", "genie civil", "immobilier", "location sans operateur"]),
    ("commerce", ["commerce", "distribution", "retail", "negoce"]),
    ("transport", ["transport", "logistique"]),
    ("hospitality", ["hotellerie", "restauration", "tourisme", "voyage", "loisirs", "recreatives", "culturelles"]),
    ("health", ["sante", "action sociale", "pharma", "medical", "clinique", "hopital"]),
    ("education", ["education", "enseignement", "formation"]),
    ("energy", ["energie", "electricite", " gaz ", " eau ", "assainissement", "dechets", "extraction", "mines",
                "hydrocarbures", "petrole", "environnement"]),
    ("public", ["administration publique", "fonction publique", "extra territoriales", "collectivite"]),
    ("services", ["services fournis principalement aux entreprises", "agence pub", "marketing direct", "conseil",
                  "audit", "centre d appel", "services personnels", "services domestiques", "activites associatives",
                  "menages", "autres services", "securite", "nettoyage", "interim"]),
]


def _norm(*parts: str | None) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", strip_accents(" ".join(p for p in parts if p)).lower()) + " "


def _hit(keyword: str, text: str) -> bool:
    # « ia », « rh », « it » : mot entier (entouré d'espaces) ; sinon préfixe/sous-chaîne (« comptab », « livr »)
    k = keyword.strip()
    return f" {k} " in text if keyword != k else k in text


def _classify(rules: list[tuple[str, list[str]]], text: str) -> str | None:
    return next((key for key, kws in rules if any(_hit(k, text) for k in kws)), None)


def job_function(title: str | None, occupation: str | None = None, description: str | None = None) -> str:
    return (_classify(FUNCTIONS, _norm(title))
            or _classify(FUNCTIONS, _norm(occupation))
            or _classify(FUNCTIONS, _norm((description or "")[:300]))
            or "other")


def sector_group(sector: str | None, title: str | None = None) -> str:
    return _classify(SECTORS, _norm(sector)) or ("public" if "concours" in _norm(title) else "other")


EXPERIENCE_LEVELS = ["entry", "1-2", "3-5", "5-10", "10+"]


def experience_level(experience: str | None, description: str | None = None) -> str | None:
    """« (moins de 6 mois) », « Intermédiaire (3 à 5 ans) », « 2 ans d'expérience » -> tranche."""
    t = strip_accents(" ".join(p for p in (experience, (description or "")[:1500]) if p)).lower()
    if not t.strip():
        return None
    # Tranches explicites d'abord (« 3 à 5 ans », « 5 à 10 ans »), puis mots-clés, puis nombre d'années isolé
    rules = [
        (r"moins de 6 mois|6 mois - 1 an|debutant|sans experience|premiere experience|jeune diplome|junior|stagiaire|\bstage\b", "entry"),
        (r"3 a 5 ans|intermediaire|2 ans - 3 ans", "3-5"),
        (r"5 a 10 ans|confirme|senior", "5-10"),
        (r"plus de 10 ans|> ?10 ans|expert|10 ans et plus", "10+"),
        (r"1 an - 2 ans|1 a 2 ans|1 a 3 ans", "1-2"),
    ]
    for pattern, level in rules:
        if re.search(pattern, t):
            return level
    m = re.search(r"(\d{1,2})\s*(?:\+\s*)?ans? d.?experience|experience (?:de |d.au moins |minimum )?(\d{1,2})\s*ans?", t)
    if m:
        n = int(m.group(1) or m.group(2))
        return "entry" if n < 1 else "1-2" if n <= 2 else "3-5" if n <= 5 else "5-10" if n <= 10 else "10+"
    if re.search(r"au moins 1 an|1 an d.experience", t):
        return "1-2"
    return None
