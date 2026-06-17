"""Admin-defined custom text commands (CRUD)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OptionalBotDep, SessionDep
from app.db.models import CustomCommand

router = APIRouter(prefix="/custom-commands", tags=["custom-commands"])


class CommandIn(BaseModel):
    name: str = Field(..., max_length=64)
    response: str
    embed_id: int | None = None


class CommandOut(BaseModel):
    id: int
    guild_id: str
    name: str
    response: str
    embed_id: int | None


def _to_out(c: CustomCommand) -> CommandOut:
    return CommandOut(
        id=c.id,
        guild_id=str(c.guild_id),
        name=c.name,
        response=c.response,
        embed_id=c.embed_id,
    )


def _invalidate(bot, guild_id: int) -> None:
    if bot is not None:
        cog = bot.get_cog("CustomCommands")
        if cog is not None:
            cog.invalidate(guild_id)


async def _get(session, guild_id: int, cmd_id: int) -> CustomCommand:
    c = await session.scalar(
        select(CustomCommand).where(
            CustomCommand.id == cmd_id, CustomCommand.guild_id == guild_id
        )
    )
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Command not found.")
    return c


@router.get("/{guild_id}", response_model=list[CommandOut])
async def list_commands(guild_id: int, session: SessionDep) -> list[CommandOut]:
    rows = await session.scalars(
        select(CustomCommand).where(CustomCommand.guild_id == guild_id).order_by(CustomCommand.name)
    )
    return [_to_out(c) for c in rows]


@router.post("/{guild_id}", response_model=CommandOut, status_code=status.HTTP_201_CREATED)
async def create_command(
    guild_id: int, payload: CommandIn, session: SessionDep, bot: OptionalBotDep
) -> CommandOut:
    c = CustomCommand(
        guild_id=guild_id,
        name=payload.name,
        response=payload.response,
        embed_id=payload.embed_id,
    )
    session.add(c)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A command with that name already exists."
        ) from exc
    await session.refresh(c)
    _invalidate(bot, guild_id)
    return _to_out(c)


@router.put("/{guild_id}/{cmd_id}", response_model=CommandOut)
async def update_command(
    guild_id: int, cmd_id: int, payload: CommandIn, session: SessionDep, bot: OptionalBotDep
) -> CommandOut:
    c = await _get(session, guild_id, cmd_id)
    c.name = payload.name
    c.response = payload.response
    c.embed_id = payload.embed_id
    await session.commit()
    await session.refresh(c)
    _invalidate(bot, guild_id)
    return _to_out(c)


@router.delete("/{guild_id}/{cmd_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_command(
    guild_id: int, cmd_id: int, session: SessionDep, bot: OptionalBotDep
) -> None:
    c = await _get(session, guild_id, cmd_id)
    await session.delete(c)
    await session.commit()
    _invalidate(bot, guild_id)
