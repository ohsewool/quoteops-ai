# Demo Flow

This demo flow is intended for portfolio review, stakeholder walkthroughs, and local MVP verification.

## Setup

Optional: seed repeatable demo data before a walkthrough.

```bash
py -3 scripts/seed_demo_data.py
```

For a full local demo reset, use the explicit confirmation form documented in
`docs/DEMO_DATA.md`.

1. Start the backend.
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
2. Start the frontend.
   ```bash
   cd frontend
   pnpm run dev
   ```
3. Open the workspace at `http://localhost:5173`.
4. Log in with the local/demo owner account if demo seeding is enabled:
   - email: `admin@quoteops.local`
   - password: `quoteops-demo-admin`

Local/demo credentials are for local demonstration only. Do not use them in public deployments.

## Walkthrough

1. **Admin Login**
   - Show that price operations require an admin session.
   - Point out the active role indicator.

2. **Operations Dashboard**
   - Review KPI cards and status charts.
   - Explain that KPI numbers come from stored backend data, not AI.

3. **Product And Catalog Data**
   - Open the product/catalog section.
   - Show A3 Flyer and Product Sticker as the MVP products.
   - Explain that future products reuse the same pricing flow.

4. **Competitor Price References**
   - Show manually entered competitor prices.
   - Explain that competitor prices are reference data only.
   - State clearly that no web scraping is used.

5. **Cost Profile**
   - Show unit cost, fixed cost, minimum margin rate, and minimum price.
   - Explain that internal margin rules protect business sustainability.

6. **Quote Preview**
   - Run a deterministic quote preview for a seeded product, quantity, and option summary.
   - Explain that quote numbers come from the active price table or cost fallback.

7. **Candidate Price Table Generation**
   - Generate a candidate table from an existing product, strategy, option summary, and quantities.
   - Explain that candidate prices are calculated by backend formulas and remain inactive.

8. **Validation Result**
   - Run validation for the candidate table.
   - Review risk level, status, warning codes, and row-level findings.
   - Explain that validation is deterministic backend logic.

9. **AI Explanation**
   - Generate an AI or fallback explanation.
   - Explain that AI summarizes deterministic facts and does not create numeric prices.
   - If `OPENAI_API_KEY` is missing, show fallback mode.

10. **Human Approval Or Rejection**
    - Show approve/reject controls.
    - Explain that only a human owner can approve or reject a candidate.
    - Explain that approval archives the previous active price table and activates the approved copy.

11. **Audit Log And Agent Timeline**
    - Show operation traceability.
    - Point out candidate generation, validation, explanation, approval/rejection, CSV, and auth-related entries.

12. **Exportable Reports**
    - Generate a read-only report such as a candidate report, validation report, approval evidence report, or operations snapshot.
    - Explain that reports are print-friendly snapshots and do not approve, activate, validate, or change prices.
    - Point out that report HTML avoids secrets and can be saved as PDF from the browser.

13. **System Status**
    - Open the System Status panel.
    - Show backend status, database connectivity, database type, OpenAI/fallback status, audit logging, job workflow, and last checked time.
    - Explain that status endpoints expose safe booleans and labels, not secrets.

## Demo Talking Points

- AI explains pricing decisions but does not decide prices.
- Human owner approval is required before a candidate affects customer quotes.
- Competitor prices are manually entered reference data.
- Quote, candidate, validation, simulation, comparison, and KPI numbers are deterministic backend outputs.
- No web scraping, payment, checkout, customer accounts, or automatic activation are included in the MVP.
