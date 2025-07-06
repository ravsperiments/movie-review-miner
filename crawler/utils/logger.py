"""Shared logging utilities."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

_INITIALISED = False


def _initialise() -> None:
    """Configure the root logger on first use."""
    global _INITIALISED
    if _INITIALISED:
        return

    log_dir = Path("crawler/logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    log_file = log_dir / f"{timestamp}.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    _INITIALISED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-specific logger with shared configuration."""
    if not _INITIALISED:
        _initialise()
    return logging.getLogger(name)
