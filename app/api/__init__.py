"""API routes."""

from app.api import graph, import_routes, jobs, persons, search
from fastapi import APIRouter

api_router = APIRouter()

# Include sub-routers
api_router.include_router(import_routes.router, prefix="/import", tags=["import"])
api_router.include_router(persons.router, prefix="/person", tags=["persons"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
