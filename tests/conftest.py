"""Pytest configuration for Lily Books tests."""

import builtins
import sys
import types
from pathlib import Path

from lily_books.models import CheckerOutput
from lily_books.utils import validators as _validators


def _install_packaging_licenses_stub() -> None:
    """Provide a minimal packaging.licenses module for older packaging versions."""
    stub_dir = Path(__file__).resolve().parents[1] / "packaging_stubs"
    if str(stub_dir) not in sys.path:
        sys.path.insert(0, str(stub_dir))
    module = sys.modules.get("packaging.licenses")
    if module is None:
        module = types.ModuleType("packaging.licenses")

        def _normalize(license_str: str | None) -> str | None:
            return license_str

        module.normalize = _normalize  # type: ignore[attr-defined]
        module.is_valid = lambda *_args, **_kwargs: True  # type: ignore[attr-defined]

        sys.modules["packaging.licenses"] = module

    import packaging

    packaging.licenses = module  # type: ignore[attr-defined]
    stub_package_dir = stub_dir / "packaging"
    if stub_package_dir.is_dir():
        package_paths = getattr(packaging, "__path__", [])
        if str(stub_package_dir) not in package_paths:
            package_paths.append(str(stub_package_dir))


_install_packaging_licenses_stub()

# Provide CheckerOutput globally for legacy tests expecting bare reference
builtins.CheckerOutput = CheckerOutput
builtins.validate_writer_output = _validators.validate_writer_output
builtins.validate_checker_output = _validators.validate_checker_output
builtins.validate_paragraph_pair = _validators.validate_paragraph_pair
builtins.validate_batch_consistency = _validators.validate_batch_consistency
builtins.safe_validate_writer_output = _validators.safe_validate_writer_output
builtins.safe_validate_checker_output = _validators.safe_validate_checker_output
