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

## Remaining parent-phase activation

- V2-06 application-database forward migration, V2 test-database
  downgrade/re-upgrade proof, final full backend/frontend verification, and
  V1 unchanged verification remain for the V2-06 parent gate.
- Browser/Playwright visual evidence remains a V2-10B manual-review gate; it
  is not claimed by V2-06.

No known mandatory V2-06A or V2-06B implementation gaps remain after verification.
