# QuoteOps AI

QuoteOps AI is a deterministic pricing-operations SaaS MVP for quote preview, candidate pricing, validation, approval workflow, simulations, reporting, dashboard metrics, and demo workflows.

QuoteOps AI does not automatically approve, activate, or send prices. Human review is required before using pricing outputs.

## Implemented Features

- Backend health and system status endpoints
- Products and cost profiles
- Quote preview
- Candidate prices
- Price validation
- Human approval/rejection workflow
- Safe explanations
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
- Render backend deployment preparation
- Render frontend deployment preparation
- CORS/env configuration
- Frontend navigation, loading, error, and empty state UX

## Local Backend Setup

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Useful local URLs:

```text
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/api/health/ready
http://127.0.0.1:8000/docs
```

## Local Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend uses `VITE_API_BASE_URL` and defaults to `http://127.0.0.1:8000` for local development.

## Verification

```bash
python -m compileall backend
pytest -q
cd frontend
npm run build
```

## Render Deployed QA

After Render backend/frontend services are configured, run optional deployed smoke checks:

```bash
python scripts/render_deployed_qa.py
```

Set `QUOTEOPS_DEPLOYED_BACKEND_URL` and `QUOTEOPS_DEPLOYED_FRONTEND_URL` to check deployed services. See [Render deployed QA](docs/deployment/render-deployed-qa.md).

## Environment Variables

Use `.env.example` as a template. Do not commit `.env` files.

- `DATABASE_URL`: SQLite locally or PostgreSQL-compatible URL in deployment
- `QUOTEOPS_ENV`: `local`, `production`, or another safe environment label
- `QUOTEOPS_AUTH_SECRET`: backend auth secret
- `QUOTEOPS_DEMO_TOOLS_ENABLED`: enables local/demo tooling when set safely
- `QUOTEOPS_CORS_ORIGINS`: comma-separated frontend origins allowed by the backend
- `VITE_API_BASE_URL`: frontend API base URL

## Deployment Notes

Render backend and frontend configuration files are prepared, but deployment must be done by configuring Render services and environment variables safely. Use placeholder URLs in docs and real values only in Render environment settings.

See:

- [Render backend deployment](docs/deployment/render-backend.md)
- [Render frontend deployment](docs/deployment/render-frontend.md)
- [Render deployed QA](docs/deployment/render-deployed-qa.md)
- [API overview](docs/api-overview.md)
- [Demo flow](docs/demo-flow.md)
- [Safety boundaries](docs/safety-boundaries.md)

## Security Notes

Do not commit `.env`, database files, Render credentials, API keys, or auth secrets. Core pricing calculations are deterministic backend workflows; external AI is not required for pricing, approval, or activation.

## Not Implemented Yet

- Real production deployment execution
- Custom domains
- Production migrations
- Email sending
- Payment flow
- Real competitor scraping
- Background scheduler or monitoring alerts
- Automatic price approval or automatic price table activation
