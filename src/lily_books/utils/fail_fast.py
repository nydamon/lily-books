"""Fail-fast validation utilities."""

import logging
import functools
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)

# Feature flag for fail-fast validation
FAIL_FAST_ENABLED = False


def enable_fail_fast() -> None:
    """Enable fail-fast behavior globally."""
    global FAIL_FAST_ENABLED
    FAIL_FAST_ENABLED = True
    logger.debug("Fail-fast mode enabled")


def disable_fail_fast() -> None:
    """Disable fail-fast behavior globally."""
    global FAIL_FAST_ENABLED
    FAIL_FAST_ENABLED = False
    logger.debug("Fail-fast mode disabled")


def _maybe_raise(message: str, exc: Exception | None = None) -> None:
    """Handle fail-fast behavior with optional exception re-raise."""
    if FAIL_FAST_ENABLED and exc is not None:
        logger.error(message)
        raise exc
    logger.warning(message)


def check_gpt5_mini_response(response: Any, context: Optional[str] = None) -> None:
    """Check GPT-5 mini response for quality issues.

    Args:
        response: The LLM response to validate
        context: Optional context string for logging

    Raises:
        ValueError: If response fails validation and FAIL_FAST_ENABLED is True
    """
    if response:
        return

    message = "Empty response from GPT-5 mini"
    if context:
        message = f"{message} ({context})"
    _maybe_raise(message, ValueError("Empty response from LLM"))


def check_llm_response(response: Any, context: Optional[str] = None) -> None:
    """Check LLM response for quality issues.

    Args:
        response: The LLM response to validate
        context: Optional context string for logging

    Raises:
        ValueError: If response fails validation and FAIL_FAST_ENABLED is True
    """
    if response:
        return

    message = "Empty response from LLM"
    if context:
        message = f"{message} ({context})"
    _maybe_raise(message, ValueError("Empty response from LLM"))


def _decorator(func: Callable) -> Callable:
    """Decorator variant to preserve backwards compatibility."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            fail_fast_on_exception(exc, func.__name__)
            raise

    return wrapper


def fail_fast_on_exception(
    exc_or_func: Union[Exception, Callable, None],
    context: Optional[str] = None
) -> Optional[Callable]:
    """Fail fast helper that works as decorator or direct exception handler.

    Args:
        exc_or_func: Exception instance to handle or callable to decorate
        context: Optional context string for logging

    Returns:
        Decorated callable when used as decorator, otherwise None
    """
    if callable(exc_or_func) and context is None:
        return _decorator(exc_or_func)

    if exc_or_func is None:
        return None

    exc = exc_or_func if isinstance(exc_or_func, Exception) else None
    message = f"Error occurred{f' in {context}' if context else ''}: {exc_or_func}"
    if exc is None:
        logger.warning(message)
        return None

    if FAIL_FAST_ENABLED:
        logger.error(f"Fail-fast enabled, raising exception: {message}")
        raise exc

    logger.warning(message)
    return None
