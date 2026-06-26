# Deployment Plan

## Primary Deployment Target

Use Render first.

Do not configure Railway for this project unless explicitly requested later.

## Why Render First

Render is suitable for this MVP because:

- FastAPI deployment is straightforward.
- GitHub integration is simple.
- Managed PostgreSQL can be attached through `DATABASE_URL`.
- It keeps deployment simpler than splitting frontend/backend/database too early.

## MVP Deployment Structure

Start with:

```text
Render Web Service
- FastAPI backend
- serves API

Render Static Site
- React + Vite frontend
- calls backend through VITE_API_BASE_URL

SQLite or PostgreSQL
- SQLite for local development
- managed PostgreSQL for production-like deployments
```

For the first MVP, local development matters more than public production readiness.

## Later Production-Like Split

After the MVP works, consider:

```text
Vercel
- React + Vite frontend

Render
- FastAPI backend

Supabase
- PostgreSQL database
```

Do not start with this split unless the MVP is stable.

## Local Development

Recommended local development:

```text
frontend: Vite dev server
backend: FastAPI uvicorn
database: SQLite file
```

Commands should eventually look like:

```bash
# backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# frontend
cd frontend
npm run dev
```

## Environment Variables

Use `.env.example` with placeholders only.

Expected variables:

```dotenv
APP_ENV=development
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
LLM_ENABLED=false

DATABASE_URL=sqlite:///./quoteops.db
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
ENABLE_DEMO_TOOLS=false
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Do not place secrets in frontend environment variables.

## Deployment Rules

- Do not store secrets in markdown files.
- Do not commit `.env`.
- Use `.env.example` only.
- Use deterministic fallback if OpenAI API key is missing.
- Do not require LLM for core pricing calculations.
- Set `ALLOWED_ORIGINS` to the deployed frontend URL in production.
- Use local SQLite for development and managed PostgreSQL for production-like deployments.
- Do not rely on ephemeral SQLite storage for real customer operations.
- Do not claim production readiness before real smoke tests.

## Render Blueprint

PR-27 adds a root-level `render.yaml` for a production-like Render deployment.
It is deployment wiring only; it does not change pricing formulas, candidate
generation, validation, approval, role enforcement, audit logging, or AI
explanation behavior.

The Blueprint defines:

- `quoteops-ai-backend`: FastAPI web service
- `quoteops-ai-frontend`: Vite/React static site
- `quoteops-ai-postgres`: managed Render PostgreSQL database

Backend service settings:

```text
runtime: python
build command: pip install -r requirements.txt
start command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
health check path: /api/health/ready
```

Frontend static site settings:

```text
runtime: static
build command: cd frontend && corepack enable && pnpm install --frozen-lockfile && pnpm run build
publish directory: frontend/dist
```

Render Blueprint environment variables:

```dotenv
# backend
APP_ENV=production
DATABASE_URL=<provided by Render PostgreSQL>
ALLOWED_ORIGINS=https://your-frontend-domain.onrender.com
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
LLM_ENABLED=false
SEED_DEMO_ADMIN=false
ENABLE_DEMO_TOOLS=false

# frontend
VITE_API_BASE_URL=https://your-backend-domain.onrender.com
```

Values marked `sync: false` in `render.yaml` must be set in the Render
dashboard. Do not commit real database URLs, API keys, admin passwords, or
private Render service URLs. Use local/demo admin seeding only for private demos
and replace it before exposing a public environment.

## Render Deployment Steps

1. Commit and push the repository with `render.yaml`.
2. Create a Render Blueprint from the Git repository.
3. Let Render create the backend service, frontend static site, and PostgreSQL database.
4. Confirm `APP_ENV=production` and `ENABLE_DEMO_TOOLS=false` on the backend.
5. Set `ALLOWED_ORIGINS` on the backend to the exact deployed frontend origin.
6. Set `VITE_API_BASE_URL` on the frontend to the exact deployed backend origin.
7. Leave `OPENAI_API_KEY` empty unless AI explanations should call OpenAI.
8. Verify `/api/health/ready` after the backend deploys.
9. Verify the frontend can call `/api/products` and `/api/dashboard/kpis`.

Do not use wildcard CORS in production. Do not rely on ephemeral SQLite storage
for production operations.

## PostgreSQL For Production

PR-24 adds PostgreSQL support through `DATABASE_URL` while keeping SQLite as
the local default.

Local development:

```dotenv
DATABASE_URL=sqlite:///./quoteops.db
```

Production-like deployment:

```dotenv
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

The backend also accepts:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
```

Use a managed PostgreSQL database such as Render PostgreSQL, Supabase
PostgreSQL, Neon PostgreSQL, or another managed provider. Do not hardcode
provider credentials in the repository. Set `DATABASE_URL` in the hosting
dashboard or secret manager.

Startup behavior:

- SQLite: creates the local database file and missing tables.
- PostgreSQL: connects through `psycopg` and creates missing tables.
- Seed data is inserted safely and avoids normal startup duplication.
- Startup does not drop or reset existing data.

Troubleshooting:

- Frontend cannot reach backend: verify `VITE_API_BASE_URL` is the deployed backend origin and the backend `/api/health/ready` URL is reachable.
- CORS blocked: set backend `ALLOWED_ORIGINS` to the exact frontend origin and redeploy the backend. Do not use `*` in production.
- Wrong API URL after frontend deploy: update `VITE_API_BASE_URL` and redeploy the static site because Vite embeds this value at build time.
- Missing or invalid `ALLOWED_ORIGINS`: backend requests from the browser will fail even if direct curl calls work.
- Invalid URL: use `sqlite:///...`, `postgresql://...`, or `postgresql+psycopg://...`.
- Missing driver: run `pip install -r requirements.txt`.
- Connection refused: verify host, port, database name, network allowlist, and provider status.
- SSL required: add the provider-required SSL option to `DATABASE_URL`, such as `?sslmode=require` when supported.
- Missing Python dependency on Render: confirm the backend build command is `pip install -r requirements.txt` and redeploy.
- Backend starts locally but fails on Render: compare Render env vars with `.env.example`, especially `DATABASE_URL`, `ALLOWED_ORIGINS`, and optional admin seed settings.
- Frontend build succeeds but API calls fail: check browser network logs, `VITE_API_BASE_URL`, and backend CORS settings.
- OpenAI key missing: this is allowed; AI explanation should use deterministic fallback mode.
- Health check failing: inspect `/api/health/db` and `/api/system/status` for safe status fields.
- Database empty after deploy: verify the backend is using Render PostgreSQL, not SQLite on an ephemeral web-service filesystem.
- Accidental production SQLite: set `DATABASE_URL` to managed PostgreSQL and redeploy before using real operational data.

Before long-lived production use, add a formal migration system such as Alembic
and a database backup/restore process.

For production database setup, migration-readiness notes, Render PostgreSQL
verification, and the non-destructive smoke check script, see
`docs/POSTGRESQL_RUNBOOK.md`.

## Smoke Test Checklist

Before claiming deployed MVP works:

- `/api/health` returns ok
- `/api/health/ready` is configured as the Render backend health check
- `/api/health/ready` returns `ready`
- `/api/health/db` reports database connectivity without exposing credentials
- `/api/system/status` shows backend, database, fallback explanation, audit, and job status
- backend uses managed PostgreSQL through `DATABASE_URL`
- frontend uses `VITE_API_BASE_URL` for backend calls
- backend `ALLOWED_ORIGINS` contains the deployed frontend origin
- landing page loads
- admin login works with a safe production admin setup
- customer quote page calculates sample quote
- admin can create or load sample competitor prices
- candidate generation works
- validation works
- owner approval works and archives prior active tables
- AI explanation fallback works when `OPENAI_API_KEY` is empty
- audit logs and dashboard KPIs load
- approval saves active price table
- quote page uses approved table
- no secrets are visible in browser source, health responses, logs, or committed files

For release-candidate review, also use:

- `docs/RELEASE_CHECKLIST.md`
- `docs/DEMO_FLOW.md`
- `docs/OPERATIONS_CHECKLIST.md`
- `docs/POSTGRESQL_RUNBOOK.md`

## Operations Diagnostics

Use PR-25 health endpoints after every deploy:

```bash
curl https://your-backend.example.com/api/health
curl https://your-backend.example.com/api/health/ready
curl https://your-backend.example.com/api/health/db
curl https://your-backend.example.com/api/system/status
```

Diagnostics intentionally return only safe configuration booleans and status
labels. They must not expose API keys, database passwords, bearer tokens, or raw
connection strings.

Common production checks:

- database unavailable: verify `DATABASE_URL`, provider status, network access, and SSL requirements
- invalid `DATABASE_URL`: use `sqlite:///...`, `postgresql://...`, or `postgresql+psycopg://...`
- missing OpenAI key: fallback explanation remains available
- CORS failure: set `ALLOWED_ORIGINS` to the exact deployed frontend origin
- frontend cannot reach backend: verify `VITE_API_BASE_URL` and `/api/health/ready`
