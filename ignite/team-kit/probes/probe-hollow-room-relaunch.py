#!/usr/bin/env python3
"""probe-hollow-room-relaunch.py — 7.607 E1b: the relaunch bound is spent by a HOLLOW room.

WHAT THIS GUARDS (F-1 of the stage-E1 §2 review; `decisions.md#d-extinguishment-design-lock`
item 3 — "relaunch the room, bounded, THEN ESCALATE LOUDLY on the bus").

⚠⚠ REPOINTED AT `team_monitor` BY TASK 7.35 PHASE A — the property MOVED, the probe did not
follow. This probe was written against `ignite/team-kit/watch.py`, whose bounded room-relaunch
ladder task 7.664 DELETED (commit `2d903ec`) as the duplicate of `team_monitor`'s. From that
commit until this repoint the probe read exit=2 INOPERATIVE on
`module 'watch' has no attribute 'RELAUNCH_EXHAUSTED_LINE'` — measuring NOTHING while the
property it guards went unguarded on the surviving ladder. Nothing it measures is weakened here:
the same six arms, the same red-first meaning, aimed at
`orchestration/cli/team-monitor/team_monitor.py` — the ONE ladder `probe-one-room-relaunch-ladder`
names as the survivor.

THE DEFECT IT CLOSES. `relaunch_room` restores the room with `tmux new-session -d`, which comes
back as an EMPTY SHELL. The lease correctly reports that shell as `live` (that is `lease.js`'s own
ruling — a room mid-relaunch between seat boots must not read as finished), and the sensor's
relaunch budget used to reset on `live` alone. So the bound reset on the very event it counts: the
ORDINARY crash walked 30 passes on ONE relaunch attempt, `RELAUNCH EXHAUSTED` was UNREACHABLE, and
the goal reported healthy forever while nothing executed it — the 7.608 deadlock's shape rebuilt
with tmux as the stale-status carrier. The fix resets the budget ONLY on an OCCUPIED room
(verified-seat count > 0).

⚠⚠ WHY THIS PROBE EXISTS AT ALL, given `team_monitor --selftest` already carries AST arms over
`cmd_run`'s reset and escalation branches: every one of those arms reads the SOURCE. An AST arm
cannot catch a `relaunch_room` that starts producing rooms the real `deriveLease` classifies
differently, because it never runs either. Here BOTH are real: a real `tmux new-session` on a real
isolated server, read back through `coord.derive_lease` -> `node server/lease/lease.js`. The only
injected seams are the pass work (`capture`/`write_snapshot` — not this row's subject) and the
sleep (which is also the MEASUREMENT: the grace window is read off the sleep arguments instead of
waiting 520 real seconds). `cmd_run` exposes no `do_pass`/`sleep_fn` parameters the way
`watch.watch_loop` did, so those two seams are bound on the MODULE for the duration of the drive
and restored after — a swap, never an edit.

THE ARMS. The GREEN CONTROL RUNS FIRST, in the same layout, and is not optional: an arm that only
showed the escalation firing is satisfied by a loop that escalates on everything.

  H0  fixture integrity — the isolated server is really isolated and the OCCUPIED room really
      verifies a seat through the real lease. Vacuity guard: if this reds, H1 means nothing.
  H1  GREEN CONTROL, FIRST: an OCCUPIED room (one ancestry-verified seat) spends NO relaunch
      attempt and raises NO escalation over the full bound's worth of passes.
  H2  THE MEASUREMENT: the ordinary crash — the room is KILLED, the REAL `relaunch_room` restores
      it as an empty shell, and the REAL lease reads that shell back. The loop must spend exactly
      `len(RELAUNCH_BACKOFF_S)` attempts and REACH the escalation.
  H3  the escalation LANDS ON THE BUS, not only on stderr — the sensor runs detached and nobody
      tails its stderr at 03:00. Read out of the appended `messages.md`.
  H4  THE LEASE IS UNCHANGED BY THE FIX: after the walk the hollow room still reads live with
      0 verified seats. The fix narrowed the SENSOR's reset, never the lease's posture; a lease
      that started calling a hollow room dead would break the mid-boot case `lease.js` protects.
  H5  the GRACE WINDOW measured off the real loop's sleep arguments: the full backoff, and NOT
      the cadence, so a lowered cadence cannot shrink the seconds a booting room is given.

RED-FIRST PROOF, at the repoint (2026-08-10, task 7.35 Phase A). Against `team_monitor.py` at
`0e2857dc` — the tree before this repoint's one-line companion change — H0/H1/H2/H4/H5 go green
and **H3 goes red**: `2d903ec` removed `watch.py`'s ladder and with it
`_escalate_relaunch_exhausted`, the ONLY bus delivery of this escalation, leaving the surviving
ladder's exhaustion reachable on stderr alone. That red is the regression this repoint SURFACED,
and it is closed in the same change by `team_monitor.escalate_relaunch_exhausted` — a port of the
deleted function, not a new design. The ORIGINAL red-first proof (against `f25f7df`'s `watch.py`,
H2/H3/H5 red) stands as this probe's provenance:
`1-projects/rbtv-sb-merge-refactor-core-build/build/subagent-closeout/evidence/w7607-e1b/`.

⚠ IT NEVER TOUCHES A REAL ROOM OR A REAL GOAL. Every tmux command runs against an ISOLATED server
(`TMUX_TMPDIR` redirected into this probe's own temp dir, `TMUX`/`TMUX_PANE` unset), killed at
teardown; the goal tree is a scratch tree under that temp dir. Nothing under `.rbtv/` is read or
written. A live owner acceptance run may be on this box.

⚠ POSIX-ONLY BY ITS SUBJECT, and that is disclosed rather than worked around: this arm set needs a
real tmux server and a real `/proc` to verify a seat, so it reports INOPERATIVE off POSIX instead
of pretending. Run decision D4 of `orch-0810-watchpy-split` asks for fixture-driven probes; this
one's fixture IS a live tmux server, which no stub can stand in for.

Run it through the suite — `node ignite/deploy/probe-suite.js --only hollow-room-relaunch` —
never by hand (`G-163`).
Exit 0 = every arm green · 1 = an arm failed · 2 = INOPERATIVE (the probe could not run at all).
"""

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
# HERE = <root>/ignite/team-kit/probes -> parents[2] is the rbtv repo root.
ROOT = HERE.parents[2]
MONITOR = ROOT / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"
OUT = HERE / "probe-hollow-room-relaunch.out"

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


def tmux(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def proc_starttime(pid):
    """/proc/<pid>/stat field 22, parsed from the LAST ')' — the same parse `lease.js` uses.

    The comm field is parenthesised and may itself contain spaces and parentheses, which is the
    classic way this parse goes quietly wrong; a mis-parsed starttime would silently produce a
    seat the lease refuses, and H1 would then be green for the wrong reason.
    """
    raw = Path(f"/proc/{pid}/stat").read_text()
    return raw[raw.rindex(")") + 2:].split()[19]


class Stop(BaseException):
    """⚠ BaseException, NOT Exception, and that is load-bearing: `cmd_run` wraps its snapshot
    write in `except Exception` so a bad pass never kills the sensor. A driver stop derived from
    `Exception` would be SWALLOWED there and the probe would hang for `max_passes` forever."""


def drive(tm, pkg, session, kill_room=None, max_passes=12):
    """Drive the REAL `cmd_run` — real `relaunch_room`, real lease, real escalation.

    Returns (printed, passes, backoff_sleeps). The pass work and the sleep are the ONLY seams:
    the pass work is not this row's subject, and the sleep is the measurement. The cadence is a
    SENTINEL (-1, provably not a backoff value — H5 asserts it) so a cadence sleep can never be
    miscounted as a backoff sleep.

    ⚠ `tm.time` is REBOUND to a shim rather than `time.sleep` being monkeypatched: patching the
    real module would slow every other consumer in this process and leak past the drive.
    """
    passes, slept = [], []

    def snapshot(_state, _pkg):
        passes.append(1)
        if kill_room and len(passes) == 1:
            tmux("kill-session", "-t", kill_room)
        if len(passes) >= max_passes:
            raise Stop()

    real_capture, real_snapshot, real_time = tm.capture, tm.write_snapshot, tm.time
    tm.capture = lambda *a, **k: {}
    tm.write_snapshot = snapshot
    tm.time = types.SimpleNamespace(sleep=slept.append, time=time.time,
                                    monotonic=time.monotonic, strftime=time.strftime)
    args = types.SimpleNamespace(package=str(pkg), session=session, interval=-1,
                                 sensor=None, heart_db=None)
    buf, ebuf = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(ebuf):
            tm.cmd_run(args)
    except Stop:
        pass
    finally:
        tm.capture, tm.write_snapshot, tm.time = real_capture, real_snapshot, real_time
    return buf.getvalue() + ebuf.getvalue(), len(passes), [s for s in slept if s != -1]


def main():
    if not MONITOR.is_file():
        check("H0", False, f"{MONITOR} does not exist — an absent target is the failure")
        return
    spec = importlib.util.spec_from_file_location("_probe_team_monitor", MONITOR)
    tm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tm)

    with tempfile.TemporaryDirectory(prefix="probe-hollow-") as td:
        td = Path(td)
        sock = td / "sock"
        sock.mkdir()
        os.environ["TMUX_TMPDIR"] = str(sock)
        # $TMUX overrides TMUX_TMPDIR: run from inside a pane, every tmux call here — including
        # the teardown's kill-server — would hit the DEFAULT server. Cleared so the redirect binds.
        os.environ.pop("TMUX", None)
        os.environ.pop("TMUX_PANE", None)
        try:
            goal = f"zzhollow{os.getpid()}"
            gdir = td / "ws" / ".rbtv" / "goals" / goal
            (gdir / "coordination").mkdir(parents=True)

            made = tmux("new-session", "-d", "-s", goal)
            sessions = tmux("list-sessions", "-F", "#{session_name}").stdout.split()
            check("H0a", made.returncode == 0 and sessions == [goal],
                  f"the isolated server carries EXACTLY the fixture room (rc={made.returncode}, "
                  f"sessions={sessions}) — a fixture reading the DEFAULT server would measure the "
                  f"box's live rooms and is the vacuity this arm exists to refuse")

            # An OCCUPIED room, built the way the real lease verifies one: a sessions.csv row
            # whose (pid, pid-starttime) is alive and whose ancestry reaches a pane of the room.
            # The pane pid is its OWN ancestor (ancestryPids starts at the pid), so the pane pid
            # IS the cheapest process that satisfies all three conjuncts — no agent is booted.
            panes = tmux("list-panes", "-a", "-F", "#{session_name} #{pane_pid}").stdout.split()
            pane_pid = panes[1] if len(panes) >= 2 else ""
            (gdir / "sessions.csv").write_text(
                f"seat,pid,pid-starttime\nalpha,{pane_pid},{proc_starttime(pane_pid)}\n",
                encoding="utf-8")
            t0 = time.perf_counter()
            alive, seats = tm.session_alive(goal), tm.verified_seat_count(gdir)
            lease_ms = (time.perf_counter() - t0) * 1000
            check("H0b", alive and seats == 1,
                  f"the REAL lease verifies the fixture seat: alive={alive} verified-seats="
                  f"{seats} in {lease_ms:.0f} ms. Vacuity guard for H1 — a control whose room was "
                  f"never OCCUPIED would take the crash path and pass H1 for the opposite reason")

            # ── H1 GREEN CONTROL, FIRST, in the same layout ──────────────────────────────────
            out1, n1, slept1 = drive(tm, gdir, goal, max_passes=12)
            esc1 = tm.RELAUNCH_EXHAUSTED_LINE in out1
            # `n1 == 12` is the SECOND vacuity guard and it is not decoration: `cmd_run` returns
            # BEFORE its first pass when the writer lock is held or the session will not resolve,
            # and every other conjunct here is trivially true of a loop that never ran.
            check("H1", n1 == 12 and not esc1 and out1.count("relaunch attempt") == 0
                  and slept1 == [],
                  f"OCCUPIED room over {n1} passes: escalated={esc1}, "
                  f"relaunch-attempts={out1.count('relaunch attempt')}, backoff-sleeps={slept1} — "
                  f"the fix cannot false-escalate on a healthy room")

            # ── H2 THE MEASUREMENT: the ordinary crash ───────────────────────────────────────
            out2, n2, slept2 = drive(tm, gdir, goal, kill_room=goal, max_passes=12)
            esc2 = tm.RELAUNCH_EXHAUSTED_LINE in out2
            attempts = out2.count("relaunch attempt")
            check("H2", esc2 and attempts == len(tm.RELAUNCH_BACKOFF_S),
                  f"room killed, REAL relaunch, REAL lease: {n2} passes, {attempts} attempts "
                  f"(bound {len(tm.RELAUNCH_BACKOFF_S)}), escalated={esc2}. Before the fix this "
                  f"measured 1 attempt and NO escalation over 30 passes")

            # ⚠ AN ABSENT BUS LOG IS THIS ARM'S FAILURE, NEVER AN EXCEPTION. When the escalation
            # does not fire, `append_message` is never called and the file does not exist — read
            # it unguarded and the probe crashes INOPERATIVE on the exact condition H3 exists to
            # detect, taking H4 and H5 down with it (observed against the M1 mutant).
            msgs = gdir / "coordination" / "messages.md"
            body = msgs.read_text(encoding="utf-8") if msgs.is_file() else ""
            check("H3", tm.RELAUNCH_EXHAUSTED_LINE.split(" — ")[0] in body
                  and "type: ask" in body,
                  f"the escalation LANDED ON THE BUS as an `ask` "
                  f"({len(body)} bytes in coordination/messages.md), not only on a stderr nobody "
                  f"tails — a stderr line alone is not an escalation")

            a_alive, a_seats = tm.session_alive(goal), tm.verified_seat_count(gdir)
            check("H4", a_alive and a_seats == 0,
                  f"the LEASE is untouched by the fix: the relaunched shell still reads "
                  f"alive={a_alive} verified-seats={a_seats} — live with zero seats, exactly as "
                  f"`lease.js` rules. The narrowing is the SENSOR's reset, never the lease's "
                  f"posture")

            check("H5", -1 not in tm.RELAUNCH_BACKOFF_S
                  and slept2 == list(tm.RELAUNCH_BACKOFF_S),
                  f"GRACE WINDOW measured off the real loop: backoff sleeps {slept2} = "
                  f"{sum(slept2)}s, cadence sleeps excluded by a sentinel. Cadence-independent — "
                  f"a cadence lowered to 5 s cannot shrink the seconds a booting room is given")
        finally:
            tmux("kill-server")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-hollow-room-relaunch  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
