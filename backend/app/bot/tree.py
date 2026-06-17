"""Custom command tree that enforces per-command permissions."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from app.db.base import SessionFactory
from app.services.permissions import can_run

log = logging.getLogger("moonie.tree")


class MoonieCommandTree(app_commands.CommandTree):
    """Applies the command-permission system to every slash command."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only gate guild commands invoked by members; allow everything else.
        if interaction.guild is None or interaction.command is None:
            return True
        if not isinstance(interaction.user, discord.Member):
            return True

        command = interaction.command.qualified_name
        async with SessionFactory() as session:
            allowed = await can_run(session, interaction.guild.id, command, interaction.user)

        if not allowed:
            await interaction.response.send_message(
                "⛔ You don't have permission to use this command.", ephemeral=True
            )
        return allowed

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        # We already replied for permission failures; swallow them quietly.
        if isinstance(error, app_commands.CheckFailure):
            return
        log.exception("Unhandled app command error", exc_info=error)
        if not interaction.response.is_done():
            try:
                await interaction.response.send_message(
                    "❌ Something went wrong running that command.", ephemeral=True
                )
            except discord.HTTPException:
                pass
