"""Role management slash commands (ported role_add)."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from app.services.roles import RoleError, add_aesthetic_role


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="role_add",
        description="Give a member an aesthetic role (created automatically if it doesn't exist).",
    )
    @app_commands.guild_only()
    @app_commands.describe(member="Member to receive the role", role_name="Name of the role")
    async def role_add(
        self, interaction: discord.Interaction, member: discord.Member, role_name: str
    ) -> None:
        assert interaction.guild is not None
        try:
            result = await add_aesthetic_role(
                interaction.guild, member, role_name, actor=str(interaction.user)
            )
        except RoleError as exc:
            await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
            return

        if result.already_had:
            msg = f"ℹ️ {member.mention} already has the **{result.role.name}** role."
        elif result.created:
            msg = f"✨ Created and assigned **{result.role.name}** to {member.mention}."
        else:
            msg = f"✅ Assigned **{result.role.name}** to {member.mention}."
        await interaction.response.send_message(msg)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roles(bot))
