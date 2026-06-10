"""Adapter registry for image-gen providers.

Adding a provider:
1. Create a new module in this package (e.g. adapters/openai.py).
2. Implement `generate(prompt, out_path, fmt, aspect=None, api_key=None)` in that module.
3. The module filename (without .py) becomes the provider name — no other registration step required.
"""

import importlib
import pkgutil
from pathlib import Path

_ADAPTER_CACHE: dict[str, object] = {}


def _discover() -> dict[str, object]:
    """Discover all adapter modules in this package."""
    if _ADAPTER_CACHE:
        return _ADAPTER_CACHE

    package_dir = Path(__file__).resolve().parent
    for _, name, ispkg in pkgutil.iter_modules([str(package_dir)]):
        if ispkg:
            continue
        if name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"adapters.{name}")
            if hasattr(mod, "generate"):
                _ADAPTER_CACHE[name] = mod
        except Exception:
            pass
    return _ADAPTER_CACHE


def resolve_provider(name: str) -> object | None:
    """Return the adapter module for the given provider name, or None."""
    adapters = _discover()
    return adapters.get(name)


def list_providers() -> list[str]:
    """Return a list of registered provider names."""
    return list(_discover().keys())
