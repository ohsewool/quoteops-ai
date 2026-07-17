# QuoteOps AI V2 Autonomous Run Report

## Run status

V2-01 through V2-09 and V2-10A are complete. This local-only checkpoint
records the verified release-regression and migration-recovery evidence;
authorized autonomous work resumes at V2-10B for manual/staging readiness
review.

## V1 evidence

V1 remained read-only on `pr-48-cpq-workflow-app-shell-restructure`. Its only working-tree item was the pre-existing `?? docs/v2/`; V2 did not modify V1 files, branches, commits, databases, deployment, or remotes.

## V2 repository state

The local-only V2 repository is on `v2-10-verification-release-readiness`
before its V2-10A checkpoint. No remote was added, no push, pull request, or
deployment was performed, and `.env` remains ignored and untracked.

## Verdicts

| Scope | Verdict | Evidence |
|---|---|---|
| V2-01A | VERIFIED | Repository/configuration/CI/frontend foundation checks passed. |
| V2-01B | VERIFIED | Real PostgreSQL migration/integration/readiness/security checks passed. |
| V2-01 parent | VERIFIED | Both required subphases and parent gate passed. |
| V2-02 parent | VERIFIED | Public/authentication application shell and role-aware workspace passed. |
| V2-03 parent | VERIFIED | Persistent customer-request workflow and workspace passed. |
| V2-04A | VERIFIED | Persistent Quote/Line/revision PostgreSQL domain passed. |
| V2-04B | VERIFIED | Atomic request-to-Quote API and audit contract passed. |
| V2-04C | VERIFIED | API-backed Quote workspace passed. |
| V2-04 parent | VERIFIED | Application DB forward activation, backend/frontend regression, and readiness passed. |
| V2-05A | VERIFIED | Deterministic pricing source/evidence PostgreSQL domain and APIs passed. |
| V2-05B | VERIFIED | API-backed Pricing Check Workspace passed. |
| V2-05 parent | VERIFIED | Application DB forward activation, backend/frontend regression, and readiness passed. |
| V2-06 parent | VERIFIED | Approval lineage and approval inbox checks passed. |
| V2-07 parent | VERIFIED | Approved-Quote reports, safe preview, lineage, and application activation passed. |
| V2-08A | VERIFIED | Immutable grounded copilot domain, provider fallback boundary, PostgreSQL guards, and API passed. |
| V2-08B | VERIFIED | Contextual grounded-draft panels, role boundary, frontend regression, and build passed. |
| V2-08 parent | VERIFIED | Test-only migration cycle, application forward activation, security gates, and full regression passed. |
| V2-09A | VERIFIED | Safe diagnostics/audit search and isolated competitor-reference CSV adapter passed. |
| V2-09B | VERIFIED | Explicit admin-only two-product guided demo and guide-state reset passed. |
| V2-09 parent | VERIFIED | Test-only migration recovery, application forward activation, security gates, full backend/frontend regression, and build passed. |
| V2-10A | VERIFIED | Local full regression, security, base rollback/rebuild, release smoke, and V1-boundary checks passed. |
| V2-10B | Not started in this report | Manual visual/staging/migration/cutover readiness review remains pending. |

## V2-01 application database activation

The application database was confirmed as `quoteops_ai_v2`; the test database was confirmed as `quoteops_ai_v2_test`; their parsed URLs were distinct without printing either value. The application database had no V2 tables, was upgraded to Alembic head, and now has only `alembic_version`, `users`, and `audit_events`. No application-database downgrade was run.

```text
application_alembic_upgrade=OK
application_alembic_head_detected=True
application_schema_tables_approved_only=True
application_readiness_status=200
```

## Test database isolation

The V2-only test database was created with Psycopg autocommit. The destructive migration cycle was limited to that database.

```text
alembic_upgrade_test_database=OK
alembic_downgrade_test_database=OK
clean_test_schema_verification=OK
alembic_reupgrade_test_database=OK
postgresql_integration_retest=OK
```

## Verification results

```text
pytest -q backend/tests: 22 passed in 16.51s
PostgreSQL integration: 1 passed, 21 deselected in 10.89s
Frontend Vitest: 1 passed
Frontend production build: 27 modules transformed; built in 3.41s
Readiness: application success 200; injected database failure 503 and sanitized
Security: no runtime create_all, no SQLite runtime path, no risky tracked artifacts
```

## User provisioning

First-user creation remains the explicit CLI command only. Startup does not seed or create an account, credential, or demo user.

## V2-01 gap result

No known mandatory V2-01 gaps remain after verification.

## Boundary and rollback result

Only the V2 application and test databases were used. V1 was never connected. The application database was upgraded once and not downgraded. Destructive proof was restricted to `quoteops_ai_v2_test`.

## V2-05A evidence

Migration `0004_pricing_check_domain` provides products, active cost profiles,
competitor references, immutable pricing checks/candidates/validations, and
the authenticated V2 pricing-check API. Candidate calculation uses only
Decimal deterministic services and persists formula, rule, rounding, source
profile/version, and normalized competitor context snapshots. Viewer pricing
responses exclude raw cost components and raw source configuration.

```text
test_downgrade_revision=0003_quote_domain
pricing_tables_absent_after_downgrade=True
pricing_enums_absent_after_downgrade=True
test_reupgrade_to_0004=OK
pricing target after recovery=6 passed in 125.20s
backend regression=39 passed in 287.34s (0:04:47)
```

The V2-05A application-database boundary was preserved until V2-05B and the
parent gate passed. V1 remains unchanged.

## V2-05B evidence

The authenticated `/app/pricing` workspace now loads persisted Quote and
pricing-check APIs, supports direct `quote_id` routing and saved Quote
selection, lets only manager/admin create a check from the current Quote
version/revision, and shows viewer-safe saved evidence. It never calculates or
generates prices in the browser and does not send raw cost components or source
configuration to the browser.

```text
frontend pricing target=3 passed in 0.93s
frontend regression=20 passed in 10.71s
frontend production build=47 modules transformed; built in 2.32s
```

## V2-05 parent evidence

The application database was confirmed at V2-04 head with no V2-05 tables,
then forward-migrated once to `0004_pricing_check_domain`. No application
database downgrade occurred. The test database remained the only destructive
recovery target.

```text
application_alembic_revision=0004_pricing_check_domain
application_tables_match_v2_05=True
application_pricing_constraints_present=True
application_pricing_evidence_triggers_match=True
test_alembic_revision=0004_pricing_check_domain
application_readiness_status=200
backend regression=39 passed in 281.40s (0:04:41)
frontend regression=20 passed in 10.71s
frontend production build=47 modules transformed; built in 2.32s
```

## V2-09 checkpoint action

Merge the verified local V2-09 checkpoint into `main`, then create the
V2-10 branch from updated local `main`.

## Current verdict

V2-09 VERIFIED

## V2-07 evidence

V2-07 adds the V2-only immutable `html_reports` artifact, backed exclusively
by an approved Quote revision and terminal approval decision. It preserves
safe canonical pricing evidence, source revision identifiers, an optional
predecessor report ID, hash, escaped CSP-protected HTML, and audit events.
Generation/regeneration is manager/admin-only; viewers can safely list, read,
and preview an artifact. No report API can alter approvals, prices, active
price tables, or V1.

```text
test downgrade/re-upgrade: 0006 -> 0005 -> 0006 on test DB only
focused report PostgreSQL API/schema: 3 passed in 116.01s
backend regression: 47 passed in 642.43s (0:10:42)
frontend report target: 3 passed in 0.92s
frontend regression: 26 passed in 32.75s
frontend production build: 51 modules transformed; built in 3.12s
application_alembic_revision=0006_html_report_domain
application_tables_match_v2_07_with_metadata=True
application_html_report_triggers_match=True
application_readiness_status=200
v2_env_ignored=True
v2_env_tracked=False
risky_tracked_files=[]
V1 tracked diff=empty
```

The application database was forward-migrated once and never downgraded. The
destructive migration proof used `quoteops_ai_v2_test` only. V1 remains
unchanged, and its pre-existing untracked `docs/v2/` directory was not touched.

## V2-06A evidence

V2-06A adds the quote-scoped approval request and immutable terminal decision
domain. Each submission records the authenticated requester, immutable Quote
revision, pricing check, selected candidate, safe validation snapshot, and
optimistic version. Submission re-runs deterministic validation from stored
Decimal snapshot inputs and rejects evidence divergence. Normal-mode
self-approval is `403`; `failed/high` is `409`; warning/medium submission
requires a written reason; no override or automatic price-table activation is
available.

Approved and rejected decisions are guarded by PostgreSQL triggers. Rejection
preserves its revision then returns the Quote to a new editable draft revision.
The test database alone was used for the four approval target tests and full
backend regression. V1 remains unchanged.

```text
approval PostgreSQL target=4 passed in 189.56s (0:03:09)
backend regression=43 passed in 451.04s (0:07:31)
```

## V2-06B evidence

`/app/approvals` is now a real authenticated Inbox, and `/app/pricing` can
submit the selected current immutable Pricing Check for approval. The frontend
uses only persisted IDs, version, reasons, and safe response aggregates.
Manager/admin decision controls are hidden for the requester and absent for
Viewer; the backend remains the authority for every authorization and terminal
transition.

```text
frontend approval target=3 passed in 6.93s
frontend regression=23 passed in 11.91s
frontend build=49 modules transformed; built in 2.36s
explicit demo self-approval target=1 passed in 52.97s
```

## V2-06 parent evidence

The V2 application database moved forward once from `0004_pricing_check_domain`
to `0005_approval_domain`; no application-database downgrade occurred. The
separate V2 test database alone completed the V2-06 downgrade, empty-schema,
and re-upgrade recovery proof. Application readiness remains a JSON `200`.

```text
application_alembic_revision=0005_approval_domain
test_alembic_revision=0005_approval_domain
application_tables_match_v2_06=True
application_approval_constraints_present=True
application_approval_triggers_match=True
backend regression=44 passed in 514.18s (0:08:34)
frontend regression=23 passed in 17.29s
frontend production build=49 modules transformed; built in 1.44s
v2_env_ignored=True
v2_env_tracked=False
risky_tracked_files=[]
V1 tracked diff=empty
```

## V2-04 parent evidence

The application database was confirmed as `quoteops_ai_v2`; the test database
was confirmed as `quoteops_ai_v2_test`; their parsed names were distinct
without printing either URL. The application database was forward-migrated
from `0002_customer_request_domain` to `0003_quote_domain` only. It now has
the approved V2-01 through V2-04 tables, Quote constraints, immutable revision
triggers, and a healthy JSON readiness response. No application-database
downgrade was run; destructive testing remained isolated to the test database.

```text
application_alembic_revision=0003_quote_domain
application_tables_match_v2_04=True
application_quote_constraints_present=True
application_quote_revision_triggers_match=True
application_quote_status_values_match=True
test_alembic_revision=0003_quote_domain
application_readiness_status=200
backend regression=33 passed in 184.45s (0:03:04)
frontend regression=17 passed in 15.41s
frontend production build=45 modules transformed; built in 3.61s
```

## V2-08 evidence

V2-08 adds immutable, grounded copilot text outputs. Each output is linked to
the existing Quote/revision and purpose-specific persisted evidence. The API
accepts no pricing, validation, approval, report, or workflow-state write
field. The default provider is disabled and produces a deterministic fallback;
test-only providers prove success, failure, and unsupported-output behavior.
No external AI request is made.

```text
test migration cycle: 0008 -> 0006 -> 0008 on test DB only
focused copilot PostgreSQL API/schema: 4 passed in 220.50s
backend regression: 51 passed in 830.15s (0:13:50)
frontend copilot/pricing/approval/report target: 11 passed in 8.71s
frontend regression: 28 passed in 13.14s
frontend production build: 53 modules transformed; built in 6.93s
V2 security gates: 14 passed in 4.58s
application_alembic_revision=0008_copilot_context_guard
application_tables_match_v2_08=True
application_copilot_constraints_present=True
application_copilot_triggers_match=True
application_readiness_status=200
application_openapi_copilot_routes_present=True
application_user_count_unchanged_after_app_start=True
v2_env_ignored=True
v2_env_tracked=False
risky_tracked_files=[]
V1 tracked diff=empty
```

The application database was forward-migrated once from V2-07 to V2-08 and
never downgraded. All destructive migration proof remained limited to
`quoteops_ai_v2_test`. V1 remained unchanged and no remote, push, pull
request, deployment, or V2-09 work occurred.

## V2-09 evidence

V2-09 adds a restrained admin Operations console, one isolated versioned
competitor-reference CSV adapter, and an explicitly enabled admin guided demo.
The adapter uses a fixed schema/header, bounded size and row count, exact
Decimal monetary parsing, whole-import validation, and one transaction. Viewer
access to the CSV endpoints is denied. Diagnostics and audit search are
admin-only, return no secret or raw connection value, and persist only
sanitized audit metadata.

The guided demo is unavailable unless enabled in a non-production setting. It
does not seed users, passwords, credentials, or data at startup. A run is an
explicit admin action and exposes exactly the two supported product codes:
`a3_flyer` and `brand_sticker`. Reset changes persisted guide state only and
does not delete or alter business workflow records.

```text
test migration cycle: 0009 -> 0008 -> 0009 on test DB only
focused operations PostgreSQL API/schema: 4 passed in 98.47s
backend regression after final V2-09 review: 55 passed in 931.85s (0:15:31)
frontend V2-09 target: 10 passed in 10.76s
frontend regression: 30 passed in 15.84s
frontend production build: 57 modules transformed; built in 1.69s
V2 security gates: 13 passed in 4.79s
application_alembic_revision=0009_operations_demo_domain
application_tables_match_v2_09=True
application_readiness_status=200
application_openapi_operations_and_demo_routes_present=True
application_user_count_unchanged_after_start=True
v2_env_ignored=True
v2_env_tracked=False
risky_tracked_files=[]
V1 tracked diff=empty
```

The application database was forward-migrated once from V2-08 to V2-09 and
never downgraded. Destructive recovery proof was restricted to the V2 test
database. V1 remained unchanged; no remote, push, pull request, deployment,
Docker installation, or external AI call occurred.

## V2-10A evidence

V2-10A adds a safe local release smoke command and a release API-contract
test. The smoke command verifies that both V2 databases are distinct and at
Alembic head, the expected schema is present, public health/live/ready/OpenAPI
responses are healthy, required Tier A paths are present, no connection string
or health secret marker is exposed, `.env` remains ignored/untracked, and no
risky generated artifact is tracked. It performs no migration or mutation.

```text
test migration cycle: 0009 -> base -> 0009 on test DB only
backend regression after clean re-upgrade: 57 passed in 937.62s (0:15:37)
frontend regression: 30 passed in 28.35s
frontend production build: 57 modules transformed; built in 1.69s
release_readiness=VERIFIED_LOCAL
v2_float_columns=[]
startup_create_all_present=False
runtime_application_sqlite_reference_present=False
V1 tracked diff=empty
```

The V2 application database was not downgraded. V2-10B remains the separate
manual/staging readiness gate; no deployment, V1 database connection, remote,
push, pull request, or cutover occurred.
