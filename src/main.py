from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from src.config import settings, validate_runtime_settings
from src.ingest import IngestResult, ingest_from_hf, ingest_topic
from src.job_store import JobStore
from src.neo4j_client import neo4j_client
from src.retrieve import query_graph


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


class _RateLimiter:
    def __init__(self, max_requests: int, period_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            cutoff = now - self.period_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True


rate_limiter = _RateLimiter(max_requests=settings.rate_limit_per_minute, period_seconds=60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_runtime_settings()
    logger.info("Starting service", extra={"event": "startup"})
    try:
        yield
    finally:
        neo4j_client.close()
        logger.info("Shutting down service", extra={"event": "shutdown"})


app = FastAPI(title="Wikipedia Neo4j GraphRAG Demo", version="0.1.0", lifespan=lifespan)


class IngestRequest(BaseModel):
    topics: list[str] = Field(min_length=1, description="Wikipedia page topics")


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=4, ge=1, le=20)


class HFDatasetIngestRequest(BaseModel):
    config_name: str = Field(default="20231101.en", description="HF config, e.g. 20231101.en")
    split: str = Field(default="train")
    sample_size: int = Field(default=5, ge=1, le=200)
    streaming: bool = Field(default=True, description="Use HF streaming mode for large configs")


class HFIngestJobRequest(HFDatasetIngestRequest):
    pass


class _JobState(BaseModel):
    job_id: str
    status: str
    config_name: str
    split: str
    sample_size: int
    streaming: bool
    started_at: str
    finished_at: str | None = None
    processed: int = 0
    total: int | None = None
    last_title: str | None = None
    error: str | None = None
    ingested: list[dict] = Field(default_factory=list)


_jobs_lock = threading.Lock()
_jobs: dict[str, _JobState] = {}
_job_stops: dict[str, threading.Event] = {}
_job_store = JobStore(".hf_ingest_jobs.json")


def _serialize_ingest_result(result: IngestResult) -> dict:
    return {
        "topic": result.topic,
        "page_id": result.page_id,
        "title": result.title,
        "url": result.url,
        "chunk_count": result.chunk_count,
        "entity_count": result.entity_count,
    }


def _persist_job(job: _JobState) -> None:
    _job_store.upsert(job.job_id, job.model_dump())


def _restore_jobs() -> None:
    persisted = _job_store.load_all()
    for job_id, payload in persisted.items():
        try:
            job = _JobState(**payload)
        except (TypeError, ValueError):
            logger.warning("Skipping invalid persisted job payload", extra={"job_id": job_id})
            continue
        if job.status in {"running", "cancelling"}:
            job.status = "interrupted"
            if not job.error:
                job.error = "Server restarted while job was in progress"
            if not job.finished_at:
                job.finished_at = datetime.now(timezone.utc).isoformat()
        _jobs[job_id] = job
        _persist_job(job)


_restore_jobs()


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _authorize(x_api_key: str | None = Header(default=None)) -> None:
    if settings.app_api_key and x_api_key != settings.app_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _enforce_rate_limit(request: Request) -> None:
    key = _client_key(request)
    if not rate_limiter.allow(key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def _guard(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    _authorize(x_api_key)
    _enforce_rate_limit(request)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    try:
        neo4j_client.verify_connectivity()
        neo4j_ok = True
        neo4j_error = None
    except Exception as exc:
        neo4j_ok = False
        neo4j_error = str(exc)

    return {
        "status": "ok" if neo4j_ok else "degraded",
        "neo4j": {"ok": neo4j_ok, "error": neo4j_error},
        "gemini": {"key_file": settings.gemini_key_file},
    }


@app.get("/metrics")
def metrics() -> str:
    with _jobs_lock:
        counts: dict[str, int] = {}
        for job in _jobs.values():
            counts[job.status] = counts.get(job.status, 0) + 1

    lines = [
        "# HELP hf_jobs_total Number of HF ingestion jobs by status",
        "# TYPE hf_jobs_total gauge",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f'hf_jobs_total{{status="{status}"}} {count}')
    if len(lines) == 2:
        lines.append('hf_jobs_total{status="none"} 0')

    return "\n".join(lines) + "\n"


@app.post("/ingest", dependencies=[Depends(_guard)])
def ingest(req: IngestRequest, request: Request) -> dict:
    request_id = _request_id(request)
    results = []
    for topic in req.topics:
        try:
            result = ingest_topic(topic)
        except ValueError as exc:
            logger.warning("Ingest validation error", extra={"request_id": request_id, "topic": topic})
            raise HTTPException(
                status_code=400, detail=f"Failed ingest for '{topic}': {exc}"
            ) from exc
        except RuntimeError as exc:
            logger.warning("Ingest runtime error", extra={"request_id": request_id, "topic": topic})
            raise HTTPException(
                status_code=400, detail=f"Failed ingest for '{topic}': {exc}"
            ) from exc
        results.append(_serialize_ingest_result(result))
    return {"ingested": results}


@app.post("/query", dependencies=[Depends(_guard)])
def query(req: QueryRequest, request: Request) -> dict:
    request_id = _request_id(request)
    started = time.perf_counter()
    try:
        result = query_graph(req.question, req.top_k)
    except RuntimeError as exc:
        logger.exception("Query failed", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info("Query completed", extra={"request_id": request_id, "duration_ms": elapsed_ms})

    return {
        "answer": result.answer,
        "citations": result.citations,
    }


@app.post("/ingest/hf", dependencies=[Depends(_guard)])
def ingest_hf(req: HFDatasetIngestRequest, request: Request) -> dict:
    request_id = _request_id(request)
    try:
        results = ingest_from_hf(
            config_name=req.config_name,
            split=req.split,
            sample_size=req.sample_size,
            streaming=req.streaming,
        )
    except RuntimeError as exc:
        logger.warning("HF ingest failed", extra={"request_id": request_id})
        raise HTTPException(status_code=400, detail=f"Failed HF ingestion: {exc}") from exc

    return {"ingested": [_serialize_ingest_result(r) for r in results]}


def _run_hf_ingest_job(job_id: str, req: HFIngestJobRequest) -> None:
    stop_event = _job_stops[job_id]

    def _on_progress(processed: int, total: int | None, title: str) -> None:
        with _jobs_lock:
            job = _jobs[job_id]
            job.processed = processed
            job.total = total
            job.last_title = title
            _persist_job(job)

    try:
        results = ingest_from_hf(
            config_name=req.config_name,
            split=req.split,
            sample_size=req.sample_size,
            streaming=req.streaming,
            on_progress=_on_progress,
            should_stop=lambda: stop_event.is_set(),
        )
        with _jobs_lock:
            job = _jobs[job_id]
            job.ingested = [_serialize_ingest_result(r) for r in results]
            job.status = "cancelled" if stop_event.is_set() else "completed"
    except RuntimeError as exc:
        with _jobs_lock:
            job = _jobs[job_id]
            job.status = "failed"
            job.error = str(exc)
    finally:
        with _jobs_lock:
            job = _jobs[job_id]
            if not job.finished_at:
                job.finished_at = datetime.now(timezone.utc).isoformat()
            _persist_job(job)
            _job_stops.pop(job_id, None)


@app.post("/ingest/hf/jobs", dependencies=[Depends(_guard)])
def start_hf_ingest_job(req: HFIngestJobRequest) -> dict:
    job_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    with _jobs_lock:
        _jobs[job_id] = _JobState(
            job_id=job_id,
            status="running",
            config_name=req.config_name,
            split=req.split,
            sample_size=req.sample_size,
            streaming=req.streaming,
            started_at=started_at,
            total=req.sample_size if req.streaming else None,
        )
        _persist_job(_jobs[job_id])
        _job_stops[job_id] = threading.Event()

    thread = threading.Thread(target=_run_hf_ingest_job, args=(job_id, req), daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "running", "started_at": started_at}


@app.get("/ingest/hf/jobs/{job_id}", dependencies=[Depends(_guard)])
def get_hf_ingest_job(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        return job.model_dump()


@app.get("/ingest/hf/jobs", dependencies=[Depends(_guard)])
def list_hf_ingest_jobs(status: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    with _jobs_lock:
        jobs = list(_jobs.values())

    if status:
        jobs = [j for j in jobs if j.status == status]

    jobs.sort(key=lambda j: j.started_at, reverse=True)
    selected = jobs[offset : offset + max(1, min(limit, 200))]

    return {
        "total": len(jobs),
        "limit": limit,
        "offset": offset,
        "items": [j.model_dump() for j in selected],
    }


@app.post("/ingest/hf/jobs/{job_id}/stop", dependencies=[Depends(_guard)])
def stop_hf_ingest_job(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
        stop_event = _job_stops.get(job_id)
        if not job or not stop_event:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        stop_event.set()
        if job.status == "running":
            job.status = "cancelling"
        _persist_job(job)
        return {"job_id": job_id, "status": job.status}
