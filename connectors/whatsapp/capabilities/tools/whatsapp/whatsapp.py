#!/usr/bin/env python3
"""Run wacli, the WhatsApp command-line client, on this installation's store."""

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path


PAGE = Path(__file__).resolve().with_suffix(".md")
TRIMMED = ("--message", "--caption")


def installation_root():
    """The first folder, from the working folder upward, holding the installation record."""
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if (folder / ".rbtv/config/install.json").is_file():
            return folder
    sys.exit("whatsapp: no-installation\n"
             "  why: no folder from the working folder upward holds .rbtv/config/install.json\n"
             "  fix: run whatsapp from inside an installation")


def trim_outgoing(arguments):
    """On a send, the message text and caption without trailing whitespace: a text file's final
    newline otherwise reaches the recipient as a blank last line."""
    if "send" not in arguments:
        return list(arguments)
    trimmed, pending = [], False
    for argument in arguments:
        if pending:
            trimmed.append(argument.rstrip())
            pending = False
            continue
        name, equals, value = argument.partition("=")
        if name in TRIMMED and equals:
            trimmed.append(f"{name}={value.rstrip()}")
        else:
            trimmed.append(argument)
            pending = argument in TRIMMED
    return trimmed


def run_wacli(arguments):
    """Run wacli and stay responsible for the process this wrapper started.

    A stop signal is forwarded to wacli and the wrapper exits only after wacli is gone, so a
    caller that awaits this wrapper's exit has awaited the whole tree (leaving wacli orphaned
    kept a stopped sync alive).
    """
    wacli = shutil.which("wacli")
    if wacli is None:
        sys.exit("whatsapp: wacli-missing\n"
                 "  why: the wacli program is not on PATH\n"
                 f"  fix: install it as {PAGE} says, then run: whatsapp doctor")
    child = subprocess.Popen([wacli, *arguments])

    def hand_off(signum, frame):
        if child.poll() is None:
            child.terminate()

    for name in ("SIGTERM", "SIGINT", "SIGHUP"):
        number = getattr(signal, name, None)
        if number is None:
            continue
        try:
            signal.signal(number, hand_off)
        except (OSError, ValueError):
            pass
    try:
        return child.wait()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


def names_store(arguments):
    """Whether the caller already named the store, so no installation needs to be found."""
    return "WACLI_STORE_DIR" in os.environ or any(a == "--store" or a.startswith("--store=") for a in arguments)


def main():
    arguments = trim_outgoing(sys.argv[1:])
    if not names_store(arguments):
        os.environ["WACLI_STORE_DIR"] = str(installation_root() / ".rbtv/runtime/whatsapp")
    # Not os.execv: on Windows it detaches the child from the console.
    sys.exit(run_wacli(arguments))


if __name__ == "__main__":
    main()
