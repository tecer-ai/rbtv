#!/usr/bin/env python3
"""Add a Slack user ID to the Nanobot DM allowlist. Run on VPS with:
   python3 add-allowlist-user.py U0AF08M4MUJ [/srv/nanobot/.nanobot/config.json]
"""
import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: add-allowlist-user.py <SLACK_USER_ID> [config_path]", file=sys.stderr)
        sys.exit(1)

    user_id = sys.argv[1]
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / ".nanobot" / "config.json"

    if not path.exists():
        print(f"Config not found: {path}", file=sys.stderr)
        sys.exit(1)

    cfg = json.loads(path.read_text())
    allow_from = cfg.setdefault("channels", {}).setdefault("slack", {}).setdefault("dm", {}).setdefault("allow_from", [])

    if user_id in allow_from:
        print(f"{user_id} already in allowlist: {allow_from}")
        return

    allow_from.append(user_id)
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Added {user_id} to allowlist: {allow_from}")

if __name__ == "__main__":
    main()
