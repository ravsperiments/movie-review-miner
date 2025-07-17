import json
import logging
from pathlib import Path
from ..db.pipeline_logger import log_step_result

class StepLogger:
    """Helper to log per-step metrics and summary.

    This class provides a standardized way to log metrics and progress for
    individual steps within the data pipeline. It creates a dedicated log file
    for each step and aggregates metrics into a central summary file.
    """

    def __init__(self, step_name: str) -> None:
        """
        Initializes the StepLogger for a given pipeline step.

        Args:
            step_name (str): The unique name of the pipeline step (e.g., "fetch_links").
        """
        self.step_name = step_name
        # Get a logger instance specific to this step, ensuring messages are
        # identifiable by the step they originate from.
        self.logger = get_logger(step_name)

        # Initialize a dictionary to store metrics for this step.
        # These metrics will be aggregated and saved in the pipeline summary.
        self.metrics = {
            "step": step_name,
            "input_count": 0,
            "processed_count": 0,
            "saved_count": 0,
            "failed_count": 0,
            "notes": [],
        }

        # Define the path for the step-specific log file.
        # Logs are stored in 'crawler/logs/' with a filename matching the step name.
        step_log = Path("crawler/logs") / f"{step_name}.log"

        # Ensure the directory for log files exists.
        step_log.parent.mkdir(parents=True, exist_ok=True)

        # Create a file handler for the step's log file.
        handler = logging.FileHandler(step_log)

        # Define the format for log messages.
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)

        # Add the file handler to the step's logger.
        self.logger.addHandler(handler)

        # Store the handler reference to remove it later during finalization.
        self._handler = handler

    def add_note(self, note: str) -> None:
        """
        Adds a descriptive note to the step's metrics.

        Notes can be used to record specific events, observations, or contextual
        information relevant to the execution of the step.

        Args:
            note (str): The note string to add.
        """
        self.metrics["notes"].append(note)

    def finalize(self) -> None:
        """
        Finalizes the step's logging by appending its metrics to the pipeline
        summary file and closing the associated log handler.

        This method should be called at the end of each pipeline step to ensure
        that all metrics are recorded and resources are properly released.
        """
        # Define the path for the central pipeline summary JSON file.
        summary_path = Path("crawler/logs") / "pipeline_summary.json"

        # Load existing summary data if the file exists, otherwise initialize an empty list.
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        # Append the current step's metrics to the summary data.
        data.append(self.metrics)

        # Write the updated summary data back to the JSON file.
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Attempt to log the step's result to the database via pipeline_logger.
        try:
            log_step_result(
                self.step_name,
                attempt_number=1, # Assuming first attempt for now; can be extended.
                status="success", # Assuming success; error handling would set this to "failed".
                result_data=self.metrics, # Store all collected metrics.
            )
        except Exception as e:  # noqa: BLE001
            # Log an error if logging to the database fails, but do not prevent finalization.
            self.logger.error("Failed to log step summary to database: %s", e)

        # Remove the file handler from the logger and close it to release the log file.
        self.logger.removeHandler(self._handler)
        self._handler.close()
