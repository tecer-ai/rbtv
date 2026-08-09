#!/usr/bin/env python3
"""probe-dead-room-sensor-session.py — the automatic sensor restart works on a DEAD room (7.561).

WHAT IT SCORES. `goal-watcher-job.py`'s STALE-SENSOR row does not merely flag: under `--notify` it
performs an inline mechanical fix, exec'ing team-monitor's own idempotent `ensure` through
`run_inline` (CMP-21 invariant 2). Both of its call sites used to build that argv WITHOUT
`--session` — and team-monitor's `resolve_session` takes an explicit `--session` first, else asks
the ROSTER for a pane that still resolves to a live tmux session, else REFUSES (`SessionUnresolved`,
`G-296`). A room whose sensor has died and whose roster panes are gone with it IS that state. So
the recovery path existed, polled, fired — and could not succeed in precisely the state it exists to
recover from. Measured on the live run-3 package: 432 roster seats, 408 carrying a pane cell, ZERO
resolving.

⚠⚠ THE FIXTURE IS A REAL DEAD ROOM, BUILT DELIBERATELY, AND THE PROBE PROVES IT IS DEAD BEFORE IT
PROVES ANYTHING ELSE. A tmux session that genuinely exists (so a restarted sensor has a room to
watch), a roster whose every pane cell is a `%`-id tmux does not know (so NOTHING resolves), and no
sensor running. A test that recovers a room which still has a LIVE pane does not exercise the defect
at all: the sessionless `ensure` would resolve from that pane and pass fix or no fix.

⚠⚠ THE RED ARM RUNS THE SHIPPING CODE, NOT A PRE-FIX COPY — and that is what makes it
discriminating rather than a re-statement of the fixture. R1 and R3 are the SAME binary, the SAME
package and the SAME `--notify` pass; they differ ONLY in whether the room's session has been banked
yet. R1 (nothing banked) builds `ensure --package X` — the pre-fix argv, byte for byte — and the
inline fix FAILS. R3 (banked) builds `ensure --package X --session <room>` and the inline fix
SUCCEEDS, leaving a sensor actually running. Revert the fix and R3 becomes R1: red.

⚠ THE ARM THAT MATTERS IS R3, AND IT IS THE **ABSENT-SNAPSHOT** SITE (`main`'s unreadable/absent
branch), not the stale-but-readable one (`evaluate`'s ROW 5). That is the dead-room arm this task
exists for, and the one the task row's own criterion (2) failed to name. R4 covers the other site,
so the pair proves ONE mechanism across both rather than a fix at the site that was easier to reach.

⚠ NO SKIP PREDICATE KEYED ON THE ROOM. The only INOPERATIVE exits here are "the fixture could not be
BUILT at all" (no tmux binary, `new-session` failed, a source file missing). An absent or
unresolvable room IS the failure state under test — a guard that skipped on it would make the whole
probe vacuous while reporting green.

ARMS
  C0  the fixture is a real dead room: the tmux session EXISTS, and not one roster pane resolves.
  R1  RED — with no session banked, the pass's inline fix runs the sessionless `ensure` and FAILS,
      and no sensor comes up. This is the pre-fix behaviour, produced by the shipping code.
  R2  a pass over a readable snapshot BANKS the room's session from the snapshot's own `session`
      field (`remember_session`) — never derived from the package path (`G-296`).
  R3  GREEN, THE DEAD-ROOM ARM — snapshot now ABSENT, same pass, and the inline fix runs
      `ensure … --session <room>`, exits OK, and a sensor is ALIVE afterwards (writer lock held).
  R4  the other call site (stale-but-readable snapshot, `evaluate`'s ROW 5) carries `--session`
      too, from the same banked source: ONE mechanism, both sites.
  R5  the staleness tripwire's PAUSE half is intact — both arms report ENFORCEMENT PAUSED, and the
      recover half did not cost the pause half (task 7.32's tripwire is pause PLUS recover).

The pass exits non-zero on its own (a scratch package has no live recipient, so flag DELIVERY
fails by construction) — every arm therefore reads the pass's STDOUT, never its exit code.

Run it through the suite — `node deploy/probe-suite.js --only dead-room-sensor-session` — never by
hand (`G-163`). Exit 0 = every property holds · 1 = a property is broken · 2 = INOPERATIVE.
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

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe-dead-room-sensor-session.out"
JOB = HERE.parent / "goal-watcher-job.py"
COORD = HERE.parents[1] / "team-kit" / "coord.py"
TEAM_MONITOR = HERE.parents[2] / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"
ROOM = f"w7561-probe-{os.getpid()}"
# ⚠ NOT AN ARGV COPY OF A POLICY NUMBER (`r-floor-single-source`, `G-42`). The job REFUSES to start
# without a declared floor, and `--mem-floor-mb` would hand it one over argv — the exact shape that
# ruling outlaws, and `floor-lint.py` refuses it. The fixture package DECLARES its own floor in its
# own `budget.json` instead (the number's one home) and the job READS it, which is also the
# production path. The value is this fixture's, not a copy of the run's — no row here reads it.
FIXTURE_FLOOR_MB = 4096

lines, failures, inoperative = [], [], []
tm = None


def say(s):
    lines.append(s)


def check(arm, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {arm}  {detail}")
    if not ok:
        failures.append(arm)


def stop(arm, why):
    say(f"INOPERATIVE  {arm}  {why}")
    inoperative.append(arm)


def tmux(*argv):
    return subprocess.run(["tmux", *argv], capture_output=True, text=True)


def write_snapshot(pkg, age_s):
    """A snapshot in team-monitor's own shape. `session` is the field the fix is banked from."""
    (pkg / "state.json").write_text(json.dumps({
        "captured_at": time.time() - age_s,
        "captured_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session": ROOM, "session_alive": True, "seats": [], "roster_absent": [],
    }), encoding="utf-8")


def job_pass(pkg, notify=True):
    """One real `--notify` pass of the job over the fixture. Returns its stdout+stderr."""
    r = subprocess.run(
        [sys.executable, "-B", str(JOB), "--package", str(pkg), "--room-package", str(pkg),
         "--coord", str(COORD), "--team-monitor", str(TEAM_MONITOR),
         *(["--notify"] if notify else [])],
        capture_output=True, text=True, timeout=180)
    return (r.stdout or "") + (r.stderr or "")


def inline_line(out):
    """The `inline fix [...]` line the pass printed — the outcome of the ACTUAL exec."""
    return next((ln.strip() for ln in out.splitlines() if "inline fix [" in ln), "")


def sensor_pid(pkg):
    lock = pkg / "coordination" / "team-monitor.lock"
    try:
        pid = int(lock.read_text(encoding="utf-8").strip().split()[0])
    except (OSError, ValueError, IndexError):
        return 0
    try:
        os.kill(pid, 0)
    except OSError:
        return 0
    return pid


def load_team_monitor():
    """Import team-monitor BY LOCATION so C0 can ask the SHIPPING resolver, not a copy of it."""
    spec = importlib.util.spec_from_file_location("team_monitor_under_probe", TEAM_MONITOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    global tm
    for p in (JOB, COORD, TEAM_MONITOR):
        if not p.exists():
            return stop("FIXTURE", f"source missing: {p}")
    if not shutil.which("tmux"):
        return stop("FIXTURE", "no tmux binary — the fixture cannot be built at all")
    tm = load_team_monitor()

    td = Path(tempfile.mkdtemp(prefix="probe-w7561-"))
    pkg = td / "runs" / "run-1"
    (pkg / "coordination").mkdir(parents=True)
    # A roster whose every pane is a %-id tmux does not know: the room is real, the panes are not.
    (pkg / "coordination" / "workers.md").write_text(
        "| agent | active | tmux pane | working on | checked in |\n"
        "|-------|--------|-----------|------------|------------|\n"
        "| leader | yes | %999901 | dead | 2026-08-09 00:00 |\n"
        "| worker-a | yes | %999902 | dead | 2026-08-09 00:00 |\n", encoding="utf-8")
    (pkg / "budget.json").write_text(
        json.dumps({"floors": {"pressure_warn_mb": FIXTURE_FLOOR_MB}}), encoding="utf-8")

    if tmux("new-session", "-d", "-s", ROOM, "sleep", "600").returncode != 0:
        shutil.rmtree(td, ignore_errors=True)
        return stop("FIXTURE", f"tmux new-session -s {ROOM} failed — fixture not built")
    try:
        # ---- C0: the fixture IS the dead-room state -----------------------------------------
        # ⚠ ASKED OF THE PRODUCTION PREDICATE ITSELF, never of a proxy. An earlier draft scored
        # `tmux display-message`'s EXIT CODE — and tmux answers 0 with an EMPTY session name for a
        # pane id it does not know, so that draft read the dead roster as fully resolving. A
        # control that re-derives the thing it is controlling for measures the re-derivation.
        alive = tmux("has-session", "-t", ROOM).returncode == 0
        try:
            resolved = tm.resolve_session(str(pkg))
        except tm.SessionUnresolved as exc:
            resolved = f"REFUSED: {str(exc).splitlines()[0][:90]}"
            unresolved = True
        else:
            unresolved = False
        check("C0", alive and unresolved and not sensor_pid(pkg),
              f"tmux session {ROOM!r} alive={alive}; team-monitor's own resolve_session on this "
              f"roster -> {resolved!r}; sensor running={bool(sensor_pid(pkg))} — a pane that "
              f"resolved here would let the SESSIONLESS ensure succeed and no arm could discriminate")

        # ---- R1: RED. Nothing banked -> the sessionless argv -> the inline fix FAILS ---------
        out1 = job_pass(pkg)                      # no state.json at all: the absent-snapshot site
        fix1 = inline_line(out1)
        check("R1", ("--session" not in fix1) and "-> FAILED" in fix1 and not sensor_pid(pkg),
              f"pre-fix argv and pre-fix outcome, from the shipping code: {fix1!r}; sensor "
              f"running after it={bool(sensor_pid(pkg))}")

        # ---- R2: a readable snapshot banks the room's session, from the SNAPSHOT ------------
        write_snapshot(pkg, age_s=9999)
        out2 = job_pass(pkg)
        banked = json.loads((pkg / "coordination" / "goal-watcher-state.json")
                            .read_text(encoding="utf-8")).get("_session")
        check("R2", banked == ROOM,
              f"banked _session={banked!r} (the snapshot's own `session` field, never derived "
              f"from {pkg})")

        # ---- R4: the OTHER call site (ROW 5, stale but readable) carries it too --------------
        fix2 = inline_line(out2)
        check("R4", f"--session {ROOM}" in fix2,
              f"evaluate()'s ROW 5 argv: {fix2!r} — same mechanism as the absent-snapshot site")

        # ---- R3: GREEN, THE DEAD-ROOM ARM. Snapshot gone; the fix must still reach the room --
        # ⚠ THE ROOM IS PUT BACK INTO THE DEAD STATE FIRST. R2's pass ACTUATED (site 1's fix ran
        # for real and a sensor came up), and a live sensor rewrites state.json within a cadence —
        # so without this the "absent snapshot" arm would read a FRESH one, take no stale branch
        # at all, and score an empty string as if it were a verdict.
        subprocess.run([sys.executable, "-B", str(TEAM_MONITOR), "stop", "--package", str(pkg)],
                       capture_output=True, text=True, timeout=60)
        (pkg / "state.json").unlink(missing_ok=True)
        say(f"R3 pre-state: sensor running={bool(sensor_pid(pkg))}, "
            f"state.json present={(pkg / 'state.json').exists()} (both must be False)")
        out3 = job_pass(pkg)
        fix3 = inline_line(out3)
        pid = sensor_pid(pkg)
        check("R3", f"--session {ROOM}" in fix3 and "-> OK" in fix3 and pid > 0,
              f"absent-snapshot argv+outcome: {fix3!r}; sensor now running pid={pid} — the room "
              f"the sessionless call could not reach in R1 is RECOVERED by the automatic path")

        # ---- R5: the tripwire's PAUSE half survived the recover half -------------------------
        check("R5", all("[ENFORCEMENT PAUSED: stale sensor]" in o for o in (out1, out3)),
              "both dead-room passes still PAUSE enforcement (task 7.32's tripwire is pause PLUS "
              "recover; fixing the recover half must not cost the pause half)")
    finally:
        subprocess.run([sys.executable, "-B", str(TEAM_MONITOR), "stop", "--package", str(pkg)],
                       capture_output=True, text=True)
        tmux("kill-session", "-t", ROOM)
        left = sensor_pid(pkg)
        if left:
            os.kill(left, 9)
        say(f"teardown: tmux session {ROOM} killed={tmux('has-session', '-t', ROOM).returncode != 0}"
            f"; sensor left running={bool(left)}")
        shutil.rmtree(td, ignore_errors=True)


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-dead-room-sensor-session  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
