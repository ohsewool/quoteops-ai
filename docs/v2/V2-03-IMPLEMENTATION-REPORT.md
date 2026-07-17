# V2-03 Implementation Report

| Subphase | Scope | Commit | Tests | Independent review | Verdict |
|---|---|---|---|---|---|
| V2-03A | Customer-request persistence, API, audit trail, roles, state machine, and PostgreSQL migration | `2d69dd8` | PostgreSQL API/schema target: 4 passed. Full backend: 27 passed. Frontend regression: 8 passed; production build passed. | Request intake is authenticated, manager/admin mutation is enforced server-side, viewer access is read-only, PostgreSQL enum values match the migration, audit metadata avoids customer notes, and V2-04-only quote conversion is not advertised as a direct action. | V2-03A VERIFIED |
| V2-03B | Customer-request workspace UI | Pending | Not started | Not started | Pending |

## V2-03A delivery

V2-03A adds the persisted `customer_requests` workflow for only the approved
V2 product codes: `a3_flyer` and `brand_sticker`. It includes identity,
contact name, product code, quantity, optional due date and notes, responsible
assignment, status, version, timestamps, creator, and audit traceability.

The deterministic request state machine is:

```text
new -> reviewing -> quoted -> closed
new/reviewing/quoted -> cancelled
```

The transition to `quoted` remains blocked from the V2-03 API until V2-04 can
atomically persist a real Quote and its line items. A reviewing request exposes
`ready_for_quote_conversion=true`, but it does not advertise an executable
direct `quoted` transition.

## API and integrity evidence

- Authenticated read endpoints: list, detail, and request audit events.
- Manager/admin mutation endpoints: create, versioned edit, and versioned
  state transition.
- Viewer writes and anonymous request access return safe authorization errors.
- Pagination, status/product/assignee filtering, customer-name search, stale
  version conflicts, unknown request behavior, and invalid quantity validation
  are covered.
- Migration `0002_customer_request_domain` creates PostgreSQL enum types,
  foreign keys, positive quantity/version checks, and list/filter indexes.
- The V2-01 `User.role` ORM enum mapping was aligned with the existing
  lowercase PostgreSQL enum values after a real database integration finding.
  This is a compatibility remediation, not a V1 change.

## PostgreSQL migration evidence

All destructive V2-03 migration verification ran only against the configured
V2 test database. The test database upgraded to `0002_customer_request_domain`,
the table/enums/constraints/indexes were inspected, it was downgraded to the
V2-01 revision and confirmed clean of V2-03 schema, then re-upgraded to head.

```text
v2_03_test_downgrade=OK
v2_03_test_downgrade_schema_clean=True
v2_03_test_reupgrade=OK
postgresql_schema_contract=1 passed in 18.92s
postgresql_api_schema_target=4 passed in 86.76s
```

The application database remains at the completed V2-01 revision during this
subphase. Its forward-only V2-03 activation is deliberately deferred until
V2-03B and parent-phase verification; no application-database downgrade was
run.

## Exact verification results

```text
python -m compileall backend alembic: completed successfully
python -m pip check: No broken requirements found.
pytest -q backend/tests: 27 passed in 110.96s (0:01:50)
Frontend Vitest: 8 passed
Frontend Vite production build: 41 modules transformed; built in 3.31s
```

No public intake, fabricated Quote, approval action, price calculation, AI
recommendation, seeded account, or V1 modification was introduced. Browser
visual verification remains unavailable in this local environment and is
reserved for the documented V2-10B manual-review evidence.
