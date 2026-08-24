#!/usr/bin/env python3
"""probe-team-monitor-approval-title.py — the approval reading is the pane TITLE (P38, map B15).

WHAT IT SCORES (task 7.663). `team_monitor.prompt_pending` regex-matched the pane's last 8 lines
of CONTENT. The kit had already tried that reading and RULED IT OUT in writing — matching the
pane's visible TEXT "would false-fire on any seat whose output merely contains the phrase — a
briefing quoting it, a log line, this design file in an editor"
(`ignite/team-kit/system-design.md:140`), which adds that a run where the watcher and the sender
disagree about which seats are gated is worse than either behaviour alone. The replacement sensor
reimplemented the rejected version, putting exactly that disagreement between the snapshot and
`coordinate send`'s own gate-skip.

⚠ R2 IS THE ARM. R1 passes under BOTH readings (a gated pane's title and its content both carry
the phrase), so an R1-only probe would report green against the defect. What separates them is a
pane that is NOT gated whose CONTENT quotes the prompt — the false positive the design record
rejected.

⚠ PLACEMENT. `team_monitor.py` lives under `orchestration/team-monitor/tool/`, which the probe
runner's discovery root (`ignite/`) does not reach — a probe beside it would be outside the ONE
denominator, which is the G-141 failure the runner exists to prevent. It therefore sits here,
beside the other sensor probes under `ignite/jobs/probes/`.

RED-FIRST. Set `RBTV_PROBE_TREE` to an alternative rbtv repo root and every arm re-runs against
THAT tree's `team_monitor.py`. Pointed at a pre-7.663 tree, R2/R3/R4 go red and C0/R1 stay green.

ARMS
  C0  the target imports and its marker source — coord's `APPROVAL_TITLE_MARKERS` — is non-empty.
  R1  a gated pane's TITLE fires the predicate, and EVERY marker in coord's set does.
  R2  THE CONTROL: a pane whose CONTENT quotes the prompt while its title is ordinary does NOT
      fire. This is the false positive `system-design.md:140` rejected.
  R3  ONE DEFINITION: the sensor declares no local pattern list of its own — the marker set is
      coord's, so the two consumers cannot drift.
  R4  THE REASON IS CITED AT THE CODE: the predicate's own comment names `system-design.md:140`,
      so the next reader meets the ruling before re-deriving the rejected version a third time.

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP.

Run it through the suite — `node ignite/deploy/probe-suite.js --only team-monitor-approval-title`
— never by hand (`G-163`). Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import importlib.util
import os
import sys
import time
import types
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

# `team_monitor` imports `fcntl` at module level for its writer lock, which the predicate under
# test never touches. Stubbed on a non-POSIX host so the probe measures something there too.
try:
    import fcntl  # noqa: F401
except ImportError:
    _m = types.ModuleType("fcntl")
    _m.__dict__.update({"LOCK_EX": 2, "LOCK_NB": 4, "flock": lambda *a: None})
    sys.modules["fcntl"] = _m

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "orchestration" / "team-monitor" / "tool" / "team_monitor.py"
DESIGN_CITATION = "system-design.md:140"
OUT = HERE / "probe-team-monitor-approval-title.out"

# A pane that is NOT gated. Every phrase the retired CONTENT matcher keyed on is present — and
# the string deliberately avoids the one marker coord reads off the TITLE, because the point is
# a pane whose CONTENT looks gated while its title does not.
QUOTING_CONTENT = ("$ cat briefing.md\n"
                   "  the harness asks 'Do you want to proceed?' and waits\n"
                   "  > 1. Yes  /  Esc to cancel — answer it before sending a wake\n"
                   "  allow this only after reading the diff\n")

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
        check("C0", False, f"{TARGET} does not exist — the predicate cannot read a title in a "
                           f"file that is gone")
        return
    spec = importlib.util.spec_from_file_location("tm_under_probe", TARGET)
    tm = importlib.util.module_from_spec(spec)
    sys.modules["tm_under_probe"] = tm
    spec.loader.exec_module(tm)
    src = TARGET.read_text(encoding="utf-8")

    markers = tuple(tm.coord().APPROVAL_TITLE_MARKERS)
    check("C0", bool(markers),
          f"target imported; coord's marker set = {markers}")

    fires = [m for m in markers if tm.prompt_pending(f"codex — {m.title()}")]
    # ⚠ THE NEGATIVE HALF IS ASSERTED, not merely printed. It lived inside the detail f-string, so a
    # `prompt_pending` that fired on EVERYTHING — e.g. a defensive `if not title: return True`, with
    # `coord.pane_title()` really returning "" on an unreadable pane — kept this arm green while
    # every unreadable-title pane read as gated. A recorded value cannot fail.
    quiet = not tm.prompt_pending("codex — bash") and not tm.prompt_pending("")
    check("R1", tm.prompt_pending("codex — Action Required") and len(fires) == len(markers) and quiet,
          f"a gated TITLE fires; {len(fires)}/{len(markers)} of coord's markers fire "
          f"({fires}); an ordinary title is quiet={quiet}")

    check("R2", not tm.prompt_pending(QUOTING_CONTENT),
          "a pane whose CONTENT quotes the prompt while its title is ordinary does NOT fire — "
          "this is the false positive system-design.md:140 rejected, and it is the ONLY arm the "
          "content reading fails")

    # The retired symbol is spelled in TWO HALVES: written whole, this very line would be the
    # match once this probe's own source is ever read into the same check.
    check("R3", ("PROMPT_" + "PATTERNS") not in src and "APPROVAL_TITLE_MARKERS" in src,
          "the sensor declares no local pattern list; it reads coord's ONE marker definition")

    check("R4", DESIGN_CITATION in src,
          f"the predicate cites {DESIGN_CITATION} at the code — the ruling meets the next reader "
          f"before they re-derive the rejected version")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-team-monitor-approval-title  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
