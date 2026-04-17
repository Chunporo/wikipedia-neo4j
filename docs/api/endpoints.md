# API Endpoints

## Health

### `GET /health`

Basic process health.

### `GET /ready`

Readiness probe with dependency status.

Returns:

- `status`: `ok` or `degraded`
- `neo4j`: `{ok, error}`
- `gemini`: key-file path metadata

### `GET /metrics`

Prometheus-style text metrics.

Current metric:

- `hf_jobs_total{status="..."}`

## Wikipedia topic ingestion

### `POST /ingest`

Request:

```json
{
  "topics": ["Graph database", "Neo4j"]
}
```

## Hugging Face ingestion

### `POST /ingest/hf`

Request:

```json
{
  "config_name": "20231101.en",
  "split": "train",
  "sample_size": 2,
  "streaming": true
}
```

## Query

### `POST /query`

Request:

```json
{
  "question": "What is Neo4j used for?",
  "top_k": 5
}
```

Response contains:

- `answer`
- `citations[]` with `page_title`, `page_url`, `chunk_id`

## Optional request auth/rate limit

If `APP_API_KEY` is set, protected endpoints require:

- `X-API-Key: <APP_API_KEY>`

Rate limiting is per client IP, configurable by `RATE_LIMIT_PER_MINUTE`.
