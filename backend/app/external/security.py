"""API key generation, hashing, and scope definitions for the external API."""

from __future__ import annotations

import base64
import binascii
import hashlib
import secrets

KEY_PREFIX = "mk_"  # "Moonie key" — makes leaked keys easy to spot/grep

# Scopes the external API understands. "*" (granted implicitly to keys holding all
# scopes is not used; keys carry an explicit list).
SCOPE_MESSAGES_WRITE = "messages:write"
SCOPE_GUILDS_READ = "guilds:read"
SCOPES = [SCOPE_MESSAGES_WRITE, SCOPE_GUILDS_READ]


def generate_key() -> str:
    """Return a fresh plaintext API key (shown to the user once)."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    """sha256 hex digest — what we persist (never the plaintext)."""
    return hashlib.sha256(key.encode()).hexdigest()


def key_prefix(key: str) -> str:
    """Short, non-secret prefix for displaying which key is which."""
    return key[:12]


def valid_scopes(scopes: list[str]) -> bool:
    return all(s in SCOPES for s in scopes)


def decode_base64_image(data_b64: str, max_bytes: int) -> bytes:
    """Decode a base64 image (optionally a data-URL); raise ValueError if invalid/oversize."""
    raw = data_b64
    if "," in raw and raw.strip().startswith("data:"):
        raw = raw.split(",", 1)[1]  # strip a data-URL prefix
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 image data.") from exc
    if not data:
        raise ValueError("Image is empty.")
    if len(data) > max_bytes:
        raise ValueError(f"Image exceeds the {max_bytes // (1024 * 1024)} MB limit.")
    return data
