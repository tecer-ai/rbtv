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
import subprocess
import sys

_ORIGINAL_LIMITS = {}


class _Timeout(Exception):
    pass


class CarrierEnvMissing(RuntimeError):
    """`detach_argv` was asked to detach a process when there is NO PATH to forward.

    REFUSES LOUDLY BY DESIGN (task 7.564). The alternative — forward some explicit safe default —
    was considered and REJECTED for two reasons. (1) PRIN-11: there is exactly ONE composer of this
    value (`server/spawn/carrier.js` `toolExecEnv()`, ruling `d-owner-f1-carrier-env-0808`); a
    default invented here would make `jobcontain` a SECOND composer, which is the precise failure
    probe arm R2 exists to catch, and it would produce a PATH that LOOKS right while omitting
    whatever the carrier actually composed. (2) An unset PATH is not a normal state on any live
    path — under the daemon `os.environ["PATH"]` IS `toolExecEnv()`'s output, and from a shell it
    is that shell's own PATH — so it means the carrier environment was already lost UPSTREAM. A
    default would convert that loud upstream bug into a quiet wrong-PATH failure much later, in
    the detached process, which is the hardest place to trace it back from.

    What is ruled OUT either way is the pre-fix behaviour this replaces: proceeding with no
    `--setenv` at all. `shutil.which` still finds `systemd-run` with PATH unset (the C library's
    `CS_PATH` fallback), so the launch went ahead and the child silently received the systemd
    MANAGER's PATH — measured, and exactly the defect task 7.551 exists to fix, reappearing
    quietly instead of failing loud.
    """


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
    # The inner hop goes back through the systemd --user MANAGER, whose environment is NOT this
    # process's — so the PATH carrier.js toolExecEnv() composed for this fired tool (the F1 fix,
    # decisions.md#d-owner-f1-carrier-env-0808) was lost here, and everything the detached process
    # later resolves BY NAME (recover-room -> coord.py's `claude`/`codex`/`opencode`, which live in
    # ~/.local/bin and ~/.opencode/bin) looked for it on the manager's PATH instead (7.551).
    # FORWARDED, NEVER RECOMPOSED (PRIN-11): under the daemon os.environ["PATH"] IS toolExecEnv()'s
    # output byte-for-byte (measured), and from a human shell it is that shell's own PATH — both
    # correct, neither a second composer. Positional, not separated by `--`: the flag must precede
    # the argv tail or systemd-run hands it to the child as an argument (probes/probe-detach-env.py).
    # REFUSE rather than degrade (task 7.564 — see CarrierEnvMissing for the decision and the
    # rejected alternative). The old spelling was `[...] if path else []`, which looked like a
    # guard and protected nothing: with PATH unset it emitted no --setenv and let the launch
    # proceed, handing the child the manager's PATH — the very defect this fix exists to prevent.
    #
    # THE EMPTY-STRING HALF OF THAT OLD GUARD WAS UNREACHABLE, and still is: `shutil.which`
    # treats PATH="" as a real (empty) search path rather than falling back to CS_PATH, so it
    # returns None and the bare-argv fallback above has ALREADY returned before this line. Only
    # PATH being genuinely UNSET reaches here, because that is the one case where which() still
    # resolves systemd-run. Probe arm P2 pins that short-circuit so this reasoning cannot rot.
    path = os.environ.get("PATH")
    if path is None:
        raise CarrierEnvMissing(
            "detach_argv: PATH is unset, so there is nothing to forward across the systemd-run "
            "hop. REFUSING to detach rather than launching without --setenv: the inner hop goes "
            "back through the systemd USER MANAGER, whose environment is not this process's, so "
            "the child would silently receive the MANAGER's PATH. ~/.local/bin and "
            "~/.opencode/bin are not on it, so claude / codex / opencode / coordinate would not "
            "resolve BY NAME in the detached process (task 7.551). Fix the CALLER's environment "
            "— under the daemon PATH is carrier.js toolExecEnv()'s output, from a shell it is "
            "the shell's own PATH. This module never composes one: there is exactly one "
            "composer (PRIN-11).")
    setenv = [f"--setenv=PATH={path}"]
    return ["systemd-run", "--user", "--collect", "--quiet", *setenv, *props,
            f"--unit={unit}", *argv], unit


def launch_detached(launch, unit, preexec_fn=None, timeout=60):
    """Fire a `detach_argv` launch and return (launcher_output, exit_code) — never waiting on a
    process that is not a launcher.

    THE LATENT HANG THIS EXISTS TO REMOVE (task 7.527). `detach_argv` returns two SHAPES and only
    one of them is a launcher, which is exactly what `unit` already tells us. With `systemd-run`
    present the argv IS a launcher: it exits the moment the unit is up, so waiting on it under a
    timeout is right and its output and exit code are worth having. With `systemd-run` ABSENT the
    fallback argv is the BARE COMMAND — not a launcher, but the long-lived process itself — and
    both callers pass `watch.py --loop-forever`, which is designed never to exit. Waiting on THAT
    with `timeout=60` blocked the caller for a full minute and then KILLED a loop that was working.

    So the shape decides: the launcher is waited on, the bare fallback is started in its own
    session and never waited on. `start_new_session=True` is what the fallback has instead of a
    cgroup — the child must not die with the caller's terminal or job.

    `preexec_fn` is the two callers' one real difference and is passed through, never assumed:
    `selfheal-watch.py` calls `contain()` first and MUST restore the pre-contain limits in the
    child (`child_preexec`) or the relaunched sensor inherits the detector's 256 MB cap;
    `rbtv-ignite-watch` never contains itself and correctly passes nothing.
    """
    if unit is None:
        subprocess.Popen(launch, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True, preexec_fn=preexec_fn)
        return "", 0
    res = subprocess.run(launch, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, timeout=timeout, preexec_fn=preexec_fn)
    return (res.stdout or b"").decode("utf-8", "replace").strip(), res.returncode


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
