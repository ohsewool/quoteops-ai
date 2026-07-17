# V2-10 Implementation Report

| Subphase | Scope | Commit | Verification | Independent review | Verdict |
|---|---|---|---|---|---|
| V2-10A | Full local regression, security, migration, role, and rollback verification | Local V2-10A checkpoint | Full PostgreSQL backend, frontend regression/build, test-only base rollback/rebuild, release smoke, and boundary checks passed. | Release contract, schema, migrations, runtime safety, tracked artifacts, V1 boundary, and frozen Tier B paths were reviewed. | V2-10A VERIFIED |
| V2-10B | Read-only V1 export transformation, quarantine evidence, local visual QA, and release handoff | Local V2-10B checkpoint | Pure export transformation and CLI tests passed; public/login desktop and true 390px mobile visual checks passed. | The transformer has no database or V1 runtime dependency. Mandatory staging, authorized V1 export, authenticated browser, rollback, and cutover gates remain external. | V2-10B BLOCKED |

## V2-10A delivery

V2-10A adds two local-only release verification artifacts:

- `backend/tests/test_release_readiness_contract.py` locks the required Tier A
  OpenAPI surface, checks public health sanitization, and fails if frozen Tier
  B route prefixes are reintroduced.
- `scripts/verify_v2_release_readiness.py` is a safe, non-destructive smoke
  command. It verifies application/test database separation and Alembic head,
  expected V2 schema tables, public health/live/ready/OpenAPI responses,
  required OpenAPI paths, `.env` ignore status, risky tracked artifacts, and
  health/OpenAPI connection-string safety. It never prints a URL, password,
  token, key, or other secret and never migrates, truncates, or modifies a
  database.

The mandatory destructive rollback rehearsal ran only against
`quoteops_ai_v2_test`. It downgraded from V2-09 all the way to Alembic base,
verified that V2 tables and V2 enum types were absent, then upgraded cleanly
through every migration to `0009_operations_demo_domain`. The application
database remained at head throughout and was never downgraded.

## V2-10A verification

```text
python -m compileall backend scripts: completed successfully
release/security/config/no-startup target: 15 passed in 6.84s
release_readiness=VERIFIED_LOCAL
test downgrade: 0009_operations_demo_domain -> base
test_non_metadata_tables_absent_after_full_downgrade=True
test_alembic_version_rows_after_full_downgrade=0
test_v2_enum_count_after_full_downgrade=0
test re-upgrade revision=0009_operations_demo_domain
test_tables_match_v2_09=True
test_immutable_lineage_trigger_count=6
test_demo_constraints_complete=True
backend regression after clean re-upgrade: 57 passed in 937.62s (0:15:37)
frontend regression: 30 passed in 28.35s
frontend production build: 57 modules transformed; built in 1.69s
v2_float_columns=[]
startup_create_all_present=False
runtime_application_sqlite_reference_present=False
v2_env_ignored=True
v2_env_untracked=True
risky_tracked_files_absent=True
V1 tracked diff=empty
```

## V2-10A independent review

- The V2-09 release smoke script was corrected to resolve the repository root
  when invoked from `scripts/`; its focused tests and safe runtime invocation
  passed afterward.
- All 57 backend tests were rerun from the clean, re-upgraded PostgreSQL test
  schema. All 30 frontend tests and the production build were rerun after the
  backend proof.
- Required Tier A workflow routes are present. Frozen scenario, simulation,
  strategy-template, workflow-job, and price-table route families are absent.
- The application still uses PostgreSQL only, has no Float model columns, and
  creates neither schema nor users at startup.
- Application/test databases remain distinct; only the test database received
  destructive migration work. V1 was inspected read-only for tracked changes
  and remains unmodified.

V2-10A VERIFIED.

## V2-10B local delivery

V2-10B adds a deliberately database-free V1 migration-preflight path:

- `backend/services/v1_export_transform.py` transforms only an explicitly
  supplied `quoteops-v1-readonly-export` JSON document. It opens neither a V1
  connection nor a V2 connection and performs no write.
- The manifest uses `v2-10-v1-transform-v1`, preserves exact Decimal text for
  accepted product/cost records, verifies legacy price evidence against the
  deterministic cost-and-margin formula, and records a SHA-256 source
  fingerprint.
- Unsupported products, non-exact numeric values, duplicate active cost
  profiles, missing source mappings, and price recomputation differences above
  `0.01` KRW are quarantined without carrying raw rejected values into the
  quarantine report.
- `scripts/transform_v1_readonly_export.py` writes a manifest and a separate
  quarantine report from an already-exported local JSON file. It never reads
  `.env`, never contacts a database, and returns a nonzero status for
  `--require-clean` when manual quarantine review is required.

The tool creates an import manifest only. It does not auto-create a user,
connect to V1, import into V2, alter an application database, or authorize a
cutover. Those actions require a separately authorized staging procedure.

The V2-10B release materials are:

- `docs/v2/V2-10-MIGRATION-RUNBOOK.md`
- `docs/v2/V2-10-CUTOVER-ROLLBACK-RUNBOOK.md`
- `docs/v2/V2-10-RELEASE-READINESS-REVIEW.md`

## V2-10B local verification

```text
python -m compileall backend scripts: completed successfully
V1 export transformer target: 6 passed in 0.39s
CLI BOM-compatible clean-export smoke: passed through the subprocess test
database_writes_performed=False
complete PostgreSQL backend regression: 63 passed in 939.95s (0:15:39)
frontend regression: 30 passed in 21.92s
frontend production build: 57 modules transformed; built in 2.75s
release_readiness=VERIFIED_LOCAL
desktop public landing and login visual smoke: rendered cleanly
true 390px mobile public viewport: innerWidth=390, clientWidth=390, scrollWidth=390
true 390px mobile login viewport: innerWidth=390, clientWidth=390, scrollWidth=390
application_user_count=0
V1 tracked diff=empty; pre-existing V1 docs/v2/ untracked content was untouched
```

The initial screenshot attempt used Chrome's minimum headless window width and
was therefore discarded as a cropped harness artifact. The final visual result
uses Chrome device emulation at an actual 390px CSS viewport, where both
responsive breakpoints and document width were verified.

## V2-10B independent review and release decision

- The transform path accepts only exact decimal strings. A binary JSON number
  from a Float-derived V1 export is quarantined rather than rounded into V2.
- V1 `price_table_items` remain out of the initial V2 import scope. They are
  retained only as validated legacy evidence when their stored Decimal text
  matches V2 recomputation within `0.01` KRW; otherwise they are quarantined.
- The transformer is covered with accepted records, unsupported data,
  malformed numeric values, recomputation drift, duplicate active cost
  profiles, secret-field rejection, and a real CLI subprocess test.
- Unauthenticated public and login surfaces were visually checked. Protected
  workflow visual QA was not bypassed: the application has no users and first
  user provisioning remains an explicit CLI-only action.
- A real staging deployment, authorized read-only V1 export, migration dry
  run, staging rollback rehearsal, and cutover approval were not performed.
  The autonomous-run restrictions prohibit deployment and V1 database access,
  so these are mandatory external gates rather than issues to work around.

V2-10B BLOCKED. V2-10 is not complete and no cutover decision is authorized.
