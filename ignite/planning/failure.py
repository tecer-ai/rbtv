#!/usr/bin/env python3
"""Failure-record writer + origin routing (spec-planning-door §4)."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from lock import current_dir

ORIGIN_APPROVAL_THREAD = "approval-thread"
ORIGIN_GATE_LANE = "gate-lane"
ORIGINS = (ORIGIN_APPROVAL_THREAD, ORIGIN_GATE_LANE)

CLASS_LOCK_COLLISION = "lock-collision"
CLASS_ROSTER_NAME_COLLISION = "roster-name-collision"
CLASS_UNRESOLVABLE_REFERENCE = "unresolvable-reference"
CLASS_ENVELOPE_REFUSAL = "envelope-refusal"
CLASS_ATOMIC_CORE_REFUSAL = "atomic-core-refusal"
CLASSES = (
    CLASS_LOCK_COLLISION,
    CLASS_ROSTER_NAME_COLLISION,
    CLASS_UNRESOLVABLE_REFERENCE,
    CLASS_ENVELOPE_REFUSAL,
    CLASS_ATOMIC_CORE_REFUSAL,
)

RECORD_FIELDS = ("origin", "origin-id", "class", "code", "subject", "reason")

ENVELOPE_REFUSED_STAMP = "failed: launch-refused"
INCOMPLETE_MATERIALIZE_FAILED = "incomplete: materialize-failed"
NAMED_EVENT = "materialize-resolved"

# TODO(impl-state-store): ending-store WRITE — stamp_gate_lane uses the session-close
# fallback until impl-state-store-core merges the write-once API.


class MaterializeFailure(Exception):
    def __init__(self, class_, code, reason, subject=""):
        super().__init__(reason)
        self.class_ = class_
        self.code = code
        self.reason = reason
        self.subject = subject


def make_record(*, origin, origin_id, class_, code, subject, reason):
    if origin not in ORIGINS:
        raise ValueError(f"origin must be one of {ORIGINS}, got {origin!r}")
    if class_ not in CLASSES:
        raise ValueError(f"class must be one of {CLASSES}, got {class_!r}")
    return {
        "origin": origin,
        "origin-id": str(origin_id),
        "class": class_,
        "code": str(code),
        "subject": str(subject),
        "reason": str(reason),
    }


def record_path(goal_folder):
    return current_dir(goal_folder) / "materialize-failure.json"


def write_failure_record(goal_folder, record):
    for key in RECORD_FIELDS:
        if key not in record:
            raise ValueError(f"failure record missing {key}")
    path = record_path(goal_folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def stamp_path(goal_folder):
    return current_dir(goal_folder) / "materialize-failed.stamp"


def stamp_gate_lane(*, goal_folder, origin_id, sessions_path=None):
    """Stamp the gate lane `incomplete: materialize-failed` (disarmed).

    Ending-store WRITE is impl-state-store's API. Until that lands this writes
    the diagnostic via the session-close fallback (sessions.csv disposition
    `incomplete` + sidecar stamp carrying the exact diagnostic spelling).
    """
    payload = {
        "path": "session-close-fallback",
        "diagnostic": INCOMPLETE_MATERIALIZE_FAILED,
        "armed": 0,
        "named_event": NAMED_EVENT,
        "who_stamped": "system",
        "origin-id": str(origin_id),
        "stamped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    dest = stamp_path(goal_folder)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if sessions_path:
        _session_close_fallback(Path(sessions_path), str(origin_id))
    return payload


def _session_close_fallback(sessions_csv, seat_id):
    if not sessions_csv.exists():
        return
    with sessions_csv.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return
    header, body = rows[0], rows[1:]
    if "seat" not in header or "disposition" not in header:
        return
    si, di = header.index("seat"), header.index("disposition")
    ei = header.index("ended") if "ended" in header else None
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for row in reversed(body):
        while len(row) < len(header):
            row.append("")
        if row[si].strip() == seat_id and (ei is None or not row[ei].strip()):
            row[di] = "incomplete"
            if ei is not None:
                row[ei] = now
            break
    with sessions_csv.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerows([header, *body])
