#!/usr/bin/env python3
"""probe-goal-root-escape.py — `goal_cli.py`'s `--root` sandbox holds for `lint` and `materialize`.

THE DEFECT IT SCORES (found by adversarial verification of task 7.63, run-2 seat `G2-goaltree-ver`,
Finding 1): `goal_dir = root / args.goal_name`. `Path.__truediv__` DISCARDS the left operand when
the right one is absolute, so an absolute `goal_name` escaped `--root` entirely — `materialize`
wrote a `seat.md` outside the declared root and still reported `"ok": true`, exit 0. `..` segments
walk out of the root the same way. Only `scaffold` validated its name (`GOAL_NAME_RE`); `lint` and
`materialize` validated nothing. `--root` is the ONLY thing that aims a write verb at a test tree
instead of a live goals package, so an escape defeats the one sandbox this tool has.

⚠ THE GREEN ARMS ALONE PROVE NOTHING, AND THAT IS WHY THE MUTANT EXISTS. "The tool refused" is also
what a tool that refuses everything, or that never found the goal, would produce. So every green
arm has a control:

  - the MUTANT arm (row 3) runs a copy of `goal_cli.py` with `resolve_goal_dir(root, name)` textually
    reverted to the pre-fix `root / name` and REQUIRES the escape to succeed there — a write landing
    outside the root, exit 0. If the mutant does NOT escape, this probe is vacuous and exits 2
    (INOPERATIVE), never 0: an assertion that cannot go red has scored nothing.
  - the POSITIVE arm (row 4) requires an ordinary in-root goal name to still lint and materialize,
    so the refusal is discriminating rather than a blanket ban.

Every path below is a throwaway tree under `tempfile`. The live `.rbtv/goals` package is never read
and never written, by either the fixed tool or the mutant.

Run it through the suite — `node deploy/probe-suite.js --only goal-root-escape` — never by hand
(`G-163`). Exit 0 = the sandbox holds and the mutant proved the check can fail · 1 = a property is
broken · 2 = INOPERATIVE (could not run, or the red control did not go red).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "tool" / "goal_cli.py"
OUT = HERE / "probe-goal-root-escape.out"

# The pre-fix expression and the fixed call, as they appear on disk. The mutant is built by
# replacing the second with the first — so if the fix is ever reshaped, the mutation stops applying
# and row 3 turns this probe INOPERATIVE rather than quietly green.
FIXED_CALLS = (
    "goal_dir = resolve_goal_dir(root, name)",
    "goal_dir = resolve_goal_dir(root, args.goal_name)",
)
PREFIX_CALLS = (
    "goal_dir = root / name",
    "goal_dir = root / args.goal_name",
)

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


def build_tree(td: Path) -> tuple[Path, Path, Path]:
    """A sandbox root, a DECOY goal outside it, and a catalog. Returns (root, decoy_goal, catalog).

    The decoy is a fully materializable goal so that an escape has somewhere real to land: if the
    outside goal were unbuildable, `materialize` would refuse for the WRONG reason and the green
    arm would be an accident.
    """
    root = td / "sandbox" / ".rbtv" / "goals"
    root.mkdir(parents=True)
    decoy_root = td / "decoy"
    decoy_root.mkdir()
    contract = td / "contract.md"
    contract.write_text("Ship the thing.\n", encoding="utf-8")

    rc, _, err = run(TOOL, ["--root", str(decoy_root), "scaffold", "outside-goal",
                            "--contract", str(contract)])
    if rc != 0:
        raise RuntimeError(f"could not scaffold the decoy goal: {err.strip()}")
    goal = decoy_root / "outside-goal"

    run_dir = goal / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    (goal / "runs.csv").write_text(
        "run-id,type,state,taskforce-id(s),opened,closed\n"
        "run-1,fresh,planning,tf-1,2026-01-01,\n", encoding="utf-8", newline="\n")
    (run_dir / "taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        "tf-1,w-demo,,claude,claude-opus-5,medium,50,m1\n", encoding="utf-8", newline="\n")
    (run_dir / "milestones.csv").write_text(
        "milestone-id,name,status\nm1,prove it,pending\n", encoding="utf-8", newline="\n")

    comp = td / "catalog" / "mod" / "comp"
    for sub in ("prompts/cognitive-units/persona", "prompts/cognitive-units/permissions",
                "tasks/cognitive-units/task-goal", "capabilities/grep-it"):
        (comp / sub).mkdir(parents=True)
    (comp / "prompts/cognitive-units/persona/p.md").write_text(
        "---\nid: cu-persona-demo\ndescription: demo persona\n---\n\n"
        "<persona>\nYou are the demo seat.\n</persona>\n", encoding="utf-8")
    (comp / "prompts/cognitive-units/permissions/perm.md").write_text(
        "---\nid: cu-permissions-demo\ndescription: demo permissions\n---\n\n"
        "<permissions>\nRead the tree. Write nothing.\n</permissions>\n", encoding="utf-8")
    (comp / "tasks/cognitive-units/task-goal/g.md").write_text(
        "---\nid: cu-task-goal-demo\ndescription: demo goal\n---\n\n"
        "<task-goal>\nProve the assembly.\n</task-goal>\n", encoding="utf-8")
    (comp / "capabilities/grep-it/grep-it.md").write_text(
        "---\nid: cu-capability-grep-it\ndescription: find things\n---\n\n"
        "<capability>\nNot inlined.\n</capability>\n", encoding="utf-8")
    (comp / "prompts.csv").write_text(
        "prompt-id,persona,permissions,description\n"
        "prompt-demo,cu-persona-demo@latest,cu-permissions-demo@latest,demo prompt\n",
        encoding="utf-8")
    (comp / "tasks.csv").write_text(
        "task-id,task-goal,capabilities,description\n"
        "task-demo,cu-task-goal-demo@latest,cu-capability-grep-it,demo task\n", encoding="utf-8")
    (comp / "seats.csv").write_text(
        "seat-id,prompt-id,task-id,description\nw-demo,prompt-demo,task-demo,the demo seat\n",
        encoding="utf-8")
    return root, goal, td / "catalog"


def seats_under(goal: Path) -> list[str]:
    return sorted(str(p) for p in goal.rglob("seat.md"))


def main() -> int:
    OUT.write_text("", encoding="utf-8")   # truncate BEFORE any work — no evidence husk

    if not TOOL.is_file():
        inoperative("goal_cli.py is present", f"{TOOL} does not exist")
        OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory(prefix="probe-goal-root-escape-") as _td:
        td = Path(_td)
        try:
            root, decoy, catalog = build_tree(td)
        except Exception as exc:                                  # noqa: BLE001
            inoperative("throwaway fixture builds", str(exc))
            OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
            return 2

        abs_name = str(decoy)
        # `..` from `<td>/sandbox/.rbtv/goals` back down into `<td>/decoy/outside-goal`
        dots_name = "../../../decoy/outside-goal"

        # ── 1. materialize (the WRITE verb) refuses both escape forms, and writes nothing ──────
        for label, name in (("absolute path", abs_name), ("`..` traversal", dots_name)):
            rc, so, se = run(TOOL, ["--root", str(root), "materialize", name,
                                    "--catalog-root", str(catalog), "--json"])
            check(f"1.{label} — materialize exits nonzero", rc != 0, f"exit={rc} stdout={so[:200]}")
            check(f"1.{label} — the refusal names the root escape",
                  "escapes --root" in se, f"stderr={se.strip()[:300]}")
            check(f"1.{label} — nothing was written outside --root",
                  seats_under(decoy) == [], str(seats_under(decoy)))
            check(f"1.{label} — nothing was written inside --root either",
                  seats_under(root) == [], str(seats_under(root)))

        # ── 2. lint (the READ verb) refuses both forms rather than reading outside the root ────
        for label, name in (("absolute path", abs_name), ("`..` traversal", dots_name)):
            rc, so, se = run(TOOL, ["--root", str(root), "lint", name])
            check(f"2.{label} — lint exits nonzero", rc != 0, f"exit={rc}")
            check(f"2.{label} — lint refuses instead of reporting findings from outside the root",
                  "escapes --root" in se and "finding(s)" not in so,
                  f"stdout={so.strip()[:200]} stderr={se.strip()[:200]}")

        # ── 3. THE RED CONTROL — the pre-fix code MUST escape, or rows 1-2 score nothing ───────
        #
        # THE MUTANT MUST SIT AT THE TOOL'S OWN DEPTH. `goal_cli.py` resolves the `after`-member
        # grammar through `coord_source_path()`, which is `Path(__file__).resolve().parents[3] /
        # "team-kit" / "coord.py"`. A mutant dropped in a FLAT temp dir has no such ancestor, so
        # the grammar import failed and `materialize` died inside `after_pred_names` with a
        # traceback — before it ever reached the escape this arm exists to reproduce. The arm
        # then reported `mutant exit=1, wrote nothing` and declared itself INOPERATIVE, which is
        # exactly right and exactly useless: the red control for a CRITICAL defect could not
        # fire, so rows 1-2 had been scoring nothing since the day it was written.
        #
        # So the temp tree MIRRORS the real depth (`<mut>/capabilities/goals-tree/tool/`) and
        # `team-kit` is symlinked to the real one, putting `coord.py` exactly where
        # `parents[3]` looks. The link is READ-ONLY by construction — nothing here writes
        # through it, and `coord.py` is certified and never edited by a probe.
        mut_root = td / "mut"
        mutant = mut_root / "capabilities" / "goals-tree" / "tool" / TOOL.name
        mutant.parent.mkdir(parents=True)
        (mut_root / "team-kit").symlink_to(TOOL.resolve().parents[3] / "team-kit")
        src = TOOL.read_text(encoding="utf-8")
        mutated = src
        applied = 0
        for fixed, prefix in zip(FIXED_CALLS, PREFIX_CALLS):
            if fixed in mutated:
                mutated = mutated.replace(fixed, prefix)
                applied += 1
        if applied != len(FIXED_CALLS):
            inoperative(
                "3. mutation applies to the landed source",
                f"only {applied}/{len(FIXED_CALLS)} guarded call sites matched — the fix has been "
                "reshaped and this probe's red control no longer bites; rows 1-2 are therefore "
                "unproven, not green",
            )
        else:
            mutant.write_text(mutated, encoding="utf-8")
            rc, so, se = run(mutant, ["--root", str(root), "materialize", abs_name,
                                      "--catalog-root", str(catalog), "--json"])
            escaped = seats_under(decoy)
            ok_json = False
            try:
                ok_json = json.loads(so).get("ok") is True
            except Exception:                                     # noqa: BLE001
                ok_json = False
            if rc == 0 and escaped:
                check("3. RED CONTROL — the pre-fix code DOES escape --root (so rows 1-2 can fail)",
                      True, f"mutant wrote {escaped[0]} and reported ok={ok_json}")
            else:
                inoperative(
                    "3. RED CONTROL — the pre-fix code DOES escape --root",
                    f"mutant exit={rc}, wrote {escaped or 'nothing'} outside the root — the "
                    "escape could not be reproduced, so the green rows above discriminate nothing",
                )
            # the mutant's damage is confined to the throwaway tree; clean it so row 4 starts fresh
            shutil.rmtree(decoy / "runs" / "run-1" / "seats", ignore_errors=True)

        # ── 4. THE POSITIVE CONTROL — an ordinary in-root name is NOT refused ──────────────────
        contract = td / "contract.md"
        rc, _, se = run(TOOL, ["--root", str(root), "scaffold", "inside-goal",
                               "--contract", str(contract)])
        check("4. an in-root goal still scaffolds", rc == 0, se.strip()[:200])
        rc, so, se = run(TOOL, ["--root", str(root), "lint", "inside-goal"])
        check("4. an in-root goal is LINTED, not refused as an escape",
              "escapes --root" not in se and "goal-lint inside-goal" in so,
              f"exit={rc} stdout={so.strip()[:200]} stderr={se.strip()[:200]}")

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
