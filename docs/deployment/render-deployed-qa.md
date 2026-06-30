# Render Deployed QA

This guide adds deployed QA support only. It does not deploy anything, create services, run production migrations, or create release tags.

Deploy the backend and frontend in Render using the prepared backend and frontend deployment docs first:

- `docs/deployment/render-backend.md`
- `docs/deployment/render-frontend.md`

## Render Environment Variables

Set backend environment variables in Render:

```text
DATABASE_URL=sqlite:///./quoteops.db
QUOTEOPS_AUTH_SECRET=change-me-in-production
QUOTEOPS_ENV=production
QUOTEOPS_CORS_ORIGINS=https://YOUR-FRONTEND-URL.onrender.com
QUOTEOPS_DEMO_TOOLS_ENABLED=false
```

Use `QUOTEOPS_DEMO_TOOLS_ENABLED=true` only for an intentional demo deployment.

Set frontend environment variables in Render:

```text
VITE_API_BASE_URL=https://YOUR-BACKEND-URL.onrender.com
```

## Run Deployed QA

Linux/macOS:

```bash
QUOTEOPS_DEPLOYED_BACKEND_URL=https://YOUR-BACKEND-URL.onrender.com \
QUOTEOPS_DEPLOYED_FRONTEND_URL=https://YOUR-FRONTEND-URL.onrender.com \
python scripts/render_deployed_qa.py
```

Windows PowerShell:

```powershell
$env:QUOTEOPS_DEPLOYED_BACKEND_URL="https://YOUR-BACKEND-URL.onrender.com"
$env:QUOTEOPS_DEPLOYED_FRONTEND_URL="https://YOUR-FRONTEND-URL.onrender.com"
python scripts/render_deployed_qa.py
```

If either URL is missing, the script skips that deployed check and exits successfully for normal local CI.

## Expected Checks

- Backend health endpoints return 200.
- Backend readiness returns 200 after the database is configured.
- OpenAPI loads and contains paths.
- System status hides secrets and raw database URLs.
- Dashboard insights, demo status, and demo guide are either reachable or safely auth-protected.
- Frontend root returns 200 and looks like the app shell.
- CORS from frontend to backend reports the `access-control-allow-origin` header value.

## Common Failures

- Backend is sleeping or cold starting.
- `DATABASE_URL` is missing or incorrect.
- `QUOTEOPS_AUTH_SECRET` is missing.
- `QUOTEOPS_CORS_ORIGINS` does not match the deployed frontend origin.
- `VITE_API_BASE_URL` points to the wrong backend.
- Frontend was not redeployed after changing environment variables.

Do not put real credentials, API keys, database URLs, auth secrets, or private Render values in this repository.
