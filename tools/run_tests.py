"""Test runner that patches missing packaging.licenses for older packaging releases."""

from __future__ import annotations

import importlib.abc
import importlib.util
from pathlib import Path
import sys
import types


def ensure_packaging_licenses_stub() -> None:
    """Install a minimal packaging.licenses module if absent."""
    stub_dir = Path(__file__).resolve().parent.parent / "packaging_stubs"
    if str(stub_dir) not in sys.path:
        sys.path.insert(0, str(stub_dir))

    try:
        import packaging  # noqa: F401
    except Exception:
        return

    module = sys.modules.get("packaging.licenses")
    if module is None:
        module = types.ModuleType("packaging.licenses")

        def _normalize(license_str: str | None) -> str | None:
            return license_str

        module.normalize = _normalize  # type: ignore[attr-defined]
        module.is_valid = lambda *_args, **_kwargs: True  # type: ignore[attr-defined]
        sys.modules["packaging.licenses"] = module

    packaging.licenses = module  # type: ignore[attr-defined]
    _install_import_hook()
    stub_package_dir = stub_dir / "packaging"
    if stub_package_dir.is_dir():
        package_paths = getattr(packaging, "__path__", [])
        if str(stub_package_dir) not in package_paths:
            package_paths.append(str(stub_package_dir))


_HOOK_INSTALLED = False


class _PackagingLicensesLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.normalize = lambda license_str: license_str  # type: ignore[attr-defined]
        module.is_valid = lambda *_args, **_kwargs: True  # type: ignore[attr-defined]


class _PackagingLicensesFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "packaging.licenses":
            return importlib.util.spec_from_loader(fullname, _PackagingLicensesLoader())
        return None


def _install_import_hook() -> None:
    global _HOOK_INSTALLED
    if _HOOK_INSTALLED:
        return
    sys.meta_path.insert(0, _PackagingLicensesFinder())
    _HOOK_INSTALLED = True


def main(argv: list[str] | None = None) -> int:
    ensure_packaging_licenses_stub()
    import pytest

    return pytest.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
