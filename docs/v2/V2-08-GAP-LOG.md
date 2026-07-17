# V2-08 Gap Log

## V2-08A verified scope

- Grounded output requests accept only a purpose and existing persisted source
  IDs. The service resolves every Quote/revision/source relationship on the
  server and rejects missing or mismatched evidence.
- No output request can submit a numeric price, margin, validation status,
  approval status, report state, workflow state, reviewer identity, secret, or
  raw cost component.
- The database requires purpose-appropriate source context, validates source
  lineage in PostgreSQL, and makes every saved output immutable.
- Provider-disabled, provider-success, provider-failure, malformed/unsupported
  provider-output, and rejection/report contexts are covered by PostgreSQL
  integration tests. All provider failure paths return a deterministic fallback
  without changing core artifacts.
- The output response includes its Quote/revision, purpose, source artifacts,
  triggered rules, source-data timestamp, deterministic-fallback state,
  provider metadata, and generation timestamps. Audit metadata is sanitized.

## V2-08B verified scope

- Pricing, approval, and report detail surfaces request only stored source IDs
  and render the returned grounded text plus safe source references.
- Viewer users have read-only access and no generation control. Manager/admin
  users explicitly initiate a request; no output is generated on page load.
- The browser does not calculate pricing, mutate a workflow state, supply raw
  cost inputs, or interpret a generated draft as an approval or price command.
- Focused UI tests, full frontend regression, and production build passed.

## Parent activation and boundaries

- The V2 test database alone completed all V2-08 downgrade/re-upgrade checks.
  The V2 application database was forward-migrated once to
  `0008_copilot_context_guard` and was not downgraded.
- Application readiness, OpenAPI copilot paths, V2-only schema/trigger set,
  ignored/untracked `.env`, and first-user startup non-provisioning were
  verified.
- V1 remains unmodified. Its existing untracked `docs/v2/` directory was not
  changed. No remote, push, pull request, deployment, or external AI call
  occurred.
- Browser/Playwright visual evidence remains a V2-10B manual-review gate and
  is not claimed by V2-08.

No known mandatory V2-08 gaps remain after verification.
