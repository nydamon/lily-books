"""Fail-fast validation utilities."""

import logging
import functools
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Feature flag for fail-fast validation
FAIL_FAST_ENABLED = False


def check_gpt5_mini_response(response: Any) -> None:
    """Check GPT-5 mini response for quality issues.

    Args:
        response: The LLM response to validate

    Raises:
        ValueError: If response fails validation and FAIL_FAST_ENABLED is True
    """
    if not FAIL_FAST_ENABLED:
        return

    # Add validation logic here if needed
    if not response:
        logger.warning("Empty response from GPT-5 mini")
        raise ValueError("Empty response from LLM")


def check_llm_response(response: Any) -> None:
    """Check LLM response for quality issues.

    Args:
        response: The LLM response to validate

    Raises:
        ValueError: If response fails validation and FAIL_FAST_ENABLED is True
    """
    if not FAIL_FAST_ENABLED:
        return

    # Add validation logic here if needed
    if not response:
        logger.warning("Empty response from LLM")
        raise ValueError("Empty response from LLM")


def fail_fast_on_exception(func: Callable) -> Callable:
    """Decorator to fail fast on exceptions.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function that fails fast if FAIL_FAST_ENABLED
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if FAIL_FAST_ENABLED:
                logger.error(f"Fail-fast enabled, stopping on error: {e}")
                raise
            else:
                logger.warning(f"Error occurred (fail-fast disabled): {e}")
                return None
    return wrapper
