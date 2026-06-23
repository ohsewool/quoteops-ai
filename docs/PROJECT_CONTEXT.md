# Project Context

## Project Name

QuoteOps AI

## Background

The original idea came from a real manual pricing setup workflow.

When creating a new print/custom-product website, the operator had to manually check competitor prices across many quantities, such as:

- 10
- 20
- 50
- 100
- 200
- 500
- 1000
- 2000
- 4000
- 8000

For each quantity, the operator compared competitor prices, entered or adjusted prices in the new site, checked whether the results looked reasonable, and repeated the process.

This was time-consuming and error-prone.

The project turns that real pain point into an AI-assisted pricing operations system.

## Important Clarification About Previous Data

Any previous quantities, prices, or discount tables from earlier work are reference material only.

They should not be hardcoded as final business rules.

They are useful as:

- problem evidence
- sample data
- demo examples
- baseline concept examples
- explanation of the manual workflow

But this project must generate price tables based on the current user's own inputs:

- selected product
- selected options
- competitor prices
- competitor type
- own cost
- minimum margin
- pricing strategy
- quantity ranges

## Problem Definition

Small print, sticker, and custom-product businesses often need to create quantity-based price tables.

However, price table setup is difficult because they must consider:

1. competitor prices,
2. different competitor types,
3. large-company prices that may be impossible to match,
4. local competitiveness,
5. own cost structure,
6. minimum margin,
7. service premium,
8. small-quantity and large-quantity strategy differences,
9. price inversion risks,
10. unnatural discount jumps.

A simple competitor-price-copying tool is dangerous.

Small businesses should not blindly follow large online companies because large companies may have:

- better material purchasing power,
- larger batch production,
- more automation,
- lower unit cost,
- lower logistics cost,
- stronger scale advantage.

Therefore, QuoteOps AI should help small businesses create a price table that is competitive but still protects margin.

## Target Users

Primary users:

- small local print shops
- sticker/label production shops
- small custom-product makers
- local promotional-product shops
- small businesses opening a new custom-product website

Secondary users:

- students building a pricing/AI agent portfolio project
- small agencies creating quote systems for clients
- operators who need price-table setup support

## MVP Domain

The MVP focuses on:

1. A3 Flyer
2. Product / Brand Sticker

These are chosen because:

- they naturally use quantity-based pricing,
- they are easy to explain in a demo,
- they connect to real print-site pricing pain,
- they support small/local business strategy,
- they can later expand into goods, promotional products, and packaging.

## Why Not Start With Full Goods / Merchandise?

Goods and promotional products are promising but too broad for the MVP.

Examples:

- acrylic keyrings
- mugs
- t-shirts
- eco bags
- photocards
- pens
- packaging boxes

These products introduce many extra complexities:

- product sourcing
- supplier cost
- stock
- size/color variants
- printing position
- packaging
- defect risk
- delivery schedule
- minimum order quantity

Therefore, the MVP should prove the pricing-agent workflow first using flyer and sticker products.

After the MVP works, the same product-template structure can expand into goods and promotional products.

## Core Concept

QuoteOps AI is not a generic AI chatbot.

It is a pricing operations agent that combines deterministic tools and AI explanations.

The system should:

1. receive competitor price data,
2. classify competitor type,
3. analyze market ranges,
4. accept own cost and minimum margin,
5. select a pricing strategy,
6. generate price table candidates,
7. validate pricing risks,
8. explain the result,
9. ask for admin approval,
10. save an approved price version.

## Core Differentiation

Bad approach:

> Copy large-company competitor prices and make our price slightly cheaper.

Better approach:

> Use large-company prices as reference, but recommend a safe price table based on local competition, own cost, minimum margin, and service advantages.

QuoteOps AI should help answer questions like:

- Are we too expensive compared with similar local shops?
- Are we trying to match a large company price that our cost structure cannot support?
- Which quantity ranges should be competitive?
- Which quantity ranges should protect margin?
- Should large-volume orders be automatic quotes or separate inquiry?
- Is there a price inversion?
- Is there an unnatural discount cliff?
- Is this candidate safe enough to approve?

## Pricing Strategy Philosophy

Small businesses should not compete against large online platforms in every quantity range.

A realistic strategy may be:

- small quantities: competitive and convenient
- medium quantities: balanced
- large quantities: margin-protected or inquiry-based
- urgent/local service: premium can be justified
- custom consultation: premium can be justified

## AI Role

The LLM should not create raw numbers by itself.

The LLM should explain:

- why a candidate was generated,
- what risks were found,
- what trade-offs exist,
- which candidate is safer,
- what the admin should review before approval.

All numeric operations must be performed by backend services.

## UI Product Direction

QuoteOps AI should look more polished than the previous ModelMate project.

The UI should feel like:

- a premium AI SaaS workspace,
- not a student CRUD dashboard,
- not a generic ecommerce template,
- not a crowded admin panel.

Use ChatGPT-like analysis flow, Apple-like spacing, and Linear/Notion-like workspace cleanliness.

## MVP Success Criteria

The MVP is successful if it can demonstrate this flow:

```text
1. Admin selects A3 Flyer or Product Sticker.
2. Admin uploads or enters competitor prices.
3. Admin labels competitors by type.
4. Admin enters own cost and minimum margin.
5. Admin selects a pricing strategy.
6. System generates 2-3 price table candidates.
7. System validates margin risk, price inversion, and discount cliffs.
8. AI explains candidate pros/cons in Korean.
9. Admin approves one candidate.
10. Customer quote page uses the approved price table.
11. Agent log shows plan, tool calls, observations, decisions, and approval.
```

## Final Project Positioning

Recommended Korean description:

> QuoteOps AI는 소규모 인쇄·스티커·주문제작 업체를 위한 AI 가격 운영 에이전트입니다. 경쟁사 가격을 무조건 따라가는 것이 아니라, 자사 원가와 최소 마진, 지역 경쟁력, 서비스 강점을 함께 고려하여 수량별 가격표 후보를 생성하고, 가격 역전·할인 절벽·마진 부족 위험을 검증한 뒤 관리자의 승인으로 가격표를 확정합니다.

Recommended English description:

> QuoteOps AI is a market-aware, margin-protected pricing agent for small print and custom-product businesses. It helps generate and validate quantity-based price tables using competitor prices, internal costs, minimum margins, and human-approved AI explanations.
