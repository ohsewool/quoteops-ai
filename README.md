# QuoteOps AI V2

QuoteOps AI V2 is a lightweight pricing operations SaaS and grounded pricing operations copilot. It connects customer requests, persistent quotes, deterministic pricing checks, human approval or rejection, and report generation.

## Current checkpoint

`V2-01A` establishes a clean repository, strict environment policy, dependency locks, neutral React foundation, and documentation structure. It does not contain product domains, business APIs, demo data, or a completed product UI.

`V2-01B` prepares the FastAPI, SQLAlchemy, Alembic, authentication, audit, Decimal, and security baseline. Its mandatory real PostgreSQL integration verification is blocked until an explicitly identified V2-only PostgreSQL target is available.

The authoritative product and security decisions are in [docs/v2/V2-00-PRODUCT-CONTRACT.md](docs/v2/V2-00-PRODUCT-CONTRACT.md).

## Local prerequisites

- Python 3.12+
- Node.js 24+ and pnpm 11+
- A clearly identified V2-only PostgreSQL development or test database before database migrations run

Docker, Docker Compose, V1 databases, shared databases, and production databases are not local-development prerequisites.

## Foundation commands

Create an isolated virtual environment, install the pinned backend dependencies, then run the foundation checks:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pytest -q backend/tests
```

For the frontend, use pnpm from the `frontend` directory:

```powershell
pnpm install --frozen-lockfile
pnpm test
pnpm build
```

Before database work, read [docs/development/native-postgresql.md](docs/development/native-postgresql.md). The environment-check script never prints URLs or secrets:

```powershell
.\scripts\validate-v2-environment.ps1 -Environment local
```

After Alembic has successfully prepared a V2-only database, create the first administrator explicitly. No account is seeded at application startup:

```powershell
.\.venv\Scripts\python -m backend.cli.create_first_user --username admin --display-name "V2 Admin"
```

## Safety boundary

- V1 remains read-only evidence and is not modified by this repository.
- The initial V2 currency is KRW. Saved money and rates use `Decimal` and PostgreSQL `NUMERIC`, never `Float`.
- No anonymous business mutation, optional-auth approval mutation, automatic price activation, or AI numeric/workflow mutation is permitted.
- Production demo users, demo seed data, docs/OpenAPI exposure, and detailed system-status access are prohibited by default.
