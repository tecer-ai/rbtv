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
import csv
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

# …and `goal_cli.py#GOAL_NAME_RE`, the THIRD reader of this same field. `execution_goal` is handed
# to `rbtv-goal scaffold`, which refuses anything that is not lowercase kebab-case — a rule STRICTER
# than the ferry's. `Scratch_Exec` passed this writer and died at the scaffold (measured
# 2026-08-27), which is a refusal in the owner's Slack thread with the approval already spent. Both
# readers are re-spoken here because both read this field; the narrower one is not a second opinion,
# it is the next door.
GOAL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# `start-execution.js`'s `COMMIT_RE`. A ref name is a MOVING binding standing in for the tree the
# owner actually read [T5-R5].
COMMIT_RE = re.compile(r"^[0-9a-f]{7,64}$")

# Refused, never written — the daemon stamps these itself (see the header).
DAEMON_STAMPED = ("planning_goal", "goals_root", "origin_id")

# `materialize-seats.py#MANIFEST_SEAT_COLUMN` — the column a workflow manifest names its seats in,
# and the one `build_goal_local_lane` reads out of a plan's own `planning/current/manifest.csv`.
MANIFEST_SEAT_COLUMN = "Seat/workflow"

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
    return bool(SAFE_NAME_RE.match(n)) and bool(GOAL_NAME_RE.match(n)) and n != OWNER_TOKEN


def build_package(*, execution_goal, bound_commit, lane, plan_artifacts, **optional):
    """The package as a dict, validated against what the reader consumes. Raises on anything the
    reader would refuse — the refusal belongs at the writer, where a seat can still fix it."""
    if not is_safe_name(execution_goal):
        raise ApprovePackageRefusal(
            "bad-execution-goal",
            f"{execution_goal!r} is not a bare safe name — it becomes a path segment under "
            ".rbtv/goals/ AND the goal name `rbtv-goal scaffold` takes, which is lowercase "
            "kebab-case ([a-z0-9] words joined by single hyphens). A name this writer accepts and "
            "the scaffold refuses is a birth that fails after the owner has already approved",
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


def refuse_bad_contract_file(goal_dir, pkg):
    """The contract file must exist UNDER the plan artifacts. Refused here, never at birth.

    ⚠ WHY THIS REFUSAL IS AT THE WRITER. The contract becomes the born goal's `goal.md` body, and
    the birth reads it out of the BOUND COMMIT — so a contract that is not among the plan artifacts
    is not in the tree the owner approved, and the birth can only refuse it after the approval is
    already spent, in the owner's Slack thread, with nothing left to fix it with. Here, a seat that
    named the wrong path is still sitting and can write the file.

    The path is relative TO THE PLANNING GOAL — the same resolution `path_b.bound_contract_file`
    performs — because that is the goal folder the seat writing this package is inside of. This
    reads the WORKING TREE; the birth re-reads the bound commit, which is the authority. The two
    disagree only when the artifact was never committed, and that is what `plan_artifacts`'
    resolvability check at birth already covers.
    """
    contract_file = pkg.get("contract_file")
    if not contract_file:
        return
    src = Path(contract_file)
    if not src.is_absolute():
        src = Path(goal_dir) / src
    artifacts = Path(pkg["plan_artifacts"]).resolve()
    try:
        src.resolve().relative_to(artifacts)
    except ValueError:
        raise ApprovePackageRefusal(
            "bad-contract-file",
            f"{contract_file} resolves to {src} — outside the approved plan artifacts "
            f"({artifacts}). The birth reads the contract from the bound commit's tree, and a "
            "file the approval does not bind is not there",
        )
    if not src.is_file():
        raise ApprovePackageRefusal(
            "bad-contract-file",
            f"{contract_file} does not exist ({src}). It becomes the born goal's goal.md body — "
            "write it into the plan artifacts and bind it, then re-run this writer",
        )


def refuse_roster_not_in_plan(goal_dir, pkg):
    """Every roster seat must be one the PLAN authored — when the plan is what mints them.

    ⚠ THE TWO ROUTES. A package that declares a `workflow` names cataloged seats, and the catalog
    is what says whether they exist; this says nothing about those. A package that declares NO
    workflow is a one-off plan, and its seats are minted `--goal-local` from
    `planning/current/manifest.csv` — so a roster id that manifest does not carry names a seat
    nothing will ever build, and an EMPTY roster with no manifest births a goal with no work in it
    at all. Both were pass-shaped births before this: the package was written, the owner approved,
    and what came back was a goal that could not run.
    """
    if str(pkg.get("workflow") or "").strip():
        return
    roster = list(pkg.get("roster") or [])
    manifest = Path(pkg["plan_artifacts"]) / "current" / "manifest.csv"
    if not manifest.is_file():
        raise ApprovePackageRefusal(
            "roster-not-in-plan",
            f"this package declares no --workflow, so the execution seats are the ones THE PLAN "
            f"authored and the birth mints them from {manifest} — which does not exist. Author "
            "the plan's seats (manifest.csv plus seats/<seat>/ prompt+task pairs and "
            "bindings.json) and bind them, or declare the --workflow whose catalog carries them",
        )
    with manifest.open(encoding="utf-8", newline="") as fh:
        authored = {(row.get(MANIFEST_SEAT_COLUMN) or "").strip()
                    for row in csv.DictReader(fh)}
    authored.discard("")
    if not roster:
        raise ApprovePackageRefusal(
            "roster-not-in-plan",
            f"the roster is empty and the plan authored {len(authored)} seat(s) "
            f"({', '.join(sorted(authored)) or 'none'}). A birth with no roster is a goal with no "
            "work in it — name the plan's execution seats",
        )
    absent = [s for s in roster if s not in authored]
    if absent:
        raise ApprovePackageRefusal(
            "roster-not-in-plan",
            f"roster seat(s) {', '.join(absent)} are not in {manifest} (it authors "
            f"{', '.join(sorted(authored)) or 'nothing'}). The birth mints the plan's own seats, "
            "so a roster id the plan never authored names a seat nothing builds",
        )
    # …and the other direction, because the MANIFEST is what mints. `--goal-local --root` builds
    # every row of it, not the roster — so a manifest seat the roster omits is born anyway, in a
    # goal whose declaration never mentioned it, and it is never uncast-checked (that check reads
    # the roster). `draft-plan.md`'s done contract already calls "a plan seat absent from the
    # roster" a fail; this is that contract at the door where it can still be enforced.
    unlisted = sorted(authored - set(roster))
    if unlisted:
        raise ApprovePackageRefusal(
            "roster-not-in-plan",
            f"{manifest} authors seat(s) {', '.join(unlisted)} that the roster does not name. The "
            "birth mints every manifest row, so those seats are born regardless — the roster must "
            "name the plan's whole execution team, or the manifest must not carry a seat the plan "
            "did not declare",
        )


def write_approve_package(goal_dir, **fields):
    """Write the package onto the PLANNING goal, atomically. Returns the path written."""
    pkg = build_package(**fields)
    # Both refusals need the PLANNING GOAL to resolve against, which `build_package` deliberately
    # does not take (it validates the package against what the reader consumes, and the reader
    # derives the goal folder itself). They run before any byte lands, which is all the placement
    # has to guarantee.
    refuse_bad_contract_file(goal_dir, pkg)
    refuse_roster_not_in_plan(goal_dir, pkg)
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
                    help="comma-separated seat ids of the execution roster (duplicates are refused "
                         "at birth). With no --workflow these are the seats THE PLAN authored, and "
                         "each must appear in <plan-artifacts>/current/manifest.csv")
    ap.add_argument("--contract-file", default=None,
                    help="the goal contract `scaffold --contract` receives — it becomes the born "
                         "goal's goal.md body, and it must exist under --plan-artifacts so the "
                         "bound commit carries it")
    ap.add_argument("--workflow", default=None,
                    help="the workflow the execution seats are minted from; omit it for a one-off "
                         "plan, whose seats are minted from the plan's own planning/current/")
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
