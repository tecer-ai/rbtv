#!/usr/bin/env python3
"""Dead-room detector + recovery relaunch (task 7.71, owner ruling `r-selfheal-job`).

Fired by the ignite daemon as a `fire-tool` job. `fire-tool` runs a tool's `argv`
VERBATIM (ticker.js `runToolLikeExec`, caps {} / sandbox {}) and appends nothing, so
every parameter — the session to watch AND the recovery argv to run — is baked into
the catalogue entry that names it. One entry per target: the live room and its
throwaway twin are separate entries, so re-pointing a job at the live room is a config
edit plus an integrator-owned daemon restart, never an edit to a file this script reads.

WHY A DETECTOR AND NOT A `launch-agent` JOB
-------------------------------------------
A periodic `launch-agent` job would spawn the recovery agent every period regardless of
room health — an unbounded paid path. Detection must be deterministic, so the job is
`fire-tool` over this script, which decides and fires nothing when the room is alive.

THE DESIGN CALL THIS SCRIPT SETTLES — recovery goes through the KIT, not the daemon
-----------------------------------------------------------------------------------
The task left open whether a dead room is recovered (a) by asking the DAEMON to launch
the recovery agent (`ignite add-job --fn launch-agent`), keeping the daemon the sole
spawn path, or (b) by re-creating the room through the team-kit path that created it.
CHOSEN: (b), and the reasons, not a default:

  1. The invariant does not reach here. DEC-1 R3/R28's sole-spawn-path rule governs
     daemon-spawned SEATS. The room is a tmux SESSION, not a seat, and this room was
     created by the kit. Routing its recovery through the daemon would WIDEN the
     invariant's scope, which the task forbids doing silently.
  2. The daemon cannot currently do it anyway. The daemon's tmux-room target activates
     only when `RBTV_IGNITE_TMUX_ROOM` is set on the unit, and it is deliberately NOT
     set (integrator, 2026-07-27 04:43) — precisely so no seat reaches the new path by
     accident. A recovery built on it would be dead code tonight.
  3. `r-cutover-gated` bars the run's own control loop from adopting a newly built
     feature before it has run in shadow and passed probes. The room IS the control
     loop. Recovering it through the un-shadowed daemon path is the exact cutover that
     ruling exists to prevent.

Neither invariant is widened: the daemon stays the sole spawner of daemon-spawned
seats, and the kit stays the spawner of this run's room. What changes is only WHO
notices the room died — a periodic job instead of a human.

KIT FALLBACK, one command (stays armed, per `r-cutover-gated`):
  python3 <team-kit>/coord.py --package <PKG> launch --only <SEAT> --force

WHAT THIS SCRIPT WRITES
-----------------------
Nothing but stdout/stderr, captured by `fire-tool` into `{data_root}/logs/<session>.log`,
which task 7.13's age sweep already bounds. A private log file would be a new unbounded
artifact class outside that sweep.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobcontain  # noqa: E402  — self-containment; a fire-tool exec gets none (G-30)


def log(msg):
    print(f"selfheal-room: {msg}", flush=True)


def session_alive(session, socket=None):
    """True when a tmux server is running AND holds a session with this exact name.

    `has-session -t =NAME` — the `=` prefix forces an EXACT match; without it tmux
    matches by prefix and a throwaway named `tw-room-probe` would answer for a live
    `tw-room-probe-2`."""
    tmux = shutil.which("tmux")
    if not tmux:
        log("tmux not on PATH — cannot judge the room; treating as UNKNOWN, firing nothing")
        return None
    cmd = [tmux] + (["-L", socket] if socket else []) + ["has-session", "-t", f"={session}"]
    res = subprocess.run(cmd,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0


def main():
    ap = argparse.ArgumentParser(
        description="Relaunch a dead team-kit room through the kit path that created it.")
    ap.add_argument("--session", required=True, help="tmux session name that IS the room")
    ap.add_argument("--timeout", type=int, default=300,
                    help="seconds to allow the recovery command (default 300)")
    ap.add_argument("--dry-run", action="store_true", help="decide and report; run no recovery")
    ap.add_argument("recovery", nargs=argparse.REMAINDER,
                    help="-- followed by the recovery argv (no shell; run verbatim)")
    ap.add_argument("--tmux-socket", default=None,
                    help="tmux -L socket name; omit for the default socket the room uses. "
                         "MUST match the socket the recovery argv targets, or the detector "
                         "judges a different server than the one it repairs.")
    ap.add_argument("--settle", type=float, default=15,
                    help="seconds to wait for the recovered room to appear (default 15)")
    ap.add_argument("--mem-mb", type=int, default=256, help="self address-space cap (default 256)")
    ap.add_argument("--budget-s", type=int, default=600, help="self wall-clock cap (default 600)")
    args = ap.parse_args()

    jobcontain.contain(mem_mb=args.mem_mb, seconds=args.budget_s)

    recovery = args.recovery[1:] if args.recovery and args.recovery[0] == "--" else args.recovery
    if not recovery:
        log("CONFIG ERROR — no recovery argv after `--`. Firing nothing.")
        return 2

    # One recovery per room at a time. The period is minutes; a recovery that launches a
    # harness is not, so without this a slow recovery would be joined by the next tick's.
    lock = Path(tempfile.gettempdir()) / f"selfheal-room.{args.session}.lock"
    held = jobcontain.single_instance(str(lock))
    if held is None:
        log(f"ANOTHER INSTANCE HOLDS {lock} — exiting without judging '{args.session}'.")
        return 0

    alive = session_alive(args.session, args.tmux_socket)
    if alive is None:
        return 2
    if alive:
        log(f"HEALTHY — tmux session '{args.session}' is alive. No-op.")
        return 0

    # The recovered room must OUTLIVE this job's exec. A tmux server (or a harness)
    # started as a plain child of the job goes down with the job's cgroup — proven on
    # the sensor side at 05:15 (jobcontain.detach_argv). Today the room recovery
    # survives only because a tmux server happens to already be running; on a GENUINELY
    # dead room there is none, which is precisely the case this job exists for. So the
    # recovery is launched as its own transient unit.
    unit = jobcontain.unit_name("rbtv-room", args.session)
    launch, unit = jobcontain.detach_argv(recovery, unit, daemonizes=True)

    log(f"DEAD ROOM — tmux session '{args.session}' does not exist. Recovery: {' '.join(launch)}")
    if args.dry_run:
        log("DRY-RUN — would run the recovery argv above; ran nothing.")
        return 0

    try:
        # preexec restores the pre-contain() limits: a recovery agent must not inherit
        # this detector's 256 MB cap, or the healer would guarantee the patient's death.
        res = subprocess.run(launch, timeout=args.timeout,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             preexec_fn=jobcontain.child_preexec)
    except subprocess.TimeoutExpired:
        log(f"RECOVERY TIMED OUT after {args.timeout}s — next period retries. "
            f"Fall back by hand: {' '.join(recovery)}")
        return 1
    except (OSError, ValueError) as exc:
        log(f"RECOVERY COULD NOT START ({exc}) — next period retries.")
        return 1

    tail = (res.stdout or b"").decode("utf-8", "replace").strip().splitlines()[-20:]
    for line in tail:
        log(f"  recovery| {line}")

    # The recovery's own exit code is not the verdict — the ROOM is. Re-check, but POLL:
    # `systemd-run` returns as soon as the unit is started, not when the room is up, so an
    # instant re-check races the recovery and reports failure on a success (observed
    # 2026-07-27 05:21 — the session was back at the same second the detector called it dead).
    for _ in range(int(args.settle * 2)):
        if session_alive(args.session, args.tmux_socket):
            log(f"RECOVERED — tmux session '{args.session}' exists again "
                f"(recovery exit {res.returncode}).")
            return 0
        time.sleep(0.5)
    log(f"RECOVERY RAN BUT THE ROOM IS STILL DEAD after {args.settle}s "
        f"(exit {res.returncode}) — next period retries. "
        f"Fall back by hand: {' '.join(recovery)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
