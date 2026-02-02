from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import account, offers, staff
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
