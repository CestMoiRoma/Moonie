"""Moderation primitives shared by the bot cog and the API route.

`apply_action` performs the Discord side-effect; `record_action` writes the audit
row. Callers do both (the cog from a slash command, the API from the dashboard).
"""

from __future__ import annotations

from datetime import timedelta

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModAction

VALID_ACTIONS = {"kick", "ban", "unban", "warn", "mute", "unmute"}


class ModerationError(Exception):
    """Raised when a moderation action cannot be performed."""


async def apply_action(
    guild: discord.Guild,
    action: str,
    target_id: int,
    *,
    reason: str | None = None,
    duration_minutes: int | None = None,
) -> str:
    """Perform the Discord action. Returns the target's tag (best effort)."""
    if action not in VALID_ACTIONS:
        raise ModerationError(f"Unknown action: {action}")

    audit_reason = reason or "No reason provided"

    try:
        if action == "ban":
            user = discord.Object(id=target_id)
            await guild.ban(user, reason=audit_reason, delete_message_days=0)
            return await _tag_for(guild, target_id)

        if action == "unban":
            await guild.unban(discord.Object(id=target_id), reason=audit_reason)
            return await _tag_for(guild, target_id)

        member = guild.get_member(target_id) or await _fetch_member(guild, target_id)
        if member is None:
            raise ModerationError("Member is not in this guild.")
        tag = str(member)

        if action == "kick":
            await member.kick(reason=audit_reason)
        elif action == "mute":
            until = discord.utils.utcnow() + timedelta(minutes=duration_minutes or 60)
            await member.timeout(until, reason=audit_reason)
        elif action == "unmute":
            await member.timeout(None, reason=audit_reason)
        elif action == "warn":
            # Warn is a logged action; try to DM the user but don't fail if blocked.
            try:
                await member.send(
                    f"⚠️ You were warned in **{guild.name}**: {audit_reason}"
                )
            except discord.HTTPException:
                pass
        return tag
    except discord.Forbidden as exc:
        raise ModerationError(
            "Missing permissions or role hierarchy too low for this action."
        ) from exc
    except discord.HTTPException as exc:
        raise ModerationError(f"Discord API error: {exc}") from exc


async def record_action(
    session: AsyncSession,
    *,
    guild_id: int,
    action: str,
    target_id: int,
    target_tag: str | None,
    moderator_id: int,
    moderator_tag: str | None,
    reason: str | None,
) -> ModAction:
    entry = ModAction(
        guild_id=guild_id,
        action=action,
        target_id=target_id,
        target_tag=target_tag,
        moderator_id=moderator_id,
        moderator_tag=moderator_tag,
        reason=reason,
    )
    session.add(entry)
    await session.flush()
    return entry


async def _fetch_member(guild: discord.Guild, user_id: int) -> discord.Member | None:
    try:
        return await guild.fetch_member(user_id)
    except discord.HTTPException:
        return None


async def _tag_for(guild: discord.Guild, user_id: int) -> str:
    try:
        user = await guild._state.client.fetch_user(user_id)
        return str(user)
    except discord.HTTPException:
        return str(user_id)
