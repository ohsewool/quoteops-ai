# V2-07 Gap Log

## V2-07A verified scope

- Report creation requires a matching approved approval request, terminal
  approved decision, and immutable approved Quote revision. Pending, rejected,
  missing, or mismatched sources cannot create an artifact.
- Saved report values are derived from immutable Quote/pricing/approval
  evidence. The response and rendered document expose safe aggregates only,
  not raw material/labor/overhead inputs, profiles, tokens, secrets, URLs, or
  executable user input.
- The HTML renderer escapes dynamic fields, embeds a restrictive CSP, excludes
  scripts, and returns additional CSP/nosniff/no-referrer/no-store headers.
- Report rows are database-immutable. Regeneration creates a separate row with
  matching snapshot source and a predecessor link; cross-source lineage is
  database-rejected.
- PostgreSQL API/schema tests cover source status, exact numeric evidence,
  Viewers, CSP/escaping, immutable trigger behavior, audit events, OpenAPI,
  and regeneration lineage.

## V2-07B verified scope

- `/app/reports` is API-backed and supports manager/admin create, list, detail,
  sandboxed preview, safe pricing-line display, history, and regeneration.
- Viewer access is read-only. The browser never calculates a price, mutates an
  approval, emits raw cost components, or renders report HTML in the parent
  DOM.
- Focused frontend tests, frontend regression, and production build passed.

## Parent activation and boundaries

- The application database moved forward only to `0006_html_report_domain`.
  The distinct V2 test database alone completed the V2-07 downgrade and
  re-upgrade proof.
- Application schema, report trigger set, JSON readiness, ignored `.env`,
  risky tracked-file gate, and V1 tracked-diff boundary were checked.
- V1 remains untouched; its pre-existing untracked `docs/v2/` directory was
  not changed. No remote or deployment action occurred.
- Browser/Playwright visual evidence remains a V2-10B manual-review gate and
  is not claimed by V2-07.

No known mandatory V2-07 gaps remain after verification.
