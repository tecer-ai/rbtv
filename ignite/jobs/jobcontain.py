"""Self-containment for `fire-tool` job scripts (issues.md G-30).

WHY THIS EXISTS. A `fire-tool` exec is UNSANDBOXED AND UNCAPPED: `runToolLikeExec`
(ticker.js) builds its carrier request with literal `caps: {}` and `sandbox: {}`, and
ticker.js never calls `buildBwrapArgv` at all. So a tool script gets no bwrap mount
namespace and no MemoryMax / TasksMax / RuntimeMaxSec — none of the containment a seat
gets from task 7.30. For PERIODIC jobs that run RECOVERY actions on a box that has
started swapping, "bounded by nothing" is the wrong shape. Containment therefore lives
inside the script, because nothing outside it provides any.
(Finding: spawn-integrator, 2026-07-27, seats/spawn-integrator/tools-block-spec.md §3.)

THE TRAP THIS MODULE EXISTS TO AVOID. `RLIMIT_AS` is INHERITED by children. A detector
that caps itself at 256 MB and then execs `coordinate launch` (which starts a claude
harness) or `watch.py` would silently hand that cap to the very process it is trying to
resurrect — a self-heal job that guarantees its own recovery dies. So the cap is applied
to SELF only, and `child_preexec()` restores the ORIGINAL limits inside every child
before its exec.

NOT capped here, deliberately: RLIMIT_NPROC. It counts processes per UID, not per
process tree, so a low value would refuse spawns for every other process this user owns,
including the run's own seats. A fork bomb in a detector is a smaller risk than a
detector that locks the box's own user out of forking.
"""

import fcntl
import hashlib
import os
import resource
import shutil
import signal
import sys

_ORIGINAL_LIMITS = {}


class _Timeout(Exception):
    pass


def _on_alarm(signum, frame):
    sys.stderr.write("jobcontain: WALL-CLOCK BUDGET EXHAUSTED — exiting non-zero so the "
                     "next period retries rather than this run lingering.\n")
    sys.stderr.flush()
    os._exit(3)


def contain(mem_mb=256, seconds=600):
    """Cap THIS process's address space and wall clock. Children are exempted."""
    for key in (resource.RLIMIT_AS, resource.RLIMIT_CPU):
        _ORIGINAL_LIMITS[key] = resource.getrlimit(key)
    soft, hard = _ORIGINAL_LIMITS[resource.RLIMIT_AS]
    want = mem_mb * 1024 * 1024
    if hard == resource.RLIM_INFINITY or want < hard:
        resource.setrlimit(resource.RLIMIT_AS, (want, hard))
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(seconds)


def child_preexec():
    """preexec_fn for every child: restore the pre-`contain()` limits and clear the alarm.

    Without this the child inherits the detector's cap — see the module docstring."""
    for key, (soft, hard) in _ORIGINAL_LIMITS.items():
        try:
            resource.setrlimit(key, (soft, hard))
        except (ValueError, OSError):
            pass
    signal.alarm(0)


def detach_argv(argv, unit, daemonizes=False):
    """Wrap `argv` so the process it starts OUTLIVES this job's exec.

    OBSERVED, not theorised (2026-07-27 05:15, evidence C2-daemon-staged-failure.txt): the
    daemon fires a `fire-tool` exec as a transient unit (`systemd-run --user --unit
    rbtv-worker-…`). A detector that relaunched `watch.py` with `Popen(start_new_session=True)`
    reported RELAUNCHED with a real pid — and the process was GONE moments later, because the
    child stayed inside the job's own cgroup and went down with it. From a shell the same code
    survives, which is exactly why this only shows up when the job is run end to end.

    So anything that must outlive the job gets its OWN transient unit. Two things come free:
    the child is outside the job's cgroup by construction, and `--unit=<name>` REFUSES when a
    unit of that name is already active — a second, systemd-enforced double-start guard under
    the script's own.

    `daemonizes=True` is for a command that FORKS ITS DURABLE PROCESS AND EXITS — `tmux
    new-session -d` being the case here. Without it the unit's main process exits, the unit
    stops, and the default KillMode=control-group reaps the daemonized server with it. That
    failure is INVISIBLE whenever a tmux server already happens to be running, because the
    command then merely asks the existing server for a session and nothing needs to survive
    — which is why every probe passed until one was run against a box with NO tmux server at
    all: the exact state a dead-room job exists for (evidence C1-deadserver.txt, 2026-07-27
    05:22 — plain unit: "no server running"; KillMode=process: session alive).

    Falls back to the bare argv when systemd-run is unavailable, so a shell run still works."""
    if not shutil.which("systemd-run"):
        return list(argv), None
    props = ["--property=KillMode=process"] if daemonizes else []
    return ["systemd-run", "--user", "--collect", "--quiet", *props, f"--unit={unit}", *argv], unit


def unit_name(prefix, key):
    """A stable, valid transient-unit name for a target (same target => same unit)."""
    digest = hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def single_instance(lock_path):
    """Refuse to run when another instance of this job already holds the lock.

    A periodic job whose period is shorter than a slow recovery would otherwise stack
    instances — each firing its own recovery at a target the previous one is still
    repairing. Returns the held file object (keep it referenced) or None when locked.
    The lock is released by process exit; a killed instance never leaves a stale lock."""
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    fh = open(lock_path, "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    fh.write(f"{os.getpid()}\n")
    fh.flush()
    return fh
