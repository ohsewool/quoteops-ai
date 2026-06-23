# QuoteOps AI

QuoteOps AI is an AI-assisted pricing and quoting operations system for small print, sticker, and custom-product businesses.

It helps generate and validate quantity-based price table candidates using competitor prices, internal cost, minimum margin, competitor type, and pricing strategy.

## Current Status

This repository is at **Phase 0 scaffold**.

Included:

- React + Vite frontend
- Tailwind CSS
- Framer Motion
- lucide-react
- Recharts dependency
- FastAPI backend
- `/api/health` endpoint
- starter project docs

Not included yet:

- pricing calculation logic
- database schema
- OpenAI integration
- candidate generation
- approval workflow
- deployment config

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

Open:

```text
http://localhost:8000/api/health
http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

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
