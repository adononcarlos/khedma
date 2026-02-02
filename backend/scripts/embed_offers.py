"""Vectorise les offres sans embedding (incrémental) : python -m scripts.embed_offers"""
import time

from sqlalchemy import select, text

from app.db import SessionLocal, engine, init_db
from app.matching.embeddings import embed, offer_text
from app.models import Offer

BATCH = 128

if __name__ == "__main__":
    init_db()
    with engine.begin() as conn:  # index ANN (HNSW, distance cosinus)
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_offers_embedding ON offers USING hnsw (embedding vector_cosine_ops)"))
    total, t0 = 0, time.time()
    while True:
        with SessionLocal() as s:
            rows = s.scalars(
                select(Offer).where(Offer.embedding.is_(None), Offer.detail_fetched.is_(True)).limit(BATCH)
            ).all()
            if not rows:
                break
            for o, v in zip(rows, embed([offer_text(o) for o in rows])):
                o.embedding = v
            s.commit()
            total += len(rows)
            print(f"{total} offres vectorisées ({total / (time.time() - t0):.0f}/s)")
    print("terminé :", total)
