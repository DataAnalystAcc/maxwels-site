"""Kleinanzeigen Bot — Core API entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings
from routers import health, listings, drafts, posting


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create required directories on startup."""
    Path(settings.images_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.screenshots_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Kleinanzeigen Bot API",
    description="Backend for the Kleinanzeigen listing automation system",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(listings.router)
app.include_router(drafts.router)
app.include_router(posting.router)

# ── Static files ─────────────────────────────────────────────
# Serve review UI
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/review", StaticFiles(directory=str(static_dir), html=True), name="review")

# Serve images from /data/images
images_dir = Path(settings.images_dir)
if images_dir.exists():
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

# Serve screenshots from /data/screenshots
screenshots_dir = Path(settings.screenshots_dir)
if screenshots_dir.exists():
    app.mount("/screenshots", StaticFiles(directory=str(screenshots_dir)), name="screenshots")


@app.get("/")
async def root():
    return {
        "service": "Kleinanzeigen Bot API",
        "version": "0.1.0",
        "docs": "/docs",
        "review_ui": "/review",
    }
