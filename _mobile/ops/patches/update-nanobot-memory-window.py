#!/usr/bin/env python3
"""Set Nanobot memory_window to 20 in config.json. Run on VPS with:
   python3 update-nanobot-memory-window.py /srv/nanobot/.nanobot/config.json
"""
import json
import sys
from pathlib import Path

def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".nanobot" / "config.json"
    if not path.exists():
        print(f"Config not found: {path}", file=sys.stderr)
        sys.exit(1)
    cfg = json.loads(path.read_text())
    cfg.setdefault("agents", {}).setdefault("defaults", {})["memory_window"] = 20
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Updated {path} -> memory_window: 20")

if __name__ == "__main__":
    main()
