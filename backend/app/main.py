"""FastAPI application.

Owns the asyncio loop, launches the discord.py bot as a background task on startup
(sharing the loop + DB), mounts the REST API under /api, and serves the built Vue SPA.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import api_router
from app.bot.client import MoonieBot
from app.config import get_settings

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("moonie")


async def _run_bot(bot: MoonieBot, token: str) -> None:
    try:
        await bot.start(token)
    except asyncio.CancelledError:
        pass
    except Exception:  # noqa: BLE001
        log.exception("Bot crashed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot = MoonieBot()
    app.state.bot = bot

    if settings.has_token:
        app.state.bot_task = asyncio.create_task(_run_bot(bot, settings.discord_token))
        log.info("Discord bot starting…")
    else:
        app.state.bot_task = None
        log.warning("DISCORD_TOKEN not set — API runs but the bot stays offline.")

    try:
        yield
    finally:
        if app.state.bot_task is not None:
            log.info("Shutting down bot…")
            await bot.close()
            app.state.bot_task.cancel()
            try:
                await app.state.bot_task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Moonie", version=__version__, lifespan=lifespan)
app.include_router(api_router)


# ── Serve the built Vue SPA (if present) ─────────────────────────────────────────
_dist = settings.frontend_dist
if _dist.is_dir():
    # Mount hashed assets, then fall back to index.html for client-side routing.
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def no_frontend() -> dict[str, str]:
        return {
            "message": "Moonie API is running. Build the frontend (npm run build) "
            "or use the Vite dev server. API docs at /docs.",
        }
