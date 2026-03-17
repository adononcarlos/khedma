"""Fabrique de faux CV pour les tests : python e2e/cv_factory.py <dossier>

Six profils réalistes (FR / AR / EN ; TXT, DOCX, PDF) et quatre fichiers invalides.
Les PDF sont rendus par Chromium en mode invisible (page.pdf n'existe qu'en headless).
"""
import base64
import json
import sys
from pathlib import Path

PERSONAS = [
    {"slug": "dev_web_fr", "format": "txt", "lang": "fr", "city": "Casablanca", "expect_skills": ["javascript", "dev_web"], "text": """Salma Bennani
Développeuse web full stack
salma.bennani@example.com | 06 11 22 33 44 | Casablanca

Profil
Développeuse web avec 3 ans d'expérience sur des applications React et Node.js.

Expérience professionnelle
2023 - Aujourd'hui Développeuse full stack - Webhelp, Casablanca
- Développement d'interfaces React et TypeScript
- Conception d'API REST avec Node.js et PostgreSQL
2021 - 2023 Développeuse junior - Agence Pixel, Rabat
- Intégration HTML, CSS et JavaScript

Formation
2021 Licence professionnelle en développement web
Université Hassan II

Compétences
React, Node.js, JavaScript, SQL, Git, travail en équipe

Langues
Arabe : natif ; Français : courant ; Anglais : bon
"""},
    {"slug": "comptable_fr", "format": "docx", "lang": "fr", "city": "Rabat", "expect_skills": ["comptabilite"], "text": """Hamza Ouhaddou
Comptable
hamza.ouhaddou@example.com | 06 55 44 33 22 | Rabat

Profil
Comptable rigoureux, 5 ans d'expérience en cabinet et en entreprise.

Expérience professionnelle
2021 - Aujourd'hui Comptable - Fiduciaire Atlas, Rabat
- Tenue de la comptabilité générale et déclarations fiscales (TVA, IS)
- Préparation des bilans annuels
2019 - 2021 Aide-comptable - Marjane, Salé
- Saisie des factures sur Sage

Formation
2019 Licence en sciences de gestion, option comptabilité
Université Mohammed V

Compétences
Comptabilité, fiscalité, Excel, Sage, rigueur

Langues
Arabe : natif ; Français : courant
"""},
    {"slug": "data_en", "format": "pdf", "lang": "en", "city": "Tanger", "expect_skills": ["python", "data"], "text": """Ines Berrada
Data Analyst
ines.berrada@example.com | 06 77 88 99 00 | Tanger

Summary
Data analyst with 2 years of experience building dashboards and automating reports.

Work experience
2024 - Present Data Analyst - Renault Tanger Med, Tanger
- Built Power BI dashboards for production KPIs
- Automated weekly reports with Python and SQL
2023 - 2024 Data intern - Capgemini, Casablanca
- Data cleaning and analysis in Python

Education
2023 Engineering degree in computer science
ENSA Tanger

Skills
Python, SQL, Power BI, Excel, machine learning

Languages
Arabic: native; French: fluent; English: fluent
"""},
    {"slug": "chauffeur_ar", "format": "pdf", "lang": "ar", "city": "Fès", "expect_skills": ["chauffeur"], "text": """عمر الفاسي
سائق شاحنة
omar.elfassi@example.com | 06 12 12 12 12 | فاس

الملف الشخصي
سائق محترف بخبرة 8 سنوات في نقل البضائع بين المدن.

الخبرة المهنية
2018 - 2026 سائق شاحنة - شركة النقل السريع، فاس
- نقل البضائع بين فاس والدار البيضاء
- صيانة الشاحنة واحترام قواعد السلامة

التكوين
2017 شهادة السياقة المهنية
مركز التكوين المهني فاس

المهارات
السياقة، رخصة الشاحنات، التنظيم

اللغات
العربية : اللغة الأم ؛ الفرنسية : متوسط
"""},
    {"slug": "infirmiere_fr", "format": "pdf", "lang": "fr", "city": "Marrakech", "expect_skills": ["soins"], "text": """Khadija Tazi
Infirmière polyvalente
khadija.tazi@example.com | 06 98 76 54 32 | Marrakech

Profil
Infirmière diplômée d'État, 4 ans d'expérience en service de réanimation.

Expérience professionnelle
2022 - Aujourd'hui Infirmière - Clinique Al Koutoubia, Marrakech
- Soins infirmiers et surveillance des patients en réanimation
- Préparation et administration des traitements
2020 - 2022 Infirmière stagiaire - CHU Mohammed VI, Marrakech

Formation
2020 Diplôme d'infirmier polyvalent
ISPITS Marrakech

Compétences
Soins infirmiers, urgences, travail en équipe, communication

Langues
Arabe : natif ; Français : courant
"""},
    {"slug": "securite_sans_diplome_fr", "format": "txt", "lang": "fr", "city": "Agadir", "expect_skills": ["securite"], "text": """Ayoub Ziani
Agent de sécurité
ayoub.ziani@example.com | 06 33 33 44 44 | Agadir

Expérience professionnelle
2022 - Aujourd'hui Agent de sécurité - G4S, Agadir
- Surveillance et gardiennage d'un centre commercial
- Contrôle des accès
2020 - 2022 Magasinier - Marjane, Agadir
- Rangement du stock et inventaire

Compétences
Surveillance, gardiennage, organisation, ponctualité

Langues
Arabe : natif ; Français : notions
"""},
]

# PNG 1x1 (pour le faux « PDF scanné » et le fichier image)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def _html(text: str, lang: str) -> str:
    body = "".join(f"<p>{line}</p>" if line.strip() else "<br>" for line in text.splitlines())
    return f"<html lang='{lang}' dir='{'rtl' if lang == 'ar' else 'ltr'}'><body style='font-family:sans-serif'>{body}</body></html>"


def build(out: Path) -> list[dict]:
    from docx import Document
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for per in PERSONAS:
            path = out / f"{per['slug']}.{per['format']}"
            if per["format"] == "txt":
                path.write_text(per["text"], encoding="utf-8")
            elif per["format"] == "docx":
                doc = Document()
                for line in per["text"].splitlines():
                    doc.add_paragraph(line)
                doc.save(path)
            else:
                page.set_content(_html(per["text"], per["lang"]))
                path.write_bytes(page.pdf(format="A4"))
            manifest.append({**{k: v for k, v in per.items() if k != "text"}, "path": str(path)})
        # PDF « scanné » : uniquement une image, aucun texte extractible
        page.set_content(f"<img src='data:image/png;base64,{base64.b64encode(PNG).decode()}' style='width:600px'>")
        (out / "scan_sans_texte.pdf").write_bytes(page.pdf(format="A4"))
        browser.close()
    (out / "vide.txt").write_text("", encoding="utf-8")
    (out / "photo.png").write_bytes(PNG)
    (out / "trop_lourd.txt").write_bytes(b"a" * (6 * 1024 * 1024))
    invalid = [{"slug": "vide", "path": str(out / "vide.txt"), "status": 422},
               {"slug": "scan_sans_texte", "path": str(out / "scan_sans_texte.pdf"), "status": 422},
               {"slug": "photo", "path": str(out / "photo.png"), "status": 415},
               {"slug": "trop_lourd", "path": str(out / "trop_lourd.txt"), "status": 413}]
    (out / "manifest.json").write_text(json.dumps({"valid": manifest, "invalid": invalid}, ensure_ascii=False, indent=1))
    return manifest


if __name__ == "__main__":
    build(Path(sys.argv[1]))
