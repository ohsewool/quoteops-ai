# V2-05 Gap Log

No known mandatory V2-05A gaps remain after verification.

## Verified V2-05A scope

- Pricing source data is restricted to the two V2 MVP product codes and is
  persisted with PostgreSQL Decimal/Numeric constraints.
- One active cost profile per product is database-enforced; input rates below
  one, positive quantities, product/competitor foreign keys, supported
  strategies, and KRW evidence currency are all constrained.
- Candidate formulas and validation rules are deterministic and independent of
  an LLM. `failed/high`, `warning/medium`, and `passed/low` readiness are
  persistent and test-covered.
- Every pricing check records its immutable Quote revision/version, selected
  strategy, source profile/version, competitor-reference snapshot, formula,
  validation rule, and rounding policy version.
- Viewers receive only aggregate safe pricing evidence and cannot read raw cost
  profiles, raw component costs, or competitor-reference management APIs.
- Pricing evidence rows are database-immutable; the test database downgrade
  and re-upgrade recovery cycle passed.
- The application database remains untouched at V2-04 head. Destructive tests
  remained limited to the V2 test database.
- V1 remains unchanged. The ignored root `.env` remains untracked.

## Deferred only to V2-05B and later scopes

- The API-backed Pricing Check Workspace is V2-05B work, not a backend gap.
- Quote workflow transition into approval is V2-06 work. V2-05A preserves a
  draft Quote after a check so a manager can correct it before submission.
- Approval requests, reports, AI outputs, price-table activation, CSV tools,
  and V1 migration are deliberately out of scope for V2-05A.

## Manual visual evidence

Browser/Playwright capability is unavailable in this local execution
environment. V2-05B component checks will run locally; full visual evidence
remains a V2-10B manual-review requirement and is not claimed here.
