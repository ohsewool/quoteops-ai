# Demo Data Tools

PR-29 adds safe demo data tooling for local demos, portfolio reviews, and
staging verification. This is not a pricing feature and does not change quote
calculation, candidate generation, validation, approval, AI explanation, role
enforcement, audit logging, database backend behavior, health checks, or Render
deployment behavior.

## What Demo Data Is

Demo data is deterministic sample data used to prepare a repeatable QuoteOps AI
workspace. It is not real market pricing.

The demo seed creates or updates records with clear demo identifiers:

- `Demo A3 Flyer`
- `Demo Product Sticker`
- `Demo Large Online Printer`
- `Demo Local Print Studio`
- `Demo Premium Sticker Shop`
- demo competitor reference prices
- demo cost profiles
- demo price tables
- a demo quote request
- demo audit events

Sample competitor prices are manually entered demo references only. They are
not scraped and are not real market prices.

## When To Use Demo Seed

Use demo seed when:

- preparing a local walkthrough,
- preparing a portfolio review,
- checking staging data flow,
- restoring a known sample workspace after manual testing.

Command:

```bash
py -3 scripts/seed_demo_data.py
```

or, when `python` points to a real interpreter:

```bash
python scripts/seed_demo_data.py
```

The seed is idempotent. Running it repeatedly updates the same known demo
records instead of duplicating them.

## When To Use Demo Reset

Use demo reset only when you want to remove known PR-29 demo records and
re-create them.

Reset requires explicit confirmation:

```bash
py -3 scripts/reset_demo_data.py --confirm RESET_DEMO_DATA
```

or:

```bash
python scripts/reset_demo_data.py --confirm RESET_DEMO_DATA
```

The reset script removes only known demo records created by the demo seed, such
as demo product slugs, demo competitor names, demo quote requests, and demo
audit events. It does not drop tables and does not wipe the whole database.

## Safety Precautions

- Do not run demo reset against production without a backup and a reviewed plan.
- Do not use demo data as real market pricing.
- Do not commit `.env` or real database credentials.
- Do not print raw `DATABASE_URL`, passwords, tokens, or OpenAI keys.
- Prefer staging verification before any production-like reset operation.
- Keep `ENABLE_DEMO_TOOLS=false` in production unless a reviewed maintenance
  task explicitly requires it.

## Environment Flag

PR-29 does not expose a backend reset API. PR-35 also blocks CLI demo seed/reset
when `APP_ENV=production` unless `ENABLE_DEMO_TOOLS=true` is set explicitly.
The project keeps the same flag for any future API-based demo tools:

```env
ENABLE_DEMO_TOOLS=false
```

Default is false. In production, leave it false for normal operation. If a
backend API is added later, it must require:

- authenticated admin session,
- `owner` role,
- `ENABLE_DEMO_TOOLS=true`,
- explicit confirmation payload such as `confirm: "RESET_DEMO_DATA"`.

## Local SQLite Usage

SQLite remains the local default:

```env
DATABASE_URL=sqlite:///./quoteops.db
```

Run:

```bash
py -3 scripts/seed_demo_data.py
py -3 scripts/reset_demo_data.py --confirm RESET_DEMO_DATA
```

## PostgreSQL Usage

The scripts use the same `DATABASE_URL` configuration as the backend. They are
expected to work with PostgreSQL, but always verify on staging first:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

Never commit real credentials. Never paste real connection strings into docs or
support tickets.

## Verification

After seeding or resetting demo data, verify:

```bash
py -3 scripts/db_smoke_check.py
```

Then verify the app:

1. backend health endpoints return safe JSON,
2. admin login works,
3. product catalog includes demo products,
4. quote preview works,
5. candidate generation still creates inactive candidates,
6. validation works,
7. approval still requires human owner action,
8. audit logs and dashboard KPIs load.

## Troubleshooting

### Reset Fails

Confirm the exact flag:

```bash
--confirm RESET_DEMO_DATA
```

### Demo Data Missing

Run:

```bash
py -3 scripts/seed_demo_data.py
```

Then check products and dashboard KPIs.

### Duplicate Demo Data

The seed is designed to be idempotent. If duplicates appear, back up the
database and inspect records with demo slugs/names before cleaning manually.

### Wrong Database

Check `DATABASE_URL`. Empty or unexpected data usually means the script is
connected to a different database than the backend.

### Secrets In Output

Stop the process, rotate exposed secrets, and remove the logging source. Demo
scripts should print only safe labels, counts, and status messages.
