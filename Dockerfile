# ── Stage 1: build the Vue dashboard ─────────────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build          # outputs to /frontend/dist

# ── Stage 2: Python runtime (FastAPI + discord.py bot) ───────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install backend deps first (better layer caching)
COPY backend/pyproject.toml ./backend/pyproject.toml
RUN pip install --upgrade pip && pip install -e ./backend

# App code
COPY backend/ ./backend/

# Built dashboard from stage 1 — served by FastAPI as static files
COPY --from=frontend /frontend/dist ./frontend/dist

# Data dir for the SQLite file (mounted as a volume in compose)
RUN mkdir -p /app/data /app/logs

WORKDIR /app/backend
EXPOSE 8080

# Run migrations then launch the app (which starts the bot in its lifespan).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host ${BIND_ADDR:-0.0.0.0} --port ${BIND_PORT:-8080}"]
