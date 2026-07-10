# Security Policy

## Reporting a vulnerability

If you discover a security issue in TRINETRA, please report it privately rather
than opening a public issue:

- Email the maintainers (Team IHRM) with a description, reproduction steps, and
  the affected component or endpoint.
- Do not include live secrets, credentials, or customer data in the report.
- Please allow reasonable time for a fix before any public disclosure.

We will acknowledge the report, investigate, and coordinate a fix and disclosure
timeline with you.

## Secrets and configuration

- All secrets and service endpoints (self-hosted Gemma/vLLM, OCR, Firecrawl, and
  the optional `API_KEY`) live in a local `.env` file.
- `.env` is git-ignored (see `.gitignore`) and must never be committed. Only
  `.env.example`, which contains no values, is tracked.
- With no endpoints configured the GenAI layer is disabled and the quantitative
  pipeline runs standalone, so the repository is safe to run without any secrets.

## Deployment hardening

The serving layer defaults to the current demo behaviour and tightens only when
you opt in via environment variables:

- **CORS.** `CORS_ORIGINS` (comma-separated) restricts allowed browser origins.
  It defaults to local development ports and the live ALB origin; set it
  explicitly in other environments.
- **API key.** `API_KEY`, when set, requires callers to send a matching
  `x-api-key` header on `/score`, `/term-structure`, and `/memo`. When unset
  (the default) no key is enforced, which keeps the same-origin cockpit working.
- **Input validation.** Scoring endpoints reject unknown feature keys, empty
  payloads, and non-finite values with HTTP 422.

## Data handling

- The engine is designed for on-premises deployment with no PII egress and is
  intended to be DPDP-compliant.
- The public datasets used for the prototype are not redistributed; the
  repository ships download scripts, not data.
