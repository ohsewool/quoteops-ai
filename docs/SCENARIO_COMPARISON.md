# Scenario Comparison

PR-33 adds Pricing Scenario Comparison v2 for QuoteOps AI. It helps admins
compare stored pricing scenarios before human approval.

## Deterministic Principle

Scenario comparison is read-only. All numbers come from stored backend data:

- internal price table rows
- candidate table rows
- saved validation results
- stored status fields

AI does not generate prices, margins, comparison numbers, validation results,
risk scores, approval recommendations, or final decision labels.

## API

```bash
curl -X POST http://localhost:8000/api/pricing-scenarios/compare \
  -H "Content-Type: application/json" \
  -d '{
    "base": {
      "scenario_type": "price_table",
      "scenario_id": 1
    },
    "compare": {
      "scenario_type": "candidate_table",
      "scenario_id": 1
    }
  }'
```

Supported scenario types:

- `price_table`
- `candidate_table`

Strategy templates are not compared directly because they are generation
settings, not stored price rows. Compare the candidate tables generated from
different templates instead.

## Response Sections

The response includes:

- `base`
- `compare`
- `summary`
- `item_differences`
- `validation_comparison`
- `approval_readiness`
- `warnings`
- `notes`

## Comparison Metrics

The backend calculates only metrics that can be derived from stored rows:

- total compared items
- matching item count
- missing item count
- average price difference
- minimum and maximum price difference
- average price difference rate
- average margin difference when stored margin data exists
- price increase count
- price decrease count
- unchanged count
- warning count

Items are matched by stable keys:

```text
product_id + quantity + normalized option_summary
```

No fuzzy matching is used. Missing rows are reported with warning codes such as
`MISSING_BASE_ITEM`, `MISSING_COMPARE_ITEM`, and `ITEM_MATCH_GAPS`.

## Validation Comparison

Validation comparison uses only the latest saved validation result for candidate
tables. It reports:

- overall status
- risk level
- saved validation summary
- latest validation timestamp

If a candidate table has not been validated, the response includes a missing
validation note. The endpoint does not run validation and does not add new
validation rules.

## Approval Readiness

Approval readiness is a deterministic status summary. It checks whether:

- the scenario is a candidate table
- a saved validation result exists
- the latest validation failed
- the candidate is pending, approved, or rejected
- an active price table exists for the product

Approval readiness does not approve or reject anything. Owner approval is still
required before a candidate can become active.

## Frontend

The frontend comparison section now includes:

- scenario type selector
- price table / candidate selector
- summary comparison cards
- item-level difference table
- validation status display
- approval readiness display
- warnings and missing-data messages
- role-aware link text for owner approval review

The UI copy states that AI does not decide price differences, margins, or
approval status.

## Limitations

- Candidate tables must exist before they can be compared.
- The current frontend exposes loaded price tables and the latest generated
  candidate table; the API supports candidate-to-candidate comparison when IDs
  are provided directly.
- Strategy templates are compared through generated candidate tables, not as
  standalone scenarios.
- Scenario comparison does not activate price tables, run validation, generate
  candidates, or change approval state.
