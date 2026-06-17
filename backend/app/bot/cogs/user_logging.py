"""Mirror flagged users' messages into their dedicated log channel.

A small per-guild cache of {user_id: log_channel_id} avoids a DB hit on every
message; the API invalidates a guild's cache when users are flagged/unflagged.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands
from sqlalchemy import select

from app.db.base import SessionFactory
from app.db.models import FlaggedUser

log = logging.getLogger("moonie.user_logging")


class UserLogging(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._cache: dict[int, dict[int, int]] = {}
        self._loaded: set[int] = set()

    async def _load(self, guild_id: int) -> None:
        async with SessionFactory() as session:
            rows = await session.scalars(
                select(FlaggedUser).where(
                    FlaggedUser.guild_id == guild_id, FlaggedUser.active.is_(True)
                )
            )
            self._cache[guild_id] = {
                r.user_id: r.log_channel_id for r in rows if r.log_channel_id
            }
        self._loaded.add(guild_id)

    def invalidate(self, guild_id: int) -> None:
        """Called by the API after flagging/unflagging so the next message reloads."""
        self._loaded.discard(guild_id)
        self._cache.pop(guild_id, None)

    async def _channel_for(self, guild_id: int, user_id: int) -> int | None:
        if guild_id not in self._loaded:
            await self._load(guild_id)
        return self._cache.get(guild_id, {}).get(user_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        channel_id = await self._channel_for(message.guild.id, message.author.id)
        if channel_id is None or channel_id == message.channel.id:
            return
        channel = message.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            description=message.content or "*(no text)*",
            color=discord.Color.orange(),
            timestamp=message.created_at,
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Jump", value=f"[link]({message.jump_url})", inline=True)
        if message.attachments:
            embed.add_field(
                name="Attachments",
                value="\n".join(a.url for a in message.attachments)[:1024],
                inline=False,
            )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            log.warning("Failed to mirror message into log channel %s", channel_id)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        channel_id = await self._channel_for(message.guild.id, message.author.id)
        if channel_id is None:
            return
        channel = message.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        embed = discord.Embed(
            description=f"🗑️ **Deleted message**\n{message.content or '*(no text)*'}",
            color=discord.Color.red(),
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserLogging(bot))
