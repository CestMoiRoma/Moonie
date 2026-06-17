"""Moderation slash commands → audit log."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from app.db.base import SessionFactory
from app.services.moderation import ModerationError, apply_action, record_action


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _do(
        self,
        interaction: discord.Interaction,
        action: str,
        member: discord.Member | discord.User,
        reason: str | None,
        *,
        duration_minutes: int | None = None,
    ) -> None:
        assert interaction.guild is not None
        try:
            tag = await apply_action(
                interaction.guild,
                action,
                member.id,
                reason=reason,
                duration_minutes=duration_minutes,
            )
        except ModerationError as exc:
            await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
            return

        async with SessionFactory() as session:
            await record_action(
                session,
                guild_id=interaction.guild.id,
                action=action,
                target_id=member.id,
                target_tag=tag,
                moderator_id=interaction.user.id,
                moderator_tag=str(interaction.user),
                reason=reason,
            )
            await session.commit()

        await interaction.response.send_message(
            f"✅ **{action}** applied to {tag}." + (f" Reason: {reason}" if reason else "")
        )

    @app_commands.command(description="Kick a member.")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to kick", reason="Reason (optional)")
    async def kick(
        self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None
    ) -> None:
        await self._do(interaction, "kick", member, reason)

    @app_commands.command(description="Ban a member.")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to ban", reason="Reason (optional)")
    async def ban(
        self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None
    ) -> None:
        await self._do(interaction, "ban", member, reason)

    @app_commands.command(description="Unban a user by id.")
    @app_commands.guild_only()
    @app_commands.describe(user_id="The user id to unban", reason="Reason (optional)")
    async def unban(
        self, interaction: discord.Interaction, user_id: str, reason: str | None = None
    ) -> None:
        try:
            uid = int(user_id)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user id.", ephemeral=True)
            return
        await self._do(interaction, "unban", discord.Object(id=uid), reason)  # type: ignore[arg-type]

    @app_commands.command(description="Timeout (mute) a member for N minutes.")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to mute", minutes="Duration in minutes", reason="Reason")
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: int = 60,
        reason: str | None = None,
    ) -> None:
        await self._do(interaction, "mute", member, reason, duration_minutes=minutes)

    @app_commands.command(description="Remove a member's timeout.")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to unmute", reason="Reason (optional)")
    async def unmute(
        self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None
    ) -> None:
        await self._do(interaction, "unmute", member, reason)

    @app_commands.command(description="Warn a member (DMs them and logs it).")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to warn", reason="Reason")
    async def warn(
        self, interaction: discord.Interaction, member: discord.Member, reason: str
    ) -> None:
        await self._do(interaction, "warn", member, reason)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
