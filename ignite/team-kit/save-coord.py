#!/usr/bin/env python3
"""save-coord.py — the IMPORT-LEVEL save gate for coord.py (campaign issue S-4(a), run issue G-45).

WHY THIS EXISTS, and why a syntax check is not it.
--------------------------------------------------
coord.py is the ONLY communications path between every seat in a room. It is read fresh on every
invocation and has no fallback. On 2026-07-27 a mid-edit save left a name referenced before its
definition; `ast.parse` reported SYNTAX OK on that exact file, and every `coordinate` command — send,
read, status, launch, close — died for every seat at once, including every recovery path, which all
run THROUGH this file. A syntax gate passes the failure that actually happened.

The gate that works is a REAL IMPORT plus a REAL PARSER BUILD, then an atomic replace. This script is
that gate as a MECHANISM rather than a discipline, and it deliberately lives OUTSIDE coord.py: a
broken coord.py cannot be asked to validate itself.

WHY IT MUST BE A SUBPROCESS. Importing executes the candidate's module body. Doing that in this
process would leave the checker holding whatever state that body created, and a candidate that called
sys.exit() at import would take the checker down with it — reporting nothing.

WHAT IT PROVES, exactly (say what you scored over):
  1. `import coord` on the CANDIDATE succeeds — the module body executes to completion under the
     candidate's own directory on sys.path. This is the check ast.parse cannot make.
  2. `python3 <candidate> --help` exits 0 — the full parser tree, every subparser included, is built.
     argparse construction is where G-45 actually died, and it happens after the module body.
  3. Only then is the file moved into place with os.replace(), which is atomic on the same
     filesystem: no reader ever observes a half-written coord.py.
It does NOT run `coord.py selftest` — that takes minutes and is the DONE gate, not the SAVE gate. Run
it yourself after saving.

USAGE
  save-coord.py --candidate NEW.py [--target /abs/path/coord.py]   # gate, then replace
  save-coord.py --check FILE                                       # gate only, change nothing
Exit 0 = gated (and replaced, unless --check). Exit 1 = REFUSED, target untouched, candidate kept.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_TARGET = Path(__file__).resolve().parent / "coord.py"

# The module body is executed exactly as `import coord` executes it — same module name, same
# directory on sys.path — because "it imports" must mean the thing the room actually does.
IMPORT_SNIPPET = (
    "import importlib.util, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "spec = importlib.util.spec_from_file_location('coord', sys.argv[2])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "sys.modules['coord'] = mod\n"
    "spec.loader.exec_module(mod)\n"
)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)


def gate(candidate: Path, target_dir: Path):
    """(ok, [failure lines]). Both checks always run so a caller sees every failure at once."""
    failures = []

    r = run([sys.executable, "-c", IMPORT_SNIPPET, str(target_dir), str(candidate)])
    if r.returncode != 0:
        failures.append("IMPORT FAILED — the module body does not execute. Every `coordinate` "
                        "command would fail for every seat at once:\n"
                        + (r.stderr.strip() or r.stdout.strip() or "(no output)"))

    r = run([sys.executable, str(candidate), "--help"])
    if r.returncode != 0:
        failures.append("PARSER BUILD FAILED — `--help` exits %d, so argparse construction dies "
                        "before any command dispatches (this is the exact G-45 shape):\n%s"
                        % (r.returncode, r.stderr.strip() or r.stdout.strip() or "(no output)"))

    return (not failures), failures


def main():
    ap = argparse.ArgumentParser(
        description="Import-level save gate for coord.py — import + parser build, then atomic replace.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--candidate", help="the new coord.py to gate and, if it passes, move into place")
    g.add_argument("--check", help="gate this file and report; never move anything")
    ap.add_argument("--target", default=str(DEFAULT_TARGET),
                    help=f"the coord.py to replace (default: {DEFAULT_TARGET})")
    args = ap.parse_args()

    src = Path(args.candidate or args.check).resolve()
    if not src.is_file():
        print(f"REFUSED: no such file: {src}", file=sys.stderr)
        return 1

    target = Path(args.target).resolve()
    ok, failures = gate(src, target.parent)
    if not ok:
        print(f"REFUSED — {src} is NOT safe to save over {target}. It was NOT moved; the live "
              f"coord.py is untouched.", file=sys.stderr)
        for f in failures:
            print("\n  " + f.replace("\n", "\n  "), file=sys.stderr)
        return 1

    if args.check:
        print(f"GATED (check only): {src} imports cleanly and builds its parser. Nothing moved.")
        return 0

    if src.parent != target.parent:
        print(f"REFUSED: candidate {src} and target {target} are in different directories, so "
              f"os.replace() is not guaranteed atomic across them.\nWrite the candidate beside "
              f"the target and retry.", file=sys.stderr)
        return 1

    # The target's MODE is part of it working. `coordinate` on this box is a symlink to coord.py
    # and is executed directly, so a candidate written by a text editor (0644) silently strips the
    # exec bit and every seat gets "Permission denied" — the same total messaging outage G-45 caused,
    # through a different door. Found the hard way: this gate did exactly that on its first real
    # save, 2026-07-27. The mode is carried over BEFORE the replace, never after, so no reader can
    # observe a non-executable coord.py even for an instant.
    try:
        mode = os.stat(target).st_mode & 0o7777
        os.chmod(src, mode)
    except OSError as err:
        print(f"REFUSED: cannot read/carry the target's mode ({err}) — replacing anyway could "
              f"strip the exec bit and take messaging down for every seat.", file=sys.stderr)
        return 1

    os.replace(src, target)
    print(f"SAVED: {target} replaced atomically (import OK, parser build OK, mode {oct(mode)} "
          f"carried over). Now run `{target} selftest` — the save gate is not the done gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
