"""Admin-defined text commands (prefix-triggered).

A per-guild cache of name -> (response, embed_id) avoids a DB hit on every message;
the API invalidates a guild's cache when commands change.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands
from sqlalchemy import select

from app.db.base import SessionFactory
from app.db.models import CustomCommand, Embed
from app.services.embeds import build_embed

log = logging.getLogger("moonie.custom_commands")


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._cache: dict[int, dict[str, tuple[str, int | None]]] = {}
        self._loaded: set[int] = set()

    async def _load(self, guild_id: int) -> None:
        async with SessionFactory() as session:
            rows = await session.scalars(
                select(CustomCommand).where(CustomCommand.guild_id == guild_id)
            )
            self._cache[guild_id] = {c.name.lower(): (c.response, c.embed_id) for c in rows}
        self._loaded.add(guild_id)

    def invalidate(self, guild_id: int) -> None:
        self._loaded.discard(guild_id)
        self._cache.pop(guild_id, None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        prefix = self.bot.command_prefix
        if not isinstance(prefix, str) or not message.content.startswith(prefix):
            return

        name = message.content[len(prefix):].split(maxsplit=1)[0].lower()
        if not name:
            return

        if message.guild.id not in self._loaded:
            await self._load(message.guild.id)
        entry = self._cache.get(message.guild.id, {}).get(name)
        if entry is None:
            return

        response, embed_id = entry
        embed = None
        if embed_id is not None:
            async with SessionFactory() as session:
                model = await session.get(Embed, embed_id)
            if model is not None:
                embed = build_embed(model)

        try:
            await message.channel.send(content=response or None, embed=embed)
        except discord.HTTPException:
            log.warning("Failed to send custom command '%s' in guild %s", name, message.guild.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CustomCommands(bot))
