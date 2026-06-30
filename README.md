# QuoteOps AI

QuoteOps AI is a deterministic pricing-operations SaaS MVP for quote preview, candidate pricing, price validation, human approval workflow, simulations, reports, dashboards, and deployment-ready demo workflows.

This repository is a portfolio MVP, not a production pricing engine. It is designed to show how pricing operations can be structured, tested, audited, and prepared for deployment without letting an AI model guess business-critical prices.

## Problem Statement

Many teams handle quote pricing through spreadsheets, manual reviews, and unclear approval processes. This can make pricing inconsistent, risky, and hard to audit, especially when products, costs, competitor references, and approval decisions change over time.

## Solution Overview

QuoteOps AI centralizes quote operations into a web app that supports deterministic price calculations, validation checks, human approval, audit logs, simulations, dashboards, and reports. AI-facing behavior is limited to safe explanation workflows; numeric pricing, validation, approval, and activation decisions stay deterministic and reviewable.

## Key Features

- Product and cost profile management
- Quote preview
- Candidate price generation
- Price validation
- Human approval/rejection workflow
- Safe quote explanations
- Audit logs
- CSV import/export
- Pricing simulations
- Customer quote requests
- Price table history and comparison
- Workflow jobs
- Strategy templates
- KPI dashboard
- Dashboard insights
- Scenario comparisons
- HTML reports
- Demo data tools
- Health/readiness/system status endpoints
- Render backend/frontend deployment preparation
- Render Deployed QA script
- Security and final regression checks
- Frontend navigation, loading, error, and empty state UX

## Architecture

```text
React/Vite Frontend
        |
        | VITE_API_BASE_URL
        v
FastAPI Backend
        |
        v
SQLite local / PostgreSQL on Render
```

- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLite locally, PostgreSQL-ready for Render
- Testing: pytest, backend compile checks, frontend build checks
- Deployment: Render backend web service + Render frontend static site

## Main User Flow

1. Check health and system status
2. Seed demo data
3. Review product and cost profile
4. Generate quote preview
5. Generate candidate prices
6. Validate a proposed price
7. Submit an approval request
8. Approve or reject through human workflow
9. Review audit logs
10. Run pricing simulation
11. Compare scenarios
12. View dashboard and insights
13. Generate HTML report

## Safety Boundaries

QuoteOps AI does not automatically approve prices. It does not automatically activate price tables, send quotes to customers, scrape real competitor websites, or require external AI APIs by default. Human review is required before business use.

## Local Setup

Backend:

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Useful local URLs:

```text
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/api/health/ready
http://127.0.0.1:8000/docs
```

## Test Commands

```bash
python -m compileall backend
pytest -q
cd frontend
npm run build
```

Optional checks:

```bash
python scripts/security_check.py
python scripts/final_regression_check.py
python scripts/render_deployed_qa.py
```

## Environment Variables

Use `.env.example` as a template. Do not commit `.env` files or real secrets.

- `DATABASE_URL`: SQLite locally or PostgreSQL-compatible URL in deployment
- `QUOTEOPS_ENV`: `local`, `production`, or another safe environment label
- `QUOTEOPS_AUTH_SECRET`: backend auth secret
- `QUOTEOPS_DEMO_TOOLS_ENABLED`: enables local/demo tooling when set safely
- `QUOTEOPS_CORS_ORIGINS`: comma-separated frontend origins allowed by the backend
- `VITE_API_BASE_URL`: frontend API base URL
- `QUOTEOPS_DEPLOYED_BACKEND_URL`: optional deployed QA backend URL
- `QUOTEOPS_DEPLOYED_FRONTEND_URL`: optional deployed QA frontend URL

## Deployment Preparation

Render backend and frontend deployment configuration is prepared. Actual deployment requires setting Render environment variables safely in the Render dashboard. This repository intentionally uses placeholders and does not include real deployed URLs or credentials.

- [Render backend deployment](docs/deployment/render-backend.md)
- [Render frontend deployment](docs/deployment/render-frontend.md)
- [Render Deployed QA](docs/deployment/render-deployed-qa.md)

## Demo Flow

For a portfolio walkthrough, show the operator workflow rather than a generic storefront:

1. Health/system status
2. Demo data tools
3. Quote preview and candidate prices
4. Price validation
5. Human approval/rejection
6. Audit logs
7. Pricing simulation
8. Scenario comparison
9. Dashboard insights
10. HTML report

See [Demo flow](docs/demo-flow.md) for the longer walkthrough.

Demo support docs:

- [Demo flow](docs/demo-flow.md)
- [Demo presenter script](docs/demo-presenter-script.md)
- [Demo checklist](docs/demo-checklist.md)
- [Demo troubleshooting](docs/demo-troubleshooting.md)

## Release Status

Current prepared release package: v0.1.0

This repository contains a portfolio-ready MVP release package. The actual git tag and GitHub Release are handled separately after final verification.

- [v0.1.0 release notes](docs/release/v0.1.0.md)
- [Release checklist](docs/release/release-checklist.md)

## Portfolio Notes

This project is useful as a portfolio example because it shows REST API design, role-based access control, audit logging, deterministic pricing logic, safe reporting, frontend UX organization, deployment preparation, security regression checks, and broad test coverage.

## Documentation

- [API overview](docs/api-overview.md)
- [Demo flow](docs/demo-flow.md)
- [Demo presenter script](docs/demo-presenter-script.md)
- [Demo checklist](docs/demo-checklist.md)
- [Demo troubleshooting](docs/demo-troubleshooting.md)
- [v0.1.0 release notes](docs/release/v0.1.0.md)
- [Release checklist](docs/release/release-checklist.md)
- [Safety boundaries](docs/safety-boundaries.md)
- [Security checklist](docs/security-checklist.md)
- [Final regression checklist](docs/final-regression-checklist.md)
- [Render backend deployment](docs/deployment/render-backend.md)
- [Render frontend deployment](docs/deployment/render-frontend.md)
- [Render Deployed QA](docs/deployment/render-deployed-qa.md)

## Project Status

The MVP includes the implemented pricing operations, approval, reporting, dashboard, security, regression, and deployment-preparation layers listed above. Not implemented: production deployment execution, custom domains, production migrations, release tags, email sending, payment flow, real competitor scraping, background schedulers, monitoring alerts, automatic price approval, and automatic price table activation.
