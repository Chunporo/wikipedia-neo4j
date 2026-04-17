#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}

echo "[1/4] health"
curl -sf "$BASE_URL/health" >/dev/null

echo "[2/4] ready"
curl -sf "$BASE_URL/ready" >/dev/null || true

echo "[3/4] ingest sample"
curl -sf -X POST "$BASE_URL/ingest/hf" \
  -H "Content-Type: application/json" \
  -d '{"config_name":"20231101.simple","split":"train","sample_size":1,"streaming":true}' >/dev/null

echo "[4/4] query"
curl -sf -X POST "$BASE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is Neo4j?","top_k":2}' >/dev/null

echo "Smoke test OK"
