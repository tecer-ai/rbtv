"""Kit door onto the supervisor: the death stamp, the reap, and the reap debt.

⚠ THIS IS A DOOR, NOT A SECOND IMPLEMENTATION. `attest-exit` used to stamp the ending store
DIRECTLY, which made it an independent stamper: a second place that decided what a dead process
means. Spec-supervisor §3 (the attest-exit row) says that door BECOMES the supervisor death stamp,
so everything below is one `node supervisor/cli.js` call and nothing below classifies anything.
The evidence-to-ending table lives once, in `supervisor/death-stamp.js`.

Same shape and the same reasons as `ending_store.py` one file over: stdlib only, one JSON document
on stdout, and an exception rather than a silent zero on a failed call — a closer that cannot reach
the stamper must SAY so, because the silent arm is the defect this whole path exists to close.
"""
import json
import os
import subprocess
from pathlib import Path

from ending_store import EndingStoreError, ending_store_db, goal_id_of

SUPERVISOR_CLI = Path(__file__).resolve().parent.parent / "supervisor" / "cli.js"


class SupervisorError(Exception):
    pass


# `SUPERVISOR_REGISTRY` exists for the same reason `ENDING_STORE_DB` does one file over: a probe, a
# selftest and a second instance each need their OWN registry file, and a door that can only reach
# the module's default would make every one of them write the live daemon's liveness surface.
def registry_override(explicit=None):
    return explicit or os.environ.get("SUPERVISOR_REGISTRY") or None


def supervisor_op(op, payload, start=None, db=None, registry=None):
    """One `--op` call. `db` is the ending store's file; `registry` overrides the registry file."""
    cmd = ["node", str(SUPERVISOR_CLI), "--op", op, "--payload", json.dumps(payload)]
    registry = registry_override(registry)
    if registry:
        cmd += ["--registry", str(registry)]
    # Only the ops that read or write an ENDING need the store, and those are exactly the ops this
    # door exposes — so the path is resolved the same way `ending_store.py` resolves it, once.
    path = Path(db) if db else ending_store_db(start)
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["--db", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SupervisorError((proc.stderr or proc.stdout or "supervisor call failed").strip())
    text = (proc.stdout or "").strip()
    return json.loads(text) if text else None


def death_stamp(pkg, seat, *, session="", pid=None, start_time=None, exit_code=None,
                transcript_tail="", checked_in=False, detail="", evidence="", registry=None):
    """Stamp the ending for a sitting whose process is gone, and reap it. Spec-supervisor §4.

    Returns the supervisor's own result document — `act`, `stamped`, `ending`, `reason_class`,
    `reaped`. The caller REPORTS it and never re-decides it: a `done` checkout comes back
    `act=confirm-and-reap` with `stamped=False`, and that is not a failure to stamp, it is the
    stamp table's first row."""
    payload = {
        "goal": goal_id_of(pkg),
        "seat": seat,
        "checkedIn": bool(checked_in),
        "detail": str(detail or ""),
    }
    if session:
        payload["session"] = str(session)
    if pid:
        payload["pid"] = int(pid)
    if start_time:
        payload["start_time"] = str(start_time)
    if exit_code is not None:
        payload["exitCode"] = exit_code
    if transcript_tail:
        payload["transcriptTail"] = str(transcript_tail)
    # The caller's own evidence WINS where it carries one: `spawn.js#crashEvidence` already built
    # the pointer from the two facts only the witness held (the exit status and the log path).
    if evidence:
        payload["evidencePointer"] = str(evidence)
    return supervisor_op("stampDeath", payload, start=pkg, registry=registry)


# ── THE DOOR LIST, READ RATHER THAN RE-SPELLED [T4-R7, spec-supervisor §3] ────────────────────
# `launch.py` composes a door token that `supervisor/doors.js#doorForLauncher` reads back at the pid
# moment. A door spelled on one side and not the other produces a launch that silently registers
# UNSUPERVISED, so the kit ASKS the list instead of carrying a second copy of it. Read through
# node, like every other supervisor question, and fail-CLOSED: a list that cannot be read is not
# evidence that a door is wrapped.
def door_is_wrapped(door):
    """True when `door` is on the supervisor's list with disposition `wrapped`."""
    try:
        proc = subprocess.run(
            ["node", "-e",
             "const d=require(process.argv[1]);const r=d.doorRow(process.argv[2]);"
             "process.stdout.write(r&&r.disposition===d.WRAPPED?'1':'0')",
             str(SUPERVISOR_CLI.parent / "doors.js"), str(door)],
            capture_output=True, text=True)
    except OSError:
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "1"


def awaiting_reap(pkg, registry=None):
    """The reap debt: every registry row whose sitting ALREADY carries an ending.

    Successor to the deleted `awaiting-close.json`. A row still present after its ending was
    stamped is, by registry write moment (iii), a reap that has not completed — which is exactly
    the G-134 pane leak, derived rather than kept in a second store."""
    return supervisor_op("awaitingReap", {"goal": goal_id_of(pkg)}, start=pkg,
                         registry=registry) or []


def confirm_and_reap(pkg, seat, *, pid=None, start_time=None, registry=None):
    """Confirm the process is gone and drop the registry row. `{reaped, rowDropped, reason}`."""
    payload = {"goal": goal_id_of(pkg), "seat": seat}
    if pid:
        payload["pid"] = int(pid)
    if start_time:
        payload["start_time"] = str(start_time)
    return supervisor_op("confirmAndReap", payload, start=pkg, registry=registry)


__all__ = ["SupervisorError", "EndingStoreError", "supervisor_op", "registry_override",
           "death_stamp", "door_is_wrapped",
           "awaiting_reap", "confirm_and_reap", "SUPERVISOR_CLI"]
