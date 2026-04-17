from __future__ import annotations

import json
import re

from google import genai
from google.genai import types

from src.config import load_gemini_api_keys, settings


def _is_retryable_gemini_error(exc: Exception) -> bool:
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


def _client() -> genai.Client:
    return genai.Client(api_key=load_gemini_api_keys()[0])


def _client_pool() -> list[genai.Client]:
    return [genai.Client(api_key=key) for key in load_gemini_api_keys()]


def embed_texts(texts: list[str]) -> list[list[float]]:
    clients = _client_pool()
    last_error: Exception | None = None

    for client in clients:
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
            return vectors
        except Exception as exc:
            last_error = exc
            if not _is_retryable_gemini_error(exc):
                raise
            continue

    raise RuntimeError(f"All Gemini keys failed for embeddings: {last_error}")


def _strip_code_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s.strip()


def generate_readonly_cypher(question: str) -> str:
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

    for client in clients:
        try:
            resp = client.models.generate_content(
                model=settings.gemini_model_text,
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
            # Ensure the runtime top_k parameter can always be applied.
            if "$top_k" not in cypher and "limit" not in cypher.lower():
                cypher = f"{cypher.rstrip(';')} LIMIT $top_k"
            return cypher
        except Exception as exc:
            last_error = exc
            if not _is_retryable_gemini_error(exc):
                raise
            continue

    raise RuntimeError(f"All Gemini keys failed for cypher generation: {last_error}")


def assert_readonly_cypher(cypher: str) -> None:
    raw = (cypher or "").strip()
    if not raw:
        raise RuntimeError("Generated Cypher is empty")

    # Block multi-statement payloads. A single optional trailing semicolon is allowed.
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

    # Enforce stable output aliases expected by the query pipeline.
    required_aliases = ["page_title", "page_url", "chunk_id", "chunk_text", "score"]
    for alias in required_aliases:
        if re.search(rf"\bas\s+{re.escape(alias)}\b", lowered) is None:
            raise RuntimeError(f"Generated Cypher missing required alias: {alias}")
