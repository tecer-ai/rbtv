# 20260824-c-engine-reads-ending-store — engine reads ending store

kind: change
component: engine
date: 2026-08-24
commit: 23d95ec3
deployed: no
pin: ignite/engine/reconcile.selftest.js
components: server

## Motivation
The engine still computed work state from the deleted verdict enum (`CLASSIFIED_VERDICTS`, `HELD`/`READY`/`SKEW`) and from `PROCESS_OUTCOME_OF` (`clean`/`crashed`/`killed`). Spec-state-store §4.2/§4.4 replace those with core's ending store plus §2 derived predicates.

## Design
New readers `ending-reads.js` (done-set = `ending=done`, hold-set = `seatWaitingOnOwner`, launchability via `isLaunchable`) and `owed-from-endings.js` (`classifyEnding` on `ending`+`armed`). `reconcile.js`/`seeding.js` consume those instead of growing the monoliths. `execution-record.js` keeps the session join and stops publishing a work outcome. `attached-execution.js` no longer writes `exited`. `laneIsPaused` reads `goal_states.stored='paused'` with a one-line file-prefix shim.

## How it works
Callers with a `heartStore` bind core's API (`state-store.bind(db)`). `readySeats` still transports coord's seed/after/dead rows but builds the ready map from endings. Class A owed work is `incomplete`+armed (relaunch that seat) or `failed` (leader nonterm); disarmed incomplete is not owed.

## Consequences
Deleted `PROCESS_OUTCOME_OF`, `RECORD_DISPOSITIONS`, `deriveOwed`, `isNonTerminal`, `CLASSIFIED_VERDICTS`. Probe-owner-ask-hold, probe-cross-lane-resume, probe-foreground-carrier, probe-engine-library, and probe-daemon-lane-watch still assert the old HELD/clean/exited seams and were not finished this sitting.

## Verification
Each edited engine `.js` file was compiled with `node --check` and exited 0. The rewritten `reconcile.selftest.js` printed `reconcile.selftest OK` end to end, including the ending+armed class-A split and the pause-gate red arm. Direct runs of `probe-verdict-vocabulary.js`, `probe-attached-status.js`, `probe-frozen-frontier.js`, `probe-enqueue-record.js`, and `probe-reconcile.js` each printed PASS. This sitting did not deploy.

## ATTENTION
- Absence of a current ending is launchable (`isLaunchable` with `ending=null`). A freeze fixture that used UNDECLARED must stamp `failed` + `leader_attempt_used=1` instead.
- `recordView`'s hold is `open_asks` posted+open, not coord `HELD`. A probe that only writes `messages.md` will see an empty blocked set.
- `execution-record` outcome is now empty on close. Anything still asserting `record.CLEAN`/`CRASHED` is reading a killed work word.
- Absent ending is launchable; UNDECLARED freeze fixtures must stamp failed-terminal.
