"""Apply permission overwrites across many channels at once.

A curated set of common channel permissions is exposed to the dashboard; each can
be set to allow (true), deny (false), or inherit (null = leave at server/category
default). Overwrites are applied per channel for a single target role or member.
"""

from __future__ import annotations

from dataclasses import dataclass

import discord

# Curated, dashboard-friendly subset of discord permission flags.
SUPPORTED_PERMISSIONS = [
    "view_channel",
    "send_messages",
    "send_messages_in_threads",
    "create_public_threads",
    "read_message_history",
    "add_reactions",
    "attach_files",
    "embed_links",
    "mention_everyone",
    "manage_messages",
    "manage_channels",
    "connect",
    "speak",
    "stream",
]

_VALID_FLAGS = set(discord.Permissions.VALID_FLAGS)


class BulkPermissionError(Exception):
    """Raised when a bulk permission application can't proceed."""


@dataclass
class ChannelResult:
    channel_id: int
    channel_name: str
    ok: bool
    error: str | None = None


def _build_overwrite(overwrites: dict[str, bool | None]) -> discord.PermissionOverwrite:
    overwrite = discord.PermissionOverwrite()
    for name, value in overwrites.items():
        if value is None:
            continue  # inherit
        if name not in _VALID_FLAGS:
            raise BulkPermissionError(f"Unknown permission: {name}")
        setattr(overwrite, name, value)
    return overwrite


def resolve_target(
    guild: discord.Guild, target_type: str, target_id: int
) -> discord.Role | discord.Member:
    if target_type == "role":
        role = guild.get_role(target_id)
        if role is None:
            raise BulkPermissionError("Target role not found.")
        return role
    if target_type == "member":
        member = guild.get_member(target_id)
        if member is None:
            raise BulkPermissionError("Target member not found.")
        return member
    raise BulkPermissionError("target_type must be 'role' or 'member'.")


async def apply_overwrites(
    guild: discord.Guild,
    target_type: str,
    target_id: int,
    channel_ids: list[int],
    overwrites: dict[str, bool | None],
    *,
    reason: str = "Bulk permission update (Moonie)",
) -> list[ChannelResult]:
    target = resolve_target(guild, target_type, target_id)
    overwrite = _build_overwrite(overwrites)

    results: list[ChannelResult] = []
    for channel_id in channel_ids:
        channel = guild.get_channel(channel_id)
        if channel is None:
            results.append(ChannelResult(channel_id, str(channel_id), False, "Channel not found"))
            continue
        try:
            await channel.set_permissions(target, overwrite=overwrite, reason=reason)
            results.append(ChannelResult(channel_id, channel.name, True))
        except discord.Forbidden:
            results.append(
                ChannelResult(channel_id, channel.name, False, "Missing permissions")
            )
        except discord.HTTPException as exc:
            results.append(ChannelResult(channel_id, channel.name, False, str(exc)))
    return results
