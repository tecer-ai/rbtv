#!/usr/bin/env python3
"""probe-sensor-cold-boot.py — 7.607 E4b: the sensor's launch-time restart is never sessionless.

WHAT THIS GUARDS. `coord.ensure_team_monitor` restarts the room's team-monitor at the end of every
`launch`. It hands over the room it MEASURED off the pane the launch used — and when tmux could not
be asked, it used to hand over NOTHING. A sessionless `team_monitor.py ensure` falls through to the
sensor's OWN roster resolution, which on a COLD roster (no seat has ever checked in) or a STALE one
(every pane cell names a dead pane) REFUSES — `SessionUnresolved`, exit 4 — or aims at a name that
was never alive, exit 5. Either way the sensor dies in under a second, `state.json` is never
written, and `launch`'s capacity term reads `CAP UNENFORCEABLE` and DEFERS every counted candidate.
The first seat of a goal is then gated on a census that cannot exist before a seat lives. Measured
in the E4 live acceptance: three consecutive deferred fires.

THE FIX, and why it is not `G-296`'s banned derivation: `#d-extinguishment-design-lock` item 2
(owner, 2026-08-09) DEFINES the room name as the goal name — one room per goal — and item 8 makes
the goal folder BE the package. So the goal name is the room's name BY CONSTRUCTION, and the CALLER
(which knows the goal) supplies it explicitly. `team_monitor.resolve_session`'s own no-derivation
ban is untouched: the sensor is never left to derive, it is TOLD. `G-296` outlawed guessing a name
at a time when nothing defined one; a defined name is not a guess.

⚠ THE CALLER'S STATUS IS NOT A RELIABLE WITNESS OF THE DEFECT — the child dies on its own
resolution refusal moments AFTER `ensure` returns, so the sessionless call reads `fail` or
`started` depending on a race with that death (`fail` in this fixture, measured at 02ad3d3). That
is why the arms below measure the SENSOR'S OWN OUTCOME (writer lock + a fresh `state.json`) and
the emitted argv, never the caller's verdict.

THE ARMS. The GREEN CONTROL RUNS FIRST, in the same layout, and is not optional: an arm that only
showed the sessionless start failing is satisfied by a fixture in which no sensor can start at all.

  S0  fixture integrity — the tmux server is really isolated, the room is really there, and the
      roster is really unresolvable. Vacuity guard: if S0 reds, S1-S5 mean nothing. The fixture is
      the real cold-boot shape: a seat DISPATCHED (a live `sessions.csv` row) but not yet CHECKED
      IN (no roster pane that resolves) — 7.552's own window.
  S1  GREEN CONTROL, FIRST: `ensure --session <goal>` in this exact layout STARTS the sensor and
      it writes `state.json`.
  S2  THE DEFECT'S MECHANISM, measured directly: the SAME `ensure` with no `--session` against the
      SAME package starts nothing and writes nothing. (Also the non-widening arm — the sensor's own
      resolution ban is preserved, not patched away.)
  S3  THE FIX AT THE REAL CALL SITE: `coord.ensure_team_monitor(args, session="")` — the sessionless
      caller — brings the sensor up and lands a fresh `state.json`. RED before the fix.
  S4  NO OVERRIDE: a MEASURED room still wins. The fallback may only fill an absence.
  S5  THE CONSUMER FLIPS: `budget.census` over the snapshot S3 produced reports `stale=False`, which
      is the exact reading whose absence made `launch` defer every counted candidate.

RED-FIRST PROOF: with `coord.py` reverted to `02ad3d3`, S3 and S5 go red and S0/S1/S2/S4 stay green.
Evidence: `1-projects/rbtv-sb-merge-refactor-core-build/build/subagent-closeout/evidence/w7607-e4b/`.

⚠ IT NEVER TOUCHES A REAL ROOM OR A REAL GOAL. Every tmux command runs against an ISOLATED server
(`TMUX_TMPDIR` redirected into this probe's own temp dir AND `mkdir`ed before the first tmux call —
tmux SILENTLY falls back to the default socket dir when `TMUX_TMPDIR` names a directory that does
not exist, and an "isolated" fixture then drives the box's live rooms; `TMUX`/`TMUX_PANE` unset in
the PROCESS environment, so children that call tmux themselves inherit the isolation). The server is
killed at teardown, sensors are stopped BEFORE it (a live sensor relaunches the room it watches).
The goal tree is a scratch tree under that temp dir. Nothing under `.rbtv/` is read or written.
A live owner acceptance run may be on this box.

Run it through the suite — `node ignite/deploy/probe-suite.js --only sensor-cold-boot` — never by
hand (`G-163`).
Exit 0 = every arm green · 1 = an arm failed · 2 = INOPERATIVE (the probe could not run at all).
"""

import os as _os, sys as _sys, pathlib as _pl  # task 7.630: solo-run tmux isolation, FIRST
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "team-kit" / "self_isolate.py").is_file()) / "team-kit"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

KIT = Path(__file__).resolve().parent.parent
MONITOR = KIT.parent.parent / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"
OUT = Path(__file__).resolve().parent / "probe-sensor-cold-boot.out"

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
    classic way this parse goes quietly wrong; a mis-parsed starttime would produce a seat the
    lease refuses, the sensor would take the crash/backoff branch, and S1 would red for a reason
    that has nothing to do with this row's subject.
    """
    raw = Path(f"/proc/{pid}/stat").read_text()
    return raw[raw.rindex(")") + 2:].split()[19]


def monitor(*args, timeout=30):
    return subprocess.run([sys.executable, str(MONITOR), *args],
                          capture_output=True, text=True, timeout=timeout)


def sensor_up(pkg):
    """(pid-or-None, state-dict-or-None) — the sensor's OWN two outcomes, read off disk.

    Both are read because either alone is satisfiable for the wrong reason: a lock with no snapshot
    is a sensor that came up and could not capture, a snapshot with no lock is a leftover from an
    earlier arm. The arms below assert on the pair.
    """
    import team_monitor                                                     # noqa: PLC0415
    pid = team_monitor.lock_holder(str(pkg))
    dest = Path(pkg) / "state.json"
    snap = None
    if dest.is_file():
        try:
            snap = json.loads(dest.read_text())
        except ValueError:
            snap = None
    return pid, snap


def settle(pkg, want, tries=40):
    """Wait up to ~4 s for the lock slot to reach `want` (True = held). Returns the final pid."""
    import team_monitor                                                     # noqa: PLC0415
    for _ in range(tries):
        pid = team_monitor.lock_holder(str(pkg))
        if bool(pid) is want:
            return pid
        time.sleep(0.1)
    return team_monitor.lock_holder(str(pkg))


def settle_snapshot(pkg, tries=100):
    """Wait up to ~10 s for the sensor's FIRST `state.json`. Absence after the wait is a real
    absence — the file is written at the end of the sensor's first pass, well inside this bound."""
    dest = Path(pkg) / "state.json"
    for _ in range(tries):
        if dest.is_file():
            return True
        time.sleep(0.1)
    return False


def main():
    if not MONITOR.is_file():
        stop("S0", f"{MONITOR} does not exist — an absent target IS the failure, not a skip")
        return
    if not (KIT / "coord.py").is_file():
        stop("S0", f"{KIT / 'coord.py'} does not exist — an absent target IS the failure")
        return
    sys.path.insert(0, str(KIT))
    sys.path.insert(0, str(MONITOR.parent))
    import coord                                                            # noqa: PLC0415
    import budget                                                           # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="probe-coldboot-") as td:
        td = Path(td)
        sock = td / "sock"
        sock.mkdir()                       # BEFORE the first tmux call — the fallback footgun
        os.environ["TMUX_TMPDIR"] = str(sock)
        # $TMUX overrides TMUX_TMPDIR: run from inside a pane, every tmux call here — including
        # the teardown's kill-server — would hit the DEFAULT server. Cleared so the redirect binds.
        os.environ.pop("TMUX", None)
        os.environ.pop("TMUX_PANE", None)
        goal = f"zzcold{os.getpid()}"
        pkg = td / "ws" / ".rbtv" / "goals" / goal
        (pkg / "coordination").mkdir(parents=True)
        args = type("A", (), {"package": str(pkg), "base": None, "workers_dir": None,
                              "run": None})()
        try:
            made = tmux("new-session", "-d", "-s", goal)
            sessions = tmux("list-sessions", "-F", "#{session_name}").stdout.split()
            check("S0a", made.returncode == 0 and sessions == [goal],
                  f"the isolated server carries EXACTLY the fixture room (rc={made.returncode}, "
                  f"sessions={sessions}) — a fixture reading the DEFAULT server would drive the "
                  f"box's live rooms and is the vacuity this arm exists to refuse")

            # THE STALE ROSTER: a checked-in row whose pane cell names a pane that does not exist.
            # This is the shape a package is left in after its room dies — 408 such rows on the
            # live run-3 package, 0 resolving (task 7.561's own measurement).
            (pkg / "coordination" / "workers.md").write_text(
                "| agent | pane | active | summary |\n"
                "|---|---|---|---|\n"
                "| alpha | %999 | yes | stale row from a dead room |\n", encoding="utf-8")
            # …and an OCCUPIED room, which is the OTHER half of the real cold-boot state and is
            # load-bearing here: a seat is DISPATCHED (its `sessions.csv` row is written at launch)
            # long before it CHECKS IN (its `workers.md` pane cell). So the lease verifies a seat
            # while the roster still resolves nothing — exactly 7.552's window. It also keeps the
            # sensor OFF the crash/relaunch branch, whose first backoff would delay the first
            # snapshot past any sane wait and red S1 for an unrelated reason.
            panes = tmux("list-panes", "-a", "-F", "#{session_name} #{pane_pid}").stdout.split()
            pane_pid = panes[1] if len(panes) >= 2 else ""
            (pkg / "sessions.csv").write_text(
                f"seat,pid,pid-starttime\nalpha,{pane_pid},{proc_starttime(pane_pid)}\n",
                encoding="utf-8")
            import team_monitor                                             # noqa: PLC0415
            try:
                resolved = team_monitor.resolve_session(str(pkg))
            except Exception as exc:                                        # noqa: BLE001
                resolved = f"REFUSED:{exc.__class__.__name__}"
            check("S0b", str(resolved).startswith("REFUSED:"),
                  f"the roster really is UNRESOLVABLE ({resolved}) — this is the whole premise of "
                  f"S2/S3: if the sensor could resolve the room on its own, a sessionless ensure "
                  f"would work and both arms would grade the wrong thing")

            # ── S1 GREEN CONTROL, FIRST, in the same layout ──────────────────────────────────
            r1 = monitor("ensure", "--package", str(pkg), "--session", goal)
            settle(pkg, True)
            settle_snapshot(pkg)
            pid1, snap1 = sensor_up(pkg)
            check("S1", bool(pid1) and snap1 is not None and snap1.get("session") == goal,
                  f"WITH the room named, the sensor STARTS and captures in this exact layout "
                  f"(rc={r1.returncode}, pid={pid1}, snapshot session={None if not snap1 else snap1.get('session')}) "
                  f"— the control that makes S2/S3's failures attributable to the missing name")
            monitor("stop", "--package", str(pkg))
            settle(pkg, False)
            (pkg / "state.json").unlink(missing_ok=True)

            # ── S2 THE DEFECT'S MECHANISM ────────────────────────────────────────────────────
            r2 = monitor("ensure", "--package", str(pkg))
            settle(pkg, True)
            settle_snapshot(pkg, tries=30)
            pid2, snap2 = sensor_up(pkg)
            check("S2", not pid2 and snap2 is None,
                  f"WITHOUT a room name the sensor starts NOTHING and captures NOTHING "
                  f"(rc={r2.returncode}, pid={pid2}, snapshot={'present' if snap2 else 'absent'}) "
                  f"— the exit-4/5 death behind `CAP UNENFORCEABLE`. Also the non-widening arm: "
                  f"team-monitor's own no-derivation ban is preserved by the fix, not patched away")
            monitor("stop", "--package", str(pkg))
            settle(pkg, False)
            (pkg / "state.json").unlink(missing_ok=True)

            # ── S3 THE FIX AT THE REAL CALL SITE ─────────────────────────────────────────────
            status3, _detail3 = coord.ensure_team_monitor(args, session="")
            settle(pkg, True)
            settle_snapshot(pkg)
            pid3, snap3 = sensor_up(pkg)
            check("S3", bool(pid3) and snap3 is not None and snap3.get("session") == goal,
                  f"the SESSIONLESS caller now brings the sensor up: ensure_team_monitor(session='') "
                  f"-> status={status3}, pid={pid3}, snapshot session="
                  f"{None if not snap3 else snap3.get('session')}. Pre-fix this arm is RED — the "
                  f"argv carried no --session and the child died on its own resolution refusal")

            # ── S5 THE CONSUMER FLIPS (read off S3's snapshot, before teardown) ──────────────
            c5 = budget.census({}, snap3 or {})
            check("S5", (snap3 is not None) and c5.get("stale") is False,
                  f"`budget.census` over the snapshot S3 produced reports stale={c5.get('stale')} "
                  f"(age {c5.get('snapshot_age_s')}s) — the exact reading whose ABSENCE made "
                  f"`launch` report CAP UNENFORCEABLE and defer every counted candidate. This is "
                  f"the consumer, not a restatement of S3")
            monitor("stop", "--package", str(pkg))
            settle(pkg, False)

            # ── S4 NO OVERRIDE: a MEASURED room still wins ───────────────────────────────────
            seen = []
            real_run, real_script = subprocess.run, coord.team_monitor_script
            try:
                coord.subprocess.run = lambda a, *x, **k: (
                    seen.append(list(a)) or subprocess.CompletedProcess(a, 0, "", ""))
                coord.team_monitor_script = lambda: MONITOR
                coord.ensure_team_monitor(args, session="measured-room")
            finally:
                coord.subprocess.run = real_run
                coord.team_monitor_script = real_script
            argv4 = seen[0] if seen else []
            check("S4", "--session" in argv4
                  and argv4[argv4.index("--session") + 1] == "measured-room",
                  f"a MEASURED room still wins — the fallback fills an ABSENCE and never overrides "
                  f"an answer the caller actually asked tmux for (argv tail: "
                  f"{argv4[-2:] if argv4 else 'no call captured'})")
        finally:
            # Sensors FIRST: a live one relaunches the room it watches (design-lock item 3), so
            # killing the server first would leave a process rebuilding rooms on a dead socket.
            try:
                monitor("stop", "--package", str(pkg), timeout=15)
            except Exception:                                               # noqa: BLE001
                pass
            tmux("kill-server")


try:
    main()
except Exception as exc:                                                    # noqa: BLE001
    stop("harness", f"{exc.__class__.__name__}: {exc}")

body = "\n".join(lines) + "\n"
OUT.write_text(body, encoding="utf-8")
print(body, end="")
if inoperative:
    print(f"probe-sensor-cold-boot: INOPERATIVE ({len(inoperative)} arm(s) could not run)")
    sys.exit(2)
if failures:
    print(f"probe-sensor-cold-boot: FAIL ({len(failures)}): {', '.join(failures)}")
    sys.exit(1)
print(f"probe-sensor-cold-boot: PASS ({len(lines)} arms)")
sys.exit(0)
