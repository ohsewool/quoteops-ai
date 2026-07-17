# V2-07 Implementation Report

| Subphase | Scope | Verification | Independent review | Verdict |
|---|---|---|---|---|
| V2-07A | Approved-Quote HTML report persistence, renderer, API, PostgreSQL guards | Focused PostgreSQL API/schema: 3 passed; full backend: 47 passed | Approved-source enforcement, exact aggregate snapshot values, self-lineage, immutable artifact triggers, CSP/escaping, audit events, Viewer DTO boundary, and OpenAPI paths were reviewed. | V2-07A VERIFIED |
| V2-07B | Report Center list/create/preview/history/regeneration UI | Focused frontend: 3 passed; frontend regression: 26 passed; production build passed | Authenticated content retrieval, sandboxed preview, manager-only mutation controls, Viewer read-only state, persisted IDs, responsive table/history layout, and raw-cost exclusion were reviewed. | V2-07B VERIFIED |

## V2-07A delivery

Migration `0006_html_report_domain` creates the V2-only `html_reports` table.
Every row has a direct Quote FK, an approved source Quote revision FK, approval
request/decision FKs, creator FK, optional predecessor FK, canonical safe
snapshot, content hash, safe HTML artifact, and timestamp. The row represents
the synchronous `ready` artifact; no additional report workflow state is used.

The Tier A compatibility API is:

```text
GET  /api/html-reports
POST /api/html-reports
GET  /api/html-reports/{report_id}
GET  /api/html-reports/{report_id}/content
```

`POST` accepts only an approved approval-request ID, a nonblank title, the
V2 report type `approved_quote`, and optionally a predecessor report ID for
regeneration. The service verifies the approved terminal decision, its exact
approved Quote revision, Quote/pricing-check/candidate lineage, and equality
between the persisted approval aggregates and immutable candidate evidence.
The report snapshot includes safe quote metadata, aggregate total cost/price,
gross profit, margin, validation/risk, deterministic version identifiers, and
pricing lines. It excludes raw material, labor, overhead, profile, competitor
input, token, secret, and connection data.

PostgreSQL rejects direct inserts not backed by a matching approved revision
and decision, rejects cross-source predecessors, requires a CSP-bearing
artifact with no script tag, and rejects every update/delete to an existing
artifact. Regeneration creates a new row only, preserves the source snapshot,
and records the predecessor. Create/regenerate/list/detail/content operations
write sanitized audit events.

The renderer escapes every dynamic text value and produces a static HTML
document with an in-document CSP. The content endpoint also returns a strict
`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, no-referrer,
no-store response policy. It never invokes AI, alters an approval, activates a
price table, sends a document, or uses V1 data.

## V2-07B delivery

`/app/reports` is now a real authenticated Report Center. Manager/admin users
select an already-approved request, choose a document title, and submit only
stored source IDs. The browser performs no pricing calculation and does not
send an approval decision, raw cost component, or report HTML.

The list and detail views show source Quote/revision, approval linkage, safe
aggregate evidence, pricing lines, content hash, and regeneration history.
The preview fetches the protected artifact and uses `iframe sandbox` with
`srcDoc`; the application does not use `dangerouslySetInnerHTML`. Managers and
admins can regenerate a new immutable artifact from the selected artifact.
Viewer users can list, inspect, and preview reports but do not see create or
regenerate controls.

## V2-07 verification

```text
python -m compileall backend alembic: completed successfully
focused HTML report PostgreSQL API/schema: 3 passed in 116.01s (0:01:56)
test downgrade: 0006_html_report_domain -> 0005_approval_domain
test_html_reports_absent_after_downgrade=True
test_html_report_triggers_absent_after_downgrade=True
test re-upgrade revision=0006_html_report_domain
test_html_reports_present_after_reupgrade=True
backend regression: 47 passed in 642.43s (0:10:42)
focused Report Center frontend: 3 passed in 0.92s
frontend regression: 26 passed in 32.75s
frontend production build: 51 modules transformed; built in 3.12s
```

The V2 test database alone completed the destructive migration cycle. The
application database was forward-migrated once from `0005_approval_domain` to
`0006_html_report_domain`; it was never downgraded.

```text
application_database_name=quoteops_ai_v2
test_database_name=quoteops_ai_v2_test
database_names_distinct=True
application_alembic_revision=0006_html_report_domain
application_tables_match_v2_07_with_metadata=True
application_html_report_triggers_match=True
application_readiness_status=200
application_readiness_is_json=True
v2_env_ignored=True
v2_env_tracked=False
risky_tracked_files=[]
V1 tracked diff: empty
V1 status: pre-existing untracked docs/v2/ only
```

The first full backend run reached the local command time limit before pytest
could emit a final result. It was rerun unchanged with a longer limit and
completed with the verified 47-pass result above.

No V1 file, V1 database, remote, push, pull request, deployment, or production
service was modified. V2-07 VERIFIED.
