"""Shared logging utilities for the service."""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token

_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_CONFIGURED = False


class RequestContextFilter(logging.Filter):
    """Inject request context fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach request id to record and allow emission."""
        record.request_id = _REQUEST_ID.get()
        return True


def set_request_id(request_id: str) -> Token[str]:
    """Set request id in logging context and return reset token."""
    return _REQUEST_ID.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    """Restore prior request id context with provided token."""
    _REQUEST_ID.reset(token)


def configure_logging(level_name: str = "INFO") -> None:
    """Configure process-wide logging once.

    Args:
        level_name: Logging level name (for example ``INFO`` or ``DEBUG``).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s",
    )
    context_filter = RequestContextFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(context_filter)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)
