# V2-06 Implementation Report

| Subphase | Scope | Commit | Tests | Independent review | Verdict |
|---|---|---|---|---|---|
| V2-06A | Quote-scoped approval lineage, deterministic revalidation, authenticated decisions, PostgreSQL guards | `7b46370` | Approval target: 5 passed; full backend: 43 passed before final demo-mode target addition | Submission revalidation, requester/reviewer separation, warning and failed gates, terminal transition trigger, decision immutability, rejection revision lineage, audit metadata, concurrent reviewer behavior, and explicit demo exception were reviewed. | V2-06A VERIFIED |
| V2-06B | Approval Inbox, pricing-check submission, role-safe detail, and decision controls | pending checkpoint | Feature target: 3 passed; frontend regression: 23 passed; production build passed | API-backed list/detail, server-owned version submission, Viewer read-only behavior, requester review guard, warning reason form, terminal rendering, responsive layout, and raw-cost exclusion were reviewed. | V2-06B VERIFIED |

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

## V2-06B delivery

`/app/approvals` is now an authenticated approval inbox rather than a future
phase placeholder. It loads the persisted approval list and selected detail
from the API, shows the Quote revision/check/candidate/requester chain, safe
candidate aggregates, validation/risk, request reason, decision record, and a
timeline reconstructed from persisted request and decision timestamps.

Managers and admins can submit the selected current Pricing Check from
`/app/pricing`. The browser sends only saved IDs and an optional or required
written reason; it never calculates a candidate or sends reviewer identity.
Warning/medium-risk requests require a visible reason locally and remain
server-enforced. After submission the UI opens the saved approval detail.

In the inbox, managers/admins can approve or reject only another requester's
pending item using the current server-provided optimistic version. The UI does
not offer a requester decision control, Viewer state remains read-only, and a
terminal result removes controls. The detail includes a visible demo label only
when the server persisted the explicit demo self-approval flag.

```text
V2-06B frontend target=3 passed in 6.93s
frontend regression=23 passed in 11.91s
Vite production build=49 modules transformed; built in 2.36s
demo self-approval backend target=1 passed in 52.97s
```

V2-06B does not add approval overrides, client-supplied reviewer identity,
price-table activation, report generation, AI decisions, or V1 integration.
