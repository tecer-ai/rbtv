# 20260901-i-coord-selftest-quarantine-was — coord selftest quarantine was an overrun

kind: issue
component: deploy
date: 2026-09-01
commit: 9995a9f1
deployed: no
pin: ignite/coord/probes/selftest_venue.py
components: coord

## Observed
`judge-looseends-2` failed the probe-suite-green sitting on one cell: `probe-coord-selftest-notmux.py` and `…-tmuxpane.py` were quarantined as `coord-selftest-24-failures`, but both GREEN suite runs captured `FAIL  python3 coord.py selftest did not finish within 165s` / `elapsed=165.1s`. The marker named a countable selftest red the probes never reached.

## Mechanism
The probes bound the child at 165 s so an overrun is their named FAIL rather than the suite runner's opaque 180 s TIMEOUT. Direct invocation on 2026-09-01 06:38:25Z–06:42:00Z completed in 215 s with `selftest: FAIL (24 failure(s))` — not a hang. The 165 s budget is simply shorter than the current run, so the hourly probes stop before any FAIL id line.

## Attempts
First attempt held — checked: selftest-aborts report (1042 checks, 24 failures, no abort); `selftest_venue.py` comment claiming ~106 s; suite `DEFAULT_TIMEOUT_MS = 180000`. Raising `BUDGET_S` above 180 would replace the named overrun with TIMEOUT. Raising it to 215 would let the 24 ids print and add ~100 s of hourly wall for a still-red selftest.

## Fix
Quarantine relabelled to `probe-suite-green/2026-09-01/coord-selftest-overrun`. Budget kept at 165 s. The 24 failures are a separate, verified fact of a direct 215 s run, not what these two probes hit.

## Consequences
Nothing else in `KNOWN_RED` moved. The 24 selftest failures remain unenforced by the hourly suite: a reader of a GREEN run still cannot treat those ids as measured this hour. The previous marker `coord-selftest-24-failures` is retired and must not be reused for this pair.

## Verification
Timed canonical `python3 coord.py selftest` from `ignite/coord`: 215 s, exit 1, 24 FAIL lines, `selftest: FAIL (24 failure(s))`. Probe `--only` after the relabel must print `known red, tracked as probe-suite-green/2026-09-01/coord-selftest-overrun`.

## ATTENTION
- Do not raise `BUDGET_S` past 180: the suite TIMEOUT is opaque and worse than a named 165 s overrun.
- The 24 failures are real on a direct run; they are not what the hourly probes capture.
- Do not raise BUDGET_S past 180: suite TIMEOUT is opaque and worse than a named 165s overrun.
- The 24 failures are real on a direct 215s run; they are not what the hourly probes capture.
