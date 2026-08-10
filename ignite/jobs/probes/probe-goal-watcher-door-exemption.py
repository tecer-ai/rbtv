#!/usr/bin/env python3
"""probe-goal-watcher-door-exemption.py — a DOOR is never coached a close/reap/renew (G-176).

WHAT IT SCORES (task 7.663, kit behaviour map rows B9 + B13). A seat declaring `relays:` has a
pane that is a DOOR to a human role, and `r-owner-afk-liaison-parked` has that pane deliberately
OUTLIVE its session — so a parked door is byte-identical to a ghost row, and to a quiet seat,
under the only observations `goal-watcher-job` has. `watch.py` carried the exemption; the
replacement job did not, and its GHOSTROW remedy was unconditionally `close-seat <name> --renew`
while QUIET-ESCALATED's was `close <name> --renew` — the exact act that ruling forbids, coached
at the owner's own channel. It had already cost once, recorded as G-176.

⚠ THE FLAG IS NOT SUPPRESSED, AND R4 IS WHAT MAKES THAT CHECKABLE. A door in trouble and a door
waiting look identical from outside, so muting the row would make this fix its own next failure.
What changes is the REMEDY, and only for the door.

⚠ THE EXEMPTION IS DERIVED FROM THE DECLARATION, WHICH IS WHAT R3 MEASURES. The SAME fixture with
`relays:` removed must produce the UN-exempted remedy. Without that arm a hardcoded seat-name
rule, or a blanket removal of every close remedy, would pass every other arm here.

RED-FIRST. Set `RBTV_PROBE_TREE` to an alternative rbtv repo root and every arm re-runs against
THAT tree's `goal-watcher-job.py`. Pointed at a pre-7.663 tree, R1/R2/R4 go red and C0/R3 stay
green — which is what makes the green run a measurement rather than a restatement. The knob has
exactly one purpose and it is this one.

ARMS
  C0  THE FIXTURE IS REAL: a NON-door ghost still gets `close-seat <seat> --renew`, and a NON-door
      quiet seat still escalates to `close <seat> --renew`. Both rows are reached; the exemption
      below is scoped, not a blanket deletion.
  R1  the DOOR's GHOSTROW remedy carries NO close / reap / renew command at all.
  R2  the DOOR's QUIET remedy carries NO close / reap / renew command at all, at EVERY rung of the
      escalation ladder (driven `escalate_after` passes, so the escalated rung is reached).
  R3  DERIVED, NOT HARDCODED: the same two seats with no `relays:` declaration get the un-exempted
      remedies back.
  R4  NOT SUPPRESSED: the door still produces a DELIVERED decision for both conditions
      (`nudge == "leader"`), and its remedy names the door and says do not close it.

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP. If `goal-watcher-job.py` is missing or will not
import, this probe FAILS. INOPERATIVE (exit 2) is for the probe itself being unable to run.

Run it through the suite — `node ignite/deploy/probe-suite.js --only goal-watcher-door-exemption`
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
OUT = HERE / "probe-goal-watcher-door-exemption.out"

# Any of these appearing in a DOOR's remedy is the defect. ⚠ THEY ARE COMMAND FORMS, NOT THE VERBS
# THEMSELVES, and that distinction is load-bearing: the door remedy has to NAME the acts it
# forbids ("do NOT close, reap or renew this row"), so a bare-verb scan would fire on the fix's own
# prohibition. What must not appear is something a leader — or an agent acting on a
# leader-addressed flag — can PASTE.
FORBIDDEN_AT_A_DOOR = ("close-seat", "--renew", "python3", "reap --go")

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


def fixture(now):
    """One snapshot carrying four seats: a door and a worker in each of the two conditions.

    The two ghost rows are `liveness: no-harness` — pane present, no harness process — which is
    the GHOSTROW condition. `liveness: absent` would be DEAD, a different row."""
    return {
        "captured_at": now, "captured_at_iso": "fixture",
        "headless": [], "headless_source": {"readable": True, "reason": ""},
        "roster_absent": [
            {"seat": "owner-door", "pane": "%1", "liveness": "no-harness",
             "reason": "roster row active, pane present but no harness process"},
            {"seat": "worker-ghost", "pane": "%2", "liveness": "no-harness",
             "reason": "roster row active, pane present but no harness process"},
        ],
        "seats": [
            {"seat": "quiet-door", "pane": "%3", "roster_active": True, "liveness": "live",
             "last_activity_age_s": 99999, "ctx_pct": None},
            {"seat": "quiet-worker", "pane": "%4", "roster_active": True, "liveness": "live",
             "last_activity_age_s": 99999, "ctx_pct": None},
        ],
    }


def drive(gwj, doors, now, passes):
    """Run `passes` consecutive evaluations over ONE state, returning the LAST decision set.

    Consecutive passes are required by construction: GHOSTROW is debounced and QUIET escalates,
    so a single pass reaches neither the fired ghost row nor the escalated quiet rung."""
    args = gwj._ns(door_seats=set(doors))
    state, decisions = {}, []
    for _ in range(passes):
        decisions = gwj.evaluate(fixture(now), args, state, {}, now)[0]
    return decisions


def rows_for(decisions, seat):
    return [d for d in decisions if d["subject"] == seat]


def remedies(decisions, seat):
    return " || ".join(d.get("remedy") or "" for d in rows_for(decisions, seat))


def main():
    if not TARGET.exists():
        # ⚠ NOT a skip: the target's absence IS a failure of the property under test.
        check("C0", False, f"{TARGET} does not exist — the exemption cannot hold in a file "
                           f"that is gone")
        return
    gwj = load_target()
    now = time.time()
    # `escalate_after` passes, so the QUIET ladder reaches its escalated rung — the rung whose
    # remedy is the forbidden `close <seat> --renew`.
    passes = max(gwj._ns().escalate_after, gwj.GHOSTROW_DEBOUNCE_PASSES) \
        if hasattr(gwj, "GHOSTROW_DEBOUNCE_PASSES") else gwj._ns().escalate_after
    exempt = drive(gwj, {"owner-door", "quiet-door"}, now, passes)
    plain = drive(gwj, set(), now, passes)

    # ---- C0: the fixture actually reaches both rows, un-exempted.
    ghost_w = remedies(exempt, "worker-ghost")
    quiet_w = remedies(exempt, "quiet-worker")
    check("C0", "close-seat" in ghost_w and "--renew" in ghost_w and "--renew" in quiet_w,
          f"non-door ghost remedy={ghost_w[-70:]!r}; non-door quiet remedy={quiet_w[-70:]!r}")

    # ---- R1 / R2: nothing at a door coaches a lifecycle act on the door's pane.
    for tag, seat in (("R1", "owner-door"), ("R2", "quiet-door")):
        rem = remedies(exempt, seat)
        hits = [t for t in FORBIDDEN_AT_A_DOOR if t in rem]
        check(tag, not hits,
              f"{seat}: {len(rows_for(exempt, seat))} row(s); forbidden token(s)={hits}; "
              f"remedy={rem[:90]!r}")

    # ---- R3: the exemption is DERIVED from `relays:` and from nothing else.
    g3 = remedies(plain, "owner-door")
    q3 = remedies(plain, "quiet-door")
    check("R3", "close-seat" in g3 and "--renew" in g3 and "--renew" in q3,
          f"with NO door declaration the SAME two seats get the un-exempted remedies back "
          f"(ghost={g3[-60:]!r}, quiet={q3[-60:]!r}) — so the exemption keys on the declaration, "
          f"not on a name and not on a blanket removal")

    # ---- R4: reported to a live recipient, and it says what must not be done.
    # ⚠ BOTH HALVES OF "delivered": a `none`-action row is REPORTED and never sent, and
    # SHADOW-BACKSTOP is exactly such a row on every absent seat — counting it would put an
    # empty remedy into the set below and red the arm for the wrong reason.
    delivered = {s: [d for d in rows_for(exempt, s)
                     if d["nudge"] == "leader" and not d["action"].startswith("none")]
                 for s in ("owner-door", "quiet-door")}
    said = all("do NOT close" in (d.get("remedy") or "")
               for rows in delivered.values() for d in rows)
    check("R4", all(delivered.values()) and said,
          f"the door is still FLAGGED, not muted — leader-addressed rows: "
          f"{ {s: [d['class'] for d in r] for s, r in delivered.items()} }; "
          f"every one states the prohibition: {said}")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-goal-watcher-door-exemption  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
