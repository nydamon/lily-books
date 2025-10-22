"""Project-wide site customization for Lily Books."""

import sys
import types
from pathlib import Path


def _ensure_packaging_licenses_stub() -> None:
    """Install a stub for packaging.licenses when using older packaging releases."""
    try:
        import packaging  # noqa: F401
    except Exception:
        return

    stub_dir = Path(__file__).resolve().parent / "packaging_stubs"
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

    packaging.licenses = module  # type: ignore[attr-defined]
    stub_package_dir = stub_dir / "packaging"
    if stub_package_dir.is_dir():
        package_paths = getattr(packaging, "__path__", [])
        if str(stub_package_dir) not in package_paths:
            package_paths.append(str(stub_package_dir))


_ensure_packaging_licenses_stub()
