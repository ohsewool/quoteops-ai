# V2-03 Implementation Report

| Subphase | Scope | Commit | Tests | Independent review | Verdict |
|---|---|---|---|---|---|
| V2-03A | Customer-request persistence, API, audit trail, roles, state machine, and PostgreSQL migration | `2d69dd8` | PostgreSQL API/schema target: 4 passed. Full backend: 27 passed. Frontend regression: 8 passed; production build passed. | Request intake is authenticated, manager/admin mutation is enforced server-side, viewer access is read-only, PostgreSQL enum values match the migration, audit metadata avoids customer notes, and V2-04-only quote conversion is not advertised as a direct action. | V2-03A VERIFIED |
| V2-03B | Customer-request workspace UI | `3485424` | Frontend target: 4 passed. Frontend regression: 12 passed; production build passed. Backend regression: 27 passed. | Real API paths drive list/detail/create/edit/transition states; viewers have no mutation actions; stale detail responses are ignored; V2-04 Quote conversion is shown only as a dependency. | V2-03B VERIFIED |

## Parent phase result

V2-03 VERIFIED.

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

The application database remained at the completed V2-01 revision during this
subphase. Its forward-only V2-03 activation is documented below; no
application-database downgrade was run.

## V2-03B delivery

The workspace now serves authenticated, persisted customer-request data at:

```text
/app/requests
/app/requests/new
/app/requests/{customer_request_id}
```

The list includes real empty, loading, safe-error, status-filter, and
customer-name search states. Managers and admins can create, edit using the
current optimistic-lock version, and execute only transitions returned by the
backend. Viewers see the list/detail as read-only and never receive mutation
controls. The detail view renders audit events without exposing tokens or
secrets and ignores stale asynchronous responses after navigation.

No Quote, price, approval, report, AI output, seeded customer, or fabricated
business metric was added. A reviewing request names V2-04 as the owner of the
atomic persisted-Quote conversion and offers no direct quoted action.

The Vitest configuration now serializes files and performs central DOM cleanup
because tests intentionally share browser-like storage and `fetch` mocks in a
single local JSDOM worker.

## Application database activation

Before activation, the configured application and test database names matched
their approved V2 names and the parsed URLs were confirmed distinct without
printing either URL. The application database was at
`0001_security_foundation`, had no `customer_requests` table, and contained
only V2-01 tables. `alembic upgrade head` then applied
`0002_customer_request_domain` forward only.

```text
application_database_name_matches_expected=True
test_database_name_matches_expected=True
database_urls_distinct=True
application_pre_upgrade_revision=0001_security_foundation
application_pre_upgrade_customer_requests_absent=True
application_pre_upgrade_v2_01_tables_only=True
application_post_upgrade_revision_is_v2_03_head=True
application_post_upgrade_tables_approved_only=True
application_customer_request_constraints_present=True
application_customer_request_enums_present=True
application_startup_user_count=0
application_startup_customer_request_count=0
application_readiness_status=200
test_database_revision_is_v2_03_head=True
```

No application-database downgrade was run. Destructive migration-cycle checks
remain isolated to the V2 test database.

## Exact verification results

```text
python -m compileall backend alembic: completed successfully
python -m pip check: No broken requirements found.
V2-03A PostgreSQL API/schema target: 4 passed in 86.76s
V2-03A backend regression: 27 passed in 110.96s (0:01:50)
V2-03B frontend target: 4 passed
V2-03 parent backend regression: 27 passed in 82.40s (0:01:22)
V2-03 parent frontend regression: 12 passed
V2-03 parent Vite production build: 43 modules transformed; built in 3.70s
```

No public intake, fabricated Quote, approval action, price calculation, AI
recommendation, seeded account, or V1 modification was introduced. V1 remained
on `pr-48-cpq-workflow-app-shell-restructure` with its pre-existing
`?? docs/v2/` item. Browser visual verification remains unavailable in this
local environment and is reserved for the documented V2-10B manual-review
evidence.
