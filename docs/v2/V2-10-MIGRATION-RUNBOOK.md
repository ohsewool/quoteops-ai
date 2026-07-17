# V2-10 Migration Runbook

## Purpose

This runbook governs the V1-to-V2 migration preflight. It is intentionally
read-only on the V1 side and does not authorize a live import or a cutover.
V1 remains available and unchanged throughout the process.

## Local artifact

The checked-in tool is:

```text
python scripts/transform_v1_readonly_export.py \
  --input <authorized-readonly-export.json> \
  --manifest <v2-import-manifest.json> \
  --quarantine-report <v2-quarantine-report.json> \
  --require-clean
```

It accepts only `quoteops-v1-readonly-export` with format version `v1`. It
does not read `.env`, open a database, create a user, mutate V1, or write V2.
It writes two local JSON artifacts and reports only aggregate counts.

## Export contract

The deployment owner supplies a versioned, read-only JSON export with an
ISO-8601 timezone-aware `exported_at` value and only the intended migration
sections. Decimal and rate values must be JSON strings, never JSON numbers.
Sensitive fields such as password hashes, tokens, secrets, or connection
strings are prohibited and make the preflight fail before it writes artifacts.

| V1 section | V2-10 treatment | Review rule |
|---|---|---|
| `products` | Candidate V2 product manifest record | Only explicit `a3_flyer` and `brand_sticker` SKU mappings are accepted. Other products are quarantined. |
| `cost_profiles` | Candidate V2 cost-profile manifest record | Amounts/rates must be exact Decimal text; active profiles must be unique per accepted product. |
| `price_table_items` | Legacy validation evidence only | It is not imported into V2. Its price is recomputed from the accepted active cost profile and margin; a difference greater than `0.01` KRW is quarantined. |
| Other sections | Quarantine only | They remain outside this initial V2 import until a separate contract approves their lineage and role mapping. |

The manifest records a SHA-256 fingerprint of the source document, accepted
records, validated legacy evidence, quarantine items, and aggregate counts. A
quarantine item records only a source entity, numeric source ID when valid, and
reason code. It does not copy rejected raw values.

## Required migration sequence

1. The V1 deployment owner produces the authorized read-only export outside
   this repository and confirms it contains no real secrets.
2. Run the transformer against a local copy of that export. Preserve the input
   unchanged and retain the output manifest/report as review evidence.
3. Stop if the command exits nonzero or the quarantine report has any items.
   Resolve each item in a reviewed source mapping; do not silently coerce,
   discard, or round a record.
4. Have an authorized reviewer approve the clean manifest, the source
   fingerprint, row counts, and every explicit exclusion.
5. Only in a separately provisioned V2 staging environment, use a dedicated
   migration actor to import the reviewed manifest. The actor must be created
   with the explicit first-user/admin provisioning flow, never at application
   startup.
6. Re-run the complete V2 validation suite and core journey on staging. Compare
   accepted/imported counts against the reviewed manifest and record any
   quarantine disposition.
7. Do not write back to V1. Do not reuse V1 credentials, database URLs, or
   session tokens for V2.

## Blocking conditions

- missing or unauthorized V1 export;
- any secret field in the export;
- non-clean quarantine report;
- source fingerprint/count disagreement;
- missing dedicated staging environment or migration actor;
- any V1/V2 database, credential, or deployment boundary breach.

No live import or cutover is permitted until every blocking condition is
cleared and the separate cutover/rollback runbook is approved.
