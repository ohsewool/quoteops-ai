# V2-09 Implementation Report

| Subphase | Scope | Verification | Independent review | Verdict |
|---|---|---|---|---|
| V2-09A | Restrained operations console, safe diagnostics, audit search, and isolated competitor-reference CSV adapter | Focused PostgreSQL API/schema: 4 passed; full backend: 55 passed | Role boundaries, all-or-nothing parsing, no raw-cost export, safe diagnostics, audit metadata sanitization, OpenAPI paths, and adapter isolation were reviewed. | V2-09A VERIFIED |
| V2-09B | Explicit two-product guided demo and guide-state reset | Focused PostgreSQL API/schema: 4 passed; frontend target: 10 passed; frontend regression: 30 passed; production build passed | Demo enablement, admin-only start/reset, no credentials/users at startup, exactly two MVP product codes per run, guide-only reset, and production-unavailable behavior were reviewed. | V2-09B VERIFIED |

## V2-09A delivery

The new admin Operations workspace exposes only safe, bounded controls:

```text
GET  /api/operations/diagnostics
GET  /api/operations/audit-events
POST /api/operations/competitor-references/import
GET  /api/operations/competitor-references/export
```

Diagnostics returns non-secret configuration state, a Boolean database-readiness
result, the Alembic revision, and an audit-event count. It never returns a
database URL, credential, password, token, API key, or raw connection detail.
Diagnostics and audit search are admin-only. Both operations themselves leave
sanitized audit events.

Audit search supports bounded pagination and exact action/entity/actor filters.
Returned metadata is sanitized again at the response boundary. Its own audit
telemetry records only whether each filter was supplied, not raw filter values;
an accidental secret-like search value cannot be persisted as audit metadata.

The only selected Tier B adapter is the versioned
`competitor-reference-csv-v1` adapter. It imports or exports competitor
reference data only, never cost profiles or raw cost components. The adapter
has a 200 KB input limit, an exact required header, at most 500 rows, exact
Decimal monetary parsing, timezone-aware observations, product/competitor
existence checks, active-competitor enforcement, and one transaction for the
entire import. Invalid input persists zero rows. Viewer access to both CSV
operations is denied.

### Adapter disposition

| Adapter | Owner | Evidence | Disposition |
|---|---|---|---|
| `competitor-reference-csv-v1` | Operations boundary | V2 pricing checks can consume persisted competitor references; focused PostgreSQL authorization, malformed-row rollback, import, export, and audit tests passed. | Reintroduced only as an isolated V2-09 Operations adapter. |
| Any raw-cost/profile CSV | Operations boundary | Viewer cost isolation and V2 cost-profile API boundary remain intact. | Excluded from V2. |
| V1 strategy, simulation, scenario, job, and workflow tools | Product contract Tier B exclusion | No V2 route, UI, model, or migration was added. | Excluded from V2. |

## V2-09B delivery

Migration `0009_operations_demo_domain` creates `demo_runs`, a V2-only
guide-state table with an owner FK, a bounded current step, a positive
concurrency version, and a `ready`/`in_progress`/`complete` status enum.

The admin-only guided-demo API is:

```text
GET  /api/demo/runs
POST /api/demo/runs
GET  /api/demo/runs/{demo_run_id}
POST /api/demo/runs/{demo_run_id}/advance
POST /api/demo/runs/{demo_run_id}/reset
```

The API is unavailable unless the existing non-production `demo_enabled`
setting is explicitly enabled; production-like settings also return the safe
unavailable response. It is not a startup seed and it creates no user,
credential, token, or password. An explicit start creates or reuses only the
two MVP source products, supplies an active V2 cost profile only when one is
missing, and creates exactly two guide requests: A3 Flyer and Product / Brand
Sticker. The response exposes the fixed two-product code list and their
persisted IDs as safe guide artifacts.

Advancing changes only the guide position with optimistic concurrency. Reset
changes only that guide position/status and preserves every seeded request,
Quote, pricing check, approval, report, and unrelated business record. Each
start, advance, reset, and explicit fixture artifact writes a sanitized audit
event. The UI renders a compact guide with persisted status, next deep link,
and a clearly labelled guide-state reset; it never supplies a credential,
calculates a price, or deletes workflow data.

## V2-09 verification

```text
python -m compileall backend alembic: completed successfully
git diff --check: completed successfully
focused operations PostgreSQL API/schema after final exact-two-product check: 4 passed in 98.47s (0:01:38)
test downgrade: 0009_operations_demo_domain -> 0008_copilot_context_guard
test_demo_runs_absent_after_downgrade=True
test_demo_run_status_absent_after_downgrade=True
test re-upgrade revision=0009_operations_demo_domain
test_demo_runs_present_after_reupgrade=True
test_demo_run_constraints_complete=True
backend regression after final V2-09 review: 55 passed in 931.85s (0:15:31)
frontend V2-09 target: 10 passed in 10.76s
frontend regression: 30 passed in 15.84s
frontend production build: 57 modules transformed; built in 1.69s
V2 security gates: 13 passed in 4.79s
```

The migration recovery proof ran only on the V2 test database. The application
database was checked at `0008_copilot_context_guard`, then forward-migrated
once to `0009_operations_demo_domain`; it was never downgraded.

```text
application_database_name_confirmed=True
test_database_name_confirmed=True
database_names_distinct=True
application_revision_after_v2_09=0009_operations_demo_domain
application_tables_match_v2_09=True
application_demo_run_constraints_complete=True
application_readiness_status=200
application_readiness_is_json=True
application_health_status=200
application_openapi_operations_and_demo_routes_present=True
application_user_count_unchanged_after_start=True
application_health_secret_markers_absent=True
v2_env_ignored=True
v2_env_tracked=False
risky_tracked_files=[]
```

No V1 file, V1 database, remote, push, pull request, deployment, Docker
installation, external AI call, or production service was modified. V2-09
VERIFIED.
