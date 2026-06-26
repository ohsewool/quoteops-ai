# Exportable Reports

PR-34 adds print-friendly HTML reports for QuoteOps AI pricing operations.

Reports are review artifacts only. They do not approve candidates, activate
price tables, change prices, run validation, or generate new candidate tables.

## Report Types

Supported HTML reports:

- Candidate Price Report: candidate table metadata, item rows, stored candidate
  prices, cost-floor fields, market reference fields, reason codes, warnings,
  latest validation status, and approval status.
- Validation Report: latest saved validation result for a candidate table,
  summary JSON, item-level checks, check codes, warnings, and blockers.
- Scenario Comparison Report: deterministic comparison between stored
  `price_table` and/or `candidate_table` scenarios.
- Approval Evidence Report: approval/rejection history and related audit events
  for a candidate table.
- Operations Snapshot Report: dashboard KPI counts, attention items, and recent
  audit activity from stored backend data.

## API Endpoints

All report endpoints require an authenticated admin bearer token. Reports are
read-only, so owner, manager, and viewer roles may generate them.

```bash
curl http://localhost:8000/api/reports/candidate/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

curl http://localhost:8000/api/reports/validation/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

curl "http://localhost:8000/api/reports/scenario-comparison?base_type=price_table&base_id=1&compare_type=candidate_table&compare_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

curl http://localhost:8000/api/reports/approval/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

curl http://localhost:8000/api/reports/operations-snapshot \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Responses use `text/html`. Open the response in a browser and use the browser
print dialog to save as PDF.

## Deterministic Data Principle

All report numbers come from stored data or existing deterministic backend
calculations:

- stored price table rows
- stored candidate table rows
- stored validation results
- stored approval rows
- stored audit log rows
- existing deterministic scenario comparison service
- existing deterministic dashboard KPI and insight services

AI does not generate prices, margins, validation results, comparison numbers,
risk scores, KPI values, approval decisions, or final recommendations.

Reports may include only existing stored operational facts. Missing market,
cost, validation, approval, or comparison data is shown as missing; the report
does not invent replacement values.

## Frontend Workflow

The admin workspace includes a Korean-first "보고서 내보내기" section.

It can generate:

- 후보 가격표 보고서
- 검증 보고서
- 시나리오 비교 보고서
- 승인 증빙 보고서
- 운영 스냅샷 보고서

The frontend fetches protected report HTML with the bearer token, previews it in
an iframe, and opens a temporary local browser tab for print/PDF export. Tokens
are not placed in report URLs.

## Role Behavior

Backend permission checks are the source of truth.

- `owner`: can generate all PR-34 reports.
- `manager`: can generate all PR-34 read-only reports.
- `viewer`: can generate all PR-34 read-only reports.

Report generation does not bypass owner-only approval. Candidate activation
still requires explicit human owner action through the approval endpoint.

## Audit Logging

Successful report generation creates a compact `report_generated` audit log
event with:

- report type
- entity type
- entity id when applicable
- actor identity and role
- request IP and user agent when available

The full report HTML is not stored in the audit log.

## Secret Safety

Reports must not expose:

- raw `DATABASE_URL`
- database passwords
- OpenAI API keys
- bearer tokens
- private environment values
- stack traces

The report service only renders operational fields already used in admin views
or safe aggregate counts.

## Limitations

- PDF generation is not implemented as a backend dependency. Use browser
  print-to-PDF from the HTML report.
- Reports are point-in-time snapshots and are not immutable legal audit
  documents.
- Validation reports show the latest saved validation result; they do not run
  validation.
- Scenario comparison reports use explicit IDs and do not persist comparison
  results.
- Operations snapshot metrics are limited to existing dashboard KPI and insight
  data.
