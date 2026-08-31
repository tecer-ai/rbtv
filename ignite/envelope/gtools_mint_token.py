#!/usr/bin/env python3
"""Mint a short-lived Google OAuth access token for one gtools account, print it, exit.

Daemon-side only — this script must never run inside a cage. It imports gtools' OWN,
already-tested OAuth refresh code (`gtools/scripts/auth.py#get_credentials`) rather than
re-implementing Google's token-refresh handshake a second time. `get_credentials` reads,
uses, and (on refresh) re-writes the account's `token.json` — including its refresh_token —
entirely inside that call; this script never reads, prints, or forwards the refresh_token.
Only `access_token` and its expiry reach stdout, which is exactly what
`ignite/envelope/gtools-token-minter.js` relays back across the broker socket.

Usage: gtools_mint_token.py --gtools-root <path> --account <name>
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gtools-root", required=True, help="the gtools tool root (holds config.yaml, credentials/)")
    parser.add_argument("--account", required=True)
    args = parser.parse_args()

    gtools_root = Path(args.gtools_root).resolve()
    scripts_dir = gtools_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import auth  # gtools/scripts/auth.py — imported, never duplicated (coding.md: no duplicate source)

    config = auth.load_config()
    try:
        creds = auth.get_credentials(args.account, config)
    except SystemExit as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    if not creds or not creds.valid:
        print(json.dumps({"error": "credentials not valid after refresh"}), file=sys.stderr)
        sys.exit(1)

    expiry = (creds.expiry.isoformat() + "Z") if creds.expiry else None
    print(json.dumps({"access_token": creds.token, "expiry": expiry}))


if __name__ == "__main__":
    main()
