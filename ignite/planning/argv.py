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
PLANNING_WORKFLOW = "planning"
MATERIALIZE_PY = _HERE.parent / "team-kit" / "materialize-seats.py"


def planning_mint_argv(*, goal_folder, catalog_root, sheet, workflow=PLANNING_WORKFLOW):
    """One invocation, whole chain. Never --milestone-id, never --nested, never full/collapsed."""
    return [
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


def main(argv=None):
    p = argparse.ArgumentParser(description="Print Path A materialize argv as JSON.")
    p.add_argument("--package", required=True)
    p.add_argument("--catalog-root", required=True)
    p.add_argument("--sheet", required=True)
    p.add_argument("--workflow", default=PLANNING_WORKFLOW)
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
        ),
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
