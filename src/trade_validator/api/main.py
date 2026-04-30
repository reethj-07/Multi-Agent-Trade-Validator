"""FastAPI application entry."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from trade_validator.api.routes import pipeline, query
from trade_validator.db.session import init_db


def _resolve_frontend_dir() -> Path | None:
    """Locate bundled SPA (repo-root/frontend/) or TRADE_VALIDATOR_FRONTEND_DIR."""
    env = os.environ.get("TRADE_VALIDATOR_FRONTEND_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        return p if (p / "index.html").is_file() else None
    here = Path(__file__).resolve().parent
    for d in [here, *here.parents]:
        cand = d / "frontend"
        if (cand / "index.html").is_file():
            return cand
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Trade document validation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


_frontend_dir = _resolve_frontend_dir()
if _frontend_dir is not None:
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dir), html=True),
        name="frontend",
    )
