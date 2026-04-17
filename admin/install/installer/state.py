"""Read and write rbtv.yaml (user choices + installed_files list preserved across installs)."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

import yaml


STATE_FILENAME = "rbtv.yaml"


def state_path(target_root: Path) -> Path:
    return target_root / STATE_FILENAME


def read_state(target_root: Path) -> dict[str, Any] | None:
    path = state_path(target_root)
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_state(
    target_root: Path,
    *,
    rbtv_version: str,
    rbtv_relative: str,
    modules: tuple[str, ...],
    installed_files: list[str],
) -> Path:
    """Write rbtv.yaml. Per D7, no output_paths section.
    Per O3, installed_files is tracked so re-installs remove only the
    previous-install files (not all rbtv-prefixed files)."""
    path = state_path(target_root)
    payload = {
        "rbtv_version": rbtv_version,
        "installed_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "rbtv_path": rbtv_relative,
        "modules": list(modules),
        "installed_files": sorted(installed_files),
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path
