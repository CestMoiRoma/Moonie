"""Auto-ban: ban members on join if they're in the global ban database."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from app.db.base import SessionFactory
from app.db.models import GlobalBan

log = logging.getLogger("moonie.autoban")


class AutoBan(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        async with SessionFactory() as session:
            ban = await session.get(GlobalBan, member.id)
        if ban is None:
            return
        try:
            await member.ban(
                reason=f"Auto-ban (global banlist): {ban.reason or 'no reason'}",
                delete_message_days=0,
            )
            log.info("Auto-banned %s from guild %s", member.id, member.guild.id)
        except discord.Forbidden:
            log.warning("Missing permission to auto-ban %s in guild %s", member.id, member.guild.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoBan(bot))
