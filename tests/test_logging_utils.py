from __future__ import annotations

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
