#!/usr/bin/env python3
"""Open a goal's own detached tmux room and launch its entry seat into it (task C5E).

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

⚠ IT PASSES NEITHER `--force` NOR `--force-memory`, and each absence is its own claim.

`--force` (the ROLE gate) WAS passed unconditionally, on the premise that "a daemon-fired exec has
no pane and therefore no seat identity, so it can pass no identity-keyed gate however it is
invoked". That premise is FALSE against the tree: `coord.py`'s F16 lane resolves a daemon-fired
exec's identity from KERNEL MEASURABLES (`daemon_exec_identity` → `DAEMON_IDENTITY`), so this call
does arrive with an identity — it simply held no grant. Owner ruling, task 7.738 (2026-08-11):
`is_authorized_launcher` now names `DAEMON_IDENTITY`, and the flag is DROPPED here. What it bought
was never an override; it was compliance with a standing act spelled as one, which is the exact
defect G-257 filed one layer over — and it made every unattended launch print
`role gate: REFUSED, overridden with --force` / `WARNING launching anyway`, so a real override and a
routine fire were indistinguishable in the log. A launch that now refuses on the role gate is a
REAL refusal: the daemon's identity did not resolve, and that must surface rather than be forced
through.

`--force-memory` (the MEMORY gate) is still NOT passed, unchanged and for the original reason: this
is a NEW launch, exactly what that floor is sized for. `jobs/recover-room.py` does pass it,
correctly and for a reason that is FALSE here — a recovery replaces a seat that already died, so it
is load-neutral; a fresh planning wave is not. Reusing that program as this launcher was considered
and rejected for precisely that: it would arm an unattended memory override on every auto-created
goal while disclosing a reason that does not hold, which is G-41 (a different mechanism wearing the
same name) one level over.
"""

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# The sole consumer of the edge fast path's arming file, and therefore the sole reader of it.
# `capabilities/<name>/tool/` → `capabilities/<name>/` → `capabilities/` → `ignite/`.
EDGE_RUNNER_PATH = Path(__file__).resolve().parents[3] / "jobs" / "edge-runner-job.py"

# The composed session name's grammar. Both inputs are kebab-validated upstream — `GOAL_NAME_RE` at
# the request inbox and `argv-template.js`'s `nameRule` at BOTH enqueue and fire — but this program
# is argv-driven and re-checks rather than trusting: a `.` or a `:` in a session name is a tmux
# SEPARATOR, not a character, so an unchecked name would address a window or a pane instead of a
# session. Anchored whole-string, so a name that needed sanitizing is refused rather than sanitized.
SESSION_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_SESSION_NAME = 100

# ⚠ THIS PROGRAM'S EXIT CODE **IS** THE STORE RECORD, so 0 is spent on exactly one claim.
# `recordToolCompletion` (server/ticker/ticker.js) maps a fired tool's exit 0 -> completion `done`
# and every non-zero -> `failed`, against a CLOSED enum with no third word. So an exit 0 that did
# not open a seat writes `done` on a fire that achieved nothing — the false success this code
# previously produced by construction (C5E-review C1). 0 now means "this fire opened at least one
# seat pane" and nothing else.
#
# 3 is its own code rather than a reuse of 1: 1 and 2 are already spent on a REFUSAL (bad inputs, an
# unresolvable target, a delegated launch that itself failed), and a launch that ran correctly and
# admitted nobody is a different fact. The store keeps `exit_code`, so the two stay tellable apart
# in the record and not only in the log.
EXIT_NO_SEAT = 3


def log(msg):
    print(f"workflow-launcher: {msg}", flush=True)


def tmux(*args, socket=None):
    exe = shutil.which("tmux")
    if not exe:
        return None
    cmd = [exe] + (["-L", socket] if socket else []) + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def session_name(goal, package=None):
    """The BARE GOAL NAME, or raise ValueError with the reason.

    7.607 E2b, `decisions.md#d-extinguishment-design-lock` item 2 (D4): ONE ROOM PER GOAL, named
    for the goal, and a second concurrent execution is REFUSED — the room's existence IS the
    lease's primary evidence (item 1). The old `<goal>-<run-id>` spelling died with the run layer:
    it made the room name carry a compartment id that no longer exists, and a per-execution room
    would have made the lease's "is this goal executing" question ambiguous by construction.

    Collision-safety is UNCHANGED in strength and simpler in argument: goal names are unique within
    the goals root (the request validator's V2/V3 uniqueness checks), so the goal name alone is
    unique. `package` is accepted and IGNORED — kept only so an unmigrated caller passing it does
    not TypeError while the rest of the tree re-keys; it contributes nothing to the name.
    """
    name = str(goal)
    if len(name) > MAX_SESSION_NAME:
        raise ValueError(f"composed session name is {len(name)} chars, over the {MAX_SESSION_NAME} cap: {name!r}")
    if not SESSION_NAME_RE.match(name):
        raise ValueError(
            f"composed session name {name!r} is not lowercase kebab-case. Refusing rather than "
            f"sanitizing: a '.' or ':' is a tmux SEPARATOR, so a name carrying one addresses a "
            f"window or a pane instead of a session")
    return name


def mint_execution(coord, package):
    """Mint this BOOT's dated execution stamp through coord.py — the ONE home of the rule
    (7.607 E2b, `d-extinguishment-design-lock` item 5). Returns the stamp, or '' on any failure.

    ⚠ CALLED ONLY WHERE THE ROOM WAS *CREATED*, never where it was joined. That is what keeps a
    re-fire of the same row idempotent: joining an existing room must not invent a second execution
    of it. `ensure_session` already distinguishes the two arms and reports which — this reads that
    verdict rather than re-deriving it.

    ⚠ BEST-EFFORT, and deliberately so: a stamp is a DELIMITER, not a gate. The launch's job is to
    open the room; failing to record a delimiter must not stop agents from booting into it. A
    failure is REPORTED (the caller logs it), never swallowed silently and never fatal — an absent
    marker is read by `coord.current_execution` as today's first execution, which is the right
    reading for a boot whose mint did not land."""
    r = subprocess.run([sys.executable, str(coord), "--package", str(package),
                        "execution", "--mint"],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.splitlines()[0].strip() if r.returncode == 0 and r.stdout.strip() else ""


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


def panes_in(name, socket=None):
    """The SET of pane ids in session `name`, or None if the room could not be read.

    ⚠ None IS NOT AN EMPTY ROOM, and the caller must never collapse them: "no pane is open" is a
    measurement, "I could not look" is the absence of one. They travel to the same exit code here
    (an unproven launch may not record a success either) but they carry different reasons, and a
    predicate that returned an empty set on a failed read would report a room it never saw.
    """
    r = tmux("list-panes", "-s", "-t", f"={name}", "-F", "#{pane_id}", socket=socket)
    if r is None or r.returncode != 0:
        return None
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


# `coordinate launch`'s own per-seat success line — `launched <seat> (<harness>/<model>, <place>) in
# %N`, printed once per seat that came up (team-kit/coord.py, `cmd_launch`'s launch loop). It is
# the ONLY per-fire identity that exists: see `panes_launched`.
LAUNCHED_PANE_RE = re.compile(r"^launched .* in (%\d+)\b")


def panes_launched(stdout):
    """The pane ids THIS FIRE's delegated launch reported opening, in the order it named them.

    ⚠ PER-FIRE IDENTITY, NOT A ROOM-WIDE DELTA, and the difference is the whole point (task 7.588).
    The room is SHARED BY CONSTRUCTION — `ensure_session` is idempotent by design, so every fire
    into a run joins the ONE session — and a before/after set difference over that room attributes
    whatever appeared in the window to whichever fire happened to look last. Two fires racing into
    one room therefore mis-attribute in BOTH directions: a fire that opened NOTHING finds the
    neighbour's pane in its delta and exits 0 (the store writes `done` for a fire that achieved
    nothing — exactly the false success EXIT_NO_SEAT was minted to make impossible), and a fire
    that opened one claims the neighbour's as well. The launch itself already knows the answer: it
    names the pane it opened for each seat, so nothing has to be inferred from the room's history.

    A parse rather than a flag because the line is coord's EXISTING contract with every caller —
    adding a second, machine-readable carrier of the same fact is two carriers to disagree. The
    coupling is pinned by `probes/probe-launcher-attribution.py` arm D, which fails if that line
    is renamed; without it a rename would silently downgrade every real launch to a WAIT.
    """
    return [m.group(1) for m in
            (LAUNCHED_PANE_RE.match(ln.strip()) for ln in (stdout or "").splitlines()) if m]


def report_arming(package):
    """Say whether this package's EDGE FAST PATH is armed. Returns nothing; never raises, never exits.

    ⚠ DOORS 2 AND 3 OF TASK 7.736 (owner ruling 2026-08-11: warn at all three doors, exit stays 0).
    Arming is the presence of `coordination/edge-fastpath.json` and nothing else. Its sole consumer
    — `jobs/edge-runner-job.py` — reads it at CHECK-OUT time and is DELIBERATELY SILENT when
    unarmed, which is correct there and was total everywhere else: a goal could be created,
    launched, run, and check a seat out with the advance hook disarmed, and no surface on the launch
    path ever said so. The run simply stopped advancing and looked like a stall. This is the
    launcher's half of the fix — it SAYS so, on the dry-run path and the live path alike, because a
    dry-run exists to show what a real launch would do.

    THE PREDICATE IS IMPORTED, NEVER REIMPLEMENTED (PRIN-11), by the same `spec_from_file_location`
    idiom `jobs/goal-state-job.py` uses on the same file for the same reason: `fastpath_arm` is THE
    one reader of that file, and a second reader here would be free to disagree with the CONSUMER
    about which packages are armed — and a disagreement about arming is the very failure this
    reporting exists to surface.

    ⚠ IT NEVER TOUCHES THE EXIT CODE. This program's exit is spent on exactly one claim ("this fire
    opened at least one seat pane", see EXIT_NO_SEAT above), and an unarmed package still opens its
    seats perfectly well — failing the launch over arming would convert a warning into an outage and
    would write `failed` on a fire that did its whole job. The signal a downstream monitor greps is
    the stable token `EDGE-FASTPATH-NOT-ARMED` in this log, never a code.
    """
    try:
        spec = importlib.util.spec_from_file_location("edge_runner_job", EDGE_RUNNER_PATH)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["edge_runner_job"] = mod
        spec.loader.exec_module(mod)
        arm, scope = mod.fastpath_arm(package)
    except Exception as err:
        # BROAD ON PURPOSE, and this is the only place this file catches everything: importing
        # executes a whole sibling module's body, and the ARMING REPORT must never be the thing that
        # breaks a launch. UNKNOWN is printed LOUDLY and is never collapsed into either verdict —
        # "I could not look" is not "not armed", and it is emphatically not "armed".
        log(f"EDGE-FASTPATH-UNKNOWN — could not read this package's arming state through "
            f"{EDGE_RUNNER_PATH} ({type(err).__name__}: {err}). NOT FATAL, and NOT A VERDICT: the "
            f"launch proceeds and its exit code is unaffected, but nothing here says whether the "
            f"check-out advance hook is armed for this goal. Read that file before trusting the run "
            f"to advance itself.")
        return
    if arm:
        log(f"edge fast path: {scope}")
        return
    log(f"EDGE-FASTPATH-NOT-ARMED — {scope}")
    log(f"EDGE-FASTPATH-NOT-ARMED — CONSEQUENCE: seats in this goal will check out and the DAG will "
        f"NOT advance on its own; every edge past a finished seat waits for a hand act. This does "
        f"NOT change this launch's exit code — the room still opens and the entry seat still runs. "
        f"Arm the package by writing {package}/coordination/edge-fastpath.json (`job-id` and "
        f"`profile` are both required) if this run is meant to advance itself.")


def launch_argv(coord, package, entry_seat, pane):
    """The EXACT argv the launch delegates to. Built above every early return so --dry-run prints
    the real thing.

    ⚠ THE COORD PATH IS NAMED, NOT RESOLVED ON PATH. A fire-tool/start-workflow exec inherits the
    systemd --user manager's PATH, which does NOT carry `~/.local/bin` — the same reason every other
    daemon-fired entry in spawn-profiles.yaml names `--coord`/`--ignite-bin` as a REPO FILE rather
    than a symlink. `coordinate` as a bare name resolves interactively and not here.
    """
    return [sys.executable, str(coord), "--package", str(package),
            "launch", "--only", entry_seat, "--tmux-target", pane]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Open a goal's own detached tmux room and launch its entry seat into it.")
    ap.add_argument("--package", required=True,
                    help="absolute GOAL-folder path (the package IS the goal folder, "
                         "design-lock item 8) — the row's {{workdir}}")
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
        log(f"FATAL — goal package {package} does not resolve to a directory. REFUSING: this act "
            f"launches into a package, it never creates one.")
        return 2
    if not Path(args.coord).is_file():
        log(f"FATAL — coord.py not found at {args.coord}")
        return 2

    # DOORS 2 AND 3 (7.736). Placed after the two REFUSALS and before everything else, so it runs on
    # the dry-run path and the live path alike and cannot be reached by a launch that was going to
    # refuse anyway. Nothing below it reads its result — it reports, and that is all it does.
    report_arming(package)

    try:
        name = session_name(args.goal, package)
    except ValueError as err:
        log(f"FATAL — {err}")
        return 2
    log(f"room for this goal: session {name!r} (ONE room per goal, the bare goal name — "
        f"design-lock item 2; ruling d-owner-planning-entry-2-0808 Q2 re-founded on it)")

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

    # THE BOOT'S ONE ACT (7.607 E2b, design-lock item 5): a CREATED room is a new execution of this
    # goal, so it mints the dated stamp every session row, message header and watcher-state entry
    # written from here on will carry. A JOINED room is the SAME execution and mints nothing —
    # which is what keeps a re-fired row idempotent.
    if provenance.startswith("CREATED"):
        stamp = mint_execution(args.coord, package)
        log(f"execution stamp: {stamp or 'MINT FAILED'} — the delimiter this boot's rows carry "
            f"(design-lock item 5; the goal's files stay single and append-only)"
            + ("" if stamp else ". NOT FATAL: an absent marker reads as today's first execution, "
                              "and a delimiter must never gate a launch"))
    else:
        log("execution stamp: UNCHANGED — this re-fire JOINED the room it already opened, so it "
            "is the same execution and mints nothing")

    env = dict(os.environ)
    env.pop("TMUX_PANE", None)      # never let an inherited pane win over the one just proven
    env.pop("COORD_LAUNCH_TARGET", None)
    cmd = launch_argv(args.coord, package, args.entry_seat, pane)
    log("launching: " + " ".join(cmd))
    log("no gate flag is passed: the ROLE gate admits the daemon on its own identity since 7.738 "
        "(`is_authorized_launcher` names DAEMON_IDENTITY), so `--force` is gone and a role refusal "
        "here is a REAL one; --force-memory stays deliberately NOT passed — this is a new launch "
        "and the memory floor binds")
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

    # ⚠ EXIT 0 MEANS "A SEAT OPENED", AND THIS IS WHERE THAT IS PROVEN — from the pane THIS FIRE'S
    # OWN LAUNCH REPORTED, re-read in the room to prove it is really there. It used to be proven
    # from a before/after delta over the WHOLE room, which is not concurrency-safe: `panes_launched`
    # above carries the reason in full (task 7.588). The room read stays, in a narrower role — it
    # answers "is the pane this fire opened actually in this room, right now", never "what changed
    # in this room" — so an unreadable room is still an UNPROVEN launch and still refuses to record
    # a success. A count is not the proof either way: a re-fire joins a room it already populated
    # (`ensure_session` is idempotent by design), and a count-based test would report that re-fire
    # as a fresh success while it opened nothing.
    #
    # Two measured facts decide the rest of the shape, and both correct what this file used to say:
    #
    #  · A VIRGIN PACKAGE'S FIRST FIRE DOES OPEN ITS ENTRY SEAT. `coordinate launch` carries a
    #    COLD-START admission (team-kit task 7.406): a package no sensor has ever run against and no
    #    seat has ever launched into is recognised on its own markers and admitted on the EMPTY-ROOM
    #    BOUND (in_use 0), because a room nothing has ever touched has an accurate census of itself.
    #    The claim this comment used to carry — the first fire opens nothing, exits 0, and whoever
    #    arms goal-creation must put the census sensor in the arming sequence — was read off 7.363's
    #    census-FAILURE branch and is FALSE against the tree. Measured end to end, the entry seat's
    #    pane opens on the first fire (`probes/probe-planning-entry.py` P5).
    #  · NO ARMING SEQUENCE COULD HAVE CARRIED THAT SENSOR ANYWAY. `team_monitor.py` resolves the
    #    room's session FROM THE ROSTER and refuses while no seat has checked in ("the roster
    #    carries no pane at all", exit 4) — it cannot run before the first launch, by construction.
    #    Cold-start admission exists precisely because a virgin room's census is unobtainable and
    #    its true reading is nonetheless known.
    #  · WHAT THE LAUNCH ITSELF NOW CARRIES (team-kit task 7.552). `coordinate launch` hands
    #    `team_monitor.py ensure` the room's session it just launched into, so the sensor STARTS
    #    with the first seat rather than refusing on an empty roster. That is what makes a SECOND
    #    fire possible at all: the cold-start bound is spent ONCE, so before 7.552 every fire after
    #    the first hit the WAIT below — and Wave D's advancement launch is exactly that second fire.
    #    `probes/probe-sensor-start.py` pins the chain end to end.
    #
    # So a WAIT here is NOT the expected first-fire outcome. It is a package that is no longer
    # virgin and has no census — its sensor died — which is the state 7.363 defers on. That is a
    # real outcome, and it is now recorded as a FAILED completion rather than a false `done`.
    #
    # ⚠ WHY `failed` DOES NOT MINT THE FAILURE-PER-CADENCE PATTERN, which is the other way this
    # could have gone wrong: the queue row this program runs under is ONE-SHOT. It is enqueued
    # `--trigger scheduled --at <t>` with no repeat rule, and `fireQueueRow` DELETES exactly that
    # row at fire (server/heart/heart-store.js). So there is no cadence for a failure to recur on —
    # one fire, one honest record. `probe-planning-entry.py` P7 pins that, because the day the row
    # becomes periodic this exit code starts writing a `failed` every pass.
    room = panes_in(name, args.tmux_socket)
    reported = panes_launched(res.stdout)
    opened = [p for p in reported if p in room] if room is not None else None
    if opened is None:
        log(f"NO SEAT PROVEN — the delegated launch exited 0 and reported "
            f"{len(reported)} pane(s), but session {name!r}'s panes could not be read, so NOTHING "
            f"here proves a seat opened in this room. Exiting "
            f"{EXIT_NO_SEAT} rather than 0: an unproven launch must not be recorded as a success.")
        return EXIT_NO_SEAT
    if not opened:
        log(f"WAIT — the delegated launch exited 0 and reported NO seat pane of its own in session "
            f"{name!r} ({len(room)} pane(s) in the room, none of them opened by THIS fire — a pane "
            f"this fire did not open is not evidence that it did"
            + (f"; it reported {' '.join(reported)}, which the room does not hold" if reported
               else "") + "). This is a "
            f"WAIT, not a refusal, in `coordinate launch`'s own terms — but it is NOT a success, so "
            f"this program exits {EXIT_NO_SEAT} and the store records `failed` instead of `done`. "
            f"Read the `launch|` lines above for the reason it named; the usual one is a package "
            f"whose team-monitor sensor is down, so its capacity census is unreadable and every "
            f"counted candidate defers. PICKUP LANE: restore the sensor for this package and fire "
            f"again.")
        return EXIT_NO_SEAT
    log(f"LAUNCHED — this fire opened {len(opened)} seat pane(s) in session {name!r}: "
        f"{' '.join(opened)} ({len(room)} pane(s) in the room, the rest not this fire's)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
