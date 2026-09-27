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
  4. The target is EXECUTABLE afterwards — asserted, not assumed. The mode is carried from the live
     file before the replace, and if the live file's own mode was already broken the exec bits are
     restored and the repair is announced. `import` passing is not runnability: a 0644 coord.py
     imports perfectly and hands every seat "Permission denied".
  5. The target's bytes equal the bytes that were gated — proof the replace landed what was checked.
  6. The candidate is not BEHIND the target — the one check that reads the target at all, and the
     only one that is about the work already in the file rather than the health of the new one.
It does NOT run `coord.py selftest` — that takes minutes and is the DONE gate, not the SAVE gate. Run
it yourself after saving.

USAGE
  save-coord.py --candidate NEW.py [--target /abs/path/coord.py]   # gate, then replace
  save-coord.py --check FILE                                       # gate only, change nothing
  save-coord.py --candidate NEW.py --force                         # ...after merging onto current
Exit 0 = gated (and replaced, unless --check). Exit 1 = REFUSED, target untouched, candidate kept.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
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


def stamp(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"


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
    ap.add_argument("--force", action="store_true",
                    help="install a candidate OLDER than the target anyway — only after you have "
                         "merged your change onto the current file")
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

    # The gate above scores the CANDIDATE and nothing else — it never opens the target. So a
    # candidate branched from an OLDER coord.py imports cleanly, builds its parser cleanly, and is
    # installed over work it does not contain, with SAVED printed as it lands. Measured 2026-08-11:
    # the live coord.py carried 259 uncommitted insertions of a parallel session's work; the
    # candidate sitting beside it, branched two hours earlier, carried none of them. One save would
    # have destroyed all of it and reported success. Nothing else in this file looks at the target's
    # content or age, so nothing else could have caught it.
    #
    # This refusal deliberately does NOT reuse the gate-failure wording above. There the candidate
    # is broken and the news is "the live coord.py is untouched"; here the candidate is fine and
    # merely BEHIND, and the remedy is a merge — different fact, different fix, different words.
    #
    # A stale SIBLING candidate this run was not pointed at is deliberately NOT warned about. The
    # gate can only install the file it was named, so a candidate nobody names destroys nothing;
    # finding siblings would need a filename convention this gate does not own (two spellings are
    # live in this folder right now, `coord-candidate.py` and `coord-candidate-d8c.py`); and a
    # warning the reader is never required to act on is how readers learn to skip the line that
    # matters. The check fires where the damage is — on the file actually being installed.
    #
    # ponytail: mtime, not content ancestry — misses a sub-second race and a candidate touched
    # after branching. Upgrade path: candidate carries its base sha256 in a header line.
    if target.is_file() and not args.force:
        t_at, s_at = os.stat(target).st_mtime, os.stat(src).st_mtime
        if t_at > s_at:
            print(f"REFUSED: STALE CANDIDATE — {target} was modified AFTER {src} was written, so "
                  f"installing it would silently drop everything that changed in between.\n"
                  f"  target    {stamp(t_at)}  {target}\n"
                  f"  candidate {stamp(s_at)}  {src}\n"
                  f"Diff them first (`diff {target.name} {src.name}`), merge your change onto the "
                  f"CURRENT {target.name}, and retry. `--force` installs it as-is and is only "
                  f"correct once that merge is done.", file=sys.stderr)
            return 1

    # The target's MODE is part of it working. `coordinate` on this box is a symlink to coord.py
    # and is executed directly, so a candidate written by a text editor (0644) silently strips the
    # exec bit and every seat gets "Permission denied" — the same total messaging outage G-45 caused,
    # through a different door. Found the hard way: this gate did exactly that on its first real
    # save, 2026-07-27. The mode is carried over BEFORE the replace, never after, so no reader can
    # observe a non-executable coord.py even for an instant.
    # Read the gated bytes BEFORE any chmod: carrying a target mode that denies reads would
    # otherwise make the gate unable to read its own candidate.
    gated_bytes = src.read_bytes()

    try:
        mode = os.stat(target).st_mode & 0o7777
        os.chmod(src, mode)
    except OSError as err:
        print(f"REFUSED: cannot read/carry the target's mode ({err}) — replacing anyway could "
              f"strip the exec bit and take messaging down for every seat.", file=sys.stderr)
        return 1

    # CARRYING the mode is not the same as the result being RUNNABLE, and the difference is not
    # theoretical: on 2026-07-27 22:41 a hand-rolled save left the live coord.py at 0644, and every
    # seat's bare `coordinate` returned "Permission denied". Gate that state and the mode carried
    # forward is the BROKEN one — measured: the gate printed SAVED, exit 0, over a file os.access
    # said was unrunnable. Refusing here would be worse than useless, because that is exactly the
    # state you are trying to save a fix over. So the exec bits are RESTORED and the repair is
    # announced: `chmod +X` semantics — x wherever r is already granted — never a hardcoded 0o755,
    # which would one day silently "fix" a mode somebody meant.
    repaired = ""
    if not (mode & 0o111):
        mode |= (mode & 0o444) >> 2
        os.chmod(src, mode)
        repaired = (f"\n  ⚠ the TARGET's own mode was NOT executable — repaired to {oct(mode)}. "
                    f"Something saved over it without carrying the mode; that is the outage shape.")

    os.replace(src, target)

    # The two assertions no syntax, import or parser check can substitute for. They run AFTER the
    # replace because that is the only moment the claim "the room can run this" is about the file
    # the room will actually run. A failure here has already installed the file, so it is reported
    # LOUDLY with the remedy — never as SAVED.
    if not os.access(target, os.X_OK):
        print(f"⚠⚠ REPLACED BUT NOT RUNNABLE: {target} is not executable ({oct(os.stat(target).st_mode & 0o7777)}). "
              f"`coordinate` is a symlink to it, so EVERY seat now gets 'Permission denied'. "
              f"Fix now: chmod +x {target}", file=sys.stderr)
        return 1
    if target.read_bytes() != gated_bytes:
        print(f"⚠⚠ REPLACED BUT NOT THE CANDIDATE: {target} does not match the bytes that were "
              f"gated. Something else wrote it between the gate and the replace. Nothing here is "
              f"trustworthy — re-check the file before the room uses it.", file=sys.stderr)
        return 1

    print(f"SAVED: {target} replaced atomically (import OK, parser build OK, mode {oct(mode)} "
          f"carried over, target verified EXECUTABLE and byte-identical to the gated candidate)."
          f"{repaired}\nNow run `{target} selftest` — the save gate is not the done gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
