# QuoteOps AI

QuoteOps AI is an AI-assisted pricing and quoting operations system for small print, sticker, and custom-product businesses.

It helps generate and validate quantity-based price table candidates using competitor prices, internal cost, minimum margin, competitor type, and pricing strategy.

The target user is a small print shop, sticker/label shop, or custom-product operator who needs safe quantity-based pricing without blindly copying competitor prices.

Core workflow:

```text
manual competitor references + internal cost/margin + pricing strategy
-> deterministic candidate price table
-> deterministic validation
-> AI or fallback explanation
-> human owner approval
-> active price table for quote preview
```

Core safety principle: AI may explain deterministic results, but it does not generate numeric prices, approve candidates, or activate price tables.

## Current Status

This repository is a **release-candidate MVP** after PR-35 final production hardening.

Included:

- React + Vite frontend
- Tailwind CSS
- Framer Motion
- lucide-react
- Recharts dependency
- FastAPI backend
- `/api/health` endpoint
- SQLite and PostgreSQL schema initialization through `DATABASE_URL`
- sample seed data for MVP products and reference tables
- basic read-only APIs
- deterministic quote preview API
- customer quote request submission and admin review APIs
- manual competitor price management APIs
- deterministic market reference summary API
- internal cost profile management APIs
- manual internal price table management APIs
- deterministic candidate price generation API
- generated candidate table storage
- deterministic candidate validation API
- persisted validation results
- agent timeline logs
- AI explanation API with local fallback
- human approval and rejection API for candidate price tables
- approval history storage
- approved candidate conversion into active internal price tables
- deterministic price table comparison and change history APIs
- audit log persistence, API, and frontend operation history viewer
- persisted workflow jobs and job-step monitor for pricing analysis
- basic admin authentication with owner / manager / viewer roles
- product catalog management APIs and admin UI
- CSV import/export for pricing operations
- deterministic pricing simulation dashboard
- deterministic operations KPI dashboard
- product/category strategy template management
- exportable print-friendly HTML reports
- Playwright E2E smoke tests
- Render deployment foundation
- local workflow smoke checks
- starter project docs

Not included yet:

- web scraping
- payment or ecommerce checkout
- customer accounts
- automatic approval
- AI-generated numeric prices
- external monitoring services
- Redis or Celery workers

## Release Candidate Docs

- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Demo flow](docs/DEMO_FLOW.md)
- [Operations checklist](docs/OPERATIONS_CHECKLIST.md)
- [Deployment notes](docs/DEPLOYMENT.md)
- [PostgreSQL production runbook](docs/POSTGRESQL_RUNBOOK.md)
- [Demo data tools](docs/DEMO_DATA.md)
- [UI navigation guide](docs/UI_NAVIGATION.md)
- [UX states guide](docs/UX_STATES.md)
- [Dashboard insights guide](docs/DASHBOARD_INSIGHTS.md)
- [Scenario comparison guide](docs/SCENARIO_COMPARISON.md)
- [Exportable reports guide](docs/REPORTS.md)

## Local Development

### Backend

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend reads database, CORS, and optional AI explanation settings through
the centralized backend settings module. For local development, the database
default is:

```dotenv
APP_ENV=development
DATABASE_URL=sqlite:///./quoteops.db
```

PR-24 adds real PostgreSQL support while keeping SQLite as the default local
database. Supported database URLs:

```dotenv
# Local default
DATABASE_URL=sqlite:///./quoteops.db

# Managed PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/dbname
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
```

On app startup, the backend safely creates the SQLite file and parent directory
when SQLite is used, connects to PostgreSQL when `DATABASE_URL` points to a
PostgreSQL database, and creates any missing tables. Startup does not drop,
reset, or overwrite existing data.

Seed data is safe to rerun. The base MVP seed inserts only when the `products`
table is empty. Catalog metadata, strategy templates, and the local/demo admin
use unique keys or existence checks to avoid duplication on normal restarts.
Seeded prices are sample data only, not real market prices.

For repeatable local or staging walkthroughs, PR-29 adds CLI-only demo seed and
reset tools. PR-35 blocks those tools when `APP_ENV=production` unless
`ENABLE_DEMO_TOOLS=true` is set explicitly. See
[docs/DEMO_DATA.md](docs/DEMO_DATA.md) before resetting data.

PostgreSQL support uses `psycopg[binary]`, installed through
`requirements.txt`. If `DATABASE_URL` is invalid, the driver is missing, the
database refuses the connection, or a managed provider requires SSL settings,
the backend will fail startup with the underlying connection error. Never commit
real database credentials.

For production database setup, migration-readiness notes, Render PostgreSQL
verification, and the non-destructive smoke check script, see
[docs/POSTGRESQL_RUNBOOK.md](docs/POSTGRESQL_RUNBOOK.md).

### Health And Operations Status

PR-25 adds production-oriented health and diagnostics endpoints. They are safe
for deployment smoke checks and do not expose API keys, database passwords,
tokens, or raw `DATABASE_URL` values.

Health endpoints:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/ready
curl http://localhost:8000/api/health/db
curl http://localhost:8000/api/system/status
```

`GET /api/health` is lightweight and returns service status, version, timestamp,
and whether LLM mode is enabled.

`GET /api/health/ready` verifies whether the app can serve requests. It checks:

- app startup
- database connectivity
- required table access
- seed data presence

`GET /api/health/db` checks database connectivity and returns only safe fields:

- database type: `sqlite`, `postgresql`, or `unsupported`
- connectivity status
- sanitized error message if unavailable

`GET /api/system/status` returns admin-facing operational diagnostics:

- backend status and environment name
- database type and connectivity
- whether `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and `ALLOWED_ORIGINS` are configured
- fallback explanation availability
- auth, audit logging, and job workflow availability

The frontend includes a Korean-first System Status panel with backend status,
database status/type, AI explanation mode, audit logging status, job workflow
status, last checked time, and a refresh button.

Startup logs are intentionally safe. They record app startup, selected database
type, schema/seed completion, OpenAI fallback mode, and CORS origins, but never
log secrets.

Operations troubleshooting:

- database connection failure: check `DATABASE_URL`, network allowlist, database status, and `/api/health/db`
- invalid `DATABASE_URL`: use `sqlite:///...`, `postgresql://...`, or `postgresql+psycopg://...`
- missing OpenAI key: the backend still starts and uses deterministic fallback explanation
- CORS misconfiguration: set `ALLOWED_ORIGINS` to the exact frontend origin
- frontend cannot reach backend: verify `VITE_API_BASE_URL`, backend health, and browser console network errors

Production operations notes:

- use managed PostgreSQL for production-like deployments
- keep secrets in environment variables or a managed secret store
- check `/api/health/ready` after every deployment
- do not expose secret values publicly or in frontend `VITE_*` variables

Open:

```text
http://localhost:8000/api/health
http://localhost:8000/api/health/ready
http://localhost:8000/api/health/db
http://localhost:8000/api/system/status
http://localhost:8000/api/auth/login
http://localhost:8000/api/auth/me
http://localhost:8000/api/products
http://localhost:8000/api/competitors
http://localhost:8000/api/competitor-prices
http://localhost:8000/api/cost-profiles
http://localhost:8000/api/price-tables
http://localhost:8000/api/quote-requests
http://localhost:8000/api/candidate-prices/generate
http://localhost:8000/api/candidate-prices/1/validate
http://localhost:8000/api/candidate-prices/1/explain
http://localhost:8000/api/candidate-prices/1/approve
http://localhost:8000/api/candidate-prices/1/reject
http://localhost:8000/api/price-tables/1/compare
http://localhost:8000/api/pricing-scenarios/compare
http://localhost:8000/api/reports/candidate/1
http://localhost:8000/api/reports/validation/1
http://localhost:8000/api/reports/scenario-comparison
http://localhost:8000/api/reports/approval/1
http://localhost:8000/api/reports/operations-snapshot
http://localhost:8000/api/price-tables/history
http://localhost:8000/api/products/1/price-table-history
http://localhost:8000/api/strategy-templates
http://localhost:8000/api/products/1/strategy-templates
http://localhost:8000/api/audit-logs
http://localhost:8000/api/simulations/pricing
http://localhost:8000/api/dashboard/kpis
http://localhost:8000/api/dashboard/insights
http://localhost:8000/api/workflows/pricing-analysis
http://localhost:8000/api/jobs
http://localhost:8000/api/approvals
http://localhost:8000/api/agent-logs
http://localhost:8000/docs
```

Optional AI explanation environment variables:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

If `OPENAI_API_KEY` is empty, the backend still starts and returns a
deterministic fallback explanation. AI explanation is optional and never
generates numeric prices.

### Admin Authentication

PR-13 adds basic admin authentication for the SaaS-style admin workspace.
Passwords are never stored in plain text. The backend stores PBKDF2-SHA256
password hashes and stores only hashed session tokens.

Local/demo seed credentials:

```dotenv
SEED_DEMO_ADMIN=true
DEMO_ADMIN_EMAIL=admin@quoteops.local
DEMO_ADMIN_PASSWORD=quoteops-demo-admin
```

These credentials are for local demo use only. Do not use them for a real
deployment. Set `SEED_DEMO_ADMIN=false` or replace the seeded admin before any
public environment is exposed.

Auth endpoints:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@quoteops.local",
    "password": "quoteops-demo-admin"
  }'

curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Most admin mutation examples in this README require a bearer token from
`POST /api/auth/login`, even when the compact curl example omits the header for
readability. Public endpoints include health checks, product reads, customer
quote request submission, and quote preview.

Supported roles:

- `owner`: can manage catalog and pricing operations, run workflows, import/export CSV, validate/explain candidates, and approve or reject candidate price tables
- `manager`: can manage pricing operations, competitor data, cost profiles, draft/internal price table rows, strategy templates, CSV operations, quote request review, candidate generation, validation, AI/fallback explanations, simulations, dashboards, and workflows
- `viewer`: read-only admin role for dashboards, products, competitors, price tables, candidates, validation results, quote requests, audit logs, simulations, and workflow/job history

PR-23 strengthens role enforcement on important admin mutation endpoints.
Approval still requires explicit human `owner` action. AI does not approve,
reject, change prices, or generate numeric price values.

Permission matrix:

| Operation | owner | manager | viewer |
|---|---:|---:|---:|
| View dashboards and pricing data | yes | yes | yes |
| Manage products and product options | yes | no | no |
| Manage competitors and competitor prices | yes | yes | no |
| Manage cost profiles | yes | yes | no |
| Manage price tables and price table items | yes | yes | no |
| Generate candidate price tables | yes | yes | no |
| Run deterministic validation | yes | yes | no |
| Generate AI/fallback explanation from deterministic facts | yes | yes | no |
| Approve or reject candidate tables | yes | no | no |
| Import/export CSV | yes | yes | no |
| Manage strategy templates | yes | yes | no |
| Run persisted workflows | yes | yes | no |
| Update or quote customer quote requests | yes | yes | no |

Protected operation examples:

```bash
# Missing bearer token returns 401
curl -X POST http://localhost:8000/api/candidate-prices/generate \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "option_summary": "A3 / snow paper / single-sided / full color", "quantities": [100]}'

# Viewer token on a mutation returns 403
curl -X POST http://localhost:8000/api/cost-profiles \
  -H "Authorization: Bearer VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 100,
    "option_summary": "A3 / snow paper / single-sided / full color",
    "unit_cost": 80,
    "fixed_cost": 10000,
    "minimum_margin_rate": 0.25,
    "minimum_price": 30000
  }'
```

API behavior:

- `401`: bearer token is missing, invalid, expired, or revoked
- `403`: authenticated admin exists, but the role is not allowed for the operation
- forbidden role attempts are logged as lightweight audit events when possible

Frontend behavior:

- the logged-in admin role is displayed in the workspace header
- viewer accounts see a read-only state and disabled mutation controls
- manager accounts can run pricing operations but cannot approve or reject candidate tables
- owner-only approval buttons are disabled for non-owner roles
- backend role checks are still enforced even if the UI is bypassed

Limitations:

- this is MVP admin RBAC, not an enterprise permission system
- the local demo auth uses bearer sessions stored in SQLite
- production should use stronger session security, secret handling, transport security, and managed identity/session storage later

### Seed Data

The local seed data is clearly sample data, not real market pricing.

It includes:

- A3 Flyer product
- Product Sticker product
- product options for both MVP products
- sample large online, local shop, and premium brand competitors
- manually entered sample competitor price references
- basic cost profiles
- one draft price table
- one active price table

### Demo Data Tools

PR-29 adds CLI-only demo seed/reset tooling for local demos, portfolio reviews,
and staging verification. Demo records are clearly labeled as sample data and
are not real market prices.

```bash
py -3 scripts/seed_demo_data.py
py -3 scripts/reset_demo_data.py --confirm RESET_DEMO_DATA
```

The seed is idempotent. The reset command requires explicit confirmation and
removes only known demo records before reseeding. No backend demo reset API or
frontend reset panel is exposed in PR-29. See
[docs/DEMO_DATA.md](docs/DEMO_DATA.md) for safety notes, PostgreSQL usage, and
troubleshooting.

### Product Catalog Management

PR-14 keeps the MVP products, A3 Flyer and Product Sticker, and adds a small
catalog management layer so future products can reuse the same pricing flow.
This is not an ecommerce catalog and does not add checkout, inventory, image
upload, shipping calculation, customer accounts, or payment.

Catalog structure:

- `products`: sellable product definitions used by cost profiles, competitor references, quotes, candidate generation, validation, AI explanation, approval, and active price tables
- `product_options`: reusable option rows such as size, material, paper type, side type, and quantity hints
- `product_categories`: lightweight grouping for print products, stickers/labels, and future custom goods
- `quantity_ladders`: sample quantity presets for admin guidance only

Seeded category examples:

- `print-products`: flyers, posters, banners, business cards
- `sticker-label-products`: product stickers, labels, packaging stickers
- `custom-goods`: future mugs, T-shirts, eco bags, acrylic keyrings, and other goods

Catalog APIs:

```bash
curl http://localhost:8000/api/products
curl http://localhost:8000/api/product-options
curl http://localhost:8000/api/product-categories
curl http://localhost:8000/api/quantity-ladders
```

Create a future product shell:

```bash
curl -X POST http://localhost:8000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Business Card",
    "slug": "business-card",
    "description": "Future product shell using the same pricing flow.",
    "category_id": 1,
    "quantity_ladder_id": 1,
    "is_active": true
  }'
```

Add a product option:

```bash
curl -X POST http://localhost:8000/api/product-options \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "option_type": "paper_type",
    "option_name": "Paper Type",
    "option_value": "Snow paper",
    "sort_order": 10,
    "is_active": true
  }'
```

Update or deactivate:

```bash
curl -X PATCH http://localhost:8000/api/products/1 \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated product note"}'

curl -X DELETE http://localhost:8000/api/products/1

curl -X PATCH http://localhost:8000/api/product-options/1 \
  -H "Content-Type: application/json" \
  -d '{"sort_order": 20}'

curl -X DELETE http://localhost:8000/api/product-options/1
```

`DELETE` deactivates products and options instead of hard-deleting them, so
existing cost profiles, competitor prices, price tables, candidate tables, and
approval history remain intact.

New products do not get a separate pricing path. Before a new product can
produce real quotes or candidates, admins must still add matching cost
profiles, manually entered competitor reference prices, price table rows or
candidate inputs, then run validation, AI explanation, and human approval.

Limitations:

- categories and quantity ladders are lightweight helpers, not full catalog taxonomy
- no product images, variants inventory, shipping rules, checkout, or customer accounts
- no new pricing formulas were added in PR-14
- option summary strings still need to match across cost profiles, competitor prices, and price table rows

### Strategy Template Management

PR-21 adds reusable strategy templates for product-specific or
category-specific candidate generation settings. Templates make admin workflow
faster, but they do not create active prices by themselves.

Strategy templates can store:

- `name`, `slug`, and `description`
- optional `product_id`
- optional `product_category_id`
- `strategy_name`: `margin_protect`, `balanced_market`, or `premium_local`
- `market_position`: `conservative`, `balanced`, or `premium`
- `margin_bias`: `low`, `medium`, or `high`
- `competitor_weight_mode`: `ignore_large_online_lowest`, `balanced_reference`, or `premium_reference`
- `rounding_unit`: `100`, `500`, or `1000`
- `is_default`
- `is_active`

Seeded local examples are sample defaults only:

- A3 Flyer Balanced Template
- Sticker Margin Protect Template
- Premium Local Print Template

List and inspect templates:

```bash
curl http://localhost:8000/api/strategy-templates
curl http://localhost:8000/api/strategy-templates/1
curl http://localhost:8000/api/products/1/strategy-templates
```

Create a template:

```bash
curl -X POST http://localhost:8000/api/strategy-templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "A3 Local Balanced",
    "slug": "a3-local-balanced",
    "description": "Sample reusable settings for A3 flyer candidates.",
    "product_id": 1,
    "product_category_id": 1,
    "strategy_name": "balanced_market",
    "market_position": "balanced",
    "margin_bias": "medium",
    "competitor_weight_mode": "balanced_reference",
    "rounding_unit": 100,
    "is_default": false,
    "is_active": true
  }'
```

Update or archive a template:

```bash
curl -X PATCH http://localhost:8000/api/strategy-templates/1 \
  -H "Content-Type: application/json" \
  -d '{"margin_bias": "high", "rounding_unit": 500}'

curl -X DELETE http://localhost:8000/api/strategy-templates/1
```

`DELETE` archives the template by setting `is_active = false`; it does not
delete candidate tables, price tables, or quote data.

Candidate generation can use a template:

```bash
curl -X POST http://localhost:8000/api/candidate-prices/generate \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "option_summary": "A3 / snow paper / single-sided / full color",
    "quantities": [100, 500],
    "strategy_template_id": 1
  }'
```

When `strategy_template_id` is provided, it takes priority over
`strategy_name`. The backend loads the active template, uses its
`strategy_name`, applies the template `rounding_unit`, and includes
`strategy_template` information in the response. If no template is provided,
the existing `strategy_name` input works as before.

All candidate prices are still calculated by deterministic backend logic.
Templates do not approve candidates, do not activate price tables, do not call
AI to generate numeric prices, and do not bypass validation or human approval.

### CSV Import And Export

PR-15 adds CSV-first bulk operations for pricing data. These endpoints are for
admin workflow speed, not automation of competitor collection. CSV upload does
not scrape websites, does not generate prices with AI, does not approve
candidates, and does not activate price tables.

Competitor price import format:

```csv
competitor_name,product_slug,quantity,option_summary,price,source_note,collected_at
Sample Local Print Shop,a3-flyer,100,A3 / snow paper / single-sided / full color,36500,Manual sample reference only,2026-06-24T00:00:00+00:00
```

Cost profile import format:

```csv
product_slug,quantity,option_summary,unit_cost,fixed_cost,minimum_margin_rate,minimum_price
a3-flyer,200,A3 / snow paper / single-sided / full color,90,15000,0.25,44000
```

Import endpoints accept raw `text/csv` bodies:

```bash
curl -X POST http://localhost:8000/api/import/competitor-prices \
  -H "Content-Type: text/csv" \
  --data-binary @competitor-prices.csv

curl -X POST http://localhost:8000/api/import/cost-profiles \
  -H "Content-Type: text/csv" \
  --data-binary @cost-profiles.csv
```

Import validation is deterministic and row-level. The backend validates that:

- product slugs exist
- competitor names exist for competitor price import
- quantity is positive
- price is positive
- unit cost and fixed cost are non-negative
- minimum margin rate is between 0 and 1
- option summary is present
- sample prices are not claimed as real market prices

If any row fails validation, the import returns `validation_failed` and does
not insert the CSV rows:

```json
{
  "status": "validation_failed",
  "valid_count": 1,
  "error_count": 2,
  "inserted_count": 0,
  "errors": [
    {
      "row": 5,
      "field": "price",
      "message": "Price must be positive."
    }
  ]
}
```

Export endpoints:

```bash
curl http://localhost:8000/api/export/competitor-prices
curl http://localhost:8000/api/export/cost-profiles
curl http://localhost:8000/api/export/price-tables/1/items
curl http://localhost:8000/api/export/candidate-tables/1/items
```

Exported columns:

- competitor prices: `competitor_name,product_slug,quantity,option_summary,price,source_note,collected_at`
- cost profiles: `product_slug,quantity,option_summary,unit_cost,fixed_cost,minimum_margin_rate,minimum_price`
- price table items: `price_table_id,quantity,option_summary,final_price,margin_rate`
- candidate table items: `candidate_table_id,quantity,candidate_price,unit_price,cost_floor_price,estimated_margin_rate,market_lowest_price,market_average_price,market_highest_price,decision_reason_codes,warnings`

Human approval is still required before candidate prices become active. CSV
import/export never bypasses validation, explanation, approval, or active price
table conversion rules.

### Read-only API Examples

```bash
curl http://localhost:8000/api/products
curl http://localhost:8000/api/products/1
curl http://localhost:8000/api/competitors
curl http://localhost:8000/api/competitor-prices
curl http://localhost:8000/api/cost-profiles
curl http://localhost:8000/api/price-tables
```

### Competitor Price Management

Competitor prices are manually entered reference data. They are not scraped,
not treated as real-time market truth, and not automatically copied into
internal price tables.

Create a competitor:

```bash
curl -X POST http://localhost:8000/api/competitors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample Neighborhood Printer",
    "competitor_type": "local_shop",
    "description": "Manual reference competitor",
    "is_active": true
  }'
```

Update a competitor:

```bash
curl -X PATCH http://localhost:8000/api/competitors/1 \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated manual reference note"
  }'
```

Create a competitor price:

```bash
curl -X POST http://localhost:8000/api/competitor-prices \
  -H "Content-Type: application/json" \
  -d '{
    "competitor_id": 1,
    "product_id": 1,
    "quantity": 100,
    "option_summary": "A3 / snow paper / single-sided / full color",
    "price": 33000,
    "source_note": "Manual sample reference only"
  }'
```

Update a competitor price:

```bash
curl -X PATCH http://localhost:8000/api/competitor-prices/1 \
  -H "Content-Type: application/json" \
  -d '{
    "price": 34000,
    "source_note": "Updated manually entered reference"
  }'
```

Delete a competitor price:

```bash
curl -X DELETE http://localhost:8000/api/competitor-prices/1
```

### Market Reference API

`GET /api/market-reference` returns grouped competitor price references and
deterministic summary numbers for a selected product, quantity, and option
summary. These numbers are simple reference statistics only; QuoteOps AI does
not blindly follow the lowest competitor price.

```bash
curl "http://localhost:8000/api/market-reference?product_slug=a3-flyer&quantity=100&option_summary=A3%20/%20snow%20paper%20/%20single-sided%20/%20full%20color"
```

Example response:

```json
{
  "product_id": 1,
  "product_name": "A3 Flyer",
  "quantity": 100,
  "option_summary": "A3 / snow paper / single-sided / full color",
  "competitor_prices": [
    {
      "competitor_name": "Sample Large Online Print Mall",
      "competitor_type": "large_online",
      "price": 32000.0,
      "source_note": "Sample manually entered reference price; not real market data.",
      "collected_at": "2026-06-24T00:00:00+00:00"
    }
  ],
  "summary": {
    "lowest_price": 32000.0,
    "highest_price": 32000.0,
    "average_price": 32000.0,
    "count": 1
  }
}
```

### Quote Preview API

`POST /api/quotes/preview` returns a deterministic customer quote preview.
The LLM does not generate numeric prices. The backend calculates the result by:

1. matching an active price table item for the product, quantity, and option summary,
2. falling back to a matching cost profile if no active price table row exists,
3. returning a clear error when neither source can be used.

Active price table match example:

```bash
curl -X POST http://localhost:8000/api/quotes/preview \
  -H "Content-Type: application/json" \
  -d '{
    "product_slug": "product-sticker",
    "quantity": 100,
    "option_summary": "50mm circle / standard paper / matte coating"
  }'
```

Example response:

```json
{
  "product_id": 2,
  "product_name": "Product Sticker",
  "quantity": 100,
  "option_summary": "50mm circle / standard paper / matte coating",
  "quote_price": 31000.0,
  "unit_price": 310.0,
  "calculation_source": "active_price_table",
  "price_table_name": "Sample sticker active table",
  "warnings": []
}
```

Cost profile fallback example:

```bash
curl -X POST http://localhost:8000/api/quotes/preview \
  -H "Content-Type: application/json" \
  -d '{
    "product_slug": "a3-flyer",
    "quantity": 100,
    "option_summary": "A3 / snow paper / single-sided / full color"
  }'
```

### Customer Quote Request Flow

PR-17 adds a lightweight customer quote request flow. This is not ecommerce
checkout, not payment, not a cart, and not a customer account system. A
customer submits a request, and an admin reviews it before running a
deterministic quote preview.

Quote request status values:

- `submitted`: customer request was received; no price has been calculated
- `reviewing`: admin is checking details
- `quoted`: admin ran deterministic quote preview and stored the preview result
- `rejected`: admin declined or cannot quote the request
- `archived`: request is retained but no longer active

Submit a request:

```bash
curl -X POST http://localhost:8000/api/quote-requests \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 2,
    "requester_name": "Sample Customer",
    "requester_email": "customer@example.com",
    "requester_phone": "010-0000-0000",
    "company_name": "Sample Company",
    "quantity": 100,
    "option_summary": "50mm circle / standard paper / matte coating",
    "request_note": "Local demo quote request."
  }'
```

Submission validates that the product exists, quantity is positive, and
requester name/email are present. It stores the request as `submitted` and does
not calculate a price.

List and inspect requests:

```bash
curl http://localhost:8000/api/quote-requests
curl http://localhost:8000/api/quote-requests/1
curl "http://localhost:8000/api/quote-requests?status=submitted"
```

Update admin status or note:

```bash
curl -X PATCH http://localhost:8000/api/quote-requests/1 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "reviewing",
    "admin_note": "Checking options before quoting."
  }'
```

Preview and store a quote from a request:

```bash
curl -X POST http://localhost:8000/api/quote-requests/1/preview-quote
```

The preview endpoint loads the stored request and reuses the same deterministic
quote preview logic described above:

1. active price table match,
2. cost profile fallback,
3. clear no-data error.

It stores `quoted_price`, `quoted_unit_price`, `quote_source`, and changes the
request status to `quoted`. AI does not generate quote request prices, does not
review the request, and does not approve anything.

Example response:

```json
{
  "quote_request": {
    "id": 1,
    "product_id": 2,
    "product_name_snapshot": "Product Sticker",
    "requester_name": "Sample Customer",
    "requester_email": "customer@example.com",
    "requester_phone": "010-0000-0000",
    "company_name": "Sample Company",
    "quantity": 100,
    "option_summary": "50mm circle / standard paper / matte coating",
    "request_note": "Local demo quote request.",
    "status": "quoted",
    "quoted_price": 31000.0,
    "quoted_unit_price": 310.0,
    "quote_source": "active_price_table",
    "admin_note": null,
    "created_at": "2026-06-24T00:00:00+00:00",
    "updated_at": "2026-06-24T00:00:00+00:00"
  },
  "quote_preview": {
    "product_id": 2,
    "product_name": "Product Sticker",
    "quantity": 100,
    "option_summary": "50mm circle / standard paper / matte coating",
    "quote_price": 31000.0,
    "unit_price": 310.0,
    "calculation_source": "active_price_table",
    "price_table_name": "Sample sticker active table",
    "warnings": []
  }
}
```

The frontend includes a public quote request form and a protected admin review
section. Admins can view requests, mark status, add an admin note, and run the
deterministic preview. The flow intentionally stops at quote request handling;
customer accounts, payment, checkout, email delivery, and shipping logic are
not included.

### Internal Cost And Price Table Management

Internal cost profiles are business-owned data used to protect margin and
sustainability. Competitor prices are reference data only and are not
automatically copied into internal price tables.

Price table statuses:

- `draft`: editable manual work-in-progress
- `active`: used by quote preview when a matching row exists
- `archived`: retained for history but not used for active quotes

When a price table is made `active`, the backend archives other active tables
for the same product so only one active table per product remains.

Internal price tables remain manually managed. PR-06 generated candidates are
stored separately and do not automatically become active price tables.

Create a cost profile:

```bash
curl -X POST http://localhost:8000/api/cost-profiles \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 100,
    "option_summary": "A3 / snow paper / single-sided / full color",
    "unit_cost": 120,
    "fixed_cost": 12000,
    "minimum_margin_rate": 0.25,
    "minimum_price": 32000
  }'
```

Update a cost profile:

```bash
curl -X PATCH http://localhost:8000/api/cost-profiles/1 \
  -H "Content-Type: application/json" \
  -d '{
    "minimum_margin_rate": 0.3,
    "minimum_price": 35000
  }'
```

Delete a cost profile:

```bash
curl -X DELETE http://localhost:8000/api/cost-profiles/1
```

Create a draft price table:

```bash
curl -X POST http://localhost:8000/api/price-tables \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "name": "Manual A3 draft table",
    "status": "draft",
    "strategy_name": "Manual Pricing"
  }'
```

Update or activate a price table:

```bash
curl -X PATCH http://localhost:8000/api/price-tables/1 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active"
  }'
```

Archive a price table:

```bash
curl -X DELETE http://localhost:8000/api/price-tables/1
```

Create a price table item:

```bash
curl -X POST http://localhost:8000/api/price-tables/1/items \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 100,
    "option_summary": "A3 / snow paper / single-sided / full color",
    "final_price": 35000,
    "margin_rate": 0.31
  }'
```

Update a price table item:

```bash
curl -X PATCH http://localhost:8000/api/price-table-items/1 \
  -H "Content-Type: application/json" \
  -d '{
    "final_price": 36000,
    "margin_rate": 0.33
  }'
```

Delete a price table item:

```bash
curl -X DELETE http://localhost:8000/api/price-table-items/1
```

### Candidate Price Generation API

`POST /api/candidate-prices/generate` creates a generated candidate price
table from deterministic backend logic. The LLM does not generate numeric
prices.

Candidate generation uses this order:

1. resolve the selected product and each requested quantity,
2. find the matching cost profile,
3. calculate the cost floor,
4. summarize manually entered competitor reference prices,
5. apply the selected strategy or active strategy template,
6. round the result to the configured rounding unit,
7. save a `generated` candidate table.

Cost floor formula:

```text
base_cost = fixed_cost + (unit_cost * quantity)
minimum_price_from_margin = base_cost / (1 - minimum_margin_rate)
cost_floor = max(minimum_price_from_margin, minimum_price)
```

Strategies:

- `margin_protect`: with market data, `max(cost_floor, market_average * 1.03)`; without market data, `cost_floor * 1.08`
- `balanced_market`: with market data, `max(cost_floor, market_average)`; without market data, `cost_floor * 1.05`
- `premium_local`: with market data, `max(cost_floor, market_average * 1.08)`; without market data, `cost_floor * 1.12`

Generated candidates are not copied into `price_tables`, are not activated for
quotes, and require explicit human approval before they can become an active
internal price table. Competitor prices remain manually entered reference data
only. No web scraping is used.

PR-06 uses a simple unweighted market average. Competitor-type weighting is a
later refinement; large online references are flagged so they are not blindly
treated as target prices.

PR-21 adds optional `strategy_template_id`. When a template is provided, the
template takes priority over `strategy_name`; the backend uses the template's
`strategy_name` and `rounding_unit`. Without a template, the existing
`strategy_name` request works unchanged.

Request:

```bash
curl -X POST http://localhost:8000/api/candidate-prices/generate \
  -H "Content-Type: application/json" \
  -d '{
    "product_slug": "a3-flyer",
    "option_summary": "A3 / snow paper / single-sided / full color",
    "quantities": [100, 500],
    "strategy_name": "balanced_market"
  }'
```

Template request:

```bash
curl -X POST http://localhost:8000/api/candidate-prices/generate \
  -H "Content-Type: application/json" \
  -d '{
    "product_slug": "a3-flyer",
    "option_summary": "A3 / snow paper / single-sided / full color",
    "quantities": [100, 500],
    "strategy_template_id": 1
  }'
```

Example response:

```json
{
  "pricing_session_id": 1,
  "candidate_table_id": 1,
  "candidate_table_name": "Balanced Market candidate - A3 Flyer",
  "product_id": 1,
  "product_name": "A3 Flyer",
  "option_summary": "A3 / snow paper / single-sided / full color",
  "strategy_name": "balanced_market",
  "status": "generated",
  "rounding_rule": "nearest_100_won",
  "strategy_template": null,
  "items": [
    {
      "quantity": 100,
      "option_summary": "A3 / snow paper / single-sided / full color",
      "candidate_price": 32000.0,
      "unit_price": 320.0,
      "cost_floor_price": 32000.0,
      "estimated_margin_rate": 0.25,
      "market_lowest_price": 32000.0,
      "market_average_price": 32000.0,
      "market_median_price": 32000.0,
      "market_highest_price": 32000.0,
      "market_summary": {
        "lowest_price": 32000.0,
        "highest_price": 32000.0,
        "average_price": 32000.0,
        "median_price": 32000.0,
        "count": 1
      },
      "decision_reason_codes": [
        "COST_FLOOR_PROTECTED",
        "STRATEGY_BALANCED_MARKET",
        "MARKET_REFERENCE_USED",
        "LARGE_ONLINE_NOT_BLINDLY_FOLLOWED"
      ],
      "warnings": []
    }
  ],
  "summary": {
    "lowest_candidate_price": 32000.0,
    "highest_candidate_price": 32000.0,
    "average_candidate_price": 32000.0,
    "total_market_references": 1,
    "item_count": 1
  },
  "warnings": [
    "Generated candidate tables are not active internal price tables and require later admin review.",
    "Competitor prices are manually entered reference data only."
  ]
}
```

### Candidate Validation API

`POST /api/candidate-prices/{candidate_table_id}/validate` runs deterministic
risk checks against a generated candidate table and stores the validation
result. Validation does not approve, activate, or copy candidate prices into
internal `price_tables`. Human approval is a separate explicit admin action.

Validation rules are calculated in backend code only. The LLM does not validate
numeric prices.

Request:

```bash
curl -X POST http://localhost:8000/api/candidate-prices/1/validate
```

Example response:

```json
{
  "validation_result_id": 1,
  "candidate_table_id": 1,
  "candidate_table_name": "Balanced Market candidate - A3 Flyer",
  "overall_status": "pass_with_warnings",
  "risk_level": "medium",
  "summary": {
    "item_count": 2,
    "pass_count": 4,
    "info_count": 0,
    "warning_count": 2,
    "error_count": 0
  },
  "results": [
    {
      "quantity": 100,
      "candidate_price": 32000.0,
      "status": "warning",
      "risk_level": "medium",
      "checks": [
        {
          "code": "ABOVE_COST_FLOOR",
          "level": "pass",
          "message": "Candidate price is above the deterministic cost floor."
        },
        {
          "code": "MARGIN_PROTECTED",
          "level": "pass",
          "message": "Estimated margin is at or above the matching minimum margin."
        },
        {
          "code": "TOO_CLOSE_TO_LOWEST_MARKET_PRICE",
          "level": "warning",
          "message": "Candidate is very close to the lowest competitor price; do not blindly follow the lowest reference."
        }
      ]
    }
  ],
  "thresholds": {
    "market_below_average_warning_rate": 0.15,
    "market_above_average_warning_rate": 0.2,
    "lowest_market_proximity_warning_rate": 0.03,
    "unit_price_increase_warning_rate": 0.05
  },
  "warnings": [
    "Validation is deterministic and does not approve or activate candidate tables.",
    "Human approval is a separate explicit admin action."
  ]
}
```

Validation status values:

- `pass`: no warnings or errors
- `pass_with_warnings`: no errors, but at least one warning
- `fail`: one or more errors

Risk levels:

- `low`: pass-only checks
- `medium`: warnings exist
- `high`: errors exist

Check levels:

- `pass`
- `info`
- `warning`
- `error`

Validation codes:

- `ABOVE_COST_FLOOR`: candidate is above the deterministic cost floor
- `BELOW_COST_FLOOR`: candidate is below the cost floor
- `MARGIN_PROTECTED`: estimated margin is at or above the cost profile minimum
- `MARGIN_BELOW_MINIMUM`: estimated margin is below the cost profile minimum
- `MISSING_COST_PROFILE`: matching cost profile is missing
- `MISSING_MARKET_DATA`: matching competitor reference data is missing
- `MARKET_REFERENCE_AVAILABLE`: matching competitor reference data is available
- `MARKET_LOW_BELOW_COST_FLOOR`: lowest competitor reference is below cost floor
- `TOO_CLOSE_TO_LOWEST_MARKET_PRICE`: candidate is within 3% of the lowest market reference
- `BELOW_MARKET_AVERAGE`: candidate is more than 15% below market average
- `ABOVE_MARKET_AVERAGE`: candidate is more than 20% above market average
- `UNIT_PRICE_INCREASES_WITH_QUANTITY`: unit price rises by more than 5% at a higher quantity
- `TOTAL_PRICE_DECREASES_WITH_QUANTITY`: total price drops as quantity increases

### Pricing Simulation API

`POST /api/simulations/pricing` compares a generated candidate price table
against a baseline internal price table, usually the current active table. This
is decision support only. It does not approve, reject, activate, archive, or
modify any price table.

If `baseline_price_table_id` is omitted, the backend uses the current active
price table for the selected product when one exists. If `volume_assumptions`
is omitted, each candidate quantity uses `expected_order_count = 1`.

Request:

```bash
curl -X POST http://localhost:8000/api/simulations/pricing \
  -H "Content-Type: application/json" \
  -d '{
    "product_slug": "a3-flyer",
    "candidate_table_id": 1,
    "baseline_price_table_id": 1,
    "option_summary": "A3 / snow paper / single-sided / full color",
    "volume_assumptions": [
      {
        "quantity": 100,
        "expected_order_count": 10
      },
      {
        "quantity": 500,
        "expected_order_count": 8
      }
    ]
  }'
```

Example response:

```json
{
  "product_id": 1,
  "product_name": "A3 Flyer",
  "candidate_table_id": 1,
  "baseline_price_table_id": 1,
  "summary": {
    "item_count": 2,
    "baseline_total_revenue": 1134000.0,
    "candidate_total_revenue": 1072000.0,
    "revenue_delta": -62000.0,
    "baseline_total_gross_profit": 422000.0,
    "candidate_total_gross_profit": 360000.0,
    "gross_profit_delta": -62000.0,
    "average_margin_delta": -0.045,
    "warning_count": 2
  },
  "items": [
    {
      "quantity": 100,
      "expected_order_count": 10,
      "baseline_price": 35000.0,
      "candidate_price": 32000.0,
      "price_delta": -3000.0,
      "price_delta_rate": -0.0857,
      "base_cost": 24000.0,
      "baseline_margin_rate": 0.3143,
      "candidate_margin_rate": 0.25,
      "margin_delta": -0.0643,
      "baseline_revenue": 350000.0,
      "candidate_revenue": 320000.0,
      "revenue_delta": -30000.0,
      "baseline_gross_profit": 110000.0,
      "candidate_gross_profit": 80000.0,
      "gross_profit_delta": -30000.0,
      "market_average_price": 32000.0,
      "candidate_vs_market_average_rate": 0.0,
      "warnings": [
        "CANDIDATE_MARGIN_LOWER_THAN_BASELINE"
      ]
    }
  ],
  "warnings": [
    "CANDIDATE_MARGIN_LOWER_THAN_BASELINE"
  ]
}
```

Simulation calculations are deterministic backend math:

```text
base_cost = fixed_cost + (unit_cost * quantity)
margin_rate = (price - base_cost) / price
revenue = price * expected_order_count
gross_profit = (price - base_cost) * expected_order_count
```

Market reference values are calculated only from manually entered competitor
prices. Missing market data stays missing; the backend does not invent market
averages.

Simulation warning codes:

- `MISSING_BASELINE_PRICE`: no matching baseline price row was found
- `MISSING_COST_PROFILE`: no matching cost profile was found
- `MISSING_MARKET_DATA`: no matching competitor reference data was found
- `CANDIDATE_MARGIN_LOWER_THAN_BASELINE`: candidate margin is below baseline margin
- `CANDIDATE_PRICE_BELOW_COST`: candidate price is below deterministic base cost
- `CANDIDATE_PRICE_MUCH_ABOVE_MARKET_AVERAGE`: candidate is more than 20% above market average
- `CANDIDATE_PRICE_MUCH_BELOW_MARKET_AVERAGE`: candidate is more than 15% below market average

The frontend simulation dashboard lets an admin select a product, candidate
table, baseline table, option summary, and expected order counts. It shows
summary cards, a revenue comparison chart, per-quantity rows, market position,
and warning badges. AI does not generate simulation numbers or approval
decisions. Human approval is still required before any candidate table affects
customer quotes.

### Agent Logs API

`GET /api/agent-logs` returns backend timeline steps recorded during candidate
generation, validation, and explanation. These logs describe deterministic
backend steps; they are not fake automation and they do not approve prices.

Optional filters:

- `pricing_session_id`
- `candidate_table_id`
- `validation_result_id`

Example:

```bash
curl "http://localhost:8000/api/agent-logs?candidate_table_id=1"
```

Example response:

```json
[
  {
    "id": 1,
    "pricing_session_id": 1,
    "candidate_table_id": 1,
    "validation_result_id": null,
    "step_type": "candidate_generated",
    "title": "Candidate table generated",
    "message": "Generated 2 candidate price rows. The table is not active.",
    "status": "completed",
    "metadata": {
      "item_count": 2,
      "status": "generated"
    },
    "created_at": "2026-06-24T00:00:00+00:00"
  }
]
```

### Workflow Jobs API

PR-20 adds a simple local persisted workflow/job layer for admin operations.
The MVP runs jobs synchronously inside the FastAPI request, but stores the job
and each step in the configured database so an admin can inspect what happened
after the run.
This is intentionally not Celery, Redis, a queue service, or an external worker.

Start the pricing analysis workflow:

```bash
curl -X POST http://localhost:8000/api/workflows/pricing-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "option_summary": "A3 / snow paper / single-sided / full color",
    "quantities": [100, 500],
    "strategy_name": "balanced_market",
    "run_validation": true,
    "run_ai_explanation": true
  }'
```

The workflow orchestrates existing deterministic services only:

1. load product and input data,
2. check cost profile and manual market reference availability,
3. run candidate price generation,
4. optionally run deterministic validation,
5. optionally generate an OpenAI or fallback explanation from existing facts,
6. verify Agent Timeline and audit log records,
7. persist the final job result.

Example response shape:

```json
{
  "job": {
    "id": 1,
    "job_type": "pricing_analysis",
    "status": "completed",
    "title": "Pricing analysis workflow",
    "input": {
      "product_id": 1,
      "option_summary": "A3 / snow paper / single-sided / full color",
      "quantities": [100, 500],
      "strategy_name": "balanced_market",
      "run_validation": true,
      "run_ai_explanation": true
    },
    "result": {
      "candidate_table_id": 7,
      "pricing_session_id": 7,
      "validation_result_id": 4,
      "validation_status": "pass_with_warnings",
      "ai_explanation_source": "fallback",
      "agent_log_count": 10,
      "audit_log_count": 4,
      "activated_price_table_id": null,
      "approval_required": true
    },
    "error_message": null
  },
  "steps": [
    {
      "step_type": "generate_candidate_table",
      "status": "completed",
      "title": "Generate candidate table",
      "message": "Candidate table generated. It is not active."
    }
  ]
}
```

Job status values:

- `queued`
- `running`
- `completed`
- `failed`
- `cancelled`

Inspect jobs and steps:

```bash
curl "http://localhost:8000/api/jobs?job_type=pricing_analysis"
curl http://localhost:8000/api/jobs/1
curl http://localhost:8000/api/jobs/1/steps
```

Workflow jobs do not approve candidate tables, do not activate price tables,
do not change pricing formulas, and do not let AI generate numeric prices.
Human approval is still required through the approval API before any generated
candidate affects quote preview. PostgreSQL-ready production deployments should
replace this synchronous local job runner with a real background worker later.

### Operations KPI Dashboard

PR-22 adds a deterministic operations KPI dashboard for admin visibility. The
dashboard summarizes stored backend data only. AI does not generate KPI values,
approval decisions, or pricing numbers.

KPI endpoint:

```bash
curl http://localhost:8000/api/dashboard/kpis
```

Dashboard insight endpoint:

```bash
curl http://localhost:8000/api/dashboard/insights
```

PR-32 adds deterministic operational insights for attention items, approval
queue, validation risk, data readiness, quote request follow-up, workflow
health, recent audit activity, and safe system readiness. These insight values
come from stored database records and existing status fields only. AI does not
generate insight numbers, decide approval safety, or activate candidate price
tables. See [docs/DASHBOARD_INSIGHTS.md](docs/DASHBOARD_INSIGHTS.md).

Example response shape:

```json
{
  "generated_at": "2026-06-24T00:00:00+00:00",
  "recent_window_days": 7,
  "pricing": {
    "total_products": 4,
    "active_products": 4,
    "total_competitors": 3,
    "total_competitor_prices": 6,
    "total_cost_profiles": 4,
    "total_price_tables": 2,
    "active_price_tables": 1,
    "draft_price_tables": 1,
    "archived_price_tables": 0
  },
  "candidates": {
    "total_candidate_tables": 3,
    "generated_candidate_tables": 2,
    "approved_candidate_tables": 1,
    "rejected_candidate_tables": 0
  },
  "validation": {
    "pass_count": 1,
    "warning_count": 1,
    "fail_count": 0,
    "high_risk_count": 0
  },
  "quote_requests": {
    "submitted": 1,
    "reviewing": 0,
    "quoted": 1,
    "rejected": 0,
    "archived": 0
  },
  "approvals": {
    "total_approvals": 1,
    "recent_approvals_count": 1
  },
  "operations": {
    "total_audit_logs": 12,
    "recent_audit_logs_count": 12,
    "total_csv_imports": 2,
    "failed_csv_imports": 0,
    "total_workflow_jobs": 1,
    "completed_workflow_jobs": 1,
    "failed_workflow_jobs": 0
  }
}
```

The frontend includes an admin operations dashboard with summary cards and
Recharts status charts for price tables, validation results, quote requests,
and workflow jobs.

KPI calculation rules:

- product, competitor, cost, price table, candidate, validation, approval,
  quote request, audit, and workflow counts are read directly from the
  configured database
- recent approval and audit counts use a 7-day window
- CSV import counts are inferred from audit log `csv_import_completed` and
  `csv_import_failed` events
- unavailable metrics should be omitted or returned as `null` in later
  implementations rather than invented

Limitations:

- this is an aggregate operations dashboard, not external analytics
- no forecasting, revenue prediction, or new pricing formula is added
- KPI views do not approve candidates or activate price tables
- human approval is still required before candidate prices affect quotes

### Audit Logs API

PR-19 adds an audit log for real backend actions that affect pricing operations
and admin accountability. Audit logs are traceability records only: they do not
change prices, approve candidates, activate price tables, or generate numeric
values. AI does not create, edit, or manipulate audit log events.

Tracked examples include:

- `admin_login` and `admin_login_failed`
- `product_created`, `product_updated`, `product_deleted`
- `product_option_created`, `product_option_updated`, `product_option_deleted`
- `competitor_price_created`, `competitor_price_updated`, `competitor_price_deleted`
- `cost_profile_created`, `cost_profile_updated`, `cost_profile_deleted`
- `price_table_created`, `price_table_updated`, `price_table_archived`
- `price_table_item_created`, `price_table_item_updated`, `price_table_item_deleted`
- `candidate_table_generated`, `candidate_table_validated`
- `ai_explanation_generated`
- `candidate_table_approved`, `candidate_table_rejected`
- `price_table_activated`, `previous_active_price_table_archived`
- `quote_request_submitted`, `quote_request_updated`, `quote_request_quoted`
- `csv_import_started`, `csv_import_completed`, `csv_import_failed`, `csv_export_completed`

List recent audit events:

```bash
curl http://localhost:8000/api/audit-logs
```

Use simple filters:

```bash
curl "http://localhost:8000/api/audit-logs?action=candidate_table_approved"
curl "http://localhost:8000/api/audit-logs?entity_type=price_table&limit=20"
curl "http://localhost:8000/api/audit-logs?actor_name=Owner"
curl "http://localhost:8000/api/audit-logs?created_from=2026-06-24T00:00:00%2B00:00"
```

Example response:

```json
{
  "items": [
    {
      "id": 1,
      "actor_id": 1,
      "actor_name": "Local Demo Owner",
      "actor_role": "owner",
      "action": "candidate_table_approved",
      "entity_type": "candidate_table",
      "entity_id": 5,
      "entity_label": "Candidate table #5",
      "before": null,
      "after": {
        "candidate_table_id": 5,
        "status": "completed"
      },
      "metadata": {},
      "ip_address": "127.0.0.1",
      "user_agent": "curl/8.0",
      "created_at": "2026-06-24T00:00:00+00:00"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

The frontend includes a Korean-first audit log viewer with action, entity,
actor, timestamp, simple filters, and expandable JSON details. This is not an
enterprise compliance or immutable ledger system; it is a lightweight MVP
operation history. External logging services, background jobs, retention rules,
and tamper-evident storage are intentionally deferred.

### AI Explanation API

`POST /api/candidate-prices/{candidate_table_id}/explain` creates a Korean
explanation from existing deterministic facts: candidate rows, cost floors,
market references, reason codes, and latest validation results.

The AI must not invent prices, margins, market data, validation results, or
approval decisions. If OpenAI is not configured, the endpoint returns a
fallback explanation and a warning.

Request:

```bash
curl -X POST http://localhost:8000/api/candidate-prices/1/explain
```

OpenAI response shape:

```json
{
  "candidate_table_id": 1,
  "explanation": "이 후보 가격표는 balanced_market 전략으로 생성되었습니다...",
  "source": "openai",
  "warnings": [],
  "created_at": "2026-06-24T00:00:00+00:00"
}
```

Fallback response shape:

```json
{
  "candidate_table_id": 1,
  "explanation": "AI API 키가 설정되지 않아 기본 설명을 표시합니다...",
  "source": "fallback",
  "warnings": [
    "OPENAI_API_KEY is not configured"
  ],
  "created_at": "2026-06-24T00:00:00+00:00"
}
```

AI explanation does not approve or activate generated candidate tables. Human
approval is handled by the explicit approval endpoint below.

### Candidate Approval API

`POST /api/candidate-prices/{candidate_table_id}/approve` is the explicit
human approval step. Approval does not ask AI to make a decision and does not
change candidate prices. The backend copies the stored candidate rows
unchanged into a new `active` internal price table.

Approval rules:

1. the candidate table must exist,
2. the candidate table must not already be approved or rejected,
3. the candidate table must have candidate items,
4. the latest validation result must exist,
5. validation status must be `pass` or `pass_with_warnings`,
6. validation status `fail` blocks approval,
7. approval archives previous active price tables for the same product,
8. approval creates one new active price table for the product.

Approve a candidate:

```bash
curl -X POST http://localhost:8000/api/candidate-prices/1/approve \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_name": "Admin",
    "reviewer_note": "Margin and warning review completed."
  }'
```

Example response:

```json
{
  "approval_id": 1,
  "candidate_table_id": 1,
  "product_id": 1,
  "action": "approve",
  "status": "completed",
  "candidate_status": "approved",
  "created_price_table_id": 3,
  "message": "Candidate table approved and converted into a new active price table."
}
```

Reject a candidate:

```bash
curl -X POST http://localhost:8000/api/candidate-prices/1/reject \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_name": "Admin",
    "reviewer_note": "Rejected because the market references are too thin."
  }'
```

Rejection marks the candidate table as `rejected` and does not change active
internal price tables.

Approval history:

```bash
curl "http://localhost:8000/api/approvals?candidate_table_id=1"
curl "http://localhost:8000/api/approvals?product_id=1&action=approve"
```

Candidate status values:

- `generated`: created by deterministic candidate generation
- `reviewed`: reserved for review workflows
- `approved`: explicitly approved by a human reviewer
- `rejected`: explicitly rejected by a human reviewer
- `discarded`: reserved for removed candidates

AI explanation is optional context only. AI does not approve candidates, does
not modify numeric prices, and does not activate price tables. Human approval
is required before a generated candidate affects quote preview.

### Price Table Comparison And History

PR-18 adds deterministic comparison and version history for internal price
tables. This is a review feature only. It does not activate, archive, approve,
or modify price tables.

Compare a price table against an explicit baseline:

```bash
curl "http://localhost:8000/api/price-tables/5/compare?baseline_price_table_id=3"
```

If `baseline_price_table_id` is omitted, the backend selects the previous
`active` or `archived` price table for the same product when one exists:

```bash
curl http://localhost:8000/api/price-tables/5/compare
```

History endpoints:

```bash
curl http://localhost:8000/api/price-tables/history
curl "http://localhost:8000/api/price-tables/history?product_id=1"
curl http://localhost:8000/api/products/1/price-table-history
```

Comparison calculations are deterministic backend math:

```text
price_delta = comparison_price - baseline_price
price_delta_rate = price_delta / baseline_price
base_cost = fixed_cost + unit_cost * quantity
margin_rate = (price - base_cost) / price
margin_delta = comparison_margin_rate - baseline_margin_rate
```

Missing values are not invented. If a baseline item is missing, the row is
marked `new_item`. If a comparison item is missing, the row is marked
`removed_item`. Other change types are `increased`, `decreased`, and
`unchanged`.

Warning codes:

- `PRICE_INCREASE_OVER_20_PERCENT`: comparison price is more than 20% above baseline
- `PRICE_DECREASE_OVER_15_PERCENT`: comparison price is more than 15% below baseline
- `MISSING_BASELINE_ITEM`: no matching baseline row exists
- `MISSING_COMPARISON_ITEM`: no matching comparison row exists
- `MISSING_COST_PROFILE`: margin comparison cannot be calculated
- `MARGIN_DECREASED`: deterministic margin rate decreased
- `PRICE_BELOW_COST`: comparison price is below deterministic base cost

Example response shape:

```json
{
  "product_id": 1,
  "product_name": "A3 Flyer",
  "baseline_price_table_id": 3,
  "comparison_price_table_id": 5,
  "summary": {
    "item_count": 2,
    "changed_count": 1,
    "unchanged_count": 1,
    "average_price_delta_rate": 0.0667,
    "total_price_delta": 8000.0,
    "warning_count": 0
  },
  "items": [
    {
      "quantity": 100,
      "option_summary": "A3 / snow paper / single-sided / full color",
      "baseline_price": 32000.0,
      "comparison_price": 34000.0,
      "price_delta": 2000.0,
      "price_delta_rate": 0.0625,
      "baseline_margin_rate": 0.25,
      "comparison_margin_rate": 0.2941,
      "margin_delta": 0.0441,
      "change_type": "increased",
      "warnings": []
    }
  ],
  "warnings": []
}
```

The history response lists price table versions with approval metadata when a
price table was created from an approved candidate. It includes the source
`candidate_table_id` when available. This is not a full audit log system; full
audit logging is intentionally deferred to a later PR.

The frontend includes a Korean-first price table comparison section with product
selector, baseline selector, comparison selector, summary cards, row-level
comparison table, warning badges, and a price table history list. AI does not
generate comparison numbers or approval decisions.

### Pricing Scenario Comparison

PR-33 adds Pricing Scenario Comparison v2 for comparing stored pricing options
before owner approval. It supports:

- active or archived `price_table` scenarios
- generated, approved, or rejected `candidate_table` scenarios

Strategy templates are generation settings, not stored price rows. To compare
two template outcomes, generate candidate tables from those templates and
compare the resulting candidate table IDs.

Compare an active price table with a candidate table:

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

Scenario comparison is deterministic and read-only. It calculates:

- matching and missing item counts
- average, minimum, and maximum price differences
- average price difference rate
- average margin difference when stored margin values exist
- price increase, decrease, and unchanged counts
- validation status comparison from saved validation results
- approval readiness from stored status and validation state

Items are matched by product, quantity, and normalized option summary. The
backend does not use fuzzy matching and does not invent missing rows. Missing
validation is reported clearly; this endpoint does not run validation or add
new validation rules.

The frontend comparison section includes scenario selectors, summary cards,
item-level differences, validation status, approval readiness, warnings, and
role-aware links. Owner approval is still a separate explicit action. Scenario
comparison does not approve, reject, archive, activate, or modify any price
table. AI does not generate comparison numbers, margins, validation results, or
approval decisions.

See [docs/SCENARIO_COMPARISON.md](docs/SCENARIO_COMPARISON.md) for details.

### Exportable Reports

PR-34 adds print-friendly HTML reports for admin review, demos, portfolio
presentation, and internal decision records. Reports are read-only snapshots.
They do not approve candidates, activate price tables, run validation, change
prices, or generate new candidate tables.

Supported report endpoints:

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

The report response format is `text/html`. Open the HTML in a browser and use
print/save as PDF when a PDF file is needed. The frontend includes a
Korean-first "보고서 내보내기" section that previews the HTML and opens a
temporary local tab for printing.

Report data rules:

- all prices, margins, validation results, comparison numbers, approval status,
  audit rows, and KPI values come from stored data or existing deterministic
  backend services
- AI does not generate report numbers, risk scores, validation results,
  approval decisions, or final recommendations
- missing data is shown as missing and is not guessed
- report generation works without `OPENAI_API_KEY`
- owner, manager, and viewer roles can generate read-only reports, while
  approval still requires explicit human owner action
- successful report generation writes a compact `report_generated` audit event
  without storing the full report body

Reports intentionally do not expose raw `DATABASE_URL`, database passwords,
OpenAI API keys, bearer tokens, private environment values, stack traces, or
other secrets.

See [docs/REPORTS.md](docs/REPORTS.md) for report types, role behavior,
print-to-PDF workflow, audit logging, and limitations.

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

`npm install` and `npm run dev` also work if npm is the package manager used in
your local environment, but this repository includes a `pnpm-lock.yaml`, so
`pnpm` is preferred for repeatable frontend installs.

Open:

```text
http://localhost:5173
```

The frontend reads the backend API URL from:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For backward compatibility, `VITE_API_URL` is also accepted locally, but new
deployments should use `VITE_API_BASE_URL`.

### Playwright QA

The Playwright suite covers the local product workflow and regression smoke
checks. The tests do not depend on external websites and do not require
`OPENAI_API_KEY`.

Install frontend dependencies first:

```bash
cd frontend
pnpm install
npx playwright install chromium
```

Run the E2E smoke tests:

```bash
cd frontend
pnpm run test:e2e
```

Interactive mode:

```bash
cd frontend
pnpm run test:e2e:ui
```

The Playwright config starts:

- FastAPI at `http://127.0.0.1:8000`
- Vite at `http://127.0.0.1:5173`
- a local SQLite E2E database at `quoteops-e2e.db`

If you already have local servers running, Playwright can reuse them.
On environments where `py -3` is not available, set
`PLAYWRIGHT_BACKEND_COMMAND`, for example:

```bash
PLAYWRIGHT_BACKEND_COMMAND="python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000" pnpm run test:e2e
```

### Product Workflow Smoke Scenario

The local product workflow smoke scenario is:

1. Admin opens the QuoteOps AI workspace.
2. Product, active price table, market reference, cost/margin, and quote preview cards render.
3. Admin reviews manually entered competitor reference prices.
4. Backend quote preview returns a deterministic quote from the active price table.
5. Admin generates a candidate price table from deterministic backend logic.
6. Admin validates the candidate table.
7. AI explanation summarizes deterministic facts only; it does not generate prices.
8. Admin approves or rejects the candidate table.
9. Approval archives the previous active table for that product and activates the approved table.
10. Quote preview uses the newly active approved price table.

Important product safety rules:

- AI는 가격 숫자를 생성하지 않습니다.
- 가격은 백엔드 계산식으로 산출됩니다.
- 경쟁사 가격은 참고 데이터입니다.
- 최저가를 무조건 따라가지 않습니다.
- 후보 가격표는 관리자 승인 전까지 적용되지 않습니다.
- 승인된 가격표만 실제 견적에 사용됩니다.

### Backend Smoke QA

```bash
python -m compileall backend
```

On Windows, if `python` is not mapped to a real interpreter, use:

```bash
py -3 -m compileall backend
```

Release-candidate QA commands:

```bash
py -3 -m compileall backend
py -3 scripts/db_smoke_check.py
cd frontend
pnpm run build
pnpm run test:e2e
```

Use [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) before tagging an
MVP release candidate.

### Deployment And Operations

PR-27 prepares a Render Blueprint deployment path without changing pricing,
validation, approval, role enforcement, audit logging, persistence, health, or
AI explanation behavior.

#### Backend Service

Recommended first deployment target:

- Platform: Render
- Service type: Web Service
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health endpoint: `/api/health/ready`

Required or supported backend environment variables:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql://user:password@host:5432/dbname
ALLOWED_ORIGINS=https://your-frontend-domain.onrender.com
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
LLM_ENABLED=false
SEED_DEMO_ADMIN=false
ENABLE_DEMO_TOOLS=false
```

`OPENAI_API_KEY` is optional. The backend starts without it, and AI explanation
falls back to a deterministic local explanation.

For local development only, omit `DATABASE_URL` or set
`DATABASE_URL=sqlite:///./quoteops.db`. For production, use a managed
PostgreSQL database such as Render PostgreSQL, Supabase PostgreSQL, Neon
PostgreSQL, or another managed provider. Do not rely on an ephemeral web-service
filesystem for production SQLite data.

#### Frontend Static Site

Recommended first deployment target:

- Platform: Render
- Service type: Static Site
- Runtime: Static
- Build command: `cd frontend && corepack enable && pnpm install --frozen-lockfile && pnpm run build`
- Publish directory: `frontend/dist`

Required frontend environment variable:

```dotenv
VITE_API_BASE_URL=https://your-backend-domain.onrender.com
```

Do not place backend secrets or OpenAI keys in `VITE_*` variables.

#### CORS

The backend reads comma-separated origins from `ALLOWED_ORIGINS`.

Local default:

```text
http://localhost:5173,http://127.0.0.1:5173
```

For production, set `ALLOWED_ORIGINS` to the deployed frontend URL. Do not use
wildcard CORS for production.

#### Render Blueprint

A root-level `render.yaml` is included as a simple starting point:

- `quoteops-ai-backend`: FastAPI web service
- `quoteops-ai-frontend`: Vite static site
- `quoteops-ai-postgres`: managed Render PostgreSQL database

Render environment values marked `sync: false` must be set in the Render
dashboard. In particular, set `VITE_API_BASE_URL` to the deployed backend URL
and `ALLOWED_ORIGINS` to the deployed frontend URL. The Blueprint wires
`DATABASE_URL` from the Render PostgreSQL database through `fromDatabase`.
Do not commit real database credentials, OpenAI keys, admin passwords, or
private Render URLs.

#### Database Storage

SQLite is acceptable for local MVP development and early operational
prototypes. PostgreSQL is recommended for production-like deployments.

Important notes:

- Local SQLite is the default when `DATABASE_URL` is missing or set to `sqlite:///./quoteops.db`.
- SQLite data persistence depends on the hosting filesystem behavior.
- Redeploys or instance replacement may reset local SQLite data if persistent storage is not configured.
- Render web service filesystems should be treated as ephemeral unless a persistent disk is configured.
- Production deployments should use a managed PostgreSQL database.
- Seeded sample data is clearly sample data, not real market pricing.

PR-24 adds PostgreSQL connectivity through the existing database access layer.
The app creates missing tables for both SQLite and PostgreSQL at startup and
keeps deterministic pricing, validation, approval, role enforcement, audit
logging, and AI explanation behavior unchanged.

Future production migration notes:

- use managed PostgreSQL before real customer operations,
- never commit database credentials,
- add a formal migration tool such as Alembic before operating long-lived production data,
- configure SSL parameters when required by the PostgreSQL provider,
- keep deterministic business logic independent from the database backend.

Troubleshooting:

- `Unsupported DATABASE_URL`: use `sqlite:///...`, `postgresql://...`, or `postgresql+psycopg://...`.
- `PostgreSQL DATABASE_URL requires the psycopg package`: run `pip install -r requirements.txt`.
- `connection refused` or DNS errors: verify host, port, database name, network allowlist, and provider status.
- authentication failures: verify username/password and rotate credentials if they were exposed.
- SSL errors: add the provider-required SSL settings to the connection string, for example `?sslmode=require` when supported.
- frontend cannot reach backend: verify `VITE_API_BASE_URL`, backend health, and browser network errors.
- CORS blocked: set `ALLOWED_ORIGINS` to the exact Render frontend origin and redeploy the backend. Do not use wildcard CORS in production.
- frontend build succeeds but API calls fail: remember Vite embeds `VITE_API_BASE_URL` at build time, so update the variable and redeploy the static site.
- health check fails: inspect `/api/health/db` and `/api/system/status` for safe diagnostic fields.
- database looks empty after deploy: confirm production is using Render PostgreSQL, not SQLite on an ephemeral web-service filesystem.

#### Product Safety Notes

- AI does not generate numeric prices.
- AI does not approve price tables.
- Competitor prices are manually entered reference data.
- Human approval is required before candidate prices become active.
- No web scraping is used.

#### Deployment Smoke Check

After deployment, verify:

1. Backend `/api/health` returns valid JSON.
2. Backend `/api/health/ready` returns `ready`.
3. Frontend loads.
4. Frontend can call the backend products API.
5. Admin login works with a safe production admin setup.
6. Quote preview works.
7. Market reference works.
8. Candidate generation works.
9. Validation works.
10. AI explanation fallback works without `OPENAI_API_KEY`.
11. Owner approval workflow works.
12. Quote preview uses the newly approved active price table.
13. Agent Timeline, audit logs, and dashboard KPIs appear.
14. No secrets are visible in browser source, health responses, logs, or committed files.

### Known Limitations

- The MVP uses SQLite by default for local development and supports PostgreSQL through `DATABASE_URL`.
- Production should use managed PostgreSQL before real customer operations.
- There is no customer account system, payment, web scraping, or Railway config.
- AI explanation is optional and falls back to a deterministic local explanation when `OPENAI_API_KEY` is missing.
- Playwright covers smoke/workflow confidence, not exhaustive business-rule testing.

## Development Rules

Read these first:

1. `AGENTS.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/MVP_SPEC.md`
4. `docs/DESIGN_SYSTEM.md`
5. `docs/DEPLOYMENT.md`

Do not copy ModelMate's `main_parts` architecture.
Do not let the LLM generate numeric prices directly.
Do not implement everything at once.
