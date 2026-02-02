"""CV et lettre ciblés, dans la langue d'ORIGINE de l'offre, au format compatible ATS.

ATS-friendly = une colonne, titres de sections standards, texte sélectionnable, pas de tableau,
pas d'image, pas de colonnes, dates homogènes, mots-clés de l'offre présents dans « Compétences ».
"""
import html
import re

from app.ai.provider import Usage, WritingBrief, get_provider
from app.matching.engine import Match
from app.matching.skills import SKILLS, label
from app.models import Offer, Profile, User

HEADINGS = {
    "fr": {"summary": "Profil", "skills": "Compétences", "experience": "Expérience professionnelle",
           "education": "Formation", "languages": "Langues", "present": "aujourd’hui"},
    "en": {"summary": "Summary", "skills": "Skills", "experience": "Professional experience",
           "education": "Education", "languages": "Languages", "present": "present"},
    "ar": {"summary": "الملف الشخصي", "skills": "المهارات", "experience": "الخبرة المهنية",
           "education": "التكوين", "languages": "اللغات", "present": "حتى الآن"},
}


def _key_points(description: str | None) -> list[str]:
    lines = [l.strip(" -•*\t") for l in (description or "").splitlines()]
    return [l for l in lines if 15 < len(l) < 160][:3]


def _relevance(exp: dict, offer_skills: set[str]) -> int:
    from app.matching.skills import extract_skills

    return len(set(extract_skills(" ".join([exp.get("title", ""), *exp.get("bullets", [])]))) & offer_skills)


def build_brief(u: User, p: Profile, o: Offer, m: Match) -> WritingBrief:
    lang = o.language
    exps = sorted(p.experiences or [], key=lambda e: -_relevance(e, set(o.skills or [])))
    return WritingBrief(
        lang=lang,
        candidate_first_name=(u.full_name or "").split(" ")[0] or None,
        candidate_headline=p.headline,
        years_experience=p.years_experience,
        matched_skills=[label(s, lang) for s in m.matched_skills] or [label(s, lang) for s in (p.skills or [])[:4] if s in SKILLS],
        top_experiences=[{"title": e.get("title"), "company": e.get("company"), "bullets": e.get("bullets", [])[:2]} for e in exps[:2]],
        education=(p.education or [{}])[0].get("degree"),
        offer_title=o.title, offer_company=o.company, offer_city=o.city,
        offer_key_points=_key_points(o.description),
    )


def tailor_cv(u: User, p: Profile, o: Offer, m: Match) -> tuple[dict, Usage]:
    lang = o.language
    brief = build_brief(u, p, o, m)
    summary, usage = get_provider().summary(brief)
    offer_skills = set(o.skills or [])
    ordered = sorted(p.skills or [], key=lambda s: (s not in offer_skills, s))
    exps = sorted(p.experiences or [], key=lambda e: (-_relevance(e, offer_skills), -(int(e.get("start") or 0))))
    education = p.education or []
    if p.cv_language and p.cv_language != lang:  # CV de base dans une autre langue : on traduit vers celle de l'offre
        exps, education, u2 = _translate_cv_parts(exps, education, lang)
        usage = Usage(usage.tokens_in + u2.tokens_in, usage.tokens_out + u2.tokens_out)
    return {
        "lang": lang,
        "name": u.full_name,
        "title": o.title,  # intitulé aligné sur l'offre : premier signal lu par un ATS
        "contact": " · ".join(filter(None, [u.email, u.phone, u.city])),
        "headings": HEADINGS[lang],
        "summary": summary,
        "skills": [label(s, lang) for s in ordered if s in SKILLS] + [s for s in (p.extra_skills or [])
                   if s.lower() not in {label(x, lang).lower() for x in ordered if x in SKILLS}][:8],
        "experiences": exps,
        "education": education,
        "languages": p.languages or [],
    }, usage


def _translate_cv_parts(exps: list[dict], education: list[dict], lang: str) -> tuple[list[dict], list[dict], Usage]:
    """Un seul appel groupé pour tous les intitulés et puces (sans LLM : contenu d'origine conservé)."""
    texts = [x for e in exps for x in [e.get("title") or "", *e.get("bullets", [])]] + [e.get("degree") or "" for e in education]
    out, usage = get_provider().translate_texts(texts, lang)
    if not out:
        return exps, education, usage
    it = iter(out)
    exps = [{**e, "title": next(it), "bullets": [next(it) for _ in e.get("bullets", [])]} for e in exps]
    education = [{**e, "degree": next(it)} for e in education]
    return exps, education, usage


def write_letter(u: User, p: Profile, o: Offer, m: Match) -> tuple[dict, Usage]:
    content, usage = get_provider().letter(build_brief(u, p, o, m))
    return {"lang": o.language, "name": u.full_name, "contact": " · ".join(filter(None, [u.email, u.phone, u.city])),
            "offer_title": o.title, "offer_company": o.company, **content}, usage


_CSS = """
@page { size: A4; margin: 16mm 16mm; }
body { font-family: 'Noto Sans', 'Noto Sans Arabic', Arial, sans-serif; font-size: var(--fs, 10.5pt); color: #111; line-height: 1.45; }
h1 { font-size: 20pt; margin: 0; } .title { font-size: 12pt; color: #333; margin: 2px 0 4px; }
.contact { font-size: 9.5pt; color: #444; margin-bottom: 10px; }
h2 { font-size: 11pt; text-transform: uppercase; letter-spacing: .04em; border-bottom: 1px solid #999; padding-bottom: 2px; margin: 14px 0 6px; }
.item { margin-bottom: 7px; } .item b { font-weight: 700; } .meta { color: #444; }
ul { margin: 3px 0 0; padding-inline-start: 18px; } li { margin: 1px 0; }
p { margin: 0 0 9px; }
"""


def _e(s) -> str:
    return html.escape(str(s or ""))


def cv_html(cv: dict, font_pt: float = 10.5, max_bullets: int = 6) -> str:
    """CV noir et blanc, une colonne. font_pt / max_bullets servent à tenir sur une page."""
    h = cv["headings"]
    cv = {**cv, "experiences": [{**e, "bullets": e.get("bullets", [])[: (max_bullets if i < 2 else max(1, max_bullets - 2))]}
                                for i, e in enumerate(cv["experiences"])]}
    exps = "".join(
        f'<div class="item"><b>{_e(e.get("title"))}</b>{", " + _e(e["company"]) if e.get("company") else ""}'
        f' <span class="meta">({_e(e.get("start"))}{" - " + _e(e.get("end") or h["present"]) if e.get("start") else ""})</span>'
        + ("<ul>" + "".join(f"<li>{_e(b)}</li>" for b in e.get("bullets", [])) + "</ul>" if e.get("bullets") else "")
        + "</div>" for e in cv["experiences"])
    edu = "".join(f'<div class="item"><b>{_e(e.get("degree"))}</b>{", " + _e(e["school"]) if e.get("school") else ""}'
                  f'{" (" + _e(e["year"]) + ")" if e.get("year") else ""}</div>' for e in cv["education"])
    langs = ", ".join(f'{_e(l["name"])}{" (" + _e(l["level"]) + ")" if l.get("level") else ""}' for l in cv["languages"])
    return f"""<!doctype html><html lang="{cv['lang']}" dir="{'rtl' if cv['lang'] == 'ar' else 'ltr'}"><head><meta charset="utf-8">
<title>CV, {_e(cv['name'])}</title><style>{_CSS} :root {{ --fs: {font_pt}pt; }}</style></head><body>
<h1>{_e(cv['name'])}</h1><div class="title">{_e(cv['title'])}</div><div class="contact">{_e(cv['contact'])}</div>
<h2>{h['summary']}</h2><p>{_e(cv['summary'])}</p>
<h2>{h['skills']}</h2><p>{_e(' · '.join(cv['skills']))}</p>
{f"<h2>{h['experience']}</h2>{exps}" if exps else ""}
{f"<h2>{h['education']}</h2>{edu}" if edu else ""}
{f"<h2>{h['languages']}</h2><p>{langs}</p>" if langs else ""}
</body></html>"""


def letter_html(letter: dict) -> str:
    paras = "".join(f"<p>{_e(p)}</p>" for p in letter["paragraphs"])
    obj = {"fr": "Objet : candidature au poste de", "en": "Re: application for the position of",
           "ar": "الموضوع: ترشح لمنصب"}[letter["lang"]]
    return f"""<!doctype html><html lang="{letter['lang']}" dir="{'rtl' if letter['lang'] == 'ar' else 'ltr'}"><head><meta charset="utf-8">
<title>Lettre, {_e(letter['name'])}</title><style>{_CSS} body {{ font-size: 11pt; }}</style></head><body>
<p><b>{_e(letter['name'])}</b><br>{_e(letter['contact'])}</p>
{f"<p>{_e(letter['offer_company'])}</p>" if letter.get('offer_company') else ""}
<p><b>{obj} {_e(letter['offer_title'])}</b></p>
<p>{_e(letter['salutation'])}</p>{paras}<p>{_e(letter['closing'])}</p><p>{_e(letter['name'])}</p>
</body></html>"""


def letter_text(letter: dict) -> str:
    return "\n\n".join([letter["salutation"], *letter["paragraphs"], letter["closing"], letter["name"] or ""])


async def cv_pdf_one_page(cv: dict) -> bytes:
    """Rend le CV et garantit UNE page : police réduite pas à pas, puis puces anciennes raccourcies."""
    import io

    from pypdf import PdfReader

    pdf = b""
    for font_pt, bullets in [(10.5, 6), (10, 5), (9.5, 4), (9, 3), (8.5, 3), (8.5, 2), (8, 1)]:
        pdf = await html_to_pdf(cv_html(cv, font_pt, bullets))
        if len(PdfReader(io.BytesIO(pdf)).pages) == 1:
            break
    return pdf


async def html_to_pdf(doc_html: str) -> bytes:
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(doc_html, wait_until="load")
        pdf = await page.pdf(format="A4", print_background=True)
        await browser.close()
        return pdf


def safe_filename(*parts: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", "_".join(p for p in parts if p))[:80] or "document"
