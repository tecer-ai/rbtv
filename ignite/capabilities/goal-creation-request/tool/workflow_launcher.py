#!/usr/bin/env python3
"""Open a run's own detached tmux room and launch its entry seat into it (task C5E).

This is the program the `workflows: planning:` entry of `config/spawn-profiles.yaml` execs when the
queue row `scaffold-and-queue` planted at goal birth comes due. It is the LAST dark piece between
the certified per-row argv templating (`server/heart/argv-template.js`) and a master-created goal
that plans itself.

WHY IT EXISTS AT ALL, in one sentence: `coordinate launch` cannot open a room, and a daemon-fired
exec has no room to be in.

  · `coordinate launch` contains ZERO `new-session` calls — it opens a WINDOW in an EXISTING
    session. At the moment this fires, the goal is minutes old and no session exists.
  · It resolves its target as `COORD_LAUNCH_TARGET or TMUX_PANE`, and the daemon exports NEITHER
    (measured: `systemctl --user show rbtv-ignite -p Environment` sets no TMUX*/COORD* variable —
    `evidence/c5e/c5e-01-premise-probes.txt` P6). With both unset tmux resolves an empty target to
    the MOST RECENT session, which is how a stray launch reaches a live room. coord.py refuses
    rather than guessing, and `--tmux-target` exists precisely for "a daemon-fired exec, which has
    neither".

Owner ruling `d-owner-planning-entry-2-0808` (Q2) settles the shape: a PER-RUN DETACHED session
whose name derives from the GOAL — the only identifier derivable from the goal itself, so nothing
short-lived is baked into boot config (the hazard `catalogue-paths.js` exists to catch). The two
rejected alternatives are recorded there: a fixed boot-time room is always-on infrastructure to
provision, and letting a pane id ride the queue row would widen the certified templating key set
with a new byte class on an exec'd command line.

⚠ THIS FILE CREATES A TMUX SESSION AND THAT IS RULED, NOT BESPOKE. Its sibling
`goal_creation_request.py` is held to "no bespoke spawn construct" by
`probes/probe-goal-creation-request.py` check 3, and rightly: the CREATE path must invoke the ruled
name `scaffold-seats` and never hand-roll seat materialization. This is a different act — it
materializes no seat and boots no harness itself; it opens a room and hands the launch to the run's
own coordination CLI, which stays the only writer of a session row. It is a separate file so that
check keeps meaning what it says instead of being widened to admit the construct it exists to catch.

⚠ IT PASSES `--force` AND NOT `--force-memory`, and the split is load-bearing. `--force` carries
the ROLE gate: a daemon-fired exec has no pane and therefore no seat identity, so it can pass no
identity-keyed gate however it is invoked. `--force-memory` carries the MEMORY gate and is NOT
passed: this is a NEW launch, exactly what that floor is sized for. `jobs/recover-room.py` does pass
it, correctly and for a reason that is FALSE here — a recovery replaces a seat that already died, so
it is load-neutral; a fresh planning wave is not. Reusing that program as this launcher was
considered and rejected for precisely that: it would arm an unattended memory override on every
auto-created goal while disclosing a reason that does not hold, which is G-41 (a different mechanism
wearing the same name) one level over.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# The composed session name's grammar. Both inputs are kebab-validated upstream — `GOAL_NAME_RE` at
# the request inbox and `argv-template.js`'s `nameRule` at BOTH enqueue and fire — but this program
# is argv-driven and re-checks rather than trusting: a `.` or a `:` in a session name is a tmux
# SEPARATOR, not a character, so an unchecked name would address a window or a pane instead of a
# session. Anchored whole-string, so a name that needed sanitizing is refused rather than sanitized.
SESSION_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_SESSION_NAME = 100


def log(msg):
    print(f"workflow-launcher: {msg}", flush=True)


def tmux(*args, socket=None):
    exe = shutil.which("tmux")
    if not exe:
        return None
    cmd = [exe] + (["-L", socket] if socket else []) + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def session_name(goal, package):
    """`<goal>-<run-id>`, or raise ValueError with the reason.

    PER-RUN and DERIVED FROM THE GOAL, which is what the ruling asks for and what makes the name
    collision-safe without a registry: goal names are unique within the goals root (the request
    validator's V2/V3 uniqueness checks) and a run id is unique within its goal, so the pair is
    unique by construction. The run id is the package's own last segment — read from the path the
    row carries rather than passed separately, because two carriers of one fact is two chances for
    them to disagree.
    """
    run_id = Path(package).name
    name = f"{goal}-{run_id}"
    if len(name) > MAX_SESSION_NAME:
        raise ValueError(f"composed session name is {len(name)} chars, over the {MAX_SESSION_NAME} cap: {name!r}")
    if not SESSION_NAME_RE.match(name):
        raise ValueError(
            f"composed session name {name!r} is not lowercase kebab-case. Refusing rather than "
            f"sanitizing: a '.' or ':' is a tmux SEPARATOR, so a name carrying one addresses a "
            f"window or a pane instead of a session")
    return name


def ensure_session(name, cwd, socket=None):
    """(pane_id, provenance) for a session guaranteed to exist, or raise RuntimeError.

    IDEMPOTENT BY DESIGN: a re-fire of the same row must join the room it already opened, never
    open a second one. `=NAME` forces an EXACT match — without it tmux matches by PREFIX, so a goal
    named `foo` would resolve the unrelated room of a goal named `foo-bar`.

    THE TARGET IS RE-READ AND PROVEN, never assumed: the pane's own session is asked back and must
    equal the one asked for. This is the guard for the dangerous half — with COORD_LAUNCH_TARGET and
    TMUX_PANE both unset tmux resolves an empty target to the most recent session — and it is the
    same proof `jobs/recover-room.py` performs for the same reason.
    """
    if tmux("-V", socket=socket) is None:
        raise RuntimeError(
            "tmux is not on PATH. REFUSING: a launcher whose whole job is to name an explicit "
            "target must not proceed without the tool that resolves one")

    exists = tmux("has-session", "-t", f"={name}", socket=socket).returncode == 0
    if exists:
        r = tmux("list-panes", "-s", "-t", f"={name}", "-F", "#{pane_id}", socket=socket)
        panes = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()] if r.returncode == 0 else []
        if not panes:
            raise RuntimeError(f"session {name!r} exists but exposes no pane — refusing rather than "
                               f"launching into an unresolvable target")
        pane, provenance = panes[0], "existing session (re-fire joins the room it already opened)"
    else:
        r = tmux("new-session", "-d", "-s", name, "-c", cwd, "-P", "-F", "#{pane_id}", socket=socket)
        if r.returncode != 0 or not r.stdout.strip():
            raise RuntimeError(f"could not create session {name!r}: {(r.stderr or r.stdout).strip()}")
        pane, provenance = r.stdout.strip(), f"CREATED detached (cwd {cwd})"

    back = tmux("display-message", "-p", "-t", pane, "#{session_name}", socket=socket)
    actual = back.stdout.strip() if back.returncode == 0 else ""
    if actual != name:
        raise RuntimeError(f"target {pane} resolves to session {actual!r}, not {name!r} — REFUSING: "
                           f"a launch that opens agents into the wrong room is worse than none")
    return pane, provenance


def launch_argv(coord, package, entry_seat, pane):
    """The EXACT argv the launch delegates to. Built above every early return so --dry-run prints
    the real thing.

    ⚠ THE COORD PATH IS NAMED, NOT RESOLVED ON PATH. A fire-tool/start-workflow exec inherits the
    systemd --user manager's PATH, which does NOT carry `~/.local/bin` — the same reason every other
    daemon-fired entry in spawn-profiles.yaml names `--coord`/`--ignite-bin` as a REPO FILE rather
    than a symlink. `coordinate` as a bare name resolves interactively and not here.
    """
    return [sys.executable, str(coord), "--package", str(package),
            "launch", "--only", entry_seat, "--tmux-target", pane, "--force"]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Open a run's own detached tmux room and launch its entry seat into it.")
    ap.add_argument("--package", required=True,
                    help="absolute run-package path (runs/run-N) — the row's {{workdir}}")
    ap.add_argument("--goal", required=True,
                    help="the goal NAME the session name derives from — the row's {{goal}}")
    ap.add_argument("--entry-seat", required=True,
                    help="the seat launched first — the row's {{entry-seat}}")
    ap.add_argument("--coord", required=True, help="absolute path to the run's coord.py")
    ap.add_argument("--tmux-socket", default=None,
                    help="tmux -L socket; omit for the default socket a room uses. Exists so a "
                         "probe can exercise this path without touching the socket live rooms are on")
    ap.add_argument("--dry-run", action="store_true",
                    help="report the plan and the exact delegated argv; create nothing, open nothing")
    args = ap.parse_args(argv)

    package = Path(args.package)
    # The package is READ, never created. A launch is not a creation act: `scaffold-and-queue`
    # materialized this package at goal birth, so an absent one means that act failed or the row
    # outlived its package — both are refusals, and creating it here would paper over either.
    if not package.is_dir():
        log(f"FATAL — run package {package} does not resolve to a directory. REFUSING: this act "
            f"launches into a package, it never creates one.")
        return 2
    if not Path(args.coord).is_file():
        log(f"FATAL — coord.py not found at {args.coord}")
        return 2

    try:
        name = session_name(args.goal, package)
    except ValueError as err:
        log(f"FATAL — {err}")
        return 2
    log(f"room for this run: session {name!r} (per-run, derived from goal {args.goal!r} + run "
        f"{package.name!r} — ruling d-owner-planning-entry-2-0808 Q2)")

    if args.dry_run:
        log(f"DRY-RUN — would ensure detached session {name!r} (cwd {package}), resolve its pane "
            f"explicitly, re-read it for ownership, then run the argv below with that pane as "
            f"--tmux-target. Nothing was created.")
        log(f"DRY-RUN argv: {' '.join(launch_argv(args.coord, package, args.entry_seat, '%<pane>'))}")
        return 0

    try:
        pane, provenance = ensure_session(name, str(package), args.tmux_socket)
    except RuntimeError as err:
        log(f"FATAL — {err}")
        return 1
    log(f"target {pane} verified in session {name!r} — {provenance}")

    env = dict(os.environ)
    env.pop("TMUX_PANE", None)      # never let an inherited pane win over the one just proven
    env.pop("COORD_LAUNCH_TARGET", None)
    cmd = launch_argv(args.coord, package, args.entry_seat, pane)
    log("launching: " + " ".join(cmd))
    log("--force is passed for the ROLE gate only (a daemon-fired exec has no seat identity); "
        "--force-memory is deliberately NOT passed — this is a new launch and the memory floor binds")
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        log("LAUNCH TIMED OUT after 300s.")
        return 1
    for line in (res.stdout or "").strip().splitlines()[-20:]:
        log(f"  launch| {line}")
    for line in (res.stderr or "").strip().splitlines()[-10:]:
        log(f"  launch! {line}")
    if res.returncode != 0:
        log(f"launch exited {res.returncode}")
        return res.returncode

    # ⚠ EXIT 0 IS NOT 'A SEAT OPENED', AND THE DIFFERENCE IS MEASURED. A freshly materialized run
    # package has no `state.json`, so the capacity census is UNENFORCEABLE and `launch` admits no
    # seat — "this is a WAIT, not a refusal — the act exits ZERO", every candidate deferred to the
    # pickup lane until the team-monitor sensor produces a census (evidence/c5e/c5e-01 P7). So on a
    # brand-new package the FIRST fire legitimately opens nothing and still exits 0. That is stated
    # loudly here rather than left to be discovered from an empty room: whoever arms goal-creation
    # needs the census sensor in the arming sequence.
    r = tmux("list-panes", "-s", "-t", f"={name}", "-F", "#{pane_id}", socket=args.tmux_socket)
    panes = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()] if r and r.returncode == 0 else []
    if len(panes) <= 1:
        log(f"WAIT — launch exited 0 but session {name!r} holds {len(panes)} pane(s), i.e. no seat "
            f"opened. On a fresh package this is the EXPECTED first-fire outcome: with no "
            f"state.json the capacity census is unenforceable and every candidate defers to the "
            f"pickup lane. The room is up and the seats arrive once a census exists.")
    else:
        log(f"LAUNCHED — session {name!r} holds {len(panes)} panes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
