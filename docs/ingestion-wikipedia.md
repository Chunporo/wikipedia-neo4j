# Ingestion Mode: Wikipedia API

Endpoint: `POST /ingest`

This mode fetches live pages from Wikipedia via the Python `wikipedia` package.

Pipeline:

1. Fetch page + summary
2. Chunk text
3. Extract simple entities
4. Generate embeddings (Gemini)
5. Upsert Page/Chunk/Entity in Neo4j
6. Add `LINKS_TO` edges from page hyperlinks

Example:

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"topics":["Graph database","Neo4j"]}'
```
