"""Dependencies for the external API: key auth, scopes, rate limiting, resolution."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated

import discord
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.config import get_settings
from app.db.base import SessionFactory
from app.db.models import ApiKey
from app.external.security import hash_key

if TYPE_CHECKING:
    from app.bot.client import MoonieBot

_bearer = HTTPBearer(auto_error=False, description="API key as a Bearer token.")

# In-memory state (single-process self-host): last-used throttle + rate-limit window.
_last_used_at: dict[int, float] = {}
_rate_window: dict[int, tuple[int, int]] = {}


def get_external_bot(request: Request) -> "MoonieBot":
    bot = getattr(request.app.state, "bot", None)
    if bot is None or not bot.is_ready():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Bot is not connected.")
    return bot


ExternalBotDep = Annotated["MoonieBot", Depends(get_external_bot)]


async def _touch_last_used(session, key: ApiKey) -> None:
    """Record last-used at most once per minute to avoid a write per request."""
    now = time.monotonic()
    if now - _last_used_at.get(key.id, 0.0) < 60:
        return
    _last_used_at[key.id] = now
    key.last_used_at = datetime.now(timezone.utc)
    await session.commit()


async def get_api_key(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> ApiKey:
    token = creds.credentials if creds else request.headers.get("X-API-Key")
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Missing API key (use 'Authorization: Bearer <key>' or 'X-API-Key').",
        )
    digest = hash_key(token)
    async with SessionFactory() as session:
        key = await session.scalar(select(ApiKey).where(ApiKey.key_hash == digest))
        if key is None or not key.enabled:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or disabled API key.")
        await _touch_last_used(session, key)
    return key


def _enforce_rate_limit(key_id: int) -> None:
    limit = get_settings().external_rate_limit_per_min
    if limit <= 0:
        return
    now = time.time()
    bucket = int(now // 60)
    window_bucket, count = _rate_window.get(key_id, (bucket, 0))
    if window_bucket != bucket:
        window_bucket, count = bucket, 0
    count += 1
    _rate_window[key_id] = (window_bucket, count)
    if count > limit:
        retry_after = 60 - int(now % 60)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Rate limit exceeded.",
            headers={"Retry-After": str(retry_after)},
        )


def require_scope(scope: str):
    """Dependency: authenticate, enforce the rate limit, and require `scope`."""

    async def dependency(api_key: Annotated[ApiKey, Depends(get_api_key)]) -> ApiKey:
        _enforce_rate_limit(api_key.id)
        if scope not in (api_key.scopes or []):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Key is missing the required scope: {scope}"
            )
        return api_key

    return dependency


def enforce_guild(api_key: ApiKey, guild_id: int) -> None:
    if api_key.guild_id is not None and api_key.guild_id != guild_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Key is restricted to a different guild.")


def resolve_channel(bot, api_key: ApiKey, channel_id: int) -> discord.abc.Messageable:
    channel = bot.get_channel(channel_id)
    guild = getattr(channel, "guild", None)
    if not isinstance(channel, discord.abc.Messageable) or guild is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found or not text-based.")
    enforce_guild(api_key, guild.id)
    return channel
