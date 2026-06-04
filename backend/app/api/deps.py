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


BotDep = Annotated["MoonieBot", Depends(get_bot)]
