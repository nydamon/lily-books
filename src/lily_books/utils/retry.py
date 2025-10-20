"""Advanced retry utilities with tenacity."""

import logging
import random
from typing import Any, Callable, Type, Union, List
from tenacity import (
    retry, stop_after_attempt, wait_exponential, wait_random,
    retry_if_exception_type, before_sleep_log, after_log
)

from ..config import settings

logger = logging.getLogger(__name__)


def create_retry_decorator(
    max_attempts: int = None,
    max_wait: int = None,
    base_wait: float = 1.0,
    jitter: bool = True,
    retry_exceptions: List[Type[Exception]] = None
) -> Callable:
    """
    Create a retry decorator with advanced configuration.
    
    Args:
        max_attempts: Maximum retry attempts (default from settings)
        max_wait: Maximum wait time in seconds (default from settings)
        base_wait: Base wait time for exponential backoff
        jitter: Whether to add random jitter to prevent thundering herd
        retry_exceptions: List of exception types to retry on
    
    Returns:
        Retry decorator
    """
    if max_attempts is None:
        max_attempts = settings.llm_max_retries
    
    if max_wait is None:
        max_wait = settings.llm_retry_max_wait
    
    if retry_exceptions is None:
        retry_exceptions = [Exception]  # Retry on all exceptions by default
    
    # Configure wait strategy
    if jitter:
        wait_strategy = wait_exponential(
            multiplier=base_wait,
            max=max_wait
        ) + wait_random(0, 1)  # Add random jitter
    else:
        wait_strategy = wait_exponential(
            multiplier=base_wait,
            max=max_wait
        )
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(tuple(retry_exceptions)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )


def create_rate_limit_retry_decorator() -> Callable:
    """Create retry decorator specifically for rate limit errors."""
    from openai import RateLimitError
    
    return create_retry_decorator(
        max_attempts=5,  # More attempts for rate limits
        max_wait=120,    # Longer max wait
        base_wait=2.0,   # Longer base wait
        jitter=True,     # Always use jitter for rate limits
        retry_exceptions=[RateLimitError]
    )


def create_validation_retry_decorator() -> Callable:
    """Create retry decorator for validation errors."""
    from ..utils.validators import ValidationError
    
    return create_retry_decorator(
        max_attempts=2,  # Fewer attempts for validation errors
        max_wait=30,     # Shorter max wait
        base_wait=1.0,   # Standard base wait
        jitter=False,    # No jitter needed for validation errors
        retry_exceptions=[ValidationError]
    )


def create_network_retry_decorator() -> Callable:
    """Create retry decorator for network-related errors."""
    import requests
    from openai import APIConnectionError, APITimeoutError
    
    return create_retry_decorator(
        max_attempts=3,
        max_wait=60,
        base_wait=1.5,
        jitter=True,
        retry_exceptions=[
            requests.RequestException,
            APIConnectionError,
            APITimeoutError
        ]
    )


def retry_with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    max_attempts: int = None,
    fallback_exceptions: List[Type[Exception]] = None
) -> Callable:
    """
    Create a function that retries primary_func and falls back to fallback_func.
    
    Args:
        primary_func: Primary function to try
        fallback_func: Fallback function if primary fails
        max_attempts: Maximum attempts for primary function
        fallback_exceptions: Exceptions that trigger fallback
    
    Returns:
        Function that tries primary then falls back
    """
    if max_attempts is None:
        max_attempts = settings.llm_max_retries
    
    if fallback_exceptions is None:
        fallback_exceptions = [Exception]
    
    def wrapper(*args, **kwargs):
        # Try primary function with retries
        retry_decorator = create_retry_decorator(max_attempts=max_attempts)
        
        try:
            return retry_decorator(primary_func)(*args, **kwargs)
        except tuple(fallback_exceptions) as e:
            logger.warning(f"Primary function failed, trying fallback: {e}")
            try:
                return fallback_func(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback function also failed: {fallback_error}")
                raise e  # Re-raise original error
    
    return wrapper


def log_retry_attempt(func_name: str, attempt: int, max_attempts: int, error: Exception) -> None:
    """Log retry attempt details."""
    logger.warning(
        f"Retry attempt {attempt}/{max_attempts} for {func_name}: {type(error).__name__}: {error}"
    )


def log_retry_success(func_name: str, attempt: int, total_attempts: int) -> None:
    """Log successful retry."""
    if attempt > 1:
        logger.info(f"Function {func_name} succeeded on attempt {attempt}/{total_attempts}")


def get_retry_stats(func_name: str) -> dict:
    """Get retry statistics for a function (placeholder for future implementation)."""
    return {
        "function": func_name,
        "total_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "retry_attempts": 0,
        "average_attempts": 0.0
    }


def retry_with_llm_enhancement(
    chain_func: Callable,
    input_data: dict,
    previous_error: str,
    attempt: int,
    output_type: str = "writer"
) -> Any:
    """
    Retry LLM chain with enhanced prompt based on failure analysis.
    
    Args:
        chain_func: The LLM chain function to retry
        input_data: Input data for the chain
        previous_error: Error message from previous attempt
        attempt: Current attempt number (1-based)
        output_type: Type of output ("writer" or "checker")
    
    Returns:
        Result from the retry attempt
    """
    from ..utils.validators import create_retry_prompt_enhancement
    
    # Enhance the prompt with specific guidance
    enhanced_prompt = create_retry_prompt_enhancement(
        input_data.get("prompt", ""),
        previous_error,
        attempt,
        output_type
    )
    
    # Update input data with enhanced prompt
    enhanced_input = input_data.copy()
    enhanced_input["prompt"] = enhanced_prompt
    
    logger.info(f"Retrying {output_type} chain with enhanced prompt (attempt {attempt})")
    
    # Retry with enhanced input
    return chain_func(enhanced_input)


def enhance_prompt_on_retry(
    original_prompt: str,
    error_context: dict,
    attempt: int,
    chain_type: str = "writer"
) -> str:
    """
    Enhance prompt for retry based on error context.
    
    Args:
        original_prompt: Original prompt that failed
        error_context: Context about what went wrong
        attempt: Current attempt number
        chain_type: Type of chain ("writer" or "checker")
    
    Returns:
        Enhanced prompt
    """
    error_msg = error_context.get("error", "Unknown error")
    error_type = error_context.get("type", "validation")
    
    if chain_type == "writer":
        enhancement = f"""
        
        RETRY ATTEMPT {attempt}: Previous attempt encountered: {error_type} - {error_msg}
        
        Please focus on:
        1. Ensuring all paragraphs are non-empty and meaningful
        2. Maintaining proper paragraph structure and count
        3. Preserving all content from the original text
        4. Following the modernization guidelines precisely
        5. Providing your best attempt even if some aspects are challenging
        
        Remember: Quality is more important than perfect adherence to rigid rules.
        """
    else:  # checker
        enhancement = f"""
        
        RETRY ATTEMPT {attempt}: Previous attempt encountered: {error_type} - {error_msg}
        
        Please focus on:
        1. Providing a comprehensive assessment with all required fields
        2. Being specific about any issues found
        3. Maintaining objectivity in your evaluation
        4. Using your judgment to assess quality appropriately
        5. Providing your best assessment even if some aspects are challenging
        
        Remember: Your judgment is more valuable than rigid adherence to metrics.
        """
    
    return original_prompt + enhancement


def enhance_qa_prompt_on_retry(
    original_prompt: str,
    error_context: dict,
    attempt: int
) -> str:
    """
    Enhance QA prompt for retry based on error context.
    
    Args:
        original_prompt: Original QA prompt that failed
        error_context: Context about what went wrong
        attempt: Current attempt number
    
    Returns:
        Enhanced QA prompt
    """
    return enhance_prompt_on_retry(original_prompt, error_context, attempt, "checker")


def analyze_failure_and_enhance_prompt(
    original_input: dict,
    error: Exception,
    attempt: int,
    chain_type: str = "writer"
) -> dict:
    """
    Analyze failure and create enhanced input for retry.
    
    Args:
        original_input: Original input that failed
        error: The error that occurred
        attempt: Current attempt number
        chain_type: Type of chain ("writer" or "checker")
    
    Returns:
        Enhanced input data
    """
    error_context = {
        "error": str(error),
        "type": type(error).__name__,
        "attempt": attempt
    }
    
    # Enhance the prompt
    enhanced_prompt = enhance_prompt_on_retry(
        original_input.get("prompt", ""),
        error_context,
        attempt,
        chain_type
    )
    
    # Create enhanced input
    enhanced_input = original_input.copy()
    enhanced_input["prompt"] = enhanced_prompt
    enhanced_input["retry_attempt"] = attempt
    enhanced_input["error_context"] = error_context
    
    return enhanced_input
