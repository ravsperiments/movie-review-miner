"""Utility functions to persist crawler progress between runs."""

import json
from typing import Dict

from utils.logger import get_logger

# JSON file on disk used to store progress information
STATE_FILE = "state.json"

logger = get_logger(__name__)


def load_state() -> Dict[str, int]:
    """Read the current crawl position from disk."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            logger.debug("Loaded state: %s", state)
            return state
    except FileNotFoundError:
        default = {"page": 1, "index": 0}
        logger.debug("State file not found, using default: %s", default)
        return default


def save_state(state: Dict[str, int]) -> None:
    """Persist the given crawl position to disk."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    logger.debug("Saved state: %s", state)

