"""Bulk channel permission manager.

The dashboard resolves which channels to target (explicit list, a category's
children, or a Group's channels) and posts the channel ids here; the bot applies
the overwrite to each for a single role or member.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import BotDep
from app.services.bulk_permissions import (
    SUPPORTED_PERMISSIONS,
    BulkPermissionError,
    apply_overwrites,
)

router = APIRouter(prefix="/bulk-permissions", tags=["bulk-permissions"])


class BulkApplyRequest(BaseModel):
    target_type: str = Field(..., pattern="^(role|member)$")
    target_id: int
    channel_ids: list[int]
    # perm name -> true (allow) / false (deny) / null (inherit)
    overwrites: dict[str, bool | None] = Field(default_factory=dict)


class ChannelResultOut(BaseModel):
    channel_id: str
    channel_name: str
    ok: bool
    error: str | None = None


class BulkApplyResponse(BaseModel):
    applied: int
    failed: int
    results: list[ChannelResultOut]


@router.get("/permissions", response_model=list[str])
async def supported_permissions() -> list[str]:
    """The curated set of permissions the dashboard can toggle."""
    return SUPPORTED_PERMISSIONS


@router.post("/{guild_id}/apply", response_model=BulkApplyResponse)
async def apply(guild_id: int, payload: BulkApplyRequest, bot: BotDep) -> BulkApplyResponse:
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guild not found.")
    if not payload.channel_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No channels selected.")

    try:
        results = await apply_overwrites(
            guild,
            payload.target_type,
            payload.target_id,
            payload.channel_ids,
            payload.overwrites,
        )
    except BulkPermissionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    out = [
        ChannelResultOut(
            channel_id=str(r.channel_id),
            channel_name=r.channel_name,
            ok=r.ok,
            error=r.error,
        )
        for r in results
    ]
    return BulkApplyResponse(
        applied=sum(1 for r in results if r.ok),
        failed=sum(1 for r in results if not r.ok),
        results=out,
    )
