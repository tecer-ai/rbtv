#!/usr/bin/env python3
"""probe-one-room-relaunch-ladder.py — EXACTLY ONE bounded room-relaunch ladder acts on a room.

WHAT IT SCORES (task 7.664; kit behaviour map row B21). Until this task there were TWO independent
bounded relaunch ladders acting on the SAME room: `ignite/team-kit/watch.py` and
`orchestration/cli/team-monitor/team_monitor.py`. Both derive their own lease reading, both spend
their own backoff budget, and both run `tmux new-session -d -s <room>` on the same name. Two
mechanisms that can disagree and BOTH ACT is the failure `ignite/jobs/goal-watcher-job.py` says the
architecture exists to prevent, and it was LIVE, not theoretical. 7.664 removed the `watch.py`
ladder; `team_monitor.relaunch_room()` is the survivor. Task 7.35 then deleted `watch.py`
itself, so R1 no longer drives that loop — it asserts the file is GONE, which is the strongest
form of "it issues no relaunch".

⚠ ZERO IS AS RED AS TWO, AND R2 IS WHERE THAT IS CHECKABLE. The property is not "watch.py stopped
relaunching" — a task that deleted BOTH ladders would satisfy that and leave a crashed room with
nothing to restore it. The property is that the count is ONE and that the survivor is named.

⚠ R1 WAS DRIVEN AND IS NOW ABSENCE. It used to run the REAL `watch_loop` over a lease pinned
`gone` and count `tmux new-session` at that module's OWN `subprocess` seam. Task 7.35 deleted the
file, and a deleted loop cannot smuggle a relaunch back under another name — so the driven
measurement is replaced by the fact that subsumes it: the second ladder's whole FILE is gone.

RED-FIRST, and it still works. `RBTV_PROBE_TREE` names an alternative rbtv repo root and
re-points the `watch.py` LOOKUP — and only that lookup — at that tree. Pointed at a pre-7.35
tree, R1 and R2 go red (the file is there, and it carries `relaunch_room`) and C0 stays green.
`team_monitor.py` is always read from the live tree: it is the survivor this probe measures
AGAINST, not a thing under test.

ARMS
  C0  THE FIXTURE MEASURES RELAUNCHES AT ALL: the surviving ladder, driven through the same spy,
      really does issue one `tmux new-session` for the room. Vacuity guard — if this reds, a green
      R1 means only that the spy is deaf.
  R1  ABSENCE: `ignite/team-kit/watch.py` does not exist, so the second loop cannot relaunch
      anything. Pointed at a pre-7.35 tree by `RBTV_PROBE_TREE` this reds.
  R2  COUNTED, NOT ASSUMED: of the two sensors, EXACTLY ONE carries a room-relaunch actuator, and
      it is `team_monitor`. Two is the defect; zero is a room nothing restores.
  R3  THE SURVIVOR IS STILL BOUNDED: `team_monitor.RELAUNCH_BACKOFF_S` is a non-empty tuple
      whose LENGTH is the attempt cap, so no second constant can disagree with it.

⚠ AN ABSENT SURVIVOR IS THE FAILURE, NEVER A SKIP. If `team_monitor.py` is missing or will not
import, its arms FAIL. (`watch.py`'s absence is the property, not a skip.) INOPERATIVE (exit 2) is for the probe itself being unable to run.

⚠ IT TOUCHES NO ROOM, NO GOAL AND NO `.rbtv/`. Every `subprocess` call on the loop's path is
intercepted by the spy; the run root is a throwaway temp dir; no tmux binary is required, so this
runs on any host (run decision D4 of `orch-0810-watchpy-split`).

Run it through the suite — `node ignite/deploy/probe-suite.js --only one-room-relaunch-ladder` —
never by hand (`G-163`). Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import os as _os, sys as _sys, pathlib as _pl  # task 7.630: solo-run tmux isolation, FIRST
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "team-kit" / "self_isolate.py").is_file()) / "team-kit"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import importlib.util
import inspect
import os
import sys
import tempfile
import time
import types
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

# `team_monitor` imports POSIX-only modules at module level; the ladder under measurement touches
# neither, so they are stubbed rather than letting the probe report INOPERATIVE on a non-POSIX host.
# A probe that can only run on one OS measures nothing on the other.
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
# HERE = <root>/ignite/team-kit/probes -> parents[2] is the rbtv repo root.
LIVE_ROOT = HERE.parents[2]
WATCH_ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or LIVE_ROOT)
WATCH = WATCH_ROOT / "ignite" / "team-kit" / "watch.py"
MONITOR = LIVE_ROOT / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"
OUT = HERE / "probe-one-room-relaunch-ladder.out"

ROOM = "zzprobe-one-ladder"

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


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class Spy:
    """Stands in for the `subprocess` module on the loop's path and records every argv."""

    def __init__(self):
        self.calls = []

    def run(self, argv, *a, **kw):
        self.calls.append(list(argv))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    def Popen(self, argv, *a, **kw):                           # noqa: N802 — mirrors subprocess
        self.calls.append(list(argv))
        return types.SimpleNamespace(pid=0, returncode=0)

    def new_sessions(self):
        return [c for c in self.calls
                if len(c) >= 2 and c[0] == "tmux" and c[1] == "new-session"]


def main():
    if not MONITOR.is_file():
        # ⚠ NOT a skip: an absent SURVIVOR is a failure of the property under test — zero
        # ladders is a crashed room with nothing to restore it.
        check("C0", False, f"{MONITOR} does not exist — the one-ladder property cannot hold "
                          f"when the survivor is gone")
        return
    tm = load("tm_under_probe", MONITOR)

    # ---- C0: the spy really does hear a relaunch.
    spy0 = Spy()
    ok0, detail0 = tm.relaunch_room(ROOM, run_fn=spy0.run)
    check("C0", ok0 and len(spy0.new_sessions()) == 1,
          f"the SURVIVING ladder relaunches through the spy: ok={ok0}, "
          f"new-session calls={spy0.new_sessions()}, detail={detail0!r} — so a zero count at R1 is "
          f"a measurement, not a deaf fixture")

    # ---- R1: the second ladder's whole FILE is gone (task 7.35), which subsumes the driven
    # measurement this arm used to take: a deleted loop issues nothing under any name.
    check("R1", not WATCH.exists(),
          f"{WATCH} exists={WATCH.exists()} — the second bounded relaunch ladder lived in that "
          f"file and it was deleted with it; RBTV_PROBE_TREE aimed at a pre-7.35 tree reds this")

    # ---- R2: the COUNT, and the survivor by name.
    carriers = (["watch"] if WATCH.exists() else []) + (
        ["team_monitor"] if callable(getattr(tm, "relaunch_room", None)) else [])
    check("R2", carriers == ["team_monitor"],
          f"room-relaunch actuators across the two sensors: {carriers} — the property is EXACTLY "
          f"one, named. Two is the defect this task removed; zero would be a crashed room with "
          f"nothing to restore it")

    # ---- R3: the survivor is bounded.
    backoff = getattr(tm, "RELAUNCH_BACKOFF_S", None)
    check("R3", isinstance(backoff, tuple) and len(backoff) > 0,
          f"the survivor's bound is {backoff} ({len(backoff) if backoff else 0} attempts, the "
          f"tuple's LENGTH is the cap, so no second constant can disagree)")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-one-room-relaunch-ladder  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"watch={WATCH}", f"team_monitor={MONITOR}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body, encoding="utf-8")
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
