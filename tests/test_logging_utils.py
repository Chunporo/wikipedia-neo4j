from __future__ import annotations

import json
import logging

import src.logging_utils as lu


def test_request_context_filter_injects_request_id() -> None:
    filt = lu.RequestContextFilter()
    token = lu.set_request_id("rid-123")
    try:
        record = logging.LogRecord(
            name="x",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        assert filt.filter(record) is True
        assert getattr(record, "request_id") == "rid-123"
    finally:
        lu.reset_request_id(token)


def test_set_and_reset_request_id_roundtrip() -> None:
    t1 = lu.set_request_id("rid-a")
    try:
        assert lu._REQUEST_ID.get() == "rid-a"
    finally:
        lu.reset_request_id(t1)

    assert lu._REQUEST_ID.get() == "-"


def test_json_formatter_emits_json_payload() -> None:
    formatter = lu.JsonFormatter()
    record = logging.LogRecord(
        name="svc",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    record.request_id = "rid-88"
    record.duration_ms = 15
    payload = json.loads(formatter.format(record))

    assert payload["logger"] == "svc"
    assert payload["request_id"] == "rid-88"
    assert payload["message"] == "hello world"
    assert payload["duration_ms"] == 15
