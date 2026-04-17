from __future__ import annotations

from contextlib import contextmanager

from neo4j import GraphDatabase

from src.config import settings


class Neo4jClient:
    def __init__(self) -> None:
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )

    def close(self) -> None:
        self.driver.close()

    def verify_connectivity(self) -> None:
        self.driver.verify_connectivity()

    @contextmanager
    def session(self):
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def setup_schema(self) -> None:
        with self.session() as session:
            session.run(
                "CREATE CONSTRAINT page_id IF NOT EXISTS FOR (p:Page) REQUIRE p.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE"
            )
            session.run(
                "CREATE FULLTEXT INDEX page_title_ft IF NOT EXISTS FOR (p:Page) ON EACH [p.title, p.summary]"
            )
            session.run(
                "CREATE FULLTEXT INDEX chunk_text_ft IF NOT EXISTS FOR (c:Chunk) ON EACH [c.text]"
            )
            session.run("CREATE INDEX page_title_idx IF NOT EXISTS FOR (p:Page) ON (p.title)")
            session.run("CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name)")


neo4j_client = Neo4jClient()
