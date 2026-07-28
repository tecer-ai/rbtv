#!/usr/bin/env python3
"""probe-save-gate.py — proves save-coord.py catches the failure ast.parse cannot (S-4(a) / G-45).

WHAT THIS SCORES OVER, stated so "probes pass" is never read as a clean class:
  · the LIVE coord.py beside it (must gate clean),
  · a mutant carrying the EXACT G-45 shape — a module-level NameError — which `ast.parse` reports
    as SYNTAX OK. This probe asserts BOTH halves: ast.parse says OK *and* the gate says REFUSED.
    Without that contrast the probe would not show what the gate adds.
  · a mutant that imports fine but whose PARSER BUILD dies (argparse construction), because G-45's
    real death was after the module body,
  · that a REFUSED candidate leaves the target file byte-identical,
  · that a PASSING candidate is actually moved into place, atomically.
It does NOT score coord.py's behaviour — that is `coord.py selftest`.

Every mutant lives in a temp directory and every subprocess runs with HOME pointed inside it (G-75:
a mutation test runs the mutant with the full write authority of the real program; a seat that
mutated a destination path this way destroyed the owner's global settings file on 2026-07-27).

Run: python3 probe-save-gate.py     ->  exit 0 all green, exit 1 on any failure.
"""

import ast
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAVE_COORD = HERE.parent / "save-coord.py"
LIVE_COORD = HERE.parent / "coord.py"

RESULTS = []


def check(label, cond):
    RESULTS.append((bool(cond), label))
    print(("ok    " if cond else "FAIL  ") + label)


def run(argv, home):
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(Path(home) / ".config"))
    return subprocess.run(argv, capture_output=True, text=True, timeout=180, env=env)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    if not SAVE_COORD.is_file():
        print(f"FAIL  save-coord.py not found at {SAVE_COORD}")
        return 1

    live_src = LIVE_COORD.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="probe-save-gate-") as td:
        td = Path(td)
        home = td / "home"
        home.mkdir()
        work = td / "kit"
        work.mkdir()

        # ⚠ THE STAND-IN KIT MUST CARRY coord.py'S SIBLINGS, NOT ONLY coord.py. Since task 7.82
        # coord.py imports budget.py at module level (the one reader of the run's declared floor),
        # so a lone copy in an empty directory dies at import with ModuleNotFoundError — and this
        # probe would then report "the LIVE coord.py fails the gate", blaming production for the
        # probe's own incomplete fixture. Measured: that is exactly the 10-failure red of 17:00.
        # The live file gates clean where it actually lives (`save-coord.py --check coord.py`
        # exits 0); what changed is that a CANDIDATE now needs its siblings beside it.
        shutil.copy2(HERE.parent / "budget.py", work / "budget.py")

        # A stand-in target: a COPY of the live coord.py, so nothing here can touch the real one.
        target = work / "coord.py"
        target.write_text(live_src, encoding="utf-8")
        target_sha = sha(target)

        # ---- 1 · the live file gates clean ---------------------------------
        r = run([sys.executable, str(SAVE_COORD), "--check", str(target)], home)
        check("the LIVE coord.py passes the gate (import + parser build)", r.returncode == 0)

        # ---- 2 · the G-45 shape: module-level NameError, syntactically valid ----
        mutant = work / "mutant-nameerror.py"
        mutant.write_text(live_src + "\n\nBROADCAST_CLAUSES_MISSPELLED_AT_MODULE_LEVEL = "
                                     "UNDEFINED_NAME_THE_EDIT_HAD_NOT_WRITTEN_YET\n",
                          encoding="utf-8")
        try:
            ast.parse(mutant.read_text(encoding="utf-8"))
            parses = True
        except SyntaxError:
            parses = False
        check("the G-45 mutant is SYNTACTICALLY VALID — ast.parse reports OK on it "
              "(this is why a syntax-only gate passed the outage)", parses)

        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(mutant),
                 "--target", str(target)], home)
        check("the gate REFUSES that same mutant (exit 1)", r.returncode == 1)
        check("the refusal names the import failure, not a syntax one",
              "IMPORT FAILED" in r.stderr)
        check("a REFUSED candidate leaves the target BYTE-IDENTICAL", sha(target) == target_sha)
        check("a REFUSED candidate is not consumed — it is still on disk to fix", mutant.is_file())

        # ---- 3 · imports fine, parser build dies ---------------------------
        # Appending to the module body would run at import; this instead breaks parser
        # CONSTRUCTION, which happens later — the half a bare import check would miss.
        pmut = work / "mutant-parser.py"
        pmut.write_text(
            live_src.replace('p = argparse.ArgumentParser(', 'p = argparse.NoSuchParser(', 1),
            encoding="utf-8")
        broke_parser = 'argparse.NoSuchParser(' in pmut.read_text(encoding="utf-8")
        check("the parser mutant was actually constructed (the string it targets exists)",
              broke_parser)
        r = run([sys.executable, str(SAVE_COORD), "--check", str(pmut)], home)
        check("the gate REFUSES a candidate whose PARSER BUILD dies though the module imports",
              r.returncode == 1 and "PARSER BUILD FAILED" in r.stderr)

        # ---- 4 · a clean candidate is moved into place ---------------------
        # The target is EXECUTABLE, as the real coord.py is (`coordinate` is a symlink executed
        # directly). The candidate is 0644, as any editor writes it. A gate that replaces without
        # carrying the mode strips the exec bit and every seat gets "Permission denied" — the same
        # total messaging outage, through a different door. This gate did exactly that on its first
        # real save; the check below is why it cannot again.
        os.chmod(target, 0o755)
        good = work / "candidate-good.py"
        good.write_text(live_src + "\n# a harmless trailing comment\n", encoding="utf-8")
        os.chmod(good, 0o644)
        good_sha = sha(good)
        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(good),
                 "--target", str(target)], home)
        check("a CLEAN candidate is accepted (exit 0)", r.returncode == 0)
        check("...and is now the target, byte for byte", sha(target) == good_sha)
        check("...and the candidate path is gone (moved, not copied)", not good.exists())
        check("...and the target is STILL EXECUTABLE — a 0644 candidate must not strip the exec "
              "bit and hand every seat 'Permission denied'",
              os.stat(target).st_mode & 0o111 == 0o111)

        # ---- 4b · the target's OWN mode is already broken (the 22:41 shape) ----
        # Leg 4 proves a 0644 CANDIDATE cannot strip the bit. This is the other direction, and it
        # is the one that shipped: when the LIVE file is already 0644 — exactly the state a
        # hand-rolled save left the room in on 2026-07-27 22:41 — carrying its mode forward
        # faithfully installs the outage. The pre-fix gate printed SAVED and exited 0 over a file
        # os.access(X_OK) said was unrunnable: a gate reporting success about an artifact the room
        # cannot execute. Refusing would be the wrong repair, because a broken live mode is
        # precisely the state you need to save a fix over; so the gate REPAIRS and SAYS SO.
        os.chmod(target, 0o644)
        good2 = work / "candidate-good2.py"
        good2.write_text(live_src + "\n# a second harmless trailing comment\n", encoding="utf-8")
        os.chmod(good2, 0o644)
        good2_sha = sha(good2)
        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(good2),
                 "--target", str(target)], home)
        check("a save over an ALREADY-NON-EXECUTABLE target leaves the target RUNNABLE — carrying "
              "a broken mode forward is how the 22:41 outage would have survived its own fix",
              os.access(target, os.X_OK))
        check("...and the gate does not report SAVED silently: the repair of the target's own "
              "broken mode is announced on stdout", "⚠" in r.stdout and "not executable" in r.stdout.lower())
        check("...and it still exits 0 — a broken live mode must not BLOCK the save that fixes it",
              r.returncode == 0)
        check("...and the bytes that landed are the bytes that were gated (the post-replace "
              "content assertion, not merely that os.replace did not raise)",
              sha(target) == good2_sha)

        # ---- 4c · the assertion is real: an unrunnable result is REPORTED, never SAVED ----
        # Without this the fix above is unfalsifiable — "the file happened to be executable" and
        # "the gate checked that it was" look identical. Here the exec bits cannot be restored at
        # all (a target with no read bits either), so the post-replace assertion is the only thing
        # standing between the room and a silent "SAVED".
        os.chmod(target, 0o000)
        good3 = work / "candidate-good3.py"
        good3.write_text(live_src + "\n# third comment\n", encoding="utf-8")
        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(good3),
                 "--target", str(target)], home)
        check("a save whose result is NOT runnable exits non-zero and says so — the gate never "
              "prints SAVED over a file the room cannot execute",
              r.returncode == 1 and "NOT RUNNABLE" in r.stderr and "SAVED:" not in r.stdout)
        os.chmod(target, 0o755)

        # ---- 5 · cross-filesystem replace is refused, not silently non-atomic ----
        # ⚠ THE FAR CANDIDATE MUST STILL BE IMPORTABLE, or this check stops testing what it names.
        # Since 7.82 coord.py imports budget.py from its own directory, so a candidate dropped in a
        # bare temp dir now fails the IMPORT gate first — still refused, still not moved, but for a
        # reason that has nothing to do with cross-directory atomicity. The guard below would then
        # be UNREACHABLE, and an unreachable guard passes and fails identically no matter what it
        # protects. So: a second kit-shaped directory, importable, and DIFFERENT from the target's.
        far_dir = td / "elsewhere-kit"
        far_dir.mkdir()
        shutil.copy2(HERE.parent / "budget.py", far_dir / "budget.py")
        far = far_dir / "elsewhere.py"
        far.write_text(live_src, encoding="utf-8")
        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(far),
                 "--target", str(target)], home)
        check("a candidate in a DIFFERENT directory is refused rather than replaced non-atomically",
              r.returncode == 1 and "different directories" in r.stderr)

        # The real coord.py was never a target of anything above.
        check("the LIVE coord.py is untouched by this probe",
              LIVE_COORD.read_text(encoding="utf-8") == live_src)

    failed = [l for ok, l in RESULTS if not ok]
    print(f"\nprobe-save-gate: {'PASS' if not failed else 'FAIL'} "
          f"({len(RESULTS) - len(failed)}/{len(RESULTS)} checks)")
    for l in failed:
        print("  failed: " + l)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
