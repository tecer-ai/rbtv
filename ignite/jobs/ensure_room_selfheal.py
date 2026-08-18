#!/usr/bin/env python3
"""Idempotent arm of room selfheal for one goal — register-job + add-job via ignite CLI.

Used by goal_creation_request after a successful scaffold. Existing id / existing
queue row is left alone. The tool name is the generic `selfheal-room-goal` entry
(workdir = goal dir); a per-room yaml key is not required.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

GENERIC_TOOL = "selfheal-room-goal"
ARGS_SCHEMA = json.dumps({
    "required": {"tool": "string"},
    "optional": {"workdir": "string"},
})
EVERY_S = 300


def job_id_for(goal):
    return f"selfheal-room-{goal}"


def _ignite_cmd(ignite_bin):
    bin_path = Path(ignite_bin)
    if bin_path.suffix == ".js":
        return ["node", str(bin_path)]
    return [str(bin_path)]


def _run(argv, dry_run):
    if dry_run:
        return {"dry-run": True, "argv": argv, "rc": 0, "stdout": "", "stderr": ""}
    env = os.environ.copy()
    proc = subprocess.run(argv, capture_output=True, text=True, env=env)
    return {
        "dry-run": False,
        "argv": argv,
        "rc": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
    }


def _inspect_rows(ignite, target):
    proc = subprocess.run(
        ignite + ["--json", "inspect", target],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout or "")
    except ValueError:
        return None
    return ((data.get("result") or {}).get("rows")) or []


def _has_id(rows, job_id):
    return any((r.get("job_id") == job_id) for r in (rows or []))


def ensure_room_selfheal(ignite_bin, goal, goal_dir, dry_run=False):
    job_id = job_id_for(goal)
    ignite = _ignite_cmd(ignite_bin)
    desc = f"dead-room detection + recovery, room {goal}"
    register = ignite + [
        "register-job", job_id,
        "--action-type", "fire-tool",
        "--args-schema", ARGS_SCHEMA,
        "--description", desc,
    ]
    add = ignite + [
        "add-job",
        "--fn", job_id,
        "--arg", f"tool={GENERIC_TOOL}",
        "--arg", f"workdir={goal_dir}",
        "--trigger", "periodic",
        "--every", str(EVERY_S),
    ]
    jobs = None if dry_run else _inspect_rows(ignite, "jobs")
    queue = None if dry_run else _inspect_rows(ignite, "queue")
    steps = []
    if jobs is not None and _has_id(jobs, job_id):
        steps.append({
            "step": "selfheal-register",
            "rc": 0,
            "skipped": "job-exists",
            "argv": register,
        })
    else:
        steps.append({"step": "selfheal-register", **_run(register, dry_run)})
    if queue is not None and _has_id(queue, job_id):
        steps.append({
            "step": "selfheal-schedule",
            "rc": 0,
            "skipped": "queue-row-exists",
            "argv": add,
        })
    else:
        steps.append({"step": "selfheal-schedule", **_run(add, dry_run)})
    return {"job_id": job_id, "tool": GENERIC_TOOL, "steps": steps}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Arm room selfheal for one goal (idempotent).")
    ap.add_argument("--ignite-bin", required=True)
    ap.add_argument("--goal", required=True)
    ap.add_argument("--goal-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out = ensure_room_selfheal(args.ignite_bin, args.goal, args.goal_dir, dry_run=args.dry_run)
    print(json.dumps(out, indent=2))
    rcs = [s.get("rc", 0) for s in out["steps"]]
    # register-job create-only refusal (existing id) and add-job of an already-queued
    # periodic row are both "left alone" — the caller treats non-zero as a note, not a
    # scaffold failure. Exit 0 unless the CLI could not be invoked.
    return 0 if all(isinstance(c, int) for c in rcs) else 2


if __name__ == "__main__":
    sys.exit(main())
