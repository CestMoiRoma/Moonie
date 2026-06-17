"""Shared accessor for per-guild configuration.

Used by both the API routes and the bot cogs so the get-or-create logic lives in
exactly one place.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GuildConfig


async def get_or_create_guild_config(session: AsyncSession, guild_id: int) -> GuildConfig:
    config = await session.get(GuildConfig, guild_id)
    if config is None:
        config = GuildConfig(guild_id=guild_id)
        session.add(config)
        await session.flush()
    return config
