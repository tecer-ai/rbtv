#!/usr/bin/env python3
"""probe-goal-watcher-delivery-retry.py — the dedup state records DELIVERY, never INTENT.

WHAT IT SCORES (task 7.536). `goal-watcher-job.py` armed its per-episode dedup state BEFORE it
knew whether `deliver()` had sent anything, so a coord outage looked exactly like a seat ignoring
its nudge: the row stayed armed, was never retried inside the episode, and the escalation ladder
advanced on a nudge that may never have arrived. The fix arms a key only once delivery is known,
bounded by `DELIVER_RETRIES` so an unreachable coord cannot become a nudge storm.

EVERYTHING RUNS AGAINST A FIXTURE PACKAGE IN A SCRATCH DIR, with a STUB `coord.py` whose
`cmd_send` either raises `SystemExit(3)` (the refusal a real coord raises) or appends to a log.
No live package's coordination folder is read or written, and no real coord is invoked.

ARMS
  R1  RED ARM — with delivery FAILING, pass 1 leaves the episode RETRYABLE: the on-disk
      `goal-watcher-state.json` carries NO armed entry for the flag, and `_undelivered` counts 1.
      Read back FROM DISK, never from the job's stdout — the file is what the next pass reads.
  R2  the NEXT pass RE-NUDGES: pass 2 emits the same key as new and attempts delivery again
      (`_undelivered` -> 2). This is the behaviour the pre-fix code cannot produce.
  R3  BOUNDED — pass 3 reaches DELIVER_RETRIES and arms the key anyway (the failure stands on the
      record), and pass 4 attempts NO delivery. Without this the fix would be a nudge storm.
  R4  CONTROL — with delivery SUCCEEDING, the key IS armed on disk after pass 1 and pass 2 sends
      nothing. The fix must not turn dedup off; a probe that only proves the retry is half a proof.
  R5  BACKWARD COMPATIBLE — a REAL `goal-watcher-state.json` written by this job in an earlier
      build (schema: bare armed keys + `_repeat` + `_swap_history`, no `_undelivered`) is COPIED
      to scratch and loaded without error, its underscore keys survive, and the ORIGINAL is
      byte-identical afterwards (sha256 before/after).

RED-FIRST PROOF: run this probe against a scratch copy of `goal-watcher-job.py` with the 7.536
hunk reverted (`git show HEAD:ignite/jobs/goal-watcher-job.py`) via RBTV_PROBE_GWJ — R1/R2/R3
fail, R4/R5 pass. The env override exists for that A/B and defaults to the shipped file.

Run it through the suite — `node ignite/deploy/probe-suite.js --only goal-watcher-delivery-retry`
— never by hand (`G-163`).
Exit 0 = green · 1 = the retry contract is broken · 2 = INOPERATIVE.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TARGET = Path(os.environ.get("RBTV_PROBE_GWJ") or (HERE.parent / "goal-watcher-job.py"))
OUT = HERE / "probe-goal-watcher-delivery-retry.out"
# A state file this job WROTE in an earlier build — the pre-`_undelivered` schema, on disk, not
# synthesised here. Copied to scratch and never mutated in place.
REAL_STATE = (HERE.parents[5] / "1-projects/rbtv-sb-merge-refactor-core-build/build"
              / "subagent-closeout/evidence/b2/fixture/row-context/coordination"
              / "goal-watcher-state.json")

STUB_COORD = '''"""Stub coord for probe-goal-watcher-delivery-retry — cmd_send only."""
import os


def cmd_send(ns):
    if os.environ.get("PROBE_COORD_FAIL") == "1":
        raise SystemExit(3)
    with open(os.environ["PROBE_COORD_LOG"], "a", encoding="utf-8") as fh:
        fh.write(f"{ns.to}|{ns.message.splitlines()[0]}\\n")
'''

lines, failures, inoperative = [], [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def stop(tag, detail):
    say(f"INOP  {tag}  {detail}")
    inoperative.append(tag)


def make_fixture(root, name):
    pkg = root / name
    (pkg / "coordination").mkdir(parents=True)
    kit = root / f"{name}-kit"
    kit.mkdir()
    (kit / "coord.py").write_text(STUB_COORD, encoding="utf-8")
    return pkg, kit / "coord.py"


def snapshot(pkg):
    """A FRESH snapshot whose only condition is the run stall — one leader-addressed row."""
    now = time.time()
    (pkg / "state.json").write_text(json.dumps({
        "captured_at": now,
        "captured_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
        "seats": [{"seat": "leader", "pane": "%0", "liveness": "live", "harness_pid": 1,
                   "roster_active": True}],
        "roster_absent": [], "headless": [],
        "headless_source": {"readable": True, "reason": ""},
        "run": {"ready_rows": 1, "live_executors": 0, "queued": 0,
                "source": {"ready_rows": "", "queued": {"reason": ""}}},
    }), encoding="utf-8")


def run_pass(pkg, coord, fail, log, state_file=None):
    snapshot(pkg)
    env = dict(os.environ, PROBE_COORD_FAIL="1" if fail else "0", PROBE_COORD_LOG=str(log))
    cmd = [sys.executable, "-B", str(TARGET), "--package", str(pkg), "--room-package", str(pkg),
           "--coord", str(coord), "--notify", "--mem-floor-mb", "2000", "--json",
           "--reflag-min", "0"]
    if state_file:
        cmd += ["--state-file", str(state_file)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
    out = res.stdout + res.stderr
    try:
        blob = json.loads(res.stdout[res.stdout.index("{\n \"layer\""):])
    except (ValueError, json.JSONDecodeError):
        blob = {}
    state_path = Path(state_file) if state_file else pkg / "coordination" / "goal-watcher-state.json"
    try:
        disk = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        disk = {}
    return res.returncode, out, blob, disk


def main():
    if not TARGET.exists():
        check("R1", False, f"{TARGET} does not exist — the job carrying the contract is gone")
        return
    root = Path(tempfile.mkdtemp(prefix="probe-gwj-retry-"))
    try:
        # ---- R1/R2/R3: delivery FAILS
        pkg, coord = make_fixture(root, "red")
        log = root / "red.log"
        rc1, out1, j1, d1 = run_pass(pkg, coord, True, log)
        keys = j1.get("new") or []
        undel = j1.get("undelivered") or []
        armed1 = [k for k in keys if d1.get(k)]
        say(f"pass1 exit={rc1} new={keys} undelivered={undel} disk={ {k: v for k, v in d1.items()} }")
        check("R1", bool(keys) and undel == sorted(keys) and not armed1
              and d1.get("_undelivered") == {k: 1 for k in keys},
              f"a FAILED delivery left the episode retryable ON DISK: armed={armed1}, "
              f"_undelivered={d1.get('_undelivered')}")

        rc2, out2, j2, d2 = run_pass(pkg, coord, True, log)
        check("R2", (j2.get("new") or []) == keys and (j2.get("delivery_failed") or 0) >= 1
              and d2.get("_undelivered") == {k: 2 for k in keys},
              f"the NEXT pass RE-NUDGED: new={j2.get('new')} "
              f"delivery_failed={j2.get('delivery_failed')} _undelivered={d2.get('_undelivered')}")

        rc3, out3, j3, d3 = run_pass(pkg, coord, True, log)
        rc4, out4, j4, d4 = run_pass(pkg, coord, True, log)
        check("R3", all(d3.get(k) for k in keys) and "retry bound reached" in out3
              and (j4.get("new") or []) == [] and (j4.get("delivery_failed") or 0) == 0
              and not log.exists(),
              f"BOUNDED at {j3.get('retry_bound')}: pass3 armed the key(s) and pass4 attempted "
              f"nothing (new={j4.get('new')}, failed={j4.get('delivery_failed')})")

        # ---- R4: CONTROL — delivery SUCCEEDS
        pkg2, coord2 = make_fixture(root, "green")
        log2 = root / "green.log"
        rcA, outA, jA, dA = run_pass(pkg2, coord2, False, log2)
        sentA = jA.get("delivered") or 0
        linesA = log2.read_text(encoding="utf-8").splitlines() if log2.exists() else []
        rcB, outB, jB, dB = run_pass(pkg2, coord2, False, log2)
        linesB = log2.read_text(encoding="utf-8").splitlines() if log2.exists() else []
        check("R4", sentA >= 1 and all(dA.get(k) for k in (jA.get("new") or []))
              and dA.get("_undelivered") == {} and (jB.get("new") or []) == []
              and len(linesB) == len(linesA),
              f"a SUCCESSFUL delivery is still deduped: sent={sentA}, armed on disk, pass2 "
              f"new={jB.get('new')} and the coord log stayed at {len(linesB)} line(s)")

        # ---- R5: BACKWARD COMPATIBLE on a real state file
        if not REAL_STATE.exists():
            stop("R5", f"no real state file at {REAL_STATE}")
        else:
            before = hashlib.sha256(REAL_STATE.read_bytes()).hexdigest()
            copy = root / "real-goal-watcher-state.json"
            shutil.copy2(REAL_STATE, copy)
            original = json.loads(copy.read_text(encoding="utf-8"))
            pkg3, coord3 = make_fixture(root, "compat")
            rcC, outC, jC, dC = run_pass(pkg3, coord3, False, root / "compat.log", state_file=copy)
            after = hashlib.sha256(REAL_STATE.read_bytes()).hexdigest()
            # `_swap_history` is the READ-PROOF: it can only be in the written state because the
            # old file was loaded. `_repeat` is deliberately NOT asserted equal — the job
            # recomputes it from the pass's own conditions, which is pre-existing behaviour.
            check("R5", "Traceback" not in outC and rcC == 0 and bool(jC)
                  and dC.get("_swap_history") == original.get("_swap_history")
                  and "_undelivered" in dC and before == after,
                  f"a pre-`_undelivered` real state file loaded clean (exit={rcC}), its "
                  f"`_swap_history` survived the round trip, the new key was added, and the "
                  f"original is byte-identical (sha256 {before[:12]} == {after[:12]})")
    finally:
        shutil.rmtree(root, ignore_errors=True)


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-goal-watcher-delivery-retry  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
