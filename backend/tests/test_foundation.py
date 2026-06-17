"""Foundation tests: templating logic + a couple of stateless API endpoints."""

from __future__ import annotations

import httpx
import pytest

from app.bot.cogs.automod import CompiledRule
from app.db.models import ApiKey, AutomodRule
from app.external import security
from app.external.deps import _enforce_rate_limit, enforce_guild
from app.main import app
from app.services.templating import DEFAULT_WELCOME, render_message


def test_render_message_substitutes_tokens():
    out = render_message(
        "Hi {user_mention}, welcome to {server} (#{member_count})",
        {"user_mention": "@Sam", "server": "Guild", "member_count": 7},
    )
    assert out == "Hi @Sam, welcome to Guild (#7)"


def test_default_welcome_renders_without_leftover_tokens():
    ctx = {
        "user": "Sam#1",
        "user_mention": "@Sam",
        "user_name": "Sam",
        "server": "Guild",
        "member_count": 7,
    }
    out = render_message(DEFAULT_WELCOME, ctx)
    assert "{" not in out and "}" not in out


def _rule(kind: str, pattern: str) -> CompiledRule:
    return CompiledRule(AutomodRule(name="r", kind=kind, pattern=pattern, action="delete"))


def test_automod_word_matches_whole_word_only():
    rule = _rule("word", "spam")
    assert rule.matches("this is SPAM here")
    assert not rule.matches("spamming is different")  # word boundary


def test_automod_link_blocks_any_or_specific():
    any_link = _rule("link", "")
    assert any_link.matches("check http://example.com")
    assert not any_link.matches("no links here")

    specific = _rule("link", "discord.gg")
    assert specific.matches("join https://discord.gg/abc")
    assert not specific.matches("visit https://example.com")


def test_automod_regex_and_invalid_regex():
    rule = _rule("regex", r"\d{4,}")
    assert rule.matches("code 12345")
    assert not rule.matches("only 12")

    broken = _rule("regex", "(")  # invalid → disabled, never matches
    assert not broken.matches("anything (")


def test_api_key_generate_hash_roundtrip():
    key = security.generate_key()
    assert key.startswith("mk_")
    assert security.hash_key(key) == security.hash_key(key)  # deterministic
    assert security.hash_key(key) != security.hash_key(security.generate_key())
    assert key.startswith(security.key_prefix(key))


def test_api_key_scope_validation():
    assert security.valid_scopes(["messages:write", "guilds:read"])
    assert not security.valid_scopes(["messages:write", "bogus"])
    assert security.valid_scopes([])  # empty is "valid" subset; create() rejects empties


def test_enforce_guild_restriction():
    from fastapi import HTTPException

    unrestricted = ApiKey(guild_id=None)
    enforce_guild(unrestricted, 123)  # any guild ok

    restricted = ApiKey(guild_id=123)
    enforce_guild(restricted, 123)  # match ok
    with pytest.raises(HTTPException) as exc:
        enforce_guild(restricted, 999)
    assert exc.value.status_code == 403


def test_rate_limiter_window():
    from fastapi import HTTPException

    from app.config import get_settings

    limit = get_settings().external_rate_limit_per_min
    key_id = 987654321  # unique bucket, avoids collisions with other tests
    for _ in range(limit):
        _enforce_rate_limit(key_id)  # within limit: no raise
    with pytest.raises(HTTPException) as exc:
        _enforce_rate_limit(key_id)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_decode_base64_image():
    import base64

    payload = base64.b64encode(b"\x89PNG fake bytes").decode()
    assert security.decode_base64_image(payload, max_bytes=1024) == b"\x89PNG fake bytes"

    # data-URL prefix is stripped
    assert security.decode_base64_image(f"data:image/png;base64,{payload}", 1024)

    with pytest.raises(ValueError):
        security.decode_base64_image("not base64!!", 1024)
    with pytest.raises(ValueError):
        security.decode_base64_image(payload, max_bytes=2)  # oversize


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["bot_ready"] is False  # no token in the test env


@pytest.mark.asyncio
async def test_welcome_preview_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/welcome/preview", json={"template": "Hello {server}"})
    assert res.status_code == 200
    assert res.json()["rendered"] == "Hello My Server"


@pytest.mark.asyncio
async def test_guilds_requires_ready_bot():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/guilds")
    assert res.status_code == 503  # bot offline in tests


@pytest.mark.asyncio
async def test_external_api_mounted_and_requires_key():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/external/v1/me")
    assert res.status_code == 401  # mount works; auth required
