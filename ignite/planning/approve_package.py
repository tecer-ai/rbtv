#!/usr/bin/env python3
"""The approve-package writer — the planning pipeline's verify step leaving
`<planning goal>/planning/approve-package.json` for the fourteenth gateway intent to read.

THE GAP THIS CLOSES. `state-store/heart/start-execution.js` — the daemon-side executor of the
`start-execution` intent (owner ruling 2026-08-24, option (b)) — reads the approve-package to learn
WHAT the owner approved. Nothing wrote one. Its `readApprovePackage` therefore refused
`no-approve-package` on every genuine `approve`, loudly and by design, and the fourteenth intent
could not open. This module is the missing writer, and it lives with the planning door because the
verify seat that calls it is a planning-pipeline seat.

⚑ THE READER DEFINES THE CONTRACT. Every required field below exists because
`start-execution.js` or `path_b.py#run_path_b` consumes it, and nothing is written that neither
reads. The three DAEMON-STAMPED keys — `planning_goal`, `goals_root`, `origin_id` — are REFUSED
here rather than filled: `readApprovePackage` refuses `package-not-bound-here` when a package's
`planning_goal` or `goals_root` disagrees with its own derivation, so a writer that emits them can
only ever agree by accident and, when a package is copied between goals, hides the very copy that
refusal exists to catch.

⚑ THE WRITE GOES THROUGH `coord.records.atomic_write`, which is tmp+rename AND the derived-tree
refusal in one door. `planning/approve-package.json` is PLANNING STATE, not a derived lane: the
regenerated tree is `planning/current/seat-lane/`, which the lane builder marks with `DERIVED.md`,
and this file sits one level above it beside Path B's own `bound-plan.json`. So the guard is
expected to PASS here and is called anyway — a goal whose `planning/` has been marked derived by
some future regenerator must refuse rather than write a file the next materialize deletes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / "coord"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from records import atomic_write  # noqa: E402  (coord's one write door)

# The package's home on the planning goal, spelled exactly as `start-execution.js`'s
# `APPROVE_PACKAGE` spells it. `planning/` is where Path B already leaves `bound-plan.json`, so the
# plan and the pointer to it sit in one folder rather than two conventions.
APPROVE_PACKAGE = Path("planning") / "approve-package.json"

# `bus-ferry.js#isSafeName`, in Python. A name, never a path: `execution_goal` becomes a PATH
# SEGMENT under `.rbtv/goals/`, and `owner` is an ADDRESS rather than a name anywhere in this system.
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
OWNER_TOKEN = "owner"

# `start-execution.js`'s `COMMIT_RE`. A ref name is a MOVING binding standing in for the tree the
# owner actually read [T5-R5].
COMMIT_RE = re.compile(r"^[0-9a-f]{7,64}$")

# Refused, never written — the daemon stamps these itself (see the header).
DAEMON_STAMPED = ("planning_goal", "goals_root", "origin_id")

# Read by `run_path_b`; optional because the birth has its own default for each.
OPTIONAL_KEYS = (
    "roster", "contract", "contract_file", "workflow", "sheet", "catalog_root",
    "git_dir", "envelope_stamp", "planning_pass_id",
)


class ApprovePackageRefusal(Exception):
    """A package that would be written wrong. Refused before any byte lands."""

    def __init__(self, code, detail):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def is_safe_name(name):
    n = str(name)
    return bool(SAFE_NAME_RE.match(n)) and n != OWNER_TOKEN


def build_package(*, execution_goal, bound_commit, lane, plan_artifacts, **optional):
    """The package as a dict, validated against what the reader consumes. Raises on anything the
    reader would refuse — the refusal belongs at the writer, where a seat can still fix it."""
    if not is_safe_name(execution_goal):
        raise ApprovePackageRefusal(
            "bad-execution-goal",
            f"{execution_goal!r} is not a bare safe name — it becomes a path segment "
            "under .rbtv/goals/",
        )
    if not COMMIT_RE.match(str(bound_commit or "")):
        raise ApprovePackageRefusal(
            "bad-bound-commit",
            f"{bound_commit!r} is not lowercase hex 7-64 — a ref name is a moving binding [T5-R5]",
        )
    if not str(lane or "").strip():
        raise ApprovePackageRefusal("bad-lane", "lane is required — `scaffold --lane` has no default")
    if not str(plan_artifacts or "").strip():
        raise ApprovePackageRefusal(
            "bad-plan-artifacts",
            "plan_artifacts is required — the birth resolves the approved plan at the bound commit "
            "through it",
        )
    for key in DAEMON_STAMPED:
        if optional.get(key) is not None:
            raise ApprovePackageRefusal(
                "daemon-stamped-key",
                f"{key} is stamped by the daemon and refused here — a package that names its own "
                "planning goal or goals root is refused `package-not-bound-here` when it disagrees, "
                "which is how a package copied from another goal is caught",
            )
    pkg = {
        "execution_goal": str(execution_goal),
        "bound_commit": str(bound_commit),
        "lane": str(lane),
        "plan_artifacts": str(plan_artifacts),
    }
    for key in OPTIONAL_KEYS:
        value = optional.get(key)
        if value is None:
            continue
        pkg[key] = list(value) if key == "roster" else str(value)
    return pkg


def package_path(goal_dir):
    return Path(goal_dir) / APPROVE_PACKAGE


def write_approve_package(goal_dir, **fields):
    """Write the package onto the PLANNING goal, atomically. Returns the path written."""
    pkg = build_package(**fields)
    dest = package_path(goal_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # tmp+rename plus the derived-tree refusal, in coord's one door. Never `open(dest, "w")`: an
    # interrupted truncate-write leaves a zero-byte package, which reads as `bad-approve-package`.
    atomic_write(dest, json.dumps(pkg, indent=2, sort_keys=True) + "\n")
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="approve-package",
        description="Write the approve-package the fourteenth gateway intent reads. Run by the "
                    "planning pipeline's verify seat, once, after both contract checks.",
    )
    ap.add_argument("--goal-dir", required=True,
                    help="the PLANNING goal's folder — the package lands at its planning/approve-package.json")
    ap.add_argument("--execution-goal", required=True,
                    help="the name the execution goal will be born under; a bare safe name")
    ap.add_argument("--bound-commit", required=True,
                    help="the commit the plan artifacts bind to, lowercase hex 7-64 — never a ref name [T5-R5]")
    ap.add_argument("--lane", required=True, help="the born goal's lane, as `scaffold --lane` takes it")
    ap.add_argument("--plan-artifacts", required=True,
                    help="path to the approved plan's artifacts, resolvable at the bound commit")
    ap.add_argument("--roster", default=None,
                    help="comma-separated seat ids of the execution roster (duplicates are refused at birth)")
    ap.add_argument("--contract-file", default=None, help="the goal contract `scaffold --contract` receives")
    ap.add_argument("--workflow", default=None, help="the workflow the execution seats are minted from")
    ap.add_argument("--sheet", default=None, help="the casting sheet the uncast check reads")
    ap.add_argument("--catalog-root", default=None, help="the catalog root the mint reads")
    ap.add_argument("--git-dir", default=None, help="the repo the bound commit lives in (defaults to --plan-artifacts)")
    ap.add_argument("--json", action="store_true", help="print the written package instead of a one-line report")
    args = ap.parse_args(argv)

    try:
        dest = write_approve_package(
            args.goal_dir,
            execution_goal=args.execution_goal,
            bound_commit=args.bound_commit,
            lane=args.lane,
            plan_artifacts=args.plan_artifacts,
            roster=[s.strip() for s in args.roster.split(",") if s.strip()] if args.roster else None,
            contract_file=args.contract_file,
            workflow=args.workflow,
            sheet=args.sheet,
            catalog_root=args.catalog_root,
            git_dir=args.git_dir,
        )
    except ApprovePackageRefusal as exc:
        print(json.dumps({"ok": False, "refusal": {"code": exc.code, "detail": exc.detail}}, indent=2))
        return 2
    if args.json:
        print(dest.read_text(encoding="utf-8"), end="")
    else:
        print(f"approve-package written: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
