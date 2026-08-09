#!/usr/bin/env python3
"""Watch-heartbeat freshness detector + relaunch (task 7.72, run issue G-2).

Fired by the ignite daemon as a `fire-tool` job. `fire-tool` runs a tool's `argv`
VERBATIM (ticker.js `runToolLikeExec`, caps {} / sandbox {}) and appends nothing, so
every parameter this script needs is baked into the catalogue entry that names it.
One entry per target — the live package and its throwaway twin are separate entries.

WHAT "HEALTHY" MEANS HERE — a heartbeat is TWO facts, never one
-----------------------------------------------------------------
`watch.py` stamps `{package}/coordination/watch-heartbeat.json` with `last_pass`,
`loop_seconds` and `pid` every pass. On 2026-07-27 04:46-04:54 that file kept reading a
recent `last_pass` and a `pid` for a watch.py the owner had just killed: a well-formed
gravestone. Freshness alone would have read it as healthy for a whole tolerance window.
So this detector requires BOTH:

  1. `last_pass` is no older than `loop_seconds * TOLERANCE` SECONDS, and
  2. the `pid` in the file is ALIVE and is a `watch.py` for THIS package.

Either fact failing is staleness.

⚠ SECONDS, NOT MINUTES, SINCE task 7.112 (`r-watch-loop-30s`: cadence 30 s maximum). This
detector used to compare whole minutes against `loop_min * TOLERANCE`, and at a 30-second
cadence that clock was COARSER THAN THE THING IT JUDGES — a loop several passes dead still
measured age 0 and read healthy. `loop_min` is still accepted as a fallback so a mixed-version
window (an older watch.py still running) is judged on the cadence it actually reported instead
of dropping to the flat window.

TOLERANCE = 3, and the number is not free: `coord.watcher_heartbeat()` judges the same file at
three missed passes ("one skipped pass is a slow tmux capture, three in a row is a dead loop")
and that judgement is what `coordinate workers` prints for humans. A different multiplier here
would make the automated and the human-visible verdicts disagree about the same file — the
automation must not invent a second truth. ⚠ THE TWO NOW DIFFER IN PRECISION, NOT IN INTENT:
coord.py still multiplies the legacy minute-denominated `loop_min`, which `watch.py` writes
rounded UP, so coord's threshold is the coarser of the two. Retiring `loop_min` across all its
readers needs `coord.py`, which task 7.112 does not hold; it is filed, not forgotten.

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
  nohup python3 <team-kit>/watch.py --package <PKG> --notify --loop-forever >/dev/null 2>&1 &
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
# ⚠ NO DEFAULT CADENCE CONSTANT LIVES HERE ANY MORE (task 7.112, ruling `r-watch-loop-30s`).
# `DEFAULT_LOOP_MIN = 10` stood here and it was THE LIVE DEFAULT — the actual value every relaunch
# carried — which made this file a home for a policy number it does not own. The cadence's one home
# is the run's `budget.json` (`r-bar-home-is-the-run-budget-json`), and the relaunch now passes
# `--loop-forever` with NO number at all, so `watch.py` resolves the declaration itself. A recovery
# path that holds no number cannot resurrect a sensor running at a cadence nobody ruled.
FLAT_STALE_S = 1800


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


def age_seconds(last_pass):
    """Age of the stamp in SECONDS, or None when it does not parse.

    ⚠ WAS `age_minutes`, AND THE UNIT WAS THE DEFECT (task 7.112). It floor-divided to whole
    minutes, so under the ruled ≤30 s cadence (`r-watch-loop-30s`) a loop that had missed SEVERAL
    passes still measured age 0 and every freshness verdict rounded to healthy. A clock coarser than
    the cadence it judges cannot see the failure it exists to detect.
    """
    try:
        return int((datetime.now() - datetime.fromisoformat(last_pass)).total_seconds())
    except (TypeError, ValueError):
        return None


def stale_after_seconds(hb, tolerance):
    """(threshold in seconds, the cadence it came from or None) — how late is too late.

    Prefers the heartbeat's `loop_seconds`; falls back to the legacy minute-denominated `loop_min`
    written by an OLDER watch.py, so a relaunch during a mixed-version window is judged on the
    cadence it actually reported rather than dropped to the flat threshold. Both absent → flat.
    """
    secs = hb.get("loop_seconds")
    if isinstance(secs, int) and not isinstance(secs, bool) and secs > 0:
        return secs * tolerance, secs
    mins = hb.get("loop_min")
    if isinstance(mins, int) and not isinstance(mins, bool) and mins > 0:
        return mins * 60 * tolerance, mins * 60
    # A one-shot pass has no cadence to be late against: judge it on a flat window.
    return FLAT_STALE_S, None


def resolve_package(args):
    """(Path, provenance) or (None, refusal) — the run package this job judges.

    THE TARGET IS RESOLVED, NEVER PINNED (task 7.117, leader ruling on ask #204; `issues.md`
    G-305/G-318). The LIVE entry used to carry `--package <a run package>` for a run that closed
    2026-07-27, so a fire would have relaunched a sensor against a CLOSED run's package while the
    mechanism's own status kept reading healthy. Swapping in a different run number would have
    reproduced that defect at the next run close; the fix is that the live entry names NO run at
    all and asks the register instead.

    ⚠ THE TWO ENTRIES WERE NEVER POINTED AT THE SAME KIND OF THING, and G-305 records them as
    though they were. Only the live entry named a RUN package. The twin names a SCRATCH FIXTURE
    that merely sits inside a closed run's folder — a different claim, and the distinction is why
    only one of them changed here.

    `--package` SURVIVES AS THE EXPLICIT OVERRIDE and wins whenever it is present. That is not a
    compatibility shim: the THROWAWAY twin must target a scratch package and must NEVER resolve
    live, because a throwaway watcher pointed at the live run injects throwaway state into the live
    room (the twin's own entry comment; C4). The twin therefore passes `--package` and NOT
    `--goal`/`--coord`, so dropping its override cannot silently promote it onto the live run — it
    refuses instead. That is a deliberate, disclosed divergence from "both entries carry an
    identical flag surface": what the twin exists to keep identical is the RELAUNCH argv it
    exercises on the live entry's behalf, and that is untouched by which target flag it carries.

    ⚠ THERE IS NO REGISTER ANY MORE, AND THE TARGET IS THE LEASE (7.607 E3, design-lock item 1).
    Liveness is DERIVED at fire time from live evidence — the goal's tmux room and its ancestry-
    verified seats — and never from a stored status. `coord.derive_lease()` is the ONE accessor
    over the one home (`server/lease/lease.js`); a second room predicate here would be the
    two-readers shape `G-301` is made of, exactly as a second `runs.csv` parse was.

    ⚠ WHAT THIS REPLACES WAS ALREADY BROKEN, NOT MERELY DATED. Until this change the resolution
    composed `<goal>/runs/<name>` out of `coord.resolve_live_run`'s compat return — and E2b moved
    the layout so that path no longer exists: a fire would have relaunched the sensor into a
    directory that is not there. The lease hands back the package directly, so there is nothing
    left to compose and nothing left to get wrong.

    `coord` is imported INSIDE this function from the `--coord` path, mirroring
    `goal-watcher-job.py:454`: at module level it would make every copy-and-test of this job carry
    a sibling dependency it does not otherwise need.

    Refusal is FAIL-CLOSED and returns no package, at THREE doors — an unreadable lease
    (ignorance), no room (the goal is not executing), and more than one room (a box state nothing
    here should resolve). A self-heal that guessed its target is the failure this task removes.
    """
    if args.package:
        return Path(args.package).resolve(), "--package (explicit override; the lease is not consulted)"
    if not args.goal or not args.coord:
        absent = [f"--{f}" for f in ("goal", "coord") if not getattr(args, f)]
        missing = " and ".join(absent) + (" are absent" if len(absent) > 1 else " is absent")
        return None, (f"no --package, so the target must be DERIVED from the goal's live lease — "
                      f"but {missing}. Lease resolution needs BOTH: --goal names the goal folder, "
                      f"--coord supplies the ONE accessor.")
    sys.path.insert(0, str(Path(args.coord).resolve().parent))
    import coord  # noqa: E402  — the lease's single accessor; see this docstring
    goal = Path(args.goal).resolve()
    lease, why = coord.derive_lease(goal)
    if why:
        return None, (f"the lease for {goal.name} is UNREADABLE ({why}). That is IGNORANCE, not an "
                      f"idle goal — refusing rather than reading it as 'nothing is running'.")
    rooms = lease.get("rooms") or []
    if len(rooms) != 1:
        return None, (f"the live lease for {goal.name} names {len(rooms)} rooms and the design "
                      f"rules exactly one (lock item 2): "
                      + ("the goal is NOT EXECUTING, so there is no sensor to judge"
                         if not rooms else
                         "two rooms of one goal is a box state nothing here should resolve"))
    pkg = Path(rooms[0].get("packageDir") or "").resolve()
    return pkg, (f"DERIVED from the live lease of {goal.name}: room {rooms[0].get('room')!r} -> "
                 f"{pkg} (no stored status read; design-lock item 1)")


def main():
    ap = argparse.ArgumentParser(description="Relaunch watch.py when the run's sensor goes stale.")
    # ⚠ NO LONGER REQUIRED, AND NO RUN NUMBER LIVES IN THE CATALOGUE ENTRY ANY MORE (task 7.117).
    # `--package` is the EXPLICIT OVERRIDE; absent, the target resolves from the run register at
    # FIRE TIME. See resolve_package() for why the override survives and why the twin needs it.
    ap.add_argument("--package", default=None,
                    help="package whose heartbeat is judged — the EXPLICIT OVERRIDE. Absent: "
                         "DERIVED from the goal's live lease (needs --goal and --coord)")
    ap.add_argument("--goal", default=None,
                    help="goal folder whose LIVE LEASE resolves the package when --package is "
                         "absent. Names a GOAL — there is no run number left to go stale")
    ap.add_argument("--coord", default=None,
                    help="absolute path to the kit's coord.py, which supplies the ONE lease "
                         "accessor (coord.derive_lease). Required when --package is absent")
    ap.add_argument("--watch-py", required=True, help="absolute path to watch.py")
    # `--loop` is GONE, not re-valued: this job held the live default, and a relaunch that carries a
    # cadence number is a second home for it. `watch.py --loop-forever` reads the run's declaration.
    # Registered ONLY to refuse, so a stale catalogue entry fails loudly instead of being ignored by
    # argparse's own "unrecognized arguments" error, which names no replacement.
    ap.add_argument("--loop", default=None,
                    help="RETIRED (r-watch-loop-30s). The relaunch passes --loop-forever and "
                         "watch.py reads the cadence from the run's budget.json")
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
    if args.loop is not None:
        ap.error("--loop is RETIRED (owner ruling r-watch-loop-30s): it was loop MINUTES and this "
                 "job held the live default, which made it a second home for a policy number. The "
                 "relaunch now passes --loop-forever and watch.py reads "
                 "cadence.watch_loop_max_seconds from the run's budget.json. Drop the flag and its "
                 "value from the catalogue entry — do not re-value them.")

    jobcontain.contain(mem_mb=args.mem_mb, seconds=args.budget_s)

    package, provenance = resolve_package(args)
    if package is None:
        # FAIL CLOSED, LOUDLY. Judging the wrong package is exactly G-305: a self-heal that reports
        # healthy while doing nothing for the live run. A refusal that names the ambiguity is the
        # only safe answer, and a non-zero exit puts it in the ticker's own completion record
        # instead of leaving it as a log line nobody reads.
        log(f"REFUSING — cannot resolve which run to judge: {provenance}")
        return 1
    log(f"target={package} via {provenance}")
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
        stale_after, cadence_s = stale_after_seconds(hb, args.tolerance)
        age = age_seconds(hb["last_pass"])
        if age is None:
            stale, why = True, f"unparseable last_pass {hb['last_pass']!r}"
        elif age > stale_after:
            basis = f"{cadence_s}sx{args.tolerance}" if cadence_s else "flat (no cadence reported)"
            stale, why = True, f"last_pass {age}s old > {stale_after}s ({basis})"
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
    # NO CADENCE VALUE CROSSES THIS BOUNDARY. `--loop-forever` says "keep looping" and carries no
    # number; `watch.py` resolves `cadence.watch_loop_max_seconds` from the run's budget.json itself.
    # This used to be `["--loop", str(args.loop)]`, which made every relaunch a courier for a policy
    # number — and by this file's own G-42 argument, a relaunch carrying a stale cadence resurrects a
    # WEAKER sensor than the one that died and the run never notices the downgrade.
    cmd.append("--loop-forever")
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
