# V2-01B API Contract

Only the following foundation operations exist in V2-01B.

| Method and path | Access | Contract |
|---|---|---|
| `GET /api/health` | public | Process-safe health response; no database URL, secret, or diagnostic detail. |
| `GET /api/health/live` | public | Process liveness response. |
| `GET /api/health/ready` | public | Executes `SELECT 1`; returns 503 with the common error body when PostgreSQL is unavailable. |
| `POST /api/auth/login` | public authentication only | Issues an expiring bearer token for a valid active user. It is not a business mutation. |
| `GET /api/auth/me` | authenticated active user | Returns the authenticated user's safe identity and role. |
| `GET /api/system/status` | admin only | Returns a secret-safe environment summary. |

No customer request, quote, pricing, approval, report, demo, seed, CSV, or Tier B route exists in this subphase.

Errors use this additive response shape:

```json
{
  "detail": "Human-readable summary",
  "code": "stable_machine_code",
  "field_errors": [],
  "request_id": "correlation-id"
}
```

Staging and production disable `/docs`, `/redoc`, and `/openapi.json`. Local/test documentation behavior is explicitly controlled by configuration.
