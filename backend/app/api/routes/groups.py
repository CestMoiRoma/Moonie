"""Groups: named bundles of roles and/or channels for bulk targeting."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep
from app.db.models import Group, GroupItem

router = APIRouter(prefix="/groups", tags=["groups"])


class GroupItemIn(BaseModel):
    kind: str = Field(..., pattern="^(role|channel)$")
    discord_id: int


class GroupItemOut(BaseModel):
    kind: str
    discord_id: str


class GroupIn(BaseModel):
    name: str
    description: str | None = None
    items: list[GroupItemIn] = Field(default_factory=list)


class GroupOut(BaseModel):
    id: int
    guild_id: str
    name: str
    description: str | None
    items: list[GroupItemOut]


def _to_out(g: Group) -> GroupOut:
    return GroupOut(
        id=g.id,
        guild_id=str(g.guild_id),
        name=g.name,
        description=g.description,
        items=[GroupItemOut(kind=i.kind, discord_id=str(i.discord_id)) for i in g.items],
    )


async def _load(session, guild_id: int, group_id: int) -> Group:
    g = await session.scalar(
        select(Group)
        .where(Group.id == group_id, Group.guild_id == guild_id)
        .options(selectinload(Group.items))
    )
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found.")
    return g


@router.get("/{guild_id}", response_model=list[GroupOut])
async def list_groups(guild_id: int, session: SessionDep) -> list[GroupOut]:
    rows = await session.scalars(
        select(Group)
        .where(Group.guild_id == guild_id)
        .options(selectinload(Group.items))
        .order_by(Group.name)
    )
    return [_to_out(g) for g in rows]


@router.post("/{guild_id}", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(guild_id: int, payload: GroupIn, session: SessionDep) -> GroupOut:
    g = Group(
        guild_id=guild_id,
        name=payload.name,
        description=payload.description,
        items=[GroupItem(kind=i.kind, discord_id=i.discord_id) for i in payload.items],
    )
    session.add(g)
    await session.commit()
    g = await _load(session, guild_id, g.id)
    return _to_out(g)


@router.put("/{guild_id}/{group_id}", response_model=GroupOut)
async def update_group(
    guild_id: int, group_id: int, payload: GroupIn, session: SessionDep
) -> GroupOut:
    g = await _load(session, guild_id, group_id)
    g.name = payload.name
    g.description = payload.description
    g.items.clear()
    for i in payload.items:
        g.items.append(GroupItem(kind=i.kind, discord_id=i.discord_id))
    await session.commit()
    g = await _load(session, guild_id, group_id)
    return _to_out(g)


@router.delete("/{guild_id}/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(guild_id: int, group_id: int, session: SessionDep) -> None:
    g = await _load(session, guild_id, group_id)
    await session.delete(g)
    await session.commit()
