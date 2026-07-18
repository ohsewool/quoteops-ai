# V2-06 Gap Log

## V2-06A verified scope

- Approval request persistence links Quote, immutable source revision, pricing
  check, selected candidate, requester, revalidated eligibility, and safe
  candidate aggregates.
- Submission re-runs deterministic Decimal validation from immutable source
  snapshots and blocks any evidence mismatch.
- Manager/admin writes and Viewer reads are backend-enforced. Reviewer identity
  comes only from the authenticated actor; normal-mode self-approval returns
  `403`.
- `failed/high` submissions return `409`; `warning/medium` submissions require
  a written reason with `422`; no administrator override exists.
- A pending request transitions exactly once to approved or rejected. The
  terminal decision, terminal audit, and source evidence are database-guarded
  against mutation or deletion.
- Rejection preserves the rejected revision and opens a distinct current draft
  revision for new pricing work. Approval does not activate a price table.
- Two simultaneous reviewers are covered by a PostgreSQL race test with one
  success and one `409` terminal-state result. Explicit local demo mode is
  separately tested for the visible self-approval flag and audit event.
- The V2 test database alone was used for integration verification. V1 remains
  unchanged. The ignored root `.env` remains ignored and untracked.

## V2-06B verified scope

- `/app/approvals` is an actual authenticated Inbox with API-backed list,
  detail, safe evidence summary, request/decision timeline, and Quote link.
- Managers/admins can submit a current selected Pricing Check from the Pricing
  workspace and decide a different requester's pending approval using the
  persisted server version. Viewer remains read-only.
- The browser does not calculate candidate values, choose reviewer identity,
  bypass warning reasons, or expose raw cost/profile fields. Terminal decisions
  remove UI controls and stale/conflict errors are surfaced safely.
- Focused frontend tests, frontend regression, and the production build passed.

## Verified V2-06 parent activation

- The application database was forward-migrated once from V2-05 to
  `0005_approval_domain`; it now has exactly the approved V2-01 through V2-06
  table set, required approval constraints/triggers, and healthy JSON
  readiness.
- The distinct V2 test database alone was downgraded to V2-05, shown to have
  no approval tables or enum, then re-upgraded to V2-06 head before final
  integration regression.
- Final backend regression, frontend regression, and production build passed.
- Root `.env` remains ignored and untracked; no risky generated/secrets/database
  artifacts are tracked. V1's tracked diff remains empty; its pre-existing
  untracked `docs/v2/` directory was not changed.
- Browser/Playwright visual evidence remains a V2-10B manual-review gate; it
  is not claimed by V2-06.

No known mandatory V2-06 gaps remain after verification.
