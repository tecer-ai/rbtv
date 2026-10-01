#!/usr/bin/env python3
"""The red-then-green log: each probe case, once broken on purpose.

For every mutation in `mutations.py` this runs the cases that mutation is meant
to break, under both regimes, and REQUIRES them to fail. A case that stays green
under its own mutation is not testing what it claims to test, and is reported
here as UNPROVEN rather than quietly passed over.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = "test_publish_job.py"

# mutation -> the cases it must turn red
ARMS = [
    ("precheck-always-new", ["test_case_a_second_run_writes_nothing_new"]),
    ("no-discriminator", ["test_case_b_same_day_collision_concurrently"]),
    ("amend-renders-a-fresh-path", ["test_case_c_late_twin_amends_in_place"]),
    ("amend-ignores-the-key", ["test_case_c_amend_refuses_a_non_matching_key"]),
    ("push-failure-is-silent", ["test_case_d_unreachable_remote_notes_the_cause_and_keeps_the_job"]),
    ("resolve-by-discarding-the-remote", ["test_case_e_owner_line_survives"]),
    ("processed-record-before-the-push",
     ["test_case_f_killed_cycle_resumes_and_flag_is_written_last"]),
    ("transcripts-get-their-own-stem",
     ["test_transcripts_are_filed_beside_the_summary_sharing_its_stem"]),
]


def run(tests, mutation=None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("M7_MUTATION", None)
    if mutation:
        env["M7_MUTATION"] = mutation
    ids = [f"{SUITE}::{name}" for name in tests]
    return subprocess.run([sys.executable, "-m", "pytest", *ids, "-q", "--no-header", "-p",
                           "no:cacheprovider"],
                          cwd=HERE, capture_output=True, text=True, env=env)


def main() -> int:
    unproven = []
    for mutation, tests in ARMS:
        green = run(tests)
        red = run(tests, mutation)
        green_ok = green.returncode == 0
        red_ok = red.returncode != 0
        status = "PROVEN" if (green_ok and red_ok) else "UNPROVEN"
        if status == "UNPROVEN":
            unproven.append(mutation)
        print(f"{status:9} {mutation:34} green={'pass' if green_ok else 'FAIL'} "
              f"red={'fail' if red_ok else 'PASSED — the case is blind'}")
        print(f"          cases: {', '.join(tests)}")
        print(f"          red tail: {red.stdout.strip().splitlines()[-1] if red.stdout.strip() else red.stderr.strip()[:160]}")
    print()
    if unproven:
        print(f"UNPROVEN ARMS: {unproven}")
        return 1
    print(f"all {len(ARMS)} arms seen red and green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
