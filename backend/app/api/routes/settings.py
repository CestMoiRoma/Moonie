"""Per-guild configuration: welcome/goodbye, autoroles, log category."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.services.guild_config import get_or_create_guild_config

router = APIRouter(prefix="/settings", tags=["settings"])


class GuildConfigOut(BaseModel):
    guild_id: str
    welcome_channel_id: str | None = None
    welcome_message: str | None = None
    goodbye_channel_id: str | None = None
    goodbye_message: str | None = None
    autorole_ids: list[str] = Field(default_factory=list)
    log_category_id: str | None = None


class GuildConfigUpdate(BaseModel):
    welcome_channel_id: int | None = None
    welcome_message: str | None = None
    goodbye_channel_id: int | None = None
    goodbye_message: str | None = None
    autorole_ids: list[int] | None = None
    log_category_id: int | None = None


def _to_out(cfg) -> GuildConfigOut:
    return GuildConfigOut(
        guild_id=str(cfg.guild_id),
        welcome_channel_id=str(cfg.welcome_channel_id) if cfg.welcome_channel_id else None,
        welcome_message=cfg.welcome_message,
        goodbye_channel_id=str(cfg.goodbye_channel_id) if cfg.goodbye_channel_id else None,
        goodbye_message=cfg.goodbye_message,
        autorole_ids=[str(r) for r in (cfg.autorole_ids or [])],
        log_category_id=str(cfg.log_category_id) if cfg.log_category_id else None,
    )


@router.get("/{guild_id}", response_model=GuildConfigOut)
async def get_config(guild_id: int, session: SessionDep) -> GuildConfigOut:
    cfg = await get_or_create_guild_config(session, guild_id)
    await session.commit()
    return _to_out(cfg)


@router.put("/{guild_id}", response_model=GuildConfigOut)
async def update_config(
    guild_id: int, payload: GuildConfigUpdate, session: SessionDep
) -> GuildConfigOut:
    cfg = await get_or_create_guild_config(session, guild_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(cfg, key, value)
    await session.commit()
    await session.refresh(cfg)
    return _to_out(cfg)
