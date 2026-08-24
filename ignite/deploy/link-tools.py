#!/usr/bin/env python3
"""link-tools — put the team-kit's bare-name commands on PATH, idempotently.

The team-kit tools are NAMED as bare commands by things that cannot see this repo's layout:
`module.md`'s "Reach it" column says `coordinate -h`, and the channel/console master prompts
(`.rbtv/mirror/meta/master/prompts/`) say `owed-answers`. On the ignite VPS those names
resolved only because someone made `~/.local/bin` symlinks BY HAND — nothing created them, so a
redeploy or a second machine leaves the name unresolvable and every caller falls back to the slow
manual path it was built to delete (measured 2026-08-12: ~120 s vs ~0.15 s for `owed-answers`).

This is that missing deploy step. Run it after cloning the repo on a box:

    python3 ignite/deploy/link-tools.py            # create/repair the links
    python3 ignite/deploy/link-tools.py --check    # report only, write nothing (exit 1 if stale)

Idempotent: a link already pointing at the right target is left untouched and reported `ok`. A
symlink pointing elsewhere is repaired. A REGULAR FILE with one of these names is never clobbered —
that is somebody else's binary and the step refuses loudly rather than deleting it.

Scope is the ignite team-kit ONLY. Other repos' PATH names (`rbtv`, `teamview`, `acct`, `sb-task`,
`sd-graph`) have the same gap and their own owners; each module exposes its own.
"""
import argparse
import os
import pathlib
import sys

KIT = pathlib.Path(__file__).resolve().parent.parent / "team-kit"

# bare name on PATH -> the file in team-kit/ it must resolve to
TOOLS = {
    "coordinate": "coord.py",
    "scaffold-seats": "materialize-seats.py",
    "owed-answers": "owed-answers.py",
    "tmux-overview": "tmux-overview",
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
        state, note = link(bindir, name, KIT / filename, args.check)
        bad = bad or state in ("stale", "REFUSED", "MISSING-TARGET")
        print(f"{state:>14}  {name}  {note}")

    if str(bindir) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"\n⚠ {bindir} is not on this shell's PATH — the names will not resolve until it is.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
