"""Embed templates: build/save in the dashboard, send to a channel via the bot."""

from __future__ import annotations

import discord
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import BotDep, SessionDep
from app.db.models import Embed as EmbedModel
from app.services.embeds import build_embed

router = APIRouter(prefix="/embeds", tags=["embeds"])


class EmbedField(BaseModel):
    name: str
    value: str
    inline: bool = False


class EmbedIn(BaseModel):
    name: str
    title: str | None = None
    description: str | None = None
    color: int | None = None  # 0xRRGGBB
    fields: list[EmbedField] = Field(default_factory=list)
    footer: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None


class EmbedOut(EmbedIn):
    id: int
    guild_id: str


def _to_out(e: EmbedModel) -> EmbedOut:
    return EmbedOut(
        id=e.id,
        guild_id=str(e.guild_id),
        name=e.name,
        title=e.title,
        description=e.description,
        color=e.color,
        fields=[EmbedField(**f) for f in (e.fields or [])],
        footer=e.footer,
        image_url=e.image_url,
        thumbnail_url=e.thumbnail_url,
    )


def _apply(e: EmbedModel, payload: EmbedIn) -> None:
    e.name = payload.name
    e.title = payload.title
    e.description = payload.description
    e.color = payload.color
    e.fields = [f.model_dump() for f in payload.fields]
    e.footer = payload.footer
    e.image_url = payload.image_url
    e.thumbnail_url = payload.thumbnail_url


async def _get(session, guild_id: int, embed_id: int) -> EmbedModel:
    e = await session.scalar(
        select(EmbedModel).where(EmbedModel.id == embed_id, EmbedModel.guild_id == guild_id)
    )
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Embed not found.")
    return e


@router.get("/{guild_id}", response_model=list[EmbedOut])
async def list_embeds(guild_id: int, session: SessionDep) -> list[EmbedOut]:
    rows = await session.scalars(
        select(EmbedModel).where(EmbedModel.guild_id == guild_id).order_by(EmbedModel.id.desc())
    )
    return [_to_out(e) for e in rows]


@router.post("/{guild_id}", response_model=EmbedOut, status_code=status.HTTP_201_CREATED)
async def create_embed(guild_id: int, payload: EmbedIn, session: SessionDep) -> EmbedOut:
    e = EmbedModel(guild_id=guild_id)
    _apply(e, payload)
    session.add(e)
    await session.commit()
    await session.refresh(e)
    return _to_out(e)


@router.put("/{guild_id}/{embed_id}", response_model=EmbedOut)
async def update_embed(
    guild_id: int, embed_id: int, payload: EmbedIn, session: SessionDep
) -> EmbedOut:
    e = await _get(session, guild_id, embed_id)
    _apply(e, payload)
    await session.commit()
    await session.refresh(e)
    return _to_out(e)


@router.delete("/{guild_id}/{embed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_embed(guild_id: int, embed_id: int, session: SessionDep) -> None:
    e = await _get(session, guild_id, embed_id)
    await session.delete(e)
    await session.commit()


@router.post("/{guild_id}/{embed_id}/send", status_code=status.HTTP_204_NO_CONTENT)
async def send_embed(
    guild_id: int, embed_id: int, channel_id: int, bot: BotDep, session: SessionDep
) -> None:
    e = await _get(session, guild_id, embed_id)
    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.abc.Messageable):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found or not text-based.")
    try:
        await channel.send(embed=build_embed(e))
    except discord.Forbidden as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Missing permission to post in that channel."
        ) from exc
