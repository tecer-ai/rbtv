#!/usr/bin/env python3
"""probe-goal-watcher-ghostrow-debounce.py — GHOSTROW needs TWO consecutive readings (map B9).

WHAT IT SCORES (task 7.663). A roster-ACTIVE row whose pane holds no harness process is, in ONE
reading, indistinguishable from a harness mid-restart and from a pane read inside a relaunch's
startup window. `watch.py` therefore required two consecutive passes — a debounce added
specifically after ONE reading flagged the owner's own `master` door on 2026-07-30 03:34. The
replacement job fired on a single snapshot row.

⚠ THE ONCE-PER-EPISODE `armed` DEDUP IS NOT A DEBOUNCE, and mistaking it for one is why the gap
was invisible: it suppresses REPEATS of a flag, never the FIRST one — and the first is precisely
the reading that fired on the door. R1 measures the first reading, which is the only reading the
dedup never touches.

RED-FIRST. Set `RBTV_PROBE_TREE` to an alternative rbtv repo root and every arm re-runs against
THAT tree's `goal-watcher-job.py`. Pointed at a pre-7.663 tree, R1, R2 and R4 go red (a single
reading fires a deliverable GHOSTROW, so nothing is held, reported, or cleared) while C0 and R3
stay green — DEAD fires on reading one under both trees, and reading two delivers under both.
(Measured 2026-08-10 against `git show HEAD:` pre-fix; an earlier draft of this line predicted
R1/R3 red, which the red capture contradicted.)

ARMS
  C0  THE FIXTURE IS REAL: after the debounce is satisfied the ghost row IS delivered
      (`nudge == "leader"`) — the debounce delays the flag, it does not delete it.
  R1  ONE reading emits NO deliverable GHOSTROW. It is REPORTED (a `none`-action row) rather than
      swallowed: a condition being debounced must not look like a condition gone quiet.
  R2  the count is CONSECUTIVE — a healthy reading between two ghost readings clears it, so the
      third reading is back at 1 and still refuses to fire.
  R3  SCOPED: DEAD (the pane is gone from the room) is NOT debounced and fires on reading one.
      Without this arm a debounce accidentally applied to every absent row would pass R1/R2.
  R4  NOT SILENT: the held-back reading appears in the decision set by its own class, carrying
      the reading count, so a leader reading the pass can see the condition is being held.

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP.

Run it through the suite — `node ignite/deploy/probe-suite.js --only goal-watcher-ghostrow-debounce`
— never by hand (`G-163`). Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import importlib.util
import os
import sys
import time
import types
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

# See probe-goal-watcher-door-exemption.py for why these are stubbed on a non-POSIX host: the
# predicates under test touch neither, and an OS-bound probe measures nothing off that OS.
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
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "ignite" / "jobs" / "goal-watcher-job.py"
OUT = HERE / "probe-goal-watcher-ghostrow-debounce.out"

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
    spec = importlib.util.spec_from_file_location("gwj_under_probe", TARGET)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gwj_under_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


def snap(now, ghost=True):
    """A snapshot whose one roster-absent row is a GHOST (pane there, no harness) or, when
    `ghost` is false, the HEALTHY reading — the row is simply not absent at all."""
    rows = [{"seat": "spectre", "pane": "%7", "liveness": "no-harness",
             "reason": "roster row active, pane present but no harness process"}] if ghost else []
    return {"captured_at": now, "captured_at_iso": "fixture",
            "headless": [], "headless_source": {"readable": True, "reason": ""},
            "roster_absent": rows, "seats": []}


def dead_snap(now):
    return {"captured_at": now, "captured_at_iso": "fixture",
            "headless": [], "headless_source": {"readable": True, "reason": ""},
            "roster_absent": [{"seat": "vanished", "pane": "%8", "liveness": "absent",
                               "reason": "roster row active, pane not in the room"}],
            "seats": []}


def delivered(decisions, cls, seat):
    return [d for d in decisions
            if d["class"] == cls and d["subject"] == seat and d["nudge"] == "leader"
            and not d["action"].startswith("none")]


def main():
    if not TARGET.exists():
        check("C0", False, f"{TARGET} does not exist — the debounce cannot hold in a file "
                           f"that is gone")
        return
    gwj = load_target()
    now = time.time()
    args = gwj._ns()

    # ---- R1: reading ONE.
    state = {}
    p1 = gwj.evaluate(snap(now), args, state, {}, now)[0]
    check("R1", not delivered(p1, "GHOSTROW", "spectre"),
          f"reading 1 delivers no GHOSTROW; classes about `spectre` = "
          f"{[d['class'] + '/' + d['action'][:22] for d in p1 if d['subject'] == 'spectre']}")

    # ---- R4: it is reported, not swallowed.
    held = [d for d in p1 if d["subject"] == "spectre" and d["nudge"] == ""]
    check("R4", any("1" in d["action"] and d["action"].startswith("none") for d in held),
          f"the held reading is REPORTED with its count: "
          f"{[d['class'] + ' -> ' + d['action'] for d in held]}")

    # ---- C0: reading TWO fires.
    p2 = gwj.evaluate(snap(now), args, state, {}, now)[0]
    check("C0", bool(delivered(p2, "GHOSTROW", "spectre")),
          f"reading 2 DOES deliver the ghost row — the debounce delays, it does not delete: "
          f"{[d['action'] for d in delivered(p2, 'GHOSTROW', 'spectre')]}")

    # ---- R2: consecutive, not cumulative.
    state2 = {}
    gwj.evaluate(snap(now), args, state2, {}, now)                    # ghost reading 1
    gwj.evaluate(snap(now, ghost=False), args, state2, {}, now)       # HEALTHY — clears the count
    p3 = gwj.evaluate(snap(now), args, state2, {}, now)[0]            # ghost reading 1 again
    check("R2", not delivered(p3, "GHOSTROW", "spectre"),
          "a healthy reading between two ghost readings CLEARS the count, so the next ghost "
          "reading is back at 1 and still refuses to fire")

    # ---- R3: the debounce is scoped to GHOSTROW; DEAD is a different condition.
    p4 = gwj.evaluate(dead_snap(now), args, {}, {}, now)[0]
    check("R3", bool(delivered(p4, "DEAD", "vanished")),
          "DEAD (pane gone from the room) is NOT debounced and fires on reading one — the "
          "debounce did not spread to every absent row")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-goal-watcher-ghostrow-debounce  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
