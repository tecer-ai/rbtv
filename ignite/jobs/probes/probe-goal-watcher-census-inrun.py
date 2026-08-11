#!/usr/bin/env python3
"""probe-goal-watcher-census-inrun.py — ROW 8 counts THIS run's own not-yet-checked-in seats (7.714).

WHAT IT SCORES. `budget.py`'s `census()` files a live agent pane carrying
`agent_type_source: no-seat` under rule 3, and rule 3 asks only whether SOME goal declares the
pane's cwd. A seat this run LAUNCHED but that has not run its own `cmd_checkin` yet has exactly
that shape — no roster row, a descriptor that IS declared — so it lands in `cross_goal`, which
`census()` deliberately keeps OUT of `in_use`. The room therefore under-counts itself and ROW 8's
BREACH verdict arrives LATE, which is the wrong direction for a cap.

Task 7.555 corrected this at `coord.py` cmd_launch (D5); the owner ruled 2026-08-11 that the
correction stays PER CONSUMER and is PORTED to the second and only other consumer, ROW 8 of
`goal-watcher-job.py`. This probe is that row's guard.

⚠ THE TERM IS ON THE ROW, NEVER ON THE CLASS, and that is why R3 exists. A legitimate other-goal
seat and a same-run leak carry the SAME class value (`cross_goal`), so nothing about class
membership separates them — only each row's own emitted `descriptor` does. A correction that
counted the whole class would turn a foreign goal's seat into this room's breach, which is a
different defect wearing the same fix.

RED-FIRST. Set `RBTV_PROBE_TREE` to an alternative rbtv repo root and every arm re-runs against
THAT tree's `goal-watcher-job.py`. Pointed at a pre-7.714 tree, R1/R2/R3 go red and C0 stays green
— R3 goes red WITH them by construction, because its second half asserts the in-run fixture DOES
flag; an R3 that stayed green there would be a tree-independent restatement, which is exactly what
its both-halves-in-one-arm shape exists to prevent. `TARGET`
derives solely from that knob with no fallback, so pointing it at an empty directory fails C0
rather than silently passing.

ARMS
  C0  THE FIXTURE IS REAL, IN EITHER TREE: `census()` over this fixture files the launched-but-
      unchecked-in pane as `cross_goal` with a `descriptor` INSIDE the run's own `seats/`, and its
      raw `in_use` sits exactly AT the cap with a NON-breach verdict. That is the under-count this
      row exists to correct, established from the census itself rather than assumed.
  R1  THE CORRECTION FIRES: `evaluate` over that same fixture yields a BUDGET / ROOM OVER CAPACITY
      decision. On the uncorrected logic there is none — the raw verdict is not BREACH.
  R2  THE CORRECTION PATH ACTUALLY COUNTED THE ROW: the decision reports the CORRECTED pane count
      (raw `in_use` + the in-run rows) and how far over the cap that puts the room, and names the
      in-run rows rather than reporting a number a reader cannot source.
  R3  DERIVED FROM THE ROW, NOT THE CLASS: the SAME fixture with that pane's descriptor resolving
      OUTSIDE this run's `seats/` yields NO budget decision at all, WHILE the in-run one does —
      both halves in one arm, so it cannot pass on a tree that simply never flags anything. The
      over-correction it guards against is silent: a room flagged over capacity for a seat that
      is not its own reads identically to a real breach.

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP. If `goal-watcher-job.py` is missing or will not
import, this probe FAILS. INOPERATIVE (exit 2) is for the probe itself being unable to run.

Run it through the suite — `node ignite/deploy/probe-suite.js --only goal-watcher-census-inrun` —
never by hand (`G-163`). Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import importlib.util
import json
import os
import sys
import tempfile
import time
import types
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

# The target's module-level imports are POSIX-only (`jobcontain` -> fcntl + resource). Neither is
# touched by the pure predicates under test, so on a non-POSIX host they are stubbed rather than
# letting the probe report INOPERATIVE — a probe that can only run on one OS measures nothing on
# the other, and `ModuleNotFoundError` reads as evidence while measuring exactly nothing.
for _m, _attrs in (("fcntl", {"LOCK_EX": 2, "LOCK_NB": 4, "flock": lambda *a: None}),
                   ("resource", {"RLIMIT_AS": 9, "RLIMIT_CPU": 0, "RLIM_INFINITY": -1,
                                 "getrlimit": lambda k: (-1, -1),
                                 "setrlimit": lambda k, v: None})):
    try:
        __import__(_m)
    except ImportError:
        _mod = types.ModuleType(_m)
        _mod.__dict__.update(_attrs)
        sys.modules[_m] = _mod

HERE = Path(__file__).resolve().parent
# HERE = <root>/ignite/jobs/probes -> parents[2] is the rbtv repo root. `RBTV_PROBE_TREE` is the
# RED-FIRST knob (see the docstring): it re-points every arm at another tree's sources.
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "ignite" / "jobs" / "goal-watcher-job.py"
OUT = HERE / "probe-goal-watcher-census-inrun.out"

CAP = 2                 # declared cap; the two checked-in workers below sit exactly ON it
LATE = "worker-late"    # the seat this run launched and that has not checked in yet

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


def load_target():
    spec = importlib.util.spec_from_file_location("gwj_census_under_probe", TARGET)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gwj_census_under_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


def build_package(tmp):
    """Write the run package ROW 8 reads, plus an OUTSIDE-the-run seat for R3's other half.

    Real files, because both halves of the split are resolved off disk: `budget.json` by ROW 8's
    own existence test, and each descriptor by `budget.resolve_descriptor` walking up from the
    pane's cwd. A fixture that faked either would measure a mock.
    """
    pkg = tmp / "runs" / "run-1"
    (pkg / "seats" / LATE).mkdir(parents=True)
    (pkg / "seats" / LATE / "seat.md").write_text("# in-run seat, launched, not checked in\n")
    (pkg / "budget.json").write_text(json.dumps({
        "cap": {"agent_panes": CAP},
        "counting": {"counts_toward_cap": ["worker"]},
    }))
    # An OUTSIDE-the-run seat folder, for R3's foreign half: declared (so `census()` still files it
    # `cross_goal` rather than `unaccounted`) but resolving nowhere near this run's `seats/`.
    other = tmp / "runs" / "run-other" / "seats" / "worker-elsewhere"
    other.mkdir(parents=True)
    (other / "seat.md").write_text("# another goal's seat\n")
    return pkg, other


def fixture(now, pkg, late_cwd):
    """ONE snapshot: the cap FULL of checked-in workers, plus one live pane with NO roster row.

    `agent_type_source: no-seat` with an agent harness is precisely rule 3's input; whether that
    pane is ours or another goal's is decided ONLY by where `late_cwd` resolves.
    """
    return {
        "captured_at": now, "captured_at_iso": "fixture",
        "headless": [], "headless_source": {"readable": True, "reason": ""},
        "roster_absent": [],
        "seats": [
            {"seat": "worker-a", "pane": "%1", "roster_active": True, "liveness": "live",
             "agent_type": "worker", "agent_type_source": "descriptor",
             "harness": "claude", "cwd": str(pkg), "last_activity_age_s": 1, "ctx_pct": None},
            {"seat": "worker-b", "pane": "%2", "roster_active": True, "liveness": "live",
             "agent_type": "worker", "agent_type_source": "descriptor",
             "harness": "claude", "cwd": str(pkg), "last_activity_age_s": 1, "ctx_pct": None},
            {"seat": None, "pane": "%3", "roster_active": False, "liveness": "live",
             "agent_type": None, "agent_type_source": "no-seat",
             "harness": "claude", "cwd": str(late_cwd), "last_activity_age_s": 1, "ctx_pct": None},
        ],
    }


def budget_rows(gwj, snap, pkg, now):
    args = gwj._ns(coord="/nonexistent/co ord.py", package=str(pkg), caller_ident=(4242, "99"))
    decisions = gwj.evaluate(snap, args, {}, {}, now)[0]
    return [d for d in decisions if d["class"] == "BUDGET"]


def main():
    if not TARGET.exists():
        # ⚠ NOT a skip: the target's absence IS a failure of the property under test.
        check("C0", False, f"{TARGET} does not exist — ROW 8 cannot carry a correction in a file "
                           f"that is gone")
        return
    gwj = load_target()
    now = time.time()
    with tempfile.TemporaryDirectory(prefix="gwj-census-inrun-") as td:
        pkg, other = build_package(Path(td))
        in_run_snap = fixture(now, pkg, pkg / "seats" / LATE)
        foreign_snap = fixture(now, pkg, other)

        # ---- C0: the under-count is REAL, established off the census itself, in EITHER tree.
        c = gwj.budget_mod.census(json.loads((pkg / "budget.json").read_text()), in_run_snap, now)
        seats_root = os.path.join(os.path.abspath(str(pkg)), "seats") + os.sep
        inside = [r for r in c["cross_goal"]
                  if os.path.abspath(r.get("descriptor") or "").startswith(seats_root)]
        check("C0", len(inside) == 1 and c["in_use"] == CAP and c["verdict"] != "BREACH",
              f"census files {len(inside)} cross_goal row(s) inside {seats_root!r}; raw "
              f"in_use={c['in_use']} against cap={c['cap']} -> verdict={c['verdict']!r} — the "
              f"launched seat is invisible to the cap")

        # ---- R1: the correction fires on that same fixture.
        rows = budget_rows(gwj, in_run_snap, pkg, now)
        detail = " || ".join(d.get("detail") or "" for d in rows)
        check("R1", len(rows) == 1 and "OVER CAPACITY" in (rows[0].get("action") or ""),
              f"{len(rows)} BUDGET row(s); action="
              f"{(rows[0].get('action') if rows else None)!r}")

        # ---- R2: it counted the ROW, and says so with sourceable numbers.
        corrected = c["in_use"] + len(inside)
        check("R2", bool(rows) and f"{corrected} agent panes" in detail
              and f"({corrected - CAP} over)" in detail and "not yet checked in" in detail,
              f"detail reports the corrected count {corrected} and {corrected - CAP} over cap "
              f"{CAP}, naming the in-run rows: {detail[:160]!r}")

        # ---- R3: the row, not the class — BOTH halves here, so it cannot pass on a tree that
        # never flags anything at all.
        foreign = budget_rows(gwj, foreign_snap, pkg, now)
        check("R3", not foreign and len(rows) == 1,
              f"the SAME pane with its descriptor under {str(other)!r} yields {len(foreign)} "
              f"BUDGET row(s) while the in-run one yields {len(rows)}")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-goal-watcher-census-inrun  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
