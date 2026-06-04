"""SQLAlchemy models for Moonie.

Most tables carry `guild_id` so a single instance can serve multiple guilds.
Discord snowflake ids are stored as BigInteger. The full v1 schema is declared
here up front to keep migrations stable as features land phase by phase.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin


class GuildConfig(Base, TimestampMixin):
    """Per-guild settings (welcome/goodbye, autoroles, logging category)."""

    __tablename__ = "guild_config"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Welcome / goodbye
    welcome_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    goodbye_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    goodbye_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Roles automatically granted on join (list of role ids).
    autorole_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)

    # Category under which per-user "ticket-style" log channels are created.
    log_category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class ModAction(Base, TimestampMixin):
    """Audit log of moderation actions."""

    __tablename__ = "mod_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # kick/ban/mute/warn/unban...
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AutomodRule(Base, TimestampMixin):
    """Simple word/link filter rules."""

    __tablename__ = "automod_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="word", nullable=False)  # word|link|regex
    action: Mapped[str] = mapped_column(String(16), default="delete", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CustomCommand(Base, TimestampMixin):
    """Admin-defined text commands (name → response)."""

    __tablename__ = "custom_commands"
    __table_args__ = (UniqueConstraint("guild_id", "name", name="uq_custom_cmd_guild_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    embed_id: Mapped[int | None] = mapped_column(ForeignKey("embeds.id"), nullable=True)


class GlobalBan(Base, TimestampMixin):
    """The auto-ban database: users banned on join across guilds."""

    __tablename__ = "global_bans"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class FlaggedUser(Base, TimestampMixin):
    """A user flagged for per-user 'ticket-style' logging into a dedicated channel."""

    __tablename__ = "flagged_users"
    __table_args__ = (UniqueConstraint("guild_id", "user_id", name="uq_flagged_guild_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ReactionRoleMessage(Base, TimestampMixin):
    """A message that grants roles via emoji reactions or buttons."""

    __tablename__ = "reaction_role_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mode: Mapped[str] = mapped_column(String(8), default="emoji", nullable=False)  # emoji|button
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    entries: Mapped[list["ReactionRoleEntry"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class ReactionRoleEntry(Base):
    """A single emoji/button → role mapping within a reaction-role message."""

    __tablename__ = "reaction_role_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_pk: Mapped[int] = mapped_column(
        ForeignKey("reaction_role_messages.id", ondelete="CASCADE"), nullable=False
    )
    emoji: Mapped[str | None] = mapped_column(String(128), nullable=True)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    message: Mapped[ReactionRoleMessage] = relationship(back_populates="entries")


class Embed(Base, TimestampMixin):
    """A saved embed template (DraftBot-style builder)."""

    __tablename__ = "embeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    footer: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class Form(Base, TimestampMixin):
    """A Discord-modal form definition."""

    __tablename__ = "forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    submit_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    fields: Mapped[list["FormField"]] = relationship(
        back_populates="form", cascade="all, delete-orphan", order_by="FormField.position"
    )


class FormField(Base):
    """A single input within a form (Discord modals allow up to 5)."""

    __tablename__ = "form_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    label: Mapped[str] = mapped_column(String(45), nullable=False)
    style: Mapped[str] = mapped_column(String(16), default="short", nullable=False)  # short|paragraph
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    placeholder: Mapped[str | None] = mapped_column(String(100), nullable=True)

    form: Mapped[Form] = relationship(back_populates="fields")


class FormSubmission(Base, TimestampMixin):
    """A captured set of answers for a form."""

    __tablename__ = "form_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Group(Base, TimestampMixin):
    """A named bundle of roles and/or channels for bulk targeting."""

    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("guild_id", "name", name="uq_group_guild_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["GroupItem"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GroupItem(Base):
    """A role or channel belonging to a Group."""

    __tablename__ = "group_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)  # role|channel
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    group: Mapped[Group] = relationship(back_populates="items")


class CommandPermission(Base, TimestampMixin):
    """Per-command access control: which roles/users may run a command."""

    __tablename__ = "command_permissions"
    __table_args__ = (UniqueConstraint("guild_id", "command", name="uq_cmdperm_guild_command"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    command: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed_role_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    allowed_user_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)


class DashboardAdmin(Base, TimestampMixin):
    """Single admin credential for the dashboard (Phase 4 — auth)."""

    __tablename__ = "dashboard_admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class ApiKey(Base, TimestampMixin):
    """A scoped key for the external HTTP API (Phase 3.5).

    Only the sha256 hash is stored; the plaintext key is shown once at creation.
    `guild_id` null means the key may act on any guild the bot is in.
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    guild_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
