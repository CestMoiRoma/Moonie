"""External messaging endpoints: text, embeds, saved embeds, images."""

from __future__ import annotations

import io
from typing import Annotated

import discord
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import SessionDep
from app.db.models import ApiKey, Embed as EmbedModel
from app.external.deps import ExternalBotDep, resolve_channel, require_scope
from app.external.security import SCOPE_MESSAGES_WRITE, decode_base64_image
from app.services.embeds import build_embed

router = APIRouter(tags=["messaging"])

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB

WriteKey = Annotated[ApiKey, Depends(require_scope(SCOPE_MESSAGES_WRITE))]


class MessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class EmbedField(BaseModel):
    name: str
    value: str
    inline: bool = False


class EmbedIn(BaseModel):
    content: str | None = Field(None, max_length=2000)
    title: str | None = None
    description: str | None = None
    color: int | None = None  # 0xRRGGBB
    fields: list[EmbedField] = Field(default_factory=list)
    footer: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None


class ImageIn(BaseModel):
    image_base64: str = Field(..., description="Base64 image data (data-URL prefix allowed).")
    filename: str = "image.png"
    caption: str | None = Field(None, max_length=2000)


class SentMessage(BaseModel):
    message_id: str
    channel_id: str


def _sent(message: discord.Message) -> SentMessage:
    return SentMessage(message_id=str(message.id), channel_id=str(message.channel.id))


async def _send(channel: discord.abc.Messageable, **kwargs) -> discord.Message:
    try:
        return await channel.send(**kwargs)
    except discord.Forbidden as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Bot lacks permission to post in that channel."
        ) from exc
    except discord.HTTPException as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Discord error: {exc}") from exc


@router.post("/channels/{channel_id}/messages", response_model=SentMessage, status_code=201)
async def send_message(
    channel_id: int, payload: MessageIn, key: WriteKey, bot: ExternalBotDep
) -> SentMessage:
    channel = resolve_channel(bot, key, channel_id)
    message = await _send(channel, content=payload.content)
    return _sent(message)


@router.post("/channels/{channel_id}/embeds", response_model=SentMessage, status_code=201)
async def send_embed(
    channel_id: int, payload: EmbedIn, key: WriteKey, bot: ExternalBotDep
) -> SentMessage:
    channel = resolve_channel(bot, key, channel_id)
    # Reuse build_embed via a transient (unsaved) Embed model.
    transient = EmbedModel(
        guild_id=0,
        name="external",
        title=payload.title,
        description=payload.description,
        color=payload.color,
        fields=[f.model_dump() for f in payload.fields],
        footer=payload.footer,
        image_url=payload.image_url,
        thumbnail_url=payload.thumbnail_url,
    )
    message = await _send(channel, content=payload.content, embed=build_embed(transient))
    return _sent(message)


@router.post("/channels/{channel_id}/embeds/{embed_name}", response_model=SentMessage, status_code=201)
async def send_saved_embed(
    channel_id: int,
    embed_name: str,
    key: WriteKey,
    bot: ExternalBotDep,
    session: SessionDep,
) -> SentMessage:
    channel = resolve_channel(bot, key, channel_id)
    embed = await session.scalar(
        select(EmbedModel).where(
            EmbedModel.guild_id == channel.guild.id, EmbedModel.name == embed_name
        )
    )
    if embed is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No saved embed named '{embed_name}'.")
    message = await _send(channel, embed=build_embed(embed))
    return _sent(message)


@router.post("/channels/{channel_id}/images", response_model=SentMessage, status_code=201)
async def send_image(
    channel_id: int, payload: ImageIn, key: WriteKey, bot: ExternalBotDep
) -> SentMessage:
    channel = resolve_channel(bot, key, channel_id)
    try:
        data = decode_base64_image(payload.image_base64, MAX_IMAGE_BYTES)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    file = discord.File(io.BytesIO(data), filename=payload.filename or "image.png")
    message = await _send(channel, content=payload.caption, file=file)
    return _sent(message)
