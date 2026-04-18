#!/usr/bin/env python3
"""install.py — RBTV standalone installer.

Installs thin loaders (skills, commands) and copies (rules, subagents) into a
target workspace's .claude/ directory, pointing back to this RBTV source repo.

Prerequisite:
    pip install pyyaml          # only external dependency

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

Re-running is safe — previous rbtv-* files are cleared before each install.
Choices are persisted in rbtv.yaml at the target root so re-installs remember
selected modules and excluded components.

Configuration:
    admin/install/defaults.yaml          Version and module availability
    admin/install/module-manifest.yaml   What each module installs

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
