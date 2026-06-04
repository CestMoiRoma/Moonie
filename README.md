# 🌙 Moonie

A **self-hosted Discord bot** with a **Vue web dashboard**, shipped as Docker containers.
Built for running on your own box / home server — not a cloud, multi-tenant product.

- **Backend:** Python 3.12 · FastAPI · [discord.py](https://discordpy.readthedocs.io/) 2.x
- **Database:** SQLite (SQLAlchemy 2.0 async + Alembic)
- **Frontend:** Vue 3 + Vite (single-page dashboard, talks to FastAPI over REST)
- **Delivery:** one Docker container (FastAPI serves the API *and* the built dashboard;
  the bot runs in the same process)

> ⚠️ **Security note:** the dashboard is **unauthenticated until Phase 4**. Keep the port on
> your **local network** (don't expose it to the internet) until login support lands.

---

## Architecture

FastAPI owns the asyncio event loop and launches the discord.py bot as a background task on
startup (`lifespan`). Both share one SQLAlchemy async engine and the live bot instance, so API
routes can act on Discord directly (create channels, post embeds, apply permissions). Vite builds
the Vue SPA to static files that FastAPI serves alongside the `/api` routes — one container, one
port, one SQLite file on a mounted volume.

```
Moonie/
├── docker-compose.yml
├── Dockerfile               # multi-stage: build Vue → copy into the Python image
├── .env.example
├── backend/                 # FastAPI app + discord.py bot
│   └── app/
│       ├── main.py          # FastAPI + lifespan that starts the bot + serves the SPA
│       ├── config.py        # env-driven settings
│       ├── db/              # engine, models, Alembic migrations
│       ├── bot/             # MoonieBot client + feature cogs
│       └── api/             # REST routers (one per feature)
└── frontend/                # Vue 3 + Vite dashboard
```

---

## Quick start

### With Docker (recommended)

```bash
cp .env.example .env        # then edit .env and set DISCORD_TOKEN
docker compose up --build
```

Open `http://<host-ip>:8080` from a machine on the same network.

### Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal — dev server proxies /api to the backend)
cd frontend
npm install
npm run dev
```

### Discord setup

1. Create an application & bot at the [Discord Developer Portal](https://discord.com/developers/applications).
2. Under **Bot → Privileged Gateway Intents**, enable **Server Members Intent** and
   **Message Content Intent** (needed for member events and per-user logging).
3. Invite the bot with the `bot` and `applications.commands` scopes and the permissions your
   features need (Manage Roles, Manage Channels, Kick/Ban Members, etc.).
4. Put the token in `.env` as `DISCORD_TOKEN`. Optionally set `GUILD_ID` for instant slash-command sync.

---

## External HTTP API

A separate, **key-authenticated** API for other apps to push content into Discord and read
basic server info. It is distinct from the dashboard's internal `/api` (different prefix, auth,
and docs).

- **Base URL:** `/external/v1` · **Interactive docs:** `/external/docs`
- **Auth:** `Authorization: Bearer <key>` (or the `X-API-Key` header)
- **Scopes:** `messages:write`, `guilds:read`. Keys can also be restricted to a single guild.
- Create/revoke keys in the dashboard under **API Keys** — the secret is shown once at creation.

```bash
# Send a message
curl -X POST https://host:8080/external/v1/channels/<channel_id>/messages \
  -H "Authorization: Bearer mk_…" -H "Content-Type: application/json" \
  -d '{"content":"Hello from my app!"}'

# Send an inline embed
curl -X POST .../external/v1/channels/<channel_id>/embeds \
  -H "Authorization: Bearer mk_…" -H "Content-Type: application/json" \
  -d '{"title":"Deploy done","description":"v1.2.3 is live","color":3066993}'

# Send a saved embed template by name
curl -X POST .../external/v1/channels/<channel_id>/embeds/<embed_name> -H "Authorization: Bearer mk_…"

# Send an image (base64 in JSON)
curl -X POST .../external/v1/channels/<channel_id>/images \
  -H "Authorization: Bearer mk_…" -H "Content-Type: application/json" \
  -d '{"image_base64":"<base64>","filename":"chart.png","caption":"Today’s chart"}'

# Read: server info, channels, presence counts
curl .../external/v1/guilds/<guild_id>            -H "Authorization: Bearer mk_…"
curl .../external/v1/guilds/<guild_id>/presence   -H "Authorization: Bearer mk_…"  # {online, members}
```

Endpoints return JSON; ids are strings. Errors: `401` (bad key), `403` (scope/guild mismatch),
`404`, `400`, `429` (rate limited, with `Retry-After`), `503` (bot offline). A per-key rate limit
(`EXTERNAL_RATE_LIMIT_PER_MIN`, default 60) applies. Disable the whole API with
`EXTERNAL_API_ENABLED=false`.

> ⚠️ The external API is key-gated, but the **dashboard (`/` and `/api`) stays unauthenticated
> until Phase 4**. To expose the external API beyond your LAN, put a reverse proxy (with TLS) in
> front that forwards **only** `/external`, and keep `/` and `/api` on the local network.
> Presence is **counts only**; a full online-member list would need the privileged Presence intent.

## Roadmap

### v1 — feature-complete (auth deferred to Phase 4)
- [x] **Scaffold** — Docker, FastAPI + discord.py wiring, SQLite + Alembic, Vue/Vite shell
- [x] **Moderation** — kick / ban / mute / warn + audit log
- [x] **Welcome / goodbye + autoroles**
- [x] **Role management** — `role_add` (aesthetic role, auto-create if missing)
- [x] **Command permission system** — per-command role/user access control
- [x] **Reaction roles** — emoji *and* button modes
- [x] **Embed builder** — DraftBot-style visual composer
- [x] **Auto-ban from DB** — global banlist + on-join enforcement
- [x] **Groups** — bundle roles + channels for bulk targeting
- [x] **Bulk channel permission manager** — target channels/categories or a Group
- [x] **Custom forms** — Discord modals
- [x] **Per-user logging** — ticket-style per-user log channels in a dedicated category
- [x] **Custom text commands + basic automod**
- [ ] **Dashboard auth** *(Phase 4 — deferred; local-driven first)*

### Planned / later
- [ ] **Modules system** — small plugins for features needing external power
      (Ollama, ComfyUI, …), loaded as optional add-ons on top of the core bot
- [x] **External HTTP API** — key-authenticated `/external/v1` (send message/embed/image, read
      server info + presence counts); see *External HTTP API* above
- [ ] Scheduled messages / reminders
- [ ] Backups / export-import of the SQLite config

> Explicitly **not** planned: music player, leveling/XP.

---

## License

[AGPL-3.0](LICENSE).
