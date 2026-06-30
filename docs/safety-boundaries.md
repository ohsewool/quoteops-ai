# Safety Boundaries

QuoteOps AI is designed as a deterministic pricing operations MVP with human review.

## What The App Does

- Uses deterministic backend calculations for quote preview, candidate prices, validation, simulations, and scenario comparisons.
- Records approval and audit activity for human-in-the-loop workflows.
- Provides safe explanations and dashboard insights based on existing deterministic results.
- Supports local/demo workflows for portfolio presentation.

## Required Boundaries

- Human approval is required before using pricing outputs.
- The app does not automatically approve prices.
- The app does not automatically activate price tables.
- External AI is not required by default for pricing calculations.
- The app does not perform real competitor scraping.
- The app does not send emails.
- The app does not include a payment flow.
- The app does not provide a production reset endpoint.
- Secrets must stay in environment variables and deployment dashboards.

## Secret Handling

Do not commit `.env`, database files, Render credentials, API keys, auth secrets, private keys, or token values. Frontend code must not contain secrets.
