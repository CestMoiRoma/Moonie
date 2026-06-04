"""Welcome/goodbye messages + autoroles on member join/leave."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from app.db.base import SessionFactory
from app.services.guild_config import get_or_create_guild_config
from app.services.templating import (
    DEFAULT_GOODBYE,
    DEFAULT_WELCOME,
    member_context,
    render_message,
)

log = logging.getLogger("moonie.welcome")


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        async with SessionFactory() as session:
            cfg = await get_or_create_guild_config(session, member.guild.id)
            await session.commit()

        # Autoroles
        if cfg.autorole_ids:
            roles = [member.guild.get_role(rid) for rid in cfg.autorole_ids]
            roles = [r for r in roles if r is not None]
            if roles:
                try:
                    await member.add_roles(*roles, reason="Autorole on join")
                except discord.Forbidden:
                    log.warning("Missing permissions to apply autoroles in %s", member.guild.id)

        # Welcome message
        if cfg.welcome_channel_id:
            channel = member.guild.get_channel(cfg.welcome_channel_id)
            if isinstance(channel, discord.TextChannel):
                template = cfg.welcome_message or DEFAULT_WELCOME
                text = render_message(template, member_context(member))
                try:
                    await channel.send(text)
                except discord.HTTPException:
                    log.warning("Failed to send welcome message in %s", member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        async with SessionFactory() as session:
            cfg = await get_or_create_guild_config(session, member.guild.id)
            await session.commit()

        if cfg.goodbye_channel_id:
            channel = member.guild.get_channel(cfg.goodbye_channel_id)
            if isinstance(channel, discord.TextChannel):
                template = cfg.goodbye_message or DEFAULT_GOODBYE
                text = render_message(template, member_context(member, mention=False))
                try:
                    await channel.send(text)
                except discord.HTTPException:
                    log.warning("Failed to send goodbye message in %s", member.guild.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
