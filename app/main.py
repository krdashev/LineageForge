"""
LineageForge FastAPI application.

This is the web service entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import settings
from app.database import init_db
from app.ui import ui_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler."""
    # Startup
    init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Mount API routes
app.include_router(api_router, prefix="/api")

# Mount UI routes
app.include_router(ui_router)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except RuntimeError:
    # Directory might not exist yet
    pass


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}
