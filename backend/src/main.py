"""Academic Hunter - FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine
from .models.models import Base
from .routers import auth, papers, pipeline, subscriptions


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

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(subscriptions.router)
app.include_router(papers.router)
app.include_router(pipeline.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
