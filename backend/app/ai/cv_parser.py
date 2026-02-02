"""Lecture du CV de base (PDF / DOCX / TXT) et structuration heuristique en profil.

Utilisé par le fournisseur « mock » ; un vrai LLM remplace `structure_cv` par un seul appel
(une fois par CV déposé, jamais par offre).
"""
import io
import re

from app.matching.skills import extract_skills
from app.sourcing.normalize import detect_language, strip_accents

SECTION_KEYS = {
    "experiences": ["experience", "experiences professionnelles", "parcours professionnel", "work experience",
                    "employment", "professional experience", "الخبرات", "الخبرة المهنية", "التجربة المهنية"],
    "education": ["formation", "formations", "education", "diplomes", "etudes", "cursus", "academic",
                  "التكوين", "الشهادات", "المسار الدراسي", "التعليم"],
    "skills": ["competences", "skills", "savoir faire", "competences techniques", "المهارات", "الكفاءات"],
    "languages": ["langues", "languages", "اللغات"],
    "summary": ["profil", "resume", "summary", "about me", "objectif", "a propos", "نبذة", "الملف الشخصي"],
    "other": ["centres d interet", "loisirs", "interests", "hobbies", "references", "certifications", "الهوايات"],
}
LEVEL_WORDS = r"(natif|native|maternelle|courant|fluent|bilingue|bon|good|intermediaire|intermediate|moyen|notions|basic|debutant|b1|b2|c1|c2|a1|a2)"
YEAR = r"(19[89]\d|20[0-3]\d)"


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    if name.endswith(".docx"):
        from docx import Document

        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    return data.decode("utf-8", errors="replace")


def _heading(line: str) -> str | None:
    k = re.sub(r"[^a-z؀-ۿ ]+", " ", strip_accents(line).lower()).strip()
    if not k or len(k) > 40:
        return None
    for section, keys in SECTION_KEYS.items():
        if any(k == key or k.startswith(key + " ") for key in keys):
            return section
    return None


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in lines:
        h = _heading(line)
        if h:
            current = h
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return sections


def _blocks(lines: list[str]) -> list[list[str]]:
    """Découpe une section en blocs : une nouvelle entrée commence par une ligne contenant une année."""
    blocks: list[list[str]] = []
    for line in lines:
        if re.search(YEAR, line) and not line.lstrip().startswith(("-", "•", "*")) or not blocks:
            blocks.append([line])
        else:
            blocks[-1].append(line)
    return blocks


def _years_experience(text: str) -> float:
    spans = re.findall(YEAR + r"\s*[-–à/to]+\s*(" + YEAR[1:-1] + r"|aujourd.?hui|present|présent|actuel|ce jour|now)", text, re.I)
    total = 0
    for start, end in spans:
        e = 2026 if not end.isdigit() else int(end)
        total += max(0, e - int(start))
    return float(min(total, 40))


def education_level(text: str) -> str:
    t = strip_accents(text).lower()
    if re.search(r"master|bac\s*\+\s*5|ingenieur|doctorat|phd|mba", t):
        return "bac+5"
    if re.search(r"licence|bachelor|bac\s*\+\s*3", t):
        return "bac+3"
    if re.search(r"bts|dut|dts|technicien specialise|bac\s*\+\s*2|deug", t):
        return "bac+2"
    if re.search(r"baccalaureat|\bbac\b|technicien|qualification", t):
        return "bac"
    return "none"


def structure_cv(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    sec = _split_sections(lines)
    header = sec.get("header", [])
    full = "\n".join(lines)

    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", full)
    phone = re.search(r"(\+212|0)\s?[5-7](?:[\s.-]?\d{2}){4}", full)
    name = next((l for l in header if not re.search(r"@|\d{3}", l) and 2 <= len(l.split()) <= 4), None)
    headline = next((l for l in header[1:4] if l != name and not re.search(r"@|\+?\d{6,}", l)), None)

    experiences = []
    for b in _blocks(sec.get("experiences", [])):
        head = b[0]
        dates = re.findall(YEAR, head)
        # Retire la période (« 2020 - 2022 », « 2022 - Aujourd'hui »), qu'elle soit en début ou en fin de ligne
        period = YEAR + r"\s*(?:[-–à/]|to)\s*(?:" + YEAR[1:-1] + r"|aujourd.?hui|pr[ée]sent|actuel|ce jour|now)?|" + YEAR
        rest = re.sub(period, "", head, flags=re.I).strip(" -–|:,")
        parts = [p.strip() for p in re.split(r"\s[-–|@]\s|\s+chez\s|\s+at\s", rest) if p.strip()]
        title = parts[0] if parts else head[:80]
        company = parts[1].split(",")[0].strip() if len(parts) > 1 else None
        experiences.append({
            "title": title or head[:80], "company": company,
            "start": dates[0] if dates else None, "end": dates[1] if len(dates) > 1 else None,
            "bullets": [l.lstrip("-•* ").strip() for l in b[1:] if len(l) > 3][:6],
        })

    education = []
    for b in _blocks(sec.get("education", [])):
        years = re.findall(YEAR, " ".join(b))
        education.append({"degree": re.sub(YEAR + r"\s*[-–]?\s*", "", b[0]).strip(" -–|:"),
                          "school": b[1] if len(b) > 1 else None, "year": years[-1] if years else None})

    languages = []
    for l in sec.get("languages", []):
        for part in re.split(r"[,;/•]", l):
            m = re.match(r"\s*([A-Za-zÀ-ÿ؀-ۿ]+)\s*[:(-]?\s*" + LEVEL_WORDS + "?", strip_accents(part), re.I)
            if m and len(m.group(1)) > 2:
                languages.append({"name": part.split(":")[0].split("(")[0].strip(), "level": (m.group(2) or "").lower() or None})

    skill_lines = sec.get("skills", [])
    extra = [s.strip(" -•*") for l in skill_lines for s in re.split(r"[,;•|]", l) if 2 < len(s.strip(" -•*")) < 40]
    return {
        "full_name": name,
        "email": email.group(0) if email else None,
        "phone": phone.group(0) if phone else None,
        "headline": headline,
        "summary": " ".join(sec.get("summary", []))[:600] or None,
        "experiences": experiences[:8],
        "education": education[:5],
        "languages": languages[:6],
        "skills": extract_skills(full),
        "extra_skills": extra[:25],
        "education_level": education_level(full),
        "years_experience": _years_experience(full),
        "cv_language": detect_language(full),
    }
