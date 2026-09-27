"""Kit door onto the ONE ending store. Calls state-store/cli.js; does not rebuild it."""
import json
import os
import subprocess
import sys
from pathlib import Path

ENDING_CLI = Path(__file__).resolve().parent.parent / "state-store" / "cli.js"

# D27's definition of a WORKSPACE, stated where this kit needs it: the folder that ROOTS THE
# INSTALL — the ancestor holding the committed endpoint record `.rbtv/modules/ignite/server.json`
# — NOT any folder that happens to contain a `.rbtv/` directory. Canonical implementation:
# `ignite/ignite-cli/lib/config.js#findInstallRoot` ("walk up to the NEAREST ancestor holding
# `.rbtv/modules/ignite/server.json`. Nearest wins"). MIRRORED here in six lines rather than
# imported, for the reason `ignite/deploy/probe-suite-scheduled.py` states beside its own copy:
# the only Python port of config.js — `ignite/coord/gateway_client.py` — takes the workspace root
# as an ARGUMENT (`resolve_workspace_root(default, env=None)`) and owns no walker to reuse. This is
# the kit's ONE copy: `ruling.py` calls this function rather than carrying a second walk.
INSTALL_RECORD_REL = Path(".rbtv") / "modules" / "ignite" / "server.json"


class EndingStoreError(Exception):
    pass


def goal_id_of(pkg):
    return Path(pkg).name


def workspace_root(start=None):
    """The workspace `start` belongs to — the nearest ancestor that ROOTS THE INSTALL, or None.

    ⚠⚠ A `.rbtv/` DIRECTORY IS NOT A WORKSPACE. This walk used to stop at the first ancestor
    holding one, and on 2026-08-28 that cost an outage: at 03:02:15Z a probe run from the rbtv repo
    root planted `<repo>/.rbtv/runtime/watchdog/`, this walk then stopped THERE, and the stray
    `<repo>/.rbtv/runtime/ignite/heart.db` beside it (written 19s later through THIS function's
    `mkdir(parents=True)`) is where every ending stamped from a cwd under that repo went — while
    the daemon kept reading the vault's store. The same wrong rule at
    `deploy/probe-suite-scheduled.py` sent the probe suite's `latest.json` into the repo and the
    watchdog reported `probe-suite down` for ~2h against a suite firing hourly and green-of-record
    (5815fbaa, memory `observation/20260828-i-a-rbtv-that-does-not-root-the`). A stray `.rbtv/` is
    gitignored (`.gitignore:76 **/.rbtv/`), so nothing in `git status` or a review ever shows it.

    ⇒ So the test is the INSTALL RECORD, never the directory. A bare `.rbtv/` walked past is NAMED
    on stderr — that line is what turns the next planting into one journal line instead of two
    components silently disagreeing about which file is `heart.db`. Nearest-ancestor-wins is
    unchanged, so a genuinely nested install still shadows an outer one.

    Returns None when no ancestor roots an install. The CALLER decides what that means: this
    function never invents a root, because the folder it would invent is the one the outage was
    made of."""
    here = Path(start or ".").resolve()
    for p in (here, *here.parents):
        if (p / INSTALL_RECORD_REL).is_file():
            return p
        if (p / ".rbtv").is_dir():
            print(f"coord: {p} holds a .rbtv/ but no {INSTALL_RECORD_REL} — a .rbtv/ that does "
                  f"not root the install is NOT a workspace; walked past it", file=sys.stderr)
    return None


def ending_store_db(start=None):
    """The ONE store's file for `start`'s workspace. `ENDING_STORE_DB` wins outright.

    ⚠ NO CREATE-AT-CWD FALLBACK. This used to answer `<start>/.rbtv/runtime/ignite/heart.db` when
    the walk found nothing, and `ending_store_op` then `mkdir(parents=True)`'d it into existence —
    so any coord-kit call from a cwd outside a workspace MINTED a `.rbtv/` there, which then
    out-voted the real install for every bare-`.rbtv/` walk starting below it. That is exactly the
    stray `3-resources/tools/rbtv/.rbtv/runtime/ignite/heart.db` found 2026-08-28 (5815fbaa). An
    ending written to a store no daemon reads is worse than a refusal: it reads as recorded."""
    env = os.environ.get("ENDING_STORE_DB")
    if env:
        return Path(env)
    root = workspace_root(start)
    if root is None:
        raise EndingStoreError(
            f"no workspace above {Path(start or '.').resolve()}: walked to the filesystem root "
            f"without finding a directory holding {INSTALL_RECORD_REL} (the install record that "
            f"D27 and ignite/ignite-cli/lib/config.js#findInstallRoot define a workspace by). "
            f"NOTHING WAS WRITTEN — set ENDING_STORE_DB to name a store explicitly.")
    return root / ".rbtv" / "runtime" / "ignite" / "heart.db"


# `evidence_pointer` is spec §1.2 TEXT, and this door is the validation boundary that decides
# what reaches the store. Callers legitimately hold richer objects — `attest-exit` carries the
# transcript path straight off `export_transcript`, which returns a `Path` — so the coercion
# belongs HERE, once, beside the one `declared_outputs` already did. It used to live on only one
# of the three text fields, and a `Path` evidence pointer aborted the whole kit selftest with
# `TypeError: Object of type PosixPath is not JSON serializable`.
def ending_store_op(op, payload, start=None, db=None):
    path = Path(db) if db else ending_store_db(start)
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["node", str(ENDING_CLI), "--db", str(path), "--op", op,
         "--payload", json.dumps(payload)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise EndingStoreError((proc.stderr or proc.stdout or "ending-store failed").strip())
    text = (proc.stdout or "").strip()
    return json.loads(text) if text else None


def get_current_ending(pkg, seat):
    return ending_store_op(
        "getCurrentEnding",
        {"goal": goal_id_of(pkg), "seat": seat},
        start=pkg)


def seat_waiting_on_owner(pkg, seat):
    return bool(ending_store_op(
        "seatWaitingOnOwner",
        {"goal": goal_id_of(pkg), "seat": seat},
        start=pkg))


# spec-state-store §2.1 as a LIST — the same WHERE clause `seat_waiting_on_owner` answers as a
# boolean, so a row can never be held by one reader and clean by the other. ONE call per goal:
# `ready.py` needs the ask ids of EVERY seat and must not pay a `node` subprocess per seat.
# `posted` DEFAULTS TO 1 AND THAT DEFAULT IS §2.1 — see the JS side. `posted=None` asks the
# different question "every open ask, delivered or not", which only the check-out door's
# never-posted note needs; it is never the wait predicate.
def list_open_asks(pkg, seat=None, posted=1):
    payload = {"goal": goal_id_of(pkg), "posted": posted}
    if seat:
        payload["seat"] = seat
    return ending_store_op("listOpenAsks", payload, start=pkg) or []


def is_launchable(predecessors_done, ending, armed, failed_terminal=False):
    return bool(ending_store_op("isLaunchable", {
        "predecessorsDone": bool(predecessors_done),
        "ending": ending,
        "armed": armed,
        "failedTerminal": bool(failed_terminal),
    }))


def stamp_seat_declare(pkg, seat, ending, *, diagnostic="", declared_outputs=None,
                       evidence="", replace=True):
    payload = {
        "goal": goal_id_of(pkg),
        "seat": seat,
        "ending": ending,
        "replace": replace,
        "evidence_pointer": str(evidence) if evidence else f"checkout:{seat}",
        "diagnostic": str(diagnostic or ""),
    }
    if declared_outputs:
        payload["declared_outputs"] = [str(p) for p in declared_outputs]
    if ending == "incomplete":
        payload["armed"] = 1
    return ending_store_op("stampSeatDeclare", payload, start=pkg)


def stamp_system(pkg, seat, ending, *, reason_class=None, diagnostic="",
                 evidence="", named_event=None, armed=None, replace=True):
    payload = {
        "goal": goal_id_of(pkg),
        "seat": seat,
        "ending": ending,
        "replace": replace,
        "evidence_pointer": str(evidence) if evidence else f"system:{seat}",
        "diagnostic": str(diagnostic or ""),
    }
    if reason_class is not None:
        payload["reason_class"] = reason_class
    if named_event is not None:
        payload["named_event"] = named_event
    if armed is not None:
        payload["armed"] = armed
    return ending_store_op("stampSystem", payload, start=pkg)



# ---- the leader's HOLD (spec-recovery: a ruling ON a row, not a counter) ----
#
# The same door as everything above: the ops live in `state-store`, and this side spells no SQL and
# opens no database. A second Python writer of `heart.db` would be the dual-writer split
# `ending_store_db`'s walk-up exists to prevent.
def hold_seat(pkg, seat, until, *, anchor, held_by, ask_id=None):
    payload = {
        "goal": goal_id_of(pkg),
        "seat": seat,
        "until": until,
        "anchor": str(anchor),
        "held_by": str(held_by),
    }
    if ask_id:
        payload["ask_id"] = str(ask_id)
    return ending_store_op("holdSeat", payload, start=pkg)


def release_seat(pkg, seat):
    return ending_store_op("releaseSeat", {"goal": goal_id_of(pkg), "seat": seat}, start=pkg)


def get_seat_hold(pkg, seat):
    """The RAW row, live or spent — what `release` is releasing."""
    return ending_store_op("getSeatHold", {"goal": goal_id_of(pkg), "seat": seat}, start=pkg)


def seat_held(pkg, seat):
    """The row if the hold is still LIVE, else None — the one predicate the reconcile pass reads."""
    return ending_store_op("seatHeld", {"goal": goal_id_of(pkg), "seat": seat}, start=pkg)
