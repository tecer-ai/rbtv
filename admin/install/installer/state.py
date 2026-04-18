"""Read and write rbtv.json — persistent state at the target workspace root.

rbtv.json records:
  - rbtv_version: which RBTV version was installed
  - installed_at: ISO timestamp of the last install
  - rbtv_path: relative path from target root to the RBTV source repo
  - modules: list of installed module names
  - installed_files: sorted list of all files written by the installer
  - excluded_components: target paths the user chose to skip (optional)
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any


STATE_FILENAME = "rbtv.json"


def state_path(target_root: Path) -> Path:
    return target_root / STATE_FILENAME


def read_state(target_root: Path) -> dict[str, Any] | None:
    path = state_path(target_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def find_state_upward(start: Path) -> tuple[Path, dict[str, Any]] | None:
    """Walk from *start* toward the filesystem root looking for rbtv.json.

    Returns ``(directory, parsed_state)`` for the first match, or ``None``.
    """
    current = start.resolve()
    for directory in [current] + list(current.parents):
        state = read_state(directory)
        if state is not None:
            return directory, state
    return None


def write_state(
    target_root: Path,
    *,
    rbtv_version: str,
    rbtv_relative: str,
    modules: tuple[str, ...],
    installed_files: list[str],
    excluded_components: set[str] | None = None,
) -> Path:
    """Write rbtv.json."""
    path = state_path(target_root)
    payload: dict[str, Any] = {
        "rbtv_version": rbtv_version,
        "installed_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "rbtv_path": rbtv_relative,
        "modules": list(modules),
        "installed_files": sorted(installed_files),
    }
    if excluded_components:
        payload["excluded_components"] = sorted(excluded_components)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
