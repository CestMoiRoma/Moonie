"""Role management actions from the dashboard (e.g. role_add)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import BotDep
from app.services.roles import RoleError, add_aesthetic_role

router = APIRouter(prefix="/roles", tags=["roles"])


class RoleAddRequest(BaseModel):
    member_id: int
    role_name: str


class RoleAddResponse(BaseModel):
    role_id: str
    role_name: str
    created: bool
    already_had: bool
    message: str


@router.post("/{guild_id}/add", response_model=RoleAddResponse)
async def role_add(guild_id: int, payload: RoleAddRequest, bot: BotDep) -> RoleAddResponse:
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guild not found.")

    member = guild.get_member(payload.member_id)
    if member is None:
        try:
            member = await guild.fetch_member(payload.member_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found.") from exc

    try:
        result = await add_aesthetic_role(guild, member, payload.role_name)
    except RoleError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    if result.already_had:
        msg = f"{member} already has the {result.role.name} role."
    elif result.created:
        msg = f"Created and assigned {result.role.name} to {member}."
    else:
        msg = f"Assigned {result.role.name} to {member}."

    return RoleAddResponse(
        role_id=str(result.role.id),
        role_name=result.role.name,
        created=result.created,
        already_had=result.already_had,
        message=msg,
    )
