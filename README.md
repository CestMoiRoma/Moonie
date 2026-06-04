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
- [ ] Scheduled messages / reminders
- [ ] Optional public HTTP API (FastAPI's OpenAPI docs already pave the way)
- [ ] Backups / export-import of the SQLite config

> Explicitly **not** planned: music player, leveling/XP.

---

## License

[AGPL-3.0](LICENSE).
