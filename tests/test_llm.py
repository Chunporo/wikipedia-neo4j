import pytest

from src.llm import assert_readonly_cypher


def test_assert_readonly_cypher_accepts_valid_aliases() -> None:
    cypher = """
    MATCH (p:Page)-[:HAS_CHUNK]->(c:Chunk)
    RETURN p.title AS page_title,
           p.url AS page_url,
           c.id AS chunk_id,
           c.text AS chunk_text,
           1.0 AS score
    LIMIT $top_k
    """
    assert_readonly_cypher(cypher)


@pytest.mark.parametrize(
    "cypher, expected_msg",
    [
        ("", "empty"),
        (
            "MATCH (p:Page) RETURN p.title AS page_title; MATCH (n) RETURN n",
            "multiple statements",
        ),
        (
            "MATCH (p:Page)-[:HAS_CHUNK]->(c:Chunk) "
            "RETURN p.title AS page_title, p.url AS page_url, c.id AS chunk_id, 1.0 AS score",
            "missing required alias",
        ),
        (
            "MATCH (p:Page) DELETE p RETURN '' AS page_title, '' AS page_url, '' AS chunk_id, '' AS chunk_text, 0 AS score",
            "not read-only",
        ),
    ],
)
def test_assert_readonly_cypher_rejects_invalid_input(cypher: str, expected_msg: str) -> None:
    with pytest.raises(RuntimeError, match=expected_msg):
        assert_readonly_cypher(cypher)
