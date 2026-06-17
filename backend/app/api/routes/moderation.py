"""Moderation: view the audit log and issue actions from the dashboard."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import BotDep, SessionDep
from app.db.models import ModAction
from app.services.moderation import ModerationError, apply_action, record_action

router = APIRouter(prefix="/moderation", tags=["moderation"])


class ModActionOut(BaseModel):
    id: int
    guild_id: str
    action: str
    target_id: str
    target_tag: str | None
    moderator_id: str
    moderator_tag: str | None
    reason: str | None
    created_at: datetime


class ModActionRequest(BaseModel):
    action: str = Field(..., description="kick | ban | unban | warn | mute | unmute")
    target_id: int
    reason: str | None = None
    duration_minutes: int | None = Field(None, description="For 'mute' actions")
    # Until dashboard auth (Phase 4), the acting moderator is identified by the client.
    moderator_id: int = 0
    moderator_tag: str | None = "dashboard"


@router.get("/{guild_id}/actions", response_model=list[ModActionOut])
async def list_actions(
    guild_id: int,
    session: SessionDep,
    limit: int = Query(50, le=200),
) -> list[ModActionOut]:
    rows = await session.scalars(
        select(ModAction)
        .where(ModAction.guild_id == guild_id)
        .order_by(ModAction.created_at.desc())
        .limit(limit)
    )
    return [
        ModActionOut(
            id=r.id,
            guild_id=str(r.guild_id),
            action=r.action,
            target_id=str(r.target_id),
            target_tag=r.target_tag,
            moderator_id=str(r.moderator_id),
            moderator_tag=r.moderator_tag,
            reason=r.reason,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{guild_id}/actions", response_model=ModActionOut, status_code=status.HTTP_201_CREATED)
async def create_action(
    guild_id: int,
    payload: ModActionRequest,
    bot: BotDep,
    session: SessionDep,
) -> ModActionOut:
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guild not found.")

    try:
        target_tag = await apply_action(
            guild,
            payload.action,
            payload.target_id,
            reason=payload.reason,
            duration_minutes=payload.duration_minutes,
        )
    except ModerationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    entry = await record_action(
        session,
        guild_id=guild_id,
        action=payload.action,
        target_id=payload.target_id,
        target_tag=target_tag,
        moderator_id=payload.moderator_id,
        moderator_tag=payload.moderator_tag,
        reason=payload.reason,
    )
    await session.commit()
    await session.refresh(entry)
    return ModActionOut(
        id=entry.id,
        guild_id=str(entry.guild_id),
        action=entry.action,
        target_id=str(entry.target_id),
        target_tag=entry.target_tag,
        moderator_id=str(entry.moderator_id),
        moderator_tag=entry.moderator_tag,
        reason=entry.reason,
        created_at=entry.created_at,
    )
