import asyncio
import random
from typing import Any, Callable, Iterable

from review_aggregator.utils.logger import get_logger

logger = get_logger(__name__)


async def run_with_retries(
    func: Callable[..., Any],
    args: Iterable[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """Run an async function with retries and exponential backoff."""

    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    attempt = 1
    delay = base_delay
    while True:
        try:
            return await func(*args, attempt=attempt, **kwargs)
        except Exception as err:
            logger.warning("Attempt %s failed: %s", attempt, err)
            if attempt >= max_retries:
                logger.error("Giving up after %s attempts", attempt)
                raise
            await asyncio.sleep(delay + random.random() * base_delay)
            attempt += 1
            delay *= 2
