"""System / health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    version: str
    bot_ready: bool
    bot_user: str | None = None
    guild_count: int = 0


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    bot = getattr(request.app.state, "bot", None)
    ready = bool(bot and bot.is_ready())
    return HealthResponse(
        status="ok",
        version=__version__,
        bot_ready=ready,
        bot_user=str(bot.user) if ready and bot.user else None,
        guild_count=len(bot.guilds) if ready else 0,
    )
