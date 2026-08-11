#!/usr/bin/env python3
"""probe-coord-selftest-tmuxpane.py — task 7.730: the same baseline, with `TMUX_PANE` SET.

The twin of `probe-coord-selftest-notmux.py`. `coord.py`'s identity resolution reads the CALLING
pane, so a seat-shaped environment (`TMUX_PANE` present) is a genuinely different venue from a bare
one — G-218: a verdict is a claim about the environment it was taken in, and these two have given
different verdicts on the same bytes. `%99999` is a pane id no live server hands out, so the mode is
exercised without binding any real pane.

Split from its twin only because one selftest run costs ~106 s and `deploy/probe-suite.js` kills a
probe at 180 s; the two modes cannot share one process. Shared body: `selftest_venue.py`.

Convergence between the modes is carried BY CONSTRUCTION: both probes assert an EMPTY fail set, and
when one reddens its `.out` carries that mode's failing check ids, so the two lists are diffable.

Exit 0 = green · 1 = the baseline broke (the failing check ids are in the output) · 2 = INOPERATIVE.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from selftest_venue import run

run(__file__, pane="%99999")
