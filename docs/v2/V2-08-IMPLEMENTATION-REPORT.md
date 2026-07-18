# V2-08 Implementation Report

| Subphase | Scope | Verification | Independent review | Verdict |
|---|---|---|---|---|
| V2-08A | Grounded copilot output domain, API, provider boundary, PostgreSQL guards | Focused PostgreSQL API/schema: 4 passed; full backend: 51 passed | Immutable core-state snapshot, role boundary, source lineage, purpose-context constraint, output guard, fallback behavior, audit event, and OpenAPI paths were reviewed. | V2-08A VERIFIED |
| V2-08B | Contextual grounded-draft panels for pricing, approval, and reports | Focused frontend: 11 passed; frontend regression: 28 passed; production build passed | Manager/admin-only generation controls, Viewer read-only state, stored IDs only, source-artifact display, state-free UI behavior, and raw-cost exclusion were reviewed. | V2-08B VERIFIED |

## V2-08A delivery

Migration `0007_copilot_output_domain` creates the V2-only immutable
`copilot_outputs` artifact. Forward migration `0008_copilot_context_guard`
adds the purpose-context database guard. Every output is linked to a Quote and
exact Quote revision, and may link to a pricing check/candidate, approval
request, or HTML report. It stores generated text, a safe grounding snapshot,
source-artifact metadata, triggered validation rules, source-data timestamp,
generation mode, provider metadata, and generation timestamp.

The authenticated API contract is:

```text
POST /api/quotes/{quote_id}/copilot-outputs
GET  /api/copilot-outputs/{output_id}
```

Manager/admin users create outputs; authenticated Viewer users can read saved
outputs. The supported purposes are `candidate_explanation`,
`validation_summary`, `approval_reason_draft`,
`rejection_revision_suggestion`, and `report_summary_draft`.

The service resolves all grounding from existing immutable artifacts. It never
accepts a price, margin, validation result, approval result, report state, or
workflow-state field from the request. Candidate/validation/approval drafts
require persisted pricing evidence; a rejection suggestion requires a rejected
terminal approval decision; a report summary requires a saved report.

`copilot_outputs` has foreign keys for all source relationships, a purpose
check, nonblank text/provider/mode checks, and a purpose-context check. Its
PostgreSQL lineage trigger rejects mismatched Quote revisions, pricing checks,
candidates, approval requests, and reports. A separate trigger rejects all
updates and deletes. Output creation records a sanitized
`copilot_output.created` audit event.

The runtime provider is intentionally disabled by default and returns a
deterministic Korean grounded fallback. No external AI call is configured or
performed. Test-only static and failing provider fixtures cover provider
success, timeout/failure fallback, and unsupported-output fallback. Provider
text is rejected when blank, oversized, HTML-like, or sensitive-looking before
it can be persisted.

Grounding contains existing Quote/pricing/approval/report metadata and safe
aggregates already permitted in their source DTOs. It excludes raw material,
labor, overhead, profile, token, secret, password, and database connection
values. Generating an output cannot change a Quote, revision, pricing check,
validation, approval request, decision, or report.

## V2-08B delivery

The reusable `Grounded Copilot` panel is now present in persisted pricing
check, approval, and report contexts. It offers candidate explanation and
validation summary actions for a selected pricing check, an approval-reason
draft and rejected-revision suggestion in approval detail, and a report summary
draft in report detail.

The browser sends only displayed persisted Quote/revision/source IDs. It does
not calculate prices, supply numerical decisions, choose a reviewer, activate
a table, mutate an approval, or render raw cost components. Manager and admin
users explicitly request an output; Viewer users see no generation control.
Returned text is labelled as a deterministic fallback or grounded provider
output and displays its source artifacts and validation-rule references.

## V2-08 verification

```text
python -m compileall backend alembic: completed successfully
git diff --check: completed successfully
focused copilot PostgreSQL API/schema before migration-cycle retry: 4 passed in 212.38s (0:03:32)
test downgrade: 0007_copilot_output_domain -> 0006_html_report_domain
test_copilot_outputs_absent_after_downgrade=True
test_copilot_triggers_absent_after_downgrade=True
test_copilot_functions_absent_after_downgrade=True
test re-upgrade revision=0007_copilot_output_domain
test_copilot_outputs_present_after_reupgrade=True
test_copilot_output_columns_complete=True
test_copilot_output_checks_complete=True
test_copilot_output_foreign_key_count=7
test_copilot_output_triggers_complete=True
focused copilot PostgreSQL API/schema after final migration graph: 4 passed in 220.50s (0:03:40)
focused frontend pricing/approval/report/copilot: 11 passed in 8.71s
frontend regression: 28 passed in 13.14s
frontend production build: 53 modules transformed; built in 6.93s
backend regression: 51 passed in 830.15s (0:13:50)
V2 security gates: 14 passed in 4.58s
```

The final migration graph completed a test-only `0008 -> 0006 -> 0008`
cycle. The rebuilt test schema contains
`ck_copilot_outputs_purpose_context`.

## Parent activation and boundaries

Before activation, the configured application database was confirmed as
`quoteops_ai_v2`, the configured test database was confirmed as
`quoteops_ai_v2_test`, and their parsed database names were distinct without
printing either URL. The application database was at
`0006_html_report_domain`, matched the V2-07 table set, and had no
`copilot_outputs` table.

Only after all V2-08 targeted, frontend, security, and backend regression
checks passed, the application database was forward-migrated to
`0007_copilot_output_domain`, then once more to the forward-only context guard
`0008_copilot_context_guard`. It was never downgraded.

```text
application_alembic_revision_after_v2_08=0008_copilot_context_guard
application_table_set_match_v2_08=True
application_copilot_constraints_complete=True
application_copilot_triggers_complete=True
application_readiness_status=200
application_readiness_is_json=True
application_openapi_copilot_routes_present=True
application_user_count_unchanged_after_app_start=True
v2_env_ignored=True
v2_env_tracked=False
risky_tracked_files=[]
V1 tracked diff: empty
V1 status: pre-existing untracked docs/v2/ only
```

The first-user CLI remains the only provisioning path. Application startup did
not create an account. No V1 file or database was accessed for mutation, no
remote/push/pull request/deployment action occurred, and no V2-09 work was
started. V2-08 VERIFIED.
