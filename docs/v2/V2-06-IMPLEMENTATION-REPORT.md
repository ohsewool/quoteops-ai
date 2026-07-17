# V2-06 Implementation Report

| Subphase | Scope | Commit | Tests | Independent review | Verdict |
|---|---|---|---|---|---|
| V2-06A | Quote-scoped approval lineage, deterministic revalidation, authenticated decisions, PostgreSQL guards | pending checkpoint | Approval target: 4 passed; full backend: 43 passed | Submission revalidation, requester/reviewer separation, warning and failed gates, terminal transition trigger, decision immutability, rejection revision lineage, audit metadata, and concurrent reviewer behavior were reviewed. | V2-06A VERIFIED |
| V2-06B | Approval Inbox and detail workspace | pending | pending | pending | pending |

## V2-06A delivery

Migration `0005_approval_domain` introduces the approval lineage tables:

```text
approval_requests
approval_decisions
```

An approval request links one Quote, the exact immutable Quote revision and
Quote version used for pricing, the selected immutable pricing check and price
candidate, and the authenticated requester. It persists safe candidate totals,
gross profit, margin, validation status, risk level, currency, optional
submission reason, and an optimistic version. It does not copy or expose raw
cost components, profile configuration, or competitor reference inputs.

The authenticated API contract is:

```text
GET  /api/approval-requests
POST /api/approval-requests
GET  /api/approval-requests/{approval_request_id}
POST /api/approval-requests/{approval_request_id}/approve
POST /api/approval-requests/{approval_request_id}/reject
```

Manager/admin users create and decide requests; viewers can safely list and
read the resulting evidence. Requester and reviewer identities are derived
only from the authenticated server-side user. In normal mode the requester
cannot decide their own request (`403`). Explicit demo mode is the only
exception; its stored response label and `demo_self_approval_used` audit event
make that exception visible.

Approval submission locks the Quote and immutable pricing evidence, confirms
that the selected candidate belongs to the check and current Quote revision,
and re-runs deterministic validation from the stored Decimal cost and market
snapshots. Submission is rejected if recreated candidate values or validation
checks differ from the persisted immutable evidence. `failed/high` returns
`409`; `warning/medium` requires a nonblank written reason (`422`);
`passed/low` can proceed. No override, AI call, price-table activation, or
customer-facing price change is available.

On submission the Quote receives an immutable `approval_pending` revision. A
separate reviewer can choose one terminal decision exactly once. PostgreSQL
guards reject further request transitions, source-evidence mutation, request
deletion, and approval-decision update/delete. Approval creates an immutable
`approved` Quote revision. Rejection creates an immutable `rejected` revision,
then a new current `draft` revision so the manager can revise content and
create a new pricing check rather than altering old evidence.

Each terminal audit event records the request, source Quote revision, pricing
check, candidate, decision, and resulting revision IDs without raw costs,
tokens, passwords, or connection data.

## V2-06A verification

```text
python -m compileall backend alembic: completed successfully
approval PostgreSQL API/schema target: 4 passed in 189.56s (0:03:09)
full backend regression: 43 passed in 451.04s (0:07:31)
```

The PostgreSQL integration suite covers authentication/role handling,
submission eligibility, safe Viewer reads, separate-reviewer enforcement,
warning and rejection reason requirements, blocked evidence, race behavior
across two reviewer sessions, immutable decision triggers, audit lineage,
rejection-to-draft editing, and the required OpenAPI paths.

V2-06A used only the configured V2 test database. The application database was
not downgraded or changed during this subphase. V1 remains unmodified, and the
ignored root `.env` remains untracked.

## V2-06B pending scope

V2-06B will add the authenticated Approval Inbox, request detail/timeline, and
review controls using these APIs. It will not add approval overrides, client
side reviewer identity, price-table activation, reports, AI decisions, or any
V1 integration.
