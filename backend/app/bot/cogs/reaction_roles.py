"""Reaction roles — emoji-mode listeners (button mode is handled by RoleButton)."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import SessionFactory
from app.db.models import ReactionRoleEntry, ReactionRoleMessage

log = logging.getLogger("moonie.reaction_roles")


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _entry_for(
        self, message_id: int, payload_emoji: discord.PartialEmoji
    ) -> ReactionRoleEntry | None:
        emoji_str = str(payload_emoji)
        async with SessionFactory() as session:
            rr = await session.scalar(
                select(ReactionRoleMessage)
                .where(
                    ReactionRoleMessage.message_id == message_id,
                    ReactionRoleMessage.mode == "emoji",
                )
                .options(selectinload(ReactionRoleMessage.entries))
            )
            if rr is None:
                return None
            for entry in rr.entries:
                if entry.emoji in (emoji_str, payload_emoji.name):
                    return entry
        return None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or payload.member is None or payload.member.bot:
            return
        entry = await self._entry_for(payload.message_id, payload.emoji)
        if entry is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        role = guild and guild.get_role(entry.role_id)
        if role is None:
            return
        try:
            await payload.member.add_roles(role, reason="Reaction role")
        except discord.Forbidden:
            log.warning("Missing permission to add role %s in guild %s", role.id, guild.id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None:
            return
        entry = await self._entry_for(payload.message_id, payload.emoji)
        if entry is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(entry.role_id)
        if member is None or member.bot or role is None:
            return
        try:
            await member.remove_roles(role, reason="Reaction role removed")
        except discord.Forbidden:
            log.warning("Missing permission to remove role %s in guild %s", role.id, guild.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReactionRoles(bot))
