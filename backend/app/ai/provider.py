"""Fournisseurs LLM interchangeables.

Principe d'économie de tokens : le LLM n'écrit QUE ce qui demande de la rédaction
(accroche du CV, lettre, traduction des puces si la langue de l'offre diffère du CV).
Tout le reste (tri, sélection, mise en page ATS) est déterministe.

- MockProvider : gabarits FR/EN/AR, zéro appel externe (démo sans clé).
- GeminiVertexProvider : Gemini (Vertex AI, GCP), région UE.
"""
from dataclasses import dataclass

from app.config import settings


@dataclass
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class WritingBrief:
    """Entrée compacte envoyée au LLM : uniquement les faits utiles, pas le CV complet (tokens + vie privée)."""

    lang: str
    candidate_first_name: str | None
    candidate_headline: str | None
    years_experience: float | None
    matched_skills: list[str]  # libellés dans la langue de l'offre
    top_experiences: list[dict]  # 2 max : {title, company, bullets[:2]}
    education: str | None
    offer_title: str
    offer_company: str | None
    offer_city: str | None
    offer_key_points: list[str]  # 3 max, extraits de la description


class MockProvider:
    name = "mock"

    def translate_texts(self, texts: list[str], target: str) -> tuple[list[str] | None, Usage]:
        return None, Usage()  # pas de traduction sans LLM : l'interface affiche l'original

    def summary(self, b: WritingBrief) -> tuple[str, Usage]:
        skills = ", ".join(b.matched_skills[:4])
        yrs = int(b.years_experience or 0)
        if b.lang == "en":
            txt = (f"{b.candidate_headline or 'Motivated professional'}"
                   f"{f' with {yrs} years of experience' if yrs else ''}"
                   f"{f', skilled in {skills}' if skills else ''}. "
                   f"Looking to contribute as {b.offer_title}{f' at {b.offer_company}' if b.offer_company else ''}.")
        elif b.lang == "ar":
            txt = (f"{b.candidate_headline or 'مرشح متحفز'}"
                   f"{f' بخبرة {yrs} سنوات' if yrs else ''}"
                   f"{f'، أتقن {skills}' if skills else ''}. "
                   f"أطمح إلى المساهمة في منصب {b.offer_title}.")
        else:
            txt = (f"{b.candidate_headline or 'Profil motivé'}"
                   f"{f' fort de {yrs} ans d’expérience' if yrs else ''}"
                   f"{f', maîtrisant {skills}' if skills else ''}. "
                   f"Souhaite mettre ces compétences au service du poste de {b.offer_title}"
                   f"{f' chez {b.offer_company}' if b.offer_company else ''}.")
        return txt, Usage()

    def letter(self, b: WritingBrief) -> tuple[dict, Usage]:
        exp = b.top_experiences[0] if b.top_experiences else None
        skills = ", ".join(b.matched_skills[:4])
        company = b.offer_company
        if b.lang == "en":
            paras = [
                f"I am writing to apply for the {b.offer_title} position"
                f"{f' at {company}' if company else ''}{f' in {b.offer_city}' if b.offer_city else ''}.",
                (f"As {exp['title']}{f' at {exp['company']}' if exp.get('company') else ''}, "
                 f"I {exp['bullets'][0][0].lower() + exp['bullets'][0][1:] if exp.get('bullets') else 'developed solid hands-on experience'}."
                 if exp else "I am eager to start my career and learn quickly on the job."),
                f"{f'My skills in {skills} match your requirements. ' if skills else ''}"
                "I am reliable, organised and committed to delivering quality work.",
                "I would welcome the opportunity to discuss my application with you.",
            ]
            return {"salutation": "Dear Hiring Manager,", "paragraphs": paras, "closing": "Kind regards,"}, Usage()
        if b.lang == "ar":
            paras = [
                f"يشرفني أن أتقدم بطلب لشغل منصب {b.offer_title}{f' لدى {company}' if company else ''}.",
                (f"بصفتي {exp['title']}{f' في {exp['company']}' if exp.get('company') else ''}، اكتسبت خبرة عملية متينة."
                 if exp else "أنا متحمس لبدء مساري المهني والتعلم بسرعة."),
                f"{f'تتوافق كفاءاتي في {skills} مع متطلبات المنصب. ' if skills else ''}أتميز بالجدية والتنظيم والالتزام.",
                "يسعدني أن أتشرف بمقابلتكم لمناقشة ترشيحي.",
            ]
            return {"salutation": "السيد(ة) المسؤول(ة) عن التوظيف،", "paragraphs": paras,
                    "closing": "وتفضلوا بقبول فائق التقدير والاحترام،"}, Usage()
        paras = [
            f"Je vous adresse ma candidature au poste de {b.offer_title}"
            f"{f' au sein de {company}' if company else ''}{f' à {b.offer_city}' if b.offer_city else ''}.",
            (f"En tant que {exp['title']}{f' chez {exp['company']}' if exp.get('company') else ''}, "
             f"j’ai notamment assuré : {exp['bullets'][0][0].lower() + exp['bullets'][0][1:] if exp.get('bullets') else 'des missions variées'}."
             if exp else "Motivé(e) et prêt(e) à apprendre, je souhaite débuter mon parcours professionnel dans votre structure."),
            f"{f'Mes compétences en {skills} correspondent à vos attentes. ' if skills else ''}"
            "Rigoureux(se), fiable et impliqué(e), je m’adapte rapidement à un nouvel environnement.",
            "Je serais heureux(se) de vous exposer ma motivation lors d’un entretien.",
        ]
        return {"salutation": "Madame, Monsieur,", "paragraphs": paras,
                "closing": "Je vous prie d’agréer, Madame, Monsieur, l’expression de mes salutations distinguées."}, Usage()


class GeminiVertexProvider:
    """Gemini sur Vertex AI (GCP), région UE. Identifiants : compte de service (GOOGLE_APPLICATION_CREDENTIALS).

    Économie de tokens : entrée = WritingBrief compact (pas le CV entier), sortie JSON contrainte et courte,
    raisonnement interne au minimum, et chaque résultat est mis en cache en base par l'appelant.
    """

    name = "gemini"

    def __init__(self):
        import json
        import os

        from google import genai

        from app.config import ROOT

        creds = settings.google_application_credentials
        if settings.gcp_service_account_json and not creds:
            # Hébergement : le JSON est fourni dans une variable d'environnement secrète (jamais dans le dépôt)
            import tempfile

            fd, creds = tempfile.mkstemp(suffix=".json")
            with os.fdopen(fd, "w") as f:
                f.write(settings.gcp_service_account_json)
        if creds:
            creds = str((ROOT / creds).resolve()) if not os.path.isabs(creds) else creds
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds
        project = settings.gcp_project or (json.load(open(creds))["project_id"] if creds else None)
        self.client = genai.Client(vertexai=True, project=project, location=settings.gcp_location)
        self.model = settings.llm_model

    def _json(self, system: str, payload: dict, schema: dict, max_tokens: int) -> tuple[dict, Usage]:
        import json

        from google.genai import types

        cfg = dict(system_instruction=system, response_mime_type="application/json", response_json_schema=schema,
                   temperature=0.4, max_output_tokens=max_tokens,
                   automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        try:
            config = types.GenerateContentConfig(**cfg, thinking_config=types.ThinkingConfig(thinking_level="low"))
            resp = self.client.models.generate_content(model=self.model, contents=json.dumps(payload, ensure_ascii=False), config=config)
        except Exception:  # modèle sans réglage de raisonnement : on réessaie sans
            resp = self.client.models.generate_content(model=self.model, contents=json.dumps(payload, ensure_ascii=False),
                                                       config=types.GenerateContentConfig(**cfg))
        u = resp.usage_metadata
        return json.loads(resp.text), Usage(u.prompt_token_count or 0, (u.candidates_token_count or 0) + (u.thoughts_token_count or 0))

    _RULES = ("Règles : n'invente AUCUN fait (diplôme, employeur, chiffre, compétence) absent des données ; "
              "ton professionnel et sobre ; pas de tiret cadratin ; écris exclusivement dans la langue demandée ({lang}).")

    def summary(self, b: WritingBrief) -> tuple[str, Usage]:
        out, usage = self._json(
            "Tu rédiges l'accroche (2 phrases, 45 mots max) d'un CV ciblé pour une offre. " + self._RULES.format(lang=b.lang),
            b.__dict__, {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}, 300)
        return out["summary"], usage

    def letter(self, b: WritingBrief) -> tuple[dict, Usage]:
        schema = {"type": "object", "properties": {
            "salutation": {"type": "string"}, "paragraphs": {"type": "array", "items": {"type": "string"}},
            "closing": {"type": "string"}}, "required": ["salutation", "paragraphs", "closing"]}
        return self._json(
            "Tu rédiges une lettre de motivation concise (3 ou 4 paragraphes, 220 mots max) pour l'offre, "
            "en t'appuyant sur les expériences et compétences fournies. Formules d'appel et de politesse usuelles "
            "dans la langue demandée. " + self._RULES.format(lang=b.lang), b.__dict__, schema, 900)

    def translate_texts(self, texts: list[str], target: str) -> tuple[list[str] | None, Usage]:
        if not texts:
            return [], Usage()
        schema = {"type": "object", "properties": {"t": {"type": "array", "items": {"type": "string"}}}, "required": ["t"]}
        out, usage = self._json(
            f"Traduis chaque élément de la liste vers la langue « {target} » (fr, ar ou en). Conserve le Markdown "
            "(**gras**, puces « - »), les noms propres, sigles et montants. Même nombre d'éléments, même ordre.",
            {"items": texts}, schema, max(256, sum(len(t) for t in texts) // 2))
        # Le modèle échappe parfois les retours à la ligne ("\\n" littéral) : on les rétablit
        items = [t.replace("\\n", "\n") for t in out["t"]]
        return (items if len(items) == len(texts) else None), usage


def get_provider():
    if settings.llm_provider in ("gemini", "vertex"):
        try:
            return GeminiVertexProvider()
        except Exception as e:  # identifiants absents ou invalides : la démo continue en mode simulé
            import logging

            logging.getLogger("khedma.ai").warning("Gemini indisponible (%s) : repli sur le mode simulé", e)
    return MockProvider()
