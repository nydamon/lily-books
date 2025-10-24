"""Token counting utilities for LLM context window management."""

import logging
import sys as _sys

import tiktoken

_sys.modules.setdefault("src.lily_books.utils.tokens", _sys.modules[__name__])

logger = logging.getLogger(__name__)

# Model context windows (approximate)
MODEL_CONTEXT_WINDOWS = {
    "openai/gpt-5-mini": 128000,
    "openai/gpt-4o-mini": 128000,
    "gpt-4": 128000,
    "gpt-4-turbo": 128000,
    "anthropic/claude-sonnet-4.5": 1000000,
    "anthropic/claude-haiku-4.5": 200000,
}

# Model encoding mappings
MODEL_ENCODINGS = {
    "openai/gpt-5-mini": "cl100k_base",
    "openai/gpt-4o-mini": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-4-turbo": "cl100k_base",
    "anthropic/claude-sonnet-4.5": "cl100k_base",  # Claude uses same encoding
    "anthropic/claude-haiku-4.5": "cl100k_base",
}


def count_tokens(text: str, model: str = "openai/gpt-5-mini") -> int:
    """Count tokens in text for the specified model."""
    try:
        encoding_name = MODEL_ENCODINGS.get(model, "cl100k_base")
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Token counting failed for model {model}: {e}")
        # Fallback: rough estimate (4 chars per token)
        return len(text) // 4


def count_tokens_batch(texts: list[str], model: str = "openai/gpt-5-mini") -> list[int]:
    """Count tokens for a batch of texts."""
    return [count_tokens(text, model) for text in texts]


def get_context_window(model: str) -> int:
    """Get context window size for a model."""
    return MODEL_CONTEXT_WINDOWS.get(model, 128000)  # Default to GPT-4 size


def validate_context_window(
    text: str, model: str, safety_margin: float = 0.2
) -> tuple[bool, int, int]:
    """
    Validate that text fits within model's context window.

    Args:
        text: Text to validate
        model: Model name
        safety_margin: Fraction of context window to reserve (0.2 = 20%)

    Returns:
        (is_valid, token_count, max_tokens)
    """
    token_count = count_tokens(text, model)
    context_window = get_context_window(model)
    max_tokens = int(context_window * (1 - safety_margin))

    is_valid = token_count <= max_tokens

    if not is_valid:
        logger.warning(
            f"Text exceeds context window for {model}: "
            f"{token_count} tokens > {max_tokens} max "
            f"(context window: {context_window}, safety margin: {safety_margin})"
        )

    return is_valid, token_count, max_tokens


def calculate_optimal_batch_size(
    paragraphs: list[str],
    model: str = "openai/gpt-5-mini",
    target_utilization: float = 0.2,  # Reduced from 0.6 to 0.2
    min_batch_size: int = 1,
    max_batch_size: int = 3,  # Reduced from 20 to 3
) -> int:
    """
    Calculate optimal batch size based on token counts.

    Args:
        paragraphs: List of paragraphs to process
        model: Model name
        target_utilization: Target fraction of context window to use
        min_batch_size: Minimum batch size
        max_batch_size: Maximum batch size

    Returns:
        Optimal batch size
    """
    if not paragraphs:
        return min_batch_size

    # Count tokens for each paragraph
    token_counts = count_tokens_batch(paragraphs, model)
    context_window = get_context_window(model)
    target_tokens = int(context_window * target_utilization)

    # Calculate cumulative token count
    cumulative_tokens = 0
    batch_size = 0

    for i, token_count in enumerate(token_counts):
        # Add separator tokens (estimate 2 tokens per paragraph separator)
        separator_tokens = max(0, i) * 2

        if cumulative_tokens + token_count + separator_tokens <= target_tokens:
            cumulative_tokens += token_count + separator_tokens
            batch_size = i + 1
        else:
            break

    # Ensure batch size is within bounds
    batch_size = max(min_batch_size, min(batch_size, max_batch_size))

    logger.info(
        f"Calculated batch size {batch_size} for {len(paragraphs)} paragraphs "
        f"(target: {target_tokens} tokens, model: {model})"
    )

    return batch_size


def estimate_prompt_tokens(
    prompt_template: str, model: str = "openai/gpt-5-mini"
) -> int:
    """Estimate tokens for a prompt template (without variable substitution)."""
    return count_tokens(prompt_template, model)


def log_token_usage(text: str, model: str, operation: str = "processing") -> None:
    """Log token usage for monitoring."""
    token_count = count_tokens(text, model)
    context_window = get_context_window(model)
    utilization = token_count / context_window

    logger.info(
        f"{operation}: {token_count} tokens ({utilization:.1%} of {model} context window)"
    )

    if utilization > 0.8:
        logger.warning(f"High token utilization: {utilization:.1%}")
