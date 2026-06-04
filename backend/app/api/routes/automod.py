"""Basic automod rules (CRUD)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import OptionalBotDep, SessionDep
from app.db.models import AutomodRule

router = APIRouter(prefix="/automod", tags=["automod"])


class RuleIn(BaseModel):
    name: str = Field(..., max_length=100)
    pattern: str
    kind: str = Field("word", pattern="^(word|link|regex)$")
    action: str = Field("delete", pattern="^(delete|warn)$")
    enabled: bool = True


class RuleOut(BaseModel):
    id: int
    guild_id: str
    name: str
    pattern: str
    kind: str
    action: str
    enabled: bool


def _to_out(r: AutomodRule) -> RuleOut:
    return RuleOut(
        id=r.id,
        guild_id=str(r.guild_id),
        name=r.name,
        pattern=r.pattern,
        kind=r.kind,
        action=r.action,
        enabled=r.enabled,
    )


def _invalidate(bot, guild_id: int) -> None:
    if bot is not None:
        cog = bot.get_cog("Automod")
        if cog is not None:
            cog.invalidate(guild_id)


async def _get(session, guild_id: int, rule_id: int) -> AutomodRule:
    r = await session.scalar(
        select(AutomodRule).where(
            AutomodRule.id == rule_id, AutomodRule.guild_id == guild_id
        )
    )
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found.")
    return r


@router.get("/{guild_id}", response_model=list[RuleOut])
async def list_rules(guild_id: int, session: SessionDep) -> list[RuleOut]:
    rows = await session.scalars(
        select(AutomodRule).where(AutomodRule.guild_id == guild_id).order_by(AutomodRule.name)
    )
    return [_to_out(r) for r in rows]


@router.post("/{guild_id}", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(
    guild_id: int, payload: RuleIn, session: SessionDep, bot: OptionalBotDep
) -> RuleOut:
    r = AutomodRule(
        guild_id=guild_id,
        name=payload.name,
        pattern=payload.pattern,
        kind=payload.kind,
        action=payload.action,
        enabled=payload.enabled,
    )
    session.add(r)
    await session.commit()
    await session.refresh(r)
    _invalidate(bot, guild_id)
    return _to_out(r)


@router.put("/{guild_id}/{rule_id}", response_model=RuleOut)
async def update_rule(
    guild_id: int, rule_id: int, payload: RuleIn, session: SessionDep, bot: OptionalBotDep
) -> RuleOut:
    r = await _get(session, guild_id, rule_id)
    r.name = payload.name
    r.pattern = payload.pattern
    r.kind = payload.kind
    r.action = payload.action
    r.enabled = payload.enabled
    await session.commit()
    await session.refresh(r)
    _invalidate(bot, guild_id)
    return _to_out(r)


@router.delete("/{guild_id}/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    guild_id: int, rule_id: int, session: SessionDep, bot: OptionalBotDep
) -> None:
    r = await _get(session, guild_id, rule_id)
    await session.delete(r)
    await session.commit()
    _invalidate(bot, guild_id)
