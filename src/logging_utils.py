"""Shared logging utilities for the service."""

from __future__ import annotations

import logging

_CONFIGURED = False


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
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)
