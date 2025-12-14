"""UI routes."""

from app.ui import views
from fastapi import APIRouter

ui_router = APIRouter()

# Include view routes
ui_router.include_router(views.router)
