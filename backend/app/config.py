"""Environment-driven application settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root (…/Moonie), used to locate the built frontend and the .env file.
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Discord ──────────────────────────────────────────────────────────────
    discord_token: str = ""
    guild_id: int | None = None
    prefix: str = "-"

    # ── Web / API ────────────────────────────────────────────────────────────
    bind_addr: str = "0.0.0.0"
    bind_port: int = 8080

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/moonie.db"

    # ── Misc ─────────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    @property
    def frontend_dist(self) -> Path:
        """Path to the built Vue SPA (created by `npm run build`)."""
        return REPO_ROOT / "frontend" / "dist"

    @property
    def has_token(self) -> bool:
        return bool(self.discord_token) and self.discord_token != "your_bot_token_here"


@lru_cache
def get_settings() -> Settings:
    return Settings()
