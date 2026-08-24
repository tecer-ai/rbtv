#!/usr/bin/env python3
"""Supervised-materialize wrapper skeleton (spec-planning-door §4)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from failure import (
    CLASS_ATOMIC_CORE_REFUSAL,
    CLASS_ENVELOPE_REFUSAL,
    CLASS_LOCK_COLLISION,
    CLASS_ROSTER_NAME_COLLISION,
    ENVELOPE_REFUSED_STAMP,
    MaterializeFailure,
    ORIGIN_APPROVAL_THREAD,
    ORIGIN_GATE_LANE,
    make_record,
    stamp_gate_lane,
    write_failure_record,
)
from lock import LockCollision, take_lock

PATH_A = "A"
PATH_B = "B"


def uncast_in_sheet(sheet_path, seat_names):
    """Refuse-before-write pattern (KEEP). Cast = harness and model both non-empty.

    Same predicate as launch-profiles/catalog.js `declaresBinding`. Call site is
    this wrapper: a non-empty result refuses the whole act.
    """
    try:
        raw = Path(sheet_path).read_text(encoding="utf-8")
        sheet = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "uncast-in-sheet",
            f"{sheet_path}: {exc}",
        ) from exc
    seats = (sheet or {}).get("seats")
    if not isinstance(seats, dict):
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "uncast-in-sheet",
            f"{sheet_path}: must be a JSON object carrying a 'seats' mapping",
        )
    missing = []
    for name in seat_names:
        entry = seats.get(name) or {}
        harness = str(entry.get("harness") or "").strip()
        model = str(entry.get("model") or "").strip()
        if not harness or not model:
            missing.append(name)
    return missing

def _fail_arm(*, goal_folder, origin, origin_id, class_, code, subject, reason, sessions_path):
    record = make_record(
        origin=origin,
        origin_id=origin_id,
        class_=class_,
        code=code,
        subject=subject,
        reason=reason,
    )
    write_failure_record(goal_folder, record)
    if origin == ORIGIN_GATE_LANE:
        stamp_gate_lane(
            goal_folder=goal_folder, origin_id=origin_id, sessions_path=sessions_path
        )
    return {"ok": False, "record": record}


def supervised_materialize(
    *,
    path,
    goal_folder,
    planning_pass_id,
    origin,
    origin_id,
    subject,
    validate,
    mint,
    scaffold=None,
    reclaim=None,
    envelope_stamp=None,
    sessions_path=None,
    uncast=None,
    record_goal_folder=None,
):
    """validate → uncast → (path B) scaffold → take lock → mint → release lock.

    Callers inject validate/scaffold/mint. `uncast` (callable → list of seat
    names) refuses the whole act if any seat would land uncast. No Slack.
    Path B: `goal_folder` is the new execution goal (lock + mint target);
    `record_goal_folder` is the planning goal that receives the D12 record.
    """
    if path not in (PATH_A, PATH_B):
        raise ValueError(f"path must be {PATH_A!r} or {PATH_B!r}")
    if origin not in (ORIGIN_APPROVAL_THREAD, ORIGIN_GATE_LANE):
        raise ValueError(f"origin must be approval-thread or gate-lane")
    record_at = record_goal_folder if record_goal_folder is not None else goal_folder
    if envelope_stamp == ENVELOPE_REFUSED_STAMP:
        return _fail_arm(
            goal_folder=record_at,
            origin=origin,
            origin_id=origin_id,
            class_=CLASS_ENVELOPE_REFUSAL,
            code="launch-refused",
            subject=subject,
            reason=ENVELOPE_REFUSED_STAMP,
            sessions_path=sessions_path,
        )

    scaffolded = False
    try:
        validate()
        if uncast is not None:
            uncast_seats = uncast()
            if uncast_seats:
                raise MaterializeFailure(
                    CLASS_ATOMIC_CORE_REFUSAL,
                    "uncast-in-sheet",
                    "would land uncast: " + ", ".join(uncast_seats),
                    subject,
                )
        if path == PATH_B:
            if scaffold is None:
                raise MaterializeFailure(
                    CLASS_ROSTER_NAME_COLLISION,
                    "scaffold-missing",
                    "path B requires a scaffold callable",
                    subject,
                )
            scaffold()
            scaffolded = True
        with take_lock(goal_folder, planning_pass_id):
            mint()
        return {"ok": True, "record": None}
    except LockCollision as exc:
        if scaffolded and reclaim is not None:
            reclaim()
        return _fail_arm(
            goal_folder=record_at,
            origin=origin,
            origin_id=origin_id,
            class_=CLASS_LOCK_COLLISION,
            code=exc.code,
            subject=subject,
            reason=exc.reason,
            sessions_path=sessions_path,
        )
    except MaterializeFailure as exc:
        if scaffolded and reclaim is not None:
            reclaim()
        return _fail_arm(
            goal_folder=record_at,
            origin=origin,
            origin_id=origin_id,
            class_=exc.class_,
            code=exc.code,
            subject=exc.subject or subject,
            reason=exc.reason,
            sessions_path=sessions_path,
        )
