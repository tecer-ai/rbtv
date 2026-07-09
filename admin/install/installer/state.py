"""Read and write rbtv.json — persistent state at the target workspace root.

rbtv.json records:
  - rbtv_version: which RBTV version was installed
  - installed_at: ISO timestamp of the last install
  - rbtv_path: relative path from target root to the RBTV source repo
  - modules: list of installed module names
  - installed_files: sorted list of all files written by the installer
  - excluded_components: target paths the user chose to skip (optional)
  - model_packages: orchestration model packages elected for this workspace
    (optional — the single election authority route.py reads; the orchestrating skill
    recalls it on demand via route.py --availability, never baked into the shared repo)
  - model_variants: per-package backend-subset election for CONFIGURABLE packages
    (optional). Shape: {package_id: [variant_id, ...]}. Present ONLY when a proper
    subset of a configurable package's native backends is elected (e.g.
    {"opencode": ["z1", "deepseek-flash"]}); a fully-elected or
    non-configurable package records no entry. The router (route.py) confines an
    elected package to these variants; an absent entry => all variants (back-compat).
  - model_mirror: mirror-driver state for elected worker packages (optional).
    Shape: {excluded_paths: list[str], managed_files: list[{path, kind, owner}],
    last_run: ISO timestamp}.  Written by the driver after a full install or a
    --mirror run; preserved verbatim on any write path that does not update it.
  - env_file: path to the env file holding API keys for orchestration model workers (optional).
  - model_plans_file: path to the YAML file with per-model subscription-plan caps and
    reference $/M-token data (optional; read by the router script for effective context
    windows — graceful skip when absent).
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
    model_packages: list[str] | None = None,
    model_variants: dict[str, list[str]] | None = None,
    model_mirror: dict[str, Any] | None = None,
    env_file: str | None = None,
    model_plans_file: str | None = None,
) -> Path:
    """Write rbtv.json for a full install.

    All installer-owned keys are rebuilt from the supplied arguments.  When
    *model_mirror* is provided (the driver's returned records), it is included
    in the payload as the ``model_mirror`` block so the file carries both
    ``model_packages`` and ``model_mirror`` in one pass.

    Preserves the ``model_mirror`` block from a previous state file when the
    caller omits the argument (``None``): the existing block is read from disk
    and re-emitted unchanged, so a reinstall that does not invoke the driver
    does not silently drop mirror state.
    """
    path = state_path(target_root)

    # Carry forward any existing model_mirror if the caller does not supply one.
    if model_mirror is None:
        existing = read_state(target_root)
        if existing is not None and "model_mirror" in existing:
            model_mirror = existing["model_mirror"]

    # Carry forward any existing env_file if the caller does not supply one.
    if env_file is None:
        existing = read_state(target_root)
        if existing is not None and "env_file" in existing:
            env_file = existing["env_file"]

    # Carry forward any existing model_plans_file if the caller does not supply one.
    if model_plans_file is None:
        existing = read_state(target_root)
        if existing is not None and "model_plans_file" in existing:
            model_plans_file = existing["model_plans_file"]

    payload: dict[str, Any] = {
        "rbtv_version": rbtv_version,
        "installed_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "rbtv_path": rbtv_relative,
        "modules": list(modules),
        "installed_files": sorted(installed_files),
    }
    if env_file is not None:
        payload["env_file"] = env_file
    if model_plans_file is not None:
        payload["model_plans_file"] = model_plans_file
    if excluded_components:
        payload["excluded_components"] = sorted(excluded_components)
    if model_packages is not None:
        payload["model_packages"] = list(model_packages)
    if model_variants:
        payload["model_variants"] = {k: list(v) for k, v in model_variants.items()}
    if model_mirror is not None:
        payload["model_mirror"] = model_mirror
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def update_mirror_state(
    target_root: Path,
    *,
    model_mirror: dict[str, Any],
) -> Path:
    """Patch rbtv.json with a fresh ``model_mirror`` block — mirror-only update.

    Used by the ``--mirror`` path: reads the existing ``rbtv.json``, replaces
    ONLY the ``model_mirror`` key (which includes ``last_run`` inside it), and
    writes the file back.  Every installer-owned key (``rbtv_version``,
    ``installed_at``, ``rbtv_path``, ``modules``, ``installed_files``,
    ``excluded_components``, ``model_packages``) is preserved byte-for-byte.

    Raises ``FileNotFoundError`` if no ``rbtv.json`` exists at *target_root* —
    the caller (``--mirror`` mode in ``cli.py``) is responsible for surfacing
    the error loudly before invoking this function.
    """
    path = state_path(target_root)
    existing_text = path.read_text(encoding="utf-8")
    payload: dict[str, Any] = json.loads(existing_text)
    payload["model_mirror"] = model_mirror
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
