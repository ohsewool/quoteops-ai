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
- The final complete PostgreSQL backend regression passed with `63 passed in
  939.95s`; frontend regression passed with `30 passed in 21.92s`, and the
  production build completed with 57 transformed modules in 2.75s.
- Public landing and login visual checks passed at desktop and at a true 390px
  emulated mobile viewport with no horizontal document overflow.
- The V2 application has zero users. The run did not auto-create a user or
  bypass the explicit first-user CLI policy.

## Mandatory external blockers

1. No authorized, versioned read-only V1 export has been supplied. The V1
   database was not accessed, and the autonomous-run boundary prohibits
   connecting V1 to either V2 database.
2. No separate V2 staging deployment, staging credentials, or staging rollback
   environment is available. Deployment is explicitly prohibited for this run.
3. Protected browser workflow QA needs a deliberately provisioned reviewer
   account through the first-user CLI, with credentials supplied through an
   ignored local environment file or interactive input. No credentials were
   provided and none were created automatically.
4. The real export transform/import dry run, quarantine review, staging
   rollback rehearsal, and separately authorized cutover decision cannot occur
   until the preceding gates are satisfied.

The autonomous run has not deployed, created a remote, pushed, opened a pull
request, modified V1, or connected V1 to either V2 database. Those safeguards
remain in force.

V2-10B BLOCKED. The parent V2-10 release gate is blocked pending the mandatory
external evidence above.
