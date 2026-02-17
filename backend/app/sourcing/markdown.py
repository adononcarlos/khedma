"""Mise au format Markdown homogène des descriptions, quelle que soit la source.

Format cible (celui d'Indeed) : titres de sections en gras (« **Missions :** »), puces « - ».
"""
import re

from selectolax.parser import HTMLParser, Node

_BLOCK = {"p", "div", "section", "article", "br", "tr"}
_HEAD = {"h1", "h2", "h3", "h4", "h5", "h6"}


def html_to_markdown(html_or_node) -> str:
    node = HTMLParser(html_or_node).body if isinstance(html_or_node, str) else html_or_node
    if node is None:
        return ""
    for bad in node.css("script,style,noscript,iframe,form,button,img,svg"):
        bad.decompose()
    out: list[str] = []

    def walk(n: Node):
        for c in n.iter(include_text=True):
            tag = c.tag
            if tag == "-text":
                t = re.sub(r"\s+", " ", c.text_content or "")
                if t.strip():
                    out.append(t)
            elif tag in _HEAD:
                out.append(f"\n\n**{c.text(strip=True).rstrip(' :')} :**\n")
            elif tag in ("strong", "b"):
                t = c.text(strip=True)
                if t:
                    out.append(f" **{t}** ")
            elif tag == "li":
                out.append("\n- " + re.sub(r"\s+", " ", c.text(separator=" ")).strip())
            elif tag in ("ul", "ol"):
                walk(c)
                out.append("\n")
            elif tag in _BLOCK:
                out.append("\n")
                walk(c)
                out.append("\n")
            else:
                walk(c)

    walk(node)
    return tidy("".join(out))


def tidy(md: str) -> str:
    md = md.replace(" ", " ").replace("—", ",").replace("–", "-")
    md = re.sub(r"\*\*\s*\*\*", "", md)
    md = re.sub(r"[ \t]+", " ", md)
    md = re.sub(r" *\n *", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


SECTION_ALIASES = {
    "missions": "Missions", "caractéristiques du poste": "Missions", "poste": "Missions", "vos missions": "Missions",
    "tâches / activités": "Missions", "description du profil": "Profil recherché", "profil recherché": "Profil recherché",
    "compétences": "Compétences", "compétences spécifiques": "Compétences", "entreprise": "Entreprise",
    "commentaire": "Informations complémentaires", "traits de personnalité souhaités": "Qualités recherchées",
}


def structure_plain(text: str) -> str:
    """Texte brut à libellés (ANAPEC) -> Markdown : sections en gras, lignes « - » en puces."""
    lines = [l.strip() for l in (text or "").splitlines()]
    out: list[str] = []
    for l in lines:
        if not l:
            continue
        m = re.match(r"^([^:]{3,40})\s*:\s*(.*)$", l)
        key = m.group(1).strip().lower() if m else None
        if key in SECTION_ALIASES:
            out.append(f"\n**{SECTION_ALIASES[key]} :**")
            if m.group(2).strip():
                out.append(f"- {m.group(2).strip()}")
        elif re.match(r"^[-•*·]\s*", l):
            out.append("- " + re.sub(r"^[-•*·]\s*", "", l))
        else:
            out.append(l)
    md = "\n".join(out)
    if not md.lstrip().startswith("**"):
        md = "**Missions :**\n" + md
    return tidy(md)


def bulletize(md: str) -> str:
    """Dans chaque section « **Titre :** », les lignes courtes non listées deviennent des puces
    (les fiches ANAPEC énumèrent les missions ligne par ligne, sans tiret)."""
    out, in_section, buf = [], False, []
    # Liste écrite sur une seule ligne (« Missions : - Piloter… - Optimiser… ») -> une puce par élément
    lines = []
    for line in md.splitlines():
        parts = re.split(r"\s+-\s+(?=[A-ZÀ-Ýa-zà-ÿ])", line)
        if len(parts) >= 3:
            head = parts[0].strip().lstrip("- ").strip()
            if head:
                lines.append(head)
            lines += [f"- {x.strip()}" for x in parts[1:] if x.strip()]
        else:
            lines.append(line)
    md = "\n".join(lines)

    def flush():
        lines = [l for l in buf if l.strip()]
        if len(lines) >= 2 and all(len(l) < 220 for l in lines):
            out.extend(l if l.startswith("- ") else f"- {l}" for l in lines)
        else:  # section mixte : seules les suites de lignes courtes (>= 2, sans point final) deviennent des puces
            short = lambda l: len(l) < 90 and not l.rstrip().endswith(".")  # noqa: E731
            for i, l in enumerate(lines):
                run = (i > 0 and short(lines[i - 1])) or (i + 1 < len(lines) and short(lines[i + 1]))
                out.append(f"- {l}" if short(l) and run and not l.startswith("- ") and not l.endswith(":") else l)
        buf.clear()

    for line in md.splitlines():
        if re.match(r"^\*\*[^*]+\*\*\s*:?$", line.strip()):
            flush()
            out.append(("\n" if out else "") + line.strip())
            in_section = True
        elif in_section:
            buf.append(line.strip())
        else:
            out.append(line)
    flush()
    return tidy("\n".join(out))


_HEADINGS = ["Profil recherché", "Vos missions", "Missions principales", "Missions", "Compétences appréciées",
             "Compétences requises", "Compétences", "Environnement technique", "Ce que vous apprendrez", "Ce que nous offrons",
             "Nous offrons", "Avantages", "Description du poste", "Responsabilités", "Qualifications", "Requirements",
             "Responsibilities", "What we offer", "About the role", "Job description", "Informations complémentaires"]
# Mots techniques en « CamelCase » à ne jamais couper
_CAMEL = ["TypeScript", "JavaScript", "GitHub", "GitLab", "NestJS", "NodeJS", "PostgreSQL", "MySQL", "MongoDB", "DevOps",
          "WordPress", "PowerPoint", "PowerBI", "LinkedIn", "FastAPI", "OpenAI", "DataBricks", "BigQuery", "iOS", "macOS",
          "SolidWorks", "AutoCAD", "SharePoint", "OneDrive", "YouTube", "TikTok", "WhatsApp", "McDonald", "iPhone", "eCommerce"]


def reflow(text: str) -> str:
    """Répare une description publiée sans aucun saut de ligne (« …déploiement.Profil recherchéVous êtes… »)."""
    if not text or len(text) < 400 or text.count("\n") > len(text) / 400:
        return text
    # Les mots techniques sont remplacés par des marqueurs (caractères Unicode réservés) le temps du découpage
    masks = {}
    for i, w in enumerate(_CAMEL):
        if w in text:
            key = f"\ue000{chr(0xE100 + i)}\ue001"
            masks[key] = w
            text = text.replace(w, key)
    for h in _HEADINGS:  # titre de section collé au texte précédent et/ou suivant
        text = re.sub(rf"\s*{re.escape(h)}\s*:?\s*(?=[A-ZÀ-Ý\ue000])", f"\n\n**{h} :**\n", text)
    text = re.sub(r"([a-zà-ÿ0-9\).:;!?\ue001])(?=[A-ZÀ-Ý\ue000])", r"\1\n", text)  # mot collé au suivant
    text = re.sub(r"\b([A-Z]{2,})(?=[A-ZÀ-Ý][a-zà-ÿ])", r"\1\n", text)  # sigle collé : « RESTGit », « CSSAu »
    for key, w in masks.items():
        text = text.replace(key, w)
    return bulletize(text)
