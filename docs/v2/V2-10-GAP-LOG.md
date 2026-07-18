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

## V2-10B locally verified scope

- A versioned, pure V1 read-only export transformer and quarantine report are
  implemented and tested with synthetic accepted and rejected data. They do
  not connect to V1 or V2 and perform no database write.
- V1 Float-derived values are accepted only as exact decimal strings. Legacy
  price evidence is recomputed against the V2 formula and quarantined when the
  difference exceeds `0.01` KRW.
- The final complete PostgreSQL backend regression passed with `69 passed in
  833.65s`; frontend regression passed with `30 passed in 78.51s`, and the
  production build completed with 57 transformed modules in 2.77s.
- The non-destructive release-readiness command returned
  `release_readiness=VERIFIED_LOCAL`. Both V2 databases are at
  `0009_operations_demo_domain`; the application database has zero users.
- Public landing and login visual checks passed at desktop and at a true 390px
  emulated mobile viewport with no horizontal document overflow.
- The V2 application has zero users. The run did not auto-create a user or
  bypass the explicit first-user CLI policy.
- The first-user CLI and a subsequent-user CLI are available only as explicit
  local commands. The latter requires an active admin actor, rejects the test
  database, writes a safe provisioning audit event, and never receives a
  password through an audit event.

## Clean-launch migration decision

- **V1 data migration: NOT APPLICABLE.** The former V1 database contained
  disposable demo data and was deleted. V2 launches against a new clean V2
  database, so no V1 data will be exported or imported.
- The V1 repository and Git history remain preserved as read-only evidence;
  no V1 database connection is required or permitted for this launch.
- This removes only the V1 export/import/migration-dry-run gate. It does not
  represent a passed migration dry run and does not remove authenticated QA,
  staging smoke, rollback rehearsal, or human cutover approval.

## Mandatory external blockers

1. No separate V2 staging deployment, staging credentials, or staging rollback
   environment is available. Deployment is explicitly prohibited for this run.
2. Protected browser workflow QA needs a deliberately provisioned reviewer
   account through the first-user CLI, with credentials supplied through an
   ignored local environment file or interactive input. No credentials were
   provided and none were created automatically.
3. The staging rollback rehearsal and separately authorized cutover decision
   cannot occur until the preceding gates are satisfied.

The autonomous run has not deployed, created a remote, pushed, opened a pull
request, modified V1, or connected V1 to either V2 database. Those safeguards
remain in force.

V2 LOCAL MANUAL REVIEW BLOCKED. The parent V2-10 release gate is blocked
pending the mandatory external evidence above.
