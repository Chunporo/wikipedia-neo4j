# Wikipedia Neo4j GraphRAG Demo

[![CI](https://github.com/Chunporo/wikipedia-neo4j/actions/workflows/ci.yml/badge.svg)](https://github.com/Chunporo/wikipedia-neo4j/actions/workflows/ci.yml) ![Python](https://img.shields.io/badge/python-3.12%2B-blue) ![Coverage](https://img.shields.io/badge/coverage-75%25%2B-brightgreen)

Backend demo that ingests Wikipedia content into Neo4j and answers questions with citations.

## Highlights

- Ingestion sources:
  - Wikipedia API (`POST /ingest`)
  - Hugging Face dataset (`POST /ingest/hf`)
  - Async HF jobs (`POST /ingest/hf/jobs`)
- Query pipeline:
  - Gemini-generated read-only Cypher (validated)
  - Safe hybrid fallback retrieval (chunk + page fulltext)
- Reliability:
  - Persistent HF job state in `.hf_ingest_jobs.json`
  - Startup restore marks stale running jobs as `interrupted`
  - Atomic job-state writes
- Operations:
  - `/health`, `/ready`, `/metrics`
  - Optional API key auth + per-client rate limiting

## Quick start

### 1) Configure

```bash
cp .env.example .env
printf "%s" "YOUR_GEMINI_API_KEY" > .gemini_key.txt
chmod 600 .gemini_key.txt
```

### 2) Start Neo4j

```bash
docker compose up -d
```

### 3) Install dependencies

```bash
uv sync --all-groups
```

### 4) Run API

```bash
uv run uvicorn src.main:app --reload --port 8000
```

Docs: <http://localhost:8000/docs>

## API examples

### Ingest topics

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"topics":["Graph database","Neo4j"]}'
```

### Ingest HF sample

```bash
curl -X POST "http://localhost:8000/ingest/hf" \
  -H "Content-Type: application/json" \
  -d '{"config_name":"20231101.simple","split":"train","sample_size":2,"streaming":true}'
```

### Start async HF job

```bash
curl -X POST "http://localhost:8000/ingest/hf/jobs" \
  -H "Content-Type: application/json" \
  -d '{"config_name":"20231101.simple","split":"train","sample_size":3,"streaming":true}'
```

### Query

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"How are graph databases used?","top_k":4}'
```

### Health/Readiness/Metrics

```bash
curl "http://localhost:8000/health"
curl "http://localhost:8000/ready"
curl "http://localhost:8000/metrics"
```

## Development

```bash
uv run ruff check src tests
uv run mypy src
uv run pytest
python -m compileall -q src tests
```

CI workflow is under `.github/workflows/ci.yml`.
