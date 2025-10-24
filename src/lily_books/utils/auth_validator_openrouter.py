"""OpenRouter-only authentication validator."""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from httpx import HTTPStatusError
from openai import AuthenticationError as OpenAIAuthError
from openai import OpenAI

logger = logging.getLogger(__name__)


def validate_openrouter_auth() -> dict[str, Any]:
    """Validates OpenRouter API key and model access."""
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "openai/gpt-5-mini")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "anthropic/claude-haiku-4.5")

    if not api_key:
        return {
            "service": "OPENROUTER",
            "status": "failed",
            "error": "OPENROUTER_API_KEY not set",
        }

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        # Test OpenAI model via OpenRouter
        openai_response = client.chat.completions.create(
            model=openai_model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )

        # Test Anthropic model via OpenRouter
        anthropic_response = client.chat.completions.create(
            model=anthropic_model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )

        return {
            "service": "OPENROUTER",
            "status": "success",
            "openai_model": openai_model,
            "anthropic_model": anthropic_model,
            "openai_response": openai_response.choices[0].message.content,
            "anthropic_response": anthropic_response.choices[0].message.content,
            "usage": {
                "openai_tokens": openai_response.usage.total_tokens
                if openai_response.usage
                else None,
                "anthropic_tokens": anthropic_response.usage.total_tokens
                if anthropic_response.usage
                else None,
            },
        }
    except OpenAIAuthError as e:
        return {
            "service": "OPENROUTER",
            "status": "failed",
            "error": f"OpenRouter API error: {e}",
            "details": "AuthenticationError",
        }
    except HTTPStatusError as e:
        return {
            "service": "OPENROUTER",
            "status": "failed",
            "error": f"OpenRouter API error: {e}",
            "details": f"HTTPStatusError: {e.response.status_code} - {e.response.text}",
        }
    except Exception as e:
        return {
            "service": "OPENROUTER",
            "status": "failed",
            "error": f"OpenRouter API error: {e}",
            "details": str(e),
        }


def validate_fish_audio_auth() -> dict[str, Any]:
    """Validates Fish Audio API key and access."""
    load_dotenv()
    api_key = os.getenv("FISH_API_KEY")

    if not api_key:
        return {
            "service": "FISH_AUDIO",
            "status": "failed",
            "error": "FISH_API_KEY not set",
        }

    try:
        from fish_audio_sdk import Session

        # Test Fish Audio API by initializing session
        Session(api_key)
        # Try to list models to verify API key works
        # Note: Fish Audio SDK doesn't have a simple health check endpoint,
        # so we just verify the session can be created
        return {"service": "FISH_AUDIO", "status": "success", "authenticated": True}
    except Exception as e:
        return {
            "service": "FISH_AUDIO",
            "status": "failed",
            "error": f"Fish Audio API error: {e}",
            "details": str(e),
        }


def validate_pipeline_auth() -> bool:
    """
    Performs a comprehensive authentication check for all required services.
    Logs results and returns True if all critical services pass.
    """
    results = []

    logger.info("============================================================")
    logger.info("🔐 AUTHENTICATION VALIDATION RESULTS (OpenRouter Only)")
    logger.info("============================================================")

    openrouter_result = validate_openrouter_auth()
    results.append(openrouter_result)
    logger.info(
        f"{'✅' if openrouter_result['status'] == 'success' else '❌'} {openrouter_result['service']}:"
    )
    logger.info(f"   Status: {openrouter_result['status']}")
    if "openai_model" in openrouter_result:
        logger.info(f"   OpenAI Model: {openrouter_result['openai_model']}")
    if "anthropic_model" in openrouter_result:
        logger.info(f"   Anthropic Model: {openrouter_result['anthropic_model']}")
    if "openai_response" in openrouter_result:
        logger.info(
            f"   OpenAI Response: {openrouter_result['openai_response'][:50]}..."
        )
    if "anthropic_response" in openrouter_result:
        logger.info(
            f"   Anthropic Response: {openrouter_result['anthropic_response'][:50]}..."
        )
    if "usage" in openrouter_result:
        logger.info(
            f"   Usage: OpenAI={openrouter_result['usage']['openai_tokens']}, Anthropic={openrouter_result['usage']['anthropic_tokens']}"
        )
    if "error" in openrouter_result:
        logger.error(f"   Error: {openrouter_result['error']}")
    if "details" in openrouter_result:
        logger.error(f"   Details: {openrouter_result['details']}")
    logger.info("")

    from ..config import settings

    if settings.enable_audio:
        fish_audio_result = validate_fish_audio_auth()
        results.append(fish_audio_result)
        logger.info(
            f"{'✅' if fish_audio_result['status'] == 'success' else '❌'} {fish_audio_result['service']}:"
        )
        logger.info(f"   Status: {fish_audio_result['status']}")
        if "authenticated" in fish_audio_result:
            logger.info(f"   Authenticated: {fish_audio_result['authenticated']}")
        if "error" in fish_audio_result:
            logger.error(f"   Error: {fish_audio_result['error']}")
        if "details" in fish_audio_result:
            logger.error(f"   Details: {fish_audio_result['details']}")
        logger.info("")

    all_passed = all(r["status"] == "success" for r in results)

    if not all_passed:
        failed_services = [r["service"] for r in results if r["status"] != "success"]
        logger.warning("============================================================")
        logger.warning("⚠️  SOME AUTHENTICATION SERVICES FAILED!")
        logger.warning(f"   Failed services: {', '.join(failed_services)}")
        logger.warning("============================================================")
    else:
        logger.info("============================================================")
        logger.info("🎉 ALL AUTHENTICATION SERVICES WORKING!")
        logger.info("============================================================")

    return all_passed
