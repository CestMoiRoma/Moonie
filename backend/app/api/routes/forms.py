"""Custom form definitions + submissions (Discord modals)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep
from app.db.models import Form, FormField, FormSubmission

router = APIRouter(prefix="/forms", tags=["forms"])


class FieldIn(BaseModel):
    label: str = Field(..., max_length=45)
    style: str = Field("short", pattern="^(short|paragraph)$")
    required: bool = True
    placeholder: str | None = Field(None, max_length=100)


class FieldOut(FieldIn):
    position: int


class FormIn(BaseModel):
    name: str
    title: str = Field(..., max_length=45)
    submit_channel_id: int | None = None
    fields: list[FieldIn] = Field(default_factory=list, max_length=5)


class FormOut(BaseModel):
    id: int
    guild_id: str
    name: str
    title: str
    submit_channel_id: str | None
    fields: list[FieldOut]


class SubmissionOut(BaseModel):
    id: int
    user_id: str
    answers: dict
    created_at: datetime


def _to_out(f: Form) -> FormOut:
    return FormOut(
        id=f.id,
        guild_id=str(f.guild_id),
        name=f.name,
        title=f.title,
        submit_channel_id=str(f.submit_channel_id) if f.submit_channel_id else None,
        fields=[
            FieldOut(
                label=fld.label,
                style=fld.style,
                required=fld.required,
                placeholder=fld.placeholder,
                position=fld.position,
            )
            for fld in f.fields
        ],
    )


async def _load(session, guild_id: int, form_id: int) -> Form:
    f = await session.scalar(
        select(Form)
        .where(Form.id == form_id, Form.guild_id == guild_id)
        .options(selectinload(Form.fields))
    )
    if f is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Form not found.")
    return f


def _apply_fields(f: Form, fields: list[FieldIn]) -> None:
    f.fields.clear()
    for i, fld in enumerate(fields):
        f.fields.append(
            FormField(
                position=i,
                label=fld.label,
                style=fld.style,
                required=fld.required,
                placeholder=fld.placeholder,
            )
        )


@router.get("/{guild_id}", response_model=list[FormOut])
async def list_forms(guild_id: int, session: SessionDep) -> list[FormOut]:
    rows = await session.scalars(
        select(Form)
        .where(Form.guild_id == guild_id)
        .options(selectinload(Form.fields))
        .order_by(Form.name)
    )
    return [_to_out(f) for f in rows]


@router.post("/{guild_id}", response_model=FormOut, status_code=status.HTTP_201_CREATED)
async def create_form(guild_id: int, payload: FormIn, session: SessionDep) -> FormOut:
    f = Form(
        guild_id=guild_id,
        name=payload.name,
        title=payload.title,
        submit_channel_id=payload.submit_channel_id,
    )
    _apply_fields(f, payload.fields)
    session.add(f)
    await session.commit()
    f = await _load(session, guild_id, f.id)
    return _to_out(f)


@router.put("/{guild_id}/{form_id}", response_model=FormOut)
async def update_form(
    guild_id: int, form_id: int, payload: FormIn, session: SessionDep
) -> FormOut:
    f = await _load(session, guild_id, form_id)
    f.name = payload.name
    f.title = payload.title
    f.submit_channel_id = payload.submit_channel_id
    _apply_fields(f, payload.fields)
    await session.commit()
    f = await _load(session, guild_id, form_id)
    return _to_out(f)


@router.delete("/{guild_id}/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form(guild_id: int, form_id: int, session: SessionDep) -> None:
    f = await _load(session, guild_id, form_id)
    await session.delete(f)
    await session.commit()


@router.get("/{guild_id}/{form_id}/submissions", response_model=list[SubmissionOut])
async def list_submissions(
    guild_id: int, form_id: int, session: SessionDep
) -> list[SubmissionOut]:
    await _load(session, guild_id, form_id)  # 404 if not in this guild
    rows = await session.scalars(
        select(FormSubmission)
        .where(FormSubmission.form_id == form_id)
        .order_by(FormSubmission.created_at.desc())
    )
    return [
        SubmissionOut(
            id=s.id, user_id=str(s.user_id), answers=s.answers, created_at=s.created_at
        )
        for s in rows
    ]
