"""Normalisation des champs d'offres : région, contrat, langue, empreinte de dédoublonnage.

Tout est déterministe (dictionnaires + règles) : zéro token LLM consommé ici.
"""
import hashlib
import re
import unicodedata
from datetime import date, datetime

REGIONS = [
    "Tanger-Tétouan-Al Hoceïma",
    "L'Oriental",
    "Fès-Meknès",
    "Rabat-Salé-Kénitra",
    "Béni Mellal-Khénifra",
    "Casablanca-Settat",
    "Marrakech-Safi",
    "Drâa-Tafilalet",
    "Souss-Massa",
    "Guelmim-Oued Noun",
    "Laâyoune-Sakia El Hamra",
    "Dakhla-Oued Ed-Dahab",
]

# Villes / provinces (sans accents, majuscules) -> index dans REGIONS
_CITY_REGION = {
    0: "TANGER TETOUAN AL HOCEIMA HOCEIMA LARACHE KSAR EL KEBIR CHEFCHAOUEN CHAOUEN OUEZZANE FNIDEQ MDIQ M'DIQ "
       "MARTIL ASSILAH IMZOUREN OUED LAOU TARGUIST",
    1: "OUJDA NADOR BERKANE TAOURIRT JERADA JERRADA FIGUIG BOUARFA GUERCIF DRIOUCH ZAIO SELOUANE AHFIR SAIDIA "
       "AL AROUI EL AIOUN AZDOUFAL",
    2: "FES FEZ MEKNES TAZA SEFROU IFRANE AZROU EL HAJEB MOULAY YACOUB TAOUNATE BOULEMANE MISSOUR IMOUZZER",
    3: "RABAT SALE KENITRA TEMARA SKHIRAT KHEMISSET SIDI KACEM SIDI SLIMANE TIFLET SOUK EL ARBAA SIDI YAHYA",
    4: "BENI MELLAL KHENIFRA KHOURIBGA FQUIH BEN SALAH FKIH BEN SALAH AZILAL KASBA TADLA OUED ZEM BEJAAD",
    5: "CASABLANCA CASA MOHAMMEDIA EL JADIDA SETTAT BERRECHID BENSLIMANE SIDI BENNOUR NOUACEUR MEDIOUNA BOUSKOURA "
       "AZEMMOUR HAD SOUALEM BOUZNIKA DAR BOUAZZA HAY HASSANI AIN SEBAA SIDI MAAROUF AIN CHOCK MAARIF SIDI BERNOUSSI",
    6: "MARRAKECH SAFI ESSAOUIRA KELAA DES SRAGHNA KELAAT SRAGHNA CHICHAOUA YOUSSOUFIA BENGUERIR BEN GUERIR REHAMNA "
       "TAHANNAOUT AL HAOUZ AIT OURIR AMIZMIZ",
    7: "ERRACHIDIA OUARZAZATE OUARZAZAT ZAGORA TINGHIR TINERHIR MIDELT RISSANI ERFOUD GOULMIMA KELAAT MGOUNA",
    8: "AGADIR INEZGANE AIT MELLOUL TAROUDANT TIZNIT TATA CHTOUKA BIOUGRA OULAD TEIMA DCHEIRA AIT BAHA",
    9: "GUELMIM TAN TAN TANTAN SIDI IFNI ASSA ZAG ASSA",
    10: "LAAYOUNE LAYOUNE BOUJDOUR TARFAYA SMARA ESSMARA ES SEMARA",
    11: "DAKHLA AOUSSERD",
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _key(s: str) -> str:
    return re.sub(r"[^A-Z' ]+", " ", strip_accents(s).upper()).strip()


# Noms de villes composés, à reconnaître avant les mots simples (ex. "SIDI SLIMANE")
_MULTI = [
    "KSAR EL KEBIR", "OUED LAOU", "AL HOCEIMA", "EL AIOUN", "AL AROUI", "EL HAJEB", "MOULAY YACOUB", "SIDI KACEM",
    "SIDI SLIMANE", "SOUK EL ARBAA", "SIDI YAHYA", "BENI MELLAL", "FQUIH BEN SALAH", "FKIH BEN SALAH", "KASBA TADLA",
    "OUED ZEM", "EL JADIDA", "SIDI BENNOUR", "HAD SOUALEM", "DAR BOUAZZA", "KELAA DES SRAGHNA", "KELAAT SRAGHNA",
    "BEN GUERIR", "AL HAOUZ", "AIT OURIR", "KELAAT MGOUNA", "AIT MELLOUL", "OULAD TEIMA", "AIT BAHA", "TAN TAN",
    "SIDI IFNI", "ASSA ZAG", "ES SEMARA", "HAY HASSANI", "AIN SEBAA", "SIDI MAAROUF", "AIN CHOCK", "SIDI BERNOUSSI",
]


def _build_index() -> list[tuple[str, int]]:
    out = []
    for idx, blob in _CITY_REGION.items():
        rest = f" {blob} "
        for m in _MULTI:
            if f" {m} " in rest:
                out.append((m, idx))
                rest = rest.replace(f" {m} ", " ")
        out += [(w, idx) for w in rest.split()]
    return sorted(out, key=lambda t: -len(t[0]))


_INDEX = _build_index()


def city_to_region(city: str | None) -> str | None:
    """'KENITRA UNIVERSITAIRE' -> 'Rabat-Salé-Kénitra' ; 'PLUSIEURS VILLES' -> None."""
    if not city:
        return None
    k = f" {_key(city)} "
    for term, idx in _INDEX:
        if f" {term} " in k:
            return REGIONS[idx]
    return None


def clean_city(city: str | None) -> str | None:
    if not city or city.strip() in {"-", ""}:
        return None
    return city.strip().title()


CONTRACTS = {  # valeur normalisée -> motifs reconnus (sur texte sans accents, minuscules)
    "IDMAJ": [r"^ci$", r"contrat d.?insertion", r"idmaj", r"anapec"],
    "CDI": [r"\bcdi\b", r"indetermin", r"permanent"],
    "CDD": [r"\bcdd\b", r"determin", r"\bcontract\b", r"temporary"],
    "Stage": [r"\bstage", r"internship", r"pfe"],
    "Intérim": [r"interim", r"temporaire"],
    "Freelance": [r"freelance", r"independant", r"consultant"],
    "Saisonnier": [r"saisonn"],
    "Concours": [r"concours"],
}


def normalize_contract(raw: str | None) -> str | None:
    if not raw:
        return None
    k = strip_accents(raw).lower().strip()
    for norm, patterns in CONTRACTS.items():
        if any(re.search(p, k) for p in patterns):
            return norm
    return "Autre"


_FR = set("le la les des une un et pour dans avec vous nous poste profil entreprise est sur".split())
_EN = set("the and for with you we our job role company is on to of in".split())


def detect_language(text: str) -> str:
    """Langue d'origine de l'offre (fr/ar/en) : heuristique rapide, sans modèle."""
    if not text:
        return "fr"
    arabic = sum(1 for c in text if "؀" <= c <= "ۿ")
    letters = sum(1 for c in text if c.isalpha()) or 1
    if arabic / letters > 0.3:
        return "ar"
    words = re.findall(r"[a-zA-Z]+", text.lower())
    fr = sum(w in _FR for w in words)
    en = sum(w in _EN for w in words)
    return "en" if en > fr * 1.2 else "fr"


def fingerprint(title: str, company: str | None, city: str | None) -> str:
    """Même poste + même employeur + même ville = même offre, quel que soit le site."""
    norm = " | ".join(_key(x or "") for x in (title, company if company not in (None, "-") else "", city))
    return hashlib.sha1(norm.encode()).hexdigest()


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None
