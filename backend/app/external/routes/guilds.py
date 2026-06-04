"""External read endpoints: server info, channel discovery, presence counts."""

from __future__ import annotations

from typing import Annotated

import discord
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db.models import ApiKey
from app.external.deps import ExternalBotDep, enforce_guild, require_scope
from app.external.security import SCOPE_GUILDS_READ

router = APIRouter(prefix="/guilds", tags=["guilds"])

ReadKey = Annotated[ApiKey, Depends(require_scope(SCOPE_GUILDS_READ))]


class GuildInfo(BaseModel):
    id: str
    name: str
    icon_url: str | None
    member_count: int | None
    online_count: int | None
    channel_count: int


class ChannelInfo(BaseModel):
    id: str
    name: str
    type: str


class Presence(BaseModel):
    online: int | None
    members: int | None


def _require_guild(bot, key: ApiKey, guild_id: int) -> discord.Guild:
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guild not found or bot not a member.")
    enforce_guild(key, guild_id)
    return guild


@router.get("/{guild_id}", response_model=GuildInfo)
async def guild_info(guild_id: int, key: ReadKey, bot: ExternalBotDep) -> GuildInfo:
    guild = _require_guild(bot, key, guild_id)
    online: int | None = None
    try:
        fetched = await bot.fetch_guild(guild_id, with_counts=True)
        online = fetched.approximate_presence_count
    except discord.HTTPException:
        pass
    return GuildInfo(
        id=str(guild.id),
        name=guild.name,
        icon_url=guild.icon.url if guild.icon else None,
        member_count=guild.member_count,
        online_count=online,
        channel_count=len(guild.channels),
    )


@router.get("/{guild_id}/channels", response_model=list[ChannelInfo])
async def list_channels(guild_id: int, key: ReadKey, bot: ExternalBotDep) -> list[ChannelInfo]:
    guild = _require_guild(bot, key, guild_id)
    return [
        ChannelInfo(id=str(ch.id), name=ch.name, type=ch.type.name)
        for ch in guild.text_channels
    ]


@router.get("/{guild_id}/presence", response_model=Presence)
async def presence(guild_id: int, key: ReadKey, bot: ExternalBotDep) -> Presence:
    _require_guild(bot, key, guild_id)
    try:
        fetched = await bot.fetch_guild(guild_id, with_counts=True)
    except discord.HTTPException as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Could not fetch guild.") from exc
    return Presence(
        online=fetched.approximate_presence_count,
        members=fetched.approximate_member_count,
    )
