# 20260831-i-path-b-birth-carries-the-plan — Path-B birth carries the plan's declared execution-mode

kind: issue
component: planning
date: 2026-08-31
commit: 835f52b0
deployed: no
pin: ignite/planning/probes/probe-planning-path-b-materialize.py

## Observed
Filed `G-plan-drafter-0828-1848`: every Path-B birth (approve→scaffold) wrote
`<goal>/execution-mode` = `autonomous` regardless of what the plan declared, because
`path_b.py#run_scaffold`'s argv carried no `--execution-mode` and `approve_package.py`'s
`OPTIONAL_KEYS` had no field for it. Measured live on `stools-canvas-audio-elevenlabs-close`
(21:04:04Z birth, 21:11:29Z hand-write to `interactive`, `decisions.md:58`) — task 154.

## Mechanism
`goal_cli.py`'s `scaffold` verb already accepted `--execution-mode` correctly and derives nothing
itself (`EXECUTION_MODE_DEFAULT` only fires when the flag is omitted) — the gap was entirely
upstream: `approve_package.py#build_package` had no `execution_mode` key to carry the plan's
declaration into the JSON package, so `path_b.py#run_scaffold` (reading that same `pkg` dict) had
nothing to pass through even if it tried.

## Attempts
First attempt held — checked `20260825-c-the-approve-package-writer.md` and
`20260831-i-path-b-birth-writes-its-own-en.md` (same two files, same `OPTIONAL_KEYS` shape, an
analogous missing-field gap for `envelope.json` fill-ins): no prior attempt touched
`execution_mode` specifically.

## Fix
Added `execution_mode` to `approve_package.py`'s `OPTIONAL_KEYS`, with a re-spoken
`EXECUTION_MODES = ("interactive", "autonomous")` validated in `build_package` (refuses
`bad-execution-mode` before any byte lands, same discipline as `bad-execution-goal`) and an
argparse `--execution-mode` choice-gated flag. `path_b.py#run_scaffold` appends
`--execution-mode <value>` to the scaffold argv only when `pkg.get("execution_mode")` is truthy —
an omitted declaration still defaults through `goal_cli.py`'s own `EXECUTION_MODE_DEFAULT`,
unchanged. Rejected: touching `goal_cli.py` — it already carries the correct contract ("this verb
derives none"); the fix belongs entirely at the two callers that drop the value before it gets
there.

## Consequences
`goal_cli.py` is byte-unchanged. Re-verifying the filing's claimed CONSEQUENCE (an owner ask
silently parked by goal-level `execution-mode`) against the current `ignite/chat/bus-ferry.js`
found that mechanism already deleted by a broader redesign: `bus-ferry.js:1108-1122` — "THE THREE
PARK RUNGS ARE DELETED [D24, T2-R17, D-7-ruling, T2-R14] … Goal-level interactive/autonomous mode
is DEAD [D24]". Owner-contact delivery today depends only on the seat's own `human-interactive:`
flag and `ask-thread.js#postAsk`'s refusal, never on the goal's `execution-mode` file — so the
specific silent-drop failure this filing measured cannot recur today regardless of this fix. The
carry fix stands on its own as data-hygiene correctness (a plan's declared execution-mode should
land accurately at mint) and closes the filing for that reason plus the mooted consequence, both
recorded in the closed filing.

## Verification
`python3 -m py_compile ignite/planning/path_b.py ignite/planning/approve_package.py` exit 0.
`probe-planning-path-b-materialize.py`: 13/13 PASS, including two new arms — P12 (a package
declaring `execution_mode: interactive`, minted through the REAL `goal_cli.py` scaffold subprocess,
no stub) reads `<goal>/execution-mode` = `interactive`; confirmed RED on unmodified HEAD
(`git stash` of just the two source files, probe unchanged) reading `autonomous` instead. P13 (no
declaration) still defaults `autonomous`, unchanged both sides. `probe-approve-package.js`: 22/27
PASS (pre-existing 20/24 baseline on unmodified HEAD, same "bad-commit" environment gap the
2026-08-31 envelope entry already recorded — not caused by this change); new arm M1 (writer emits
`execution_mode` in the written package) PASS, M3 (writer refuses a value `cmd_scaffold` would
reject) PASS; M2 (value reaches the daemon-side birth via `startExecution`) FAILS for the SAME
pre-existing `bad-commit` gap that already fails sibling arms A1-A3 on unmodified HEAD — not a
regression of this fix. NOT DEPLOYED — no deploy or restart performed, per plan discipline.

## ATTENTION
1. `GOAL_CLI.PY`'S SCAFFOLD VERB ALREADY HONORS `--execution-mode` CORRECTLY. Do not re-touch
   `EXECUTION_MODE_DEFAULT`/the scaffold argparse block for this class of gap again — the contract
   comment there ("this verb derives none") is accurate; the caller is always the bug.
2. GOAL-LEVEL `execution-mode` NO LONGER GATES OWNER CONTACT. `bus-ferry.js`'s three park rungs
   (goal execution-mode, seat human-interactive, seat fallback:park) were deleted by ruling D24 and
   siblings; `goalExecutionMode`/the three-rung ladder (bus-ferry.js:175-228) is still exported and
   still a correct PREDICATE, but nothing in the send path calls it to decide delivery any more. A
   future fix aimed at "goal-level execution-mode blocks an owner ask" is chasing a mechanism that
   no longer exists — verify against the CURRENT `bus-ferry.js` before building, not the filing's
   description of 2026-08-28's behaviour.
3. `probe-approve-package.js`'s A1-A3/M2 arms fail on UNMODIFIED HEAD too (a `bad-commit` refusal
   from `startExecution`'s own `COMMIT_RE` check, cause not yet diagnosed) — confirmed by
   `git stash` of the probe file alone. Don't attribute a fresh failure there to a future change
   without first checking whether it's this same pre-existing 20/24 baseline.
- Goal-level execution-mode no longer gates owner contact — verify against CURRENT bus-ferry.js
