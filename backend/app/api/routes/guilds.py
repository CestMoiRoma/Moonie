"""Read-only introspection of the guilds the bot is in.

Powers the dashboard's selectors (which guild, role, channel to act on).
"""

from __future__ import annotations

import discord
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import BotDep

router = APIRouter(prefix="/guilds", tags=["guilds"])


class GuildOut(BaseModel):
    id: str
    name: str
    icon_url: str | None = None
    member_count: int | None = None


class RoleOut(BaseModel):
    id: str
    name: str
    color: int
    position: int
    managed: bool


class ChannelOut(BaseModel):
    id: str
    name: str
    type: str
    category_id: str | None = None
    position: int


def _require_guild(bot, guild_id: int) -> discord.Guild:
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guild not found or bot not a member.")
    return guild


@router.get("", response_model=list[GuildOut])
async def list_guilds(bot: BotDep) -> list[GuildOut]:
    return [
        GuildOut(
            id=str(g.id),
            name=g.name,
            icon_url=g.icon.url if g.icon else None,
            member_count=g.member_count,
        )
        for g in bot.guilds
    ]


@router.get("/{guild_id}/roles", response_model=list[RoleOut])
async def list_roles(guild_id: int, bot: BotDep) -> list[RoleOut]:
    guild = _require_guild(bot, guild_id)
    return [
        RoleOut(
            id=str(r.id),
            name=r.name,
            color=r.color.value,
            position=r.position,
            managed=r.managed,
        )
        for r in sorted(guild.roles, key=lambda r: r.position, reverse=True)
        if not r.is_default()  # skip @everyone
    ]


@router.get("/{guild_id}/channels", response_model=list[ChannelOut])
async def list_channels(guild_id: int, bot: BotDep) -> list[ChannelOut]:
    guild = _require_guild(bot, guild_id)
    out: list[ChannelOut] = []
    for ch in guild.channels:
        out.append(
            ChannelOut(
                id=str(ch.id),
                name=ch.name,
                type=ch.type.name,
                category_id=str(ch.category_id) if ch.category_id else None,
                position=ch.position,
            )
        )
    return out
