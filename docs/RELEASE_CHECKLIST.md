# Release Candidate Checklist

Use this checklist before tagging QuoteOps AI as a release-candidate MVP.

## Required QA

- [ ] Backend compile passes: `python -m compileall backend` or `py -3 -m compileall backend` on Windows.
- [ ] Frontend build passes: `cd frontend && pnpm run build` or the package manager used by the project.
- [ ] Playwright smoke tests pass when available: `cd frontend && pnpm run test:e2e`.
- [ ] Local SQLite startup works with `DATABASE_URL=sqlite:///./quoteops.db`.
- [ ] A missing local SQLite DB file is created safely on startup.
- [ ] Seed data loads without duplicating normal startup rows.
- [ ] Demo data tools are documented in `docs/DEMO_DATA.md`.
- [ ] Demo reset requires explicit `RESET_DEMO_DATA` confirmation and is not exposed publicly.
- [ ] Production demo tooling is blocked unless `APP_ENV=production` is paired with `ENABLE_DEMO_TOOLS=true`.
- [ ] PostgreSQL configuration is documented through `DATABASE_URL`.
- [ ] PostgreSQL runbook exists at `docs/POSTGRESQL_RUNBOOK.md`.
- [ ] Database smoke check passes: `python scripts/db_smoke_check.py` or `py -3 scripts/db_smoke_check.py`.
- [ ] Render `render.yaml` uses managed PostgreSQL for production-like deployment.
- [ ] Render backend health check path is `/api/health/ready`.
- [ ] Render frontend static build uses pnpm and publishes `frontend/dist`.
- [ ] Production `ALLOWED_ORIGINS` and `VITE_API_BASE_URL` are set to exact deployed origins.
- [ ] Health endpoints return safe JSON: `/api/health`, `/api/health/ready`, `/api/health/db`, `/api/system/status`.
- [ ] Admin login works with local/demo credentials only in local demo mode.
- [ ] Owner, manager, and viewer permissions behave as documented.
- [ ] Quote preview returns deterministic prices.
- [ ] Candidate generation returns generated, inactive candidate tables.
- [ ] Validation returns deterministic pass/warning/fail results.
- [ ] Approval requires explicit human owner action.
- [ ] Candidate approval archives prior active tables and creates a new active price table.
- [ ] AI/fallback explanation works without `OPENAI_API_KEY`.
- [ ] Audit logs record important backend actions.
- [ ] Workflow jobs and job steps are persisted.
- [ ] Dashboard KPI values come from stored backend data.
- [ ] Dashboard insight values come from stored backend data.
- [ ] Scenario comparison v2 returns deterministic stored-data comparisons.
- [ ] Exportable reports return print-friendly HTML without exposing secrets.
- [ ] CSV import/export validates rows deterministically.
- [ ] Health/status endpoints do not expose raw `DATABASE_URL`, database passwords, OpenAI keys, tokens, or auth secrets.
- [ ] `APP_ENV`, `DATABASE_URL`, `ALLOWED_ORIGINS`, demo-tool flags, and Render environment values are documented consistently.
- [ ] README, `.env.example`, and deployment docs match the implementation.

## Product Safety Rules

- [ ] AI does not generate numeric prices.
- [ ] AI does not approve or reject price tables.
- [ ] Candidate tables are not activated automatically.
- [ ] Competitor data is manually entered reference data.
- [ ] No web scraping, payment, customer accounts, Redis, Celery, OAuth, or external monitoring service was added.

## Release Notes

- SQLite is the local MVP default.
- Managed PostgreSQL is recommended for production-like deployments.
- OpenAI is optional and used only for explanations; local fallback must remain available.
- This is an MVP operations tool, not a full ecommerce checkout or enterprise compliance system.
