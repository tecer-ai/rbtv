#!/usr/bin/env python3
"""probe-edge-runner-selftest.py — `edge-runner-job.py --selftest` is GREEN, and still has teeth.

WHAT IT SCORES (task 7.739). `edge-runner-job.py` carries by far the largest `--selftest` in
`jobs/` — the disposition grading table, the refusal discipline, the readiness predicate and its
agreement with `coord.ready_seat_rows`, the guard evaluator, STEP 4's enqueue bar, STEP 4a's
declared-output admission, and the check-out fast path's arming. **NOTHING IN THE PROBE SUITE RAN
IT.** The suite enumerates every probe beside every component, and not one of them invoked this
target's `--selftest`, so every arm above could rot — be deleted, be inverted, or stop being
reached — and no suite run would notice. 7.739 rebuilt `verify()` around coord's ONE reader and
added its checks to that same unrun selftest; without this probe the new coverage would have landed
exactly where the old coverage already was, which is nowhere. That is the state this probe ends.

⚠ IT IS ITS OWN PROBE, and deliberately scores NOTHING but this one selftest. The sibling
`probe-goal-watcher-selftest.py` states the reason in full: coupling two selftests masks the clean
one behind a red that has nothing to do with it, which is the exact masking that let this target go
unrun while the folder looked covered.

ARMS
  R1  the selftest EXITS 0 **and printed no `FAIL` row**. Both halves, because a selftest that
      swallows its tally exits 0 with the failures still on screen — an exit-code-only R1 calls
      that GREEN while naming the failing check in its own detail string.
  R2  it is NOT VACUOUS — it prints at least CHECK_FLOOR verdict rows. An exit-0 selftest whose
      check list was emptied would pass R1 alone; this is what makes R1 a check. The floor is the
      count the selftest carried when this probe was written: erosion is precisely what this probe
      exists to catch, so a deliberate removal updates the number in the SAME change. Additions
      never red it.
  R3  the named CHECKS are all still present by label. A selftest can be gutted one check at a time
      without ever dropping below a count floor; these are the ones whose silent loss would reopen
      a defect that was measured and closed.
  R4  it says so IN ITS OWN VOICE — the terminal `N/M checks passed` tally. A run that dies
      part-way and still exits 0 (an `except SystemExit` swallowing, a truncated stream) is caught
      here and nowhere else.

⚠ THE VENUE IS THE VPS, AND THIS PROBE IS RED ON A WINDOWS CLONE BY CONSTRUCTION. The target's
`catalogue-entry-drives-parser` check asserts that the `edge-runner` catalogue entry's argv in
`config/spawn-profiles.yaml` names the target file, and that argv is the VPS absolute path
(`/home/henri/ht-wkdir/...`). On a Windows clone it cannot match, so R1 reds. **NO VENUE CARVE-OUT
IS CODED FOR IT**, and that is a decision, not an omission: an exemption keyed on a platform is
exactly how a genuine failure gets waved through on the box where it matters. Read a Windows red
against this one named check before treating it as a defect.

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP. If `edge-runner-job.py` is missing or will not
start, this probe FAILS (exit 1) — it does not report INOPERATIVE. INOPERATIVE (exit 2) is for the
probe being unable to run AT ALL (no interpreter, the probe itself crashed).

RED-FIRST PROOF: the target's own pre-7.739 tree. With the caged-check-out fixture seat added and
`verify()` still short-circuiting on its private `ended_rows` scan, the selftest exited 1 with five
FAIL rows (`dispositions`, `readiness-verdicts`, `agrees-with-coord-ready-seats`,
`enqueue-excludes-self-marked`, `seed-carries-pred-outputs`) — R1 reds on both halves there, so
this probe fails on a broken target rather than only passing on today's.

Run it through the suite — `node ignite/deploy/probe-suite.js --only edge-runner-selftest` —
never by hand (`G-163`).
Exit 0 = green · 1 = the selftest is red, gutted, or absent · 2 = INOPERATIVE.
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "edge-runner-job.py"
OUT = HERE / "probe-edge-runner-selftest.out"

# The count the selftest carried at 2026-08-11 (task 7.739, which added `mark-never-outruns-coord-
# reader` in place of the retired `scan-agrees-with-coord-reader`). RAISED IN THE SAME CHANGE that
# adds checks, or the new coverage is deletable without reddening anything. See R2.
CHECK_FLOOR = 49

# Verdict rows are printed as `  %-32s %s  %s` — two leading spaces, the check name, then PASS or
# FAIL. Anchored so a detail string that merely CONTAINS the word `FAIL` cannot be counted as one.
ROW = re.compile(r"^  (\S+)\s+(PASS|FAIL)\s+(.*)$")

# Checks whose disappearance is a silent loss of coverage. Each names a guard whose failure mode is
# invisible without it.
REQUIRED_CHECKS = (
    # The discriminating control over the whole grading table — the check that says `done` means
    # done. Everything else in the file is downstream of it.
    "dispositions",
    # The refusal discipline. Its loss is how an undecidable seat starts taking a default, which is
    # how a false `done` is born.
    "refusal-is-explicit",
    "evidence-is-per-seat",
    # 7.739 — THE ONE-DIRECTIONAL INVARIANT, successor to `scan-agrees-with-coord-reader`. It is the
    # only thing asserting this stage never marks a seat coord's reader said nothing about, and
    # never marks `done` where the reader did not say exactly `done`. Its loss reopens the defect
    # 7.739 closed, silently, because every OTHER check would still pass on a stage that invented
    # an ending.
    "mark-never-outruns-coord-reader",
    # Rule 14 — a pass writes no status column anywhere.
    "no-status-column-written",
    # The readiness predicate and its agreement with coord's. Two readers of one graph that disagree
    # is G-301, the defect class the whole file is bounded against.
    "readiness-verdicts",
    "agrees-with-coord-ready-seats",
    # The leader's bar: a ready seat carrying a terminal mark must never be relaunched.
    "enqueue-excludes-self-marked",
    # `done` is the only value that reaches the check-out fast path's door.
    "fastpath-only-done-advances",
    # STEP 4a's declared-output admission rule, whose undecided cases must REFUSE rather than admit.
    "admission-truth-table",
)

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


def main():
    if not TARGET.exists():
        # ⚠ NOT a skip: the target's absence IS the condition this probe scores.
        check("R1", False, f"{TARGET} does not exist — the selftest cannot be green if the file "
                           f"carrying it is gone")
        return
    t0 = time.time()
    try:
        res = subprocess.run([sys.executable, "-B", str(TARGET), "--selftest"],
                             capture_output=True, text=True, timeout=300)
    except OSError as exc:
        stop("R1", f"could not start {TARGET}: {type(exc).__name__}: {exc}")
        return
    except subprocess.TimeoutExpired:
        check("R1", False, "the selftest did not finish within 300s")
        return
    out = res.stdout + res.stderr
    say(f"ran {TARGET} --selftest in {time.time() - t0:.1f}s, exit={res.returncode}")

    rows = [ROW.match(l) for l in out.splitlines()]
    rows = [m for m in rows if m]
    reds = [f"{m.group(1)}: {m.group(3)[:120]}" for m in rows if m.group(2) == "FAIL"]

    # ⚠ EXIT CODE **AND** THE PRINTED ROWS, never the exit code alone. A selftest that swallows its
    # own failures — a cleared counter, an `except` around the tally — exits 0 while still printing
    # FAIL rows, and an exit-code-only R1 would report GREEN while this very detail string names the
    # failing check.
    check("R1", res.returncode == 0 and not reds,
          f"exit={res.returncode}"
          + (f"; {len(reds)} failing check(s) PRINTED: {reds[:3]}" if reds else "; no FAIL rows"))

    check("R2", len(rows) >= CHECK_FLOOR,
          f"{len(rows)} verdict rows printed (floor {CHECK_FLOOR} — a selftest that exits 0 with "
          f"its check list emptied passes R1 and fails here)")

    names = {m.group(1) for m in rows}
    missing = [c for c in REQUIRED_CHECKS if c not in names]
    check("R3", not missing, f"every named check present; missing={missing}")

    check("R4", re.search(r"^\d+/\d+ checks passed$", out, re.M) is not None,
          "the selftest reports its own tally line (a run that dies part-way and still exits 0 is "
          "caught here)")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-edge-runner-selftest  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
