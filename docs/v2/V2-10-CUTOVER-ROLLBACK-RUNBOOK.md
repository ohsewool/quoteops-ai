# V2-10 Cutover and Rollback Runbook

## Status

This is a manual runbook, not deployment authorization. V2-10B has not
performed staging deployment, production deployment, cutover, or rollback.

## Preconditions

1. V2 local release readiness, full regression, and security gates are green.
2. A V2 staging deployment has separate credentials and databases from V1 and
   from the V2 local/test environments.
3. The staged application has passed health, liveness, readiness, OpenAPI,
   authentication, CORS, and complete core-workflow smoke checks.
4. A reviewer provisioned the required staging accounts through the explicit
   first-user flow. No default or startup account is permitted.
5. The V1 read-only export transform/import dry run is approved: all row-count
   differences are explained and every quarantine disposition is recorded.
6. A recoverable V2 staging/database snapshot and prior V2 artifact are
   identified. V1 remains unchanged and independently available.
7. A named human release owner explicitly approves the cutover window.

## Staging verification sequence

1. Deploy only the approved V2 artifact to the isolated V2 staging target.
2. Confirm public health/live/ready and the protected-system/OpenAPI policy.
3. Perform authenticated browser QA for both MVP products through the complete
   request, quote, pricing check, approval, and report journey.
4. Verify viewer, manager, and admin authorization behavior and audit lineage.
5. Run the reviewed V1 manifest import only with the dedicated migration actor.
   Compare accepted, quarantined, and imported counts to the approved report.
6. Exercise the rollback procedure below against staging before any cutover
   decision.

## Rollback rehearsal

1. Stop new V2 writes and record the incident/cutover timestamp.
2. Route traffic back to the unchanged V1 serving path.
3. Deploy the previously verified V2 artifact or disable the new V2 entry
   point, according to the approved platform procedure.
4. Restore only the V2 database from the verified V2 snapshot when required.
   Never restore, truncate, or reverse-write V1 data.
5. Verify V1 availability independently and verify V2 post-rollback health.
6. Record elapsed recovery time, data scope, observations, and approval. Any
   unexplained discrepancy blocks the cutover.

## Cutover decision

The release owner may approve cutover only after the staging verification and
rollback rehearsal evidence is complete. Otherwise record a rejection or
deferral and keep V1 serving. A V2 migration never authorizes an automatic V1
decommission.
