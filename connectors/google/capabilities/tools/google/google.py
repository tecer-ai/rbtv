#!/usr/bin/env python3
"""Launch Google Workspace operations from the component's managed checkout."""

import os
from pathlib import Path
import subprocess
import sys


def main():
    repository = Path(os.environ.get("GOOGLE_TOOLS_ROOT") or
                      Path(__file__).resolve().parents[3] / "repository")
    entry = repository / "gtools.py"
    if not entry.is_file():
        print("google: repository is missing. Run rbtv add connectors/google.", file=sys.stderr)
        return 2
    env = os.environ.copy()
    for start in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        for root in (start, *start.parents):
            if (root / ".rbtv/config/install.json").is_file():
                env.setdefault("GOOGLE_TOOLS_CONFIG", str(root / ".rbtv/config/google/config.yaml"))
                break
        else:
            continue
        break
    return subprocess.call([sys.executable, str(entry), *sys.argv[1:]], env=env)


if __name__ == "__main__":
    sys.exit(main())
