# Changelog

## v0.1.0 - Initial MVP Release

### Core Pricing Workflow

- Added deterministic quote preview from active price tables with cost-profile fallback.
- Added manual product catalog, product options, competitor references, cost profiles, and internal price table management.
- Added customer quote request submission and admin review flow.

### Candidate Generation And Validation

- Added deterministic candidate price table generation from stored costs, market references, and strategy templates.
- Added deterministic validation, risk levels, warning codes, and persisted validation results.
- Candidate tables remain inactive until explicit human approval.

### AI Explanation

- Added optional AI explanation endpoint with deterministic local fallback.
- AI summarizes stored backend facts only and does not generate prices, margins, validation results, or approval decisions.

### Human Approval Workflow

- Added owner-controlled candidate approval and rejection.
- Approval copies candidate table items deterministically into a new active price table.
- Previous active price tables are archived during approval.

### Admin Roles And Permissions

- Added admin authentication with hashed passwords and bearer sessions.
- Added owner, manager, and viewer roles.
- Enforced backend role checks for mutations, approval, reports, imports, workflows, and admin operations.

### Audit Logs And Workflows

- Added audit log persistence and audit log viewer.
- Added agent timeline logs and workflow job/job-step persistence for pricing analysis flows.

### Dashboard And Insights

- Added operations KPI dashboard.
- Added advanced dashboard insights from stored backend data.
- KPI and insight values are deterministic and are not AI-generated.

### Scenario Comparison And Reports

- Added price table history and deterministic price table comparison.
- Added pricing scenario comparison v2 for price table and candidate table scenarios.
- Added print-friendly HTML reports for candidates, validation, scenario comparison, approval evidence, and operations snapshots.

### Database And Deployment Readiness

- Added SQLite local persistence with automatic schema initialization and safe seed behavior.
- Added PostgreSQL-ready configuration through `DATABASE_URL`.
- Added Render Blueprint deployment files and managed PostgreSQL notes.
- Added health, readiness, database health, and safe system status endpoints.

### Demo And Release Tooling

- Added local/staging demo seed and reset scripts.
- Demo reset requires explicit confirmation and targets known demo records.
- Production demo tools are blocked unless explicitly enabled.
- Added Playwright smoke tests and release/operations checklists.

### Final Production Hardening

- Added environment/config safety cleanup.
- Hardened system status environment reporting.
- Documented CORS, secret safety, demo-tool safety, and Render production settings.
- Verified no web scraping, payment, customer accounts, external monitoring service, Redis, Celery, OAuth, or AI-generated numeric pricing are included.
