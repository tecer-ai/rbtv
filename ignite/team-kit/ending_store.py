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


def open_asks(pkg, seat=None, start=None, db=None):
    """Every `open_asks` row for this goal (optionally one seat), oldest first — READ-ONLY.

    Spec-state-store §3: `owner-asks.json` is gone and the ONE record is the `open_asks` table in
    `.rbtv/runtime/ignite/heart.db`. `ignite/bridges/chat/ask-store.js` is still the ONE WRITER —
    this reader exists so the boot-prompt re-inject and the owed-answers digest ask the store which
    asks are open instead of parsing a second file that could disagree with it.

    A read, not an op: the store's JSON CLI exposes single-ask and counting reads only, and adding
    a writer-shaped door for a listing would be a second way to reach the same rows.

    NEVER RAISES. Both callers compose on paths that must degrade to "no ask" rather than fail — a
    boot prompt is built on EVERY relaunch of EVERY seat, and a digest is a report. A store that
    does not exist yet, or is mid-write, is an ABSENT ask.

    Each row carries `text`, read back off `evidence_pointer` — §3 defines that pointer as the
    thread permalink or the on-disk reply copy, and the bridge writes the copy.
    """
    import sqlite3
    path = Path(db) if db else ending_store_db(start or pkg)
    if not path.exists():
        return []
    sql = ("SELECT ask_id, goal, seat, label, state, posted, posted_at, evidence_pointer "
           "FROM open_asks WHERE goal = ?")
    params = [goal_id_of(pkg)]
    if seat:
        sql += " AND seat = ?"
        params.append(seat)
    sql += " ORDER BY rowid ASC"
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(sql, params)]
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    for r in rows:
        try:
            r["text"] = Path(r["evidence_pointer"]).read_text(encoding="utf-8").strip()
        except OSError:
            r["text"] = ""
    return rows
