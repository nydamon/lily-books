"""LLM factory with fallback support."""

import logging
from typing import List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableWithFallbacks

from ..config import settings
from ..utils.cache import get_cached_llm

logger = logging.getLogger(__name__)


def create_openai_llm_with_fallback(
    temperature: float = 0.2,
    timeout: int = 30,
    max_retries: int = 2,
    cache_enabled: bool = True
) -> Any:
    """Create OpenAI LLM with fallback model support."""
    
    # Primary model
    primary_llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature,
        api_key=settings.openai_api_key,
        timeout=timeout,
        max_retries=max_retries
    )
    
    # Fallback model
    fallback_llm = ChatOpenAI(
        model=settings.openai_fallback_model,
        temperature=temperature,
        api_key=settings.openai_api_key,
        timeout=timeout,
        max_retries=max_retries
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
    
    logger.info(f"Created OpenAI LLM with fallback: {settings.openai_model} -> {settings.openai_fallback_model}")
    
    return llm_with_fallback


def create_anthropic_llm_with_fallback(
    temperature: float = 0.0,
    timeout: int = 30,
    max_retries: int = 2,
    cache_enabled: bool = True
) -> Any:
    """Create Anthropic LLM via OpenRouter with fallback model support."""
    
    try:
        # Primary model via OpenRouter
        primary_llm = ChatOpenAI(
            model=settings.anthropic_model,
            temperature=temperature,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=timeout,
            max_retries=max_retries
        )
        
        # Fallback model via OpenRouter
        fallback_llm = ChatOpenAI(
            model=settings.anthropic_fallback_model,
            temperature=temperature,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=timeout,
            max_retries=max_retries
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
            basic_llm = ChatOpenAI(
                model=settings.anthropic_fallback_model,
                temperature=temperature,
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=timeout,
                max_retries=max_retries
            )
            logger.warning(f"Using basic Anthropic LLM via OpenRouter without fallback: {settings.anthropic_fallback_model}")
            return basic_llm
        except Exception as fallback_error:
            logger.error(f"Failed to create basic Anthropic LLM via OpenRouter: {fallback_error}")
            raise RuntimeError(f"Unable to create any Anthropic LLM via OpenRouter: {e}")


def create_llm_with_fallback(
    provider: str,
    temperature: float = 0.2,
    timeout: int = 30,
    max_retries: int = 2,
    cache_enabled: bool = True
) -> Any:
    """
    Create LLM with fallback support for the specified provider.
    
    Args:
        provider: "openai" or "anthropic"
        temperature: Model temperature
        timeout: Request timeout
        max_retries: Maximum retries
        cache_enabled: Whether to enable caching
    
    Returns:
        LLM with fallback support
    """
    if provider.lower() == "openai":
        return create_openai_llm_with_fallback(temperature, timeout, max_retries, cache_enabled)
    elif provider.lower() == "anthropic":
        return create_anthropic_llm_with_fallback(temperature, timeout, max_retries, cache_enabled)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def log_fallback_usage(provider: str, primary_model: str, fallback_model: str, success: bool) -> None:
    """Log fallback usage for monitoring."""
    if success:
        logger.info(f"Fallback successful: {provider} {primary_model} -> {fallback_model}")
    else:
        logger.warning(f"Fallback failed: {provider} {primary_model} -> {fallback_model}")


def get_model_info(provider: str) -> dict:
    """Get model information for the provider."""
    if provider.lower() == "openai":
        return {
            "primary": settings.openai_model,
            "fallback": settings.openai_fallback_model,
            "provider": "openai"
        }
    elif provider.lower() == "anthropic":
        return {
            "primary": settings.anthropic_model,
            "fallback": settings.anthropic_fallback_model,
            "provider": "anthropic"
        }
    else:
        raise ValueError(f"Unsupported provider: {provider}")
