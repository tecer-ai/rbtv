#!/usr/bin/env python3
"""probe-team-monitor-activity-fallback.py — a seat with NO transcript still has activity (B13).

WHAT IT SCORES (task 7.663). `team_monitor.capture()` set `last_activity` straight from the
ctx-monitor engine's `as_of`, and that value is a HARNESS TRANSCRIPT FILE'S MTIME
(`ctx_monitor.py`, `f.stat().st_mtime`). A harness that publishes no readable transcript —
**codex and opencode**, named as such in `watch.py`'s own docstring — therefore produced
`as_of: None`, so `last_activity` AND `last_activity_age_s` were both None and every inactivity
threshold downstream (`goal-watcher-job`'s QUIET row reads `last_activity_age_s`) produced
NOTHING for those seats.

⚠ THAT IS A SILENT NO-SIGNAL, NOT A WRONG ONE, WHICH IS WHY IT NEEDED ITS OWN PROBE: a codex seat
that died quietly was INVISIBLE rather than mis-reported, and nothing in the run could tell that
state apart from a healthy one. `watch.py` never had the hole because it hashed the pane's
visible content, which works for any pane regardless of harness.

⚠ EVERY ARM DRIVES `capture()` END TO END WITH A SIMULATED CODEX SEAT, never the helper alone. A
fallback that computed correctly and was never called by the seat-row builder would pass a
helper-level probe and leave the hole exactly where it was.

⚠ PLACEMENT: see probe-team-monitor-approval-title.py — the runner's discovery root is `ignite/`,
so a probe beside `team_monitor.py` would be outside the ONE denominator (G-141).

RED-FIRST. Set `RBTV_PROBE_TREE` to an alternative rbtv repo root and every arm re-runs against
THAT tree's `team_monitor.py`. Pointed at a pre-7.663 tree, R1/R2/R3 go red (the codex seat's
`last_activity` is None on every pass) and C0/R4 stay green.

ARMS
  C0  THE FIXTURE IS REAL: the claude seat, which HAS a transcript, reports that transcript's
      mtime as its `last_activity`. `capture()` is producing rows and the engine is being read.
  R1  the CODEX seat — same room, same pass, no transcript — reports a NON-None `last_activity`
      and a non-None `last_activity_age_s`.
  R2  UNCHANGED pane content across two passes carries the stamp forward, so the seat visibly
      AGES. An implementation that restamped every pass would report a permanently-fresh seat,
      which is the same blindness wearing a number.
  R3  CHANGED pane content RE-ARMS the stamp — the age drops back to zero.
  R4  SCOPED: the claude seat is untouched by the fallback across all three passes — its
      `last_activity` stays its transcript mtime and it carries no content digest.

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP.

Run it through the suite —
`node ignite/deploy/probe-suite.js --only team-monitor-activity-fallback` — never by hand
(`G-163`). Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import importlib.util
import os
import sys
import tempfile
import time as _realtime
import types
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

try:
    import fcntl  # noqa: F401
except ImportError:                      # non-POSIX host; the writer lock is not under test.
    _m = types.ModuleType("fcntl")
    _m.__dict__.update({"LOCK_EX": 2, "LOCK_NB": 4, "flock": lambda *a: None})
    sys.modules["fcntl"] = _m

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"
OUT = HERE / "probe-team-monitor-activity-fallback.out"

T0 = 1_700_000_000.0            # a fixed wall clock, so an age is a measurement and not a race
TRANSCRIPT_AS_OF = T0 - 42.0

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


class Clock:
    """`time` with a settable `time()`. Everything else delegates to the real module — only the
    wall clock is controlled, so an age below is a difference between two chosen instants rather
    than whatever the two capture calls happened to cost."""

    def __init__(self, now):
        self.now = now

    def time(self):
        return self.now

    def __getattr__(self, name):
        return getattr(_realtime, name)


class FakeEngine:
    """The ctx-monitor engine, simulated. TWO seats and the difference between them is the whole
    fixture: `claude-seat` publishes a transcript mtime (`as_of`), `codex-seat` publishes NONE —
    which is what a harness with no readable transcript actually reports."""

    HARNESSES = ("claude", "codex")

    def __init__(self):
        self.tails = {"%1": "claude working\n", "%2": "codex turn 1\n"}

    def list_panes(self, session):
        return [{"pane_id": "%1", "pid": 101, "cwd": "/w"},
                {"pane_id": "%2", "pid": 102, "cwd": "/w"}]

    def pane_records(self, session):
        return [
            {"pane_id": "%1", "harness": "claude", "title": "claude — bash", "window": "0",
             "window_name": "w", "as_of": TRANSCRIPT_AS_OF, "ctx_pct": 10, "source": "transcript"},
            # ⚠ THE SIMULATED CODEX SEAT. `as_of: None` is not an invented value — it is what the
            # engine returns for a harness whose transcript it cannot read.
            {"pane_id": "%2", "harness": "codex", "title": "codex — bash", "window": "0",
             "window_name": "w", "as_of": None, "ctx_pct": None, "source": ""},
        ]

    def capture_pane(self, pane_id):
        return self.tails[pane_id]


def install(tm, engine, clock):
    """Bind the sensor to the fixture: the engine, the clock, and the handful of collaborators
    that would otherwise read the real box. NOTHING that computes activity is replaced."""
    tm._SENSOR = engine
    tm.time = clock
    tm.ps_table = lambda: {101: {"ppid": 1, "rss_kb": 1000, "comm": "claude"},
                           102: {"ppid": 1, "rss_kb": 1000, "comm": "codex"}}
    tm.roster = lambda package: {"claude-seat": {"pane": "%1", "active": True, "checked_in": "",
                                                 "ctx_refresh": None},
                                 "codex-seat": {"pane": "%2", "active": True, "checked_in": "",
                                                "ctx_refresh": None}}
    tm.declared_agent_types = lambda package: {}
    tm.session_alive = lambda session: True
    tm.messages_tail = lambda package: None
    tm.dispatch_tokens = lambda package, seats: {}
    tm.headless = lambda package, at, db=None: ([], None,
                                                {"readable": False, "reason": "probe fixture"})
    tm.ready_row_count = lambda package: (None, "probe fixture")
    tm.queued_count = lambda package, db=None: (None, {"reason": "probe fixture"})


def row(snap, seat):
    return next((s for s in snap["seats"] if s.get("seat") == seat), {})


def main():
    if not TARGET.exists():
        check("C0", False, f"{TARGET} does not exist — a sensor that is gone reports no activity")
        return
    spec = importlib.util.spec_from_file_location("tm_under_probe", TARGET)
    tm = importlib.util.module_from_spec(spec)
    sys.modules["tm_under_probe"] = tm
    spec.loader.exec_module(tm)

    engine = FakeEngine()
    clock = Clock(T0)
    install(tm, engine, clock)

    with tempfile.TemporaryDirectory() as td:
        pkg = Path(td)
        (pkg / "coordination").mkdir()

        def a_pass():
            """One full sensor pass: capture, then WRITE — because the snapshot is where the
            fallback's one carried fact lives, a pass that never wrote would test nothing."""
            snap = tm.capture(str(pkg), session="probe-room")
            tm.write_snapshot(snap, str(pkg))
            return snap

        p1 = a_pass()
        claude1, codex1 = row(p1, "claude-seat"), row(p1, "codex-seat")

        check("C0", claude1.get("last_activity") == TRANSCRIPT_AS_OF
              and claude1.get("last_activity_age_s") == 42.0,
              f"the transcript-publishing seat reports its mtime: "
              f"last_activity={claude1.get('last_activity')}, "
              f"age={claude1.get('last_activity_age_s')} — capture() is producing real rows")

        check("R1", codex1.get("last_activity") is not None
              and codex1.get("last_activity_age_s") is not None,
              f"the SIMULATED CODEX seat (as_of=None) reports "
              f"last_activity={codex1.get('last_activity')}, "
              f"age={codex1.get('last_activity_age_s')} — a None here is the silent no-signal "
              f"this probe exists for")

        # ---- pass 2: SAME content, 60s later.
        clock.now = T0 + 60
        p2 = a_pass()
        codex2 = row(p2, "codex-seat")
        check("R2", codex2.get("last_activity") == codex1.get("last_activity")
              and codex2.get("last_activity_age_s") == 60.0,
              f"unchanged pane content 60s on: last_activity carried forward "
              f"({codex2.get('last_activity')}), age={codex2.get('last_activity_age_s')} — the "
              f"seat AGES rather than reading permanently fresh")

        # ---- pass 3: the pane PRINTS something, 90s in.
        engine.tails["%2"] = "codex turn 1\ncodex turn 2\n"
        clock.now = T0 + 90
        p3 = a_pass()
        codex3 = row(p3, "codex-seat")
        check("R3", codex3.get("last_activity_age_s") == 0.0
              and codex3.get("last_activity") != codex1.get("last_activity"),
              f"changed pane content re-arms the stamp: age={codex3.get('last_activity_age_s')}, "
              f"last_activity={codex3.get('last_activity')}")

        untouched = [row(p, "claude-seat").get("last_activity") for p in (p1, p2, p3)]
        digests = [row(p, "claude-seat").get("activity_digest") for p in (p1, p2, p3)]
        check("R4", untouched == [TRANSCRIPT_AS_OF] * 3 and not any(digests),
              f"the transcript-publishing seat is untouched across all three passes "
              f"(last_activity={untouched}, digests={digests}) — the fallback is scoped to the "
              f"seats that have no transcript")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-team-monitor-activity-fallback  "
                  f"({_realtime.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
