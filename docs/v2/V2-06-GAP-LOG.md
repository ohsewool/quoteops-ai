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
  success and one `409` terminal-state result.
- The V2 test database alone was used for integration verification. V1 remains
  unchanged. The ignored root `.env` remains ignored and untracked.

## Pending V2-06B scope, not a V2-06A backend gap

- Approval Inbox list/detail/timeline and real review controls remain for the
  approved V2-06B frontend subphase.
- Browser/Playwright visual evidence remains a V2-10B manual-review gate; it
  is not claimed by V2-06A.

No known mandatory V2-06A backend gaps remain after verification.
