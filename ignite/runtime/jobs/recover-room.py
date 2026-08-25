#!/usr/bin/env python3
"""Re-create a dead coordination-kit room and boot a recovery seat into it (task 7.71).

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
from pathlib import Path


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
        # pane ROOT or its child: a harness typed into a shell is a child of pane_pid, but a
        # command tmux was given directly IS pane_pid. A children-only scan is blind to the
        # second shape (measured in selfheal-room.py's own probe, 2026-07-27 05:55).
        if (ppid == root or pid == root) and any(h in argv for h in ("claude", "codex", "opencode")):
            kids.append((pid, argv[:120]))
    return kids


def resolve_package(args):
    """(Path, provenance) or (None, refusal) — the run package the recovery seat is launched into.

    THE TARGET IS RESOLVED, NEVER PINNED. The LIVE `selfheal-room` entry used to carry
    `--package .../runs/run-1` for a run closed 2026-07-27, so a fire would have booted a recovery
    seat into a CLOSED run's package while the job's own status kept reading healthy. Swapping in a
    different run number reproduces that defect at the next run close; the fix is that the live
    entry names NO run at all and asks the register instead (task 7.188 / design M4-49, discharging
    7.106 criterion 3's remainder). This is the same remedy `selfheal-watch.py:resolve_package()`
    already carries for the sensor, deliberately in the same shape — two jobs answering "which run
    is live" two different ways is the defect one level up.

    `--package` SURVIVES AS THE EXPLICIT OVERRIDE and wins whenever it is present. That is not a
    compatibility shim: the THROWAWAY twin (`selfheal-room-throwaway`) must target a scratch
    package and must NEVER resolve live, because a throwaway recovery pointed at the live run opens
    agents into the live room. The twin therefore passes `--package` and NOT `--goal`, so dropping
    its override cannot silently promote it onto the live run — it refuses instead.

    ⚠ THERE IS NO REGISTER ANY MORE, AND THE TARGET IS THE LEASE (7.607 E3, design-lock item 1).
    Liveness is DERIVED at fire time from the goal's tmux room and its ancestry-verified seats,
    never from a stored status. `coord.derive_lease()` is the ONE accessor over the one home
    (`server/lease/lease.js`); a second room predicate here would be the same two-readers defect a
    second `runs.csv` parse was. What this replaces was already BROKEN, not merely dated: it
    composed `<goal>/runs/<name>` from `resolve_live_run`'s compat return, and E2b moved the layout
    out from under that path — the recovery seat would have booted into a directory that is gone.

    `coord` is imported INSIDE this function from the `--coord` path this job already requires, so
    a copy-and-test of this file carries no sibling dependency it does not otherwise need.

    Refusal is FAIL-CLOSED and returns no package, at THREE doors — an unreadable lease
    (ignorance), no room (the goal is not executing, so there is no room to recover), and more than
    one room. A recovery that guessed its target is worse than no recovery, which is this whole
    script's premise."""
    if args.package:
        return Path(args.package).resolve(), "--package (explicit override; the lease is not consulted)"
    if not args.goal:
        return None, ("no --package, so the target must be DERIVED from the goal's live lease — "
                      "but --goal is absent. Lease resolution needs the goal folder.")
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
                      + ("the goal is NOT EXECUTING, so there is no room to recover"
                         if not rooms else
                         "two rooms of one goal is a box state nothing here should resolve"))
    pkg = Path(rooms[0].get("packageDir") or "").resolve()
    return pkg, (f"DERIVED from the live lease of {goal.name}: room {rooms[0].get('room')!r} -> "
                 f"{pkg} (no stored status read; design-lock item 1)")


def launch_argv(args, package):
    """The EXACT argv the recovery executes. Built here, above every early return, so a
    `--dry-run` can print the real thing (G-56).

    coord.py's per-verb ROLE gate is deleted whole [T2-R10, D24, F-simplicity-7]: `launch` no
    longer refuses on WHO is calling, so `--force` carries no authority override here anymore. It
    is still passed because `launch_seat`'s window-drift check and `resolve_agent`'s
    identity-mismatch check both read it directly for unrelated reasons, and both are plausibly in
    the way of an unattended, identity-less daemon-fired exec. `--force-memory` is the one flag
    left that overrides an actual GATE — the memory floor — for the reason below.

    WHY THE MEMORY GATE IS OVERRIDDEN, stated rather than assumed: a RECOVERY launch is
    load-NEUTRAL. It replaces a seat that has already died, so the memory that seat held is
    already back; the gate is sized for a NEW launch, which this is not. Without the flag the
    daemon-fired recovery is REFUSED below the floor (exit 2) — self-healing switches off in
    EXACTLY the low-memory state that kills seats and calls for recovery. Tonight's readings
    touched 2449 / 2757 / 2837 against a 2800 floor. A run whose healing fails precisely when it
    is needed is worse than one with no healing, because the second is honest about it."""
    return [sys.executable, args.coord, "--package", str(package),
            "launch", "--only", args.seat, "--force", "--force-memory"]


def disclose_overrides():
    """RIDER (leader #409): the override is LOGGED with its reason on every firing — and on every
    DRY-RUN too, or the cheap check would be silent about the very thing it should surface."""
    log("OVERRIDING THE MEMORY GATE (--force-memory) — deliberate and load-neutral: this "
        "recovery replaces a seat that already died, so its memory is already returned. The "
        "gate is sized for a NEW launch; a recovery is not one. `--force` is also passed, but "
        "carries no gate anymore [T2-R10, D24, F-simplicity-7] — it only silences the "
        "window-drift and identity-mismatch checks a daemon-fired exec cannot otherwise clear.")


def main():
    ap = argparse.ArgumentParser(
        description="Re-create a dead room and boot a recovery seat into it, explicitly.")
    ap.add_argument("--session", required=True, help="tmux session name that IS the room")
    # ⚠ NO LONGER REQUIRED, AND THE LIVE ENTRY CARRIES NO RUN NUMBER ANY MORE (task 7.188).
    # `--package` is the EXPLICIT OVERRIDE; absent, the target is DERIVED from the goal's live
    # lease at FIRE TIME. See resolve_package() for why the override survives and why the twin
    # needs it.
    ap.add_argument("--package", default=None,
                    help="package the seat belongs to — the EXPLICIT OVERRIDE. Absent: DERIVED "
                         "from the goal's live lease (needs --goal)")
    ap.add_argument("--goal", default=None,
                    help="goal folder whose LIVE LEASE resolves the package when --package is "
                         "absent. Names a GOAL — there is no run number left to go stale")
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

    # ---- 0a · the target, RESOLVED and never pinned (task 7.188) -----------
    # Ahead of the gate check and of any tmux call: a recovery that cannot say which run it is
    # repairing must not create a session first and discover that afterwards.
    package, provenance = resolve_package(args)
    if package is None:
        log(f"FATAL — REFUSING to recover: {provenance}")
        return 2
    log(f"target package {package} — {provenance}")
    cwd = args.cwd or str(package)

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
            log(f"DRY-RUN — would create session '{args.session}' (cwd {cwd}), resolve its pane "
                f"explicitly, re-read it for ownership, then run the argv below with "
                f"COORD_LAUNCH_TARGET set to that pane.")
            disclose_overrides()
            log(f"DRY-RUN argv: {' '.join(launch_argv(args, package))}")
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
        disclose_overrides()
        log(f"DRY-RUN argv: {' '.join(launch_argv(args, package))}")
        return 0

    # ---- 3 · launch, with the target handed over EXPLICITLY ---------------
    env = dict(os.environ)
    env["COORD_LAUNCH_TARGET"] = pane
    env.pop("TMUX_PANE", None)   # never let a stale pane win over the one we just proved
    cmd = launch_argv(args, package)
    disclose_overrides()
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
