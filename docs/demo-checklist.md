# Demo Checklist

## Before Demo

- Backend starts without errors.
- Frontend starts and can reach the backend.
- `/api/health`, `/api/health/live`, `/api/health/ready`, and `/api/system/status` return healthy responses.
- OpenAPI loads at `/openapi.json`.
- Demo data is seeded or the Demo Tools status says the demo is ready.
- Demo users are available for admin, manager, and viewer roles.
- `VITE_API_BASE_URL` points to the intended backend.
- Browser zoom and window size are readable for the audience.
- No `.env`, local database files, tokens, or secrets are shown on screen.
- Presenter has the safety boundaries ready: no AI approval, no automatic price activation, no real customer send, no scraping, no payment, no email.

## During Demo

- Follow the main quote flow from customer request to quote preview.
- Show product and cost profile data before pricing output.
- Show candidate prices and price validation.
- Submit or inspect an approval request.
- Approve or reject through a human manager/admin workflow.
- Show audit logs after the decision.
- Show pricing simulation and scenario comparison.
- Show KPI dashboard and dashboard insights.
- Generate or inspect an HTML report.
- Repeat that human review is required before business use.

## After Demo

- Mention that this is a portfolio MVP, not a production pricing engine.
- Mention limitations: no production deployment execution, no payment, no email, no scraping, no autonomous price approval.
- Mention future work: production hardening, managed database migration, real deployment, monitoring, and deeper reporting.
- Close any local terminals or browser tabs that might expose local paths or configuration.
