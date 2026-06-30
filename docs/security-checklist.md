# Security Checklist

QuoteOps AI uses deterministic pricing workflows and human approval boundaries. This checklist covers the project security basics expected before regression and release work.

## Secrets

- Do not commit `.env` or `.env.local`.
- Do not commit database files such as `quoteops.db`, `*.db`, `*.sqlite`, or `*.sqlite3`.
- Set `DATABASE_URL`, `QUOTEOPS_AUTH_SECRET`, and optional `OPENAI_API_KEY` in Render environment variables.
- Use a production-specific `QUOTEOPS_AUTH_SECRET`; do not use `change-me-in-production` outside local development.
- Never place backend secrets in `VITE_*` frontend variables.

## CORS

- Set `QUOTEOPS_CORS_ORIGINS` to the deployed frontend URL, for example `https://YOUR-FRONTEND-URL.onrender.com`.
- Do not use wildcard CORS in production.
- Local defaults may include localhost frontend origins for development only.

## Runtime Safety

- Health and system status endpoints must not expose raw environment variables, database URLs, passwords, tokens, private keys, or tracebacks.
- HTML reports must escape user-provided text before rendering.
- Demo reset must only target known deterministic demo data and must not delete unknown products, customers, users, price tables, approval requests, auth secrets, or environment variables.

## Pricing Boundary

- Human approval is required before pricing use.
- Demo tools, reports, and simulations do not approve, reject, activate, scrape, email, or deploy anything.
