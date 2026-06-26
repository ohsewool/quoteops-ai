# UI Navigation

PR-30 organizes the existing QuoteOps AI workspace into clearer navigation
groups. It does not add pricing behavior, change backend business rules, or
remove existing screens.

## Navigation Groups

### Overview

- Dashboard: operations KPIs and deterministic dashboard insights calculated
  from stored backend data

### Pricing Data

- Products: product and option catalog administration
- Data Summary: product, market reference, cost/margin, and quote preview cards
- Price Tables: active internal price tables

### Price Operations

- Candidate Generation: deterministic candidate table generation
- Strategy Templates: reusable generation settings
- Validation / Approval: validation result, AI/fallback explanation, agent
  timeline, and human owner approval controls

### Requests And Simulation

- Quote Requests: customer quote request submission and admin review
- Simulation: compare candidate table revenue and margin against a baseline
- Price Table Comparison: compare table versions, candidate scenarios, and
  approval readiness before owner review
- Reports: generate print-friendly HTML reports for candidate, validation,
  scenario comparison, approval evidence, and operations snapshot review

### Operations

- Workflow Jobs: persisted workflow job and step status
- Audit Logs: backend operation traceability
- CSV Import / Export: bulk pricing data operations

### Admin

- Account / Role: current admin role and role guidance
- System Status: backend, database, AI fallback, audit, and job status

## Recommended Demo Order

1. Dashboard
2. Products
3. Pricing Data summary
4. Price Tables
5. Candidate Generation
6. Validation / Approval
7. AI Explanation panel
8. Reports
9. Audit Logs
10. Workflow Jobs
11. System Status

## Role-Aware Navigation

The frontend navigation uses the logged-in admin role to explain expected
access:

- `owner`: sees all tools, including final candidate approval and activation
- `manager`: sees operational pricing tools but cannot approve or activate
  candidate tables
- `viewer`: can review read-only sections and should not mutate pricing data

Frontend visibility is a convenience only. Backend role enforcement remains the
source of truth.

## Known Limitations

- The workspace is still a single-page React screen with anchor-based
  navigation, not a multi-route app.
- PR-31 standardizes readable Korean loading, empty, error, permission, backend
  unavailable, and OpenAI fallback states across the main workspace sections.
- Demo data tools remain CLI-only and are not exposed as a frontend reset panel.

## Safety Notes

- AI does not generate numeric prices.
- AI does not approve or reject candidate tables.
- Candidate tables are not activated automatically.
- Competitor prices are manually entered reference data.
- No web scraping, payment, OAuth, Redis, Celery, or external monitoring service
  is introduced by PR-30.
