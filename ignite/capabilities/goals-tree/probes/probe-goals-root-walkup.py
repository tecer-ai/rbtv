#!/usr/bin/env python3
"""probe-goals-root-walkup.py — `resolve_goals_root` scans for an ENCLOSING goals tree FIRST.

THE DEFECT IT SCORES (measured 2026-08-12, channel-master's misrooted sitting): `resolve_goals_root`
had ONE scan — walk up from cwd looking for a CHILD `.rbtv/goals` under each ancestor. A seat runs
with cwd inside its own seat folder, `<goals>/<goal>/runs/<run>/seats/<seat>/`; a cwd-RELATIVE
`--inbox` handed to `master_profile.py` `mkdir -p`'d a stray `.rbtv/goals` THERE, and from that
moment the child scan matched the seat's own poisoned tree before it ever reached the real root —
from EVERY seat cwd under it. The seat's next `scaffold` created a real goal inside the poison,
where nothing enumerates it. The fix adds a scan for an ancestor that IS a goals tree
(`name == "goals"` under a `.rbtv` parent) and runs it BEFORE the child scan.

⚠ THE ORDER IS THE WHOLE FIX, AND THAT IS WHAT THE MUTANT ATTACKS. Both scans, in either order,
return SOMETHING; a probe that only asserted "a root was found" would be green on the defect. So
the red control (row 4) does not delete the new scan — it SWAPS the two loops, leaving both present
and every line of logic intact, and REQUIRES the scaffold to land in the poison. A mutant that
still lands in the real root means rows 1-3 discriminate nothing and this probe exits 2
(INOPERATIVE), never 0.

The rows:

  1. THE INCIDENT ITSELF — from a seat cwd with a poisoned nested `.rbtv/goals` present, `scaffold`
     lands the goal (and `goals.csv`) in the ENCLOSING root, and the poison is left EMPTY.
  2. THE OVER-REACH CONTROL — from INSIDE the nested tree, that tree is still its own root. The fix
     must not mean "always the outermost": a genuinely nested workspace, entered on purpose, keeps
     answering for itself. Non-discriminating against the defect BY DESIGN (both orders agree
     here); it is what stops the fix being a blanket rule.
  3. THE PLAIN-WORKSPACE CONTROL — from an ordinary directory that is not inside any goals tree,
     the CHILD scan still resolves `<ws>/.rbtv/goals`. The new loop must not have shadowed it.
  4. THE RED CONTROL — the two loops swapped; row 1's scaffold MUST land in the poison.

Every path is a throwaway tree under `tempfile`, and every scaffold runs with cwd inside it. The
live `.rbtv/goals` package is never read and never written, by the tool or by the mutant.

Run it through the suite — `node deploy/probe-suite.js --only goals-root-walkup` — never by hand
(`G-163`). Exit 0 = the enclosing tree wins and the mutant proved the order can fail · 1 = a
property is broken · 2 = INOPERATIVE (could not run, or the red control did not go red).
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "tool" / "goal_cli.py"
OUT = HERE / "probe-goals-root-walkup.out"

# The mutation as a FORM, not as a line number: it captures the two scans of `resolve_goals_root`
# and re-emits them in the OPPOSITE order. Both must match exactly once — a source where either
# loop has been reworded is a source this control no longer bites, and row 4 reports INOPERATIVE
# rather than passing on a mutation it never applied.
SWAP_RE = re.compile(
    r'(    for cand in \(here, \*here\.parents\):\n'
    r'        if cand\.name == "goals" and cand\.parent\.name == "\.rbtv":\n'
    r'            return cand\n)'
    r'(    for cand in \(here, \*here\.parents\):\n'
    r'        goals = cand / "\.rbtv" / "goals"\n'
    r'        if goals\.is_dir\(\):\n'
    r'            return goals\.resolve\(\)\n)')

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


def scaffold(tool: Path, cwd: Path, name: str, contract: Path):
    """`scaffold` with NO `--root` — the whole point is what cwd resolves to. It is the write verb
    the incident actually took, and it also reindexes, so the resolved root gets TWO observable
    artifacts (`<name>/goal.md` and `goals.csv`) rather than one."""
    r = subprocess.run([sys.executable, "-B", str(tool), "scaffold", name,
                        "--contract", str(contract), "--lane", "console"],
                       capture_output=True, text=True, timeout=120, cwd=str(cwd))
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def goals_in(root: Path):
    return sorted(p.parent.name for p in root.glob("*/goal.md"))


def build(td: Path):
    """A real workspace, a seat folder deep inside its goals tree, and the POISON in that seat.

    `<td>/ws/.rbtv/goals/`                                   the enclosing (real) root
    `<td>/ws/.rbtv/goals/host-goal/runs/r1/seats/s1/`        the seat cwd
    `<td>/ws/.rbtv/goals/host-goal/runs/r1/seats/s1/.rbtv/goals/`   the poison

    The host goal is a bare folder rather than a scaffolded one on purpose: `reindex` runs on every
    scaffold and projects every `goal.md` under the root, so a half-built neighbour would refuse
    row 1 for a reason that has nothing to do with cwd resolution.
    """
    ws = td / "ws"
    real = ws / ".rbtv" / "goals"
    seat = real / "host-goal" / "runs" / "r1" / "seats" / "s1"
    poison = seat / ".rbtv" / "goals"
    poison.mkdir(parents=True)
    contract = td / "contract.md"
    contract.write_text("Ship the thing.\n", encoding="utf-8")
    return real, seat, poison, contract


def main() -> int:
    OUT.write_text("", encoding="utf-8")   # truncate BEFORE any work — no evidence husk

    if not TOOL.is_file():
        inoperative("goal_cli.py is present", f"{TOOL} does not exist")
        OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory(prefix="probe-goals-root-walkup-") as _td:
        td = Path(_td).resolve()

        # ── 1. THE INCIDENT — a seat cwd under a poisoned tree still resolves to the real root ──
        real, seat, poison, contract = build(td)
        rc, so, se = scaffold(TOOL, seat, "probe-goal-a", contract)
        check("1. scaffold from a poisoned seat cwd succeeds", rc == 0,
              f"exit={rc} stderr={se.strip()[:300]}")
        check("1. the goal landed in the ENCLOSING root, not the seat's nested tree",
              goals_in(real) == ["probe-goal-a"], f"enclosing={goals_in(real)}")
        check("1. the poisoned nested tree is still EMPTY — no goal was created inside the seat",
              goals_in(poison) == [] and sorted(p.name for p in poison.iterdir()) == [],
              f"poison holds {sorted(p.name for p in poison.iterdir())}")
        check("1. reindex wrote goals.csv into the enclosing root and nowhere else",
              (real / "goals.csv").is_file() and not (poison / "goals.csv").exists(),
              f"real={(real / 'goals.csv').is_file()} poison={(poison / 'goals.csv').exists()}")

        # ── 2. THE OVER-REACH CONTROL — inside the nested tree, it answers for ITSELF ──────────
        rc, so, se = scaffold(TOOL, poison, "probe-goal-b", contract)
        check("2. scaffold from INSIDE the nested tree succeeds", rc == 0,
              f"exit={rc} stderr={se.strip()[:300]}")
        check("2. it landed in the nested tree — the fix is not 'always the outermost'",
              goals_in(poison) == ["probe-goal-b"] and goals_in(real) == ["probe-goal-a"],
              f"nested={goals_in(poison)} enclosing={goals_in(real)}")

        # ── 3. THE PLAIN-WORKSPACE CONTROL — the CHILD scan still works where it is the only one ─
        plain = td / "plain"
        (plain / ".rbtv" / "goals").mkdir(parents=True)
        rc, so, se = scaffold(TOOL, plain, "probe-goal-c", contract)
        check("3. an ordinary workspace dir still resolves its own child .rbtv/goals",
              rc == 0 and goals_in(plain / ".rbtv" / "goals") == ["probe-goal-c"],
              f"exit={rc} got={goals_in(plain / '.rbtv' / 'goals')} stderr={se.strip()[:200]}")

    # ── 4. THE RED CONTROL — swap the two scans and row 1 MUST land in the poison ──────────────
    #
    # THE MUTANT SITS AT THE TOOL'S OWN DEPTH. `goal_cli.py` reaches `team-kit/coord.py` through
    # `Path(__file__).resolve().parents[3]`; a mutant in a flat temp dir has no such ancestor and
    # dies on the import — a crash wearing a red verdict, which would report this control as
    # firing when it never ran the code under test.
    with tempfile.TemporaryDirectory(prefix="probe-goals-root-walkup-mut-") as _td:
        td = Path(_td).resolve()
        src = TOOL.read_text(encoding="utf-8")
        mutated, applied = SWAP_RE.subn(r"\2\1", src)
        if applied != 1:
            inoperative(
                "4. the mutation swaps the two scans of resolve_goals_root",
                f"the two-loop form matched {applied} time(s) in {TOOL.name}, expected exactly 1 — "
                "one of the scans has been reworded, so this probe's red control no longer bites "
                "and rows 1-3 are unproven, not green. Re-derive SWAP_RE against the landed source.")
        else:
            try:
                compile(mutated, "mutant", "exec")
            except SyntaxError as exc:                             # noqa: BLE001
                inoperative("4. the swapped source is valid Python", f"{exc}")
            else:
                mut_root = td / "mut"
                mutant = mut_root / "capabilities" / "goals-tree" / "tool" / TOOL.name
                mutant.parent.mkdir(parents=True)
                (mut_root / "team-kit").symlink_to(TOOL.resolve().parents[3] / "team-kit")
                mutant.write_text(mutated, encoding="utf-8")
                real, seat, poison, contract = build(td)
                rc, so, se = scaffold(mutant, seat, "probe-goal-a", contract)
                if rc == 0 and goals_in(poison) == ["probe-goal-a"] and goals_in(real) == []:
                    check("4. RED CONTROL — child-scan-first DOES land the goal in the poison "
                          "(so rows 1-3 can fail)", True,
                          f"mutant wrote {poison / 'probe-goal-a'}")
                else:
                    inoperative(
                        "4. RED CONTROL — child-scan-first lands the goal in the poison",
                        f"mutant exit={rc}, poison={goals_in(poison)}, enclosing={goals_in(real)} — "
                        "the misrooting could not be reproduced with the scans swapped, so the "
                        "green rows above discriminate nothing. stderr: " + se.strip()[:200])

    failures = [lbl for ok, lbl in RESULTS if not ok]
    out("")
    out(f"checks: {len(RESULTS)}  failures: {len(failures)}  inoperative: {len(INOPERATIVE)}")
    for lbl, why in INOPERATIVE:
        out(f"  INOPERATIVE  {lbl}: {why}")
    for lbl in failures:
        out(f"  FAILED  {lbl}")
    OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")

    # A REAL failure outranks INOPERATIVE (the sibling probe-goal-root-escape.py carries the same
    # mapping and the reason): a live misroot reds rows 1-2 AND can strand row 4, and reporting
    # that as "could not run" buries a goal being created where nothing enumerates it.
    if failures:
        return 1
    return 2 if INOPERATIVE else 0


if __name__ == "__main__":
    sys.exit(main())
