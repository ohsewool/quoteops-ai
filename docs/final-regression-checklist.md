# Final Regression Checklist

Use this checklist before Render deployed QA or release/tag work.

- Backend compiles with `python -m compileall backend`.
- Full pytest suite passes with `pytest -q`.
- Frontend installs and builds with `npm install` and `npm run build`.
- Health endpoints return safe 200 responses: `/api/health`, `/api/health/live`, `/api/health/ready`.
- `/api/system/status` returns operational metadata without secrets.
- `/openapi.json` loads and includes the implemented QuoteOps API surface.
- Core quote flow works: quote preview, candidate prices, price validation, approval request, and human review.
- Audit logs are created after major workflow actions.
- Dashboard summary and dashboard insights load with viewer access.
- HTML reports generate deterministic escaped content.
- Demo status and demo guide load safely; demo reset is not part of final regression execution.
- `python scripts/security_check.py` passes.
- `python scripts/final_regression_check.py` passes.
- Risky generated files are not tracked: `.env`, database files, `frontend/dist`, `frontend/node_modules`, `__pycache__`, or `.pyc`.
- Render config remains a configuration sanity check only; do not deploy from this checklist.
- Deployment docs and `.env.example` use placeholders only.

Final regression does not approve production prices, activate price tables, scrape websites, send email, run production migrations, create release tags, or deploy services.
