# V2-01B Test Strategy

Local non-database verification covers:

- typed configuration and environment policy
- exact Decimal rounding and float rejection
- password hash and expiring bearer-token behavior
- audit metadata sanitization
- API route, role, 401/403/422/503, correlation-ID, docs/OpenAPI policy
- no implicit schema creation
- offline Alembic upgrade and downgrade rendering
- dependency integrity, frontend foundation test, and production build

The PostgreSQL integration test is intentionally marked `postgresql` and skips unless `QUOTEOPS_POSTGRES_INTEGRATION=1`. A skip is recorded as an incomplete mandatory gate, never as PostgreSQL success.

GitHub Actions is configured with an ephemeral PostgreSQL 16 service and temporary CI-only credentials. It runs `alembic upgrade head`, `alembic current`, and the full backend suite with the integration marker enabled after this repository is pushed by a human-approved future action.
