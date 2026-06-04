"""Dashboard management of external API keys.

The plaintext key is returned exactly once (at creation); only its hash is stored.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import SessionDep
from app.db.models import ApiKey
from app.external.security import (
    SCOPES,
    generate_key,
    hash_key,
    key_prefix,
    valid_scopes,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: list[str]
    guild_id: str | None
    enabled: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(..., max_length=100)
    scopes: list[str] = Field(default_factory=list)
    guild_id: int | None = None


class ApiKeyCreated(ApiKeyOut):
    key: str  # plaintext — shown once


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    scopes: list[str] | None = None
    guild_id: int | None = None
    enabled: bool | None = None


def _to_out(k: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=k.id,
        name=k.name,
        key_prefix=k.key_prefix,
        scopes=k.scopes or [],
        guild_id=str(k.guild_id) if k.guild_id else None,
        enabled=k.enabled,
        last_used_at=k.last_used_at,
        created_at=k.created_at,
    )


async def _get(session, key_id: int) -> ApiKey:
    k = await session.get(ApiKey, key_id)
    if k is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found.")
    return k


@router.get("/scopes", response_model=list[str])
async def available_scopes() -> list[str]:
    return SCOPES


@router.get("", response_model=list[ApiKeyOut])
async def list_keys(session: SessionDep) -> list[ApiKeyOut]:
    rows = await session.scalars(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return [_to_out(k) for k in rows]


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_key(payload: ApiKeyCreate, session: SessionDep) -> ApiKeyCreated:
    if not payload.scopes or not valid_scopes(payload.scopes):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"scopes must be a non-empty subset of {SCOPES}"
        )
    plaintext = generate_key()
    k = ApiKey(
        name=payload.name,
        key_prefix=key_prefix(plaintext),
        key_hash=hash_key(plaintext),
        scopes=payload.scopes,
        guild_id=payload.guild_id,
        enabled=True,
    )
    session.add(k)
    await session.commit()
    await session.refresh(k)
    return ApiKeyCreated(**_to_out(k).model_dump(), key=plaintext)


@router.patch("/{key_id}", response_model=ApiKeyOut)
async def update_key(key_id: int, payload: ApiKeyUpdate, session: SessionDep) -> ApiKeyOut:
    k = await _get(session, key_id)
    data = payload.model_dump(exclude_unset=True)
    if "scopes" in data:
        if not data["scopes"] or not valid_scopes(data["scopes"]):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"scopes must be a non-empty subset of {SCOPES}"
            )
    for field, value in data.items():
        setattr(k, field, value)
    await session.commit()
    await session.refresh(k)
    return _to_out(k)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(key_id: int, session: SessionDep) -> None:
    k = await _get(session, key_id)
    await session.delete(k)
    await session.commit()
