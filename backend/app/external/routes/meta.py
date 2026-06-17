"""External meta endpoint: verify the authenticated key."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.models import ApiKey
from app.external.deps import get_api_key

router = APIRouter(tags=["meta"])


class KeyInfo(BaseModel):
    name: str
    scopes: list[str]
    guild_id: str | None


@router.get("/me", response_model=KeyInfo)
async def me(key: Annotated[ApiKey, Depends(get_api_key)]) -> KeyInfo:
    return KeyInfo(
        name=key.name,
        scopes=key.scopes or [],
        guild_id=str(key.guild_id) if key.guild_id else None,
    )
