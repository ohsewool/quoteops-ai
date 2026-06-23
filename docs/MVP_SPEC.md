# MVP Specification

## Product

QuoteOps AI

## MVP Goal

Build a working AI-assisted pricing and quoting system for two product categories:

1. A3 Flyer
2. Product / Brand Sticker

The MVP should prove the core loop:

```text
competitor prices + own cost + margin rule + strategy
-> candidate price tables
-> validation
-> AI explanation
-> admin approval
-> customer quote
```

## MVP Scope Summary

The MVP is not a full ecommerce platform.

It is a pricing operations and quote generation system.

The MVP should include:

- customer quote calculation
- admin price setup
- competitor price input
- cost and minimum margin setup
- pricing strategy selection
- candidate price table generation
- price risk validation
- AI explanation
- approval and versioning
- agent log

## User Roles

### Customer

Can:

- choose product
- choose options
- enter quantity
- see quote price

Cannot:

- edit price tables
- view competitor data
- approve candidates
- access agent logs

### Admin / Pricing Manager

Can:

- manage products and options
- enter competitor price data
- classify competitor type
- enter cost profile
- set minimum margin
- choose pricing strategy
- generate price table candidates
- compare candidates
- approve or reject candidate
- view agent logs and version history

### AI Pricing Agent

Can:

- analyze competitor price data
- call deterministic pricing tools
- identify risky quantity ranges
- generate candidate explanations
- recommend review points
- log decisions

Cannot:

- apply prices without approval
- invent unsupported market data
- ignore minimum margin
- replace deterministic numeric calculations

## MVP Products and Options

### Product 1: A3 Flyer

Recommended MVP options:

| Option | MVP Values |
|---|---|
| Size | A3 |
| Paper Type | Snow paper |
| Paper Weight | 100g, 120g |
| Print Side | Single-sided |
| Color | Full color |
| Finishing | None |

Do not add too many paper types or finishing options at first.

### Product 2: Product / Brand Sticker

Recommended MVP options:

| Option | MVP Values |
|---|---|
| Shape | Circle, Square |
| Material | Standard paper, Yupo |
| Coating | None, Matte |
| Color | Full color |

Keep sticker options simple.

## Quantity Ranges

Do not hardcode one universal quantity table.

Allow quantity ranges or quantity points to be configurable.

Recommended demo quantity points:

```text
10, 20, 50, 100, 200, 500, 1000, 2000, 4000, 8000
```

These are demo examples, not fixed business rules.

## Competitor Price Input

MVP should support manual or CSV input.

Recommended CSV format:

```csv
competitor_name,competitor_type,product_key,option_key,quantity,total_price,shipping_included,tax_included,note
LargePrintMall,large_online,a3_flyer,snow_100g,100,30000,true,true,
LocalShopA,local_shop,a3_flyer,snow_100g,100,36000,false,true,
SimilarShopB,similar_size,a3_flyer,snow_100g,100,34000,false,true,
```

Required fields:

- competitor_name
- competitor_type
- product_key
- option_key
- quantity
- total_price

Optional fields:

- shipping_included
- tax_included
- note

## Cost Profile Input

The admin should enter simple cost data.

Recommended MVP fields:

| Field | Example |
|---|---:|
| base_setup_cost | 3000 |
| unit_material_cost | 40 |
| unit_print_cost | 20 |
| packaging_cost_per_order | 1000 |
| labor_cost_per_order | 5000 |
| minimum_margin_rate | 0.25 |

The backend should calculate estimated cost and minimum safe price.

The LLM must not calculate these directly.

## Pricing Strategy Modes

MVP should include at least three.

1. Local Competition Strategy
2. Margin Protection Strategy
3. Small-Quantity Focus Strategy

Optional later:

- Premium Service Strategy
- Aggressive Entry Strategy
- Large-Quantity Inquiry Strategy

## Candidate Price Tables

The backend should generate 2-3 candidates.

Recommended candidates:

### Candidate A: Balanced

- near weighted market median
- respects minimum margin
- moderate discount progression

### Candidate B: Margin-Protected

- higher than market when needed
- strong minimum margin protection
- safer for small businesses

### Candidate C: Entry Competitive

- competitive in selected small/medium quantity ranges
- still blocks prices below minimum safe price

Each candidate should include:

- quantity
- suggested total price
- unit price
- estimated cost
- estimated margin rate
- market comparison
- validation flags

## Validation Checks

Required validations:

1. Margin Risk
2. Price Inversion
3. Discount Cliff
4. Market Gap
5. Large-Online Follow Risk

## AI Explanation

Use AI only after deterministic results are created.

Input to LLM:

- strategy selected
- candidate tables
- validation results
- market summary
- margin summary
- admin goal

Output from LLM:

- Korean summary
- candidate pros/cons
- risk explanation
- recommended candidate
- approval checklist

## Approval and Versioning

Required approval states:

```text
draft
generated
approved
rejected
active
archived
```

Every approval should store:

- approved_by
- approved_at
- candidate_id
- strategy
- summary
- validation status

## Agent Log

Each agent run should log:

- run_id
- admin_goal
- selected_product
- selected_strategy
- tools_called
- observations
- decisions
- validation_results
- llm_explanation
- approval_result

Example tool call sequence:

```text
1. load_competitor_prices
2. analyze_market_prices
3. calculate_minimum_safe_prices
4. generate_candidate_tables
5. validate_candidate_tables
6. summarize_candidates_with_llm
7. wait_for_admin_approval
8. save_approved_version
```

## Suggested Database Tables

MVP tables:

```text
users
products
product_options
competitors
competitor_prices
cost_profiles
price_tables
price_table_items
pricing_sessions
candidate_tables
candidate_table_items
validation_results
agent_logs
approvals
quote_requests
generated_quotes
```

## Suggested API Endpoints

### Customer

```text
GET  /api/products
POST /api/quotes/calculate
```

### Admin Product Setup

```text
GET  /api/admin/products
POST /api/admin/products
POST /api/admin/product-options
```

### Competitor Prices

```text
POST /api/admin/competitor-prices/upload
GET  /api/admin/competitor-prices
```

### Cost Profiles

```text
POST /api/admin/cost-profiles
GET  /api/admin/cost-profiles
```

### Pricing Agent

```text
POST /api/admin/pricing-sessions
POST /api/admin/pricing-sessions/{session_id}/generate-candidates
GET  /api/admin/pricing-sessions/{session_id}
POST /api/admin/candidates/{candidate_id}/approve
POST /api/admin/candidates/{candidate_id}/reject
GET  /api/admin/agent-logs/{session_id}
```

### Active Price Tables

```text
GET /api/admin/price-tables
GET /api/admin/price-tables/{price_table_id}
```

## Suggested Frontend Screens

### Customer

1. Product selection
2. Option selection
3. Quantity input
4. Quote result

### Admin

1. Admin dashboard
2. Product setup
3. Competitor price upload/input
4. Cost and margin setup
5. Strategy selection
6. Candidate comparison
7. Validation result
8. AI explanation
9. Approval/version history
10. Agent log

## Frontend Design Requirement

The MVP frontend must be more polished than the previous ModelMate UI.

Use:

- React + Vite + JavaScript
- Tailwind CSS
- shadcn/ui-inspired custom components
- lucide-react
- Framer Motion
- Recharts
- Axios
- Pretendard or Inter font

Design references:

- ChatGPT-style analysis flow
- Apple-style spacing and typography
- Linear/Notion-style workspace clarity

Avoid:

- generic ecommerce templates
- colorful admin dashboards
- crowded tables
- excessive animations
- ModelMate UI copy/paste

## MVP Demo Scenario

Use this demo story:

```text
A small local print shop wants to open a new pricing page for A3 flyers.

The owner has competitor prices from a large online print mall, a local shop, and a similar-size shop.

The owner uploads competitor prices, enters own cost, sets minimum margin to 25%, and selects Local Competition Strategy.

QuoteOps AI analyzes market prices and warns that blindly following the large online competitor would break margin in large quantities.

The system generates three candidate price tables:
- Balanced
- Margin-Protected
- Entry Competitive

The AI explains the trade-offs.

The owner approves the Margin-Protected candidate.

The customer quote page now uses the approved table.
```

## What Counts as Done

MVP is done when:

- customer can calculate a quote from an approved table,
- admin can upload/input competitor prices,
- admin can enter cost and margin,
- admin can generate candidate tables,
- backend validates candidate risks,
- AI explanation uses deterministic results,
- admin can approve a candidate,
- approved version is saved,
- agent log shows the workflow,
- demo can be completed without manual DB edits.

## What Not To Do

Do not:

- build a full ecommerce checkout,
- add payment,
- add hundreds of products,
- auto-scrape competitor websites,
- let LLM invent numeric prices,
- skip approval,
- fake tool logs,
- overclaim commercial readiness,
- turn this into another AutoML project.
