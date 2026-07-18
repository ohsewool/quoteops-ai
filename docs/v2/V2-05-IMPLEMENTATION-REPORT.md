# V2-05 Implementation Report

| Subphase | Scope | Commit | Tests | Independent review | Verdict |
|---|---|---|---|---|---|
| V2-05A | Deterministic pricing source data, candidates, validation, immutable evidence, and authenticated APIs | `98bfe38` | Pricing target: 6 passed; full backend: 39 passed | Decimal formulas, validation severities, immutable triggers, source lineage, role-safe DTOs, migration recovery, and raw-cost boundaries were reviewed. | V2-05A VERIFIED |
| V2-05B | Pricing Check Workspace | `fd6d360` | Feature target: 3 passed; frontend regression: 20 passed; production build passed | Actual API loading, manager create action, Viewer read-only state, URL selection, safe rendering, and responsive CSS were reviewed. | V2-05B VERIFIED |

## V2-05A delivery

Migration `0004_pricing_check_domain` adds the V2 pricing source and evidence
domain:

```text
products
cost_profiles
competitors
competitor_references
pricing_checks
price_candidates
price_candidate_lines
price_validation_results
price_validation_checks
```

The source domain is limited to the two V2 MVP product codes. Cost profiles use
`NUMERIC(18,2)` component costs and a `NUMERIC(9,6)` target margin; the
database enforces non-negative costs, a rate below one, and at most one active
profile for a product. Competitor references capture product, quantity, basis,
observed timestamp, and competitor type through the related competitor record.
No V1 data, route, database, or service was read or modified at runtime.

The authenticated V2 API contract is:

```text
GET/POST /api/products
GET/POST /api/cost-profiles
GET/POST /api/competitors
GET/POST /api/competitor-references
POST     /api/quotes/{quote_id}/pricing-checks
GET      /api/quotes/{quote_id}/pricing-checks
GET      /api/pricing-checks/{pricing_check_id}
```

Manager/admin controls every source-data and pricing-check write. Viewers can
read product summaries and pricing evidence but cannot read cost-profile or
competitor-reference source data. Pricing-check DTOs expose aggregate total
cost, candidate outputs, margin, risk, and validation outcomes only; material,
labor, overhead, cost-profile IDs, internal formula inputs, and raw validation
details are not sent to the browser.

## Deterministic calculation and validation

`backend/services/pricing_engine.py` is a pure Decimal service. It calculates
the fixed V2 candidate strategies `low_margin` (`0.250000`), `target_margin`
(`0.350000`), and `premium_margin` (`0.450000`) from the active profile:

```text
unit_cost = material_cost + labor_cost + overhead_cost
unit_price = unit_cost / (1 - margin_rate)
total_cost = unit_cost * quantity
total_price = unit_price * quantity
gross_profit = total_price - total_cost
estimated_margin = gross_profit / total_price
```

Intermediate arithmetic stays Decimal. Each saved monetary output is rounded
once with KRW half-up `NUMERIC(18,2)` storage and each saved rate uses the
canonical six-decimal V2 rate boundary. Raw component inputs and unrounded
intermediates are retained only inside immutable server-side evidence JSON.

The validation snapshot has four deterministic checks:

```text
price_above_cost      error
minimum_margin        error
market_floor          warning
market_ceiling        warning
```

Error failures produce `failed/high` and a `blocked` pricing-check result.
Market warnings produce `warning/medium` and `needs_review`; all passing checks
produce `passed/low` and `ready`. No AI call participates. The V1 `>= cost`
edge was deliberately strengthened to strict `> cost` so a zero-margin or
zero-price result cannot appear approval-ready. Competitor context is an
explicit, unweighted normalized unit-price snapshot because no verified V1
numeric weighting behavior was available to port.

Pricing evidence is append-only: PostgreSQL triggers reject update and delete
against every snapshot table. A pricing check deliberately leaves the current
Quote in `draft` during V2-05A, allowing the manager to correct lines after a
blocked or warning result. V2-06 will own the authorized approval submission
and Quote workflow-state transition; the immutable check still records the
exact source Quote revision and source Quote version.

## PostgreSQL migration evidence

Only the configured V2 test database was used for destructive recovery:

```text
test_downgrade_revision=0003_quote_domain
pricing_tables_absent_after_downgrade=True
pricing_enums_absent_after_downgrade=True
test_reupgrade_to_0004=OK
```

The application database remains at V2-04 head during V2-05A. It was not
downgraded or altered. V2-05 will perform its single forward-only application
upgrade only after V2-05B and the parent phase gates pass.

## Verification

```text
python -m compileall backend alembic: completed successfully
pricing engine/API/schema target: 6 passed in 125.20s after recovery
full backend regression: 39 passed in 287.34s (0:04:47)
```

The tests cover exact Decimal formulas, threshold boundaries, binary-float
rejection, authentication and role enforcement, source-data creation, active
cost profile requirements, candidate count and selected output, warning and
blocked readiness, stale Quote conflicts, Viewer raw-cost exclusion, audit
sanitization, OpenAPI paths, database constraints, partial active-profile
uniqueness, and actual immutable-evidence update rejection.

No price table activation, approval decision, report, AI action, automatic
customer price change, V1 modification, remote, push, pull request, or
deployment is included in V2-05A.

## V2-05B delivery

`/app/pricing` is now an authenticated, API-backed Pricing Check Workspace.
It accepts an optional `quote_id` query parameter from the Quote workspace and
also offers a real saved-Quote selector when opened directly. It loads the
persisted Quote, its pricing-check history, and the selected immutable detail
through the V2 API; it does not manufacture candidates or calculate totals in
the browser.

Managers and admins can choose one of the fixed server-supported strategies
and whether to include competitor context, then POST the current Quote version
and current immutable revision ID. The created server snapshot becomes the
selected view. Viewers can select a Quote and read its existing snapshot but
have no creation control. The page includes loading, empty, safe error,
permission, ineligible Quote, saved-history, summary, candidate comparison,
and selected validation states.

The table renders only server-provided aggregate total cost, total price, gross
profit, margin, validation, and risk. It contains no raw material/labor/
overhead/profile fields, raw competitor references, browser-side formula, or
AI call. The responsive table uses horizontal containment on narrow screens;
the summary and validation rows collapse to stable single-column layouts.

```text
V2-05B frontend target=3 passed in 0.93s
V2-05B frontend regression=20 passed in 10.71s
V2-05B Vite production build=47 modules transformed; built in 2.32s
```

## V2-05 parent activation

After both subphases passed, the application database and test database names
were parsed without printing either URL and confirmed distinct. The application
database was still exactly at V2-04 head with no V2-05 tables. It was then
forward-migrated once, from `0003_quote_domain` to
`0004_pricing_check_domain`. No application-database downgrade was run.

```text
application_database_name=quoteops_ai_v2
test_database_name=quoteops_ai_v2_test
database_names_distinct=True
application_alembic_revision_before=0003_quote_domain
application_tables_match_v2_04=True
application_pricing_tables_absent_before=True
application_alembic_revision=0004_pricing_check_domain
application_tables_match_v2_05=True
application_pricing_constraints_present=True
application_pricing_evidence_triggers_match=True
test_alembic_revision=0004_pricing_check_domain
application_readiness_status=200
application_readiness_is_json=True
```

The V2 test database remained the only target for downgrade/re-upgrade proof.
The parent regression at the V2-05B checkpoint passed:

```text
python -m compileall backend alembic: completed successfully
backend regression=39 passed in 281.40s (0:04:41)
frontend regression=20 passed in 10.71s
frontend production build=47 modules transformed; built in 2.32s
```

V2-05 VERIFIED.
