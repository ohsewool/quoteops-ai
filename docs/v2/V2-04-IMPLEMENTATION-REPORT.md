# V2-04 Implementation Report

| Subphase | Scope | Commit | Tests | Independent review | Verdict |
|---|---|---|---|---|---|
| V2-04A | Persistent Quote, QuoteLine, immutable revision snapshots, PostgreSQL migration | `69a1387` | Domain/schema target: 3 passed. Full backend: 30 passed. | KRW Numeric types, request lineage, lower-case PostgreSQL enum values, positive snapshot quantities, FK/check/unique constraints, and database-enforced revision immutability were reviewed. | V2-04A VERIFIED |
| V2-04B | Quote conversion, draft, line, revision APIs | Pending | Not started | Not started | Pending |
| V2-04C | Quote list and workspace UI | Pending | Not started | Not started | Pending |

## V2-04A delivery

Migration `0003_quote_domain` adds four PostgreSQL tables:

```text
quotes
quote_lines
quote_revisions
quote_revision_lines
```

The Quote holds the request lineage, customer/request snapshot, one of the
contractual Quote statuses, currency, current deterministic total, formula and
rounding policy versions, assignee, creator, optimistic version, and current
revision number. Current quote lines remain mutable draft working data; each
immutable revision copies complete header and line snapshots for reproducible
history.

All monetary fields are PostgreSQL-compatible `NUMERIC(18,2)`, all stored
currency values are constrained to `KRW`, and quantities/positions/versions are
checked at the database boundary. `quote_revisions` and
`quote_revision_lines` have PostgreSQL triggers that reject update or delete
attempts. No Quote API, pricing calculation, approval, AI behavior, automatic
activation, or V1 change is included in this subphase.

## PostgreSQL evidence

The V2 test database upgraded to `0003_quote_domain`, was downgraded to
`0002_customer_request_domain`, verified clear of all Quote tables and the
`quote_status` enum, then re-upgraded to V2-04A head. This destructive cycle
ran only on the test database.

```text
v2_04_test_downgrade_revision_is_0002=True
v2_04_test_quote_tables_absent_after_downgrade=True
v2_04_test_quote_status_absent_after_downgrade=True
v2_04_test_reupgrade=OK
quote_domain_schema_target=3 passed in 17.36s
backend_regression=30 passed in 92.69s (0:01:32)
```

The application database remains at V2-03 head during V2-04A. Its forward-only
V2-04 activation is deferred to parent-phase verification after V2-04B and
V2-04C. No application-database downgrade was run.

## Exact verification results

```text
python -m compileall backend alembic: completed successfully
pytest -q backend/tests/test_quote_domain.py backend/tests/test_quote_postgresql_schema.py: 3 passed in 17.36s
pytest -q backend/tests: 30 passed in 92.69s (0:01:32)
```

Browser visual verification is not claimed in this local environment and
remains a V2-10B manual-review item.
