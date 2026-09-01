# 20260901-i-scheduled-probe-suite-standing — scheduled probe suite standing reds triaged

kind: issue
component: deploy
date: 2026-09-01
commit: 4d4aae4d
deployed: no
pin: ignite/deploy/probe-suite.js
components: planning,operator,runtime,supervisor,coord,chat

## Observed
The scheduled probe suite had been permanently RED at 199 passed / 21 failed / 1 inop (runs `2026-08-31T05-00-27Z` and `15-00-14Z`). Every concurrent seat re-derived that the reds were pre-existing; several reached for whole-tree `git stash` to prove it. The 05:00Z fire on 2026-09-01, after commit `4d4aae4d`, showed the quarantine class working (14 quarantined with `known red, tracked as …`) and four NEW named reds outside it.

## Mechanism
Standing reds mixed three classes: probes still asserting a retired contract (file-prefix pause, two-arg `startExecution`, bare `--lane daemon`, a mutation ANCHOR that no longer exists in source), environment/selftest aborts wrapped as FAIL, and a handful of real product gaps. A suite that cannot tell those apart cannot answer "did my change break something".

## Attempts
First attempt held — checked: `660e6cf2` (store is the pause row), `4ed8acc8` (`daemon-lane-unmaterialized`), start-execution.js dropping the `{db}` first argument, `owed-from-endings.js` cursor filter replacing `tsAfter`, selftest-aborts report (cwd/`capg` aborts STALE, 24 coord selftest failures remaining). No prior sitting had quarantined with a visible marker; INOPERATIVE (exit 2) was the only non-fail class and is for "could not run", not "known red".

## Fix
Three probes were retargeted at the live contract (not loosened): approve-package calls the single-arg API with an ask bound to the goal under test; paused-gate C4 resumes via `writeGoalWord running`; lane-at-birth pins the daemon-lane refusal and `--materialize-follows`. Two mutation anchors were updated to the live source (`reconcile.selftest.js` L846; `probe-hold-classb` A3.1 now includes the `abandonedMap` line). `probe-workspace-record-walk` copies `planning/` so `ready.py`'s `planning_bind` import is not a fixture miss. Remaining original-21 reds plus `probe-save-gate` (product: newer candidate / `--force` stale) and `probe-chat-live-session` (EPIPE, capture INCOMPLETE) grade QUARANTINE with a dated `known red, tracked as` marker. A listed probe that PASSES is still PASS.

## Consequences
`probe-suite.js` accounting gained `quarantined:` so GREEN is `failed === 0` even with standing reds visible. `save-coord.py` was not patched — the two failing save-gate assertions are a product finding. `probe-consumer-closure` stays INOPERATIVE: it identifies the ignite root by `server/`, which the refactor deleted.

## Verification
Named probes re-run green: approve-package 27/27, paused-gate EXIT 0, lane-at-birth 18/0, hold-classb 10/10, workspace-record-walk 13/13 EXIT 0. Runner `--selftest` 26/26. Partial `--only` of chat-boundary + paused-gate: 1 PASS / 1 QUARANTINE / 0 failed / GREEN. Full suite after this sitting if started before 05:35Z.

## ATTENTION
- A QUARANTINE row that starts PASSing has lifted itself — do not keep it in `KNOWN_RED` as a freeze.
- `probe-save-gate`'s two reds ("NEWER candidate still SAVES", "`--force` installs a stale candidate") are product, not a broken probe. Do not weaken those checks to go green.
- `probe-consumer-closure` aborts because it hunts `ignite/server`, which no longer exists. Fixing the identifier will RUN the probe; it was one of the original 21 FAILs and will likely go red, not green.
- A QUARANTINE row that PASSES has lifted itself — do not freeze it in KNOWN_RED.
- probe-save-gate reds are product (newer-candidate / --force stale); do not weaken the checks.
- probe-consumer-closure hunts ignite/server which the refactor deleted; fixing the identifier will RUN it, likely red.
