"""Build a discord.Embed from a stored Embed template."""

from __future__ import annotations

import discord

from app.db.models import Embed as EmbedModel


def build_embed(model: EmbedModel) -> discord.Embed:
    embed = discord.Embed(
        title=model.title or None,
        description=model.description or None,
        color=discord.Color(model.color) if model.color is not None else None,
    )
    for field in model.fields or []:
        name = str(field.get("name", "​"))[:256]
        value = str(field.get("value", "​"))[:1024]
        embed.add_field(name=name, value=value, inline=bool(field.get("inline", False)))
    if model.footer:
        embed.set_footer(text=model.footer[:2048])
    if model.image_url:
        embed.set_image(url=model.image_url)
    if model.thumbnail_url:
        embed.set_thumbnail(url=model.thumbnail_url)
    return embed
