"""Shared logging utilities for the service."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from datetime import datetime, timezone

_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_CONFIGURED = False


class RequestContextFilter(logging.Filter):
    """Inject request context fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach request id to record and allow emission."""
        record.request_id = _REQUEST_ID.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render log records as one-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize logging record as JSON."""
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }

        for key in ("duration_ms", "count", "topic", "job_id", "status", "error"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def set_request_id(request_id: str) -> Token[str]:
    """Set request id in logging context and return reset token."""
    return _REQUEST_ID.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    """Restore prior request id context with provided token."""
    _REQUEST_ID.reset(token)


def configure_logging(level_name: str = "INFO", json_logs: bool = False) -> None:
    """Configure process-wide logging once.

    Args:
        level_name: Logging level name (for example ``INFO`` or ``DEBUG``).
        json_logs: When true, emit one-line JSON log records.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level)

    formatter: logging.Formatter
    if json_logs:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s"
        )

    context_filter = RequestContextFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
        handler.addFilter(context_filter)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)
