#!/usr/bin/env python3
"""Generic dead-room detector: one frozen argv, target is this process's cwd.

`fire-tool` already crosses `args.workdir` as the child's cwd (`ticker.js`
`runToolLikeExec`). Session name is the goal folder name (lease design-lock
item 2). Package is the goal folder (item 8). `--seat` is resolved from
`taskforce.csv` (`leader` if present, else the first seat).

A goal that has never started (no `sessions.csv` data rows) is not a dead
room — exit 0, no recovery. That is what makes auto-arm at creation safe.

`--package` (not `--goal`) is handed to recover-room: `--goal` derives the
lease, and a dead room is 0 rooms, which recover-room refuses as "not
executing". The throwaway twin already uses `--package` for the same reason.
"""

import argparse
import csv
import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SELFHEAL = HERE / "selfheal-room.py"
RECOVER = HERE / "recover-room.py"


def log(msg):
    print(f"selfheal-room-for-goal: {msg}", flush=True)


def resolve_seat(goal_dir):
    tf = goal_dir / "taskforce.csv"
    if not tf.is_file():
        return None, f"no taskforce.csv in {goal_dir}"
    with tf.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    seats = [(r.get("seat") or "").strip() for r in rows if (r.get("seat") or "").strip()]
    if not seats:
        return None, f"taskforce.csv in {goal_dir} names no seat"
    if "leader" in seats:
        return "leader", "taskforce.csv carries leader"
    return seats[0], f"no leader in taskforce.csv; first seat is {seats[0]!r}"


def ever_started(goal_dir):
    sessions = goal_dir / "sessions.csv"
    if not sessions.is_file():
        return False
    with sessions.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return any((r.get("session-id") or r.get("seat") or "").strip() for r in rows)


def main():
    ap = argparse.ArgumentParser(description="Dead-room detection for the goal dir that is cwd.")
    ap.add_argument("--coord", required=True, help="absolute path to coord.py")
    ap.add_argument("--require-cmd", action="append", default=[],
                    help="forwarded to selfheal-room.py (repeatable)")
    ap.add_argument("--budget-s", type=int, default=600)
    ap.add_argument("--goal-dir", default=None,
                    help="goal folder; default: cwd (fire-tool workdir)")
    args = ap.parse_args()

    goal_dir = Path(args.goal_dir or os.getcwd()).resolve()
    if not goal_dir.is_dir():
        log(f"CONFIG ERROR — goal dir {goal_dir} is not a directory. Firing nothing.")
        return 2

    session = goal_dir.name
    if session.startswith("_"):
        log(f"SKIP — {session!r} is a reserved/_-prefixed folder, not a goal room.")
        return 0

    if not ever_started(goal_dir):
        log(f"NEVER STARTED — {goal_dir} has no sessions.csv rows. Not a dead room. No-op.")
        return 0

    seat, why = resolve_seat(goal_dir)
    if seat is None:
        log(f"SKIP — cannot resolve a recovery seat: {why}")
        return 0
    log(f"recovery seat {seat!r} — {why}")

    recovery = [
        sys.executable, str(RECOVER),
        "--session", session,
        "--package", str(goal_dir),
        "--seat", seat,
        "--coord", args.coord,
    ]
    argv = [
        sys.executable, str(SELFHEAL),
        "--session", session,
        "--budget-s", str(args.budget_s),
    ]
    for cmd in args.require_cmd:
        argv.extend(["--require-cmd", cmd])
    argv.append("--")
    argv.extend(recovery)

    log(f"exec: {' '.join(argv)}")
    os.execv(argv[0], argv)


if __name__ == "__main__":
    sys.exit(main())
