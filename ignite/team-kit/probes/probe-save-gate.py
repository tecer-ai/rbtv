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

        # ---- 5 · cross-filesystem replace is refused, not silently non-atomic ----
        far = td / "elsewhere.py"
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
