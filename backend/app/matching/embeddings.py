"""Embeddings multilingues LOCAUX (FR/AR/EN, interlingues) : zéro token, zéro appel API.

Modèle : paraphrase-multilingual-MiniLM-L12-v2 (ONNX via fastembed, 384 dim, ~220 Mo, CPU).
Un profil rédigé en arabe peut ainsi être rapproché d'une offre rédigée en français.
"""
from functools import lru_cache

import numpy as np

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _model():
    import os

    from fastembed import TextEmbedding

    # FASTEMBED_CACHE_PATH : modèle pré-téléchargé dans l'image Docker (démarrage sans réseau)
    return TextEmbedding(MODEL, threads=4, cache_dir=os.environ.get("FASTEMBED_CACHE_PATH"))


def embed(texts: list[str], batch_size: int = 64) -> list[np.ndarray]:
    return list(_model().embed(texts, batch_size=batch_size))


def offer_text(o) -> str:
    """Texte représentatif d'une offre : le titre et le métier pèsent plus (répétés)."""
    parts = [o.title, o.title, o.occupation or "", o.sector or "", o.education or "", (o.description or "")[:1200]]
    return "\n".join(p for p in parts if p)
