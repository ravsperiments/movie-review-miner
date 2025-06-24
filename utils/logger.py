"""Simple helper for creating consistent loggers across modules."""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured to output nicely formatted messages."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Stream logs to stdout so they appear in the console
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger
