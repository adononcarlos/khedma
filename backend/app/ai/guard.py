"""Protection contre l'injection de prompt (CV déposés et annonces scrapées).

Défense en couches :
1. normalize() : retire les caractères invisibles et de contrôle bidirectionnel, NFKC (lettres
   « déguisées » en formes Unicode équivalentes), pour que l'analyse voie le texte réel.
2. scan() : repère les formules d'injection (FR / EN / AR) et les marqueurs de rôle de chat.
   Le texte caché d'un PDF (blanc sur blanc, taille minuscule) est extrait comme le reste, donc analysé.
3. clean_field() : chaque champ transmis au LLM est nettoyé et tronqué ; le CV brut n'est jamais envoyé.
4. suspicious_output() : une réponse du LLM contenant un lien, un email ou des traces d'injection est rejetée.
"""
import re
import unicodedata

# Invisibles : espaces sans chasse, joints, marques de direction, isolats bidi, BOM, soft hyphen, tags Unicode
_INVISIBLE = re.compile("[­​-‏‪-‮⁠-⁤⁦-⁩﻿\U000e0000-\U000e007f]")

_PATTERNS = [
    # anglais
    r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(previous|prior|above|earlier|all|any|the|your|system)\b.{0,30}\b(instruction|instructions|prompt|prompts|rules|directions|guidelines)\b",
    r"\b(you are now|you're now|from now on,? you|pretend to be|act as|roleplay as)\b.{0,30}\b(dan|chatgpt|jailbroken|unrestricted|unfiltered|uncensored|(an? )?(ai|assistant|model|llm) (with no|without) (rules|restrictions|limits|filters))\b",
    r"\b(system|developer)\s*(prompt|message|instruction)s?\b\s*[:=]",
    r"\b(reveal|print|show|output|repeat)\b.{0,30}\b(system prompt|your instructions|hidden instructions|initial prompt)\b",
    r"\b(recruiter|hiring manager|ai|model|assistant)s?\b.{0,40}\b(must|should)\b.{0,40}\b(select|hire|rank|recommend|score)\b.{0,30}\b(me|this candidate)\b",
    r"\b(give|assign|rate)\b.{0,20}\b(this candidate|me)\b.{0,30}\b(highest|maximum|top|100|10/10)\b",
    # français
    r"\b(ignore[rz]?|oublie[rz]?|néglige[rz]?|contourne[rz]?)\b.{0,40}\b(instructions?|consignes?|règles?|directives?)\b.{0,20}(précédentes?|antérieures?|ci-dessus|du système|système|de l'ia|du modèle|données)",
    r"\b(tu es maintenant|vous êtes maintenant|à partir de maintenant,? tu|fais comme si tu étais|agis comme)\b.{0,30}(dan\b|chatgpt|sans (règles|restrictions?|limites|filtres?)|débridée?)",
    r"\b(révèle|affiche|répète|donne)[rz]?\b.{0,30}\b(prompt système|tes instructions|instructions cachées|consignes système)\b",
    r"\b(le recruteur|l'ia|le modèle|l'assistant)\b.{0,40}\b(doit|devra)\b.{0,40}\b(sélectionner|choisir|recommander|retenir|classer)\b.{0,30}\b(ce candidat|moi|ma candidature)\b",
    # arabe
    r"(تجاهل|انس|تخط)\S*\s.{0,40}(التعليمات|الأوامر|التوجيهات|القواعد)",
    r"(أنت الآن|تصرف ك|تظاهر بأنك).{0,40}(مساعد|نموذج|ذكاء اصطناعي|شات)",
    r"(اكشف|اعرض|كرر).{0,30}(التعليمات|موجه النظام)",
]
# Marqueurs de rôle et délimiteurs de prompt (formats de chat des modèles)
_MARKERS = [
    r"<\|?(im_start|im_end|system|endoftext|assistant|user)\|?>", r"\[/?(INST|SYS)\]", r"<</?SYS>>",
    r"^\s*(###\s*)?(system|assistant|user)\s*:", r"\bBEGIN (SYSTEM )?PROMPT\b", r"\bEND OF (USER )?INPUT\b",
    r"^\s*(###\s*)?(new instructions?|nouvelles? instructions?)\s*:",
]
_RE = [re.compile(p, re.I | re.S) for p in _PATTERNS] + [re.compile(p, re.I | re.M) for p in _MARKERS]


def normalize(text: str) -> str:
    return _INVISIBLE.sub("", unicodedata.normalize("NFKC", text or ""))


def scan(text: str) -> list[str]:
    """Extraits suspects (vide = rien trouvé). Analyse ligne par ligne ET texte aplati (injections coupées en lignes)."""
    t = normalize(text)
    flat = re.sub(r"\s+", " ", t)
    hits = []
    for rx in _RE:
        m = rx.search(t) or rx.search(flat)
        if m:
            hits.append(m.group(0)[:120])
    invisible = len(_INVISIBLE.findall(unicodedata.normalize("NFKC", text or "")))
    if invisible > 20:  # beaucoup de caractères invisibles = tentative de dissimulation
        hits.append(f"{invisible} caractères invisibles")
    return hits


def clean_field(value, max_len: int = 300):
    """Nettoie un champ avant envoi au LLM : invisibles retirés, marqueurs neutralisés, longueur bornée."""
    if value is None:
        return None
    if isinstance(value, list):
        return [clean_field(v, max_len) for v in value]
    if isinstance(value, dict):
        return {k: clean_field(v, max_len) for k, v in value.items()}
    if not isinstance(value, str):
        return value
    v = normalize(value)
    for rx in _RE:
        v = rx.sub("[…]", v)
    return v[:max_len]


_URL_OR_EMAIL = re.compile(r"https?://|www\.|[\w.+-]+@[\w-]+\.[\w.]+", re.I)


def suspicious_output(text: str, allowed: str = "") -> bool:
    """Réponse du LLM à rejeter : traces d'injection, ou lien / email absent des données fournies."""
    if scan(text):
        return True
    return any(m.group(0).lower() not in allowed.lower() for m in _URL_OR_EMAIL.finditer(text or ""))
