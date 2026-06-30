# Render Frontend Deployment

This guide covers frontend deployment preparation only. It does not deploy services automatically.

## Frontend service

Create a Render Static Site for the Vite frontend.

- Build command: `cd frontend && npm install && npm run build`
- Publish directory: `frontend/dist`
- Runtime: Node.js

## Environment variables

Set frontend environment variables in Render. Do not commit `.env` files or real credentials.

Required value:

- `VITE_API_BASE_URL`: deployed backend URL, for example `https://YOUR-BACKEND-URL.onrender.com`.

## Backend CORS

The backend must allow the deployed frontend origin through `QUOTEOPS_CORS_ORIGINS`, for example:

```text
QUOTEOPS_CORS_ORIGINS=https://YOUR-FRONTEND-URL.onrender.com
```

Do not use wildcard CORS in production.

## Safety notes

- `frontend/dist` is build output and must not be committed.
- Do not put API keys, auth secrets, database credentials, or Render credentials in frontend code.
- The frontend should use `VITE_API_BASE_URL` only for the public backend URL.
