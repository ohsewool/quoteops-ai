# V2-10 Release Readiness Review

## Local result

V2-10A is verified. V2-10B local deliverables are verified:

- release smoke and API contract checks are green;
- the V2 application/test databases are distinct and at Alembic head;
- destructive migration recovery was confined to the V2 test database;
- the complete PostgreSQL backend regression passed with `69 passed in
  833.65s`, frontend regression passed with `30 passed in 78.51s`, and the
  production build completed with 57 transformed modules in 2.77s;
- the non-destructive release-readiness command returned
  `release_readiness=VERIFIED_LOCAL`; both V2 databases are reachable at
  Alembic revision `0009_operations_demo_domain`, and the application database
  remains a clean review target with zero users;
- the versioned V1 export transformer, manifest, and quarantine report are
  covered by six focused tests and a real CLI subprocess check;
- public landing and login visual checks passed at desktop and a true 390px
  emulated mobile viewport with no horizontal document overflow;
- no user was auto-created, no secret was logged, and no V1 runtime/database
  connection was made.

## Clean-launch migration decision

**V1 data migration: NOT APPLICABLE.** The V1 database held disposable demo
data and was deleted. This release uses a new clean V2 database, so no V1 rows
will be exported or imported and no V1 database connection is required. The
V1 source repository and Git history remain preserved as read-only evidence.

This removes only the former V1 export/import and migration-dry-run gate. It
does not mark a migration dry run as passed and does not remove authenticated
QA, V2 staging smoke, rollback rehearsal, or human cutover approval.

## Local review account commands

Use only the V2 application database. Store the four passwords in ignored
local environment variables or enter them in the non-echoing prompt. Do not
place password values in Git, shell history, reports, screenshots, or command
arguments.

```powershell
.\.venv\Scripts\python.exe -m backend.cli.create_first_user --username review-admin --display-name "Review Admin" --password-env QUOTEOPS_REVIEW_ADMIN_PASSWORD
.\.venv\Scripts\python.exe -m backend.cli.create_user --actor-username review-admin --username review-manager-1 --display-name "Review Manager 1" --role manager --password-env QUOTEOPS_REVIEW_MANAGER_1_PASSWORD
.\.venv\Scripts\python.exe -m backend.cli.create_user --actor-username review-admin --username review-manager-2 --display-name "Review Manager 2" --role manager --password-env QUOTEOPS_REVIEW_MANAGER_2_PASSWORD
.\.venv\Scripts\python.exe -m backend.cli.create_user --actor-username review-admin --username review-viewer --display-name "Review Viewer" --role viewer --password-env QUOTEOPS_REVIEW_VIEWER_PASSWORD
```

`create_first_user` refuses to run after any user exists. `create_user` refuses
to use the test database, requires an existing active admin actor, records a
safe audit event, and never runs during application startup.

## Authenticated manual-review status

The local authenticated review has **not** been performed. The V2 application
database has zero users, and no password values were supplied, created, or
recorded during this preparation. The four commands above are deliberately
explicit and must be run against the V2 application database before starting
the local backend and frontend.

After those accounts exist, the reviewer must record real browser evidence for:

- admin, manager, and viewer login;
- protected-route redirect and role-aware navigation;
- customer-request creation, request-to-Quote conversion, quote lines, and
  totals;
- deterministic candidate generation and pricing-check snapshot;
- approval submission, self-approval rejection, decision by a different
  manager, and rejection with a required reason;
- approved-report generation and end-to-end audit lineage;
- viewer read-only enforcement; and
- loading, empty, error, conflict, and permission states on desktop and a
  true 390px authenticated mobile viewport.

No item in this list is inferred from unit or API regression coverage.

## Staging configuration checklist

The deployment owner must provide a separate V2 staging application and two
separate V2 staging databases before a release attempt. Configuration must use
ignored secret storage, never frontend `VITE_*` secrets. The staging review
must verify:

- separate V2 staging application and test database credentials, with no V1
  database connectivity;
- production-like security flags and approved CORS origins;
- public health/live/ready only, with protected system status and API docs;
- no demo account/data seeding and no automatic first-user creation;
- prior V2 artifact and V2 database snapshot availability for rollback.

## Remaining mandatory gates

| Gate | Current result | Owner/action |
|---|---|---|
| V1 export/import and migration dry run | Not applicable | Clean V2 launch was explicitly selected; no V1 data remains to migrate. |
| Authenticated browser core journey | Not performed | Reviewer provisions a staging account using the explicit first-user CLI and executes the full workflow. |
| V2 staging deployment smoke | Not performed | Deployment owner deploys only to separate V2 staging. |
| Rollback rehearsal | Not performed | Release owner rehearses the checked-in runbook on staging. |
| Cutover approval or rejection | Not made | Named human release owner records the final decision after all evidence. |

## Decision

**V2 LOCAL MANUAL REVIEW BLOCKED.** Local code and evidence are ready for
manual review, but authenticated QA, staging deployment smoke, rollback
rehearsal, and human cutover approval remain mandatory gates. No release or
cutover is authorized by this document.
