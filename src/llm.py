"""Gemini integration for embeddings and Cypher generation."""

from __future__ import annotations

import json
import re

from google import genai
from google.genai import types

from src.config import (
    load_gemini_api_keys,
    resolve_cypher_model,
    settings,
)
from src.logging_utils import get_logger


logger = get_logger(__name__)


def _is_retryable_gemini_error(exc: Exception) -> bool:
    """Return whether an exception message indicates retryable API failure."""
    msg = str(exc).lower()
    retry_tokens = [
        "429",
        "rate",
        "quota",
        "unauthorized",
        "forbidden",
        "failed_precondition",
        "location is not supported",
        "api key",
    ]
    return any(tok in msg for tok in retry_tokens)


def _client_pool() -> list[genai.Client]:
    """Create a client per configured Gemini API key."""
    keys = load_gemini_api_keys()
    return [genai.Client(api_key=key) for key in keys]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for texts with key-rotation fallback."""
    clients = _client_pool()
    last_error: Exception | None = None

    for i, client in enumerate(clients, start=1):
        try:
            vectors: list[list[float]] = []
            for text in texts:
                resp = client.models.embed_content(
                    model=settings.gemini_model_embedding,
                    contents=text,
                )
                emb_list = getattr(resp, "embeddings", None)
                if not emb_list:
                    raise RuntimeError("Gemini embedding response had no vectors")
                vectors.append(list(emb_list[0].values))
            logger.debug("Embedding generation succeeded", extra={"client_index": i, "count": len(texts)})
            return vectors
        except Exception as exc:
            last_error = exc
            logger.warning("Embedding generation failed", extra={"client_index": i, "error": str(exc)})
            if not _is_retryable_gemini_error(exc):
                raise
            continue

    raise RuntimeError(f"All Gemini keys failed for embeddings: {last_error}")


def _strip_code_fence(s: str) -> str:
    """Strip markdown code fences from model output."""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s.strip()


def generate_readonly_cypher(question: str) -> str:
    """Generate a read-only Cypher query for a natural-language question."""
    schema = (
        "Nodes: Page(id,title,url,summary), Chunk(id,text,sequence_number,embedding), "
        "Entity(id,name,type). Relationships: (Page)-[:HAS_CHUNK]->(Chunk), "
        "(Chunk)-[:MENTIONS]->(Entity)."
    )
    prompt = f"""
You are a Neo4j Cypher generator.
Generate ONE read-only Cypher query for this question: {question}

Schema: {schema}

Strict rules:
- Read-only only. No CREATE, MERGE, DELETE, SET, DROP, CALL dbms/procedures writes.
- Return fields exactly as: page_title, page_url, chunk_id, chunk_text, score.
- Use MATCH/WHERE with safe logic.
- LIMIT 8 max.
- Return ONLY JSON object: {{"cypher":"..."}}
""".strip()

    clients = _client_pool()
    last_error: Exception | None = None

    for i, client in enumerate(clients, start=1):
        try:
            resp = client.models.generate_content(
                model=resolve_cypher_model(),
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=512,
                    response_mime_type="application/json",
                ),
            )
            text = _strip_code_fence(resp.text or "")
            parsed = json.loads(text)
            cypher = str(parsed.get("cypher", "")).strip()
            if not cypher:
                raise RuntimeError("Gemini returned empty Cypher")
            if "$top_k" not in cypher and "limit" not in cypher.lower():
                cypher = f"{cypher.rstrip(';')} LIMIT $top_k"
            logger.debug("Cypher generation succeeded", extra={"client_index": i})
            return cypher
        except Exception as exc:
            last_error = exc
            logger.warning("Cypher generation failed", extra={"client_index": i, "error": str(exc)})
            if not _is_retryable_gemini_error(exc):
                raise
            continue

    raise RuntimeError(f"All Gemini keys failed for cypher generation: {last_error}")


def assert_readonly_cypher(cypher: str) -> None:
    """Validate that generated Cypher is read-only and shape-compatible."""
    raw = (cypher or "").strip()
    if not raw:
        raise RuntimeError("Generated Cypher is empty")

    trimmed = raw[:-1] if raw.endswith(";") else raw
    if ";" in trimmed:
        raise RuntimeError("Generated Cypher contains multiple statements")

    lowered = re.sub(r"\s+", " ", raw.lower())
    blocked = [
        " create ",
        " merge ",
        " delete ",
        " detach ",
        " set ",
        " remove ",
        " drop ",
        " load csv",
        " apoc.periodic",
        " call dbms",
    ]
    padded = f" {lowered} "
    if any(token in padded for token in blocked):
        raise RuntimeError("Generated Cypher is not read-only")

    required_aliases = ["page_title", "page_url", "chunk_id", "chunk_text", "score"]
    for alias in required_aliases:
        if re.search(rf"\bas\s+{re.escape(alias)}\b", lowered) is None:
            raise RuntimeError(f"Generated Cypher missing required alias: {alias}")
