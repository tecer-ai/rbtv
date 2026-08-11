#!/usr/bin/env python3
"""probe-goal-watcher-worktree-watch-start.py — the un-cleaned-worktree report also fires ONCE
when a healthy watch starts, not only from the refusal branch (task 7.557).

WHAT IT SCORES. Before this fix `[WORKTREE-SWEEP]` only ever printed from the REFUSAL branch of
`main()` (the job could not find exactly one live run to watch). While a run is healthy and being
watched normally, leftover per-seat worktrees under `{workspace}/.rbtv/worktrees/` went unreported
until something else checked later. The owner ruled (2026-08-08) for a check ONCE at watch-start —
explicitly NOT every cycle, to close the blind spot without per-cycle cost.

EVERYTHING RUNS AGAINST A FIXTURE WORKSPACE IN A SCRATCH DIR, with a STUB `coord.py` (`cmd_send`,
`derive_lease`, both no-ops/deterministic) so no real coord or lease file is read or written.

ARMS
  W1  RED/GREEN — a package carrying ONE leftover worktree is watched HEALTHILY (an explicit
      `--room-package` override so room resolution always succeeds). Pre-fix (reverted target via
      RBTV_PROBE_GWJ) pass 1 prints NO `[WORKTREE-SWEEP]` line. Post-fix (shipped target, the
      default) pass 1 DOES, naming the goal and the one leftover.
  W2  ONCE PER WATCH — passes 2-4 against the SAME package (same on-disk watch state) print NO
      further `[WORKTREE-SWEEP]` line; the total count across all 4 passes is exactly 1. A
      per-cycle regression (the owner-ruled-out failure mode) would make this count 4.
  W3  A NEW WATCH RE-REPORTS — a second, distinct package (a fresh `coordination/` folder, i.e. a
      fresh watch) reports again on ITS pass 1. Proves the gate is watch-scoped, not "ever".
  W4  REFUSAL BRANCH UNCHANGED — a pass with NO `--room-package` and a lease the stub reports
      UNREADABLE hits the refusal branch (exit 2) and STILL prints the WHOLE report for the same
      goal: the marker, the leftover NAMED, and the remedy line. Graded on the payload, not on
      the marker's presence — the extraction into `report_worktree_leftovers` is exactly the
      change that could preserve the marker while dropping what it carries.

RED-FIRST PROOF: run this probe with RBTV_PROBE_GWJ pointing at a scratch copy of
`goal-watcher-job.py` with the 7.557 hunk reverted — W1's post-fix half and W2/W3 fail (W4, the
refusal branch, still passes: it predates this task). The env override defaults to the shipped
file, which is GREEN throughout.

Run it through the suite — `node ignite/deploy/probe-suite.js --only goal-watcher-worktree-watch-start`
— never by hand (`G-163`).
Exit 0 = green · 1 = the once-per-watch contract is broken · 2 = INOPERATIVE.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TARGET = Path(os.environ.get("RBTV_PROBE_GWJ") or (HERE.parent / "goal-watcher-job.py"))
OUT = HERE / "probe-goal-watcher-worktree-watch-start.out"

STUB_COORD = '''"""Stub coord for probe-goal-watcher-worktree-watch-start — cmd_send + derive_lease only."""
import os


def cmd_send(ns):
    with open(os.environ["PROBE_COORD_LOG"], "a", encoding="utf-8") as fh:
        fh.write(f"{ns.to}|{ns.message.splitlines()[0]}\\n")


def derive_lease(goal):
    """Deterministic refusal for W4: no lease file, no rooms — UNREADABLE, never guessed."""
    return {}, "no lease file (probe stub — deliberately unreadable)"
'''

lines, failures, inoperative = [], [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def stop(tag, detail):
    say(f"INOP  {tag}  {detail}")
    inoperative.append(tag)


def make_fixture(root, name):
    """A workspace with ONE leftover worktree for `<name>-goal`, and a distinct package to watch
    it from. Layout: `<root>/<name>-ws/.rbtv/{goals/<name>-goal, worktrees/repo--<name>-goal--s1}`
    and `<root>/<name>-pkg/coordination/`."""
    ws = root / f"{name}-ws"
    goal = ws / ".rbtv" / "goals" / f"{name}-goal"
    goal.mkdir(parents=True)
    worktrees = ws / ".rbtv" / "worktrees"
    worktrees.mkdir(parents=True)
    (worktrees / f"repo--{name}-goal--seat1").mkdir()
    pkg = root / f"{name}-pkg"
    (pkg / "coordination").mkdir(parents=True)
    return pkg, goal


def snapshot(pkg):
    """A FRESH, healthy snapshot — one live leader seat, nothing flagged."""
    import json
    now = time.time()
    (pkg / "state.json").write_text(json.dumps({
        "captured_at": now,
        "captured_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
        "seats": [{"seat": "leader", "pane": "%0", "liveness": "live", "harness_pid": 1,
                   "roster_active": True}],
        "roster_absent": [], "headless": [],
        "headless_source": {"readable": True, "reason": ""},
        "run": {"ready_rows": 0, "live_executors": 0, "queued": 0,
                "source": {"ready_rows": "", "queued": {"reason": ""}}},
    }), encoding="utf-8")


def run_pass(pkg, goal, coord, room_package=True):
    """One `main()` invocation. `room_package=True` forces healthy resolution (`--room-package`
    explicit override); `False` omits it so `resolve_room_package` falls to the stub's refused
    `derive_lease` — the REFUSAL branch (W4)."""
    snapshot(pkg)
    cmd = [sys.executable, "-B", str(TARGET),
           "--package", str(pkg), "--room-goal", str(goal), "--coord", str(coord),
           "--mem-floor-mb", "2000", "--reflag-min", "0"]
    if room_package:
        cmd += ["--room-package", str(pkg)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                          env=dict(os.environ, PROBE_COORD_LOG=str(pkg.parent / "coord.log")))
    return res.returncode, res.stdout + res.stderr


def main():
    if not TARGET.exists():
        stop("PROBE", f"{TARGET} does not exist — the job carrying the contract is gone")
        return
    root = Path(tempfile.mkdtemp(prefix="probe-gwj-worktree-watch-"))
    try:
        coord = root / "coord.py"
        coord.write_text(STUB_COORD, encoding="utf-8")

        # ---- W1/W2: one watch (one package), several cycles
        pkg, goal = make_fixture(root, "a")
        outs = []
        for i in range(4):
            rc, out = run_pass(pkg, goal, coord, room_package=True)
            outs.append(out)
            if i == 0 and rc != 0:
                stop("W1", f"pass1 exited {rc} on a healthy fixture — nothing scorable: {out[-800:]}")
                return

        sweeps = [i for i, o in enumerate(outs) if "[WORKTREE-SWEEP]" in o]
        p1 = outs[0]
        check("W1", sweeps == [0]
              and "1 leftover worktree(s): repo--a-goal--seat1" in p1
              and "a-goal" in p1 and "worktree-flow.py" in p1,
              f"healthy pass 1 reported the leftover (sweep-bearing passes={sweeps}); "
              f"pass1 line: {[ln for ln in p1.splitlines() if 'WORKTREE-SWEEP' in ln]}")
        check("W2", sweeps == [0],
              f"ONCE PER WATCH: only pass 1 of 4 against the same package carried the report "
              f"(sweep-bearing passes={sweeps}, expected [0] — a per-cycle regression would "
              f"give [0, 1, 2, 3])")

        # ---- W3: a SECOND, distinct watch (fresh package) re-reports on ITS pass 1
        pkg2, goal2 = make_fixture(root, "b")
        rc2a, out2a = run_pass(pkg2, goal2, coord, room_package=True)
        rc2b, out2b = run_pass(pkg2, goal2, coord, room_package=True)
        check("W3", "[WORKTREE-SWEEP]" in out2a and "b-goal" in out2a
              and "[WORKTREE-SWEEP]" not in out2b,
              f"a NEW watch (fresh package) reports on ITS pass 1 (rc={rc2a}) and stays quiet on "
              f"pass 2 (rc={rc2b}) — the gate is per-watch, not a one-time global flag")

        # ---- W4: refusal branch — unchanged, still reports
        pkg3, goal3 = make_fixture(root, "c")
        rc3, out3 = run_pass(pkg3, goal3, coord, room_package=False)
        check("W4", rc3 == 2 and "REFUSING TO START" in out3
              and "[WORKTREE-SWEEP] c-goal" in out3
              and "1 leftover worktree(s): repo--c-goal--seat1" in out3
              and "remedy:" in out3 and "worktree-flow.py" in out3,
              f"the pre-existing refusal-branch report still fires (exit={rc3}): "
              f"{[ln for ln in out3.splitlines() if 'WORKTREE-SWEEP' in ln or 'REFUSING' in ln]}")
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-goal-watcher-worktree-watch-start  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
