#!/usr/bin/env python3
"""probe-goal-scaffold-standard-files.py — a fresh goal creation produces R21's FULL standard set.

WHAT IT SCORES (task 7.582; set extended by 7.595). Owner ruling R21 (2026-08-08,
`build/meta-workflow/interview-findings.md`; meta-planner-v4 §9 / §11.12): the goal-creation
machinery writes the standard goal-folder artifacts from DETERMINISTIC templates — the ROUTER of
every supported harness (`CLAUDE.md` plus each equivalent, here `AGENTS.md`) plus the
write-if-something files. Owner ruling Q16 (2026-08-09, `d-owner-batch-q12-q19-0809` item 5)
added `ideas.md` to that set, making it FIVE (`issues.md`, `decisions.md`, `doubts.md`,
`gotchas.md`, `ideas.md`) and the created goal TEN files. Measured at the commit before 7.582
landed, `rbtv-goal scaffold` wrote four files — `goal.md`, `decisions.md`, `runs.csv`,
`threads.sql` — so the rest were the gap.

The five properties scored:

  1. a fresh scaffold lands EVERY file of the ruled set, each NON-EMPTY;
  2. the routers ROUTE — each router names every write-if-something file BY NAME (a count of
     files is not routing, and an empty router would satisfy a count);
  3. the mirror declares itself one — `AGENTS.md` carries the same routing body as `CLAUDE.md`
     and says in its own header that `CLAUDE.md` is the source;
  4. no agent is in the path — two scaffolds of the same name in different roots produce
     BYTE-IDENTICAL routers (a deterministic template, not a generated one);
  5. re-writing the standard set over a goal whose files HAVE CONTENT clobbers nothing.

⚠ THE GREEN ARMS ALONE PROVE NOTHING, WHICH IS WHY THE MUTANTS EXIST. "Every file is present" is
also what a probe reading its own fixture would report. So:

  - mutant A removes the `write_standard_artifacts` call from `cmd_scaffold` and MUST then leave
    the seven ruled files absent — that is the pre-fix state this row closed, reproduced;
  - mutant B turns the skip-if-exists guard into an unconditional write and MUST then destroy the
    content arm 5 protects.

If a mutant does NOT misbehave, the arm it controls is reported INOPERATIVE and this probe exits
2 — never 0. A check that could not have failed has scored nothing.

⚠ EVERY PATH BELOW IS A THROWAWAY `tempfile` TREE. No `.rbtv/goals` package is read or written,
by the tool or by either mutant — the live goals root is a production loop and this probe never
goes near it.

Run it through the suite — `node deploy/probe-suite.js --only goal-scaffold-standard-files` —
never by hand (`G-163`). Exit 0 = every property holds and the mutants proved the checks can
fail · 1 = a property is broken · 2 = INOPERATIVE.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "tool" / "goal_cli.py"
OUT = HERE / "probe-goal-scaffold-standard-files.out"

# The ruled set, spelled as LITERALS. Importing ROUTER_FILENAMES / WRITE_IF_SOMETHING would make
# this probe's expectation move with the code under test — deleting a name from the tuple would
# then delete the check that name is written, and the probe would stay green over the regression.
ROUTERS = ("CLAUDE.md", "AGENTS.md")
WRITE_IF_SOMETHING = ("issues.md", "decisions.md", "doubts.md", "gotchas.md", "ideas.md")
PRE_EXISTING = ("goal.md", "runs.csv", "threads.sql")

# The landed call + guard, verbatim. Textual replacement: a reshaped fix stops matching and turns
# the arm INOPERATIVE rather than quietly green.
SCAFFOLD_CALL = "    write_standard_artifacts(goal_dir, name)"
SCAFFOLD_MUTANT = "    pass  # MUTANT A: the R21 standard-artifact write is gone"

SKIP_GUARD = """        if path.exists():
            continue"""
SKIP_MUTANT = """        if False:
            continue"""

RESULTS = []
INOPERATIVE = []
_lines = []


def out(line):
    _lines.append(line)
    print(line)


def check(label, cond, detail=""):
    RESULTS.append((bool(cond), label))
    out(("PASS  " if cond else "FAIL  ") + label + (f"\n        {detail}" if detail else ""))


def inoperative(label, why):
    INOPERATIVE.append((label, why))
    out(f"SKIP  {label}\n        INOPERATIVE: {why}")


def read(path: Path) -> str:
    """The file's text, or `""` when it is absent.

    ⚠ AN ABSENT FILE IS A FAILURE TO SCORE, NOT AN EXCEPTION TO RAISE. Measured on this probe's
    own red-first run against the pre-fix code: a bare `read_text` in arm 3 raised
    `FileNotFoundError` the moment the routers were missing — exactly the condition the probe
    exists to detect — and killed the run before arms 4-7 (including BOTH red controls) scored
    anything. A probe that crashes on the defect it hunts reports less the more broken the code
    is. Every read of a file whose ABSENCE is a scored outcome goes through here.
    """
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def read_bytes(path: Path) -> bytes:
    return path.read_bytes() if path.is_file() else b""


def scaffold(tool: Path, root: Path, goal: str, contract: Path):
    r = subprocess.run(
        [sys.executable, str(tool), "--root", str(root), "scaffold", goal,
         "--contract", str(contract)],
        capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def fresh_root(td: Path, tag: str, tool: Path, goal="demo-goal"):
    """A throwaway goals root carrying one freshly scaffolded goal. Returns (goal_dir, rc, err)."""
    root = td / tag / ".rbtv" / "goals"
    root.mkdir(parents=True)
    contract = td / "contract.md"
    if not contract.is_file():
        contract.write_text("Ship the thing.\n", encoding="utf-8")
    rc, _, err = scaffold(tool, root, goal, contract)
    return root / goal, rc, err


def main() -> int:
    OUT.write_text("", encoding="utf-8")   # truncate BEFORE any work — no evidence husk

    if not TOOL.is_file():
        inoperative("goal_cli.py is present", f"{TOOL} does not exist")
        OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory(prefix="probe-goal-scaffold-std-") as _td:
        td = Path(_td)
        gd, rc, err = fresh_root(td, "a", TOOL)
        if rc != 0 or not gd.is_dir():
            inoperative("throwaway fixture builds",
                        f"the fixture scaffold exited {rc}: {err.strip()[:300]}")
            OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
            return 2

        # ── 1. THE FULL RULED SET LANDS, AND EVERY FILE HAS CONTENT ───────────────────────────
        for fname in (*PRE_EXISTING, *ROUTERS, *WRITE_IF_SOMETHING):
            p = gd / fname
            check(f"1. a fresh scaffold writes {fname}, non-empty",
                  p.is_file() and p.stat().st_size > 0,
                  f"exists={p.is_file()} size={p.stat().st_size if p.is_file() else 'n/a'}")

        # ── 2. THE ROUTERS ROUTE — content, not count ─────────────────────────────────────────
        for router in ROUTERS:
            text = read(gd / router)
            missing = [f for f in WRITE_IF_SOMETHING if f not in text]
            check(f"2. {router} names every write-if-something file",
                  not missing, f"not named: {missing}")
            check(f"2. {router} names the goal it routes",
                  "demo-goal" in text, text[:120])
            check(f"2. {router} states the write-if-something contract",
                  "nothing writes nothing" in text or "writes nothing" in text,
                  text[:200])

        # ── 2b. THE decisions.md TEMPLATE CARRIES Q19 — the split, and the citation ──────────
        # Content, not presence: arm 1 above passes on any decisions.md, including the pre-Q19
        # body. Both conjuncts are spelled as literals for the same reason the set is.
        dec = read(gd / "decisions.md")
        check("2b. decisions.md names the run-folder half of the durability split",
              "runs/run-<n>/decisions.md" in dec, dec[:200])
        check("2b. decisions.md adopts the entry shape by CITING decisions-discipline.md",
              "authoring/decisions-discipline.md" in dec, dec[:200])
        check("2b. decisions.md no longer carries the pre-Q19 'NOT a log' body",
              bool(dec) and "NOT a log" not in dec, dec[:200])

        # ── 3. THE MIRROR DECLARES ITSELF ONE, AND CARRIES THE SAME BODY ─────────────────────
        claude = read(gd / "CLAUDE.md")
        agents = read(gd / "AGENTS.md")
        check("3. AGENTS.md carries CLAUDE.md's routing body verbatim",
              bool(claude) and agents.endswith(claude),
              f"claude={len(claude)}B agents={len(agents)}B")
        check("3. AGENTS.md names CLAUDE.md as the source of truth",
              bool(claude) and "CLAUDE.md" in agents[:len(agents) - len(claude)],
              agents[:200])
        # `bool(claude)` is part of the assertion, not decoration: an ABSENT CLAUDE.md reads as
        # `""`, which contains no mirror header either, so without the presence conjunct this
        # check PASSED in the pre-fix red state — a check that cannot go red on the very defect
        # the probe hunts. Verified: with the conjunct it FAILS against `git show 91d67f9:`.
        check("3. CLAUDE.md carries no mirror header (it IS the source)",
              bool(claude) and "AUTO-GENERATED MIRROR" not in claude, claude[:120])

        # ── 4. DETERMINISTIC — no agent in the path ──────────────────────────────────────────
        gd2, rc2, err2 = fresh_root(td, "b", TOOL)
        if rc2 != 0:
            inoperative("4. a second independent scaffold builds",
                        f"exited {rc2}: {err2.strip()[:300]}")
        else:
            for fname in (*ROUTERS, *WRITE_IF_SOMETHING):
                a, b = read_bytes(gd / fname), read_bytes(gd2 / fname)
                # `a` non-empty is part of the assertion: two ABSENT files are also byte-equal,
                # and a determinism arm that passes on a pair of nothings scores nothing.
                check(f"4. {fname} is byte-identical across two independent scaffolds",
                      bool(a) and a == b, f"{len(a)}B vs {len(b)}B")

        # ── 5. RE-WRITING OVER CONTENT CLOBBERS NOTHING ──────────────────────────────────────
        # Exercised through the writer, because `cmd_scaffold` refuses an existing goal outright:
        # the skip-if-exists property lives in the writer and this is where it can be observed.
        loaded = gd / "issues.md"
        loaded.write_text("# issues\n\n- S-1: a real issue an agent wrote here.\n", encoding="utf-8")
        before = loaded.read_bytes()
        rewrite = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util,sys;"
             "spec=importlib.util.spec_from_file_location('gc',sys.argv[1]);"
             "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
             "print(m.write_standard_artifacts(__import__('pathlib').Path(sys.argv[2]),'demo-goal'))",
             str(TOOL), str(gd)],
            capture_output=True, text=True, timeout=120)
        if rewrite.returncode != 0:
            inoperative("5. the standard-artifact writer is callable",
                        f"exited {rewrite.returncode}: {rewrite.stderr.strip()[:300]}")
        else:
            check("5. a re-write over a goal with content changes nothing",
                  loaded.read_bytes() == before,
                  f"wrote={rewrite.stdout.strip()} content={loaded.read_text(encoding='utf-8')[:120]!r}")
            check("5. the re-write reports it wrote nothing",
                  rewrite.stdout.strip() == "[]", rewrite.stdout.strip())

        # ── 6. MUTANT A — without the R21 write, the five ruled files MUST be absent ─────────
        src = TOOL.read_text(encoding="utf-8")
        if SCAFFOLD_CALL not in src:
            inoperative(
                "6. RED CONTROL — the scaffold call is what writes the ruled set",
                "the call text no longer matches the landed source, so the mutation does not "
                "apply — arm 1 is therefore unproven, not green",
            )
        else:
            mut_a = td / "goal_cli_no_standard_write.py"
            mut_a.write_text(src.replace(SCAFFOLD_CALL, SCAFFOLD_MUTANT), encoding="utf-8")
            gd_a, rc_a, err_a = fresh_root(td, "mut-a", mut_a)
            absent = [f for f in (*ROUTERS, *WRITE_IF_SOMETHING) if not (gd_a / f).is_file()]
            if rc_a == 0 and sorted(absent) == sorted([*ROUTERS, *WRITE_IF_SOMETHING]):
                check("6. RED CONTROL — the mutant leaves all 7 ruled files absent "
                      "(so arm 1 can fail)", True, f"absent: {sorted(absent)}")
            else:
                inoperative(
                    "6. RED CONTROL — the mutant leaves the ruled files absent",
                    f"mutant exit={rc_a}, absent={sorted(absent)}, err={err_a.strip()[:200]} — "
                    "arm 1 discriminates nothing",
                )
            check("6. the mutant still writes the pre-existing four (the fix is ADDITIVE)",
                  rc_a == 0 and all((gd_a / f).is_file() for f in PRE_EXISTING),
                  f"exit={rc_a} " + str([f for f in PRE_EXISTING if not (gd_a / f).is_file()]))

        # ── 7. MUTANT B — without skip-if-exists, the content MUST be destroyed ──────────────
        if SKIP_GUARD not in src:
            inoperative(
                "7. RED CONTROL — the skip-if-exists guard is what protects existing content",
                "the guard text no longer matches the landed source — arm 5 is unproven, not green",
            )
        else:
            mut_b = td / "goal_cli_no_skip.py"
            mut_b.write_text(src.replace(SKIP_GUARD, SKIP_MUTANT), encoding="utf-8")
            victim = td / "mut-b-goal"
            victim.mkdir()
            (victim / "issues.md").write_text("# issues\n\n- S-1: a real issue.\n",
                                              encoding="utf-8")
            keep = (victim / "issues.md").read_bytes()
            r = subprocess.run(
                [sys.executable, "-c",
                 "import importlib.util,sys;"
                 "spec=importlib.util.spec_from_file_location('gc',sys.argv[1]);"
                 "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
                 "m.write_standard_artifacts(__import__('pathlib').Path(sys.argv[2]),'demo-goal')",
                 str(mut_b), str(victim)],
                capture_output=True, text=True, timeout=120)
            destroyed = r.returncode == 0 and (victim / "issues.md").read_bytes() != keep
            if destroyed:
                check("7. RED CONTROL — the mutant DESTROYS existing content (so arm 5 can fail)",
                      True, f"issues.md changed from {len(keep)}B to "
                            f"{len((victim / 'issues.md').read_bytes())}B")
            else:
                inoperative(
                    "7. RED CONTROL — the mutant destroys existing content",
                    f"mutant exit={r.returncode}, content unchanged, err={r.stderr.strip()[:200]} "
                    "— arm 5 discriminates nothing",
                )

    failures = [lbl for ok, lbl in RESULTS if not ok]
    out("")
    out(f"checks: {len(RESULTS)}  failures: {len(failures)}  inoperative: {len(INOPERATIVE)}")
    for lbl, why in INOPERATIVE:
        out(f"  INOPERATIVE  {lbl}: {why}")
    for lbl in failures:
        out(f"  FAILED  {lbl}")
    OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")

    if INOPERATIVE:
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
