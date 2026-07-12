# V2-01B Security Baseline

Implemented foundation controls:

- No anonymous business mutation route exists.
- No optional-authentication mutation route exists.
- No startup seed, demo user, demo route, or automatic administrator exists.
- Only the explicit first-user CLI can create the initial administrator after a V2-only PostgreSQL database and configured auth secret exist.
- Passwords use Argon2 through `pwdlib`; bearer tokens are signed, issuer-bound, and expiring.
- Authentication resolves the active user from persistent storage rather than trusting a role claim alone.
- Admin-only system status returns only a safe configuration summary.
- Staging and production reject demo mode, wildcard CORS, enabled docs/OpenAPI, and missing/placeholder auth secrets.
- Every API response receives an `X-Request-ID`; API errors include the same request ID.
- Audit metadata has recursive key-based redaction for token, password, secret, API key, private key, authorization, and database URL fields.
- Runtime source does not call `Base.metadata.create_all()`.

Not yet verified against a real PostgreSQL target:

- Initial Alembic upgrade/downgrade/re-upgrade execution.
- `users` and `audit_events` constraints in PostgreSQL.
- Readiness behavior using a live V2-only database.
- Concurrent database behavior.

Those items remain blockers for V2-01B verification, not accepted risks.
