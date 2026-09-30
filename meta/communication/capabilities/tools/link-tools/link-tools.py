#!/usr/bin/env python3
"""link-tools — put this component's bare-name CLI on PATH, idempotently.

`audio` (the `capabilities/tools/audio/` tool) is reached bare-name by callers that
have `~/.local/bin` on PATH. Nothing in this repo created that symlink: a manual,
per-box link did not survive as repo state — a rebuild or a second machine leaves
the name unresolvable and every caller falls back to exit 127.

This is that missing step, scoped to THIS component. It does not link any other
module's tools.

Run it after cloning the repo on a box:

    python3 meta/communication/capabilities/tools/link-tools/link-tools.py            # create/repair the links
    python3 meta/communication/capabilities/tools/link-tools/link-tools.py --check    # report only, write nothing (exit 1 if stale)

Idempotent: a link already pointing at the right target is left untouched and reported `ok`. A
symlink pointing elsewhere is repaired. A REGULAR FILE with one of these names is never clobbered —
that is somebody else's binary and the step refuses loudly rather than deleting it.
"""
import argparse
import os
import pathlib
import sys

COMPONENT = pathlib.Path(__file__).resolve().parents[3]

# bare name on PATH -> the component-relative file it must resolve to.
TOOLS = {
    "audio": "capabilities/tools/audio/audio.py",
}


def link(bindir, name, target, check):
    """Return (state, note). States: ok | linked | relinked | stale | REFUSED | MISSING-TARGET."""
    if not target.exists():
        return "MISSING-TARGET", str(target)
    path = bindir / name
    if path.is_symlink():
        if path.readlink() == target:
            return "ok", str(target)
        if check:
            return "stale", f"{path.readlink()} -> {target}"
        path.unlink()
        path.symlink_to(target)
        return "relinked", str(target)
    if path.exists():  # a real file, not ours
        return "REFUSED", f"{path} exists and is not a symlink"
    if check:
        return "stale", f"absent -> {target}"
    path.symlink_to(target)
    return "linked", str(target)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only; write nothing (exit 1 if any link is stale)")
    ap.add_argument("--bindir", default=None, help="target dir (default: $HOME/.local/bin)")
    args = ap.parse_args()

    bindir = pathlib.Path(args.bindir) if args.bindir else pathlib.Path.home() / ".local" / "bin"
    if not args.check:
        bindir.mkdir(parents=True, exist_ok=True)

    bad = False
    for name, filename in sorted(TOOLS.items()):
        state, note = link(bindir, name, COMPONENT / filename, args.check)
        bad = bad or state in ("stale", "REFUSED", "MISSING-TARGET")
        print(f"{state:>14}  {name}  {note}")

    if str(bindir) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"\n⚠ {bindir} is not on this shell's PATH — the names will not resolve until it is.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
