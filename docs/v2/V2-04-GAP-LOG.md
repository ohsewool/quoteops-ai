# V2-04 Gap Log

No known mandatory V2-04B gaps remain after verification.

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

## Remaining planned work

- V2-04C must replace the V2-02 Quote placeholder with a responsive,
  accessible, API-backed list and workspace without fabricated prices or
  pricing candidates.
- Parent V2-04 activation must forward-migrate only the V2 application
  database after V2-04B/C verification.

## Manual visual evidence

Browser/Playwright capability is unavailable in this local execution
environment. This is recorded for V2-10B manual review and is not claimed as a
visual pass.
