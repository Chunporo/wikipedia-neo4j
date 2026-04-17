# Wikipedia Neo4j GraphRAG Demo

Minimal backend service for ingesting Wikipedia content into Neo4j and querying it with citations.

## Key capabilities

- Topic ingestion via Wikipedia API
- Dataset ingestion via Hugging Face (`wikimedia/wikipedia`)
- Async background HF ingestion jobs with persistent state
- Gemini-assisted read-only Cypher generation with safety validation
- Hybrid fallback retrieval for robust answers
- Health, readiness, and metrics endpoints

## Quick links

- [Architecture](architecture.md)
- [Setup & Run](setup.md)
- [API Endpoints](api/endpoints.md)
- [Background Jobs](api/background-jobs.md)
- [Operations & Troubleshooting](operations.md)
