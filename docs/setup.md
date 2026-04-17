# Setup & Run

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker + Docker Compose

## 1) Configure environment

```bash
cp .env.example .env
printf "%s" "YOUR_GEMINI_API_KEY" > .gemini_key.txt
chmod 600 .gemini_key.txt
```

Important envs:

- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
- Optional: `APP_API_KEY`, `RATE_LIMIT_PER_MINUTE`, `LOG_LEVEL`
- Optional strict startup check: `REQUIRE_GEMINI_KEY_ON_STARTUP=true`

## 2) Start Neo4j

```bash
docker compose up -d
```

## 3) Install dependencies

```bash
uv sync --all-groups
```

## 4) Run API

```bash
uv run uvicorn src.main:app --reload --port 8000
```

Open:

- API docs: <http://localhost:8000/docs>
- Neo4j Browser: <http://localhost:7474>

## 5) Local quality checks

```bash
uv run ruff check src tests
uv run mypy src
uv run pytest
python -m compileall -q src tests
```
