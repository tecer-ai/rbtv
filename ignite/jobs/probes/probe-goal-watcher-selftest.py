#!/usr/bin/env python3
"""probe-goal-watcher-selftest.py — `goal-watcher-job.py --selftest` is GREEN, and still has teeth.

WHAT IT SCORES (task 7.575, finding A's cheap half). `goal-watcher-job.py` carries a `--selftest`
covering the pure predicates a reader cannot verify by reading — the stall predicate's null
discipline, the per-decision recipient chain, `run_inline`'s exec allowlist, the retired-role
absence, and (task 7.578) the remedy TEXT's shell-safety. NOTHING RAN IT. The whole file had
exactly one probe touching it and that probe never invoked `--selftest`, so every one of those
arms could rot — be deleted, be inverted, or stop being reached — and no suite run would notice.
That is the state this probe ends.

⚠ IT WIRES CLEAN, WHICH IS WHY IT IS ITS OWN PROBE. The selftest EXITS 0 TODAY. The sibling half
of 7.575 (`watch.py`'s selftest, which has four pre-existing failures) is deliberately NOT scored
here: coupling the two would mask this one behind a red that has nothing to do with it — the same
masking that hid the `watch.py` enforcement in the first place. `watch.py`'s bounded-failure
enforcement lives in `team-kit/probes/probe-watch-selftest-bounded.py`.

ARMS
  R1  the selftest EXITS 0 **and printed no `[FAIL]` row**. Both halves, because a selftest that
      swallows its tally exits 0 with the failures still on screen — an exit-code-only R1 calls
      that GREEN while naming the failing arm in its own detail string.
  R2  it is NOT VACUOUS — it prints at least ARM_FLOOR verdict rows. An exit-0 selftest whose body
      was deleted would pass R1 alone; this is what makes R1 a check. The floor is the count the
      selftest carried when this probe was written: erosion is precisely what this probe exists to
      catch, so a deliberate removal updates the number in the SAME change. Additions never red it.
  R3  the named ARM FAMILIES are all still present by label. A selftest can be gutted one arm at a
      time without ever dropping below a count floor; these are the families whose silent loss the
      row was filed over.
  R4  it says so IN ITS OWN VOICE — the terminal `selftest: all green` line. A run that dies
      part-way and still exits 0 (an `except SystemExit` swallowing, a truncated stream) is caught
      here and nowhere else.

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP. If `goal-watcher-job.py` is missing or will not
start, this probe FAILS (exit 1) — it does not report INOPERATIVE. INOPERATIVE (exit 2) is for the
probe being unable to run AT ALL (no `python3`, the probe itself crashed).

RED-FIRST PROOF: `1-projects/rbtv-sb-merge-refactor-core-build/build/subagent-closeout/evidence/
w7575-7578/04-gwj-redfirst-unquoted.out` — a scratch copy with the 7.578 renderer reverted exits 1
with one FAIL, so this probe reds on a broken arm rather than only passing today.

Run it through the suite — `node ignite/deploy/probe-suite.js --only goal-watcher-selftest` —
never by hand (`G-163`).
Exit 0 = green · 1 = the selftest is red, gutted, or absent · 2 = INOPERATIVE.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "goal-watcher-job.py"
OUT = HERE / "probe-goal-watcher-selftest.out"

# The count the selftest carried at 2026-08-09 (task 7.575, raised 29 -> 35 by task 7.590's six
# arms, 35 -> 45 by task 7.601's ten — the floor is RAISED IN THE SAME CHANGE that adds arms, or
# the new coverage is deletable without reddening anything). See R2.
ARM_FLOOR = 45
# Label prefixes whose disappearance is a silent loss of coverage. Each names a guard whose
# failure mode is invisible without it — the two 7.578 rows are the text/exec split the row was
# filed over, and RETIRED ROLE is the AST scan that makes `d-watcher-deterministic-chain`
# enforceable rather than documented.
REQUIRED_FAMILIES = (
    "STALL:",
    "CONTEXT:",
    "ESCALATION:",
    "EXEC ALLOWLIST:",
    "RETIRED ROLE:",
    "7.578 TEXT PATH:",
    "7.578 EXEC PATH UNCHANGED:",
    # Task 7.590 — the SAME text/exec split at the two sites 7.578's criterion did not word. The
    # two TEXT PATH arms are the guards; CALL SITE is the guard-vacuity closer (a renderer nothing
    # calls would pass the TEXT PATH arm alone); EXEC PATH UNCHANGED asserts the path that must
    # NOT move. Named individually rather than by a bare `7.590` prefix, so losing FIVE of the six
    # cannot still satisfy this check.
    "7.590 TEXT PATH (package):",
    "7.590 TEXT PATH (goal name):",
    "7.590 CALL SITE (goal name):",
    "7.590 EXEC PATH UNCHANGED:",
    # Task 7.601 — the SAME split at the seven remedy strings that append a SEAT NAME. Six arms
    # reach six sites through `evaluate`'s real decisions; CENSUS closes the seventh (`COMPLETED`
    # needs a taskforce.csv the selftest has no package for) off the file's own AST and is the
    # only arm that covers a site no fixture can reach — losing it silently reopens that site.
    # CONTROL is what makes the six measurements rather than restatements, and EXEC PATH UNCHANGED
    # asserts the argv that must NOT move. Named individually, per the 7.590 precedent: a bare
    # `7.601` prefix would still be satisfied after losing eight of the nine.
    "7.601 TEXT PATH (DEAD):",
    "7.601 TEXT PATH (GHOSTROW):",
    "7.601 TEXT PATH (APPROVAL):",
    "7.601 TEXT PATH (CONTEXT):",
    "7.601 TEXT PATH (QUIET-ESCALATED):",
    "7.601 TEXT PATH (CONTEXT-ESCALATED):",
    "7.601 CONTROL:",
    "7.601 CENSUS:",
    "7.601 EXEC PATH UNCHANGED:",
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
                             capture_output=True, text=True, timeout=120)
    except OSError as exc:
        stop("R1", f"could not start {TARGET}: {type(exc).__name__}: {exc}")
        return
    except subprocess.TimeoutExpired:
        check("R1", False, "the selftest did not finish within 120s")
        return
    out = res.stdout + res.stderr
    say(f"ran {TARGET} --selftest in {time.time() - t0:.1f}s, exit={res.returncode}")

    # ⚠ EXIT CODE **AND** THE PRINTED ROWS, never the exit code alone (§2 review, 2026-08-09). A
    # selftest that swallows its own failures — `fails.clear()` before the verdict print, an
    # `except` around the tally — exits 0 while still printing `[FAIL]` rows, and an exit-code-only
    # R1 reports GREEN while this very detail string names the failing arm. Driven, not reasoned:
    # a mutant with the 7.578 renderer reverted AND the tally cleared passed all four arms
    # (`evidence/w7575-7578-review/r12-probeA-masked-failure-mutant.out`).
    reds = [l for l in out.splitlines() if l.startswith("  [FAIL]")]
    check("R1", res.returncode == 0 and not reds,
          f"exit={res.returncode}"
          + (f"; {len(reds)} failing arm(s) PRINTED: {reds[:3]}" if reds else "; no [FAIL] rows"))

    arms = [l for l in out.splitlines() if l.startswith("  [ok ]") or l.startswith("  [FAIL]")]
    check("R2", len(arms) >= ARM_FLOOR,
          f"{len(arms)} verdict rows printed (floor {ARM_FLOOR} — a selftest that exits 0 with "
          f"its body deleted passes R1 and fails here)")

    missing = [f for f in REQUIRED_FAMILIES if not any(f in a for a in arms)]
    check("R3", not missing,
          f"every named arm family present; missing={missing}")

    check("R4", "selftest: all green" in out,
          "the selftest reports its own verdict line (a run that dies part-way and still exits 0 "
          "is caught here)")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-goal-watcher-selftest  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
