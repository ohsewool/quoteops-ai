# QuoteOps AI v0.1.0 Release Notes

QuoteOps AI v0.1.0 is the first stable MVP release of an AI-assisted pricing and quoting operations system for small print, sticker, label, and custom-product businesses.

## Project Overview

QuoteOps AI helps operators manage market-aware, margin-protected price tables without blindly copying competitor prices. It combines manually entered competitor references, internal cost/margin settings, deterministic candidate generation, deterministic validation, optional AI/fallback explanations, and human owner approval.

## Target User

The target user is a small print shop, sticker/label shop, or custom-product operator who needs safer quantity-based pricing workflows for products such as flyers, stickers, business cards, banners, posters, and future custom goods.

## Core Workflow

```text
manual competitor references + internal cost/margin + pricing strategy
-> deterministic candidate price table
-> deterministic validation
-> AI or fallback explanation
-> human owner approval
-> active price table for quote preview
```

## Major Features

- React/Vite admin workspace with Korean-first operations UI.
- FastAPI backend with SQLite local persistence and PostgreSQL-ready configuration.
- Product catalog, product option, competitor, competitor price, cost profile, and price table management.
- Deterministic quote preview using active price table rows first, then cost-profile fallback.
- Deterministic candidate price table generation and persisted candidate tables.
- Deterministic validation with risk levels, warning/error codes, and saved validation results.
- Optional AI explanation with local fallback when `OPENAI_API_KEY` is missing.
- Human approval/rejection workflow with owner-only approval.
- Admin authentication with owner, manager, and viewer roles.
- Audit logs, agent timeline logs, workflow jobs, and job steps.
- CSV import/export for competitor prices, cost profiles, price table items, and candidate table items.
- Operations dashboard KPIs and advanced dashboard insights.
- Pricing simulation and deterministic scenario comparison.
- Price table history and comparison views.
- Customer quote request submission and admin review.
- Print-friendly HTML reports for candidates, validation, scenario comparison, approval evidence, and operations snapshots.
- Demo data seed/reset tools for local and staging walkthroughs.
- Health, readiness, database health, and safe system status endpoints.
- Render Blueprint deployment readiness with managed PostgreSQL notes.

## Deterministic Pricing Principle

All numeric pricing outputs are produced by backend logic from stored data. Quote prices, candidate prices, margins, validation results, KPI values, simulation numbers, scenario comparison values, and report numbers are deterministic backend outputs.

## AI Limitation

AI does not generate prices. AI does not generate margins. AI does not generate validation results. AI does not generate KPI values or scenario comparison numbers. AI does not approve or reject candidate price tables. AI explanation is optional context only and can fall back to a deterministic local explanation.

## Human Approval Workflow

Candidate tables are not activated automatically. Final approval is human-controlled. Only an owner can approve or reject candidate price tables. Approval copies stored candidate rows into a new active internal price table and archives the previous active table for the product.

## Role-Based Access Control

The backend is the source of truth for permissions:

- `owner`: can perform final approval/rejection and manage operations.
- `manager`: can manage pricing data and run candidate/validation/explanation workflows, but cannot approve.
- `viewer`: read-only admin role.

Frontend disabled controls are convenience only; backend role enforcement remains required.

## Audit Logging And Traceability

Important operations create audit logs, and pricing workflow steps are visible through agent timeline logs and persisted jobs. Audit logs are operational traceability for the MVP, not a full enterprise compliance system.

## Dashboard KPIs And Insights

The dashboard summarizes stored backend data such as products, competitors, price tables, candidate status, validation status, quote request status, audit log counts, workflow job counts, and operational insight items. AI does not generate dashboard numbers.

## Scenario Comparison

Scenario comparison compares stored price tables and candidate tables deterministically. It reports price differences, margin differences where cost data exists, validation/approval readiness, warnings, and missing data. It does not activate price tables.

## Report Generation

Reports are read-only, print-friendly HTML snapshots. Supported report types include candidate price reports, validation reports, scenario comparison reports, approval evidence reports, and operations snapshots. Reports do not expose secrets, run approval, change prices, run validation, or create candidates.

## PostgreSQL And SQLite Support

SQLite is the default local MVP database. PostgreSQL is supported through `DATABASE_URL` for production-like deployments. Production should use managed PostgreSQL instead of ephemeral SQLite storage. Startup creates missing tables and avoids destructive resets.

## Render Deployment Readiness

The repository includes `render.yaml` for a FastAPI backend, Vite static frontend, and managed Render PostgreSQL database. Production configuration should set exact `ALLOWED_ORIGINS`, `APP_ENV=production`, `SEED_DEMO_ADMIN=false`, and `ENABLE_DEMO_TOOLS=false`.

## Demo Data Tools

Demo data tools create repeatable local/staging sample data only. Demo data is not real market data. Demo reset requires `RESET_DEMO_DATA` confirmation and targets known demo records. Demo tooling is blocked in production mode unless explicitly enabled.

## Health And Status Endpoints

The release includes:

- `GET /api/health`
- `GET /api/health/ready`
- `GET /api/health/db`
- `GET /api/system/status`

These endpoints return safe operational status and must not expose raw `DATABASE_URL`, database passwords, OpenAI keys, bearer tokens, or private environment values.

## Security And Secret Safety

Secrets must be stored in environment variables or a managed secret store. Do not commit real database credentials, OpenAI API keys, bearer tokens, admin passwords, private Render URLs, or production `.env` files. Frontend `VITE_*` variables must not contain backend secrets.

## Known Limitations

- This is an MVP admin operations tool, not a full ecommerce checkout.
- No customer accounts, payment, shipping, inventory, OAuth, Redis, Celery, or external monitoring service are included.
- No web scraping is used; competitor prices are manually entered reference data.
- AI explanation is optional and explanation-only.
- SQLite is suitable for local development; production should use managed PostgreSQL.
- Formal database migrations and backup/restore automation should be added before long-lived production operations.
- Audit logging is useful for traceability but is not a full enterprise compliance system.
- Playwright tests are smoke tests, not exhaustive business-rule coverage.

## Recommended Next Version Ideas

- Add formal database migrations with Alembic.
- Add production backup/restore documentation and scripts.
- Add deeper automated API regression tests.
- Add stricter session security and production auth hardening.
- Add richer admin onboarding and guided setup.
- Add optional notification/email workflow after admin-reviewed quotes.
- Add more product templates while preserving the same deterministic pricing flow.
