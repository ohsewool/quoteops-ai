# QuoteOps AI V2 Autonomous Run Report

## Run status

V2-01 through V2-04 and V2-05A/B are complete. This local-only checkpoint
records the verified deterministic pricing workspace; V2-05 parent database
activation is the next local-only step.

## V1 evidence

V1 remained read-only on `pr-48-cpq-workflow-app-shell-restructure`. Its only working-tree item was the pre-existing `?? docs/v2/`; V2 did not modify V1 files, branches, commits, databases, deployment, or remotes.

## V2 repository state

The local-only V2 repository is on `v2-05-pricing-check`; no remote was added,
no push, pull request, or deployment was performed, and `.env` remains ignored
and untracked.

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
| V2-05 parent | Pending activation | Forward-only application migration and parent regression remain. |
| V2-06A through V2-10B | Not started in this report | Authorized to proceed sequentially after this checkpoint. |

## Application database activation

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

The application database is deliberately unchanged at V2-04 head; it has not
been downgraded and will receive only a forward V2-05 migration after V2-05B
and parent verification. V1 remains unchanged.

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

## Next action

Create the verified local V2-05B checkpoint, forward-migrate the application
database only, perform V2-05 parent verification, then merge locally into
`main` and create `v2-06-approval-inbox`.

## Current verdict

V2-05A VERIFIED

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
