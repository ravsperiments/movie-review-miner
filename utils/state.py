import json
from typing import Dict

STATE_FILE = "state.json"


def load_state() -> Dict[str, int]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"page": 1, "index": 0}


def save_state(state: Dict[str, int]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

