# Render Backend Deployment

This guide covers backend deployment preparation only. Frontend deployment is handled in a later PR.

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

Optional values:

- `ALLOWED_ORIGINS`: comma-separated frontend origins when the frontend is deployed later.
- `OPENAI_API_KEY`: only if explanation features are configured to use an external provider.

## PostgreSQL

Use a Render PostgreSQL database or an equivalent managed PostgreSQL instance. QuoteOps AI supports PostgreSQL URLs through the `DATABASE_URL` environment variable and masks database credentials in status responses.

Do not commit real PostgreSQL URLs, passwords, API keys, auth secrets, local SQLite files, or Render credentials.

## Safety notes

- This PR does not deploy anything manually.
- This PR does not configure frontend deployment.
- This PR does not add migrations, custom domains, release tags, schedulers, emails, or production monitoring.
- `/api/health` is unauthenticated and safe for Render health checks.
- `/api/system/status` must not expose raw database passwords or secrets.
