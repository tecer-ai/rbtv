#!/usr/bin/env python3
"""probe-launcher-attribution.py — `workflow_launcher.py` grades THIS fire, not the room (7.588).

WHAT THIS EXISTS TO CATCH. The launcher's exit code IS the store record (`recordToolCompletion`
maps exit 0 -> `done`, non-zero -> `failed`), and exit 0 claims exactly one thing: "this fire
opened a seat pane". Until 7.588 that claim was proven from a ROOM-WIDE pane-set delta — the whole
session's panes read before the delegated launch and again after it. The room is SHARED BY
CONSTRUCTION (`ensure_session` is idempotent by design, so every fire of a run's passes joins the
one session), so the delta attributes any pane that appeared in that window to whichever fire
happened to look last. Two fires racing into one room therefore mis-attribute in BOTH directions:

  · a fire that opened NOTHING sees the neighbour's pane in its delta, exits 0, and the store
    records `done` for a fire that achieved nothing — the exact false success EXIT_NO_SEAT was
    minted to make impossible; and
  · a fire that opened ONE pane claims the neighbour's as well, so the record of WHICH panes this
    fire opened is wrong even when the exit code happens to land right.

INVISIBLE TODAY only because passes are serial (ruled interim R22). This probe is the witness that
must exist BEFORE anything permits concurrent fires.

THE ARMS.

  A. RACE — a fire that opened nothing must NOT claim a neighbour's pane. Fire A1 launches into
     the fixture room and opens NO pane (the WAIT case); fire A2 races in behind it and opens one
     inside A1's window. A1 MUST exit EXIT_NO_SEAT (3); A2 MUST exit 0 naming its own pane.
     RED-FIRST CONTROL: against the pre-7.588 delta contract A1 exits 0.
  B. RACE — a fire must name EXACTLY the pane it opened. Fire B1 reads the room, B2 opens a pane
     inside B1's window, then B1 opens its own. B1 MUST report its own pane and ONLY its own.
     RED-FIRST CONTROL: against the delta contract B1 reports two panes, one of them B2's.
  C. SERIAL CONTROL (7.588 criterion 3) — the single-fire path is UNCHANGED. One fire alone in a
     room that opens a pane exits 0 and names it; one fire alone that opens nothing exits
     EXIT_NO_SEAT. These two are the old contract's own outcomes and must stay identical, so a fix
     that graded concurrency right by breaking the serial path fails here.
  E. MEMBERSHIP (7.588 criterion 3, the fast-crash case) — the attribution is `reported ∩ room`,
     not `reported`. A pane the launch REPORTED opening but that the room no longer holds when the
     launcher reads it (the seat died between the two) must NOT be claimed: the old delta contract
     excluded it too (absent from `after`), so claiming it would be a REGRESSION — a false `done`
     for a seat that is gone. Without this arm the `in room` membership filter is unexercised: it
     can be deleted and every other arm stays green (verified by mutation at the §2 review).
  D. THE COUPLING IS PINNED — the attribution reads `coordinate launch`'s own per-seat success
     line, so this probe asserts that line still exists in `team-kit/coord.py` verbatim. Without
     D, a rename in coord.py would silently turn every real launch into a WAIT while A/B/C stayed
     green against this probe's stub.

NO AGENT IS EVER BOOTED, AND NO LIVE ROOM IS TOUCHED. The delegated `coord.py` is a STUB written
into a tempdir: it opens a `sleep` pane and prints coord's own `launched … in %N` line, nothing
else. Every room lives on a PRIVATE tmux socket (`-L`), is created by the probe, and is killed in
`finally`. The stub is the right fixture here precisely because the launcher's contract is about
what the DELEGATED LAUNCH REPORTS, not about what a harness does afterwards — `probe-planning-entry`
already drives the real coord end to end.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CAP = Path(__file__).resolve().parents[1]
LAUNCHER = CAP / "tool" / "workflow_launcher.py"
COORD = Path(__file__).resolve().parents[3] / "team-kit" / "coord.py"
SOCKET = "probe-launcher-attribution"   # PRIVATE socket; never the one live rooms are on

# coord.py's own per-seat success line, verbatim (`cmd_launch`'s launch loop). The launcher parses
# it, so a drift here is a silent downgrade of every real launch to a WAIT — arm D pins it.
COORD_SUCCESS_LINE = 'print(f"launched {label} in {pane}"'

EXIT_NO_SEAT = 3

STUB_COORD = '''#!/usr/bin/env python3
"""Fixture stand-in for `coord.py launch` — opens a `sleep` pane, prints coord's own success line.

Behaviour is env-driven so a race can be composed deterministically:
  W7588_SOCK       the private tmux socket
  W7588_MODE       `open` (default) opens one pane · `noop` opens none (coord's WAIT outcome) ·
                   `open-kill` opens one, reports it, then KILLS it (the reported-but-dead pane)
  W7588_PRE_SLEEP  seconds to wait BEFORE opening, so another fire's window overlaps this one
  W7588_REPORT     file this stub writes the pane id it opened into (the probe's ground truth)
"""
import os, subprocess, sys, time

argv = sys.argv[1:]
target = argv[argv.index("--tmux-target") + 1]
seat = argv[argv.index("--only") + 1]
sock = os.environ["W7588_SOCK"]

time.sleep(float(os.environ.get("W7588_PRE_SLEEP", "0")))
mode = os.environ.get("W7588_MODE", "open")
if mode in ("open", "open-kill"):
    r = subprocess.run(["tmux", "-L", sock, "split-window", "-d", "-t", target,
                        "-P", "-F", "#{pane_id}", "sleep 600"],
                       capture_output=True, text=True)
    pane = r.stdout.strip()
    if r.returncode != 0 or not pane:
        print(f"stub-coord: could not open a pane: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    open(os.environ["W7588_REPORT"], "w").write(pane)
    print(f"launched {seat} (claude/stub, pane) in {pane}")
    if mode == "open-kill":
        # the seat died between coord reporting it and the launcher reading the room
        subprocess.run(["tmux", "-L", sock, "kill-pane", "-t", pane],
                       capture_output=True, text=True)
else:
    print(f"  {seat}: WAIT — deferred (fixture noop)")
sys.exit(0)
'''

failures: list[str] = []
inoperative: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> bool:
    print(f"  {'ok  ' if cond else 'FAIL'} {label}{'' if cond else ': ' + detail}")
    if not cond:
        failures.append(label)
    return cond


def tmux(*a):
    exe = shutil.which("tmux")
    return subprocess.run([exe, "-L", SOCKET, *a], capture_output=True, text=True) if exe else None


def fire(pkg: Path, goal: str, coord: Path, env_extra: dict):
    """Start ONE launcher process detached. Returns the Popen; the caller waits."""
    env = dict(os.environ)
    env["W7588_SOCK"] = SOCKET
    env.update({k: str(v) for k, v in env_extra.items()})
    return subprocess.Popen(
        [sys.executable, str(LAUNCHER), "--package", str(pkg), "--goal", goal,
         "--entry-seat", "fixture-seat", "--coord", str(coord), "--tmux-socket", SOCKET],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)


def collect(proc):
    out, err = proc.communicate(timeout=120)
    return proc.returncode, out, err


def claimed_panes(stdout: str) -> list[str]:
    """The pane ids the launcher's own LAUNCHED verdict line claims for that fire."""
    for line in stdout.splitlines():
        if "LAUNCHED —" in line:
            return re.findall(r"%\d+", line)
    return []


def main() -> int:
    if shutil.which("tmux") is None:
        inoperative.append("tmux is not on PATH — the fixture room cannot be built AT ALL")
        return report_inoperative()
    if not LAUNCHER.is_file():
        # An absent target IS the failure, never a skip.
        return check("the launcher under test exists", False, str(LAUNCHER)) or grade()

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        coord = tmp / "coord.py"
        coord.write_text(STUB_COORD, encoding="utf-8")
        coord.chmod(0o755)

        def pkg_for(goal: str) -> Path:
            p = tmp / goal / "run-9"
            p.mkdir(parents=True)
            return p

        try:
            print("A. RACE — a fire that opened NOTHING must not claim the neighbour's pane")
            goal_a = "w7588-a"
            pkg_a = pkg_for(goal_a)
            rep_a2 = tmp / "a2.pane"
            a1 = fire(pkg_a, goal_a, coord, {"W7588_MODE": "noop", "W7588_PRE_SLEEP": 3,
                                             "W7588_REPORT": tmp / "a1.pane"})
            time.sleep(1.0)   # A2 opens its pane INSIDE A1's before/after window
            a2 = fire(pkg_a, goal_a, coord, {"W7588_MODE": "open", "W7588_PRE_SLEEP": 0,
                                             "W7588_REPORT": rep_a2})
            rc2, out2, err2 = collect(a2)
            rc1, out1, err1 = collect(a1)
            pane_a2 = rep_a2.read_text().strip() if rep_a2.is_file() else ""
            if not check("the racing fire A2 actually opened a fixture pane", bool(pane_a2),
                         f"stub reported none (rc={rc2}) {err2.strip()[:200]}"):
                inoperative.append("arm A's fixture never opened a pane — the race was not staged")
            check("A1 (opened nothing) exits EXIT_NO_SEAT, not a false `done`",
                  rc1 == EXIT_NO_SEAT, f"exit={rc1}; claimed {claimed_panes(out1)}")
            check("A1 claims NO pane at all", claimed_panes(out1) == [],
                  f"claimed {claimed_panes(out1)}, A2's pane was {pane_a2}")
            check("A2 (opened one) exits 0", rc2 == 0, f"exit={rc2} {err2.strip()[:200]}")
            check("A2 claims exactly its own pane", claimed_panes(out2) == [pane_a2],
                  f"claimed {claimed_panes(out2)}, opened {pane_a2}")

            print("B. RACE — a fire must claim EXACTLY the pane it opened")
            goal_b = "w7588-b"
            pkg_b = pkg_for(goal_b)
            rep_b1, rep_b2 = tmp / "b1.pane", tmp / "b2.pane"
            b1 = fire(pkg_b, goal_b, coord, {"W7588_MODE": "open", "W7588_PRE_SLEEP": 3,
                                             "W7588_REPORT": rep_b1})
            time.sleep(1.0)   # B2's pane appears after B1 read the room, before B1 opened its own
            b2 = fire(pkg_b, goal_b, coord, {"W7588_MODE": "open", "W7588_PRE_SLEEP": 0,
                                             "W7588_REPORT": rep_b2})
            rc_b2, out_b2, err_b2 = collect(b2)
            rc_b1, out_b1, err_b1 = collect(b1)
            pane_b1 = rep_b1.read_text().strip() if rep_b1.is_file() else ""
            pane_b2 = rep_b2.read_text().strip() if rep_b2.is_file() else ""
            if not check("both racing fires opened a fixture pane",
                         bool(pane_b1) and bool(pane_b2) and pane_b1 != pane_b2,
                         f"b1={pane_b1!r} b2={pane_b2!r}"):
                inoperative.append("arm B's fixture did not stage two distinct panes")
            check("B1 exits 0", rc_b1 == 0, f"exit={rc_b1} {err_b1.strip()[:200]}")
            check("B1 claims its OWN pane and ONLY its own (no cross-attribution)",
                  claimed_panes(out_b1) == [pane_b1],
                  f"claimed {claimed_panes(out_b1)}, opened {pane_b1}, neighbour opened {pane_b2}")
            check("B2 exits 0 claiming exactly its own pane",
                  rc_b2 == 0 and claimed_panes(out_b2) == [pane_b2],
                  f"exit={rc_b2}, claimed {claimed_panes(out_b2)}, opened {pane_b2}")

            print("C. SERIAL CONTROL — the single-fire path and its exit contract are unchanged")
            goal_c = "w7588-c"
            pkg_c = pkg_for(goal_c)
            rep_c = tmp / "c.pane"
            rc_c, out_c, err_c = collect(fire(pkg_c, goal_c, coord,
                                              {"W7588_MODE": "open", "W7588_REPORT": rep_c}))
            pane_c = rep_c.read_text().strip() if rep_c.is_file() else ""
            check("a lone fire that opens a seat pane exits 0", rc_c == 0,
                  f"exit={rc_c} {err_c.strip()[:200]}")
            check("a lone fire names exactly the pane it opened",
                  claimed_panes(out_c) == [pane_c] and bool(pane_c),
                  f"claimed {claimed_panes(out_c)}, opened {pane_c}")

            goal_d = "w7588-d"
            pkg_d = pkg_for(goal_d)
            rc_d, out_d, err_d = collect(fire(pkg_d, goal_d, coord,
                                              {"W7588_MODE": "noop", "W7588_REPORT": tmp / "d.pane"}))
            check("a lone fire that opens nothing still exits EXIT_NO_SEAT",
                  rc_d == EXIT_NO_SEAT, f"exit={rc_d} {err_d.strip()[:200]}")
            check("and says WAIT rather than reporting a success",
                  "WAIT" in out_d, out_d.strip()[-200:])

            print("E. MEMBERSHIP — a REPORTED pane the room does not hold is not a success")
            goal_e = "w7588-e"
            pkg_e = pkg_for(goal_e)
            rep_e = tmp / "e.pane"
            rc_e, out_e, err_e = collect(fire(pkg_e, goal_e, coord,
                                              {"W7588_MODE": "open-kill", "W7588_REPORT": rep_e}))
            pane_e = rep_e.read_text().strip() if rep_e.is_file() else ""
            if not check("the fixture staged a reported-then-dead pane", bool(pane_e),
                         f"the stub reported none (rc={rc_e}) {err_e.strip()[:200]}"):
                inoperative.append("arm E's fixture never opened a pane to kill")
            check("a fire whose reported pane died before the room read exits EXIT_NO_SEAT",
                  rc_e == EXIT_NO_SEAT,
                  f"exit={rc_e}, claimed {claimed_panes(out_e)}, reported {pane_e}")
            check("and it claims no pane (the old delta contract claimed none either)",
                  claimed_panes(out_e) == [], f"claimed {claimed_panes(out_e)}")
        finally:
            tmux("kill-server")

    print("D. THE COUPLING — coord.py still prints the per-seat line the attribution reads")
    if not COORD.is_file():
        check("team-kit/coord.py resolves from this probe", False, str(COORD))
    else:
        check("coord.py's launch loop still prints `launched {label} in {pane}`",
              COORD_SUCCESS_LINE in COORD.read_text(encoding="utf-8"),
              f"not found in {COORD} — the launcher's attribution would read every launch as a WAIT")

    return grade()


def report_inoperative() -> int:
    for item in inoperative:
        print(f"INOPERATIVE: {item}")
    print("probe-launcher-attribution: INOPERATIVE — not a pass")
    return 2


def grade() -> int:
    print()
    if inoperative:
        return report_inoperative()
    if failures:
        print(f"probe-launcher-attribution: FAIL — {len(failures)} failure(s): {failures}")
        return 1
    print("probe-launcher-attribution: PASS — every fire is graded by the pane it opened; two "
          "fires racing into one room cross-attribute neither the exit code nor the pane ids, "
          "and the serial single-fire contract is unchanged")
    return 0


class _Tee:
    def __init__(self, real):
        self.real, self.buf = real, []

    def write(self, s):
        self.real.write(s)
        self.buf.append(s)
        return len(s)

    def flush(self):
        self.real.flush()


if __name__ == "__main__":
    tee = _Tee(sys.stdout)
    sys.stdout = tee
    try:
        rc = main()
    finally:
        sys.stdout = tee.real
        (Path(__file__).with_suffix(".out")).write_text("".join(tee.buf), encoding="utf-8")
    sys.exit(rc)
