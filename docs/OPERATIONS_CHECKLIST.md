# Operations Checklist

Use this checklist before a local demo, staging deploy, or release-candidate review.

## Environment

- [ ] Set backend environment variables in the host or deployment dashboard.
- [ ] Set `APP_ENV=development` locally and `APP_ENV=production` for production deployments.
- [ ] Use `DATABASE_URL=sqlite:///./quoteops.db` for local development.
- [ ] Use a managed PostgreSQL `DATABASE_URL` for production-like deployments.
- [ ] Set `ALLOWED_ORIGINS` to the exact frontend origin.
- [ ] Set `OPENAI_API_KEY` only when OpenAI explanations are desired.
- [ ] Keep `OPENAI_API_KEY` empty to verify deterministic fallback explanation.
- [ ] Set `OPENAI_MODEL=gpt-4o-mini` or the approved explanation model.
- [ ] Set `VITE_API_BASE_URL` on the frontend to the deployed backend URL.
- [ ] Keep `ENABLE_DEMO_TOOLS=false` in production unless a reviewed maintenance task explicitly requires it.
- [ ] Never commit real database credentials, API keys, tokens, or passwords.

## Database

- [ ] Confirm SQLite is local-only or backed by persistent storage for prototypes.
- [ ] Confirm production-like deployments use managed PostgreSQL.
- [ ] Confirm startup creates missing tables without dropping existing data.
- [ ] Confirm seed data is clearly sample data and does not duplicate on normal startup.
- [ ] Use `py -3 scripts/seed_demo_data.py` only for local/staging demo preparation.
- [ ] Use demo reset only with `--confirm RESET_DEMO_DATA`, backup, and `docs/DEMO_DATA.md` reviewed.
- [ ] Run `py -3 scripts/db_smoke_check.py` against the configured database.
- [ ] Review `docs/POSTGRESQL_RUNBOOK.md` before any production database migration.
- [ ] Confirm backups and a formal migration tool are planned before long-lived production use.

## Health And Diagnostics

- [ ] `GET /api/health` returns valid JSON.
- [ ] `GET /api/health/ready` returns `ready`.
- [ ] `GET /api/health/db` reports database connectivity.
- [ ] `GET /api/system/status` reports safe operational status for the admin UI.
- [ ] Health/status endpoints do not expose raw `DATABASE_URL`, database passwords, OpenAI keys, bearer tokens, or auth secrets.
- [ ] Startup logs show database type, schema/seed completion, OpenAI/fallback mode, and CORS origins without secrets.

## Access Control

- [ ] Local/demo owner login works only for local demo use.
- [ ] Owner can approve and reject candidates.
- [ ] Manager can manage pricing operations but cannot approve or reject candidates.
- [ ] Viewer is read-only for mutation endpoints.
- [ ] Missing bearer token returns `401` for protected mutations.
- [ ] Insufficient role returns `403` for protected mutations.

## Workflow Smoke

- [ ] Product list loads.
- [ ] Competitor reference data loads.
- [ ] Cost profiles load.
- [ ] Quote preview works.
- [ ] Candidate generation creates inactive candidate tables.
- [ ] Validation works.
- [ ] AI/fallback explanation works without requiring `OPENAI_API_KEY`.
- [ ] Approval requires human owner action.
- [ ] Approved candidate becomes an active price table.
- [ ] Quote preview uses the newly active price table.
- [ ] Audit logs and Agent Timeline show the operation trail.
- [ ] Dashboard KPIs load.
- [ ] Dashboard insights load.
- [ ] Scenario comparison loads and does not change active prices.
- [ ] Exportable reports return print-friendly HTML without secrets.
- [ ] Workflow jobs and job steps load.
- [ ] CSV import/export works with deterministic row-level validation.

## Deployment Review

- [ ] Render Blueprint includes backend, frontend static site, and managed PostgreSQL resources.
- [ ] Backend start command is `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- [ ] Frontend Render build uses `pnpm install --frozen-lockfile` and publishes `frontend/dist`.
- [ ] Frontend can reach backend through `VITE_API_BASE_URL`.
- [ ] Backend CORS allows only the expected frontend origin.
- [ ] Production CORS does not use wildcard origins.
- [ ] Render or hosting environment stores secrets outside the repository.
- [ ] Backend health check path is `/api/health/ready`.
- [ ] Production backend uses managed PostgreSQL through `DATABASE_URL`, not ephemeral SQLite.
- [ ] PostgreSQL SSL or provider-specific connection options are configured if required.
- [ ] `/api/health/ready` is checked after every deployment.
- [ ] OpenAI fallback is verified when `OPENAI_API_KEY` is empty.
- [ ] Admin login, quote preview, candidate generation, validation, owner approval, audit logs, and dashboard KPIs work after deployment.
- [ ] Known MVP limitations are communicated clearly.
