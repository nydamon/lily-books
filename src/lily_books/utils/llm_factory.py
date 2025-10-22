"""LLM factory with fallback support and Langfuse tracing."""

import logging
from typing import List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableWithFallbacks
import sys as _sys

_sys.modules.setdefault("src.lily_books.utils.llm_factory", _sys.modules[__name__])
ChatAnthropic = ChatOpenAI

from ..config import settings
from .gpt5_mini_llm import create_gpt5_mini_llm
from ..utils.cache import get_cached_llm
from .langfuse_tracer import is_langfuse_enabled, get_langchain_callback_handler

logger = logging.getLogger(__name__)


def create_openai_llm_with_fallback(
    temperature: float = 0.2,
    timeout: int = 60,  # Increased for OpenRouter API latency
    max_retries: int = 2,
    cache_enabled: bool = True,  # Re-enabled for cost optimization
    trace_name: Optional[str] = None  # For Langfuse tracing
) -> Any:
    """Create OpenAI LLM via OpenRouter with fallback model support and Langfuse tracing.
    
    Args:
        temperature: Model temperature
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        cache_enabled: Whether to enable caching
        trace_name: Optional name for Langfuse traces
        
    Returns:
        LLM with fallback support and Langfuse tracing
    """
    
    # Prepare callbacks for Langfuse tracing
    callbacks = []
    if is_langfuse_enabled():
        callback_handler = get_langchain_callback_handler()
        if callback_handler:
            callbacks.append(callback_handler)
            logger.info("Added Langfuse callback handler to OpenAI LLM")

    api_key = str(getattr(settings, "openrouter_api_key", ""))

    # Primary model via OpenRouter
    logger.info(f"Creating primary OpenAI LLM via OpenRouter: {settings.openai_model}")
    primary_llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        timeout=timeout,
        max_retries=max_retries,
        callbacks=callbacks if callbacks else None,
        model_kwargs={"extra_headers": {"X-Title": trace_name or "lily-books"}}
    )
    
    # Fallback model via OpenRouter
    logger.info(f"Creating fallback OpenAI LLM via OpenRouter: {settings.openai_fallback_model}")
    fallback_llm = ChatOpenAI(
        model=settings.openai_fallback_model,
        temperature=temperature,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        timeout=timeout,
        max_retries=max_retries,
        callbacks=callbacks if callbacks else None,
        model_kwargs={"extra_headers": {"X-Title": trace_name or "lily-books"}}
    )
    
    # Add caching if enabled
    if cache_enabled:
        primary_llm = get_cached_llm(primary_llm)
        fallback_llm = get_cached_llm(fallback_llm)
    
    # Create fallback chain
    llm_with_fallback = RunnableWithFallbacks(
        runnable=primary_llm,
        fallbacks=[fallback_llm]
    )
    
    logger.info(f"Created OpenAI LLM via OpenRouter with fallback: {settings.openai_model} -> {settings.openai_fallback_model}")
    
    return llm_with_fallback


def create_anthropic_llm_with_fallback(
    temperature: float = 0.0,
    timeout: int = 60,  # Increased for OpenRouter API latency
    max_retries: int = 2,
    cache_enabled: bool = True,  # Re-enabled for cost optimization
    trace_name: Optional[str] = None  # For Langfuse tracing
) -> Any:
    """Create Anthropic LLM via OpenRouter with fallback model support and Langfuse tracing.
    
    Args:
        temperature: Model temperature
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        cache_enabled: Whether to enable caching
        trace_name: Optional name for Langfuse traces
        
    Returns:
        LLM with fallback support and Langfuse tracing
    """
    
    try:
        # Prepare callbacks for Langfuse tracing
        callbacks = []
        if is_langfuse_enabled():
            callback_handler = get_langchain_callback_handler()
            if callback_handler:
                callbacks.append(callback_handler)
                logger.info("Added Langfuse callback handler to Anthropic LLM")

        api_key = str(getattr(settings, "openrouter_api_key", ""))

        # Primary model via OpenRouter
        logger.info(f"Creating primary Anthropic LLM via OpenRouter: {settings.anthropic_model}")
        primary_llm = ChatAnthropic(
            model=settings.anthropic_model,
            temperature=temperature,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=timeout,
            max_retries=max_retries,
            callbacks=callbacks if callbacks else None,
            model_kwargs={"extra_headers": {"X-Title": trace_name or "lily-books"}}
        )
        
        # Fallback model via OpenRouter
        logger.info(f"Creating fallback Anthropic LLM via OpenRouter: {settings.anthropic_fallback_model}")
        fallback_llm = ChatAnthropic(
            model=settings.anthropic_fallback_model,
            temperature=temperature,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=timeout,
            max_retries=max_retries,
            callbacks=callbacks if callbacks else None,
            model_kwargs={"extra_headers": {"X-Title": trace_name or "lily-books"}}
        )
        
        # Add caching if enabled
        if cache_enabled:
            primary_llm = get_cached_llm(primary_llm)
            fallback_llm = get_cached_llm(fallback_llm)
        
        # Create fallback chain
        llm_with_fallback = RunnableWithFallbacks(
            runnable=primary_llm,
            fallbacks=[fallback_llm]
        )
        
        logger.info(f"Created Anthropic LLM via OpenRouter with fallback: {settings.anthropic_model} -> {settings.anthropic_fallback_model}")
        
        return llm_with_fallback
        
    except Exception as e:
        logger.error(f"Failed to create Anthropic LLM via OpenRouter with fallback: {e}")
        # Return a basic LLM without fallback as last resort
        try:
            callbacks = []
            if is_langfuse_enabled():
                callback_handler = get_langchain_callback_handler()
                if callback_handler:
                    callbacks.append(callback_handler)
            
            basic_llm = ChatAnthropic(
                model=settings.anthropic_fallback_model,
                temperature=temperature,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=timeout,
                max_retries=max_retries,
                callbacks=callbacks if callbacks else None,
                model_kwargs={"extra_headers": {"X-Title": trace_name or "lily-books"}}
            )
            logger.warning(f"Using basic Anthropic LLM via OpenRouter without fallback: {settings.anthropic_fallback_model}")
            return basic_llm
        except Exception as fallback_error:
            logger.error(f"Failed to create basic Anthropic LLM via OpenRouter: {fallback_error}")
            raise RuntimeError(f"Unable to create any Anthropic LLM via OpenRouter: {e}")


def create_llm_with_fallback(
    provider: str,
    temperature: float = 0.2,
    timeout: int = 60,  # Increased for OpenRouter API latency
    max_retries: int = 2,
    cache_enabled: bool = True,  # Re-enabled for cost optimization
    trace_name: Optional[str] = None  # For Langfuse tracing
) -> Any:
    """
    Create LLM with fallback support for the specified provider with Langfuse tracing.
    
    Args:
        provider: "openai" or "anthropic"
        temperature: Model temperature
        timeout: Request timeout
        max_retries: Maximum retries
        cache_enabled: Whether to enable caching
        trace_name: Optional name for Langfuse traces
    
    Returns:
        LLM with fallback support and Langfuse tracing
    """
    if provider.lower() == "openai":
        return create_openai_llm_with_fallback(temperature, timeout, max_retries, cache_enabled, trace_name)
    elif provider.lower() == "anthropic":
        return create_anthropic_llm_with_fallback(temperature, timeout, max_retries, cache_enabled, trace_name)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def log_fallback_usage(provider: str, primary_model: str, fallback_model: str, success: bool) -> None:
    """Log fallback usage for monitoring."""
    if success:
        logger.info(f"Fallback successful: {provider} {primary_model} -> {fallback_model}")
    else:
        logger.warning(f"Fallback failed: {provider} {primary_model} -> {fallback_model}")


def _normalize_model_name(model: str) -> str:
    return model.split("/", 1)[-1] if "/" in model else model


def get_model_info(provider: str) -> dict:
    """Get model information for the provider."""
    provider = provider.lower()

    if provider == "openai":
        return {
            "primary": _normalize_model_name(settings.openai_model),
            "fallback": _normalize_model_name(settings.openai_fallback_model),
            "provider": "openai"
        }
    if provider == "anthropic":
        primary = settings.anthropic_model
        fallback_display = "claude-3-haiku"

        return {
            "primary": primary,
            "fallback": fallback_display,
            "provider": "anthropic"
        }

    raise ValueError(f"Unsupported provider: {provider}")
