"""File I/O helper utilities."""

from datetime import datetime
from pathlib import Path

# Directory to store failure logs
FAILURES_DIR = Path("failures")
FAILURES_DIR.mkdir(parents=True, exist_ok=True)

# Timestamp used in failure filenames for the current run
RUN_TIME = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def write_failure(path: str, item: str, error: Exception | str) -> None:
    """Append a failed item to a timestamped file under ``FAILURES_DIR``."""
    original = Path(path)
    filename = f"{original.stem}_{RUN_TIME}{original.suffix}"
    failure_path = FAILURES_DIR / filename
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    with open(failure_path, "a", encoding="utf-8") as f:
        f.write(f"{item} | {error}\n")

