#!/usr/bin/env python3
"""Path A mint: uncast-in-sheet + supervised wrapper + one materialize argv."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from argv import PLANNING_SEATS, planning_mint_argv
from failure import CLASS_ATOMIC_CORE_REFUSAL, MaterializeFailure, ORIGIN_GATE_LANE
from wrapper import PATH_A, supervised_materialize, uncast_in_sheet

PASS_ID = "goal-wide"
ORIGIN_ID = "goal-wide-mint"


def run_path_a(*, goal_folder, catalog_root, sheet, subject, seats=None, mint=None):
    seat_names = tuple(seats) if seats is not None else PLANNING_SEATS
    argv = planning_mint_argv(
        goal_folder=goal_folder, catalog_root=catalog_root, sheet=sheet
    )

    def _uncast():
        return uncast_in_sheet(sheet, seat_names)

    def _mint():
        if mint is not None:
            mint(argv)
            return
        try:
            subprocess.run(
                [sys.executable, *argv],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            code = "materialize-refused"
            payload = exc.stdout or ""
            try:
                code = (json.loads(payload).get("refusal") or {}).get("code") or code
            except json.JSONDecodeError:
                pass
            reason = ((exc.stdout or "") + (exc.stderr or "")).strip()[:600]
            raise MaterializeFailure(
                CLASS_ATOMIC_CORE_REFUSAL, code, reason or code, subject
            ) from exc

    return supervised_materialize(
        path=PATH_A,
        goal_folder=goal_folder,
        planning_pass_id=PASS_ID,
        origin=ORIGIN_GATE_LANE,
        origin_id=ORIGIN_ID,
        subject=subject,
        validate=lambda: None,
        uncast=_uncast,
        mint=_mint,
    )


def main(argv=None):
    p = argparse.ArgumentParser(description="Path A supervised planning-seat mint.")
    p.add_argument("--package", required=True)
    p.add_argument("--catalog-root", required=True)
    p.add_argument("--sheet", required=True)
    p.add_argument("--subject", default="")
    args = p.parse_args(argv)
    subject = args.subject or Path(args.package).name
    out = run_path_a(
        goal_folder=args.package,
        catalog_root=args.catalog_root,
        sheet=args.sheet,
        subject=subject,
    )
    json.dump(
        {"ok": out["ok"], "record": out.get("record")},
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
