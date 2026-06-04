"""MoonieBot — the discord.py client, intents, and cog loader."""

from __future__ import annotations

import logging
import pkgutil

import discord
from discord.ext import commands

from app.config import get_settings

log = logging.getLogger("moonie.bot")


def build_intents() -> discord.Intents:
    """Intents required by Moonie's features.

    `members` and `message_content` are privileged — enable them in the Discord
    Developer Portal (Bot → Privileged Gateway Intents).
    """
    intents = discord.Intents.default()
    intents.members = True          # member join/leave, role assignment
    intents.message_content = True  # automod + per-user logging
    intents.reactions = True        # reaction roles
    return intents


class MoonieBot(commands.Bot):
    """The bot. Loads every cog under app.bot.cogs on startup."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            command_prefix=settings.prefix,
            intents=build_intents(),
            help_command=None,
        )
        self.settings = settings

    async def setup_hook(self) -> None:
        await self._load_cogs()

        # Sync slash commands. Scoped to GUILD_ID syncs instantly; otherwise global.
        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Slash commands synced to guild %s", self.settings.guild_id)
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally (may take up to ~1h to appear)")

    async def _load_cogs(self) -> None:
        import app.bot.cogs as cogs_pkg

        for module in pkgutil.iter_modules(cogs_pkg.__path__):
            if module.name.startswith("_"):
                continue
            ext = f"app.bot.cogs.{module.name}"
            try:
                await self.load_extension(ext)
                log.info("Loaded cog: %s", ext)
            except Exception:  # noqa: BLE001 — one bad cog shouldn't kill the bot
                log.exception("Failed to load cog: %s", ext)

    async def on_ready(self) -> None:
        guilds = ", ".join(g.name for g in self.guilds) or "—"
        log.info("Logged in as %s (id: %s)", self.user, self.user and self.user.id)
        log.info("Serving guilds: %s", guilds)
