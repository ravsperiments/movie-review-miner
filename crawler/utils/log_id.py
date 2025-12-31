"""Log ID generation for pipeline run tracking."""
import uuid
from contextvars import ContextVar

# Context variable for pipeline-run-scoped log ID
_log_id: ContextVar[str] = ContextVar("log_id", default="")


def generate_log_id() -> str:
    """Generate short 8-char log ID for error tracking."""
    return uuid.uuid4().hex[:8]


def set_log_id(log_id: str) -> None:
    """Set the log ID for the current context."""
    _log_id.set(log_id)


def get_log_id() -> str:
    """Get the log ID for the current context."""
    return _log_id.get()
