# Changelog

## v0.5.0 (upgrade baseline)

- Added FastAPI lifespan lifecycle and runtime config validation.
- Added `/ready` and `/metrics` endpoints.
- Added optional API key auth and per-client rate limit guard.
- Added HF jobs list endpoint with pagination/filtering.
- Improved retrieval fallback to hybrid fulltext strategy.
- Expanded tests for HF ingestion and background jobs APIs.
- Added CI workflow with lint, type-check, tests, and compile checks.
- Added coverage threshold gate.
