"""Compatibility stub for packaging.licenses used by pytest plugins."""

from __future__ import annotations

def normalize(license_str: str | None) -> str | None:
    """Return the supplied license string unchanged."""
    return license_str


def is_valid(*_args, **_kwargs) -> bool:
    """Placeholder validation that always succeeds."""
    return True

