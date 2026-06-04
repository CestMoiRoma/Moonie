"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session

if TYPE_CHECKING:
    from app.bot.client import MoonieBot

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_bot(request: Request) -> "MoonieBot":
    """Return the live bot instance, or 503 if it isn't ready yet."""
    bot = getattr(request.app.state, "bot", None)
    if bot is None or not bot.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot is not connected yet.",
        )
    return bot


def get_bot_optional(request: Request) -> "MoonieBot | None":
    """Return the live bot if ready, else None — for best-effort actions (e.g.
    invalidating a cog's cache) that must not fail when the bot is offline."""
    bot = getattr(request.app.state, "bot", None)
    if bot is None or not bot.is_ready():
        return None
    return bot


BotDep = Annotated["MoonieBot", Depends(get_bot)]
OptionalBotDep = Annotated["MoonieBot | None", Depends(get_bot_optional)]
