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
  · that a PASSING candidate is actually moved into place, atomically,
  · a candidate that is HEALTHY but BEHIND the target — the only leg that scores the target rather
    than the candidate, and the one failure mode every check above is blind to by construction.
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
    # encoding is PINNED: the gate's own output carries ⚠, and on Windows the default capture
    # codec (cp1252) raises UnicodeDecodeError, leaving stderr None and every check below a
    # TypeError instead of a verdict.
    return subprocess.run(argv, capture_output=True, text=True, timeout=180, env=env,
                          encoding="utf-8", errors="replace")


def kit_siblings():
    """Every kit module coord.py imports at MODULE level — derived, never listed by hand.

    Listing them by hand is what broke this fixture twice: task 7.82 added `budget`, task 7.57
    added `gateway_client`, and each time the copy site was swept a release late (the second one
    reported as "the LIVE coord.py fails the gate" — production blamed for the probe's own kit).
    Reading coord.py's own imports means the next sibling arrives for free.
    """
    kit = HERE.parent
    names, in_supervisor = _coord_module_names()
    return (sorted(p for p in (kit / f"{n}.py" for n in names - in_supervisor) if p.is_file()),
            sorted(p for p in (kit.parent / "supervisor" / f"{n}.py" for n in in_supervisor)
                   if p.is_file()))


def _coord_module_names():
    """(every module name coord.py needs at load, the subset that lives in `supervisor/`).

    DERIVED FROM coord.py'S OWN TEXT, never listed by hand — listing them by hand is what broke
    this fixture twice (task 7.82 added `budget`, 7.57 added `gateway_client`, and each time the
    copy site was swept a release late, reported as "the LIVE coord.py fails the gate": production
    blamed for the probe's own kit). Parsed rather than imported on purpose — this probe's subject
    is a stand-in kit, so it must not depend on the live one importing.
    """
    names, in_supervisor = set(), set()
    for node in ast.parse(LIVE_COORD.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
        # …and the files coord.py LOADS rather than imports: the move-only split [D23, T4-R12]
        # put most of the product in siblings named by `SPLIT_MODULES`, and a stand-in kit
        # missing them dies at load exactly the way a missing `budget` used to. Read from the
        # tuple for the same reason the imports are read: the next split file arrives for free.
        elif isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "SPLIT_MODULES" for t in node.targets):
            names.update(e.value for e in node.value.elts if isinstance(e, ast.Constant))
        # ⚠ AND WHICH OF THEM DO NOT LIVE BESIDE coord.py. The six supervisor-landing modules left
        # `coord/` for the sibling component `supervisor/` (owner ruling 2026-08-25), and coord.py
        # resolves them one directory up. A stand-in kit that stages every name FLAT reproduces a
        # layout the real loader never sees, and the gate would pass on a fixture that cannot
        # exist — so the split is read from coord.py's own tuple, exactly like the list above.
        elif isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "SUPERVISOR_MODULES" for t in node.targets):
            in_supervisor.update(e.value for e in node.value.elts
                                 if isinstance(e, ast.Constant))
    return names, in_supervisor


def stock_kit(dest, siblings, supervisor_siblings):
    for p in siblings:
        shutil.copy2(p, dest / p.name)
    # The stand-in `supervisor/` is a SIBLING of the stand-in kit, because that is where coord.py
    # looks: `Path(__file__).resolve().parent.parent / "supervisor"`.
    if supervisor_siblings:
        sup = dest.parent / "supervisor"
        sup.mkdir(exist_ok=True)
        for p in supervisor_siblings:
            shutil.copy2(p, sup / p.name)


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

        # ⚠ THE STAND-IN KIT MUST CARRY coord.py'S SIBLINGS, NOT ONLY coord.py. coord.py imports
        # kit modules at module level (budget since 7.82, gateway_client since 7.57), so a lone
        # copy in an empty directory dies at import with ModuleNotFoundError — and this probe
        # would then report "the LIVE coord.py fails the gate", blaming production for the probe's
        # own incomplete fixture. Measured: exactly the 10-failure red of 17:00, and again on
        # 2026-08-10 (task 7.669). The list is DERIVED from coord.py — see kit_siblings().
        siblings, supervisor_siblings = kit_siblings()
        check("the stand-in kit carries every kit module coord.py imports at module level "
              f"(found: {[p.name for p in siblings]})", len(siblings) >= 2)
        check("the stand-in kit reproduces the sibling `supervisor/` half of the product "
              f"(found: {[p.name for p in supervisor_siblings]})",
              len(supervisor_siblings) == 6)
        stock_kit(work, siblings, supervisor_siblings)

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
        # ⚠ ANCHOR ON THE argparse API, NOT ON THE PARSER CLASS. The original anchor was
        # `p = argparse.ArgumentParser(`; coord.py's build_parser() now constructs a local
        # `_RefusingParser`, so the anchor matched nothing, the mutant was a byte-identical copy
        # of a healthy file, and the arm went red for rot rather than for a regression (7.633).
        # ⚠ AND NO LONGER ON A STRING INSIDE `build_parser`: the move-only split [D23, T4-R12]
        # carried that function into `cli_main.py`, so a CANDIDATE coord.py contains no anchor
        # inside it — the old `p.add_subparsers(` replace matched nothing and the mutant became a
        # byte-identical copy of a healthy file, the exact 7.633 rot this comment warns about, one
        # move later. The mutation stays on the argparse API and stays inside the candidate: the
        # module is rebound to None just BEFORE the __main__ guard, so the body still executes to
        # completion (the import arm above stays green) and parser CONSTRUCTION dies on the first
        # argparse attribute it touches — the half a bare import check would miss.
        pmut = work / "mutant-parser.py"
        pmut.write_text(
            live_src.replace('if __name__ == "__main__":',
                             'argparse = None\n\n\nif __name__ == "__main__":', 1),
            encoding="utf-8")
        broke_parser = ('argparse = None' in pmut.read_text(encoding="utf-8")
                        and 'if __name__ == "__main__":' in live_src)
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
        stock_kit(far_dir, siblings, supervisor_siblings)
        far = far_dir / "elsewhere.py"
        far.write_text(live_src, encoding="utf-8")
        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(far),
                 "--target", str(target)], home)
        check("a candidate in a DIFFERENT directory is refused rather than replaced non-atomically",
              r.returncode == 1 and "different directories" in r.stderr)

        # ---- 6 · a candidate that is HEALTHY but BEHIND the target -------------
        # Every leg above scores the CANDIDATE. None of them opens the target, and neither did the
        # gate: a candidate branched from an older coord.py imports cleanly, builds its parser
        # cleanly, and was installed over work it does not contain — printing SAVED, exit 0, as it
        # landed. Measured live 2026-08-11: coord.py carried 259 uncommitted insertions of a
        # parallel session's work, and the candidate sitting beside it, branched two hours earlier,
        # carried none of them. One save would have destroyed all of it and reported success.
        #
        # ⚠ THREE ARMS, BECAUSE EACH ONE ALONE PASSES FOR A DIFFERENT BROKEN GATE:
        #   (a) a refusal is also what a gate that refuses EVERYTHING produces — hence (b);
        #   (b) an exit code cannot see an os.replace that already ran before the message printed,
        #       which is precisely the failure being guarded — hence the sha256 either side of (a);
        #   (c) without --force still installing, the gate is a wall and the merge-then-retry path
        #       documented in the refusal itself does not exist.
        target_sha = sha(target)
        stale = work / "candidate-stale.py"
        stale.write_text(live_src + "\n# branched earlier; carries none of the target's work\n",
                         encoding="utf-8")
        # Relative to the TARGET's own mtime, so the fixture holds whatever the legs above left.
        behind = os.stat(target).st_mtime - 7200
        os.utime(stale, (behind, behind))
        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(stale),
                 "--target", str(target)], home)
        check("a STALE candidate — healthy, but older than the target it would overwrite — is "
              "REFUSED", r.returncode == 1 and "STALE CANDIDATE" in r.stderr)
        check("...and the TARGET is BYTE-IDENTICAL after that refusal — the exit code alone cannot "
              "see a replace that already happened, so the bytes are what score it",
              sha(target) == target_sha)
        check("...and the candidate is still on disk to be merged, not consumed", stale.is_file())
        check("...and the refusal names BOTH files and BOTH timestamps, in its OWN words — a stale "
              "candidate is fine but BEHIND, so the broken-candidate block's 'the live coord.py is "
              "untouched' would be the wrong news and the wrong remedy",
              str(target) in r.stderr and str(stale) in r.stderr
              and r.stderr.count("Z  ") >= 2 and "merge" in r.stderr.lower()
              and "the live coord.py is untouched" not in r.stderr)

        # (b) THE POSITIVE CONTROL. Without it every arm above is satisfied by a gate that refuses
        #     every save there is — which is its own total outage, arriving as a wall of REFUSED.
        fresh = work / "candidate-fresh.py"
        fresh.write_text(live_src + "\n# written after the target — the ordinary case\n",
                         encoding="utf-8")
        os.chmod(fresh, 0o644)
        fresh_sha = sha(fresh)
        ahead = os.stat(target).st_mtime + 5
        os.utime(fresh, (ahead, ahead))
        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(fresh),
                 "--target", str(target)], home)
        check("a NEWER candidate still SAVES — the staleness check is a gate, not a wall",
              r.returncode == 0 and sha(target) == fresh_sha)

        # (c) --force: the path the refusal itself tells the reader to take, after merging.
        forced = work / "candidate-forced.py"
        forced.write_text(live_src + "\n# merged onto the current file by hand, then forced\n",
                          encoding="utf-8")
        forced_sha = sha(forced)
        os.utime(forced, (behind, behind))
        r = run([sys.executable, str(SAVE_COORD), "--candidate", str(forced),
                 "--target", str(target), "--force"], home)
        check("...and --force installs a stale candidate anyway, so the merge-then-retry remedy "
              "the refusal names is actually reachable",
              r.returncode == 0 and sha(target) == forced_sha)

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
