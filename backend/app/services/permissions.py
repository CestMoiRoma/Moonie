"""Per-command access control.

Default policy: the guild owner and members with the `administrator` permission
always pass. For a command with an explicit `command_permissions` row, the invoker
must hold one of the allowed roles or be an allowed user. Commands without a row are
open (admins can lock them down from the dashboard).
"""

from __future__ import annotations

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CommandPermission


async def get_permission(
    session: AsyncSession, guild_id: int, command: str
) -> CommandPermission | None:
    return await session.scalar(
        select(CommandPermission).where(
            CommandPermission.guild_id == guild_id,
            CommandPermission.command == command,
        )
    )


async def can_run(
    session: AsyncSession, guild_id: int, command: str, member: discord.Member
) -> bool:
    # Owner / administrators always bypass.
    if member.guild and member.guild.owner_id == member.id:
        return True
    perms = getattr(member, "guild_permissions", None)
    if perms is not None and perms.administrator:
        return True

    rule = await get_permission(session, guild_id, command)
    if rule is None:
        return True  # open by default

    if member.id in (rule.allowed_user_ids or []):
        return True
    member_role_ids = {r.id for r in getattr(member, "roles", [])}
    if member_role_ids & set(rule.allowed_role_ids or []):
        return True
    return False
