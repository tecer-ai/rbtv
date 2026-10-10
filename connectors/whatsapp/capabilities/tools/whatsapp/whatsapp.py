#!/usr/bin/env python3
"""Run wacli, the WhatsApp command-line client, on this installation's store."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PAGE = Path(__file__).resolve().with_suffix(".md")


def installation_root():
    """The first folder, from the working folder upward, holding the installation record."""
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if (folder / ".rbtv/config/install.json").is_file():
            return folder
    sys.exit("whatsapp: no-installation\n"
             "  why: no folder from the working folder upward holds .rbtv/config/install.json\n"
             "  fix: run whatsapp from inside an installation")


def main():
    wacli = shutil.which("wacli")
    if wacli is None:
        sys.exit("whatsapp: wacli-missing\n"
                 "  why: the wacli program is not on PATH\n"
                 f"  fix: install it as {PAGE} says, then run: whatsapp doctor")
    os.environ.setdefault("WACLI_STORE_DIR", str(installation_root() / ".rbtv/runtime/whatsapp"))
    # Not os.execv: on Windows it detaches the child from the console.
    sys.exit(subprocess.call([wacli, *sys.argv[1:]]))


if __name__ == "__main__":
    main()
