#!/usr/bin/env python3
"""probe-sensor-start.py — the census SENSOR starts on a fresh package, so the SECOND fire admits.

WHAT THIS GUARDS THAT NOTHING ELSE DOES (task 7.552). `probe-planning-entry.py` P5 proves the FIRST
fire on a virgin package opens the entry seat, on the cold-start admission (team-kit 7.406). The
cold-start bound is spent ONCE — it fires only while the package carries none of its four virginity
markers — so everything after the first fire depends on a real census existing, which depends on the
team-monitor sensor RUNNING. It never started: `coordinate launch` calls `ensure_team_monitor` after
its seat loop, but passed no `--session`, and `team_monitor.py` resolves the room from the ROSTER,
which is written at seat CHECK-IN and is therefore still empty at that instant. So every subsequent
launch read `CAP UNENFORCEABLE` and deferred every counted candidate. Wave D's advancement IS the
second fire, so the run's first fire worked and the run then stalled.

The fix passes the room's session — the one `cmd_launch` already resolved and launched into — to
`team_monitor.py ensure`. This probe is the end-to-end proof of the consequence: sensor up, second
fire ADMITS, and the honesty semantics of `73823ab` unchanged when the census is genuinely gone.

⚠ NOTHING HERE TOUCHES A LIVE ROOM, THE LIVE DAEMON OR THE LIVE STORE. The goals root is a tempdir,
`ignite` is stubbed, and every tmux act goes through a PATH shim pinned to a PRIVATE `-L` socket —
including the ones `coord.py` and `team_monitor.py` make, which call bare `tmux` and therefore
inherit this process's PATH.

⚠⚠ AND IT BOOTS NO REAL AGENT, WHICH IS ASSERTED RATHER THAN CLAIMED (arm S0). A `claude` PATH shim
alone does NOT bind: tmux starts a pane's shell as a LOGIN shell, whose profile PREPENDS the real
`~/.local/bin` and wins (finding F1 of the `73823ab` review — `probe-planning-entry.py` boots a real
`claude --effort max` per run because of it). This fixture defeats that LOCALLY, without touching
that probe's design: it pre-creates the room on its own private socket, sets
`default-command 'bash --noprofile --norc'` on THAT SERVER ONLY, and then asserts the stub actually
executed by reading a marker file the stub itself writes (arm S0 goes RED on an empty marker) — so
this probe can never silently pay for a real agent the way its sibling does.

Exit 0 GREEN · 1 RED · 2 INOPERATIVE.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAP = HERE.parent
IGNITE = CAP.parents[1]
LAUNCHER = CAP / "tool" / "workflow_launcher.py"
COORD = IGNITE / "team-kit" / "coord.py"
TEAM_MONITOR = IGNITE.parent / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"
ENTRY_PROBE = HERE / "probe-planning-entry.py"

SOCKET = "probe-sensor-start"          # PRIVATE; never the socket live rooms are on
GOAL = "probe-sensor-start-goal"
ROOM = GOAL   # 7.607 E2b, design-lock item 2: the room name IS the goal name

FAILED = []
INOPERATIVE = []
CHECKS = []


def report(check, ok, expected=True, detail=""):
    CHECKS.append(check)
    good = (bool(ok) == expected)
    print(f"  [{'ok ' if good else 'BAD'}] {check} -> {'GREEN' if ok else 'RED'} "
          f"(expected {'GREEN' if expected else 'RED'})" + (f" — {detail}" if detail else ""))
    if not good:
        (FAILED if expected else INOPERATIVE).append(check)
    return good


def load_entry_probe():
    """`probe-planning-entry.py` as a module — for `shipped()` and `drain()`.

    IMPORTED, NEVER RE-IMPLEMENTED. `drain()` runs the real `scaffold-and-queue` with the SHIPPED
    flags parsed out of `spawn-profiles.yaml`; a second copy here would agree with it only until one
    of them changed, and the fixture's whole value is that the package is built by the shipped create
    path. Its module body only binds constants and defines functions — `main()` runs under
    `__main__` alone — so importing it executes nothing.
    """
    spec = importlib.util.spec_from_file_location("probe_planning_entry", str(ENTRY_PROBE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tmux(*a):
    exe = shutil.which("tmux")
    return subprocess.run([exe, "-L", SOCKET, *a], capture_output=True, text=True) if exe else None


def make_shims(d, marker):
    """The PATH seam: every `tmux` in the whole composed act lands on THIS socket, and `claude` is a
    stub harness that RECORDS that it ran.

    ⚠ THE STUB'S SHAPE IS `acceptance-room.py`'s `STUB_BODY`, NOT AN INVENTION — a bash COPY at
    `.hb/claude` used as the SHEBANG INTERPRETER of the script `claude`. Every clause there is a
    measurement, and the one that bites here is `coord.py`'s: `wait_harness_up` polls
    `pane_harness_pids`, which matches a HARNESS process under the pane. A stub that `exec sleep`s
    is a pane whose process is `sleep`, so coord reports POSITIVE ABSENCE — "only its shell is
    there (G-11)" — refuses the seat and the launch exits 1. Measured on this fixture's first run.
    `printf` and `read` are builtins, so the stub itself stays the pane's foreground process.

    The marker is the second half. F1 was invisible for exactly one reason — nothing checked
    whether the stub executed — so the stub writes its argv and S0 reads it back."""
    d.mkdir(parents=True, exist_ok=True)
    real = shutil.which("tmux")
    (d / "tmux").write_text(f'#!/bin/sh\nexec {real} -L {SOCKET} "$@"\n', encoding="utf-8")
    hb = d / ".hb"
    hb.mkdir(exist_ok=True)
    shutil.copy2("/bin/bash", hb / "claude")
    (d / "claude").write_text(
        f"#!{hb / 'claude'}\n"
        "# stub harness — no model, no network, no cost. Flags are deliberately ignored.\n"
        f'printf "%s\\n" "$*" >> {marker}\n'
        "while :; do read -rt 3600 _ || true; done\n", encoding="utf-8")
    for f in ("tmux", "claude"):
        (d / f).chmod(0o755)
    return d


def room_panes():
    r = tmux("list-panes", "-s", "-t", f"={ROOM}", "-F", "#{pane_id}\t#{pane_current_command}")
    return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r and r.returncode == 0 else []


def monitor_pid(pkg):
    """The pid holding the sensor's writer lock, or None — asked the way `coord.team_monitor_holder`
    asks it (pid file + /proc), never parsed out of anyone's wording."""
    try:
        pid = int((pkg / "coordination" / "team-monitor.lock").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return pid if pid and Path(f"/proc/{pid}").exists() else None


def state_json(pkg):
    try:
        return json.loads((pkg / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def wait_for(fn, timeout=15.0, step=0.25):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return fn()


def main():
    if shutil.which("tmux") is None:
        print("VERDICT: INOPERATIVE — tmux is absent, so the room arms cannot run")
        return 2
    ep = load_entry_probe()
    flags, _wf_argv = ep.shipped()
    entry_seat = flags["--entry-seat"]

    tmpdir = Path(tempfile.mkdtemp(prefix="probe-sensor-start-"))
    try:
        marker = tmpdir / "claude-stub-ran.txt"
        shims = make_shims(tmpdir / "shims", marker)
        env = dict(os.environ)
        env["PATH"] = f"{shims}{os.pathsep}{os.environ.get('PATH', '')}"
        for v in ("TMUX", "TMUX_PANE", "COORD_LAUNCH_TARGET"):
            env.pop(v, None)
        os.environ["PATH"] = env["PATH"]          # so this probe's own `tmux()` hits the shim too

        _out, _calls, root = ep.drain(tmpdir / "a", flags, goal=GOAL)
        pkg = root / GOAL   # 7.607 E2b item 8: the package IS the goal folder
        report("S1 the scaffolded package exists", pkg.is_dir(), True, str(pkg))
        virgin = not any((pkg / m).exists() for m in
                         ("state.json", "sessions.csv", "coordination/team-monitor.log",
                          "coordination/team-monitor.lock"))
        report("S1 it is VIRGIN — no marker of a sensor or a launch", virgin, True,
               "state.json / sessions.csv / team-monitor.log / team-monitor.lock all absent")

        # The room is pre-created HERE, not by the launcher, for ONE reason: `default-command` is a
        # server option and the seat's pane must be opened AFTER it is set. `ensure_session` is
        # idempotent by design, so the launcher joins this room ("existing session") — the session
        # CREATION path is `probe-planning-entry.py` P4's claim, not this probe's.
        tmux("new-session", "-d", "-s", ROOM, "-c", str(pkg))
        tmux("set-option", "-g", "default-command", "bash --noprofile --norc")

        fire = [sys.executable, str(LAUNCHER), "--package", str(pkg), "--goal", GOAL,
                "--entry-seat", entry_seat, "--coord", str(COORD)]

        # ---- S2 · the FIRST fire opens the entry seat on the cold-start bound ------------------
        r2 = subprocess.run(fire, capture_output=True, text=True, env=env, timeout=600)
        o2, panes2 = r2.stdout + r2.stderr, room_panes()
        report("S2 first fire on a virgin package EXITS 0", r2.returncode == 0, True,
               f"exit={r2.returncode} :: " + (o2.strip().splitlines() or [""])[-1][:180])
        report("S2 cold-start admission is what admitted it", "COLD-START" in o2, True,
               next((l for l in o2.splitlines() if "COLD-START" in l), "")[:170])
        report("S2 a seat pane opened", len(panes2) >= 2, True, f"{len(panes2)} pane(s): {panes2}")

        # ---- S0 · the stub BOUND, so nothing here booted a paid agent -------------------------
        ran = marker.read_text(encoding="utf-8").strip() if marker.exists() else ""
        report("S0 the `claude` stub ACTUALLY EXECUTED (no real agent booted)", bool(ran), True,
               (ran.splitlines() or [""])[0][:150] or "MARKER EMPTY — a real agent booted instead")

        # ---- S3 · THE FIX · the sensor is RUNNING after the first launch ----------------------
        pid = wait_for(lambda: monitor_pid(pkg))
        snap = wait_for(lambda: state_json(pkg))
        report("S3 the census sensor is RUNNING (a live pid holds the writer lock)", bool(pid), True,
               f"lock pid={pid}")
        report("S3 it wrote a state.json naming THIS ROOM", bool(snap) and snap.get("session") == ROOM,
               True, f"session={None if not snap else snap.get('session')} "
                     f"writer_pid={None if not snap else snap.get('writer_pid')}")
        report("S3 the launch REPORTED the start rather than warning it failed",
               "team-monitor start FAILED" not in o2, True,
               next((l for l in o2.splitlines() if "team-monitor" in l), "")[:170])

        # ---- S4 · THE CONSEQUENCE · the SECOND fire ADMITS ------------------------------------
        # This is the arm the row exists for. Pre-fix it exits 3 with `CAP UNENFORCEABLE`, because
        # the package is no longer virgin (the first fire left sessions.csv behind) and no census
        # was ever produced. Wave D's advancement is exactly this fire.
        r4 = subprocess.run(fire, capture_output=True, text=True, env=env, timeout=600)
        o4, panes4 = r4.stdout + r4.stderr, room_panes()
        report("S4 the second fire ADMITS and EXITS 0", r4.returncode == 0, True,
               f"exit={r4.returncode} :: " + (o4.strip().splitlines() or [""])[-1][:180])
        report("S4 the census was ENFORCEABLE — no blind-defer line",
               "CAP UNENFORCEABLE" not in o4, True,
               next((l for l in o4.splitlines() if "capacity:" in l), "")[:170])
        report("S4 it opened ANOTHER seat pane (the room grew)", len(panes4) > len(panes2), True,
               f"{len(panes2)} -> {len(panes4)} pane(s)")

        # ---- S5 · CONTROL ARM · the 73823ab honesty semantics are UNCHANGED -------------------
        # A fire that opens ZERO seats must still exit 3 and still record `failed`. Reached the way
        # the launcher's own WAIT text describes it: the sensor DIED and its census is gone. If this
        # arm ever goes green, the happy path was bought by making the zero-seat path look
        # successful — the exact defect 7.548 fixed.
        subprocess.run([sys.executable, str(TEAM_MONITOR), "stop", "--package", str(pkg)],
                       capture_output=True, text=True, env=env, timeout=60)
        (pkg / "state.json").unlink(missing_ok=True)
        report("S5 the sensor is DOWN and its census is gone (the fixture's premise)",
               monitor_pid(pkg) is None and not (pkg / "state.json").exists(), True,
               "no lock holder, no state.json")
        r5 = subprocess.run(fire, capture_output=True, text=True, env=env, timeout=600)
        o5, panes5 = r5.stdout + r5.stderr, room_panes()
        report("S5 a fire with no census EXITS 0 (it must not)", r5.returncode == 0, False,
               f"exit={r5.returncode} (EXIT_NO_SEAT=3)")
        report("S5 the blind defer is named LOUDLY and typed",
               "CAP UNENFORCEABLE" in o5 and "WAIT" in o5, True,
               next((l for l in o5.splitlines() if "WAIT" in l), "")[:170])
        report("S5 no pane opened while the room still holds several",
               len(panes5) == len(panes4) and len(panes5) > 1, True,
               f"{len(panes5)} pane(s), unchanged — an absolute count would have said LAUNCHED")
        # …and the pickup lane the WAIT names now actually works: the SAME launch restarted the
        # sensor (after the capacity decision, which is why this fire still deferred), so the next
        # fire has a census again. Before the fix nothing could restart it — the roster is still
        # empty, so `team_monitor.py` refused every time.
        report("S5 that same launch RESTARTED the sensor (the pickup lane closes on its own)",
               bool(wait_for(lambda: monitor_pid(pkg))), True, f"lock pid={monitor_pid(pkg)}")
    finally:
        subprocess.run([sys.executable, str(TEAM_MONITOR), "stop",
                        "--package", str(tmpdir / "a" / ".rbtv" / "goals" / GOAL)],
                       capture_output=True, text=True)
        tmux("kill-server")
        shutil.rmtree(tmpdir, ignore_errors=True)

    print()
    if INOPERATIVE:
        print(f"VERDICT: INOPERATIVE — {len(INOPERATIVE)} arm(s) did not land on their expected "
              f"polarity, so every green above is vacuous: {INOPERATIVE}")
        return 2
    if FAILED:
        print(f"VERDICT: RED — {len(FAILED)} check(s) failed: {FAILED}")
        return 1
    print(f"VERDICT: GREEN — {len(CHECKS)} checks. The sensor starts with the room's first seat, the "
          f"second fire admits on a real census, and a fire with NO census still exits 3. Boundary: "
          f"the room is pre-created by the fixture so the non-login `default-command` is in place "
          f"before the seat's pane opens — session CREATION is probe-planning-entry.py P4's claim, "
          f"not this probe's; and the seat's PANE is asserted, never an agent (S0 proves the stub "
          f"ran, so no paid harness boots here).")
    return 0


class _Tee:
    def __init__(self, real):
        self.real, self.buf = real, []

    def write(self, s):
        self.real.write(s)
        self.buf.append(s)
        return len(s)

    def flush(self):
        self.real.flush()


if __name__ == "__main__":
    tee = _Tee(sys.stdout)
    sys.stdout = tee
    try:
        rc = main()
    finally:
        sys.stdout = tee.real
        (Path(__file__).with_suffix(".out")).write_text("".join(tee.buf), encoding="utf-8")
    sys.exit(rc)
