#!/usr/bin/env python3
"""Re-create a dead team-kit room and boot a recovery seat into it (task 7.71).

This is the recovery argv `selfheal-room.py` runs when the room is gone. It exists because
the obvious recovery — `coordinate launch --only <seat> --force` — CANNOT DO THE JOB, for
two reasons measured at source on 2026-07-27 05:41 (evidence `C1-target-resolution.txt`):

1. **`coordinate launch` never creates a session.** `grep -c new-session coord.py` → 0. It
   opens a WINDOW in an existing session (`tmux_new_window` → `tmux new-window -t <session>:`).
   On a genuinely dead room there is no session, so the launch has nowhere to go. A
   self-healing-room job built on it cannot create a room — its one purpose.

2. **Worse: it would not fail, it would guess.** `launch` resolves its target as
   `COORD_LAUNCH_TARGET or TMUX_PANE` (coord.py:3105, :3467), and a daemon-fired `fire-tool`
   exec has NEITHER. With both unset, tmux resolves an empty target to the MOST RECENT
   session — measured, it answered `build-core-daemon-mvp`, the LIVE room. **A recovery that
   opens agents into the live room believing it is repairing a dead one is worse than no
   recovery at all.**

So this script resolves the target EXPLICITLY and FAILS LOUD when it cannot. It never lets
tmux pick. Every exit path either names the pane it created, in the session it was asked for,
or refuses and returns non-zero so the next period retries.

Why this was not caught earlier, recorded because the lesson outlives the bug (run `issues.md`
G-41): every probe of the room recovery passed while its recovery argv was `tmux new-session`
— a command that DOES create a session — whereas the live entry's argv was `coordinate launch`,
which does not. The probe was not merely healthier than the real target; it was a DIFFERENT
MECHANISM wearing the same name.

Survival: this script is invoked by `selfheal-room.py` inside a transient unit started with
`KillMode=process`, so the tmux server it creates outlives the job's exec. Run it any other
way and that is on the caller.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time


def log(msg):
    print(f"recover-room: {msg}", flush=True)


def tmux_bin():
    exe = shutil.which("tmux")
    if not exe:
        log("FATAL — tmux is not on PATH. Refusing: a recovery that cannot see tmux must not "
            "guess at what it is repairing.")
        sys.exit(2)
    return exe


def tmux(*args, socket=None):
    cmd = [tmux_bin()] + (["-L", socket] if socket else []) + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def session_exists(session, socket=None):
    # `=NAME` forces an EXACT match; without it tmux matches by prefix.
    return tmux("has-session", "-t", f"={session}", socket=socket).returncode == 0


def session_of(pane, socket=None):
    r = tmux("display-message", "-p", "-t", pane, "#{session_name}", socket=socket)
    return r.stdout.strip() if r.returncode == 0 else ""


def panes_of(session, socket=None):
    """EVERY pane in the session. `-s` is load-bearing: without it `list-panes -t <session>`
    lists only the session's CURRENT WINDOW, so a seat launched into a new window is invisible.
    Measured 2026-07-27 05:48 — the harness had booted in %58 and the check reported no harness
    at all, i.e. FAILURE ON A SUCCESS. A check that can be wrong is not a check, whichever
    direction it errs in."""
    r = tmux("list-panes", "-s", "-t", f"={session}", "-F", "#{pane_id}", socket=socket)
    return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r.returncode == 0 else []


def first_pane_of(session, socket=None):
    panes = panes_of(session, socket)
    return panes[0] if panes else ""


def harness_pids(pane, socket=None):
    """Live harness pids under a pane — 'launched' is not 'running' (run issue G-11)."""
    r = tmux("display-message", "-p", "-t", pane, "#{pane_pid}", socket=socket)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    root = r.stdout.strip()
    ps = subprocess.run(["ps", "-eo", "pid,ppid,args"], capture_output=True, text=True)
    kids = []
    for line in ps.stdout.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, ppid, argv = parts
        if ppid == root and any(h in argv for h in ("claude", "codex", "opencode")):
            kids.append((pid, argv[:120]))
    return kids


def main():
    ap = argparse.ArgumentParser(
        description="Re-create a dead room and boot a recovery seat into it, explicitly.")
    ap.add_argument("--session", required=True, help="tmux session name that IS the room")
    ap.add_argument("--package", required=True, help="run package the seat belongs to")
    ap.add_argument("--seat", required=True, help="seat to launch as the recovery agent")
    ap.add_argument("--coord", required=True, help="absolute path to coord.py")
    ap.add_argument("--cwd", default=None, help="cwd for the created session (default: package)")
    ap.add_argument("--tmux-socket", default=None,
                    help="tmux -L socket; omit for the default socket the room uses")
    ap.add_argument("--boot-wait", type=float, default=60,
                    help="seconds to wait for the seat's harness to appear (default 60)")
    ap.add_argument("--dry-run", action="store_true", help="report the plan; change nothing")
    args = ap.parse_args()

    sock = args.tmux_socket
    cwd = args.cwd or args.package

    # ---- 1 · the session, created if absent -------------------------------
    if session_exists(args.session, sock):
        pane = first_pane_of(args.session, sock)
        if not pane:
            log(f"FATAL — session '{args.session}' exists but exposes no pane. Refusing rather "
                f"than launching into an unresolvable target.")
            return 2
        log(f"session '{args.session}' already exists; explicit target {pane}")
    else:
        if args.dry_run:
            log(f"DRY-RUN — would create session '{args.session}' (cwd {cwd}) and launch "
                f"'{args.seat}' into it with COORD_LAUNCH_TARGET set explicitly.")
            return 0
        r = tmux("new-session", "-d", "-s", args.session, "-c", cwd,
                 "-P", "-F", "#{pane_id}", socket=sock)
        if r.returncode != 0 or not r.stdout.strip():
            log(f"FATAL — could not create session '{args.session}': "
                f"{(r.stderr or r.stdout).strip()}")
            return 1
        pane = r.stdout.strip()
        log(f"CREATED session '{args.session}', explicit target {pane}")

    # ---- 2 · the target is PROVEN to be the room, never assumed -----------
    # This is the guard for the dangerous half: with COORD_LAUNCH_TARGET and TMUX_PANE both
    # unset, tmux resolves an empty target to the most-recent session. We never let it choose,
    # and we re-read the pane's session to prove the one we hand over is the one we meant.
    actual = session_of(pane, sock)
    if actual != args.session:
        log(f"FATAL — target {pane} resolves to session '{actual}', not '{args.session}'. "
            f"REFUSING to launch: a recovery that opens agents into the wrong room is worse "
            f"than no recovery.")
        return 1
    log(f"target verified: {pane} is in session '{actual}'")

    if args.dry_run:
        log(f"DRY-RUN — would launch '{args.seat}' with COORD_LAUNCH_TARGET={pane}")
        return 0

    # ---- 3 · launch, with the target handed over EXPLICITLY ---------------
    env = dict(os.environ)
    env["COORD_LAUNCH_TARGET"] = pane
    env.pop("TMUX_PANE", None)   # never let a stale pane win over the one we just proved
    cmd = [sys.executable, args.coord, "--package", args.package,
           "launch", "--only", args.seat, "--force"]
    log(f"launching: COORD_LAUNCH_TARGET={pane} {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        log("LAUNCH TIMED OUT — next period retries.")
        return 1
    for line in (res.stdout or "").strip().splitlines()[-15:]:
        log(f"  launch| {line}")
    for line in (res.stderr or "").strip().splitlines()[-10:]:
        log(f"  launch! {line}")

    # ---- 4 · 'launched' is not 'running' (G-11) — verify BY PID -----------
    deadline = time.time() + args.boot_wait
    while time.time() < deadline:
        for p in panes_of(args.session, sock):
            kids = harness_pids(p, sock)
            if kids:
                log(f"RECOVERED — session '{args.session}' is up and a harness is RUNNING in "
                    f"{p}: " + "; ".join(f"pid {pid} {argv}" for pid, argv in kids))
                return 0
        time.sleep(2)

    log(f"ROOM IS UP BUT NO HARNESS BOOTED in '{args.session}' after {args.boot_wait}s "
        f"(launch exit {res.returncode}) — reporting FAILURE, because a room with no agent in "
        f"it is not a recovered run. Next period retries.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
