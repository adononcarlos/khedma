"""Recalcule tous les embeddings avec le fournisseur configuré (ex. passage du modèle local à Vertex) :
EMBEDDING_PROVIDER=vertex DATABASE_URL=... python -m scripts.reembed"""
import time

from sqlalchemy import select

from app.db import SessionLocal
from app.matching.embeddings import embed, offer_text
from app.matching.engine import profile_text
from app.models import Offer, Profile

BATCH = 100

if __name__ == "__main__":
    t0 = time.time()
    for model, to_text, task in ((Offer, offer_text, "RETRIEVAL_DOCUMENT"), (Profile, profile_text, "RETRIEVAL_QUERY")):
        with SessionLocal() as s:
            rows = s.scalars(select(model)).all()
            for i in range(0, len(rows), BATCH):
                batch = rows[i:i + BATCH]
                for r, v in zip(batch, embed([to_text(r) for r in batch], task=task)):
                    r.embedding = v
                s.commit()
                print(f"{model.__tablename__} : {min(i + BATCH, len(rows))}/{len(rows)} ({time.time() - t0:.0f}s)", flush=True)
