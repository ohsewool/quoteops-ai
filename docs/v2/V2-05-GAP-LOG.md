# V2-05 Gap Log

No known mandatory V2-05 gaps remain after verification.

## Verified V2-05A scope

- Pricing source data is restricted to the two V2 MVP product codes and is
  persisted with PostgreSQL Decimal/Numeric constraints.
- One active cost profile per product is database-enforced; input rates below
  one, positive quantities, product/competitor foreign keys, supported
  strategies, and KRW evidence currency are all constrained.
- Candidate formulas and validation rules are deterministic and independent of
  an LLM. `failed/high`, `warning/medium`, and `passed/low` readiness are
  persistent and test-covered.
- Every pricing check records its immutable Quote revision/version, selected
  strategy, source profile/version, competitor-reference snapshot, formula,
  validation rule, and rounding policy version.
- Viewers receive only aggregate safe pricing evidence and cannot read raw cost
  profiles, raw component costs, or competitor-reference management APIs.
- Pricing evidence rows are database-immutable; the test database downgrade
  and re-upgrade recovery cycle passed.
- V2-05A did not alter the application database; only the V2 test database was
  used for destructive recovery proof. The parent forward-only activation is
  recorded below.
- V1 remains unchanged. The ignored root `.env` remains untracked.

## Verified V2-05B scope

- `/app/pricing` is a real authenticated Pricing Check Workspace rather than a
  future-phase placeholder.
- The route supports direct URL opening with `quote_id` and a safe saved-Quote
  selector when no query is present.
- Manager/admin creation sends the current persisted Quote version, current
  immutable revision ID, selected server strategy, and competitor-context flag
  to the V2 API; Viewer controls remain read-only.
- Existing snapshots render their aggregate totals, candidates, validation,
  risk, and context summary from server data only. Raw source-cost/profile and
  raw competitor-reference fields are absent from browser responses and tests.
- Loading, empty, error, stale/source prerequisite, and ineligible Quote states
  are explicit. The frontend test and production-build gates passed.

## Verified parent activation

- The V2 application database was confirmed as `quoteops_ai_v2` and upgraded
  forward from V2-04 to `0004_pricing_check_domain` only after V2-05A/B passed.
- The V2 test database remains `quoteops_ai_v2_test`, distinct from the
  application database, and remains at V2-05 head after the destructive
  recovery cycle.
- The application schema exactly contains the approved V2-01 through V2-05
  tables, expected pricing constraints, and immutable evidence triggers.
- Application readiness remains a healthy JSON `200` response.
- No application-database downgrade, V1 database connection, V1 modification,
  remote, push, pull request, deployment, price-table activation, approval,
  report, or AI action occurred.

## Deferred only to V2-05B and later scopes

- Quote workflow transition into approval is V2-06 work. V2-05A preserves a
  draft Quote after a check so a manager can correct it before submission.
- Approval requests, reports, AI outputs, price-table activation, CSV tools,
  and V1 migration are deliberately out of scope for V2-05A.

## Manual visual evidence

Browser/Playwright capability is unavailable in this local execution
environment. V2-05B component checks will run locally; full visual evidence
remains a V2-10B manual-review requirement and is not claimed here.
