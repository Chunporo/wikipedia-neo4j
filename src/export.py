"""Graph export utilities for JSONL and CSV formats."""

from __future__ import annotations

import csv
import json
from collections.abc import Generator, Iterable
from io import StringIO
from typing import LiteralString

from src.neo4j_client import neo4j_client


def _iter_records(query: LiteralString) -> Iterable[dict[str, object]]:
    with neo4j_client.session() as session:
        records = session.run(query)
        for record in records:
            yield dict(record)


def _stream_jsonl(records: Iterable[dict[str, object]]) -> Generator[bytes, None, None]:
    for record in records:
        yield (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")


def export_jsonl() -> Generator[bytes, None, None]:
    """Stream graph export as JSON Lines bytes."""
    yield from _stream_jsonl(
        _iter_records(
            """
            MATCH (p:Page)
            RETURN 'Page' AS label,
                   p.id AS id,
                   p.title AS title,
                   p.url AS url,
                   p.summary AS summary
            UNION ALL
            MATCH (c:Chunk)
            RETURN 'Chunk' AS label,
                   c.id AS id,
                   c.text AS text,
                   c.sequence_number AS sequence_number,
                   c.embedding AS embedding
            UNION ALL
            MATCH (e:Entity)
            RETURN 'Entity' AS label,
                   e.id AS id,
                   e.name AS name,
                   e.type AS type
            UNION ALL
            MATCH (p:Page)-[:HAS_CHUNK]->(c:Chunk)
            RETURN 'HAS_CHUNK' AS rel_type,
                   p.id AS source,
                   c.id AS target
            UNION ALL
            MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
            RETURN 'MENTIONS' AS rel_type,
                   c.id AS source,
                   e.id AS target
            UNION ALL
            MATCH (p:Page)-[:LINKS_TO]->(t:Page)
            RETURN 'LINKS_TO' AS rel_type,
                   p.id AS source,
                   t.id AS target
            """
        )
    )


def export_csv() -> Generator[bytes, None, None]:
    """Stream graph export as CSV bytes with a type column."""
    headers = ["kind", "label", "rel_type", "id", "source", "target", "props"]
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    yield buffer.getvalue().encode("utf-8")
    _ = buffer.seek(0)
    _ = buffer.truncate(0)

    def _write_rows(rows: Iterable[dict[str, object]], kind: str) -> Generator[bytes, None, None]:
        for row in rows:
            label = row.get("label")
            rel_type = row.get("rel_type")
            entity_id = row.get("id")
            source = row.get("source")
            target = row.get("target")
            props = {
                k: v
                for k, v in row.items()
                if k not in {"label", "rel_type", "id", "source", "target"}
            }
            writer.writerow(
                [kind, label or "", rel_type or "", entity_id or "", source or "", target or "", json.dumps(props, ensure_ascii=False)]
            )
            yield buffer.getvalue().encode("utf-8")
            _ = buffer.seek(0)
            _ = buffer.truncate(0)

    nodes = _iter_records(
        """
        MATCH (p:Page)
        RETURN 'Page' AS label,
               p.id AS id,
               p.title AS title,
               p.url AS url,
               p.summary AS summary
        UNION ALL
        MATCH (c:Chunk)
        RETURN 'Chunk' AS label,
               c.id AS id,
               c.text AS text,
               c.sequence_number AS sequence_number,
               c.embedding AS embedding
        UNION ALL
        MATCH (e:Entity)
        RETURN 'Entity' AS label,
               e.id AS id,
               e.name AS name,
               e.type AS type
        """
    )
    relationships = _iter_records(
        """
        MATCH (p:Page)-[:HAS_CHUNK]->(c:Chunk)
        RETURN 'HAS_CHUNK' AS rel_type,
               p.id AS source,
               c.id AS target
        UNION ALL
        MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
        RETURN 'MENTIONS' AS rel_type,
               c.id AS source,
               e.id AS target
        UNION ALL
        MATCH (p:Page)-[:LINKS_TO]->(t:Page)
        RETURN 'LINKS_TO' AS rel_type,
               p.id AS source,
               t.id AS target
        """
    )

    yield from _write_rows(nodes, "node")
    yield from _write_rows(relationships, "relationship")
