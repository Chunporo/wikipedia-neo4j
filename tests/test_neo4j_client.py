from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import src.neo4j_client as n4


class _FakeDriver:
    def __init__(self) -> None:
        self.closed = False
        self.verified = False

    def close(self) -> None:
        self.closed = True

    def verify_connectivity(self) -> None:
        self.verified = True

    @contextmanager
    def session(self) -> Iterator["_FakeSession"]:
        yield _FakeSession()


class _FakeSession:
    def __init__(self) -> None:
        self.runs: list[str] = []

    def run(self, query: str):
        self.runs.append(query)


def test_close_calls_driver_close() -> None:
    client = n4.Neo4jClient.__new__(n4.Neo4jClient)
    client.driver = _FakeDriver()

    client.close()

    assert client.driver.closed is True


def test_verify_connectivity_calls_driver() -> None:
    client = n4.Neo4jClient.__new__(n4.Neo4jClient)
    client.driver = _FakeDriver()

    client.verify_connectivity()

    assert client.driver.verified is True
