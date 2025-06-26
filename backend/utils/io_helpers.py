"""File I/O helper utilities."""

from pathlib import Path


def write_failure(path: str, item: str, error: Exception | str) -> None:
    """Append a failed item to the given file for later retry."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{item} | {error}\n")

