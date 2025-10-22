"""Langfuse tracing utilities."""

from contextlib import contextmanager
import logging
from typing import Optional, List, Dict, Any, Iterator
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)

try:
    from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    LangfuseCallbackHandler = None


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is available and enabled."""
    from ..config import settings
    return (
        LANGFUSE_AVAILABLE
        and settings.langfuse_enabled
        and bool(settings.langfuse_public_key)
        and bool(settings.langfuse_secret_key)
    )


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
        logger.warning("Failed to create Langfuse callback: %s", e)
        return None


@contextmanager
def trace_pipeline(
    slug: str,
    book_id: int,
    chapters: Optional[List[int]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Iterator[Optional[Any]]:
    """Context manager placeholder for pipeline tracing."""
    if not is_langfuse_enabled():
        yield None
        return

    logger.debug(
        "Langfuse tracing not configured for pipeline slug=%s book_id=%s",
        slug,
        book_id,
    )
    yield None


@contextmanager
def trace_node(
    trace: Optional[Any],
    node_name: str,
    slug: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Iterator[Optional[Any]]:
    """Context manager placeholder for node-level tracing."""
    if not trace:
        yield None
        return

    logger.debug(
        "Langfuse tracing not configured for node=%s slug=%s",
        node_name,
        slug,
    )
    yield None


def track_error(trace: Optional[Any], error: Exception, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Placeholder error tracking."""
    if not trace:
        return

    logger.debug("Langfuse error tracking noop: %s (%s)", error, metadata)


def flush_langfuse() -> None:
    """Placeholder flush."""
    if not is_langfuse_enabled():
        return

    logger.debug("Langfuse flush noop")
