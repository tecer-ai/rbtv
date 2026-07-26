#!/usr/bin/env python3
"""install.py — RBTV standalone installer.

Installs thin loaders (skills, commands) and copies (rules, subagents) into a
target workspace's .claude/ directory, pointing back to this RBTV source repo.

No external dependencies — Python 3.11+ only.

Interactive mode (recommended for first install):
    python install.py

    Prompts for:
      1. Target workspace path
      2. Module selection (arrow keys + space to toggle, 'i' to view contents)
      3. Optional per-component customization

Scripted / CI mode:
    python install.py --target /path/to/workspace
    python install.py --target /path/to/workspace --modules core,innovation
    python install.py --target /path/to/workspace --non-interactive

Mirror-only mode (refresh worker guidance artifacts, no component install):
    python install.py --mirror [--target /path/to/workspace]
    python install.py --mirror --check [--target /path/to/workspace]
    python install.py --mirror --exclude 4-archives 5-workbench/vendor
    python install.py --mirror --uninstall [--target /path/to/workspace]

    --mirror re-renders the mirror artifacts (worker guidance files, the shared
    .agents/ library, per-model config dirs) for the model packages already
    recorded in rbtv.json, skipping the target/module/component prompts. The
    target resolves from --target, else the nearest rbtv.json walking upward
    from the current directory.

    --check applies ONLY with --mirror: a read-only drift probe that writes
    NOTHING. It names every managed file that is missing or has fallen behind
    its source, then exits 1 when the mirror is out of sync and 0 when it is
    current — so CI and pre-flight checks can gate on it. Answers "is my mirror
    current?"; a plain --mirror run is what makes it current. Mirrors are
    gitignored and refresh only when this installer runs, so drift is
    per-machine and invisible to git — nothing else will tell you.

    --exclude PATH [PATH ...] takes workspace-root-relative posix paths the
    mirror skips — no guidance file is rendered beside any CLAUDE.md inside an
    excluded path, and an already-mirrored excluded path has its generated
    guidance files deleted (hand-authored files are spared). Passing --exclude
    REPLACES the list recorded in rbtv.json (model_mirror.excluded_paths);
    omitting it PRESERVES it. Applies on both a full install and --mirror.

    --uninstall applies ONLY with --mirror: a full mirror teardown that removes
    every generated mirror artifact for the target and clears the model_mirror
    block from rbtv.json.

Re-running is safe — previous rbtv-* files are cleared before each install.
Choices are persisted in rbtv.json at the target root so re-installs remember
selected modules and excluded components.

Configuration:
    admin/install/defaults.json          Installer version (modules come from the manifest)
    admin/install/module-manifest.json   What each module installs

"""
from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_import_path() -> None:
    repo_root = Path(__file__).resolve().parent
    installer_parent = repo_root / "admin" / "install"
    if str(installer_parent) not in sys.path:
        sys.path.insert(0, str(installer_parent))


def main() -> int:
    _bootstrap_import_path()
    from installer.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
