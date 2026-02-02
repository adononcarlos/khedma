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

    def flush():
        lines = [l for l in buf if l.strip()]
        as_list = len(lines) >= 2 and all(len(l) < 220 for l in lines)
        out.extend((l if l.startswith("- ") or not as_list else f"- {l}") for l in lines)
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
