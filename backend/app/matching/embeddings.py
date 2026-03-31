"""Embeddings multilingues (FR/AR/EN, interlingues) : un profil en arabe retrouve une offre en français.

Deux fournisseurs, même dimension (384) pour rester compatibles avec l'index pgvector :
- "local"  : paraphrase-multilingual-MiniLM-L12-v2 en ONNX (fastembed), zéro appel externe ;
- "vertex" : text-multilingual-embedding-002 (Vertex AI, europe-west1), pour l'hébergement sans serveur
             où un modèle de 220 Mo ne tient pas.
"""
from functools import lru_cache

from app.config import settings

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384


@lru_cache(maxsize=1)
def _local_model():
    import os

    from fastembed import TextEmbedding

    # FASTEMBED_CACHE_PATH : modèle pré-téléchargé dans l'image Docker (démarrage sans réseau)
    return TextEmbedding(MODEL, threads=4, cache_dir=os.environ.get("FASTEMBED_CACHE_PATH"))


@lru_cache(maxsize=1)
def _vertex_client():
    from google import genai

    from app.ai.provider import vertex_credentials

    project = vertex_credentials()
    return genai.Client(vertexai=True, project=project, location=settings.embedding_location)


def _vertex_embed(texts: list[str], task: str) -> list[list[float]]:
    from google.genai import types

    out: list[list[float]] = []
    for i in range(0, len(texts), 25):  # limite de l'API : nombre de textes et de tokens par requête
        r = _vertex_client().models.embed_content(
            model=settings.embedding_model, contents=[t[:6000] for t in texts[i:i + 25]],
            config=types.EmbedContentConfig(output_dimensionality=DIM, task_type=task))
        out += [e.values for e in r.embeddings]
    return out


def embed(texts: list[str], batch_size: int = 64, task: str = "RETRIEVAL_DOCUMENT") -> list:
    """task : RETRIEVAL_DOCUMENT pour les offres, RETRIEVAL_QUERY pour un profil (Vertex uniquement)."""
    if settings.embedding_provider == "vertex":
        return _vertex_embed(texts, task)
    return list(_local_model().embed(texts, batch_size=batch_size))


def offer_text(o) -> str:
    """Texte représentatif d'une offre : le titre et le métier pèsent plus (répétés)."""
    parts = [o.title, o.title, o.occupation or "", o.sector or "", o.education or "", (o.description or "")[:1200]]
    return "\n".join(p for p in parts if p)
