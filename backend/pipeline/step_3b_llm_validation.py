"""Step 3b: placeholder for additional LLM based validations."""
from utils import StepLogger


def validate_reviews() -> None:
    """Run extra validation steps on parsed reviews using LLMs."""
    step_logger = StepLogger("step_3b_llm_validation")
    step_logger.logger.info("LLM validation not yet implemented")
    step_logger.finalize()
