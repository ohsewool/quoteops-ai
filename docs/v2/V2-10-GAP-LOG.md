# V2-10 Gap Log

## V2-10A verified scope

- Complete backend and frontend regression passed after a clean PostgreSQL
  downgrade-to-base and upgrade-to-head cycle on the V2 test database only.
- The application database remained at V2-09 Alembic head and was not
  downgraded, truncated, or reseeded.
- Local release smoke, API contract, security/configuration/no-startup checks,
  schema/table/trigger checks, environment/secret artifact checks, and V1
  read-only tracked-diff checks passed.
- The new release smoke tool is deliberately non-destructive and does not
  expose database URLs, credentials, tokens, keys, or passwords.

## V2-10B pending scope

- Manual authenticated browser visual QA requires a deliberately provisioned
  local reviewer account through the explicit first-user CLI; no credential was
  supplied and no account was created automatically.
- Staging deployment smoke, V1 read-only export/migration dry-run, quarantine
  review, rollback rehearsal against deployed staging, and cutover approval
  require external staging infrastructure and authorized V1 export evidence.
- The autonomous run has not deployed, created a remote, pushed, or connected
  V1 to either V2 database. Those safeguards are intentional and remain in
  force.

V2-10B remains a mandatory release-readiness gate and has not yet received a
verdict in this checkpoint.
