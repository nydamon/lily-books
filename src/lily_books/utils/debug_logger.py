"""Debug logging utilities for pipeline monitoring."""

import logging
import functools
from typing import Any, Callable

logger = logging.getLogger(__name__)


def log_step(step_name: str, **kwargs):
    """Log a pipeline step with context."""
    logger.debug(f"Step: {step_name} - {kwargs}")


def update_activity(message: str):
    """Update activity status."""
    logger.debug(f"Activity: {message}")


def log_api_call(api_name: str, **kwargs):
    """Log an API call with context."""
    logger.debug(f"API Call: {api_name} - {kwargs}")


def check_for_hang():
    """Check for hanging operations."""
    pass


def debug_function(func: Callable) -> Callable:
    """Decorator to debug synchronous functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling function: {func.__name__}")
        result = func(*args, **kwargs)
        logger.debug(f"Completed function: {func.__name__}")
        return result
    return wrapper


def debug_async_function(func: Callable) -> Callable:
    """Decorator to debug async functions."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger.debug(f"Calling async function: {func.__name__}")
        result = await func(*args, **kwargs)
        logger.debug(f"Completed async function: {func.__name__}")
        return result
    return wrapper
