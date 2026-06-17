"""Role helpers, including the ported `role_add` behaviour.

Ported from the user's standalone bot: assign an aesthetic (zero-permission) role
to a member, creating it if it doesn't exist. The create-if-missing + graceful
`Forbidden` handling here is reused by the bulk-permission and reaction-role features.
"""

from __future__ import annotations

from dataclasses import dataclass

import discord


class RoleError(Exception):
    """Raised when a role operation can't be completed."""


@dataclass
class RoleAddResult:
    role: discord.Role
    created: bool
    already_had: bool


def find_role(guild: discord.Guild, role_name: str) -> discord.Role | None:
    """Case-sensitive match first, then case-insensitive fallback."""
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        role = discord.utils.find(
            lambda r: r.name.lower() == role_name.lower(), guild.roles
        )
    return role


async def add_aesthetic_role(
    guild: discord.Guild,
    member: discord.Member,
    role_name: str,
    *,
    actor: str = "Moonie dashboard",
) -> RoleAddResult:
    """Add (creating if needed) a zero-permission role to a member."""
    role_name = role_name.strip().strip('"').strip("'").strip()
    if not role_name:
        raise RoleError("Role name cannot be empty.")

    role = find_role(guild, role_name)
    created = False

    if role is None:
        try:
            role = await guild.create_role(
                name=role_name,
                permissions=discord.Permissions.none(),
                reason=f"Aesthetic role created by {actor}",
            )
            created = True
        except discord.Forbidden as exc:
            raise RoleError(
                "Missing **Manage Roles** permission to create roles."
            ) from exc

    if role in member.roles:
        return RoleAddResult(role=role, created=created, already_had=True)

    try:
        await member.add_roles(role, reason=f"Added by {actor}")
    except discord.Forbidden as exc:
        raise RoleError(
            "Missing **Manage Roles** permission, or my role sits below the target "
            "role in the hierarchy."
        ) from exc

    return RoleAddResult(role=role, created=created, already_had=False)
