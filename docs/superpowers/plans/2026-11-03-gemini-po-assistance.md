# Gemini PO Recognition Assistance Implementation Plan

> **For implementer:** Execute inline in the existing local PO app. User selected PO file recognition/verification assistance; preserve local extraction and explicit human PO confirmation.

## Scope and design

Use the server-held Gemini key and configurable free-tier-supported Flash-Lite model. Add an optional consent-based action on the unconfirmed extraction review screen. Send only the chosen PDF/PNG (or extracted spreadsheet evidence), display validated structured proposals, and replace the extraction draft only after explicit Apply. Never create/update a registered PO automatically. Keep previous draft results for recovery and optimistic version checks. Default app limits: 20 attempts/KST day and 10MiB/file; Google project limits remain independent.

## Tasks

1. Add a Gemini REST client and strict proposal normalization, with tests for numeric/date validation, model errors, malformed/truncated responses and secret-free error text. No automatic retries or paid-model fallback.
2. Add proposal/usage ledger models and migrations. Analyze outside DB transactions, atomically claim daily quota and prevent concurrent duplicate calls. Apply under row/version locks and preserve original draft JSON. Test consent, quota, confirmation/version conflicts, and no registered PO mutation.
3. Add consent, usage disclosure, Analyze/Apply controls and safe proposal preview to review UI. Local forms remain intact until Apply. Disable controls during requests and display actionable errors without exposing keys.
4. Keep credentials only in ignored server environment. Back up the database before migrating the live app. Verify live API with synthetic documents only; do not transmit existing business POs during automated tests.
5. Run related unit tests and the full backend regression suite; validate browser failure/consent paths and live synthetic extraction. Apply migration/restart and verify actual review controls.

## Files

- `server/intake/gemini.py`: fixed Google endpoint, structured request/response and proposal validation.
- `server/intake/ai_services.py`, `ai_views.py`, models/migration: analyze/apply lifecycle and budget.
- Review template/static module and settings: consent-based product flow, configuration without credential exposure.
- Tests and operational notes: regression evidence, quota/cap explanation and rotation/configuration steps.

## Official references

- https://aistudio.google.com/docs/pricing
- https://aistudio.google.com/docs/rate-limits
- https://generativelanguage.googleapis.com/$discovery/rest?version=v1beta
