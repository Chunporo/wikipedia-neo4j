"""Graph retrieval and deterministic answer assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import LiteralString, TypedDict, cast

from src.llm import assert_readonly_cypher, generate_readonly_cypher
from src.logging_utils import get_logger
from src.neo4j_client import neo4j_client


logger = get_logger(__name__)


@dataclass
class QueryResult:
    """Query response model used by API layer."""

    answer: str
    citations: list["CitationRow"]
    strategy: str
    strategy_used: str
    fallback_reason: str | None = None


class CitationRow(TypedDict):
    """Normalized citation row returned to API clients."""

    page_title: str | None
    page_url: str | None
    chunk_id: str | None
    snippet: str
    score: float


def _score_row(row: dict[str, object]) -> float:
    """Normalize score field for sorting and display."""
    score_value = row.get("score")
    if isinstance(score_value, (int, float)):
        return float(score_value)
    if isinstance(score_value, str):
        try:
            return float(score_value)
        except ValueError:
            return 0.0
    return 0.0


def _dedupe_rows(rows: list[dict[str, object]], top_k: int) -> list[dict[str, object]]:
    """Dedupe rows by chunk_id while keeping highest score per chunk."""
    by_chunk: dict[str, dict[str, object]] = {}
    for row in rows:
        chunk_id = row.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            continue
        score = _score_row(row)
        existing = by_chunk.get(chunk_id)
        if not existing or score > _score_row(existing):
            by_chunk[chunk_id] = row
    ranked = sorted(by_chunk.values(), key=_score_row, reverse=True)
    return ranked[: max(1, top_k)]


_HYBRID_FALLBACK_CYPHER = """
CALL {
  CALL db.index.fulltext.queryNodes('chunk_text_ft', $q) YIELD node, score
  MATCH (p:Page)-[:HAS_CHUNK]->(node)
  RETURN p.title AS page_title,
         p.url AS page_url,
         node.id AS chunk_id,
         node.text AS chunk_text,
         score * 1.0 AS score
  LIMIT $top_k

  UNION

  CALL db.index.fulltext.queryNodes('page_title_ft', $q) YIELD node, score
  MATCH (node:Page)-[:HAS_CHUNK]->(c:Chunk)
  RETURN node.title AS page_title,
         node.url AS page_url,
         c.id AS chunk_id,
         c.text AS chunk_text,
         score * 0.8 AS score
  LIMIT $top_k
}
WITH page_title, page_url, chunk_id, chunk_text, max(score) AS score
RETURN page_title, page_url, chunk_id, chunk_text, score
ORDER BY score DESC
LIMIT $top_k
"""


def _run_fallback_query(question: str, top_k: int) -> list[dict[str, object]]:
    """Execute safe fallback query when LLM-generated Cypher fails."""
    with neo4j_client.session() as session:
        records = session.run(
            cast(LiteralString, _HYBRID_FALLBACK_CYPHER),
            q=question,
            top_k=top_k,
        )
        rows: list[dict[str, object]] = [dict(r) for r in records]
    logger.info("Fallback retrieval executed", extra={"rows": len(rows)})
    return rows


def _run_generated_query(question: str, top_k: int) -> list[dict[str, object]]:
    """Generate, validate, and execute LLM-produced read-only Cypher."""
    cypher = generate_readonly_cypher(question)
    assert_readonly_cypher(cypher)

    with neo4j_client.session() as session:
        records = session.run(cast(LiteralString, cypher), q=question, top_k=top_k)
        rows: list[dict[str, object]] = [dict(r) for r in records]

    required_keys = {"page_title", "page_url", "chunk_id", "chunk_text", "score"}
    for row in rows:
        if not required_keys.issubset(row):
            raise RuntimeError("Generated query returned unexpected shape")

    logger.info("Generated retrieval executed", extra={"rows": len(rows)})
    return rows


def query_graph(question: str, top_k: int = 4) -> QueryResult:
    """Query graph and synthesize a deterministic answer with citations."""
    try:
        rows = _run_generated_query(question, top_k)
        strategy = "generated_readonly_cypher"
        fallback_reason = None
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        logger.warning("Generated query failed; falling back", extra={"error": str(exc)})
        rows = _run_fallback_query(question, top_k)
        strategy = "hybrid_fulltext"
        fallback_reason = str(exc)

    rows = _dedupe_rows(rows, top_k)
    if not rows:
        return QueryResult(
            answer="I could not find relevant context in the graph yet. Try ingesting more topics.",
            citations=[],
            strategy=strategy,
            strategy_used=strategy,
            fallback_reason=fallback_reason,
        )

    citations: list[CitationRow] = []
    snippets: list[str] = []
    for r in rows:
        chunk_text = r.get("chunk_text")
        txt = str(chunk_text or "").strip().replace("\n", " ")
        snippet = txt[:220]
        snippets.append(snippet)
        citations.append(
            {
                "page_title": cast(str | None, r.get("page_title")),
                "page_url": cast(str | None, r.get("page_url")),
                "chunk_id": cast(str | None, r.get("chunk_id")),
                "snippet": snippet,
                "score": _score_row(r),
            }
        )

    answer = "Deterministic demo answer from retrieved graph context: " + " | ".join(snippets[:2])

    return QueryResult(
        answer=answer,
        citations=citations,
        strategy=strategy,
        strategy_used=strategy,
        fallback_reason=fallback_reason,
    )
