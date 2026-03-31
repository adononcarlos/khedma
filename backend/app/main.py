from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api import account, offers, staff
from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.skip_init_db:  # en hébergement, le schéma est créé une fois, pas à chaque démarrage à froid
        init_db()
    yield


app = FastAPI(title="Khedma API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3010", "http://127.0.0.1:3010"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(offers.router)
app.include_router(account.router)
app.include_router(staff.router)


@app.get("/", include_in_schema=False)
def root():
    """La racine de l'API renvoie vers le site."""
    return RedirectResponse(settings.site_url)


@app.get("/api/health")
def health():
    return {"status": "ok"}
