"""
FastAPI application entry point.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.routes import process, jobs, clips


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure output directories exist
    settings.ensure_dirs()
    yield
    # Shutdown: nothing to clean up for now


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Auto highlight detection from YouTube videos",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(process.router, prefix="/api", tags=["process"])
app.include_router(jobs.router,    prefix="/api", tags=["jobs"])
app.include_router(clips.router,   prefix="/api", tags=["clips"])


# ── Serve clip files statically ──────────────────────────────────────────────
# e.g. GET /media/clips/abc.mp4
app.mount("/media/clips",  StaticFiles(directory=str(settings.CLIPS_DIR),  check_dir=False), name="clips")
app.mount("/media/videos", StaticFiles(directory=str(settings.VIDEOS_DIR), check_dir=False), name="videos")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION}
