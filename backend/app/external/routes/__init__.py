"""External API v1 router aggregation."""

from fastapi import APIRouter

from app.external.routes import guilds, messaging, meta

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(meta.router)
v1_router.include_router(messaging.router)
v1_router.include_router(guilds.router)
