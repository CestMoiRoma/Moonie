"""The external API as a standalone FastAPI sub-application.

Mounted at /external by the main app (which also injects the live bot into this
app's state). Has its own OpenAPI docs at /external/docs covering only these
endpoints, separate from the dashboard's internal /api.
"""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.external.routes import v1_router
from app.external.security import SCOPES

DESCRIPTION = f"""
Key-authenticated API for sending content to Discord and reading basic server info.

**Auth:** send your key as `Authorization: Bearer <key>` (or the `X-API-Key` header).

**Scopes:** {", ".join(f"`{s}`" for s in SCOPES)}. Keys may also be restricted to a
single guild. Manage keys from the Moonie dashboard.
"""

external_app = FastAPI(
    title="Moonie External API",
    version=__version__,
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
external_app.include_router(v1_router)


@external_app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"name": "Moonie External API", "version": __version__, "docs": "/external/docs"}
