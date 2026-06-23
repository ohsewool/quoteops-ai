# AGENTS.md

## Project Name

QuoteOps AI

## Project Overview

QuoteOps AI is an AI-assisted pricing and quoting operations system for small print, sticker, and custom-product businesses.

The MVP helps small/local businesses generate and tune quantity-based price tables by considering:

- competitor prices
- competitor type
- own cost
- minimum margin
- local competitiveness
- service premium
- quantity-range strategy

QuoteOps AI must not be positioned as a generic shopping mall, ERP, or simple GPT chatbot.

Canonical English positioning:

> QuoteOps AI helps small print/custom-product businesses create safe and competitive quantity-based price tables by combining market reference prices, internal cost, minimum margin, and human-approved AI recommendations.

Canonical Korean positioning:

> QuoteOps AI는 소규모 인쇄·스티커·주문제작 업체가 경쟁사 가격, 자사 원가, 최소 마진, 지역 경쟁력, 서비스 강점을 함께 고려해 수량별 가격표를 생성하고 검증하는 AI 가격 운영 에이전트입니다.

## MVP Products

Keep the MVP small.

Use only:

1. A3 Flyer
2. Product / Brand Sticker

Do not add many product categories in the MVP.

Future expansion can include:

- business cards
- posters
- labels
- acrylic keyrings
- photocards
- mugs
- t-shirts
- eco bags
- shopping bags
- packaging boxes

These are not MVP scope.

## Core Problem

When creating a new print/custom-product website, an operator often checks competitor prices manually for many quantities such as 10, 20, 50, 100, 200, 500, 1000, 2000, 4000, and 8000 units.

This is repetitive, slow, and error-prone.

The project generalizes this pain point into a pricing operations system that:

1. accepts competitor price data,
2. analyzes market price ranges,
3. protects minimum margin,
4. generates quantity-based price table candidates,
5. detects pricing risks,
6. explains trade-offs,
7. asks for human approval,
8. saves approved price table versions.

## Core AI-Agent Principle

Do not build a fake AI agent.

A real QuoteOps AI workflow must include:

```text
admin goal / strategy
-> tool plan
-> deterministic tool calls
-> observations
-> pricing decisions
-> validation results
-> candidate price tables
-> AI explanation
-> human approval
-> versioned artifact
```

The LLM must not guess final numeric prices.

All numeric pricing calculations must be handled by deterministic backend modules.

The LLM may only be used for:

- explaining analysis results
- summarizing candidate price tables
- describing pricing risks
- writing decision logs
- guiding the admin workflow
- translating technical validation results into Korean user-facing explanations

## Deterministic Modules Required

Implement pricing logic in backend code, not directly in the LLM.

Required service modules:

- pricing engine
- market price analyzer
- competitor weighting module
- cost and margin calculator
- price table candidate generator
- price inversion detector
- unit price progression checker
- discount cliff detector
- margin risk checker
- before/after simulator
- version storage
- approval workflow
- agent decision logger

## Pricing Strategy Modes

The MVP should support strategy selection.

Recommended strategy modes:

1. Local Competition Strategy
   - Compare mainly with local/similar-size competitors.
   - Do not blindly follow large online competitors.

2. Margin Protection Strategy
   - Keep minimum margin as the top priority.
   - Warn when market prices are too low.

3. Small-Quantity Focus Strategy
   - Make small orders competitive.
   - Protect margin in large-quantity ranges.

4. Premium Service Strategy
   - Allow prices above market average when service advantages exist.
   - Examples: local pickup, urgent work, direct consultation, design correction.

5. Aggressive Entry Strategy
   - Temporarily lower selected quantity ranges for a new site launch.
   - Must still respect minimum margin.

## Competitor Types

Do not treat all competitors equally.

Supported competitor types:

- large_online
- local_shop
- similar_size
- premium_shop
- ultra_low_cost
- unknown

Large online competitors are useful as reference points but should not automatically become target prices.

Ultra-low-cost competitors may be treated as outliers or high-risk references.

## Human-in-the-Loop Rule

The AI must never apply a price table automatically.

Every generated candidate must require admin approval before becoming active.

Required approval flow:

```text
candidate generated
-> validation completed
-> AI explanation shown
-> admin approves/rejects
-> approved candidate saved as a new version
```

## MVP Must-Have Features

Build these first:

1. Customer quote generator
   - select product
   - select options
   - enter quantity
   - view calculated quote

2. Admin product and option setup
   - A3 Flyer
   - Product / Brand Sticker

3. Competitor price input
   - manual input or CSV upload
   - include competitor type

4. Own cost and minimum margin input

5. Pricing strategy selection

6. Candidate price table generation

7. Validation checks
   - price inversion
   - unit price progression
   - discount cliff
   - margin risk
   - market gap

8. AI explanation
   - Korean explanation of why a candidate is recommended
   - risk summary
   - trade-off summary

9. Approval and versioning
   - approve/reject candidate
   - save approved table version
   - show before/after comparison

10. Agent log
   - record tools called
   - record observations
   - record decisions
   - record approval result

## Should-Have Features

Add only after must-have features work:

- simple charts for market vs candidate price
- CSV export
- PDF/HTML report
- failed range highlighting
- sample/demo data
- simple admin dashboard

## Do Not Build Yet

Do not build these in the MVP:

- automatic web scraping
- real-time competitor monitoring
- payment integration
- full shopping mall checkout
- ERP/MIS integration
- multi-vendor marketplace
- inventory management
- customer accounts
- complex coupon system
- team workspace
- enterprise RBAC
- custom ML model training
- fine-tuning
- large product catalog
- mobile app
- TypeScript migration unless explicitly requested
- Railway-specific deployment setup

## Tech Stack

Use a clean new repository.

Frontend:

- React + Vite
- JavaScript, not TypeScript
- Tailwind CSS
- shadcn/ui-inspired custom components
- lucide-react
- Recharts
- Framer Motion
- Axios
- Pretendard or Inter font

Backend:

- FastAPI + Python
- SQLite for local MVP
- PostgreSQL-compatible structure for later migration
- OpenAI API only for explanations and summaries

Deployment:

- Render first
- Optional later split: Vercel frontend + Render backend + Supabase PostgreSQL

Do not copy ModelMate's `main_parts` architecture.

Use a cleaner structure:

```text
backend/
  main.py
  db.py
  models/
  schemas/
  routers/
  services/
  agents/
frontend/
  src/
docs/
```

## Backend Architecture Rule

Use clear separation:

```text
routers/      HTTP API routes
services/     deterministic business logic
agents/       agent orchestration and logs
models/       database models or SQL helpers
schemas/      request/response contracts
```

The pricing calculation and candidate generation must live in `services/`, not in route handlers.

## Frontend Design Direction

The frontend should feel like a premium AI SaaS workspace, not a basic student project.

Visual references:

- ChatGPT-style conversational analysis
- Apple-style spacing and typography
- Linear/Notion-style clean workspace

Design principles:

- Korean-first UI
- spacious layout
- soft rounded cards
- clean typography
- neutral colors
- minimal shadows
- clear primary actions
- progressive disclosure
- no clutter
- no colorful dashboard overload
- subtle animations only

Core screens should include:

1. Landing page
2. Customer quote calculator
3. Admin dashboard
4. Competitor price input
5. Cost and margin setup
6. Pricing strategy selection
7. Candidate price table comparison
8. Agent timeline / execution log
9. Approval and version history

Do not build a generic ecommerce UI.
Do not copy ModelMate's UI structure.
Do not overbuild animations.
Do not use fake data as real results.

## Security Rules

- Never expose API keys in frontend code.
- Never place secrets in `VITE_*` variables.
- Mask API keys, DB passwords, and tokens in docs.
- Do not store raw secret values in markdown files.
- Use `.env.example` with placeholders only.

## Development Rules for Codex

- Read this `AGENTS.md` before coding.
- Do one small phase at a time.
- Do not implement the entire roadmap at once.
- Before editing, summarize the intended change.
- After editing, run the smallest relevant checks.
- Do not claim completion without concrete evidence.
- Prefer a simple working MVP over complex unfinished architecture.

## Recommended First Build Phases

### Phase 0: Project Scaffold

Create frontend/backend folders, basic FastAPI app, basic React app, Tailwind setup, and docs.

### Phase 1: Data Model

Create database tables for products, product options, competitors, competitor prices, cost profiles, price tables, candidate tables, approvals, and agent logs.

### Phase 2: Quote Engine

Implement customer quote calculation from active price table.

### Phase 3: Market Analyzer

Analyze competitor price data by quantity and competitor type.

### Phase 4: Candidate Generator

Generate 2-3 price table candidates using deterministic strategies.

### Phase 5: Validation Engine

Detect price inversion, discount cliff, margin risk, and market gap.

### Phase 6: AI Explanation

Use LLM only to explain deterministic results.

### Phase 7: Approval and Versioning

Approve candidate and save it as active version.

### Phase 8: Demo Polish

Add charts, Korean copy, sample CSV, and report.
