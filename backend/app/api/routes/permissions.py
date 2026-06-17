"""Per-command permission management."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import BotDep, SessionDep
from app.db.models import CommandPermission
from app.services.permissions import get_permission

router = APIRouter(prefix="/permissions", tags=["permissions"])


class CommandPermissionOut(BaseModel):
    command: str
    allowed_role_ids: list[str] = Field(default_factory=list)
    allowed_user_ids: list[str] = Field(default_factory=list)


class CommandPermissionUpdate(BaseModel):
    allowed_role_ids: list[int] = Field(default_factory=list)
    allowed_user_ids: list[int] = Field(default_factory=list)


def _to_out(command: str, rule: CommandPermission | None) -> CommandPermissionOut:
    if rule is None:
        return CommandPermissionOut(command=command)
    return CommandPermissionOut(
        command=command,
        allowed_role_ids=[str(r) for r in (rule.allowed_role_ids or [])],
        allowed_user_ids=[str(u) for u in (rule.allowed_user_ids or [])],
    )


@router.get("/commands", response_model=list[str])
async def list_commands(bot: BotDep) -> list[str]:
    """All registered slash-command names (for the dashboard editor)."""
    return sorted(c.qualified_name for c in bot.tree.get_commands())


@router.get("/{guild_id}", response_model=list[CommandPermissionOut])
async def list_permissions(guild_id: int, session: SessionDep) -> list[CommandPermissionOut]:
    rows = await session.scalars(
        select(CommandPermission).where(CommandPermission.guild_id == guild_id)
    )
    return [_to_out(r.command, r) for r in rows]


@router.put("/{guild_id}/{command}", response_model=CommandPermissionOut)
async def set_permission(
    guild_id: int,
    command: str,
    payload: CommandPermissionUpdate,
    session: SessionDep,
) -> CommandPermissionOut:
    rule = await get_permission(session, guild_id, command)

    # Empty rule == "open"; remove any existing row to keep the table tidy.
    if not payload.allowed_role_ids and not payload.allowed_user_ids:
        if rule is not None:
            await session.delete(rule)
            await session.commit()
        return _to_out(command, None)

    if rule is None:
        rule = CommandPermission(guild_id=guild_id, command=command)
        session.add(rule)
    rule.allowed_role_ids = payload.allowed_role_ids
    rule.allowed_user_ids = payload.allowed_user_ids
    await session.commit()
    await session.refresh(rule)
    return _to_out(command, rule)
