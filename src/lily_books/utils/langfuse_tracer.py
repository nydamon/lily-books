"""Langfuse tracing utilities."""

from typing import Optional, List
from langchain_core.callbacks import BaseCallbackHandler

try:
    from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    LangfuseCallbackHandler = None


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is available and enabled."""
    from ..config import settings
    return LANGFUSE_AVAILABLE and settings.langfuse_enabled


def get_langchain_callback_handler() -> Optional[LangfuseCallbackHandler]:
    """Get Langfuse callback handler if available and configured."""
    if not is_langfuse_enabled():
        return None

    from ..config import settings

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    try:
        callback = LangfuseCallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host
        )
        return callback
    except Exception as e:
        print(f"Failed to create Langfuse callback: {e}")
        return None
