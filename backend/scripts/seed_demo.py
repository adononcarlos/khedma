"""Données de démonstration (comptes synthétiques, is_demo=True) : python -m scripts.seed_demo

Les OFFRES restent réelles ; seuls les comptes, profils, candidatures et placements sont simulés,
avec un historique étalé depuis novembre 2025. Relançable : supprime d'abord les données is_demo.
"""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.auth import hash_password
from app.db import SessionLocal, init_db
from app.matching.embeddings import embed
from app.matching.engine import profile_text
from app.matching.ghosts import detect
from app.models import Application, GeneratedDocument, Offer, Profile, User
from app.sourcing.normalize import REGIONS, city_to_region

random.seed(2026)
NOW = datetime.now(timezone.utc)
LAUNCH = datetime(2025, 11, 3, tzinfo=timezone.utc)
N_SEEKERS = 1200
PASSWORD = hash_password("demo12345")

FIRST_M = "Mohamed Youssef Amine Hamza Omar Mehdi Anas Ayoub Yassine Othmane Hicham Karim Rachid Soufiane Adil Ilyas Zakaria Badr Nabil Achraf Walid Reda Ismail Hassan Abdelilah Said Khalid Mustapha Taha Imad".split()
FIRST_F = "Fatima Khadija Salma Imane Meryem Sara Hajar Zineb Asmae Nada Houda Ghizlane Chaimae Oumaima Kawtar Soukaina Hind Loubna Amal Najat Latifa Siham Rim Yasmine Nisrine Ikram Btissam Wiam Malak Hiba".split()
LAST = "El Amrani;Benali;El Idrissi;Alaoui;Bennani;Tazi;Berrada;El Fassi;Chraibi;Lahlou;Kettani;Benjelloun;El Ouazzani;Bouzidi;Amrani;Ait Lahcen;Ouhaddou;Boukhari;El Mansouri;Naciri;Sebti;Filali;Rahmani;Zerouali;El Hajji;Belkadi;Moussaoui;Hamdaoui;Ait Ali;Essafi;Lamrani;Skalli;Guessous;Cherkaoui;Jabri;Ziani;Mernissi;Oukacha;Bakkali;Toumi".split(";")
# Villes pondérées (≈ population urbaine)
CITIES = [("Casablanca", 28), ("Rabat", 8), ("Salé", 6), ("Fès", 8), ("Tanger", 8), ("Marrakech", 8), ("Meknès", 5),
          ("Agadir", 5), ("Oujda", 4), ("Kénitra", 4), ("Tétouan", 4), ("Safi", 3), ("El Jadida", 3), ("Béni Mellal", 3),
          ("Nador", 2), ("Khouribga", 2), ("Settat", 2), ("Berrechid", 2), ("Laâyoune", 2), ("Errachidia", 1),
          ("Ouarzazate", 1), ("Guelmim", 1), ("Dakhla", 1), ("Taza", 1), ("Larache", 1), ("Mohammedia", 3)]
# Profils types par fonction : (poids, intitulés, compétences, niveaux d'études)
PERSONAS = {
    "production": (18, ["Technicien de maintenance", "Opérateur de production", "Électricien industriel", "Technicien qualité"],
                   ["maintenance", "electricite", "automatisme", "production", "qualite", "hse", "cablage_auto"], ["bac", "bac+2"]),
    "sales": (13, ["Commercial terrain", "Conseiller de vente", "Chargé de clientèle", "Délégué commercial"],
              ["vente", "relation_client", "communication", "crm", "merchandising", "caisse"], ["bac", "bac+2", "bac+3"]),
    "admin": (10, ["Assistante administrative", "Secrétaire de direction", "Agent administratif", "Gestionnaire de dossiers"],
              ["administration", "office", "excel", "word", "saisie", "organisation"], ["bac+2", "bac+3"]),
    "finance": (9, ["Comptable", "Aide-comptable", "Analyste financier junior", "Actuaire junior", "Contrôleur de gestion"],
                ["comptabilite", "fiscalite", "finance", "excel", "sap", "erp"], ["bac+2", "bac+3", "bac+5"]),
    "it": (9, ["Développeur web", "Ingénieur data", "Développeur Python", "Technicien support informatique", "Ingénieur IA junior"],
           ["python", "javascript", "sql", "dev_web", "data", "reseaux", "support_it", "java"], ["bac+2", "bac+3", "bac+5"]),
    "customer": (8, ["Téléconseiller", "Chargé de relation client", "Agent d'accueil"],
                 ["teleconseil", "relation_client", "francais", "communication", "anglais"], ["bac", "bac+2"]),
    "logistics": (7, ["Magasinier", "Chauffeur livreur", "Cariste", "Agent logistique"],
                  ["logistique", "chauffeur", "permis_b", "permis_c", "cariste"], ["none", "bac"]),
    "hospitality": (6, ["Cuisinier", "Serveur", "Réceptionniste", "Commis de cuisine"],
                    ["cuisine", "service_salle", "hotellerie", "tourisme", "anglais"], ["none", "bac", "bac+2"]),
    "education": (5, ["Enseignant", "Éducatrice de la petite enfance", "Formateur"],
                  ["enseignement", "petite_enfance", "communication", "francais"], ["bac+2", "bac+3", "bac+5"]),
    "construction": (4, ["Maçon", "Conducteur de travaux", "Dessinateur bâtiment"], ["btp", "cao", "plomberie", "menuiserie"], ["none", "bac", "bac+2"]),
    "health": (3, ["Infirmier", "Aide-soignante", "Préparateur en pharmacie"], ["soins", "pharmacie", "communication"], ["bac+2", "bac+3"]),
    "security": (3, ["Agent de sécurité", "Agent de surveillance"], ["securite", "organisation"], ["none", "bac"]),
    "marketing": (3, ["Community manager", "Chargé de marketing digital", "Graphiste"], ["digital_marketing", "design", "communication"], ["bac+2", "bac+3", "bac+5"]),
    "hr": (2, ["Chargé de recrutement", "Assistant RH"], ["rh", "office", "communication"], ["bac+3", "bac+5"]),
}
LEVEL_LABEL = {"none": "Sans diplôme", "bac": "Baccalauréat", "bac+2": "Technicien spécialisé / BTS",
               "bac+3": "Licence professionnelle", "bac+5": "Master / diplôme d'ingénieur"}


def weighted(items):
    return random.choices([i for i, _ in items], weights=[w for _, w in items])[0]


def signup_date() -> datetime:
    """Inscriptions en croissance depuis le lancement (densité ∝ temps)."""
    span = (NOW - LAUNCH).total_seconds()
    return LAUNCH + timedelta(seconds=span * random.random() ** 0.6)


def main():
    init_db()
    with SessionLocal() as s:
        demo_ids = [i for (i,) in s.execute(select(User.id).where(User.is_demo.is_(True)))]
        for model, col in ((Application, Application.user_id), (GeneratedDocument, GeneratedDocument.user_id), (Profile, Profile.user_id)):
            s.execute(delete(model).where(col.in_(demo_ids)))
        s.execute(delete(User).where(User.is_demo.is_(True)))
        s.commit()

        # Conseillers (un par région) et administrateur
        counselors = {}
        for i, region in enumerate(REGIONS):
            first = random.choice(FIRST_F if i % 2 else FIRST_M)
            c = User(email=f"conseiller{i + 1}@demo.khedma.ma", password_hash=PASSWORD, role="counselor",
                     full_name=f"{first} {random.choice(LAST)}", region=region, email_verified=True, is_demo=True,
                     created_at=LAUNCH - timedelta(days=20), last_active_at=NOW - timedelta(hours=random.randint(1, 30)))
            s.add(c)
            counselors[region] = c
        s.add(User(email="admin@demo.khedma.ma", password_hash=PASSWORD, role="admin", full_name="Administrateur Khedma",
                   email_verified=True, is_demo=True, created_at=LAUNCH - timedelta(days=30), last_active_at=NOW))
        s.flush()

        personas = list(PERSONAS.items())
        users, profiles = [], []
        for n in range(N_SEEKERS):
            fn, (w, titles, skills, levels) = random.choices(personas, weights=[p[1][0] for p in personas])[0]
            female = random.random() < 0.48
            name = f"{random.choice(FIRST_F if female else FIRST_M)} {random.choice(LAST)}"
            city = weighted(CITIES)
            created = signup_date()
            engagement = random.random()
            last = min(NOW, created + timedelta(days=(NOW - created).days * (engagement ** 0.35)))
            phone = f"06{random.randint(10000000, 99999999)}"
            u = User(email=f"{name.lower().replace(' ', '.')}.{n}@demo.khedma.ma", password_hash=PASSWORD, full_name=name,
                     phone=phone, city=city, region=city_to_region(city), role="seeker", is_demo=True,
                     preferred_language=random.choices(["fr", "ar", "en"], weights=[70, 24, 6])[0],
                     birth_year=random.randint(1980, 2006), anapec_registered=random.random() < 0.62,
                     email_verified=random.random() < 0.86, phone_verified=random.random() < 0.7,
                     created_at=created, last_active_at=last)
            u.counselor_id = counselors[u.region].id if u.region in counselors else None
            # ~18 % ont retrouvé un emploi (dont une partie via la plateforme)
            if engagement > 0.55 and random.random() < 0.3 and (NOW - created).days > 45:
                u.employed = True
                u.hired_at = created + timedelta(days=random.randint(30, max(31, (NOW - created).days)))
            users.append((u, fn, titles, skills, levels))
        # Comptes créés puis jamais utilisés (~7 %) : cas typique des registres d'inscrits gonflés
        for u, *_ in random.sample(users, int(0.07 * N_SEEKERS)):
            if (NOW - u.created_at).days > 20 and not u.employed:
                u.email_verified, u.last_active_at = False, u.created_at
        # Doublons volontaires (même téléphone ou même nom + ville), pour la détection des fantômes
        for u, *_ in random.sample(users, 40):
            twin = random.choice(users)[0]
            if random.random() < 0.5:
                u.phone = twin.phone
            else:
                u.full_name, u.city, u.region = twin.full_name, twin.city, twin.region
        s.add_all([u for u, *_ in users])
        s.flush()

        for u, fn, titles, skills, levels in users:
            if not u.email_verified and random.random() < 0.7:
                continue  # comptes jamais complétés
            level = random.choice(levels)
            years = round(max(0, random.gauss(4, 3.5)), 1) if level != "none" else round(random.uniform(0, 6), 1)
            chosen = random.sample(skills, k=min(len(skills), random.randint(2, 5)))
            chosen += random.sample(["francais", "arabe", "anglais", "equipe", "organisation", "office"], k=2)
            title = random.choice(titles)
            start = 2026 - int(years)
            p = Profile(user_id=u.id, version=1, headline=title, skills=sorted(set(chosen)), education_level=level,
                        years_experience=years, cv_language=random.choices(["fr", "ar", "en"], weights=[82, 12, 6])[0],
                        cv_filename=f"CV_{u.full_name.replace(' ', '_')}.pdf",
                        education=[{"degree": LEVEL_LABEL[level], "school": None, "year": str(start - 1)}],
                        experiences=[{"title": title, "company": None, "start": str(start), "end": None, "bullets": []}] if years >= 1 else [],
                        languages=[{"name": "Arabe", "level": "natif"}, {"name": "Français", "level": random.choice(["courant", "bon", "intermédiaire"])}],
                        updated_at=u.created_at + timedelta(days=random.randint(0, 20)))
            profiles.append((p, u, fn))
        for i in range(0, len(profiles), 128):
            batch = profiles[i:i + 128]
            for (p, _, _), v in zip(batch, embed([profile_text(p) for p, _, _ in batch])):
                p.embedding = v
        s.add_all([p for p, _, _ in profiles])
        s.flush()

        # Candidatures sur les vraies offres récentes, cohérentes avec le métier et la région
        offers_by_fn: dict[str, list[Offer]] = {}
        for o in s.scalars(select(Offer).where(Offer.duplicate_of.is_(None))):
            offers_by_fn.setdefault(o.job_function or "other", []).append(o)
        n_apps = 0
        for p, u, fn in profiles:
            if (NOW - u.last_active_at).days > 30 or random.random() < 0.35:
                continue
            pool = [o for o in offers_by_fn.get(fn, []) if o.region == u.region] or offers_by_fn.get(fn, [])
            for o in random.sample(pool, k=min(len(pool), random.randint(1, 4))):
                posted = datetime.combine(o.posted_at, datetime.min.time(), tzinfo=timezone.utc) if o.posted_at else NOW - timedelta(days=10)
                when = min(NOW, posted + timedelta(hours=random.randint(2, 24 * 10)))
                status = random.choices(["generated", "applied", "interview", "hired"], weights=[25, 55, 15, 5])[0]
                s.add(Application(user_id=u.id, offer_id=o.id, status=status, created_at=when))
                if status != "generated":
                    s.add(GeneratedDocument(user_id=u.id, offer_id=o.id, kind="cv", language=o.language, profile_version=1,
                                            content={"demo": True}, provider="demo", created_at=when))
                n_apps += 1
        s.commit()
        print("comptes :", len(users), "| profils :", len(profiles), "| candidatures :", n_apps)
        print("statuts :", detect(s))


if __name__ == "__main__":
    main()
