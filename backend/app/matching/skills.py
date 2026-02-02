"""Référentiel de compétences FR/EN/AR et extraction par dictionnaire (déterministe, zéro token).

Chaque compétence a un identifiant canonique, un libellé par langue et des synonymes.
C'est ce qui alimente : le score de matching, « pourquoi cette offre », les compétences
manquantes et les recommandations de formation.
"""
import re
from functools import lru_cache

from app.sourcing.normalize import strip_accents

# id: (fr, en, ar, [synonymes supplémentaires])
SKILLS: dict[str, tuple[str, str, str, list[str]]] = {
    # Bureautique & numérique
    "excel": ("Excel", "Excel", "إكسل", ["microsoft excel", "tableur", "tableaux croises"]),
    "word": ("Word", "Word", "وورد", ["microsoft word", "traitement de texte"]),
    "powerpoint": ("PowerPoint", "PowerPoint", "باوربوينت", ["power point"]),
    "office": ("Pack Office", "MS Office", "حزمة أوفيس", ["pack office", "microsoft office", "bureautique", "outils bureautiques"]),
    "saisie": ("Saisie de données", "Data entry", "إدخال البيانات", ["saisie", "data entry"]),
    "sap": ("SAP", "SAP", "ساب", []),
    "erp": ("ERP", "ERP", "نظام تخطيط الموارد", ["sage", "odoo"]),
    "crm": ("CRM", "CRM", "إدارة علاقات العملاء", ["salesforce"]),
    # Informatique
    "python": ("Python", "Python", "بايثون", ["django", "flask", "fastapi"]),
    "java": ("Java", "Java", "جافا", ["spring", "spring boot"]),
    "javascript": ("JavaScript", "JavaScript", "جافاسكريبت", ["js", "typescript", "node", "nodejs", "react", "angular", "vue"]),
    "php": ("PHP", "PHP", "بي إتش بي", ["laravel", "symfony", "wordpress"]),
    "sql": ("SQL / bases de données", "SQL / databases", "قواعد البيانات", ["sql", "mysql", "postgresql", "oracle", "base de donnees"]),
    "dev_web": ("Développement web", "Web development", "تطوير الويب", ["developpeur web", "html", "css", "front end", "back end", "full stack"]),
    "reseaux": ("Réseaux informatiques", "Networking", "الشبكات", ["reseau", "cisco", "tcp ip", "administration systeme", "telecoms"]),
    "support_it": ("Support informatique", "IT support", "الدعم المعلوماتي", ["helpdesk", "support technique", "maintenance informatique"]),
    "data": ("Analyse de données", "Data analysis", "تحليل البيانات", ["data analyst", "power bi", "tableau", "data science", "machine learning", "statistiques"]),
    "cao": ("CAO / DAO", "CAD", "التصميم بمساعدة الحاسوب", ["autocad", "solidworks", "catia", "revit", "dao", "cao"]),
    "digital_marketing": ("Marketing digital", "Digital marketing", "التسويق الرقمي", ["community manager", "reseaux sociaux", "social media", "seo", "marketing digital"]),
    "design": ("Design graphique", "Graphic design", "التصميم الجرافيكي", ["photoshop", "illustrator", "canva", "infographie", "montage video", "video editing"]),
    # Langues
    "francais": ("Français", "French", "الفرنسية", ["francais", "french"]),
    "anglais": ("Anglais", "English", "الإنجليزية", ["anglais", "english"]),
    "arabe": ("Arabe", "Arabic", "العربية", ["arabe", "arabic"]),
    "espagnol": ("Espagnol", "Spanish", "الإسبانية", ["espagnol", "spanish"]),
    "allemand": ("Allemand", "German", "الألمانية", ["allemand", "german"]),
    # Commerce & relation client
    "vente": ("Vente", "Sales", "البيع", ["vendeur", "vendeuse", "commercial", "prospection", "negociation", "sales"]),
    "relation_client": ("Relation client", "Customer service", "خدمة العملاء", ["service client", "accueil", "customer service", "satisfaction client"]),
    "teleconseil": ("Centre d'appels", "Call center", "مركز النداء", ["teleconseiller", "teleoperateur", "call center", "centre d appel", "hotline"]),
    "caisse": ("Caisse", "Cashier", "الصندوق", ["caissier", "caissiere", "encaissement"]),
    "merchandising": ("Merchandising", "Merchandising", "عرض السلع", ["mise en rayon", "animateur de vente", "merchandiser"]),
    # Gestion, finance, RH
    "comptabilite": ("Comptabilité", "Accounting", "المحاسبة", ["comptable", "comptabilite", "accounting", "bilan", "tenue de comptes"]),
    "fiscalite": ("Fiscalité", "Taxation", "الضرائب", ["fiscal", "tva", "declarations fiscales"]),
    "finance": ("Finance", "Finance", "المالية", ["controle de gestion", "tresorerie", "audit", "analyse financiere"]),
    "rh": ("Ressources humaines", "Human resources", "الموارد البشرية", ["ressources humaines", "recrutement", "paie", "human resources", "hr"]),
    "administration": ("Gestion administrative", "Administration", "التدبير الإداري", ["assistant administratif", "secretariat", "secretaire", "gestion administrative", "classement"]),
    "logistique": ("Logistique", "Logistics", "اللوجستيك", ["supply chain", "gestion de stock", "magasinier", "entrepot", "inventaire", "approvisionnement"]),
    "achats": ("Achats", "Purchasing", "المشتريات", ["acheteur", "procurement"]),
    "gestion_projet": ("Gestion de projet", "Project management", "تدبير المشاريع", ["chef de projet", "project manager", "agile", "scrum"]),
    # Industrie & technique
    "maintenance": ("Maintenance industrielle", "Industrial maintenance", "الصيانة الصناعية", ["maintenance", "mecanique", "technicien de maintenance"]),
    "electricite": ("Électricité", "Electrical work", "الكهرباء", ["electricien", "electrique", "electrotechnique", "cablage"]),
    "automatisme": ("Automatisme", "Automation", "الأتمتة", ["automate", "plc", "automaticien", "automatise"]),
    "soudure": ("Soudure", "Welding", "التلحيم", ["soudeur", "soudage"]),
    "cablage_auto": ("Câblage automobile", "Automotive wiring", "كابلاج السيارات", ["cablage automobile", "faisceaux", "operateur cablage"]),
    "production": ("Production industrielle", "Manufacturing", "الإنتاج الصناعي", ["operateur de production", "chaine de production", "montage", "assemblage", "conditionnement"]),
    "qualite": ("Qualité", "Quality", "الجودة", ["controle qualite", "iso 9001", "haccp", "quality"]),
    "hse": ("Hygiène, sécurité, environnement", "Health & safety", "الصحة والسلامة", ["hse", "securite au travail", "qhse"]),
    "btp": ("Bâtiment / BTP", "Construction", "البناء والأشغال العمومية", ["batiment", "chantier", "genie civil", "macon", "construction", "conducteur de travaux"]),
    "froid": ("Froid et climatisation", "HVAC", "التبريد والتكييف", ["climatisation", "frigoriste", "hvac"]),
    "plomberie": ("Plomberie", "Plumbing", "السباكة", ["plombier", "sanitaire"]),
    "menuiserie": ("Menuiserie", "Carpentry", "النجارة", ["menuisier", "ebeniste", "bois"]),
    "carrosserie": ("Mécanique / carrosserie auto", "Auto repair", "ميكانيك السيارات", ["carrosserie", "mecanicien auto", "reparateur de vehicules"]),
    # Transport
    "permis_b": ("Permis B", "Driving licence B", "رخصة السياقة ب", ["permis b", "permis de conduire"]),
    "permis_c": ("Permis C / poids lourd", "Truck licence", "رخصة الشاحنات", ["permis c", "poids lourd", "conducteur routier", "chauffeur poids lourd"]),
    "chauffeur": ("Conduite / chauffeur", "Driving", "السياقة", ["chauffeur", "conducteur", "livreur", "livraison", "driver"]),
    "cariste": ("Conduite de chariot (cariste)", "Forklift", "سائق الرافعة", ["cariste", "chariot elevateur", "forklift"]),
    # Hôtellerie, restauration, services
    "cuisine": ("Cuisine", "Cooking", "الطبخ", ["cuisinier", "chef de partie", "commis de cuisine", "patissier", "boulanger"]),
    "service_salle": ("Service en salle", "Waiting staff", "خدمة المطاعم", ["serveur", "serveuse", "barman", "service en salle"]),
    "hotellerie": ("Hôtellerie", "Hospitality", "الفندقة", ["reception", "receptionniste", "hebergement", "housekeeping", "gouvernante", "femme de chambre"]),
    "tourisme": ("Tourisme", "Tourism", "السياحة", ["guide", "agent de voyage", "touristique"]),
    "boucherie": ("Boucherie / charcuterie", "Butchery", "الجزارة", ["boucher", "charcutier"]),
    "securite": ("Sécurité / gardiennage", "Security", "الحراسة", ["agent de securite", "surveillance", "gardiennage", "vigile"]),
    "nettoyage": ("Nettoyage / entretien", "Cleaning", "النظافة", ["agent de nettoyage", "entretien des locaux", "proprete"]),
    "esthetique": ("Esthétique / coiffure", "Beauty care", "التجميل والحلاقة", ["estheticienne", "coiffeur", "coiffeuse", "soins de beaute"]),
    "couture": ("Couture / textile", "Sewing", "الخياطة", ["couturiere", "piqueuse", "textile", "confection", "machine a coudre"]),
    # Santé, éducation, social
    "soins": ("Soins infirmiers", "Nursing", "التمريض", ["infirmier", "infirmiere", "aide soignant", "nursing", "soins"]),
    "pharmacie": ("Pharmacie", "Pharmacy", "الصيدلة", ["pharmacien", "preparateur en pharmacie"]),
    "enseignement": ("Enseignement", "Teaching", "التعليم", ["enseignant", "professeur", "formateur", "educateur", "educatrice", "teacher", "prescolaire"]),
    "petite_enfance": ("Petite enfance", "Childcare", "الطفولة المبكرة", ["creche", "garde d enfants", "maternelle", "animatrice"]),
    "agriculture": ("Agriculture", "Agriculture", "الفلاحة", ["agricole", "ouvrier agricole", "cueillette", "elevage", "irrigation"]),
    # Savoir-être
    "equipe": ("Travail en équipe", "Teamwork", "العمل الجماعي", ["esprit d equipe", "teamwork", "travail en equipe"]),
    "communication": ("Communication", "Communication", "التواصل", ["communication", "aisance relationnelle", "sens du relationnel"]),
    "organisation": ("Organisation / rigueur", "Organisation", "التنظيم", ["rigueur", "organise", "sens de l organisation", "ponctualite"]),
    "autonomie": ("Autonomie", "Autonomy", "الاستقلالية", ["autonome", "autonomie", "self starter"]),
}


def _norm(s: str) -> str:
    s = strip_accents(s).lower()
    return " " + re.sub(r"[^a-z0-9؀-ۿ+#]+", " ", s).strip() + " "


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[str, str]]:
    pats = []
    for sid, (fr, en, ar, syn) in SKILLS.items():
        for term in {fr, en, *syn}:
            pats.append((_norm(term), sid))
        pats.append((" " + ar + " ", sid))
    return sorted(pats, key=lambda p: -len(p[0]))


def extract_skills(text: str | None) -> list[str]:
    """Identifiants de compétences présentes dans le texte (ordre d'apparition dans le référentiel)."""
    if not text:
        return []
    t = _norm(text)
    found = {sid for pat, sid in _patterns() if pat in t}
    return [sid for sid in SKILLS if sid in found]


def label(sid: str, lang: str = "fr") -> str:
    fr, en, ar, _ = SKILLS[sid]
    return {"fr": fr, "en": en, "ar": ar}.get(lang, fr)
