#!/usr/bin/env python3
"""probe-coord-selftest-notmux.py — task 7.730: `python3 coord.py selftest` stays GREEN, OUTSIDE tmux.

WHAT THIS ENFORCES. `coord.py` is re-read by every seat on every invocation and has no fallback, and
its selftest went green for the FIRST time on 2026-08-10 (8fe4fb8). Nothing then kept it green:
`coord/CLAUDE.md` tells an author to run it after saving, and a rule nothing executes is a hope.
This probe is the execution — auto-discovered by `deploy/probe-suite.js`, so the VPS's hourly suite
enforces the baseline within the hour of any `coord.py` change, from ANY harness.

WHY A TWIN. `probe-coord-selftest-tmuxpane.py` runs the same baseline with `TMUX_PANE` SET. G-218:
a verdict is a claim about the environment it was taken in. Two probes rather than one because a
run costs ~106 s against a 180 s per-probe timeout. Shared body: `selftest_venue.py`.

Exit 0 = green · 1 = the baseline broke (the failing check ids are in the output) · 2 = INOPERATIVE.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from selftest_venue import run

run(__file__, pane=None)
