"""Per-user logging: flag/unflag users and list who is being logged."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import BotDep, SessionDep
from app.db.models import FlaggedUser
from app.services.guild_config import get_or_create_guild_config
from app.services.user_logging import UserLoggingError, create_log_channel

router = APIRouter(prefix="/user-logging", tags=["user-logging"])


class FlaggedOut(BaseModel):
    id: int
    user_id: str
    reason: str | None
    log_channel_id: str | None
    active: bool
    created_at: datetime


class FlagRequest(BaseModel):
    user_id: int
    reason: str | None = None


def _to_out(f: FlaggedUser) -> FlaggedOut:
    return FlaggedOut(
        id=f.id,
        user_id=str(f.user_id),
        reason=f.reason,
        log_channel_id=str(f.log_channel_id) if f.log_channel_id else None,
        active=f.active,
        created_at=f.created_at,
    )


def _invalidate(bot, guild_id: int) -> None:
    cog = bot.get_cog("UserLogging")
    if cog is not None:
        cog.invalidate(guild_id)


@router.get("/{guild_id}", response_model=list[FlaggedOut])
async def list_flagged(guild_id: int, session: SessionDep) -> list[FlaggedOut]:
    rows = await session.scalars(
        select(FlaggedUser)
        .where(FlaggedUser.guild_id == guild_id)
        .order_by(FlaggedUser.created_at.desc())
    )
    return [_to_out(f) for f in rows]


@router.post("/{guild_id}", response_model=FlaggedOut, status_code=status.HTTP_201_CREATED)
async def flag_user(
    guild_id: int, payload: FlagRequest, bot: BotDep, session: SessionDep
) -> FlaggedOut:
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guild not found.")

    config = await get_or_create_guild_config(session, guild_id)
    if not config.log_category_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No logging category configured. Set one in Settings first.",
        )

    existing = await session.scalar(
        select(FlaggedUser).where(
            FlaggedUser.guild_id == guild_id, FlaggedUser.user_id == payload.user_id
        )
    )
    if existing is not None and existing.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already being logged.")

    user = bot.get_user(payload.user_id) or await bot.fetch_user(payload.user_id)
    try:
        channel = await create_log_channel(guild, user, config.log_category_id)
    except UserLoggingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    if existing is not None:
        existing.active = True
        existing.reason = payload.reason
        existing.log_channel_id = channel.id
        flagged = existing
    else:
        flagged = FlaggedUser(
            guild_id=guild_id,
            user_id=payload.user_id,
            reason=payload.reason,
            log_channel_id=channel.id,
            active=True,
        )
        session.add(flagged)
    await session.commit()
    await session.refresh(flagged)
    _invalidate(bot, guild_id)
    return _to_out(flagged)


@router.delete("/{guild_id}/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unflag_user(
    guild_id: int, user_id: int, bot: BotDep, session: SessionDep
) -> None:
    flagged = await session.scalar(
        select(FlaggedUser).where(
            FlaggedUser.guild_id == guild_id, FlaggedUser.user_id == user_id
        )
    )
    if flagged is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not flagged.")
    flagged.active = False  # keep the channel + history; just stop logging
    await session.commit()
    _invalidate(bot, guild_id)
