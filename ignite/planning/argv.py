#!/usr/bin/env python3
"""Path A argv builder (spec-planning-door §2.1)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SEATS_FILE = _HERE / "pipeline-seats.json"
PLANNING_SEATS = tuple(json.loads(_SEATS_FILE.read_text(encoding="utf-8")))
PLANNING_WORKFLOW = "plan-console"
MATERIALIZE_PY = _HERE / "materialize-seats.py"

# `materialize-seats.py#GOAL_LOCAL_WORKFLOW` — the name of the ONE workflow manifest the
# goal-local lane synthesizes. `unbuilt-seats.js#goalLocalArgv` spells the same literal for the
# same reason: the lane is built inside the materializer, so its workflow name reaches a caller
# only as an argv value. It is paired with the flag below so the two cannot disagree.
GOAL_LOCAL_WORKFLOW = "goal-local"


def planning_mint_argv(*, goal_folder, catalog_root, sheet, workflow=PLANNING_WORKFLOW,
                       goal_local=False, creation_inputs=None):
    """One invocation, whole chain. Never --milestone-id, never --nested, never full/collapsed.

    `creation_inputs=(claude_md, budget_json)` supplies the two CALLER-SUPPLIED base texts a
    BRAND-NEW goal package needs. `plan_package_creation` refuses `create-inputs-missing` without
    them on a folder that carries no `taskforce.csv` — it "never invents run conventions and never
    defaults a floor" — so a mint into a freshly scaffolded folder (Path B's birth) must name them,
    while a mint into a goal that already has a registry (Path A) must NOT: there the option is
    read only when supplied, and supplying it would write a constitution over a goal that has one.

    `goal_local=True` mints the seats THE GOAL'S OWN PLANNING PASS AUTHORED — read from the
    package's `planning/current/` (manifest.csv plus seats/<seat>/ prompt+task pairs) instead of
    the component catalog. It FORCES the workflow name, because the lane synthesizes exactly one
    manifest and its name is not the caller's to choose: a `--goal-local` run under any other
    `--workflow` refuses `workflow-unknown` against a catalog that carries one.
    """
    if goal_local:
        workflow = GOAL_LOCAL_WORKFLOW
    argv = [
        str(MATERIALIZE_PY),
        "--package",
        str(goal_folder),
        "--workflow",
        str(workflow),
        "--catalog-root",
        str(catalog_root),
        "--root",
        "--bindings",
        str(sheet),
        "--force-partial",
        "--json",
    ]
    if goal_local:
        argv.append("--goal-local")
    if creation_inputs:
        claude_md, budget_json = creation_inputs
        argv += ["--claude-md", str(claude_md), "--budget-json", str(budget_json)]
    return argv


def main(argv=None):
    p = argparse.ArgumentParser(description="Print Path A materialize argv as JSON.")
    p.add_argument("--package", required=True)
    p.add_argument("--catalog-root", required=True)
    p.add_argument("--sheet", required=True)
    p.add_argument("--workflow", default=PLANNING_WORKFLOW)
    p.add_argument("--goal-local", action="store_true", dest="goal_local",
                   help="mint the seats the goal's own planning pass authored")
    p.add_argument("--seats-json", action="store_true", help="print PLANNING_SEATS and exit")
    args = p.parse_args(argv)
    if args.seats_json:
        json.dump(list(PLANNING_SEATS), sys.stdout)
        sys.stdout.write("\n")
        return 0
    json.dump(
        planning_mint_argv(
            goal_folder=args.package,
            catalog_root=args.catalog_root,
            sheet=args.sheet,
            workflow=args.workflow,
            goal_local=args.goal_local,
        ),
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
