# Dashboard Insights

PR-32 adds deterministic operational insights to the QuoteOps AI dashboard.
These insights help an admin quickly see what needs attention before pricing
work continues.

## Deterministic Principle

All insight values are calculated from stored backend data and existing status
fields. AI does not generate KPI numbers, risk scores, validation results,
prices, margins, approval decisions, or operational status values.

Candidate tables are still inactive until an owner explicitly approves them.

## API

```bash
curl http://localhost:8000/api/dashboard/insights
```

Response sections:

- `attention_items`
- `approval_queue`
- `validation_summary`
- `data_quality`
- `quote_request_summary`
- `job_health`
- `audit_activity`
- `system_readiness`

## Attention Items

Attention items are simple rule-based alerts. Each item includes:

- `severity`: `info`, `warning`, or `critical`
- `title`
- `message`
- `related_area`
- optional `count`
- optional frontend anchor route

Current deterministic checks include:

- candidate tables waiting for approval
- validation failures
- validation warnings
- quote requests waiting for follow-up
- failed workflow jobs
- missing active price table
- missing competitor prices
- missing cost profiles
- OpenAI fallback mode

## Data Readiness

Data readiness is based on boolean and count checks only:

- products exist
- competitors exist
- competitor prices exist
- cost profiles exist
- price tables exist
- candidate tables exist

The dashboard does not judge whether sample competitor prices are real market
prices. Seeded prices remain sample data only.

## Approval Queue

The approval queue summarizes generated or reviewed candidate tables, recently
approved/rejected candidate tables, and active/draft price table counts.

The API explicitly reports:

```json
{
  "human_approval_required": true,
  "automatic_activation_enabled": false
}
```

## System Readiness

System readiness exposes safe booleans and labels only:

- backend health available
- database status available
- database type
- OpenAI configured true/false
- fallback mode available
- audit logging available
- job workflow available

It must not expose raw `DATABASE_URL`, passwords, API keys, bearer tokens, or
other secrets.

## Frontend

The frontend dashboard adds an "운영 인사이트" section with:

- attention needed cards
- approval queue count
- validation risk count
- quote request follow-up count
- workflow failure count
- data readiness summary
- recent audit activity summary
- system readiness badges

All sections are visible to authenticated roles as read-only operational
context. Owner-only actions still require backend owner authorization.

## Limitations

- This is not external monitoring or analytics.
- No forecasting, new pricing formulas, new validation rules, or new candidate
  generation strategies are added.
- Insights summarize stored records; they do not approve candidates, activate
  price tables, or change prices.
