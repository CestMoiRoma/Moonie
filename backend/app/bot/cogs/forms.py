"""Custom forms via Discord modals.

`/form <name>` opens a modal built from the form's stored fields; submissions are
saved to the DB and posted to the form's configured channel.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import SessionFactory
from app.db.models import Form, FormSubmission

log = logging.getLogger("moonie.forms")


class FormModal(discord.ui.Modal):
    def __init__(self, form: Form) -> None:
        super().__init__(title=form.title[:45])
        self.form_id = form.id
        self.form_name = form.name
        self.submit_channel_id = form.submit_channel_id
        self._inputs: list[tuple[str, discord.ui.TextInput]] = []

        for field in form.fields[:5]:  # Discord modals allow at most 5 inputs
            text_input = discord.ui.TextInput(
                label=field.label[:45],
                style=(
                    discord.TextStyle.paragraph
                    if field.style == "paragraph"
                    else discord.TextStyle.short
                ),
                required=field.required,
                placeholder=(field.placeholder or None),
                max_length=4000,
            )
            self.add_item(text_input)
            self._inputs.append((field.label, text_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        answers = {label: ti.value for label, ti in self._inputs}

        async with SessionFactory() as session:
            session.add(
                FormSubmission(
                    form_id=self.form_id,
                    user_id=interaction.user.id,
                    answers=answers,
                )
            )
            await session.commit()

        # Post to the configured channel (best effort).
        if self.submit_channel_id and interaction.guild is not None:
            channel = interaction.guild.get_channel(self.submit_channel_id)
            if isinstance(channel, discord.abc.Messageable):
                embed = discord.Embed(title=f"📝 {self.form_name}", color=discord.Color.green())
                embed.set_author(
                    name=str(interaction.user),
                    icon_url=interaction.user.display_avatar.url,
                )
                for label, value in answers.items():
                    embed.add_field(name=label[:256], value=(value or "—")[:1024], inline=False)
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    log.warning("Failed to post form submission to channel %s", self.submit_channel_id)

        await interaction.response.send_message("✅ Submitted, thank you!", ephemeral=True)


class Forms(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _load_form(self, guild_id: int, name: str) -> Form | None:
        async with SessionFactory() as session:
            return await session.scalar(
                select(Form)
                .where(Form.guild_id == guild_id, Form.name == name)
                .options(selectinload(Form.fields))
            )

    @app_commands.command(name="form", description="Open a custom form.")
    @app_commands.guild_only()
    @app_commands.describe(name="Which form to open")
    async def form(self, interaction: discord.Interaction, name: str) -> None:
        assert interaction.guild is not None
        form = await self._load_form(interaction.guild.id, name)
        if form is None:
            await interaction.response.send_message(
                f"❌ No form named **{name}**.", ephemeral=True
            )
            return
        if not form.fields:
            await interaction.response.send_message(
                "❌ That form has no fields configured yet.", ephemeral=True
            )
            return
        await interaction.response.send_modal(FormModal(form))

    @form.autocomplete("name")
    async def form_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None:
            return []
        async with SessionFactory() as session:
            names = await session.scalars(
                select(Form.name).where(Form.guild_id == interaction.guild.id)
            )
        return [
            app_commands.Choice(name=n, value=n)
            for n in names
            if current.lower() in n.lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Forms(bot))
