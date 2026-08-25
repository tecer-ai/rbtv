"""config_assets.py — per-model config-dir renderer for the rbtv mirror driver.

Renders the elected worker's config directory (`.codex/`) into a target
workspace by copying its assets tree.  A config-less package (opencode — no
assets seed) is never passed here; the driver skips it.  For the ``codex``
package it additionally generates `.codex/hooks.json` from
`.claude/settings.json` when that file contains a ``hooks`` block; when the
block is absent the file is skipped (not an error).

Public API
----------
``render_config(target_root, package, *, check) -> list[dict]``
    Copy the package's assets tree into ``target_root`` idempotently.
    Returns a list of managed-file records:
        ``{"path": "<target-root-relative posix path>", "kind": "config",
           "owner": "codex-cli"}``

Constraints
-----------
- Source-agnostic: reads NO manifest file.  All inputs come from the
  ``assets/`` subtree living beside ``driver/`` in this ``mirror/`` package.
- Uses ``write_if_changed`` from ``state.py`` for idempotent writes and
  ``--check`` semantics (returns ``"stale"`` without writing in check mode).
- Codex-only: `.codex/hooks.json` is generated from ``.claude/settings.json``
  ``hooks``; absent ``hooks`` block → file silently skipped.
- NO commits.  The conductor commits at wave-close.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from .state import write_if_changed

# ---------------------------------------------------------------------------
# Resolve the assets/ tree, sibling to driver/ in this mirror/ package.  This
# module lives at:
#   ignite/coord/mirror/driver/config_assets.py
# assets live at:
#   ignite/coord/mirror/assets/<name>/
# ---------------------------------------------------------------------------
_DRIVER_DIR = Path(__file__).resolve().parent          # …/mirror/driver/
_MIRROR_DIR = _DRIVER_DIR.parent                       # …/mirror/
_ASSETS_DIR = _MIRROR_DIR / "assets"                   # …/mirror/assets/


# ---------------------------------------------------------------------------
# Supported packages and their assets subtrees
# ---------------------------------------------------------------------------

#: Packages this module knows how to render.  kimi-code-cli's config leg was
#: retired 2026-08-18 (kimi models are reached via opencode instead).
SUPPORTED_PACKAGES: frozenset[str] = frozenset({"codex-cli"})

#: Config-dir name produced in the target workspace for each package.
#: Keys are the package ids; values are the tool's native config-dir name (unchanged).
_CONFIG_DIR: dict[str, str] = {
    "codex-cli": ".codex",
}

#: Assets subdirectory name (under ``assets/``) for each package.
_ASSETS_DIR_NAME: dict[str, str] = {
    "codex-cli": "codex",
}


def _mirror_assets_dir(package: str) -> Path:
    """Absolute path to the assets subtree for *package*."""
    return _ASSETS_DIR / _ASSETS_DIR_NAME[package]


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
    stale_sink: list[str] | None = None,
) -> list[dict[str, str]]:
    """Copy the package's assets tree into *target_root*.

    For the ``codex`` package, also generates ``.codex/hooks.json`` from
    ``.claude/settings.json`` ``hooks`` when present; silently skips when absent.

    Parameters
    ----------
    target_root:
        Absolute path to the target workspace (e.g. the vault root).
    package:
        ``"codex-cli"`` (the only supported package).
    check:
        When ``True`` the function performs a read-only drift check via
        ``write_if_changed``'s check semantics — it returns ``"stale"`` for any
        file that would change without actually writing it.  The returned record
        list is still complete (useful for the driver's ``--check`` mode).
    stale_sink:
        Optional list.  In check mode, every config file found missing or
        differing has its workspace-relative path appended to it, so the caller
        can turn content drift into an exit code.

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
        If the assets directory for *package* does not exist.
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
            f"assets directory not found for package {package!r}: {assets_dir}"
        )

    wic = write_if_changed

    records: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    # 1. Copy every file from assets/<name>/ into target_root (idempotent)
    # ------------------------------------------------------------------
    for src in sorted(assets_dir.rglob("*")):
        if not src.is_file():
            continue
        # Relative path inside assets/<name>/ (e.g. ".codex/config.toml")
        rel_inside = src.relative_to(assets_dir)
        dest = target_root / rel_inside
        content = src.read_text(encoding="utf-8")
        status = wic(dest, content, check=check)
        rel = _rel(dest, target_root)
        if status == "stale" and stale_sink is not None:
            stale_sink.append(rel)
        records.append({
            "path": rel,
            "kind": "config",
            "owner": package,
        })

    # ------------------------------------------------------------------
    # 2. Codex-only: generate .codex/hooks.json from .claude/settings.json
    # ------------------------------------------------------------------
    if package == "codex-cli":
        hooks_record = _render_codex_hooks(
            target_root, check=check, wic=wic, stale_sink=stale_sink
        )
        if hooks_record is not None:
            records.append(hooks_record)

    return records


def _render_codex_hooks(
    target_root: Path,
    *,
    check: bool,
    wic: object,  # write_if_changed callable (state.py)
    stale_sink: list[str] | None = None,
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

    # wic is the state.write_if_changed callable; call it for idempotency.
    status = wic(dest, content, check=check)  # type: ignore[call-arg]

    rel = _rel(dest, target_root)
    if status == "stale" and stale_sink is not None:
        stale_sink.append(rel)

    return {
        "path": rel,
        "kind": "config",
        "owner": "codex-cli",
    }
