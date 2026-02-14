#!/usr/bin/env python3
"""Set Nanobot workspace path to /opt/robotville/BMAD so bootstrap files
(AGENTS.md, SOUL.md, TOOLS.md, USER.md) and skills/ are loaded from the
correct location. Run on VPS with:
   python3 fix-nanobot-workspace.py /srv/nanobot/.nanobot/config.json
"""
import json
import sys
from pathlib import Path

WORKSPACE_PATH = "/opt/robotville/BMAD"

def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".nanobot" / "config.json"
    if not path.exists():
        print(f"Config not found: {path}", file=sys.stderr)
        sys.exit(1)

    cfg = json.loads(path.read_text())
    defaults = cfg.setdefault("agents", {}).setdefault("defaults", {})

    old_workspace = defaults.get("workspace", "~/.nanobot/workspace (default)")
    defaults["workspace"] = WORKSPACE_PATH

    path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Updated {path}")
    print(f"  workspace: {old_workspace} -> {WORKSPACE_PATH}")

if __name__ == "__main__":
    main()
