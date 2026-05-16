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
- `citations[]` with `page_title`, `page_url`, `chunk_id`, `snippet`, `score`
- `strategy` (`generated_readonly_cypher` or `hybrid_fulltext`)

## Optional request auth/rate limit

If `APP_API_KEY` is set, protected endpoints require:

- `X-API-Key: <APP_API_KEY>`

Rate limiting is per client IP, configurable by `RATE_LIMIT_PER_MINUTE`.

## Error responses

All endpoints return standardized error payloads:

```json
{
  "error_code": "invalid_request",
  "message": "Rate limit exceeded",
  "request_id": "c2c57f7b-1b2b-4a7c-8b4f-9ae6e1f1f5c2",
  "hint": "Reduce request rate or increase RATE_LIMIT_PER_MINUTE"
}
```


## Query explain

### `POST /query/explain`

Returns query strategy and active provider/model settings without executing retrieval.

Request:

```json
{
  "question": "What is Neo4j used for?",
  "top_k": 5
}
```

Response includes:
- `strategy.primary`
- `strategy.fallback`
- `providers.orchestrator` / `providers.orchestrator_model`
- `providers.cypher` / `providers.cypher_model`

## Export

### `GET /export?format=jsonl|csv`

Streams Page/Chunk/Entity nodes and relationships.

Formats:
- `jsonl` (default): NDJSON records of nodes and relationships.
- `csv`: rows with `kind`, `label`, `rel_type`, `id`, `source`, `target`, `props`.

Example:

```bash
curl "http://localhost:8000/export?format=jsonl" -H "X-API-Key: $APP_API_KEY"
```
