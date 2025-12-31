"""
Centralized logging configuration for the movie review miner crawler.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .log_id import get_log_id

# Log format constants
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_FORMAT_WITH_ID = "%(asctime)s | %(levelname)s | [%(log_id)s] | %(name)s | %(message)s"
CONSOLE_FORMAT = "%(asctime)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Track if pipeline logging has been configured
_pipeline_logging_configured = False

# Loggers allowed to print to console (stage progress only)
CONSOLE_LOGGERS = {"__main__", "crawler.run_pipeline"}


class LogIdFilter(logging.Filter):
    """Filter that adds log_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.log_id = get_log_id() or "--------"
        return True


class ConsoleFilter(logging.Filter):
    """Filter that only allows main pipeline logs to console."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Only main pipeline orchestrator logs
        if record.name in CONSOLE_LOGGERS:
            return True
        # Errors always shown
        if record.levelno >= logging.ERROR:
            return True
        return False


def get_logger(name: str, level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Configure and return a logger with standardized formatting.

    Args:
        name: Name of the logger (typically __name__)
        level: Logging level (default: INFO)
        log_file: Optional log file path. If None, relies on root logger handlers.

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # If pipeline logging is configured, don't add handlers - use root logger's handlers
    if _pipeline_logging_configured:
        return logger

    # Avoid adding multiple handlers to the same logger
    if logger.handlers:
        return logger

    # Only add handlers if not using pipeline logging
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def setup_pipeline_logging(log_dir: str = "review_aggregator/logs") -> None:
    """
    Set up logging configuration for the entire pipeline.

    Console: Shows only stage progress and errors (clean output)
    File: Full detailed logs with log_id for debugging

    Args:
        log_dir: Directory to store log files
    """
    global _pipeline_logging_configured
    if _pipeline_logging_configured:
        return

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Console: clean format, filtered to stage progress only
    console_formatter = logging.Formatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(ConsoleFilter())

    # File: detailed format with log_id for debugging
    file_formatter = logging.Formatter(LOG_FORMAT_WITH_ID, datefmt=DATE_FORMAT)
    file_handler = logging.FileHandler(log_path / "pipeline.log")
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(LogIdFilter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Clear handlers from any loggers that were configured before pipeline logging
    # This prevents duplicate log messages
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        if logger.handlers:
            logger.handlers.clear()

    _pipeline_logging_configured = True