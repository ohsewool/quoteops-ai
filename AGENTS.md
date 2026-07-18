# QuoteOps AI V2 Guardrails

## Scope

This repository is the clean V2 implementation. The V1 repository is read-only evidence. Do not copy V1 frontend structure, `App.jsx`, `activeSection`, source-placement tests, the full backend, or the full API/test surface.

## Product and security invariants

- Implement Tier A core workflow first: Customer Request -> Quote -> Pricing Check -> Approval/Reject -> Report.
- Keep all numbers, validation, approval, and state transitions deterministic and human-controlled.
- Use KRW with Python `Decimal`, PostgreSQL `NUMERIC(18,2)` for money, `NUMERIC(9,6)` for rates, and `ROUND_HALF_UP` snapshot boundaries.
- No anonymous business write, optional-auth mutation, automatic price activation, or frontend-only authorization.
- Viewer sees safe summaries only, never raw cost profiles/components/CSV/configuration.
- Normal requester self-approval is forbidden. Any non-production demo exception needs an explicit audit event.
- AI is contextual, grounded, and text-only. It cannot change numeric values or workflow state and must not block the deterministic core.

## Development rules

- Work one V2 subphase at a time and record its implementation report and gap log.
- Use Alembic for every V2 schema change. Do not call `Base.metadata.create_all()` on startup.
- Do not use SQLite as evidence for PostgreSQL integration verification.
- Do not connect to V1, production, shared, or unverified databases.
- Do not use Docker, Docker Compose, TypeScript, Tailwind, Redux, microservices, or a new deployment platform.
- Keep dependencies minimal and pinned. Never expose secrets in code, docs, logs, API responses, or frontend variables.
- Create local checkpoint commits only after a subphase is verified. Do not push or add a remote.
