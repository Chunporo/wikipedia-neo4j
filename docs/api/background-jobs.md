# Background HF Ingestion Jobs

These endpoints run Hugging Face ingestion asynchronously.

## Start job

`POST /ingest/hf/jobs`

```json
{
  "config_name": "20231101.simple",
  "split": "train",
  "sample_size": 3,
  "streaming": true
}
```

Returns a `job_id`.

## Check single job

`GET /ingest/hf/jobs/{job_id}`

## List jobs

`GET /ingest/hf/jobs?status=<status>&limit=50&offset=0`

Supports filtering by status and pagination.

## Stop job

`POST /ingest/hf/jobs/{job_id}/stop`

## Status values

- `running`
- `cancelling`
- `cancelled`
- `completed`
- `failed`
- `interrupted` (server restarted mid-run)

## Persistence

Job state is persisted in `.hf_ingest_jobs.json` using atomic writes.
On startup, stale `running/cancelling` jobs are marked `interrupted`.
