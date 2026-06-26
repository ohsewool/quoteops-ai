# PostgreSQL Production Runbook

This runbook explains how to prepare QuoteOps AI for a production-like
PostgreSQL database while keeping SQLite as the local development default.

PR-28 is database readiness documentation and verification support only. It
does not change quote formulas, candidate generation, validation, approval,
AI explanation, role enforcement, audit logging, health checks, or Render
deployment behavior.

## Core Rules

- Use SQLite for local development, demos, and short-lived smoke checks.
- Use managed PostgreSQL for production-like or long-lived deployments.
- Do not use ephemeral SQLite for real customer operations.
- Do not commit real database credentials.
- Do not print raw `DATABASE_URL` values in logs, scripts, README examples, or
  health responses.
- Back up production data before any migration or schema change.
- Test production data migration on staging before touching production.

## When To Use SQLite

Use SQLite when:

- running local development,
- running Playwright smoke tests,
- testing backend behavior on a workstation,
- verifying the MVP without real customer data.

Local example:

```env
DATABASE_URL=sqlite:///./quoteops.db
```

SQLite remains the default if `DATABASE_URL` is not set. It is intentionally
kept for local development.

## When To Use PostgreSQL

Use PostgreSQL when:

- deploying to Render or another production-like host,
- storing long-lived operational data,
- validating multi-instance or durable deployment behavior,
- preparing for real customer quote operations.

Production placeholder example:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

The backend also supports:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

Set the real value only in the hosting dashboard or secret manager. Never
commit it to the repository.

## Why Not Production SQLite

SQLite data is stored on the local filesystem. On many web-service hosts,
including typical Render web service setups without persistent disks, that
filesystem should be treated as ephemeral. Redeploys, instance replacement, or
scaling changes can lose local SQLite data.

For production-like deployments, use managed PostgreSQL through `DATABASE_URL`.

## Schema Initialization

On backend startup, QuoteOps AI runs the existing database initialization flow:

```text
connect to DATABASE_URL
create missing tables
apply small compatibility migrations
run safe seed checks
start FastAPI
```

The startup flow uses `CREATE TABLE IF NOT EXISTS` and existence checks. It does
not drop or reset existing data as part of normal startup.

Important limitation: this MVP does not yet include a full migration framework
such as Alembic. Before long-lived production use, add formal migrations,
backup/restore procedures, and rollback plans.

## Seed Data Behavior

Seed data is sample data only. It is not real market pricing.

The base MVP seed inserts products, options, competitors, sample competitor
prices, cost profiles, and starter price tables only when the `products` table
is empty. Later metadata seeds use unique keys or existence checks.

Local/demo admin seeding is controlled by:

```env
SEED_DEMO_ADMIN=true
DEMO_ADMIN_EMAIL=admin@quoteops.local
DEMO_ADMIN_PASSWORD=quoteops-demo-admin
```

For public production-like deployments, set:

```env
SEED_DEMO_ADMIN=false
```

Create or replace the production owner account through a controlled operational
process before exposing the admin UI.

## Non-Destructive Smoke Check

PR-28 adds:

```bash
py -3 scripts/db_smoke_check.py
```

or, on systems where `python` is configured:

```bash
python scripts/db_smoke_check.py
```

The script checks:

- whether `DATABASE_URL` is configured or using the local default,
- database type detection,
- connection success,
- required table availability,
- basic read queries,
- seed data presence,
- simple duplicate checks for unique seed slugs,
- that no raw secret values are printed.

The default mode is read-only after connecting. It does not create tables,
insert rows, drop tables, or wipe data.

For a fresh local or staging database where you explicitly want to run the
existing safe app initialization first, use:

```bash
py -3 scripts/db_smoke_check.py --initialize
```

Use `--initialize` carefully on production. It uses the same safe startup
initialization as the backend, but production changes should still be reviewed,
backed up, and tested on staging first.

Example safe output:

```text
Database configured: default sqlite
Database type: sqlite
Connection: ok
Schema: ok
Seed data: present
Duplicate seed keys: none
Secrets exposed: no
```

## Manual API Verification

After database setup, verify the backend with:

```bash
curl https://YOUR_BACKEND_DOMAIN/api/health
curl https://YOUR_BACKEND_DOMAIN/api/health/ready
curl https://YOUR_BACKEND_DOMAIN/api/health/db
curl https://YOUR_BACKEND_DOMAIN/api/system/status
curl https://YOUR_BACKEND_DOMAIN/api/products
curl https://YOUR_BACKEND_DOMAIN/api/dashboard/kpis
```

Then verify the core workflow:

1. admin login works,
2. product list loads,
3. quote preview works,
4. candidate generation creates inactive candidates,
5. validation returns deterministic results,
6. approval still requires an owner,
7. audit logs are written,
8. dashboard KPIs load from stored database data.

## Render PostgreSQL Verification

Use these steps for Render:

1. Create or attach a Render PostgreSQL database.
2. Set backend `DATABASE_URL` from the Render PostgreSQL connection string.
3. Set backend `ALLOWED_ORIGINS` to the exact Render frontend origin.
4. Set frontend `VITE_API_BASE_URL` to the exact Render backend origin.
5. Deploy the backend service.
6. Check `GET /api/health`.
7. Check `GET /api/health/ready`.
8. Check `GET /api/health/db`.
9. Confirm database type is `postgresql`.
10. Deploy the frontend static site.
11. Confirm the frontend can call the backend.
12. Confirm admin login.
13. Confirm quote preview.
14. Confirm candidate generation.
15. Confirm validation.
16. Confirm approval still requires owner action.
17. Confirm audit logs are written.
18. Confirm dashboard KPIs load.
19. Confirm no raw database URL, password, OpenAI key, token, or admin secret is visible in responses or logs.

## SQLite To PostgreSQL Migration Readiness

This MVP does not yet provide an automated SQLite-to-PostgreSQL migration tool.
Before migrating real data:

1. create a staging PostgreSQL database,
2. back up the SQLite database file,
3. design an explicit table-by-table export/import plan,
4. preserve primary keys and foreign key relationships,
5. verify timestamps and JSON/text columns,
6. run the import on staging first,
7. run `scripts/db_smoke_check.py` against staging,
8. verify health endpoints,
9. verify quote preview, candidate generation, validation, approval, audit logs, and dashboard KPIs,
10. back up production immediately before migration,
11. avoid destructive schema changes without a rollback plan.

Recommended future work:

- add Alembic migrations,
- add backup/restore runbooks,
- add staging migration fixtures,
- add production owner account creation tooling.

## Troubleshooting

### Invalid DATABASE_URL

Use one of:

```env
DATABASE_URL=sqlite:///./quoteops.db
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

Do not include unsupported schemes.

### Missing PostgreSQL Driver

Install backend dependencies:

```bash
pip install -r requirements.txt
```

The project requires `psycopg[binary]` for PostgreSQL.

### Connection Refused

Check host, port, database provider status, network allowlist, and whether the
database is accepting external connections.

### SSL Required

Some managed providers require SSL. Add the provider-required option to
`DATABASE_URL`, such as `?sslmode=require` when supported by the provider.

### DNS Or Host Resolution Failure

Verify the host name is copied correctly from the provider dashboard. On Render,
prefer the internal connection string when the backend and database are in the
same Render environment.

### Wrong Password

Rotate the database password in the provider dashboard and update the backend
environment variable. Never paste the password into docs or commit history.

### Wrong Database Name

Confirm the database name in the provider dashboard and update `DATABASE_URL`.
Then redeploy or restart the backend.

### Schema Not Initialized

Check backend startup logs and `/api/health/ready`. If this is a fresh staging
database, run the backend once or run:

```bash
py -3 scripts/db_smoke_check.py --initialize
```

Review the output before exposing the environment.

### Seed Data Missing

Check whether `products` is empty and whether seed settings are intended for
the environment. Public production environments should avoid relying on local
demo admin credentials.

### Seed Data Duplicated

Run:

```bash
py -3 scripts/db_smoke_check.py
```

The script checks common duplicate seed keys. If duplicates exist, back up the
database and clean them manually with an reviewed SQL plan.

### Backend Deploys But DB Health Fails

Check `DATABASE_URL`, PostgreSQL provider availability, SSL requirements,
dependency installation, and `/api/health/db`.

### Frontend Works But API Data Is Empty

Confirm the frontend points to the intended backend through `VITE_API_BASE_URL`.
Then confirm the backend points to the intended PostgreSQL database through
`DATABASE_URL`. Empty data often means the backend is connected to a different
database than expected.

### Accidentally Using SQLite In Production

Set `DATABASE_URL` to managed PostgreSQL and redeploy the backend before using
real operational data. Treat any SQLite file on an ephemeral web-service
filesystem as disposable.

### Secrets Appearing In Logs

Stop the deployment, rotate any exposed secrets, remove the logging source, and
redeploy. Health endpoints, smoke scripts, and docs should show only safe
booleans, labels, counts, and placeholder examples.
