#!/usr/bin/env python3
"""Update Nanobot config model to claude-opus-4-6. Run on VPS with:
   python3 update-nanobot-model.py /srv/nanobot/.nanobot/config.json
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
    cfg.setdefault("agents", {}).setdefault("defaults", {})["model"] = "claude-opus-4-6"
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Updated {path} -> model: claude-opus-4-6")

if __name__ == "__main__":
    main()
