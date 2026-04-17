#!/usr/bin/env python3
"""install.py — RBTV standalone installer.

Installs thin loaders into a target workspace that point back to this RBTV source.
Modules are declared in admin/install/module-manifest.yaml.

Usage:
    python install.py --target /path/to/workspace
    python install.py --target /path/to/workspace --modules core,innovation
    python install.py --target /path/to/workspace --non-interactive
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
