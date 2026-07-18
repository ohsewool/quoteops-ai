# Native PostgreSQL Policy

QuoteOps AI V2 requires a PostgreSQL database for migrations and integration verification. Docker, Docker Compose, V1 databases, production databases, and shared databases are prohibited.

## Approved targets

Use exactly one clearly identified target:

1. Existing native local PostgreSQL for V2 development or V2 test only.
2. A dedicated V2-only remote development or test PostgreSQL database.
3. The temporary PostgreSQL service in GitHub Actions CI.

## Before connecting

- Record the target classification: local development, local test, remote development, remote test, or CI test.
- Confirm that it is not a V1, production, or shared database.
- Use different application and test database names.
- Keep the URL in an untracked `.env`; never print it in scripts, logs, API responses, or documentation.
- Run Alembic only after this identification is complete.

## Native local setup

This repository does not install PostgreSQL automatically. If PostgreSQL is already installed, create V2-only roles and databases manually through the operator's normal PostgreSQL administration process. Use the placeholder patterns from `.env.example`, replace `CHANGE_ME` locally, and keep local test data disposable.

## Verification rule

SQLite can support fast non-database unit tests only. It never proves PostgreSQL compatibility, Alembic correctness, Numeric precision, locking, or concurrent approval behavior. If no approved PostgreSQL target is available, database-dependent V2 subphases remain blocked.
