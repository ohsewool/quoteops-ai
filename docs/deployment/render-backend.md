# Render Backend Deployment

This guide covers backend deployment preparation. Frontend deployment preparation is documented in `docs/deployment/render-frontend.md`.

## Backend service

Create a Render Web Service for the FastAPI backend.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/health`
- Runtime: Python

## Environment variables

Set environment variables in Render. Do not commit `.env` files or real credentials.

Required production values:

- `DATABASE_URL`: use a Render PostgreSQL database URL from Render environment variables.
- `QUOTEOPS_AUTH_SECRET`: set a secret value in Render.
- `QUOTEOPS_ENV`: set to `production`.
- `QUOTEOPS_DEMO_TOOLS_ENABLED`: set to `false` for production-like deployments.
- `QUOTEOPS_CORS_ORIGINS`: set to the deployed frontend origin, such as `https://YOUR-FRONTEND-URL.onrender.com`.

Optional values:

- `OPENAI_API_KEY`: only if explanation features are configured to use an external provider.

## CORS and frontend API URL

Local development defaults allow Vite and React dev server origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:3000`
- `http://127.0.0.1:3000`

For Render, configure `QUOTEOPS_CORS_ORIGINS` on the backend with the frontend URL, for example `https://YOUR-FRONTEND-URL.onrender.com`. Do not use wildcard CORS in production.

Set `VITE_API_BASE_URL` on the frontend to the backend URL, for example `https://YOUR-BACKEND-URL.onrender.com`. Keep these as Render dashboard environment variables; do not commit `.env` files or real Render credentials.

## PostgreSQL

Use a Render PostgreSQL database or an equivalent managed PostgreSQL instance. QuoteOps AI supports PostgreSQL URLs through the `DATABASE_URL` environment variable and masks database credentials in status responses.

Do not commit real PostgreSQL URLs, passwords, API keys, auth secrets, local SQLite files, or Render credentials.

## Safety notes

- This PR does not deploy anything manually.
- This PR does not add migrations, custom domains, release tags, schedulers, emails, or production monitoring.
- `/api/health` is unauthenticated and safe for Render health checks.
- `/api/system/status` must not expose raw database passwords or secrets.
