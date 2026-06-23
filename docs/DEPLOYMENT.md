# Deployment Plan

## Primary Deployment Target

Use Render first.

Do not configure Railway for this project unless explicitly requested later.

## Why Render First

Render is suitable for this MVP because:

- FastAPI deployment is straightforward.
- GitHub integration is simple.
- PostgreSQL can be added later.
- It keeps deployment simpler than splitting frontend/backend/database too early.

## MVP Deployment Structure

Start with:

```text
Render Web Service
- FastAPI backend
- serves API
- optionally serves built React frontend
- SQLite for local development
```

For the first MVP, local development matters more than public production readiness.

## Later Production-Like Split

After the MVP works, consider:

```text
Vercel
- React + Vite frontend

Render
- FastAPI backend

Supabase
- PostgreSQL database
```

Do not start with this split unless the MVP is stable.

## Local Development

Recommended local development:

```text
frontend: Vite dev server
backend: FastAPI uvicorn
database: SQLite file
```

Commands should eventually look like:

```bash
# backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# frontend
cd frontend
npm run dev
```

## Environment Variables

Use `.env.example` with placeholders only.

Expected variables:

```dotenv
OPENAI_API_KEY=***
OPENAI_MODEL=gpt-5-mini
LLM_ENABLED=false

DATABASE_URL=sqlite:///./quoteops.db
ALLOWED_ORIGINS=http://localhost:5173
```

Do not place secrets in frontend environment variables.

## Deployment Rules

- Do not store secrets in markdown files.
- Do not commit `.env`.
- Use `.env.example` only.
- Use deterministic fallback if OpenAI API key is missing.
- Do not require LLM for core pricing calculations.
- Do not claim production readiness before real smoke tests.

## Render Build Direction

Codex should eventually create Render-friendly files only after local MVP works.

Do not spend Phase 0 overbuilding deployment.

Recommended order:

1. local scaffold
2. backend health route
3. frontend landing page
4. database initialization
5. pricing engine
6. then deployment config

## Smoke Test Checklist

Before claiming deployed MVP works:

- `/api/health` returns ok
- landing page loads
- customer quote page calculates sample quote
- admin can create or load sample competitor prices
- candidate generation works
- approval saves active price table
- quote page uses approved table
