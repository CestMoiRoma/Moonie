"""Reaction-role helpers: render the message and publish it to a channel."""

from __future__ import annotations

import discord

from app.bot.reaction_role_views import build_button_view
from app.db.models import ReactionRoleMessage


class ReactionRoleError(Exception):
    """Raised when a reaction-role message can't be published."""


def build_embed(rr: ReactionRoleMessage) -> discord.Embed:
    embed = discord.Embed(
        title=rr.title or "Roles",
        description=rr.description or _default_description(rr),
        color=discord.Color.blurple(),
    )
    return embed


def _default_description(rr: ReactionRoleMessage) -> str:
    lines: list[str] = []
    for entry in rr.entries:
        if rr.mode == "emoji" and entry.emoji:
            lines.append(f"{entry.emoji} — <@&{entry.role_id}>")
        else:
            label = entry.label or f"<@&{entry.role_id}>"
            lines.append(f"• {label}")
    return "\n".join(lines) or "No roles configured yet."


async def publish(channel: discord.abc.Messageable, rr: ReactionRoleMessage) -> int:
    """Send (or re-send) the reaction-role message; return the new message id."""
    embed = build_embed(rr)

    if rr.mode == "button":
        view = build_button_view(rr.entries)
        message = await channel.send(embed=embed, view=view)
    else:
        message = await channel.send(embed=embed)
        for entry in rr.entries:
            if not entry.emoji:
                continue
            try:
                await message.add_reaction(discord.PartialEmoji.from_str(entry.emoji))
            except discord.HTTPException as exc:
                raise ReactionRoleError(
                    f"Could not add reaction {entry.emoji!r}: {exc}"
                ) from exc

    return message.id
