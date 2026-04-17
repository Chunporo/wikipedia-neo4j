# Operations & Troubleshooting

## Common issues

### Neo4j auth mismatch

- Symptom: `Neo.ClientError.Security.Unauthorized`
- Fix: ensure `.env` `NEO4J_PASSWORD` matches `docker-compose.yml` auth.

### Empty retrieval after ingestion

- Ensure ingestion actually completed.
- Retry with direct page-title keywords.

### Gemini region/quota errors

- Multi-key rotation is supported via `.gemini_key.txt`.
- If all keys fail, ingestion/query generation may fail and query falls back.

### Background jobs after restart

- Jobs are persisted in `.hf_ingest_jobs.json`.
- Jobs active during restart are marked `interrupted`.

## Security controls

Optional:

- `APP_API_KEY` to require `X-API-Key` on protected endpoints.
- `RATE_LIMIT_PER_MINUTE` for per-client request throttling.

## Readiness and metrics

- `GET /ready` verifies Neo4j connectivity and reports dependency status.
- `GET /metrics` exposes `hf_jobs_total{status=...}`.

## Useful commands

```bash
uv run ruff check src tests
uv run mypy src
uv run pytest
python -m compileall -q src tests
uv run mkdocs build
```

## About MkDocs Material warning banner

Material may print an informational warning about MkDocs 2.0 changes.

- Not a build failure.
- Project pins compatible versions (`mkdocs<2`, `mkdocs-material<10`).

Optional quiet build:

```bash
NO_MKDOCS_2_WARNING=1 uv run mkdocs build
```
