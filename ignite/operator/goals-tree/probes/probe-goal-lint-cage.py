#!/usr/bin/env python3
"""probe-goal-lint-cage.py — `rbtv-goal lint` can reach exit 0 on a goal-master goal, BOTH
uncaged and from inside a REAL cage that masks `seats/` to one seat's own folder (task 125).

TWO HALVES, one fixture. HALF ONE: a materialized goal-master seat's `relays:`/`rw-paths:`
frontmatter VALUES (`master`, `1-projects`, `2-areas`) are cage-grant data, not
cognitive-unit references — `LINT_NON_REF_KEYS` must exclude those keys or the walker reports
three false "no assembled block in the body" findings on every goal carrying a goal-master.
HALF TWO: the "taskforce row resolves to a real seat" criterion was a `Path.is_dir()` test
against `seats/<seat>`, but at spawn time `seats/` is masked (tmpfs + one bind, per
`envelope/cagespec.py`) to hold only the OCCUPANT's own folder — so every OTHER row's
folder reads "absent" from inside every cage, and no seat could ever pass the lint its own
done-contract asks for.

⚠ HALF TWO IS PROVEN WITH A REAL `bwrap` CAGE, not a simulation. The probe reproduces the
exact mount shape `cagespec.py` documents for `seats/<seat>` (`tmpfs:{goalDir}/seats` +
`bind:{goalDir}/seats/<occupant>`) and runs `goal_cli.py lint` inside it, as the occupant of
ONE seat in a two-seat taskforce — the other seat's folder is genuinely invisible, the same
way it would be for a real seated sitting. `--only lint-cage`, exit 0 = both halves hold ·
1 = a finding survived · 2 = INOPERATIVE (bwrap absent, or the fixture could not be built).
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
OUT = HERE / "probe-goal-lint-cage.out"
BWRAP = shutil.which("bwrap")

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


def run(args, cwd=None):
    r = subprocess.run(args, capture_output=True, text=True, timeout=120, cwd=cwd)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


GOAL_MASTER_SEAT_MD = """---
seat: goal-master
description: fixture goal-master, shaped like a real materialized one — `relays:` and
  `rw-paths:` are cage-grant VALUES this probe pins as the false-positive surface.
cwd: {cwd}/seats/goal-master/
agent_type: master
harness: claude
model: claude-opus-5
effort: medium
mode: interactive
auto-wake: 'yes'
component: {cwd}
relays: master
read-root: true
rw-paths:
- 1-projects
- 2-areas
human-interactive: true
fallback: block-and-queue
---
<permissions>
Read the tree. Write nothing.
</permissions>
"""

WORKER_SEAT_MD = """---
seat: worker-a
description: fixture worker — the OTHER seat, invisible from inside goal-master's cage.
cwd: {cwd}/seats/worker-a/
agent_type: worker
harness: claude
model: claude-opus-5
effort: medium
mode: headless
---
<permissions>
Read the tree. Write nothing.
</permissions>
"""


def build_fixture(td: Path):
    """A scaffolded goal (real `scaffold` verb, CMP-4 layout) plus a hand-placed taskforce
    of two seats — a goal-master (the false-positive surface) and a plain worker (the seat
    that goes invisible when the probe cages as goal-master)."""
    root = td / ".rbtv" / "goals"
    root.mkdir(parents=True)
    contract = td / "contract.md"
    contract.write_text("Prove lint reaches exit 0, caged and uncaged.\n", encoding="utf-8")
    rc, _, err = run([sys.executable, str(TOOL), "--root", str(root), "scaffold", "live-goal",
                      "--contract", str(contract), "--lane", "console"])
    if rc != 0:
        raise RuntimeError(f"could not scaffold the fixture goal: {err.strip()}")
    goal = root / "live-goal"
    goal.joinpath("taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        "tf-1,goal-master,,claude,claude-opus-5,medium,50,m1\n"
        "tf-1,worker-a,goal-master,claude,claude-opus-5,medium,50,m1\n",
        encoding="utf-8", newline="")
    seats = goal / "seats"
    (seats / "goal-master").mkdir(parents=True)
    (seats / "worker-a").mkdir(parents=True)
    (seats / "goal-master" / "seat.md").write_text(
        GOAL_MASTER_SEAT_MD.format(cwd=goal), encoding="utf-8")
    (seats / "worker-a" / "seat.md").write_text(
        WORKER_SEAT_MD.format(cwd=goal), encoding="utf-8")
    return root, goal


def main() -> int:
    OUT.write_text("", encoding="utf-8")   # truncate BEFORE any work — no evidence husk

    if not TOOL.is_file():
        inoperative("goal_cli.py is present", f"{TOOL} does not exist")
        OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory(prefix="probe-goal-lint-cage-") as _td:
        td = Path(_td)
        try:
            root, goal = build_fixture(td)
        except Exception as exc:                                    # noqa: BLE001
            inoperative("throwaway fixture builds", str(exc))
            OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
            return 2

        # ── HALF ONE + uncaged HALF TWO — a full-visibility console lint ──────────────────────
        rc, so, se = run([sys.executable, str(TOOL), "--json", "--root", str(root),
                          "lint", "live-goal"])
        try:
            payload = json.loads(so)
        except Exception:                                            # noqa: BLE001
            payload = {}
        findings = payload.get("findings", [])
        check("uncaged: lint exits 0 on a goal-master goal (relays/rw-paths excluded)",
              rc == 0 and payload.get("ok") is True and not findings,
              f"exit={rc} findings={findings}")
        surface_checks = {f.get("check") for f in findings}
        check("uncaged: no 'taskforce row resolves to a real seat' finding either",
              "taskforce row resolves to a real seat" not in surface_checks, str(findings))

        # ── HALF TWO, CAGED — a REAL bwrap mount masking seats/ to goal-master's own folder,
        # exactly `cagespec.py`'s `tmpfs:{goalDir}/seats` + `bind:{goalDir}/seats/<seat>` ──────
        if not BWRAP:
            inoperative("caged: lint exits 0 from inside a real seats/ mask",
                        "bwrap is not on PATH — cannot build the real cage this half needs")
        else:
            seats = goal / "seats"
            cage_cmd = [BWRAP, "--dev-bind", "/", "/",
                       "--tmpfs", str(seats),
                       "--bind", str(seats / "goal-master"), str(seats / "goal-master"),
                       "--", sys.executable, str(TOOL), "--json", "--root", str(root),
                       "lint", "live-goal"]
            rc, so, se = run(cage_cmd)
            try:
                payload = json.loads(so)
            except Exception:                                        # noqa: BLE001
                payload = {}
            findings = payload.get("findings", [])
            # Control: prove the mask actually bites, so a green lint below isn't green because
            # the cage silently failed to apply.
            rc_ls, so_ls, _ = run([BWRAP, "--dev-bind", "/", "/", "--tmpfs", str(seats),
                                   "--bind", str(seats / "goal-master"),
                                   str(seats / "goal-master"), "--", "ls", str(seats)])
            check("control: caged `ls seats/` sees ONLY goal-master, not worker-a",
                  rc_ls == 0 and so_ls.split() == ["goal-master"], repr(so_ls))
            check("caged: lint STILL exits 0 with worker-a's folder masked away",
                  rc == 0 and payload.get("ok") is True and not findings,
                  f"exit={rc} findings={findings} stderr={se.strip()[:200]}")

    failures = [lbl for ok, lbl in RESULTS if not ok]
    out("")
    out(f"checks: {len(RESULTS)}  failures: {len(failures)}  inoperative: {len(INOPERATIVE)}")
    for lbl, why in INOPERATIVE:
        out(f"  INOPERATIVE  {lbl}: {why}")
    for lbl in failures:
        out(f"  FAILED  {lbl}")
    OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")

    if failures:
        return 1
    return 2 if INOPERATIVE else 0


if __name__ == "__main__":
    sys.exit(main())
