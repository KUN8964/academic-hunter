"""Academic Hunter - FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from .config import settings
from .database import engine
from .models.models import Base
from .routers import auth, papers, pipeline, public, subscriptions

# Rate limiter: in-memory, keyed by client IP
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: sync_conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector")))
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Academic Hunter",
    description="科研情报聚合平台 — 科研版 Google Alerts + Feedly 合体",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow frontend dev server (configurable via CORS_ORIGINS env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(public.router)        # No auth required
app.include_router(auth.router)
app.include_router(subscriptions.router)
app.include_router(papers.router)
app.include_router(pipeline.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
