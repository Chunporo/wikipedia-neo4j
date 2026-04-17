# Ingestion Mode: Hugging Face Wikipedia Dataset

Dataset: `wikimedia/wikipedia`

Common config format: `<dump>.<lang>` (for example `20231101.en`, `20231101.simple`).

## Synchronous endpoint

`POST /ingest/hf`

```bash
curl -X POST "http://localhost:8000/ingest/hf" \
  -H "Content-Type: application/json" \
  -d '{"config_name":"20231101.en","split":"train","sample_size":2,"streaming":true}'
```

## Streaming mode

Use `"streaming": true` for large language subsets to avoid loading full dataset into memory.

## Recommended for large imports

Use background jobs (`/ingest/hf/jobs`) so API remains responsive during ingestion.
