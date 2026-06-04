"""Basic automod: delete messages matching word / link / regex rules.

Rules are cached per guild (compiled) and the cache is invalidated by the API on
change. A matched message is deleted and recorded in the moderation audit log;
'warn' rules additionally drop a short auto-deleting notice in the channel.
"""

from __future__ import annotations

import logging
import re

import discord
from discord.ext import commands
from sqlalchemy import select

from app.db.base import SessionFactory
from app.db.models import AutomodRule
from app.services.moderation import record_action

log = logging.getLogger("moonie.automod")

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


class CompiledRule:
    def __init__(self, rule: AutomodRule) -> None:
        self.name = rule.name
        self.action = rule.action
        self.kind = rule.kind
        self.pattern = rule.pattern
        self._regex: re.Pattern | None = None
        try:
            if rule.kind == "word":
                self._regex = re.compile(rf"\b{re.escape(rule.pattern)}\b", re.IGNORECASE)
            elif rule.kind == "regex":
                self._regex = re.compile(rule.pattern, re.IGNORECASE)
        except re.error:
            log.warning("Invalid automod regex in rule '%s'; disabling it", rule.name)
            self._regex = None

    def matches(self, content: str) -> bool:
        if self.kind == "word":
            return bool(self._regex and self._regex.search(content))
        if self.kind == "regex":
            return bool(self._regex and self._regex.search(content))
        if self.kind == "link":
            urls = _URL_RE.findall(content)
            if not urls:
                return False
            if not self.pattern:
                return True  # any link
            return any(self.pattern.lower() in u.lower() for u in urls)
        return False


class Automod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._cache: dict[int, list[CompiledRule]] = {}
        self._loaded: set[int] = set()

    async def _load(self, guild_id: int) -> None:
        async with SessionFactory() as session:
            rows = await session.scalars(
                select(AutomodRule).where(
                    AutomodRule.guild_id == guild_id, AutomodRule.enabled.is_(True)
                )
            )
            self._cache[guild_id] = [CompiledRule(r) for r in rows]
        self._loaded.add(guild_id)

    def invalidate(self, guild_id: int) -> None:
        self._loaded.discard(guild_id)
        self._cache.pop(guild_id, None)

    async def _rules_for(self, guild_id: int) -> list[CompiledRule]:
        if guild_id not in self._loaded:
            await self._load(guild_id)
        return self._cache.get(guild_id, [])

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or not message.content:
            return
        # Don't moderate members who can manage messages (mods/admins).
        perms = getattr(message.author, "guild_permissions", None)
        if perms is not None and perms.manage_messages:
            return

        for rule in await self._rules_for(message.guild.id):
            if not rule.matches(message.content):
                continue
            try:
                await message.delete()
            except discord.HTTPException:
                return

            async with SessionFactory() as session:
                await record_action(
                    session,
                    guild_id=message.guild.id,
                    action="automod",
                    target_id=message.author.id,
                    target_tag=str(message.author),
                    moderator_id=self.bot.user.id if self.bot.user else 0,
                    moderator_tag="automod",
                    reason=f"Rule: {rule.name}",
                )
                await session.commit()

            if rule.action == "warn":
                try:
                    await message.channel.send(
                        f"{message.author.mention}, your message was removed (automod: {rule.name}).",
                        delete_after=5,
                    )
                except discord.HTTPException:
                    pass
            return  # one rule action per message is enough


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Automod(bot))
