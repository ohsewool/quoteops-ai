# New Codex Session Prompt

Paste this into a new Codex session after creating the new repository.

```text
You are starting a new project called QuoteOps AI.

First read these files in order:
1. AGENTS.md
2. docs/PROJECT_CONTEXT.md
3. docs/MVP_SPEC.md
4. docs/DESIGN_SYSTEM.md
5. docs/DEPLOYMENT.md

Treat these files as the source of truth.

Project summary:
QuoteOps AI is an AI-assisted pricing and quoting operations system for small print, sticker, and custom-product businesses. The MVP focuses on A3 Flyer and Product / Brand Sticker. The system should generate and validate quantity-based price table candidates using competitor prices, own cost, minimum margin, competitor type, and pricing strategy. The LLM must not invent numeric prices. All numeric calculations must be deterministic backend logic. The LLM may only explain results, risks, and approval recommendations.

Final stack:
- Frontend: React + Vite + JavaScript
- Styling: Tailwind CSS
- UI: shadcn/ui-inspired local components
- Animation: Framer Motion
- Icons: lucide-react
- Charts: Recharts
- Backend: FastAPI + Python
- Database: SQLite for MVP, PostgreSQL-compatible later
- AI: OpenAI API only for explanations
- Deployment: Render first, not Railway

Before writing code, summarize:
1. project goal,
2. MVP scope,
3. target users,
4. frontend design direction,
5. backend architecture rules,
6. core AI-agent principle,
7. deterministic modules required,
8. what must not be built yet.

Then propose a clean folder structure.

Do not copy ModelMate's main_parts architecture.
Do not implement everything at once.
Start with Phase 0 only:
- create frontend/backend scaffold,
- install basic dependencies,
- add a backend health endpoint,
- add a polished landing page shell,
- add a simple README,
- add .env.example,
- do not build pricing logic yet.
```
