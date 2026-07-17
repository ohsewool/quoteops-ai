# V2-04 Gap Log

No known mandatory V2-04 gaps remain after verification.

## Verified V2-04A scope

- Persistent Quote, current QuoteLine, immutable QuoteRevision, and immutable
  QuoteRevisionLine schema exists only in the V2 test database so far.
- Request lineage, creator/assignee foreign keys, quote number uniqueness,
  KRW `NUMERIC(18,2)` storage, timestamps, enum values, and business checks
  are covered by real PostgreSQL inspection.
- Revision header and line snapshots are database-immutable through dedicated
  triggers, while current draft lines remain separate mutable working data.
- Destructive downgrade/re-upgrade checks ran only against the V2 test
  database.

## Verified V2-04B scope

- A reviewing customer request converts to an atomic persisted draft Quote and
  revision 1 only for manager/admin, then becomes quoted in the same database
  transaction.
- Quote worklist/detail, draft metadata update, atomic current-line
  replacement, revision list/detail, pagination/filtering, role errors, stale
  version conflicts, Decimal wire values, audit events, and OpenAPI paths are
  covered by real PostgreSQL integration tests.
- No pricing candidate, pricing check, approval, report, AI action, or price
  table activation has been added.

## Verified V2-04C and parent scope

- The authenticated Quote worklist and detail workspace are backed by the
  persisted V2-04 APIs, with real loading, empty, safe-error, filtering, and
  read-only Viewer states.
- Managers/admins can convert a reviewing request through the atomic Quote API,
  then update draft metadata or replace complete ordered lines using the
  server-provided optimistic version. Stale line edits remain visible after a
  conflict.
- The browser does not generate prices, totals, candidates, validation,
  approvals, reports, or AI output. Money is sent as exact strings and totals
  are rendered from deterministic server responses.
- The application database was forward-migrated to V2-04 head without a
  downgrade. The V2 test database remains the only destructive migration-test
  target and is also at V2-04 head.
- The root `.env` is ignored and untracked; no V1 file, branch, database,
  remote, deployment, or rescue branch was touched.

## Manual visual evidence

Browser/Playwright capability is unavailable in this local execution
environment. This is recorded for V2-10B manual review and is not claimed as a
visual pass.
