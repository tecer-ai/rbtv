"""Path context for RBTV install."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstallContext:
    """Resolved paths and choices for a single install run.

    Per D7 (2026-04-17): output paths are NOT part of install context.
    They are resolved at runtime by components following the rbtv-output-resolution
    rule, which reads `## File Routing` blocks from workspace CLAUDE.md files.
    """
    rbtv_root: Path
    target_root: Path
    rbtv_relative: Path
    modules_selected: tuple[str, ...]


def _normcase_path(p: Path) -> Path:
    """Windows-friendly normalization. No-op on POSIX."""
    if os.name == "nt":
        return Path(os.path.normcase(os.path.normpath(str(p))))
    return p


def resolve_from_cli(
    target: Path,
    rbtv_path: Path,
    modules: tuple[str, ...],
) -> InstallContext:
    target_abs = target.resolve()
    rbtv_abs = rbtv_path.resolve()
    # O1: normalize case on Windows for the CONTAINMENT CHECK only.
    # The returned rbtv_relative preserves original case (filesystems are
    # case-insensitive on Windows but display case matters for human reading).
    target_norm = _normcase_path(target_abs)
    rbtv_norm = _normcase_path(rbtv_abs)
    if not str(rbtv_norm).startswith(str(target_norm) + os.sep) and rbtv_norm != target_norm:
        raise ValueError(
            f"RBTV repo must live inside the target workspace.\n"
            f"  rbtv: {rbtv_abs}\n"
            f"  target: {target_abs}"
        )
    # Compute relative path from original (case-preserving) absolute paths.
    rbtv_rel = Path(os.path.relpath(rbtv_abs, target_abs))
    return InstallContext(
        rbtv_root=rbtv_abs,
        target_root=target_abs,
        rbtv_relative=rbtv_rel,
        modules_selected=modules,
    )
