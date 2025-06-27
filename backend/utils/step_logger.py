import json
import logging
from pathlib import Path
from utils.logger import get_logger

class StepLogger:
    """Helper to log per-step metrics and summary."""

    def __init__(self, step_name: str) -> None:
        self.step_name = step_name
        self.logger = get_logger(step_name)
        self.metrics = {
            "step": step_name,
            "input_count": 0,
            "processed_count": 0,
            "saved_count": 0,
            "failed_count": 0,
            "notes": [],
        }
        step_log = Path("logs") / f"{step_name}.log"
        step_log.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(step_log)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self._handler = handler

    def add_note(self, note: str) -> None:
        self.metrics["notes"].append(note)

    def finalize(self) -> None:
        """Append metrics to the pipeline summary file and close handler."""
        summary_path = Path("logs") / "pipeline_summary.json"
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        data.append(self.metrics)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.logger.removeHandler(self._handler)
        self._handler.close()
