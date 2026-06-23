# Frontend Design System

## Design Goal

QuoteOps AI should look like a modern premium AI SaaS workspace.

It should feel closer to ChatGPT, Apple, Linear, and Notion than a typical student CRUD project.

The UI should be calm, spacious, and trustworthy.

## Stack

Use:

- React + Vite
- JavaScript
- Tailwind CSS
- shadcn/ui-inspired custom components
- lucide-react
- Framer Motion
- Recharts
- Axios
- Pretendard or Inter font

Do not use TypeScript unless explicitly requested.

## Visual Style

### Layout

- spacious pages
- centered content where appropriate
- max-width containers
- clear left/right structure for work screens
- sticky sidebar for admin workspace
- top-level navigation should be minimal

### Cards

Use soft rounded cards:

- border: subtle gray
- radius: 16px to 24px
- shadow: minimal
- background: white or near-white
- dark mode optional later

### Colors

Recommended base palette:

```text
Background: #F7F7F8
Surface: #FFFFFF
Primary Text: #111827
Secondary Text: #6B7280
Border: #E5E7EB
Primary Action: #111827 or #2563EB
Success: #16A34A
Warning: #F59E0B
Danger: #DC2626
```

Use color mainly for status, not decoration.

### Typography

Use a clean sans-serif font.

Recommended:

- Pretendard for Korean-first UI
- Inter as fallback

Text should be clear, not dense.

### Motion

Use Framer Motion only for subtle effects:

- fade in
- slight upward entrance
- soft panel transition
- progress timeline animation

Do not overuse animation.

## UX Principles

- Korean-first copy
- progressive disclosure
- summary first, technical detail later
- show user what is happening
- no fake AI magic
- no crowded tables as default
- use tables only when comparison is necessary
- use cards for candidate summaries
- use timeline for agent execution

## Core Screens

### 1. Landing Page

Goal: explain the problem and show product value quickly.

Sections:

- Hero
- Problem
- How it works
- Agent workflow
- MVP products
- Demo scenario
- CTA

Hero copy example:

> 작은 업체를 위한 AI 가격 운영 에이전트

Subcopy:

> 경쟁사 가격, 자사 원가, 최소 마진, 지역 경쟁력을 함께 고려해 안전한 수량별 가격표를 생성하고 검증합니다.

### 2. Customer Quote Calculator

Layout:

- left: product and option selection
- right: real-time quote card

Should feel clean and simple.

### 3. Admin Dashboard

Cards:

- active price tables
- margin risk ranges
- pending candidates
- recent approved versions

### 4. Competitor Price Input

Support:

- CSV upload
- manual table input
- competitor type labels

### 5. Cost and Margin Setup

Use clean form cards.

### 6. Strategy Selection

Use selectable strategy cards.

Examples:

- Local Competition
- Margin Protection
- Small-Quantity Focus

### 7. Candidate Comparison

This is a key demo screen.

Show 2-3 candidate cards:

- Balanced
- Margin-Protected
- Entry Competitive

Each card should show:

- market position
- estimated margin
- risk level
- AI explanation summary
- approve button

### 8. Agent Timeline

This is the key "real AI agent" screen.

Timeline steps:

1. Load competitor prices
2. Analyze market prices
3. Calculate minimum safe prices
4. Generate candidate tables
5. Validate risks
6. Explain results
7. Wait for approval
8. Save approved version

Each step should show status:

- pending
- running
- completed
- needs_review
- failed

### 9. Version History

Show approved price table versions and approval notes.

## Components to Build

Create local components instead of importing a heavy UI framework.

Recommended components:

- Button
- Card
- Badge
- Input
- Select
- Tabs
- Dialog
- Toast
- PageHeader
- EmptyState
- LoadingSkeleton
- MetricCard
- StrategyCard
- CandidateCard
- AgentTimeline
- RiskBadge
- PriceTable

## Design Warnings

Do not:

- copy ModelMate layout directly
- build a colorful admin template
- make it look like a generic shopping mall
- show all raw data at once
- overuse gradients
- overuse animation
- use fake AI messages as real analysis

## Success Standard

The frontend is successful if a viewer can understand the product in 30 seconds:

1. This is an AI pricing operations tool.
2. It helps small businesses avoid unsafe price tables.
3. It compares competitor prices with own margin.
4. It generates candidate price tables.
5. It validates risks.
6. It requires human approval.
