# 20260824-c-ending-store-stamp-api — Ending store stamp API

kind: creation
component: server
date: 2026-08-24
commit: 28c464b0,3b2469cf
deployed: no
pin: ignite/state-store/ending-store.selftest.js

## Motivation
Four independent work-state machines (disposition, verdict, `jobs_log.status`, process `outcome`) plus dual writers made wait and launchability untrustworthy. The redesign baseline closes the stored set: three seat endings, three goal words, derived wait. This creation is the store those later seats must read and write — not a reader migration.

## Design
Tables `seat_endings`, `seat_endings_log`, `goal_states`, and `open_asks` live in the existing `heart.db` host (`heart-store.js` execs one `tables.sql`; migration 10 walks existing stores). Write and read APIs live in `ignite/state-store/` so `heart-store.js` is not grown into a second product. Rejected: a fifth database, per-goal `heart.db` as a writer, and dumping stamp logic into the 2320-line heart-store monolith (named leftover; map says no body split this plan).

## How it works
Callers `openHeartStore` then `bind(db)` from `ignite/state-store`. `stampSeatDeclare` / `stampSystem` refuse a second current row (`E_WRITE_ONCE`); `replaceSeatEnding` archives to `seat_endings_log` in one transaction. Seat declare of `done` runs `checkDoneOutputs` and rewrites to `failed:outputs-missing` when a declared path is missing or empty. `reapAndRelaunch` flips `answered` then `closed` in the same transaction (idempotent on `ask_id`) and arms a matching `ask-answered` incomplete. Derived readers (`seatWaitingOnOwner`, `goalWaitingOnOwner`, `isLaunchable`, `killClockPauses`) never persist those words. Runtime path helper: `endingStorePath(workspaceRoot)` → `.rbtv/runtime/ignite/heart.db`. Kit door: `cli.js --db --op --payload`. Cutover copy: `copyHeartHome` — do not run against a live daemon.

## Consequences
No legacy reader was retargeted (kit/engine/periphery own that). `jobs_log` stays the history/turn table. `ignite/module.md` gained an ending-store row in the working tree but was not committed: parallel seats (planning, envelope) also edited that file. Daemon `dbPath` still opens `{data_root}/heart.db`; cutover/periphery switch the live open to the runtime home.

## Verification
`node --check` on every new/edited `.js` file. `node ignite/state-store/ending-store.selftest.js` printed PASS for every required derivation case plus killed-vocabulary and copy-home. `probe-migration.js` still exits 0 after LATEST became 10. Not deployed (`deployed: no`).

## ATTENTION
- A second `stampSeatDeclare`/`stampSystem` on a current `(goal, seat)` is refused; a new sitting must call `replaceSeatEnding` or pass `replace: true`. Calling stamp again looks like a flake; it is write-once.
- `answered` must never be visible after `reapAndRelaunch` returns. If you persist `state='answered'` as a resting value you have split reap from relaunch.
- `copyHeartHome` refuses an existing dest and must not be pointed at a live daemon `{state_root}/heart.db` as dest. Sources are read; dest is created.
- `goalWaitingOnOwner` takes caller-supplied `canAdvance`. This store does not walk the task graph; lying about `canAdvance` mints a false wait.
- `failed:crash` without a non-empty `evidence_pointer` is refused. Death-truth must name the observed death.

2026-08-31 addendum: superseded on the store location — since 361a56f2, openAsk/reapAsk/listOpenAsks resolve the workspace ending store (`<workspace>/.rbtv/runtime/ignite/heart.db`); the lane-store `open_asks` copy was drained (rows copied over, table emptied) on 2026-08-31. Read the store location from `ask-record.js`, not from this note.
