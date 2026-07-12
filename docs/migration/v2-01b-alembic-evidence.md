# V2-01B Alembic Evidence

The initial migration is `0001_security_foundation` and creates only:

- PostgreSQL `user_role` enum (`admin`, `manager`, `viewer`)
- `users`
- `audit_events`

Offline verification completed without opening a database connection:

```text
alembic upgrade head --sql
CREATE TYPE user_role AS ENUM ('admin', 'manager', 'viewer');
CREATE TABLE users (...)
CREATE TABLE audit_events (...)

alembic downgrade 0001_security_foundation:base --sql
DROP TABLE audit_events;
DROP TABLE users;
DROP TYPE user_role;
```

The upgrade SQL emits the enum exactly once. This proves migration rendering only. It does not prove a PostgreSQL migration execution.

## Required real-database gate

Before `V2-01B VERIFIED`, use an explicitly identified V2-only PostgreSQL development, test, remote test, or CI target to run:

```text
alembic upgrade head
alembic downgrade base
alembic upgrade head
pytest -q backend/tests -m postgresql
```

No V1, production, shared, or unverified database may be used for this gate.
