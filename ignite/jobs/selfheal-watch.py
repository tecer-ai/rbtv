#!/usr/bin/env python3
"""Watch-heartbeat freshness detector + relaunch (task 7.72, run issue G-2).

Fired by the ignite daemon as a `fire-tool` job. `fire-tool` runs a tool's `argv`
VERBATIM (ticker.js `runToolLikeExec`, caps {} / sandbox {}) and appends nothing, so
every parameter this script needs is baked into the catalogue entry that names it.
One entry per target — the live package and its throwaway twin are separate entries.

WHAT "HEALTHY" MEANS HERE — a heartbeat is TWO facts, never one
-----------------------------------------------------------------
`watch.py` stamps `{package}/coordination/watch-heartbeat.json` with `last_pass`,
`loop_min` and `pid` every pass. On 2026-07-27 04:46-04:54 that file kept reading a
recent `last_pass` and a `pid` for a watch.py the owner had just killed: a well-formed
gravestone. Freshness alone would have read it as healthy for a whole tolerance window.
So this detector requires BOTH:

  1. `last_pass` is no older than `loop_min * TOLERANCE` minutes, and
  2. the `pid` in the file is ALIVE and is a `watch.py` for THIS package.

Either fact failing is staleness.

TOLERANCE = 3, and the number is not free: `coord.watcher_heartbeat()` already judges
the same file at `loop_min * 3` ("one skipped pass is a slow tmux capture, three in a
row is a dead loop") and that judgement is what `coordinate workers` prints for humans.
A different multiplier here would make the automated and the human-visible verdicts
disagree about the same file — the automation must not invent a second truth.

DOUBLE-START REFUSAL
--------------------
Before relaunching, the script scans /proc for any live `watch.py --package <target>`.
If one exists the relaunch is REFUSED even when the heartbeat looks stale — a run that
carries two watch loops is its own defect, and a stale-looking heartbeat beside a live
writer is a heartbeat-write problem, not a dead-sensor problem. Reported, never healed.

WHAT THIS SCRIPT WRITES
-----------------------
Nothing but stdout/stderr. `fire-tool` captures that into
`{data_root}/logs/<session>.log`, which task 7.13's age sweep already bounds. Inventing
a private log file would create a new unbounded artifact class outside that sweep.

FALLBACK, one command (the kit path stays armed):
  nohup python3 <team-kit>/watch.py --package <PKG> --notify --loop 10 >/dev/null 2>&1 &
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobcontain  # noqa: E402  — self-containment; a fire-tool exec gets none (G-30)

TOLERANCE = 3
DEFAULT_LOOP_MIN = 10


def log(msg):
    print(f"selfheal-watch: {msg}", flush=True)


def read_cmdline(pid):
    """argv of a live pid as a list, or None when the pid is not alive/readable."""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
        return None
    return [p for p in raw.decode("utf-8", "replace").split("\0") if p]


def is_watch_for(pid, package):
    """True when `pid` is alive AND is a watch.py loop for exactly this package.

    Identity by argv, not by liveness: a recycled pid belonging to some other process
    must never be mistaken for the sensor (the reaper lesson, coord.py arm_pid_reaper)."""
    argv = read_cmdline(pid)
    if not argv:
        return False
    if not any(a.endswith("watch.py") for a in argv):
        return False
    return str(package) in argv


def live_watchers(package):
    """Every live watch.py pid bound to this package. The double-start guard's evidence."""
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == os.getpid():
            continue
        if is_watch_for(pid, package):
            found.append(pid)
    return sorted(found)


def read_heartbeat(path):
    """(dict, None) or (None, reason). An unreadable heartbeat is STALE, never a crash."""
    if not path.exists():
        return None, "no heartbeat file"
    try:
        hb = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, f"unreadable heartbeat ({exc})"
    if not isinstance(hb, dict) or not hb.get("last_pass"):
        return None, "heartbeat carries no last_pass"
    return hb, None


def age_minutes(last_pass):
    try:
        return int((datetime.now() - datetime.fromisoformat(last_pass)).total_seconds() // 60)
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser(description="Relaunch watch.py when the run's sensor goes stale.")
    ap.add_argument("--package", required=True, help="run package whose heartbeat is judged")
    ap.add_argument("--watch-py", required=True, help="absolute path to watch.py")
    ap.add_argument("--loop", type=int, default=DEFAULT_LOOP_MIN,
                    help="loop minutes to relaunch with (default 10)")
    ap.add_argument("--tolerance", type=int, default=TOLERANCE,
                    help="missed passes tolerated before stale (default 3)")
    ap.add_argument("--notify", action="store_true",
                    help="relaunch watch.py with --notify (the live sensor's shape)")
    ap.add_argument("--watch-arg", action="append", default=[],
                    help="extra argument passed through to the relaunched watch.py, repeatable. "
                         "The relaunch must reproduce the sensor's OWN invocation: the live loop "
                         "runs with --mem-floor-mb, and a self-heal that silently drops it would "
                         "resurrect a WEAKER sensor than the one that died.")
    ap.add_argument("--dry-run", action="store_true",
                    help="decide and report; never relaunch")
    ap.add_argument("--mem-mb", type=int, default=256, help="self address-space cap (default 256)")
    ap.add_argument("--budget-s", type=int, default=120, help="self wall-clock cap (default 120)")
    args = ap.parse_args()

    jobcontain.contain(mem_mb=args.mem_mb, seconds=args.budget_s)

    package = Path(args.package).resolve()
    held = jobcontain.single_instance(str(package / "coordination" / ".selfheal-watch.lock"))
    if held is None:
        log("ANOTHER INSTANCE HOLDS THE LOCK — exiting without judging. A periodic job must "
            "never stack instances onto a target a previous run is still repairing.")
        return 0
    hb_path = package / "coordination" / "watch-heartbeat.json"
    log(f"package={package} heartbeat={hb_path} tolerance={args.tolerance}")

    hb, reason = read_heartbeat(hb_path)

    # ---- fact 1: freshness -------------------------------------------------
    if hb is None:
        stale, why = True, reason
    else:
        loop_min = hb.get("loop_min") if isinstance(hb.get("loop_min"), int) else None
        stale_after = (loop_min * args.tolerance) if loop_min and loop_min > 0 else 30
        age = age_minutes(hb["last_pass"])
        if age is None:
            stale, why = True, f"unparseable last_pass {hb['last_pass']!r}"
        elif age > stale_after:
            stale, why = True, f"last_pass {age} min old > {stale_after} min ({loop_min}x{args.tolerance})"
        else:
            # ---- fact 2: the stated writer is a LIVE watch.py for this package ----
            pid = hb.get("pid")
            if not isinstance(pid, int):
                stale, why = True, "heartbeat carries no pid — freshness alone is not liveness"
            elif not is_watch_for(pid, package):
                stale, why = True, (f"GRAVESTONE: last_pass is {age} min old (fresh) but pid {pid} "
                                    f"is not a live watch.py for this package")
            else:
                stale, why = False, f"last_pass {age} min old, pid {pid} is a live watch.py"

    if not stale:
        log(f"HEALTHY — no-op. {why}")
        return 0

    log(f"STALE — {why}")

    # ---- double-start refusal ---------------------------------------------
    others = live_watchers(package)
    if others:
        log(f"REFUSING RELAUNCH — live watch.py already bound to this package: {others}. "
            f"A run never carries two watch loops; a stale heartbeat beside a live writer is a "
            f"heartbeat-write defect, not a dead sensor. Reported, not healed.")
        return 0

    cmd = [sys.executable, str(Path(args.watch_py).resolve()), "--package", str(package)]
    if args.notify:
        cmd.append("--notify")
    cmd += ["--loop", str(args.loop)]
    cmd += list(args.watch_arg)

    # The sensor must OUTLIVE this job's exec, so it gets its own transient unit —
    # a plain detached child dies with the job's cgroup (see jobcontain.detach_argv).
    unit = jobcontain.unit_name("rbtv-watch", package)
    launch, unit = jobcontain.detach_argv(cmd, unit)

    if args.dry_run:
        log(f"DRY-RUN — would relaunch: {' '.join(launch)}")
        return 0

    # preexec restores the pre-contain() limits: the relaunched sensor must NOT inherit
    # this detector's 256 MB cap, or self-healing would guarantee the next death.
    res = subprocess.run(launch, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, timeout=60,
                         preexec_fn=jobcontain.child_preexec)
    out = (res.stdout or b"").decode("utf-8", "replace").strip()
    if out:
        log(f"  launcher| {out}")

    # The launcher's exit code is not the verdict — a LIVE watch.py is. Re-check.
    for _ in range(20):
        back = live_watchers(package)
        if back:
            log(f"RELAUNCHED AND VERIFIED ALIVE — pid(s) {back}"
                + (f", unit {unit}" if unit else "") + f" — {' '.join(cmd)}")
            return 0
        time.sleep(0.5)
    log(f"RELAUNCH DID NOT TAKE — no live watch.py for this package after 10s "
        f"(launcher exit {res.returncode}). Next period retries. Fall back by hand: "
        f"nohup {' '.join(cmd)} >/dev/null 2>&1 &")
    return 1


if __name__ == "__main__":
    sys.exit(main())
