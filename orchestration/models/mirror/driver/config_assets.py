"""config_assets.py — per-model config-dir renderer for the rbtv mirror driver.

Renders the elected worker's config directory (`.codex/`, `.kimi/`) into
a target workspace by copying its `mirror-assets/` tree.  A config-less package
(opencode — no mirror-assets seed) is never passed here; the driver skips it.  For the ``codex`` package
it additionally generates `.codex/hooks.json` from `.claude/settings.json` when that
file contains a ``hooks`` block; when the block is absent the file is skipped (not an
error).

Public API
----------
``render_config(target_root, package, *, check) -> list[dict]``
    Copy the package's ``mirror-assets/`` tree into ``target_root`` idempotently.
    Returns a list of managed-file records:
        ``{"path": "<target-root-relative posix path>", "kind": "config",
           "owner": "<codex-cli|kimi-code-cli>"}``

Constraints
-----------
- Source-agnostic: reads NO manifest file.  All inputs come from the
  ``mirror-assets/`` subtree living beside each model package.
- Uses ``write_if_changed`` from the sibling ``mirror.py`` for idempotent writes
  and ``--check`` semantics (returns ``"stale"`` without writing in check mode).
- Codex-only: `.codex/hooks.json` is generated from ``.claude/settings.json``
  ``hooks``; absent ``hooks`` block → file silently skipped.
- NO commits.  The conductor commits at wave-close.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Resolve the mirror.py sibling so write_if_changed can be imported without
# the rbtv package being installed.  This module lives at:
#   orchestration/models/mirror/driver/config_assets.py
# mirror.py lives at:
#   orchestration/models/mirror/mirror.py
# ---------------------------------------------------------------------------
_DRIVER_DIR = Path(__file__).resolve().parent          # …/mirror/driver/
_MIRROR_DIR = _DRIVER_DIR.parent                       # …/mirror/
_MODELS_DIR = _MIRROR_DIR.parent                       # …/models/

import importlib.util as _ilu
import sys as _sys

def _import_mirror() -> object:
    """Import mirror.py as a module without polluting sys.modules with a
    generic name that could collide with other 'mirror' modules."""
    mod_name = "rbtv_mirror_engine"
    if mod_name in _sys.modules:
        return _sys.modules[mod_name]
    spec = _ilu.spec_from_file_location(mod_name, _MIRROR_DIR / "mirror.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate mirror.py at {_MIRROR_DIR / 'mirror.py'}")
    mod = _ilu.module_from_spec(spec)
    _sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Supported packages and their mirror-assets subtrees
# ---------------------------------------------------------------------------

#: Packages this module knows how to render.
SUPPORTED_PACKAGES: frozenset[str] = frozenset({"codex-cli", "kimi-code-cli"})

#: Config-dir name produced in the target workspace for each package.
#: Keys are the package ids; values are the tool's native config-dir name (unchanged).
_CONFIG_DIR: dict[str, str] = {
    "codex-cli": ".codex",
    "kimi-code-cli": ".kimi",
}


def _mirror_assets_dir(package: str) -> Path:
    """Absolute path to the ``mirror-assets/`` subtree for *package*."""
    return _MODELS_DIR / package / "mirror-assets"


def _rel(path: Path, root: Path) -> str:
    """Vault-root-relative POSIX path string."""
    return path.relative_to(root).as_posix()


# ---------------------------------------------------------------------------
# Core rendering
# ---------------------------------------------------------------------------

def render_config(
    target_root: Path | str,
    package: str,
    *,
    check: bool = False,
) -> list[dict[str, str]]:
    """Copy the package's ``mirror-assets/`` tree into *target_root*.

    For the ``codex`` package, also generates ``.codex/hooks.json`` from
    ``.claude/settings.json`` ``hooks`` when present; silently skips when absent.

    Parameters
    ----------
    target_root:
        Absolute path to the target workspace (e.g. the vault root).
    package:
        One of ``"codex-cli"``, ``"kimi-code-cli"``.
    check:
        When ``True`` the function performs a read-only drift check via
        ``write_if_changed``'s check semantics — it returns ``"stale"`` for any
        file that would change without actually writing it.  The returned record
        list is still complete (useful for the driver's ``--check`` mode).

    Returns
    -------
    list[dict]
        Managed-file records ``{"path": <str>, "kind": "config",
        "owner": <package>}``.  Paths are POSIX strings relative to
        *target_root*.

    Raises
    ------
    ValueError
        If *package* is not in ``SUPPORTED_PACKAGES``.
    FileNotFoundError
        If the ``mirror-assets/`` directory for *package* does not exist.
    """
    if package not in SUPPORTED_PACKAGES:
        raise ValueError(
            f"render_config: unknown package {package!r}. "
            f"Supported: {sorted(SUPPORTED_PACKAGES)}"
        )

    target_root = Path(target_root).resolve()
    assets_dir = _mirror_assets_dir(package)
    if not assets_dir.is_dir():
        raise FileNotFoundError(
            f"mirror-assets directory not found for package {package!r}: {assets_dir}"
        )

    mirror = _import_mirror()
    wic = mirror.write_if_changed  # type: ignore[attr-defined]

    records: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    # 1. Copy every file from mirror-assets/ into target_root (idempotent)
    # ------------------------------------------------------------------
    for src in sorted(assets_dir.rglob("*")):
        if not src.is_file():
            continue
        # Relative path inside mirror-assets/ (e.g. ".codex/config.toml")
        rel_inside = src.relative_to(assets_dir)
        dest = target_root / rel_inside
        content = src.read_text(encoding="utf-8")
        wic(dest, content, check=check)
        records.append({
            "path": _rel(dest, target_root),
            "kind": "config",
            "owner": package,
        })

    # ------------------------------------------------------------------
    # 2. Codex-only: generate .codex/hooks.json from .claude/settings.json
    # ------------------------------------------------------------------
    if package == "codex-cli":
        hooks_record = _render_codex_hooks(target_root, check=check, wic=wic)
        if hooks_record is not None:
            records.append(hooks_record)

    return records


def _render_codex_hooks(
    target_root: Path,
    *,
    check: bool,
    wic: object,  # write_if_changed callable from mirror.py
) -> dict[str, str] | None:
    """Generate ``.codex/hooks.json`` from ``.claude/settings.json``.

    Returns a managed-file record dict, or ``None`` when the ``hooks`` block is
    absent from ``.claude/settings.json`` (not an error — simply skipped).
    """
    settings_path = target_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return None

    try:
        data: dict = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if "hooks" not in data:
        return None

    content = json.dumps({"hooks": data["hooks"]}, indent=2, ensure_ascii=False) + "\n"
    dest = target_root / ".codex" / "hooks.json"

    # wic is the mirror.write_if_changed callable; call it for idempotency.
    wic(dest, content, check=check)  # type: ignore[call-arg]

    return {
        "path": _rel(dest, target_root),
        "kind": "config",
        "owner": "codex-cli",
    }
