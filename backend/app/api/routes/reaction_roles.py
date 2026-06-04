"""Reaction-role messages: build them in the dashboard, then publish to a channel."""

from __future__ import annotations

import discord
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import BotDep, SessionDep
from app.db.models import ReactionRoleEntry, ReactionRoleMessage
from app.services.reaction_roles import ReactionRoleError, publish

router = APIRouter(prefix="/reaction-roles", tags=["reaction-roles"])


class EntryIn(BaseModel):
    role_id: int
    emoji: str | None = None
    label: str | None = None


class EntryOut(BaseModel):
    role_id: str
    emoji: str | None = None
    label: str | None = None


class ReactionRoleIn(BaseModel):
    channel_id: int
    mode: str = Field("emoji", pattern="^(emoji|button)$")
    title: str | None = None
    description: str | None = None
    entries: list[EntryIn] = Field(default_factory=list)


class ReactionRoleOut(BaseModel):
    id: int
    guild_id: str
    channel_id: str
    message_id: str | None
    mode: str
    title: str | None
    description: str | None
    entries: list[EntryOut]


async def _load(session, guild_id: int, rr_id: int) -> ReactionRoleMessage:
    rr = await session.scalar(
        select(ReactionRoleMessage)
        .where(ReactionRoleMessage.id == rr_id, ReactionRoleMessage.guild_id == guild_id)
        .options(selectinload(ReactionRoleMessage.entries))
    )
    if rr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reaction-role message not found.")
    return rr


def _to_out(rr: ReactionRoleMessage) -> ReactionRoleOut:
    return ReactionRoleOut(
        id=rr.id,
        guild_id=str(rr.guild_id),
        channel_id=str(rr.channel_id),
        message_id=str(rr.message_id) if rr.message_id else None,
        mode=rr.mode,
        title=rr.title,
        description=rr.description,
        entries=[EntryOut(role_id=str(e.role_id), emoji=e.emoji, label=e.label) for e in rr.entries],
    )


@router.get("/{guild_id}", response_model=list[ReactionRoleOut])
async def list_messages(guild_id: int, session: SessionDep) -> list[ReactionRoleOut]:
    rows = await session.scalars(
        select(ReactionRoleMessage)
        .where(ReactionRoleMessage.guild_id == guild_id)
        .options(selectinload(ReactionRoleMessage.entries))
        .order_by(ReactionRoleMessage.id.desc())
    )
    return [_to_out(rr) for rr in rows]


@router.post("/{guild_id}", response_model=ReactionRoleOut, status_code=status.HTTP_201_CREATED)
async def create_message(
    guild_id: int, payload: ReactionRoleIn, session: SessionDep
) -> ReactionRoleOut:
    rr = ReactionRoleMessage(
        guild_id=guild_id,
        channel_id=payload.channel_id,
        mode=payload.mode,
        title=payload.title,
        description=payload.description,
        entries=[
            ReactionRoleEntry(role_id=e.role_id, emoji=e.emoji, label=e.label)
            for e in payload.entries
        ],
    )
    session.add(rr)
    await session.commit()
    rr = await _load(session, guild_id, rr.id)
    return _to_out(rr)


@router.delete("/{guild_id}/{rr_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(guild_id: int, rr_id: int, session: SessionDep) -> None:
    rr = await _load(session, guild_id, rr_id)
    await session.delete(rr)
    await session.commit()


@router.post("/{guild_id}/{rr_id}/publish", response_model=ReactionRoleOut)
async def publish_message(
    guild_id: int, rr_id: int, bot: BotDep, session: SessionDep
) -> ReactionRoleOut:
    rr = await _load(session, guild_id, rr_id)
    channel = bot.get_channel(rr.channel_id)
    if not isinstance(channel, discord.abc.Messageable):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found or not text-based.")
    try:
        message_id = await publish(channel, rr)
    except ReactionRoleError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except discord.Forbidden as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Missing permission to post in that channel."
        ) from exc
    rr.message_id = message_id
    await session.commit()
    rr = await _load(session, guild_id, rr_id)
    return _to_out(rr)
