"""Ingestion pipelines for Wikipedia API and Hugging Face dataset."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Callable

import wikipedia
from datasets import load_dataset

from src.llm import embed_texts
from src.logging_utils import get_logger
from src.neo4j_client import neo4j_client


logger = get_logger(__name__)


@dataclass
class IngestResult:
    """Summary result of a single ingested page/document."""

    topic: str
    page_id: str
    title: str
    url: str
    chunk_count: int
    entity_count: int


def _upsert_page_from_text(
    page_id: str,
    title: str,
    url: str,
    text: str,
    summary: str,
) -> IngestResult:
    """Upsert one page, chunks, entities, and mention edges into Neo4j."""
    chunks = _chunk_text(text)
    entities = _extract_entities_simple(text)
    embeddings = embed_texts(chunks) if chunks else []

    neo4j_client.setup_schema()
    with neo4j_client.session() as session:
        session.run(
            """
            MERGE (p:Page {id: $id})
            SET p.title = $title,
                p.url = $url,
                p.summary = $summary
            """,
            id=page_id,
            title=title,
            url=url,
            summary=summary,
        )

        for idx, chunk in enumerate(chunks):
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{page_id}#chunk#{idx}"))
            embedding = embeddings[idx] if idx < len(embeddings) else []
            session.run(
                """
                MATCH (p:Page {id: $page_id})
                MERGE (c:Chunk {id: $chunk_id})
                SET c.text = $text,
                    c.sequence_number = $seq,
                    c.embedding = $embedding
                MERGE (p)-[:HAS_CHUNK]->(c)
                """,
                page_id=page_id,
                chunk_id=chunk_id,
                text=chunk,
                seq=idx,
                embedding=embedding,
            )

        for name in entities:
            entity_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, name.lower()))
            session.run(
                """
                MERGE (e:Entity {id: $entity_id})
                SET e.name = $name,
                    e.type = coalesce(e.type, 'Unknown')
                """,
                entity_id=entity_id,
                name=name,
            )
            session.run(
                """
                MATCH (p:Page {id: $page_id})-[:HAS_CHUNK]->(c:Chunk)
                WHERE toLower(c.text) CONTAINS toLower($name)
                MATCH (e:Entity {id: $entity_id})
                MERGE (c)-[:MENTIONS]->(e)
                """,
                page_id=page_id,
                entity_id=entity_id,
                name=name,
            )

    logger.info(
        "Page upserted",
        extra={"page_id": page_id, "title": title, "chunks": len(chunks), "entities": len(entities)},
    )

    return IngestResult(
        topic=title,
        page_id=page_id,
        title=title,
        url=url,
        chunk_count=len(chunks),
        entity_count=len(entities),
    )


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """Split text into overlapping chunks for retrieval and embedding."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    i = 0
    n = len(cleaned)
    while i < n:
        j = min(i + chunk_size, n)
        chunks.append(cleaned[i:j])
        if j == n:
            break
        i = max(j - overlap, i + 1)
    return chunks


def _extract_entities_simple(text: str, max_entities: int = 25) -> list[str]:
    """Extract simple title-cased entities using regex heuristic."""
    candidates = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)
    deduped: list[str] = []
    seen = set()
    for c in candidates:
        key = c.strip().lower()
        if len(c) < 3 or key in seen:
            continue
        seen.add(key)
        deduped.append(c.strip())
        if len(deduped) >= max_entities:
            break
    return deduped


def ingest_topic(topic: str) -> IngestResult:
    """Ingest one topic from Wikipedia API into graph."""
    page = wikipedia.page(topic, auto_suggest=False)
    page_id = str(uuid.uuid5(uuid.NAMESPACE_URL, page.url))
    summary = wikipedia.summary(topic, auto_suggest=False, sentences=3)
    chunks = _chunk_text(page.content)
    entities = _extract_entities_simple(page.content)
    embeddings = embed_texts(chunks) if chunks else []
    linked_titles = page.links[:50]

    neo4j_client.setup_schema()

    with neo4j_client.session() as session:
        session.run(
            """
            MERGE (p:Page {id: $id})
            SET p.title = $title,
                p.url = $url,
                p.summary = $summary
            """,
            id=page_id,
            title=page.title,
            url=page.url,
            summary=summary,
        )

        for idx, chunk in enumerate(chunks):
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{page_id}#chunk#{idx}"))
            embedding = embeddings[idx] if idx < len(embeddings) else []
            session.run(
                """
                MATCH (p:Page {id: $page_id})
                MERGE (c:Chunk {id: $chunk_id})
                SET c.text = $text,
                    c.sequence_number = $seq,
                    c.embedding = $embedding
                MERGE (p)-[:HAS_CHUNK]->(c)
                """,
                page_id=page_id,
                chunk_id=chunk_id,
                text=chunk,
                seq=idx,
                embedding=embedding,
            )

        for name in entities:
            entity_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, name.lower()))
            session.run(
                """
                MERGE (e:Entity {id: $entity_id})
                SET e.name = $name,
                    e.type = coalesce(e.type, 'Unknown')
                """,
                entity_id=entity_id,
                name=name,
            )
            session.run(
                """
                MATCH (p:Page {id: $page_id})-[:HAS_CHUNK]->(c:Chunk)
                WHERE toLower(c.text) CONTAINS toLower($name)
                MATCH (e:Entity {id: $entity_id})
                MERGE (c)-[:MENTIONS]->(e)
                """,
                page_id=page_id,
                entity_id=entity_id,
                name=name,
            )

        for linked_title in linked_titles:
            linked_url = f"https://en.wikipedia.org/wiki/{linked_title.replace(' ', '_')}"
            linked_page_id = str(uuid.uuid5(uuid.NAMESPACE_URL, linked_url))
            session.run(
                """
                MATCH (p:Page {id: $source_id})
                MERGE (t:Page {id: $target_id})
                ON CREATE SET t.title = $target_title,
                              t.url = $target_url,
                              t.summary = coalesce(t.summary, '')
                MERGE (p)-[:LINKS_TO]->(t)
                """,
                source_id=page_id,
                target_id=linked_page_id,
                target_title=linked_title,
                target_url=linked_url,
            )

    logger.info("Wikipedia topic ingested", extra={"topic": topic, "page_id": page_id})

    return IngestResult(
        topic=topic,
        page_id=page_id,
        title=page.title,
        url=page.url,
        chunk_count=len(chunks),
        entity_count=len(entities),
    )


def ingest_from_hf(
    config_name: str = "20231101.en",
    split: str = "train",
    sample_size: int = 5,
    streaming: bool = True,
    on_progress: Callable[[int, int | None, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[IngestResult]:
    """Ingest sample records from `wikimedia/wikipedia` Hugging Face dataset."""
    results: list[IngestResult] = []
    total: int | None = sample_size if streaming else None

    if streaming:
        iterable = load_dataset("wikimedia/wikipedia", config_name, split=split, streaming=True)
    else:
        ds = load_dataset("wikimedia/wikipedia", config_name, split=split)
        total = min(sample_size, len(ds))
        iterable = ds.select(range(total))

    processed = 0

    for idx, raw_row in enumerate(iterable):
        if should_stop and should_stop():
            logger.info("HF ingestion stop requested", extra={"processed": processed})
            break
        if streaming and idx >= sample_size:
            break

        try:
            row = raw_row if isinstance(raw_row, dict) else dict(raw_row)
            page_id = str(row.get("id", ""))
            title = str(row.get("title", "")).strip() or f"untitled-{uuid.uuid4()}"
            url = str(row.get("url", "")).strip() or f"https://example.org/{title.replace(' ', '_')}"
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            summary = text[:400]
            if not page_id:
                page_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
            result = _upsert_page_from_text(
                page_id=page_id,
                title=title,
                url=url,
                text=text,
                summary=summary,
            )
        except Exception as exc:
            logger.warning("Skipping malformed HF row", extra={"index": idx, "error": str(exc)})
            continue

        results.append(result)
        processed += 1
        if on_progress:
            on_progress(processed, total, result.title)

    logger.info("HF ingestion completed", extra={"processed": processed, "requested": sample_size})
    return results
