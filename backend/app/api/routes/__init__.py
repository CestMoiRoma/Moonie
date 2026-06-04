"""Aggregates all feature routers under a single APIRouter."""

from fastapi import APIRouter

from app.api.routes import (
    autoban,
    embeds,
    guilds,
    moderation,
    permissions,
    reaction_roles,
    roles,
    settings,
    system,
    welcome,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(system.router)
api_router.include_router(guilds.router)
api_router.include_router(settings.router)
api_router.include_router(moderation.router)
api_router.include_router(welcome.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(reaction_roles.router)
api_router.include_router(embeds.router)
api_router.include_router(autoban.router)
