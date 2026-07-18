# V2 Foundation Architecture

V2 is a clean repository with independent source control, configuration, credentials, databases, and staging lifecycle. V1 is read-only evidence.

```text
frontend/                 React/Vite application
backend/                  FastAPI, domain services, routers, schemas, models
alembic/                  V2-only schema migrations (introduced in V2-01B)
docs/                     product contract, reports, security, migration evidence
scripts/                  local validation helpers with secret-safe output
```

The first production workflow is:

```text
Customer Request -> Quote -> Pricing Check -> Approval/Reject -> Report
```

Tier B legacy features are not part of the initial application navigation or completion gate.
