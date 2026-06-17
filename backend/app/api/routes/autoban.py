"""The global ban database: members in it are banned on join (see the autoban cog)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import SessionDep
from app.db.models import GlobalBan

router = APIRouter(prefix="/autoban", tags=["autoban"])


class BanOut(BaseModel):
    user_id: str
    reason: str | None
    added_by: str | None
    created_at: datetime


class BanIn(BaseModel):
    user_id: int
    reason: str | None = None
    added_by: int | None = None


class ImportIn(BaseModel):
    user_ids: list[int]
    reason: str | None = None


def _to_out(b: GlobalBan) -> BanOut:
    return BanOut(
        user_id=str(b.user_id),
        reason=b.reason,
        added_by=str(b.added_by) if b.added_by else None,
        created_at=b.created_at,
    )


@router.get("", response_model=list[BanOut])
async def list_bans(session: SessionDep) -> list[BanOut]:
    rows = await session.scalars(select(GlobalBan).order_by(GlobalBan.created_at.desc()))
    return [_to_out(b) for b in rows]


@router.post("", response_model=BanOut, status_code=status.HTTP_201_CREATED)
async def add_ban(payload: BanIn, session: SessionDep) -> BanOut:
    existing = await session.get(GlobalBan, payload.user_id)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User already in the ban database.")
    ban = GlobalBan(user_id=payload.user_id, reason=payload.reason, added_by=payload.added_by)
    session.add(ban)
    await session.commit()
    await session.refresh(ban)
    return _to_out(ban)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_ban(user_id: int, session: SessionDep) -> None:
    ban = await session.get(GlobalBan, user_id)
    if ban is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not in the ban database.")
    await session.delete(ban)
    await session.commit()


@router.post("/import", response_model=dict)
async def import_bans(payload: ImportIn, session: SessionDep) -> dict:
    existing = set(
        (await session.scalars(select(GlobalBan.user_id))).all()
    )
    added = 0
    for uid in payload.user_ids:
        if uid in existing:
            continue
        session.add(GlobalBan(user_id=uid, reason=payload.reason))
        existing.add(uid)
        added += 1
    await session.commit()
    return {"added": added, "skipped": len(payload.user_ids) - added}


@router.get("/export", response_model=list[int])
async def export_bans(session: SessionDep) -> list[int]:
    rows = await session.scalars(select(GlobalBan.user_id))
    return list(rows)
