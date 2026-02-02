"""Connecteur ANAPEC.

- Liste : endpoint JSON public du SIGEC utilisé par le portail anapec.ma (15 offres / page).
- Détail : fiche HTML SIGEC (anapec.org), parsée par libellés « Clé : valeur ».
anapec.org a une chaîne de certificat incomplète : vérification SSL désactivée pour ce seul hôte.
"""
import re
from typing import AsyncIterator

from selectolax.parser import HTMLParser

from app.sourcing.connectors.base import Connector, RawOffer
from app.sourcing.normalize import parse_date

LIST_URL = "https://www.anapec.org/sigec-app-rv/chercheurs/resultat_recherche_json/page:{page}/tout:all/language:fr"
DETAIL_URL = "https://www.anapec.org/sigec-app-rv/fr/entreprises/bloc_offre_home/{id}/display"

# Libellés de champs structurés de la fiche -> champ
_FIELDS = {
    "référence de l’offre": "ref", "date": "date", "agence": "agence", "secteur d’activité": "sector",
    "date de début": "start", "type de contrat": "contract", "lieu de travail": "city", "formation": "education",
    "langues": "languages", "salaire mensuel": "salary", "permis": "license",
    "expérience professionnelle": "experience", "poste": "occupation", "commentaire": "comment",
}
# Libellés qui ouvrent un bloc de texte libre (regroupé dans la description)
_TEXT_BLOCKS = {"caractéristiques du poste", "description du profil", "missions", "compétences",
                "compétences spécifiques", "tâches / activités"}
_SECTIONS = {"description de l'entreprise", "description de poste", "profil recherché"}
_NOISE = {"partager sur", "envoyer à un ami", "[scanner qr]"}


def _label(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace("\uf0b7", "").replace("\xa0", " ")).strip().rstrip(":").strip().lower()


class AnapecConnector(Connector):
    key = "anapec"
    name = "ANAPEC"
    base_url = "https://anapec.ma"
    verify_ssl = False

    async def list_offers(self, max_pages: int = 5) -> AsyncIterator[RawOffer]:
        for page in range(1, max_pages + 1):
            data = (await self.get(LIST_URL.format(page=page))).json()
            items = data.get("Offre") or []
            if not items:
                return
            for it in items:
                if not (it.get("id") and (it.get("intitule_poste") or "").strip()):
                    continue  # entrée incomplète côté source
                yield RawOffer(
                    source=self.key,
                    source_ref=it["id"],
                    url=DETAIL_URL.format(id=it["id"]),
                    title=it["intitule_poste"].strip(),
                    company=None if (it.get("entreprise") or "-").strip() == "-" else it["entreprise"].strip(),
                    city=it.get("lieu_travail"),
                    posted_at=parse_date(it.get("date_offre")),
                    extra={"ref_offre": it.get("ref_offre")},
                )
            if not data.get("paginate", {}).get("next"):
                return

    async def fetch_detail(self, offer: RawOffer) -> RawOffer:
        html = (await self.get(offer.url)).text
        node = HTMLParser(html).css_first(".bloc-affiche-offre")
        if node is None:
            return offer
        for bad in node.css("script,style"):
            bad.decompose()
        lines = [l.strip() for l in node.text(separator="\n").splitlines() if l.strip()]

        fields: dict[str, list[str]] = {}
        desc: list[str] = []
        current = None
        for line in lines:
            lab = _label(line)
            if lab in _NOISE or lab in _SECTIONS:
                current = None
            elif lab in _FIELDS:
                current = _FIELDS[lab]
                fields[current] = []
            elif lab in _TEXT_BLOCKS:
                current = "desc"
                if lab != "caractéristiques du poste":
                    desc.append(f"\n{line.strip().rstrip(':').strip()} :")
            elif current == "desc":
                desc.append(line)
            elif current:
                fields[current].append(line)

        m = re.search(r"^\((\d+)\)$", next((l for l in lines if re.fullmatch(r"\(\d+\)", l)), ""))
        if m:
            offer.positions = int(m.group(1))
        get = lambda k: " ".join(fields.get(k, [])).strip() or None  # noqa: E731
        offer.sector = get("sector")
        offer.contract_raw = get("contract")
        city = get("city")
        if city and not city.lower().startswith("http"):  # parfois une pièce jointe à la place de la ville
            offer.city = city
        offer.start_date = parse_date(get("start"))
        offer.education = (get("education") or "").replace(" ,", ", ").strip() or None
        if get("comment"):
            desc.append(f"\nCommentaire : {get('comment')}")
        offer.description = "\n".join(desc).strip() or None
        offer.extra.update(salary=get("salary"), experience=get("experience"),
                           occupation=get("occupation"), license=(get("license") or "").strip(", ") or None)
        offer.languages = {
            k.strip(): v.strip() for k, v in (l.split(":", 1) for l in fields.get("languages", []) if ":" in l)
        } or None
        offer.extra["agence"] = get("agence")
        return offer
