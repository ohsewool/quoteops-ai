# V2-04 Implementation Report

| Subphase | Scope | Commit | Tests | Independent review | Verdict |
|---|---|---|---|---|---|
| V2-04A | Persistent Quote, QuoteLine, immutable revision snapshots, PostgreSQL migration | `69a1387` | Domain/schema target: 3 passed. Full backend: 30 passed. | KRW Numeric types, request lineage, lower-case PostgreSQL enum values, positive snapshot quantities, FK/check/unique constraints, and database-enforced revision immutability were reviewed. | V2-04A VERIFIED |
| V2-04B | Quote conversion, draft, line, revision APIs | `5d2739d` | PostgreSQL API target: 3 passed. Full backend: 33 passed. | Request-to-Quote conversion is transactionally coupled to the request state; Decimal strings, atomic line replacement, revisions, roles, stale versions, audit metadata, and OpenAPI routes were reviewed. | V2-04B VERIFIED |
| V2-04C | Quote list and workspace UI | `805b482` | Frontend target: 9 passed. Frontend regression: 17 passed; production build passed. Backend regression: 33 passed. | Actual request-to-Quote conversion, list/detail API use, manager-only draft edits, Viewer read-only controls, exact money strings, stale-version preservation, responsive CSS, and no client-side pricing calculation were reviewed. | V2-04C VERIFIED |

## Parent phase result

V2-04 VERIFIED.

## V2-04A delivery

Migration `0003_quote_domain` adds four PostgreSQL tables:

```text
quotes
quote_lines
quote_revisions
quote_revision_lines
```

The Quote holds the request lineage, customer/request snapshot, one of the
contractual Quote statuses, currency, current deterministic total, formula and
rounding policy versions, assignee, creator, optimistic version, and current
revision number. Current quote lines remain mutable draft working data; each
immutable revision copies complete header and line snapshots for reproducible
history.

All monetary fields are PostgreSQL-compatible `NUMERIC(18,2)`, all stored
currency values are constrained to `KRW`, and quantities/positions/versions are
checked at the database boundary. `quote_revisions` and
`quote_revision_lines` have PostgreSQL triggers that reject update or delete
attempts. No Quote API, pricing calculation, approval, AI behavior, automatic
activation, or V1 change is included in this subphase.

## PostgreSQL evidence

The V2 test database upgraded to `0003_quote_domain`, was downgraded to
`0002_customer_request_domain`, verified clear of all Quote tables and the
`quote_status` enum, then re-upgraded to V2-04A head. This destructive cycle
ran only on the test database.

```text
v2_04_test_downgrade_revision_is_0002=True
v2_04_test_quote_tables_absent_after_downgrade=True
v2_04_test_quote_status_absent_after_downgrade=True
v2_04_test_reupgrade=OK
quote_domain_schema_target=3 passed in 17.36s
backend_regression=30 passed in 92.69s (0:01:32)
```

The application database remains at V2-03 head during V2-04A. Its forward-only
V2-04 activation is deferred to parent-phase verification after V2-04B and
V2-04C. No application-database downgrade was run.

## Exact verification results

```text
python -m compileall backend alembic: completed successfully
pytest -q backend/tests/test_quote_domain.py backend/tests/test_quote_postgresql_schema.py: 3 passed in 17.36s
pytest -q backend/tests: 30 passed in 92.69s (0:01:32)
```

Browser visual verification is not claimed in this local environment and
remains a V2-10B manual-review item.

## V2-04B delivery

The authenticated Tier A Quote contract is now available:

```text
POST /api/customer-quote-requests/{customer_request_id}/quotes
GET  /api/quotes
GET  /api/quotes/{quote_id}
PATCH /api/quotes/{quote_id}
PUT  /api/quotes/{quote_id}/lines
GET  /api/quotes/{quote_id}/revisions
GET  /api/quote-revisions/{revision_id}
```

Only a manager/admin can atomically convert a `reviewing` customer request
with its current request version. The conversion persists a draft Quote, an
empty immutable revision 1, a request snapshot, and the request transition to
`quoted` in one transaction. Conversion does not create a price candidate,
approval, report, or price-table activation.

Draft metadata and complete ordered line replacement use the Quote optimistic
version. Each successful mutation increments the Quote version and revision,
recalculates the deterministic line-sum total using Decimal half-up rounding,
and writes a new immutable revision snapshot. Money is accepted only as exact
JSON decimal strings and returned as canonical decimal strings. Viewer reads
are allowed but all mutations remain backend-enforced manager/admin actions.

```text
quote_api_postgresql_target=3 passed in 102.30s (0:01:42)
full_backend_regression=33 passed in 179.98s (0:02:59)
```

Audit events use `quote.created`, `quote.lines_replaced`, and
`quote.draft_updated` with IDs, versions, status, line count, and total only;
customer names, notes, tokens, and secrets are excluded from metadata.

## V2-04C delivery

The V2-02 planned Quote page is replaced with API-backed routes:

```text
/app/quotes
/app/quotes/{quote_id}
```

The worklist uses the persisted Quote API with actual loading, safe-error,
empty, customer-name search, and status-filter states. A manager or admin is
routed back to a reviewing customer request to make a Quote; no standalone or
fabricated Quote is created in the browser. Viewer access remains read-only.

The customer-request detail now calls the atomic V2-04 conversion endpoint
with the current request version and opens the persisted Quote route on
success. It never directly sends a `quoted` request transition.

The Quote workspace renders request lineage, deterministic server-calculated
totals, current lines, and immutable revision summaries. Managers and admins
can edit draft metadata and atomically replace ordered draft lines using the
current Quote version. Wire money remains an exact decimal string; the browser
only formats the server response for display and does not calculate a price or
total. A stale-version response keeps the user's draft lines visible for a
safe retry. Pricing review remains a future V2-05 route and is linked only
when the Quote is still a draft with saved lines.

The responsive layout uses unframed workspace bands and tables rather than
inventing dashboard data. V2-02's old planned-page regression test now asserts
the actual authenticated Quote list API path instead.

```text
V2-04C frontend target=9 passed in 11.71s
V2-04C frontend regression=17 passed in 15.41s
V2-04C Vite production build=45 modules transformed; built in 3.61s
V2-04 parent backend regression=33 passed in 184.45s (0:03:04)
```

## Application database activation

Before activation, the configured application and test database names matched
their approved V2 names and the parsed database names were distinct without
printing either URL. The application database was at
`0002_customer_request_domain` and its tables matched only V2-01 through
V2-03. `alembic upgrade head` then applied `0003_quote_domain` forward only.

```text
application_database_name=quoteops_ai_v2
test_database_name=quoteops_ai_v2_test
database_names_distinct=True
application_alembic_revision_before=0002_customer_request_domain
application_tables_match_v2_03=True
application_alembic_revision=0003_quote_domain
application_tables_match_v2_04=True
application_quote_constraints_present=True
application_quote_revision_triggers_match=True
application_quote_status_values_match=True
test_alembic_revision=0003_quote_domain
application_readiness_status=200
application_readiness_is_json=True
```

No application-database downgrade was run. Destructive migration cycles remain
limited to the configured V2 test database.

## Parent verification result

```text
python -m compileall backend: completed successfully
pytest -q backend/tests: 33 passed in 184.45s (0:03:04)
frontend Vitest: 17 passed in 15.41s
frontend Vite production build: 45 modules transformed; built in 3.61s
```

No candidate price, pricing validation, approval request, report, AI action,
automatic activation, seed account, or V1 modification was introduced. The
root `.env` remains ignored and untracked. V1 remained on
`pr-48-cpq-workflow-app-shell-restructure` with its pre-existing
`?? docs/v2/` item. Browser visual verification remains unavailable in this
local environment and is reserved for V2-10B manual review.
