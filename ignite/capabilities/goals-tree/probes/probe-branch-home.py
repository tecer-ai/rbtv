#!/usr/bin/env python3
"""probe-branch-home.py — `rbtv-goal branch-home` mints the registry's settled branch path, create-only.

WHAT IT SCORES (task 7.450 / MC8). `concepts/branch.md` (settled-by `d-branch-family`) fixes where a
branch's files live: *"their files live under the parent run's branches folder
(`runs/run-{n}/branches/branch-{m}/`), each branch folder shaped exactly like a run folder,
recursively — a branch may carry its own `branches/`"*. No machinery realized that shape at HEAD
(`branches/` → 0 hits across `*.py`/`*.js` with `taskforce` → 358 as the positive control), so this
is a first landing. The four properties scored here are the task's done criteria:

  1. the minted path is `<parent>/branches/branch-<m>` — the settled form, nothing else;
  2. the numbering rule is deterministic — two reads of the SAME state return the same name, and a
     folder that does not match `branch-<digits>` never enters the count;
  3. a collision REFUSES rather than overwriting, reusing, or writing into an existing home;
  4. the recursion holds — a branch home is itself a legal parent for a branch.

⚠ THE GREEN ARMS ALONE PROVE NOTHING, WHICH IS WHY THE MUTANTS EXIST. "The tool refused" is also
what a tool that refuses everything would produce, and "the tool created it" is what a tool with no
guard at all would produce. So the two refusal arms each carry a MUTANT control that reverts the one
guard under test and REQUIRES the bad outcome to occur there:

  - mutant A drops the create-only guard (the `home.exists()` refusal, and `exist_ok=True` on the
    mkdir) and must then admit a collision;
  - mutant B drops the parent-layout guard and must then mint `branches/` under a folder that is
    neither a run nor a branch.

If a mutant does NOT misbehave, the arm it controls is reported INOPERATIVE and this probe exits 2 —
never 0. An assertion that could not have failed has scored nothing. The POSITIVE control is that
ordinary mints in the same run still succeed, so the refusals are discriminating rather than blanket.

Every path below is a throwaway tree under `tempfile`. No live `.rbtv/goals` package is read or
written, by the tool or by either mutant.

Run it through the suite — `node deploy/probe-suite.js --only branch-home` — never by hand (`G-163`).
Exit 0 = every property holds and the mutants proved the checks can fail · 1 = a property is broken ·
2 = INOPERATIVE (could not run, or a red control did not go red).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "tool" / "goal_cli.py"
OUT = HERE / "probe-branch-home.out"

# The landed guards, verbatim. The mutants are built by textual replacement, so a reshaped fix stops
# matching and turns the arm INOPERATIVE instead of quietly green.
CREATE_ONLY_GUARD = """    if home.exists():
        raise Refusal(
            f"{home}: already exists — minting a branch home is create-only and "
            "never overwrites, reuses or writes into an existing home"
        )
    if create:
        home.mkdir(parents=True)   # no exist_ok: the create IS the collision check"""
CREATE_ONLY_MUTANT = """    if create:
        home.mkdir(parents=True, exist_ok=True)"""

LAYOUT_GUARD = """    if kind is None:
        raise Refusal("""
LAYOUT_MUTANT = """    if False:
        raise Refusal("""

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


def run(tool: Path, args: list[str]):
    r = subprocess.run([sys.executable, str(tool), *args], capture_output=True, text=True,
                       timeout=120)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def mint(tool: Path, root: Path, goal: str, *extra):
    """Returns (rc, payload-or-None, stderr) for a --json branch-home call."""
    rc, so, se = run(tool, ["--root", str(root), "branch-home", goal, "--json", *extra])
    try:
        payload = json.loads(so)
    except Exception:                                             # noqa: BLE001
        payload = None
    return rc, payload, se


def build_tree(td: Path) -> tuple[Path, Path]:
    """A sandbox goals root carrying one goal with a real `runs/run-1/` layout."""
    root = td / "sandbox" / ".rbtv" / "goals"
    root.mkdir(parents=True)
    contract = td / "contract.md"
    contract.write_text("Ship the thing.\n", encoding="utf-8")
    rc, _, err = run(TOOL, ["--root", str(root), "scaffold", "demo-goal",
                            "--contract", str(contract)])
    if rc != 0:
        raise RuntimeError(f"could not scaffold the fixture goal: {err.strip()}")
    goal = root / "demo-goal"
    (goal / "runs" / "run-1").mkdir(parents=True)
    (goal / "runs.csv").write_text(
        "run-id,type,state,taskforce-id(s),opened,closed\n"
        "run-1,fresh,open,tf-1,2026-01-01,\n", encoding="utf-8", newline="\n")
    # a plain folder inside the goal — neither a run nor a branch — for the layout red arm
    (goal / "planning").mkdir()
    # a `run-1` that is NOT under `runs/`: the name alone must not admit it
    (goal / "loose" / "run-1").mkdir(parents=True)
    return root, goal


def main() -> int:
    OUT.write_text("", encoding="utf-8")   # truncate BEFORE any work — no evidence husk

    if not TOOL.is_file():
        inoperative("goal_cli.py is present", f"{TOOL} does not exist")
        OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory(prefix="probe-branch-home-") as _td:
        td = Path(_td)
        try:
            root, goal = build_tree(td)
        except Exception as exc:                                  # noqa: BLE001
            inoperative("throwaway fixture builds", str(exc))
            OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
            return 2

        run1 = goal / "runs" / "run-1"

        # ── 1. THE NUMBERING RULE IS DETERMINISTIC — same state, same answer ───────────────────
        rc_a, pay_a, se_a = mint(TOOL, root, "demo-goal", "--dry-run")
        rc_b, pay_b, se_b = mint(TOOL, root, "demo-goal", "--dry-run")
        check("1. two reads of the same state agree",
              rc_a == 0 and rc_b == 0 and pay_a and pay_b and pay_a["home"] == pay_b["home"],
              f"a={pay_a} b={pay_b} err={se_a.strip()[:200]}{se_b.strip()[:200]}")
        check("1. the empty state yields branch-1",
              bool(pay_a) and pay_a["branch"] == "branch-1", str(pay_a))
        check("1. --dry-run created nothing", not (run1 / "branches").exists(),
              str(sorted(p.name for p in run1.iterdir())))

        # ── 2. THE MINTED PATH IS THE SETTLED FORM ────────────────────────────────────────────
        rc, pay, se = mint(TOOL, root, "demo-goal")
        check("2. the mint exits 0", rc == 0, f"exit={rc} stderr={se.strip()[:200]}")
        home1 = run1 / "branches" / "branch-1"
        check("2. the path is <goal>/runs/run-1/branches/branch-1",
              bool(pay) and Path(pay["home"]).relative_to(goal).as_posix()
              == "runs/run-1/branches/branch-1",
              str(pay))
        check("2. the folder exists on disk", home1.is_dir(), str(pay))
        check("2. the mint reports the parent as a run",
              bool(pay) and pay["parent_kind"] == "run", str(pay))
        check("2. the home is EMPTY — filling it is the materialization step's, not this one's",
              home1.is_dir() and list(home1.iterdir()) == [],
              str(sorted(p.name for p in home1.iterdir())) if home1.is_dir() else "absent")

        # ── 3. THE NUMBERING ADVANCES, AND IGNORES WHAT IS NOT A BRANCH FOLDER ────────────────
        (run1 / "branches" / "notes.md").write_text("x\n", encoding="utf-8")
        (run1 / "branches" / "branch-x").mkdir()
        (run1 / "branches" / "branch-99.bak").mkdir()
        rc, pay, se = mint(TOOL, root, "demo-goal", "--dry-run")
        check("3. non-conforming neighbours never enter the count",
              rc == 0 and bool(pay) and pay["branch"] == "branch-2",
              f"{pay} err={se.strip()[:200]}")
        rc, pay, _ = mint(TOOL, root, "demo-goal")
        check("3. the second mint is branch-2 and lands",
              rc == 0 and bool(pay) and pay["branch"] == "branch-2"
              and (run1 / "branches" / "branch-2").is_dir(), str(pay))

        # ── 4. RECURSION — a branch home is itself a legal parent ─────────────────────────────
        rc, pay, se = mint(TOOL, root, "demo-goal",
                           "--parent", "runs/run-1/branches/branch-1")
        nested = home1 / "branches" / "branch-1"
        check("4. a branch home carries its own branches/",
              rc == 0 and nested.is_dir()
              and bool(pay) and pay["parent_kind"] == "branch",
              f"exit={rc} {pay} err={se.strip()[:200]}")
        check("4. the nested path repeats the settled form",
              bool(pay) and Path(pay["home"]).relative_to(goal).as_posix()
              == "runs/run-1/branches/branch-1/branches/branch-1", str(pay))

        # ── 5. COLLISION REFUSES — pre-state and post-state compared ─────────────────────────
        sentinel = home1 / "sentinel.txt"
        sentinel.write_text("written by the FIRST mint's owner\n", encoding="utf-8")
        pre = sorted(p.name for p in home1.iterdir())
        pre_bytes = sentinel.read_bytes()
        rc, pay, se = mint(TOOL, root, "demo-goal", "--branch", "branch-1")
        post = sorted(p.name for p in home1.iterdir())
        check("5. a collision exits nonzero", rc != 0, f"exit={rc} stdout={json.dumps(pay)[:200]}")
        check("5. the refusal names create-only", "create-only" in se, se.strip()[:300])
        check("5. the existing home is untouched",
              pre == post and sentinel.read_bytes() == pre_bytes,
              f"pre={pre} post={post}")

        # ── 6. RED ARM — a parent with no run/branch layout REFUSES ──────────────────────────
        for label, rel in (("a plain folder", "planning"),
                           ("a `run-1` outside `runs/`", "loose/run-1")):
            rc, pay, se = mint(TOOL, root, "demo-goal", "--parent", rel)
            check(f"6. {label} is refused", rc != 0, f"exit={rc} stdout={json.dumps(pay)[:200]}")
            check(f"6. {label} — the refusal names the settled parent shape",
                  "not a run folder or a branch folder" in se, se.strip()[:300])
            check(f"6. {label} — nothing was created",
                  not (goal / rel / "branches").exists(), rel)

        # ── 7. RED ARM — a parent that escapes the goal folder REFUSES ───────────────────────
        outside = td / "outside" / "runs" / "run-1"
        outside.mkdir(parents=True)
        for label, rel in (("an absolute path", str(outside)),
                           ("`..` traversal", "../../../outside/runs/run-1")):
            rc, pay, se = mint(TOOL, root, "demo-goal", "--parent", rel)
            check(f"7. {label} is refused", rc != 0, f"exit={rc} stdout={json.dumps(pay)[:200]}")
            check(f"7. {label} — nothing was written outside the goal",
                  not (outside / "branches").exists(), str(outside))

        # ── 8. MUTANT A — without the create-only guard, the collision MUST be admitted ───────
        src = TOOL.read_text(encoding="utf-8")
        if CREATE_ONLY_GUARD not in src:
            inoperative(
                "8. RED CONTROL — the create-only guard is what refuses a collision",
                "the guard text no longer matches the landed source, so the mutation does not "
                "apply — arm 5 is therefore unproven, not green",
            )
        else:
            mut_a = td / "goal_cli_no_create_only.py"
            mut_a.write_text(src.replace(CREATE_ONLY_GUARD, CREATE_ONLY_MUTANT), encoding="utf-8")
            rc, pay, se = mint(mut_a, root, "demo-goal", "--branch", "branch-1")
            if rc == 0:
                check("8. RED CONTROL — the mutant ADMITS the collision (so arm 5 can fail)",
                      True, f"mutant exit=0, reported {pay}")
            else:
                inoperative(
                    "8. RED CONTROL — the mutant ADMITS the collision",
                    f"mutant exit={rc} stderr={se.strip()[:200]} — the collision could not be "
                    "reproduced without the guard, so arm 5 discriminates nothing",
                )
            check("8. the mutant did not damage the existing home",
                  sorted(p.name for p in home1.iterdir()) == post
                  and sentinel.read_bytes() == pre_bytes,
                  str(sorted(p.name for p in home1.iterdir())))

        # ── 9. MUTANT B — without the layout guard, a plain folder MUST be accepted ───────────
        if LAYOUT_GUARD not in src:
            inoperative(
                "9. RED CONTROL — the layout guard is what refuses a non-run parent",
                "the guard text no longer matches the landed source — arm 6 is unproven, not green",
            )
        else:
            mut_b = td / "goal_cli_no_layout.py"
            mut_b.write_text(src.replace(LAYOUT_GUARD, LAYOUT_MUTANT), encoding="utf-8")
            rc, pay, se = mint(mut_b, root, "demo-goal", "--parent", "planning")
            landed = (goal / "planning" / "branches" / "branch-1").is_dir()
            if rc == 0 and landed:
                check("9. RED CONTROL — the mutant mints under a plain folder (so arm 6 can fail)",
                      True, f"mutant exit=0, wrote {pay['home'] if pay else '?'}")
            else:
                inoperative(
                    "9. RED CONTROL — the mutant mints under a plain folder",
                    f"mutant exit={rc}, landed={landed}, stderr={se.strip()[:200]} — arm 6 "
                    "discriminates nothing",
                )

        # ── 10. POSITIVE CONTROL — the fixed tool still mints ordinarily, after all refusals ──
        rc, pay, se = mint(TOOL, root, "demo-goal")
        check("10. POSITIVE CONTROL — an ordinary mint still succeeds (the refusals are not blanket)",
              rc == 0 and bool(pay) and pay["branch"] == "branch-3"
              and (run1 / "branches" / "branch-3").is_dir(),
              f"exit={rc} {pay} err={se.strip()[:200]}")

        # ── 11. A MATCHING NAME COUNTS WHATEVER THE ENTRY IS ─────────────────────────────────
        # A stray FILE called `branch-9` must not stay invisible to the numbering and then
        # collide as a refusal six mints later.
        (run1 / "branches" / "branch-9").write_text("not a folder\n", encoding="utf-8")
        rc, pay, se = mint(TOOL, root, "demo-goal", "--dry-run")
        check("11. a non-directory `branch-<n>` still occupies its number",
              rc == 0 and bool(pay) and pay["branch"] == "branch-10",
              f"exit={rc} {pay} err={se.strip()[:200]}")

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
