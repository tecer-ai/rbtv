#!/usr/bin/env python3
"""probe-g158-stale-code — does anything notice a source file changing UNDER a running loop?

REPOINTED BY TASK 7.35 (Phase B). It used to score `watch.py`'s import-time fingerprint. That file
is retired and the exposure did NOT retire with it — it MOVED. `goal-watcher-job` is per-fire and
re-imports on every fire, so it needs no marker at all; `team_monitor.cmd_run` is now the system's
ONLY `while True:` single-process loop, and python binds module source at import, so an edit to it
or to `coord.py` never reaches a running sensor. The loop keeps writing snapshots that are
indistinguishable from a correct run. Three long-lived processes ran stale code inside one hour on
2026-07-27 and every one was caught by hand, comparing a start time against a commit time.

WHAT IT PROVES, and why a selftest cannot. The decision this fix turns on is on the WRITER side —
the fingerprint is captured ONCE and never recomputed. Only changing a file AFTER that capture can
tell the two designs apart, and the wrong one is the one a reasonable person writes:

  arm A (the shipped fix)  — must DETECT the change
  arm B (the mutation)     — recomputes the fingerprint at stamp time, and must FAIL to detect it,
                             because hashing a file against itself can never disagree. It reports a
                             healthy loop over the exact defect: a green harness in the fix for the
                             green-harness class.

A probe that only ran arm A would pass just as happily over a detector that can never fire.

⚠ THE FILE IT MUTATES IS NOT THE MODULE UNDER TEST, and that is the point. A watch.py-only marker
read CURRENT throughout the 2026-07-27 drift because the file that moved was `coord.py`. So the
mutation lands on the SENSOR ENGINE the loop imports by path — a second file, in a second custody
directory — which only a `sys.modules`-derived fingerprint can cover.

HERMETIC BY CONSTRUCTION, and this is a safety property, not tidiness. The experiment MUTATES
source, so it builds a throwaway tree mirroring the repo's layout and does every write there. It
never writes inside the tree it was launched from.

  python3 probes/probe-g158-stale-code.py    # exit 0 = the detector discriminates
Exit 0 = green · 1 = the detector does not discriminate · 2 = INOPERATIVE.
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"
ENGINE = ROOT / "orchestration" / "cli" / "ctx-monitor" / "ctx_monitor.py"
OUT = HERE / "probe-g158-stale-code.out"

lines, failures, inoperative = [], [], []


def check(tag, ok, detail):
    lines.append(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def stop(tag, detail):
    lines.append(f"INOP  {tag}  {detail}")
    inoperative.append(tag)


def main():
    if not TARGET.exists() or not ENGINE.exists():
        # NOT a skip: the target's absence IS a failure of the property under test.
        check("C0", False, f"missing {TARGET if not TARGET.exists() else ENGINE}")
        return

    tmp = Path(tempfile.mkdtemp(prefix="g158-tm-"))
    try:
        tm_dir = tmp / "orchestration" / "cli" / "team-monitor"
        eng_dir = tmp / "orchestration" / "cli" / "ctx-monitor"
        tm_dir.mkdir(parents=True)
        eng_dir.mkdir(parents=True)
        shutil.copy2(TARGET, tm_dir / "team_monitor.py")
        shutil.copy2(ENGINE, eng_dir / "ctx_monitor.py")

        spec = importlib.util.spec_from_file_location("tm_g158", tm_dir / "team_monitor.py")
        tm = importlib.util.module_from_spec(spec)
        sys.modules["tm_g158"] = tm
        spec.loader.exec_module(tm)

        if not hasattr(tm, "code_state") or not hasattr(tm, "loaded_code_fingerprint"):
            check("C0", False, "this tree's sensor carries NO loaded-code fingerprint — a "
                               "long-lived loop running stale code is undetectable from outside, "
                               "which is G-158 itself")
            return

        # The loop's own import surface: the engine is reached by path, so it enters `sys.modules`
        # only once the sensor has actually used it — which is why the capture is at first use.
        tm.sensor()
        before = tm.code_state()
        covered = sorted(Path(p).name for p in before["files"])
        check("C0", before["known"] is True and "ctx_monitor.py" in covered
              and "team_monitor.py" in covered,
              f"the fingerprint is DERIVED from what this process loaded and covers more than "
              f"the module itself: {covered}")

        # The moment the defect models: a fix lands while the process is running. Python bound the
        # source at import, so this process can never pick it up — it just keeps capturing.
        engine_copy = eng_dir / "ctx_monitor.py"
        engine_copy.write_bytes(engine_copy.read_bytes()
                                + b"\n# a fix landed while this process was running\n")

        a = tm.code_state()                       # arm A — the shipped fix
        tm._LOADED_CODE = None                    # arm B — recompute the fingerprint at stamp time
        b = tm.code_state()

        a_detects = a["known"] is True and "ctx_monitor.py" in a["drifted"]
        b_detects = bool(b["drifted"])
        check("A-FIX", a_detects,
              f"a file changed UNDER the running process is detected: known={a['known']} "
              f"drifted={a['drifted']}")
        check("B-MUTATION", not b_detects,
              f"the recompute-at-stamp design detects NOTHING (drifted={b['drifted']}) — hashing "
              f"a file against itself can never disagree, so this arm is what makes A a "
              f"measurement rather than a restatement")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-g158-stale-code  ({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
