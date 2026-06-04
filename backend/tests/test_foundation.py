"""Foundation tests: templating logic + a couple of stateless API endpoints."""

from __future__ import annotations

import httpx
import pytest

from app.bot.cogs.automod import CompiledRule
from app.db.models import AutomodRule
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
