"""Simple helper for creating consistent loggers across modules."""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with basic settings."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger(name)
