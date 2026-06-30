# API Overview

This overview lists the implemented API groups visible in FastAPI OpenAPI. It is intentionally high-level; use `/docs` or `/openapi.json` for exact request and response schemas.

## System

- `GET /`
- `GET /api/health`
- `GET /api/health/live`
- `GET /api/health/ready`
- `GET /api/system/status`

## Auth and Demo

- `/api/auth/login`
- `/api/auth/me`
- `/api/auth/demo-users`
- `/api/demo/status`
- `/api/demo/seed`
- `/api/demo/reset`
- `/api/demo/scenario/full`
- `/api/demo/guide`

## Pricing Operations

- `/api/products`
- `/api/products/{product_id}`
- `/api/cost-profiles`
- `/api/cost-profiles/{cost_profile_id}`
- `/api/competitors`
- `/api/competitors/{competitor_id}`
- `/api/competitor-prices`
- `/api/quote-preview`
- `/api/candidate-prices`
- `/api/price-validation`
- `/api/explanations/quote`

## Approval, Audit, and Customer Requests

- `/api/approval-requests`
- `/api/approval-requests/{approval_request_id}`
- `/api/approval-requests/{approval_request_id}/approve`
- `/api/approval-requests/{approval_request_id}/reject`
- `/api/audit-logs`
- `/api/audit-logs/{audit_log_id}`
- `/api/customer-quote-requests`
- `/api/customer-quote-requests/{request_id}`
- `/api/customer-quote-requests/{request_id}/status`
- `/api/customer-quote-requests/{request_id}/quote-preview`
- `/api/customer-quote-requests/{request_id}/candidate-prices`

## Price Tables and Simulations

- `/api/price-tables`
- `/api/price-tables/{price_table_id}`
- `/api/price-tables/{price_table_id}/items`
- `/api/price-tables/{price_table_id}/summary`
- `/api/price-tables/{price_table_id}/snapshots`
- `/api/price-tables/compare`
- `/api/price-table-snapshots/{snapshot_id}`
- `/api/price-table-snapshots/compare`
- `/api/pricing-simulations`
- `/api/pricing-simulations/{simulation_id}`
- `/api/scenario-comparisons`
- `/api/scenario-comparisons/{comparison_id}`

## Workflow, Strategy, Dashboard, Reports, and CSV

- `/api/workflow-jobs`
- `/api/workflow-jobs/{job_id}`
- `/api/workflow-jobs/{job_id}/run`
- `/api/workflow-jobs/{job_id}/cancel`
- `/api/strategy-templates`
- `/api/strategy-templates/{template_id}`
- `/api/strategy-templates/{template_id}/candidate-prices`
- `/api/strategy-templates/{template_id}/pricing-simulation`
- `/api/dashboard/summary`
- `/api/dashboard/insights`
- `/api/dashboard/metrics`
- `/api/html-reports`
- `/api/html-reports/{report_id}`
- `/api/html-reports/{report_id}/content`
- `/api/import/products`
- `/api/import/cost-profiles`
- `/api/import/competitor-prices`
- `/api/export/products.csv`
- `/api/export/cost-profiles.csv`
- `/api/export/competitor-prices.csv`

## Notes

- Some endpoints require authentication and role access.
- The API does not automatically approve, activate, or send prices.
- CSV endpoints are implemented as import/export routes, not under a single `/api/csv` prefix.
