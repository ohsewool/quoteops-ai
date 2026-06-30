# Deployment Notes

QuoteOps AI is prepared for Render deployment, but this repository does not perform deployment automatically.

## Local Development

```bash
uvicorn backend.main:app --reload
cd frontend
npm run dev
```

Local backend defaults to SQLite through `DATABASE_URL=sqlite:///./quoteops.db`. Local frontend defaults to `http://127.0.0.1:8000` through `VITE_API_BASE_URL`.

## Render Backend

Use a Render Web Service for the FastAPI backend.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/health`

Set secrets and environment variables in the Render dashboard, not in committed files.

## Render Frontend

Use a Render Static Site for the Vite frontend.

- Build command: `cd frontend && npm install && npm run build`
- Publish directory: `frontend/dist`
- Set `VITE_API_BASE_URL` to the deployed backend URL.

## Environment Variables

- `DATABASE_URL`
- `QUOTEOPS_ENV`
- `QUOTEOPS_AUTH_SECRET`
- `QUOTEOPS_DEMO_TOOLS_ENABLED`
- `QUOTEOPS_CORS_ORIGINS`
- `VITE_API_BASE_URL`

Do not commit `.env`, database files, API keys, Render credentials, or auth secrets.

## Smoke Checks

- `/api/health`
- `/api/health/live`
- `/api/health/ready`
- `/api/system/status`
- `/openapi.json`

Frontend deployment should be checked by loading the app and confirming the System Status cards can reach the backend.
