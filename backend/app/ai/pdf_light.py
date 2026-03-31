"""Rendu PDF léger (fpdf2), sans navigateur : pour l'hébergement sans serveur.

Même mise en page que la version Chromium : noir et blanc, une colonne, titres de sections soulignés,
une seule page (police réduite pas à pas si besoin), arabe de droite à gauche (mise en forme HarfBuzz).
Polices : Noto Sans et Noto Sans Arabic (licence SIL OFL, voir fonts/OFL.txt).
"""
from pathlib import Path

from fpdf import FPDF

FONTS = Path(__file__).parent / "fonts"
OBJ = {"fr": "Objet : candidature au poste de", "en": "Re: application for the position of", "ar": "الموضوع: ترشح لمنصب"}


class _Doc(FPDF):
    def __init__(self, lang: str, size: float):
        super().__init__(format="A4")
        self.rtl = lang == "ar"
        self.size = size
        self.set_margins(16, 14, 16)
        self.set_auto_page_break(True, 14)
        for style, name in (("", "Regular"), ("B", "Bold")):
            self.add_font("Noto", style, str(FONTS / f"NotoSans-{name}.ttf"))
            self.add_font("NotoAr", style, str(FONTS / f"NotoSansArabic-{name}.ttf"))
        base, fallback = ("NotoAr", "Noto") if self.rtl else ("Noto", "NotoAr")
        self.base = base
        self.set_fallback_fonts([fallback])
        self.set_text_shaping(use_shaping_engine=True, direction="rtl" if self.rtl else "ltr")
        self.add_page()

    @property
    def align(self):
        return "R" if self.rtl else "L"

    def text_block(self, text: str, size: float | None = None, bold: bool = False, gap: float = 1.2, color=(17, 17, 17)):
        self.set_font(self.base, "B" if bold else "", size or self.size)
        self.set_text_color(*color)
        self.multi_cell(0, (size or self.size) * 0.5, text, align=self.align, markdown=False)
        self.ln(gap)

    def heading(self, text: str):
        self.ln(1.5)
        self.set_font(self.base, "B", self.size + 0.8)
        self.set_text_color(17, 17, 17)
        self.cell(0, (self.size + 0.8) * 0.5, text.upper() if not self.rtl else text, align=self.align,
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(150, 150, 150)
        self.line(self.l_margin, self.get_y() + 0.8, self.w - self.r_margin, self.get_y() + 0.8)
        self.ln(2.2)

    def bullet(self, text: str):
        self.set_font(self.base, "", self.size)
        self.set_text_color(17, 17, 17)
        indent = 4
        if self.rtl:
            self.set_right_margin(self.r_margin + indent)
            self.multi_cell(0, self.size * 0.5, f"{text} •", align="R")
            self.set_right_margin(self.r_margin - indent)
        else:
            self.set_left_margin(self.l_margin + indent)
            self.set_x(self.l_margin - 3)
            self.multi_cell(0, self.size * 0.5, f"•  {text}", align="L")
            self.set_left_margin(self.l_margin - indent)
        self.ln(0.4)


def _cv(cv: dict, size: float, max_bullets: int) -> _Doc:
    d = _Doc(cv["lang"], size)
    h = cv["headings"]
    sep = "، " if d.rtl else ", "
    d.text_block(cv["name"] or "", size + 9, bold=True, gap=0.6)
    d.text_block(cv["title"], size + 1.5, gap=0.4, color=(51, 51, 51))
    d.text_block(cv["contact"], size - 0.8, gap=2, color=(68, 68, 68))
    d.heading(h["summary"])
    d.text_block(cv["summary"] or "")
    d.heading(h["skills"])
    d.text_block(" · ".join(cv["skills"]))
    if cv["experiences"]:
        d.heading(h["experience"])
        for i, e in enumerate(cv["experiences"]):
            period = f" ({e['start']} - {e.get('end') or h['present']})" if e.get("start") else ""
            head = f"{e.get('title') or ''}{sep + e['company'] if e.get('company') else ''}{period}"
            d.text_block(head, bold=True, gap=0.4)
            for b in e.get("bullets", [])[: (max_bullets if i < 2 else max(1, max_bullets - 2))]:
                d.bullet(b)
            d.ln(1.2)
    if cv["education"]:
        d.heading(h["education"])
        for e in cv["education"]:
            line = f"{e.get('degree') or ''}{sep + e['school'] if e.get('school') else ''}{' (' + e['year'] + ')' if e.get('year') else ''}"
            d.text_block(line, gap=0.8)
    if cv["languages"]:
        d.heading(h["languages"])
        d.text_block(sep.join(f"{l['name']}{' (' + l['level'] + ')' if l.get('level') else ''}" for l in cv["languages"]))
    return d


def cv_pdf(cv: dict) -> bytes:
    """CV sur une page : police réduite pas à pas, puis puces des expériences anciennes raccourcies."""
    doc = None
    for size, bullets in [(10.5, 6), (10, 5), (9.5, 4), (9, 3), (8.5, 3), (8.5, 2), (8, 1)]:
        doc = _cv(cv, size, bullets)
        if doc.pages_count == 1:
            break
    return bytes(doc.output())


def letter_pdf(letter: dict) -> bytes:
    doc = None
    for size in (11, 10.5, 10, 9.5):
        doc = _Doc(letter["lang"], size)
        doc.text_block(letter["name"] or "", bold=True, gap=0.3)
        doc.text_block(letter["contact"], size - 1, gap=4, color=(68, 68, 68))
        if letter.get("offer_company"):
            doc.text_block(letter["offer_company"], gap=3)
        doc.text_block(f"{OBJ[letter['lang']]} {letter['offer_title']}", bold=True, gap=4)
        doc.text_block(letter["salutation"], gap=3)
        for p in letter["paragraphs"]:
            doc.text_block(p, gap=3)
        doc.text_block(letter["closing"], gap=4)
        doc.text_block(letter["name"] or "")
        if doc.pages_count == 1:
            break
    return bytes(doc.output())
