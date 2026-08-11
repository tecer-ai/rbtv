"""selftest_venue — the shared body of the two `coord.py selftest` enforcement probes.

WHY TWO PROBES AND ONE BODY. The baseline being enforced is `python3 coord.py selftest` GREEN in
BOTH tmux env modes (outside tmux, and with a `TMUX_PANE` set) — G-218: a verdict is a claim about
the environment it was taken in, and these two environments have historically given different
verdicts on the same bytes. One run costs ~106 s and `deploy/probe-suite.js`'s per-probe timeout is
180 000 ms, so the two modes CANNOT share one probe process. They share this module instead.

Not named `probe-*` on purpose: `discoverProbes` collects exactly `probe-*.{js,py}`, so this file is
a library beside them, never a counted probe.

Exit 0 = the baseline is green in this mode · 1 = it is not (the FAIL id lines are the diagnostic
and are printed) · 2 = INOPERATIVE (no venue here — never a vacuous green).
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# The selftest costs ~106 s; the runner kills at 180 s. Bounded here so an overrun is OUR verdict
# (a FAIL with a reason) rather than the runner's opaque TIMEOUT row.
BUDGET_S = 165


def run(probe_file, pane):
    """`pane` = the TMUX_PANE handed to the selftest child, or None for the unset mode."""
    here = Path(probe_file).resolve()
    kit = here.parent.parent                      # <tree>/ignite/team-kit — coord.py's own folder
    out = here.with_suffix(".out")
    label = f"TMUX_PANE={pane}" if pane else "TMUX/TMUX_PANE unset"
    lines, started = [], time.time()

    sys.path.insert(0, str(kit))                  # task 7.630 solo-run isolation, before any tmux
    from self_isolate import self_isolate_tmux
    self_isolate_tmux()

    def finish(verdict, code):
        body = "\n".join([
            f"{verdict}  {here.stem}  ({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
            f"tree={kit}  env={label}  elapsed={time.time() - started:.1f}s",
            *lines]) + "\n"
        out.write_text(body, encoding="utf-8")
        sys.stdout.write(body)
        sys.exit(code)

    # A host with no venue REFUSES. The Windows desktop has neither tool; a green there would be a
    # green nobody measured.
    for tool, why in (("tmux", "no tmux — selftest venue requires a reachable tmux server"),
                      ("python3", "no python3 — the enforced baseline is `python3 coord.py "
                                  "selftest`")):
        if not shutil.which(tool):
            lines.append(f"INOP  {why}; enforced hourly on the VPS")
            finish("INOPERATIVE", 2)

    env = {k: v for k, v in os.environ.items() if k not in ("TMUX", "TMUX_PANE")}
    if pane:
        env["TMUX_PANE"] = pane
    try:
        r = subprocess.run(["python3", "coord.py", "selftest"], cwd=str(kit), env=env,
                           capture_output=True, text=True, timeout=BUDGET_S)
    except subprocess.TimeoutExpired:
        lines.append(f"FAIL  `python3 coord.py selftest` did not finish within {BUDGET_S}s")
        finish("FAILED", 1)

    text = r.stdout + r.stderr
    if r.returncode == 0 and "PASS (0 failure(s))" in text:
        lines.append("PASS  exit 0 and `selftest: PASS (0 failure(s))` — the baseline holds here")
        finish("GREEN", 0)

    # ⚠ THE FAIL ID LINES ARE THE DIAGNOSTIC. Never a count: the two modes converge by BOTH
    # asserting an EMPTY fail set, and when one reddens its `.out` carries that mode's ids so the
    # two lists can be diffed. A total tells you nothing about WHICH check moved.
    lines.append(f"FAIL  exit={r.returncode}; the failing check ids follow:")
    lines += [ln.rstrip() for ln in text.splitlines()
              if ln.startswith("FAIL") or ln.startswith("selftest:")] or [
        "      (no FAIL line at all — the selftest reached no verdict)"]
    finish("FAILED", 1)
