"""Kit door onto the ONE ending store. Calls state-store/cli.js; does not rebuild it."""
import json
import os
import subprocess
from pathlib import Path

ENDING_CLI = Path(__file__).resolve().parent.parent / "state-store" / "cli.js"


class EndingStoreError(Exception):
    pass


def goal_id_of(pkg):
    return Path(pkg).name


def ending_store_db(start=None):
    env = os.environ.get("ENDING_STORE_DB")
    if env:
        return Path(env)
    here = Path(start or ".").resolve()
    for p in [here, *here.parents]:
        if (p / ".rbtv").is_dir():
            return p / ".rbtv" / "runtime" / "ignite" / "heart.db"
    return here / ".rbtv" / "runtime" / "ignite" / "heart.db"


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
        "evidence_pointer": evidence or f"checkout:{seat}",
        "diagnostic": diagnostic,
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
        "evidence_pointer": evidence or f"system:{seat}",
        "diagnostic": diagnostic,
    }
    if reason_class is not None:
        payload["reason_class"] = reason_class
    if named_event is not None:
        payload["named_event"] = named_event
    if armed is not None:
        payload["armed"] = armed
    return ending_store_op("stampSystem", payload, start=pkg)
