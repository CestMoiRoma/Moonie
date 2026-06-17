"""Persistent button for button-mode reaction roles.

Uses a DynamicItem so buttons keep working across restarts without storing/rebuilding
per-message views — the role id is encoded in the custom_id and matched by template.
"""

from __future__ import annotations

import discord


class RoleButton(discord.ui.DynamicItem[discord.ui.Button], template=r"rr:(?P<role_id>\d+)"):
    def __init__(self, role_id: int, label: str | None = None, emoji: str | None = None) -> None:
        self.role_id = role_id
        super().__init__(
            discord.ui.Button(
                label=(label or "Role")[:80],
                emoji=discord.PartialEmoji.from_str(emoji) if emoji else None,
                style=discord.ButtonStyle.secondary,
                custom_id=f"rr:{role_id}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):  # noqa: ANN001
        return cls(int(match["role_id"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            return
        role = guild.get_role(self.role_id)
        if role is None:
            await interaction.response.send_message("That role no longer exists.", ephemeral=True)
            return
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Reaction role (button)")
                await interaction.response.send_message(f"Removed **{role.name}**.", ephemeral=True)
            else:
                await member.add_roles(role, reason="Reaction role (button)")
                await interaction.response.send_message(f"Added **{role.name}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I can't manage that role — check my permissions and role position.",
                ephemeral=True,
            )


def build_button_view(entries) -> discord.ui.View:
    """Build a persistent View of role buttons from reaction-role entries."""
    view = discord.ui.View(timeout=None)
    for entry in entries:
        view.add_item(RoleButton(entry.role_id, label=entry.label, emoji=entry.emoji))
    return view
