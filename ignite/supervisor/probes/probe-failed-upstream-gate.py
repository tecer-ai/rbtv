#!/usr/bin/env python3
"""probe-failed-upstream-gate — successor held behind a failed milestone gate.

G-leader-0823-1443: readiness advanced on the predecessor's SESSION disposition (`done`)
instead of its MILESTONE VERDICT. A successor launched behind a FAIL evidence JSON.

Option (a): taskforce row declares `gate-artifact` + `gate-required`; readiness reads
that file. Sitting `done` + FAIL JSON → successor BLOCKED. Same sitting + PASS → READY.
No disposition is rewritten.

Red arm: the `if not unmet and seat in gates:` hunk, disabled, launches the successor.
"""
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COORD = HERE.parent.parent / "coord"
OUT = HERE / "probe-failed-upstream-gate.out"
FIX_ANCHOR = "if not unmet and seat in gates:"

sys.path.insert(0, str(COORD))
import coord  # noqa: E402
import ending_store  # noqa: E402
import ready  # noqa: E402

CHECKS = []
T0 = time.time()


def check(name, ok, evidence=None):
    CHECKS.append({"name": name, "pass": bool(ok), "evidence": evidence or {}})


def fixture(root, verdict):
    rec = root / ".rbtv" / "modules" / "ignite" / "server.json"
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text('{"machines": {}}\n', encoding="utf-8")
    pkg = root / ".rbtv" / "goals" / "test-failed-upstream-gate"
    for seat in ("pred", "succ"):
        (pkg / "seats" / seat).mkdir(parents=True, exist_ok=True)
        (pkg / "seats" / seat / "seat.md").write_text(
            f"---\nagent: {seat}\nmodel: opus\n---\nbrief\n", encoding="utf-8")
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    (pkg / "coordination" / "workers.md").write_text(
        "# workers\n\n| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
        "|-------|--------|-----------|------------|------------|-------------|-----------|\n",
        encoding="utf-8")
    ev = pkg / "planning" / "m4-triage-contract" / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "pred.json").write_text(
        json.dumps({"verdict": verdict}, indent=1) + "\n", encoding="utf-8")
    (pkg / "taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id,"
        "gate-artifact,gate-required\n"
        "tf,pred,,bash,probe,high,35,,,\n"
        "tf,succ,pred,bash,probe,high,35,,"
        "planning/m4-triage-contract/evidence/pred.json,verdict=PASS\n",
        encoding="utf-8")
    ending_store.stamp_seat_declare(pkg, "pred", "done", evidence="probe-failed-upstream-gate")
    return pkg


def rows_of(pkg):
    ns = type("A", (), {"package": str(pkg), "base": None, "workers_dir": None,
                        "as_agent": None, "force": False, "json": True,
                        "explain": None, "fail_on_skew": False})()
    return {r["seat"]: r for r in ready.ready_seat_rows(ns)}


root = Path(tempfile.mkdtemp(prefix="probe-failed-upstream-gate-"))
try:
    pkg = fixture(root, "FAIL")
    fail_rows = rows_of(pkg)
    check("FAIL artifact + pred done → succ not READY",
          fail_rows["succ"]["verdict"] != "READY"
          and fail_rows["succ"]["verdict"] == "BLOCKED"
          and fail_rows["pred"]["verdict"] == "DONE",
          {"succ": fail_rows["succ"]["verdict"],
           "reason": fail_rows["succ"]["reason"]})
    check("FAIL reason names the gate, not a rewritten disposition",
          "gate=" in fail_rows["succ"]["reason"]
          and "FAIL" in fail_rows["succ"]["reason"]
          and fail_rows["pred"]["disposition"] == "done",
          {"reason": fail_rows["succ"]["reason"]})

    (pkg / "planning" / "m4-triage-contract" / "evidence" / "pred.json").write_text(
        json.dumps({"verdict": "PASS"}, indent=1) + "\n", encoding="utf-8")
    pass_rows = rows_of(pkg)
    check("PASS artifact + pred done → succ READY (not a blanket freeze)",
          pass_rows["succ"]["verdict"] == "READY"
          and pass_rows["pred"]["verdict"] == "DONE",
          {"succ": pass_rows["succ"]["verdict"]})

    src = (HERE.parent / "ready.py").read_text(encoding="utf-8")
    check("FIX_ANCHOR present in ready.py", FIX_ANCHOR in src)
    (pkg / "planning" / "m4-triage-contract" / "evidence" / "pred.json").write_text(
        json.dumps({"verdict": "FAIL"}, indent=1) + "\n", encoding="utf-8")
    orig_gates = ready.taskforce_gates
    ready.taskforce_gates = lambda _pkg: {}
    try:
        red_rows = rows_of(pkg)
    finally:
        ready.taskforce_gates = orig_gates
    check("RED: skipping the gate read launches succ on FAIL (the pre-fix arithmetic)",
          red_rows["succ"]["verdict"] == "READY" and red_rows["pred"]["verdict"] == "DONE",
          {"succ": red_rows["succ"]["verdict"]})
finally:
    shutil.rmtree(root, ignore_errors=True)

failed = [c for c in CHECKS if not c["pass"]]
exit_code = 1 if failed else 0
lines = [f"{'ok  ' if c['pass'] else 'FAIL'}  {c['name']}"
         + ("" if c["pass"] else f" — {c['evidence']}") for c in CHECKS]
lines.append("")
lines.append("RESULT: PASS — successor held behind failed gate; PASS still launches"
             if exit_code == 0
             else f"RESULT: FAIL — {len(failed)} check(s): "
             + " · ".join(c["name"] for c in failed))
lines.append(f"WALL_MS {int((time.time() - T0) * 1000)}")
lines.append(f"EXIT {exit_code}")
text = "\n".join(lines) + "\n"
OUT.write_text(text, encoding="utf-8")
sys.stdout.write(text)
sys.exit(exit_code)
