#!/usr/bin/env python3
"""probe-runner-grade-verdicts.py — the probe-suite row grades a BROKEN RUNNER, not just a RED one.

WHAT IS UNDER TEST (owner ruling 2026-08-11). `probe_probe_suite` alarmed on `verdict == "RED"`
alone. But the scheduled runner (`ignite/deploy/probe-suite-scheduled.py`) also grades ITSELF
broken — ERROR · COVERAGE-MISMATCH · ARTIFACT-PATH-MISMATCH · ARTIFACT-MISSING · INCOMPLETE — and
every one of those landed in the `up` branch: a run that produced NO clean grade was reported to
the owner as a healthy suite. The row now alarms on ANY verdict that is not GREEN/UNKNOWN.

FIXTURE-DRIVEN, so it runs on ANY host: a temp workspace, a hand-written latest.json with a fresh
fired_at, no systemd, no network, and nothing written under the real `.rbtv/runtime/`.

RUN IT:  python3 probes/probe-runner-grade-verdicts.py
  RBTV_WATCHDOG_TOOL_PATH=<path>  point it at another copy of the tool — this is how the red-first
  control runs it against the PRE-WIDENING watchdog.
Exit 0 = every verdict is graded as ruled. Exit 1 = a verdict is graded wrong. Exit 2 = the probe
could not run (never a pass — a probe that cannot execute has proven nothing).
"""

import importlib.util
import json
import os
import sys
import tempfile
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = os.environ.get("RBTV_WATCHDOG_TOOL_PATH") or str(HERE.parent / "tool" / "rbtv-ignite-watchdog")

try:
    # The tool is an extensionless executable, so it is loaded by path rather than imported.
    _spec = importlib.util.spec_from_loader(
        "rbtv_ignite_watchdog", SourceFileLoader("rbtv_ignite_watchdog", TOOL))
    W = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(W)
except Exception as exc:  # noqa: BLE001 — a probe that cannot import proves nothing
    print(f"INOPERATIVE: could not load the watchdog tool at {TOOL} ({exc})")
    sys.exit(2)

FAILED = []
PASSED = []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


# (verdict, extra payload fields, expected state). The extras are the REAL payload shapes the
# scheduled runner writes for each verdict — a `failed` count for RED, a `note`/`error` for the
# runner-grade-broken set, which is exactly why the RED message cannot be reused for them.
CASES = [
    ("RED", {"failed": 3}, "alarm"),
    ("ERROR", {"error": "OSError: [Errno 28] No space left on device",
               "note": "the trigger fired and failed"}, "alarm"),
    ("COVERAGE-MISMATCH", {"note": "discovered 98, excluded 2, so 96 should have run; "
                                   "the suite reports discovered=95 attempted=95"}, "alarm"),
    ("GREEN", {"passed": 96, "failed": 0}, "up"),
    ("UNKNOWN", {}, "up"),
]


def main():
    with tempfile.TemporaryDirectory(prefix="rbtv-watchdog-verdicts-") as tmp:
        latest = Path(tmp, ".rbtv", "runtime", "probe-suite", "latest.json")
        latest.parent.mkdir(parents=True)
        orig_ws = W.WORKSPACE
        W.WORKSPACE = tmp
        try:
            for verdict, extra, expected in CASES:
                payload = dict(extra, verdict=verdict,
                               # ALWAYS FRESH: the staleness branch above this one must never be
                               # what a grading case is actually measuring.
                               fired_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               stale_after_seconds=3600)
                latest.write_text(json.dumps(payload))
                state, detail = W.probe_probe_suite()
                check(f"verdict={verdict} is graded {expected}", state == expected,
                      f"got {state!r} — {detail}")
                # Only grade the MESSAGE once the state is right — the `up` branch's text also
                # happens to contain the verdict, so ungated these two would read PASS on the very
                # rows the red-first arm is failing.
                if expected == "alarm" and state == "alarm":
                    check(f"verdict={verdict} names the verdict in its alarm message",
                          verdict in detail, detail[:90])
                    check(f"verdict={verdict} alarm message carries no unresolved placeholder",
                          "None" not in detail and "%s" not in detail, detail[:90])
        finally:
            W.WORKSPACE = orig_ws

    print(f"\nCHECKS {len(PASSED)}/{len(PASSED) + len(FAILED)}")
    if FAILED:
        print("FAILED: " + "; ".join(FAILED))
        return 1
    if len(PASSED) < 11:
        print(f"INOPERATIVE: only {len(PASSED)} checks ran; this probe asserts at least 11")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
