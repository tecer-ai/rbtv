#!/usr/bin/env python3
"""probe-watch-selftest-bounded.py — `watch.py --selftest` fails in EXACTLY four named places.

WHAT IT SCORES (task 7.575, criterion 3 — the `watch.py` half of finding A). The kit's rule is
that `watch.py --selftest` gates any edit to that file, and two probes DO assert it exits 0
(`probe-s410-revival-no-agent.py`, `probe-s412-ram-floor-refusal.py`). ⚠ BOTH OF THOSE SIT IN THE
STANDING FAILING SET, so the enforcement is MASKED, not absent: a probe that is ALREADY RED CANNOT
SIGNAL A NEW RED, and every arm in that selftest — including the three task 7.561 added and the
three task 7.578/7.575 added — could rot with nothing changing colour anywhere. This probe unmasks
it.

⚠ THE ASSERTION IS NOT `exit 0`, AND IT IS NOT LOOSENED EITHER. `watch.py --selftest` has FOUR
PRE-EXISTING failures that are neither this row's to fix nor inside its write set, so `exit 0` is
unreachable today and asserting it would just add a ninth permanently-red row — a second mask.
Asserting "no more failures than today" by COUNT would be the loosening the row forbids: a count
survives a fixed arm being swapped for a broken one. So the bar is the FAILING SET BY NAME. A
fifth failure reds. A different failure reds. A named exclusion that stops failing reds too — a
stale exclusion is how a bounded set silently becomes an unbounded one.

THE FOUR EXCLUSIONS, each already diagnosed (evidence `build/subagent-closeout/evidence/w7561/
w7561-10-*`; do NOT re-diagnose them):
  · `7.164 (5)`, `7.164 (5b)`, `7.164 (5c)` — the owner-door arms. Proven PRE-EXISTING by running
    a `git show HEAD:` copy of the file, which failed the same three byte-identically, so they
    predate every recent row and belong to task 7.164's own unfinished work.
  · `s4-07 (4)` — `floor-lint.py` exits 1 on a literal in `materialize-seats.py:4187`. That is a
    DIFFERENT FILE, outside watch.py's write set, and the arm's own text says the exit code is
    reported so it is not read as this arm's.

ARMS
  R1  the FAILING SET matches the four names EXACTLY — no extra, no missing, one match each.
  R2  it is NOT VACUOUS: at least ARM_FLOOR verdict rows are printed. A selftest whose body was
      deleted would emit an empty failing set and satisfy R1 alone.
  R3  the arm families that the masking hid are still present by label — the 7.561 session arms
      and the 7.575/7.578 arms this row added. A selftest can be gutted one arm at a time without
      the failing set or the count ever moving.

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP. A missing or unstartable `watch.py` FAILS
(exit 1). INOPERATIVE (exit 2) is for the probe being unable to run at all.

RED-FIRST PROOF: `1-projects/rbtv-sb-merge-refactor-core-build/build/subagent-closeout/evidence/
w7575-7578/06-*`, `07-*`, `08-*` — three scratch-tree mutants (quoting reverted; the retired role
restored in the wake line; a retired role reintroduced into an unrelated `Flag()`), each producing
a failing label the control run does not have, i.e. each reds this probe.

⚠⚠ DELETE THIS PROBE IN THE SAME CHANGE AS `watch.py` — task 7.35 (dissolve `watch.py`) is OPEN,
unblocked (7.32 and 7.33 are done) and unscheduled. This probe's whole subject is that file's
selftest, so once 7.35 deletes it this probe FAILS loudly on an absent target — which is the right
failure mode for an accident and pure noise for a deliberate deletion. 7.35's executor: remove this
file, do not "fix" it. Nothing else here outlives `watch.py`; the retired-role guard it scores
lives inside `watch.py` itself and goes with it.

Run it through the suite — `node ignite/deploy/probe-suite.js --only watch-selftest-bounded` —
never by hand (`G-163`).
Exit 0 = the failing set is exactly the four named · 1 = it is not, or the selftest is gutted or
absent · 2 = INOPERATIVE.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "watch.py"
OUT = HERE / "probe-watch-selftest-bounded.out"

# The four excluded failures, keyed on the stable identifier each arm's own label opens with.
KNOWN_FAILURES = ("7.164 (5)", "7.164 (5b)", "7.164 (5c)", "s4-07 (4)")
# The count the selftest carried at 2026-08-09 (task 7.575). Additions never red it; removals do.
ARM_FLOOR = 314
REQUIRED_FAMILIES = (
    "7.561 THE REMEDY CARRIES `--session`",
    "7.561 CONTROL:",
    "7.575 (B) THE WAKE ADDRESSES NO RETIRED ROLE",
    "7.575 (B) RETIRED ROLE:",
    "7.578 TEXT PATH:",
    "7.578 CONTROL:",
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
        check("R1", False, f"{TARGET} does not exist — an absent target is the failure, not a skip")
        return
    t0 = time.time()
    try:
        res = subprocess.run([sys.executable, "-B", str(TARGET), "--selftest"],
                             capture_output=True, text=True, timeout=150)
    except OSError as exc:
        stop("R1", f"could not start {TARGET}: {type(exc).__name__}: {exc}")
        return
    except subprocess.TimeoutExpired:
        check("R1", False, "the selftest did not finish within 150s")
        return
    out = res.stdout + res.stderr
    say(f"ran {TARGET} --selftest in {time.time() - t0:.1f}s, exit={res.returncode}")

    # ⚠ ENUMERATED BY VERDICT PREFIX, never by grepping the word FAIL: the fixture stubs print
    # lines like `wake FAILED -> alpha (%1): stub`, which a naive grep counts as failures.
    reds = [l[len("FAIL  "):] for l in out.splitlines() if l.startswith("FAIL  ")]
    arms = [l for l in out.splitlines() if l.startswith("ok    ") or l.startswith("FAIL  ")]

    matched = {k: [i for i, r in enumerate(reds) if k in r] for k in KNOWN_FAILURES}
    stale = [k for k, v in matched.items() if not v]
    ambiguous = [k for k, v in matched.items() if len(v) > 1]
    claimed = {i for v in matched.values() for i in v}
    unexpected = [r[:110] for i, r in enumerate(reds) if i not in claimed]
    check("R1", not stale and not ambiguous and not unexpected,
          f"{len(reds)} failing arm(s); NEW/unexpected={unexpected}; "
          f"exclusions that no longer fire (delete them)={stale}; "
          f"exclusions matching >1 arm={ambiguous}")

    check("R2", len(arms) >= ARM_FLOOR,
          f"{len(arms)} verdict rows printed (floor {ARM_FLOOR} — a gutted selftest emits an "
          f"empty failing set and would satisfy R1 alone)")

    missing = [f for f in REQUIRED_FAMILIES if not any(f in a for a in arms)]
    check("R3", not missing, f"every named arm family present; missing={missing}")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-watch-selftest-bounded  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
