# Vet Clinic Workflow Automation

Multi-clinic SaaS for vet clinic workflow automation (scheduling, records, reminders, billing). This is currently a bare scaffold: a runnable skeleton with no business logic yet, used as the foundation for future feature work.

## Stack

- Backend: Python 3.13 + FastAPI, SQLAlchemy 2.0 + Alembic, PostgreSQL
- Frontend: React + TypeScript (Vite)
- Local infra: Docker Compose (Postgres + Redis)

## Multi-tenancy convention

Every clinic's data lives in the same schema, scoped by a `clinic_id` column. Any model holding per-clinic data uses `TenantScopedMixin` (`backend/app/models/mixins.py`). Any repository/service function reading or writing such a table **must** take `clinic_id` as an explicit, mandatory argument and apply it via `scoped()` (`backend/app/core/tenancy.py`) — never infer the current clinic implicitly. This is enforced by convention/review today, not by Postgres row-level security.

## Prerequisites

- Python 3.13+
- Node 20+ / npm
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Postgres + Redis)

## Setup (PowerShell)

### 1. Start Postgres + Redis

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps    # both services should show "healthy"
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Verify: open http://localhost:8000/api/health — should return `{"status":"ok","environment":"development"}`.

Run tests: `.venv\Scripts\python.exe -m pytest`

> Note: `backend/.env`'s `DATABASE_URL` credentials must match the root `.env` used by `docker-compose.yml` — they're two separate files by design (backend config vs. compose config), kept in sync manually.

### 3. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Verify: open http://localhost:5173 — should show a "Backend health check" page with a live `status: ok` response fetched from the FastAPI backend. If you see a CORS or fetch error instead, make sure `backend/.env`'s `BACKEND_CORS_ORIGINS` includes `http://localhost:5173` and restart uvicorn.

## Windows notes

- If venv activation is blocked by execution policy, either run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or just call `.venv\Scripts\python.exe` / `.venv\Scripts\pip.exe` directly without activating.
- PowerShell 5.1 has no `&&` — the commands above are already written to run one line at a time.
- This repo may sit under a OneDrive-synced `Documents` folder. If `uvicorn --reload` or Vite HMR misbehave with file-lock errors, exclude this folder from sync or move the working copy to a non-synced path.
- If ports 5432/6379 are already in use by a local Postgres/Redis install, override `POSTGRES_PORT`/`REDIS_PORT` in the root `.env` instead of editing `docker-compose.yml`.

## Project layout

```
backend/
  app/
    api/        # FastAPI routers
    core/       # cross-cutting conventions (tenancy scoping)
    db/         # SQLAlchemy base/session
    models/     # ORM models (clinics, users, owners, pets, appointments)
    config.py   # pydantic-settings
    main.py     # FastAPI app entrypoint
  alembic/      # migrations
  tests/
frontend/
  src/
    api/        # backend API client functions
    pages/      # page components
    config.ts   # env-driven config
docker-compose.yml   # Postgres + Redis for local dev
```
