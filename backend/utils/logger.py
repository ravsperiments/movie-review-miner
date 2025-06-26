"""Shared logging utilities."""

from __future__ import annotations

import logging
import json
from datetime import datetime
from pathlib import Path

_INITIALISED = False


def _initialise() -> None:
    """Configure the root logger on first use."""
    global _INITIALISED
    if _INITIALISED:
        return

    log_dir = Path("logs")
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


class StepLogger:
    """Utility to log step progress and write a pipeline summary."""

    def __init__(self, step_name: str, log_dir: str = "logs") -> None:
        self.step_name = step_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.logger = get_logger(step_name)

        self._handler = logging.FileHandler(self.log_dir / f"step_{step_name}.log")
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        self._handler.setFormatter(fmt)
        self.logger.addHandler(self._handler)

        self.input_count = 0
        self.processed_count = 0
        self.saved_count = 0
        self.failed_count = 0
        self.notes: list[str] = []

    def set_input_count(self, count: int) -> None:
        self.input_count = count

    def processed(self, n: int = 1) -> None:
        self.processed_count += n

    def saved(self, n: int = 1) -> None:
        self.saved_count += n

    def failed(self, n: int = 1) -> None:
        self.failed_count += n

    def note(self, message: str) -> None:
        self.notes.append(message)
        self.logger.info(message)

    def finalize(self) -> None:
        """Write summary metrics and close the step log file."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "step": self.step_name,
            "input": self.input_count,
            "processed": self.processed_count,
            "saved": self.saved_count,
            "failed": self.failed_count,
            "notes": "; ".join(self.notes),
        }
        self.logger.info(
            "Summary - input=%s processed=%s saved=%s failed=%s notes=%s",
            self.input_count,
            self.processed_count,
            self.saved_count,
            self.failed_count,
            "; ".join(self.notes),
        )
        summary_file = self.log_dir / "pipeline_summary.json"
        if summary_file.exists():
            with open(summary_file, "r+", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = []
                if not isinstance(data, list):
                    data = [data]
                data.append(summary)
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
        else:
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump([summary], f, indent=2)

        self._handler.flush()
        self.logger.removeHandler(self._handler)
        self._handler.close()
