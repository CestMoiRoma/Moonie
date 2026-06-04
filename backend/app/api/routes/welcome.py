"""Welcome/goodbye helpers for the dashboard editor (preview).

The actual config lives under /api/settings; this router renders a live preview of
a message template with sample data so the editor can show what members will see.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.templating import (
    DEFAULT_GOODBYE,
    DEFAULT_WELCOME,
    render_message,
)

router = APIRouter(prefix="/welcome", tags=["welcome"])

_SAMPLE_CONTEXT = {
    "user": "SampleUser#1234",
    "user_mention": "@SampleUser",
    "user_name": "SampleUser",
    "server": "My Server",
    "member_count": 42,
}


class PreviewRequest(BaseModel):
    template: str


class PreviewResponse(BaseModel):
    rendered: str


class DefaultsResponse(BaseModel):
    welcome: str
    goodbye: str
    placeholders: list[str]


@router.get("/defaults", response_model=DefaultsResponse)
async def defaults() -> DefaultsResponse:
    return DefaultsResponse(
        welcome=DEFAULT_WELCOME,
        goodbye=DEFAULT_GOODBYE,
        placeholders=list(_SAMPLE_CONTEXT.keys()),
    )


@router.post("/preview", response_model=PreviewResponse)
async def preview(payload: PreviewRequest) -> PreviewResponse:
    return PreviewResponse(rendered=render_message(payload.template, _SAMPLE_CONTEXT))
