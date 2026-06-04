"""Per-user 'ticket-style' logging helpers.

A flagged user gets a dedicated text channel created under the guild's configured
log category; the user_logging cog mirrors their messages into it.
"""

from __future__ import annotations

import re

import discord


class UserLoggingError(Exception):
    """Raised when a per-user log channel can't be created."""


def _channel_name(user: discord.abc.User) -> str:
    base = re.sub(r"[^a-z0-9-]+", "-", user.name.lower()).strip("-") or "user"
    return f"log-{base}-{user.id}"[:100]


async def create_log_channel(
    guild: discord.Guild,
    user: discord.abc.User,
    category_id: int,
) -> discord.TextChannel:
    category = guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        raise UserLoggingError("Configured log category not found. Set one in Settings.")

    # Private by default: hide from @everyone; the category's staff overwrites apply.
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }
    try:
        channel = await guild.create_text_channel(
            name=_channel_name(user),
            category=category,
            overwrites=overwrites,
            reason=f"Per-user logging for {user} ({user.id})",
            topic=f"Activity log for {user} ({user.id})",
        )
    except discord.Forbidden as exc:
        raise UserLoggingError("Missing permission to create channels.") from exc
    return channel
