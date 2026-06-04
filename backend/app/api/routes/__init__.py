"""Aggregates all feature routers under a single APIRouter."""

from fastapi import APIRouter

from app.api.routes import guilds, moderation, roles, settings, system, welcome

api_router = APIRouter(prefix="/api")
api_router.include_router(system.router)
api_router.include_router(guilds.router)
api_router.include_router(settings.router)
api_router.include_router(moderation.router)
api_router.include_router(welcome.router)
api_router.include_router(roles.router)
