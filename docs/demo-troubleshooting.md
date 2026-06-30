# Demo Troubleshooting

Use these safe checks during local or portfolio demos. Do not paste real credentials, tokens, or database URLs into tickets, slides, or screenshots.

## Backend Not Reachable

- Check that the FastAPI process is running.
- Confirm the backend port matches the frontend API base URL.
- Open `/api/health` directly in the browser.
- Restart the backend if the local process stopped.

## Frontend Cannot Call API

- Check `VITE_API_BASE_URL`.
- Confirm the backend URL includes the correct protocol and port.
- Refresh the browser after changing frontend environment variables.
- Use the browser network tab to confirm which URL is failing, without exposing secrets.

## CORS Issue

- Check `QUOTEOPS_CORS_ORIGINS`.
- Include the local frontend origin, such as the Vite dev URL.
- Restart the backend after changing CORS configuration.
- Do not use wildcard origins for a production-like demo unless intentionally showing local-only behavior.

## Database Not Initialized

- Run the backend startup path that creates local tables.
- Check `/api/health/ready`.
- Use a local SQLite database for demos.
- Do not connect the demo to a production database.

## Demo Data Missing

- Sign in as an admin demo user.
- Open Demo Tools and click Seed demo data.
- Refresh Demo status and confirm products, competitors, and scenario counts.
- If data still looks wrong, restart with a clean local demo database.

## Auth Role Issue

- Use admin for demo seed/reset and manager/admin for approval-style actions.
- Use viewer for read-only dashboard and demo guide checks.
- Sign out and sign back in if the token belongs to the wrong role.
- Do not display real credentials; only use documented demo accounts.

## Render Cold Start

- Open the backend health endpoint and wait for the service to wake.
- Retry the frontend after the backend responds.
- Explain that free or low-traffic services may need a short warm-up.
- Do not claim a production uptime guarantee.

## Wrong VITE_API_BASE_URL

- Compare the configured frontend API URL with the backend URL being shown.
- Rebuild or restart the frontend after changing the variable.
- For local demos, prefer a local backend URL.
- Do not commit real hosted URLs unless they are intentionally public project configuration.

## Health Ready Fails

- Check system status and backend logs locally.
- Confirm the database file is writable and migrations/table creation ran.
- Verify required local environment placeholders are set.
- Do not show raw tracebacks, secret values, or full database connection strings.
