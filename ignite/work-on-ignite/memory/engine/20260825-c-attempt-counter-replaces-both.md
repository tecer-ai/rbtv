# 20260825-c-attempt-counter-replaces-both — Attempt counter replaces both byte-equality brakes

kind: creation
component: engine
date: 2026-08-25
commit: 01196394,1cb188d3
deployed: no
pin: ignite/supervisor/attempt-counters.selftest.js
components: server,supervisor

## Motivation
Two brakes compared owed-content bytes that moved, so neither bound ever fired.

Two brakes, both dead on arrival. `reconcile.js`'s `strike()`/`stuckStands()` counted a retry only while the owed-set SIGNATURE stayed byte-identical, and `heart-store.js`'s `ADMISSION_BRAKE_LIMIT` door did the same comparison at `enqueue()`. Both signatures carried volatile fields (a re-checkout's `ended`, a session id, the argv-bytes floor `hashArgsFloor`), so a drifting field read as PROGRESS, reset the count, and the bound never fired — D88 hand-relaunched meet's leader at 219 attempts with `stuck_emitted=1` already set. spec-recovery §5 rules both out and names one replacement: a counter that increments on a same-reason retry and is reset ONLY by a named event.

## Design
One counter keyed on (driver, subject, reason CLASS) replaces both, reset only by a named event.

`ignite/supervisor/attempt-counters.js` keys a counter on `(driver, subject, reason CLASS)`. The reason class is the driver's failure/refusal class — `unknown-tool`, `incomplete`, `nonterm`, `unread`, `room` — never row content. `refuseVolatile` is a tripwire at the key builder: a class carrying an ISO timestamp, a uuid, an 8+ hex run or a 6+ digit number is REFUSED, so the old defect cannot be re-typed at a call site. `DRIVER_LIST` is closed (`ticker-deferred`, `reconcile-respawn`, `reconcile-class-a-relaunch`, `alarm-refire`) and `FROZEN_HOURLY_REPEAT` is a named driver `requireDriver` throws on — the [C-5] exclusion made mechanical rather than remembered. `RE_ARM_EVENTS` is the closed reset list; a deploy or config change clears everything, an owner/leader act or a `resume` clears one lane. N is always an argument, read by the caller from `recovery-config.js#loadRecoveryConfig().attempt_counter_n`; the module refuses a missing or non-positive `n` rather than defaulting. Storage is a small JSON object beside the module (`countersFile` overridable), written tmp-then-rename — NOT a table in the ending store (spec-state-store pins three record kinds there) and NOT `reconcile_attempts` (whose `signature` column is the deleted design).

`ignite/supervisor/exhaustion.js` is the exit at N: `stampSystem` with the diagnostic `attempt-counter exhaustion`, which is `state-store/vocabulary.js#LISTED_INCOMPLETE`'s own listed row and supplies `armed: 0` + `named_event`. Because that string is matched byte for byte, the refusal TEXT cannot be appended to it — it rides on the ask record the `evidence_pointer` names. The record is `{workspace}/.rbtv/runtime/ignite/asks/<ask-id>.json`, one per failure signature `(driver, reason class)`, appended-to for a second lane rather than duplicated, plus one `open_asks` row with `posted = 0`. No Slack, no outbox.

`ignite/supervisor/relaunch-budget.js` answers both caps off the ending row's own `failure_strike_count` / `recovery_relaunch_count`, so it cannot disagree with the row the scheduler reads. `spendRecoveryRelaunch` refuses `ask-resume` by name [C-11]. `leaderHandoff` refuses a payload missing any [T4-R6] field and sets `leader_attempt_used` in the same act, so the D6 rung is bounded by the store. `executeLeaderInstruction` performs one of exactly four instructions and refuses one carrying `work_product` / `patch` / `outputs` — the leader-decides-daemon-executes wall as code.

## How it works
Each driver counts its own retries. `ticker.js` gained `deferredRetry` / `deferredDisarmed` (inside `createTicker`) applied at four arms: the `unknown-tool` and `unknown-workflow` defers, and both `expandArgv` refusals (fire-tool and start-workflow). A disarmed job gets action `defer-disarmed` and does not re-fire. `reconcile.js` gained `driverFor` (class A `incomplete` → `reconcile-class-a-relaunch`, everything else → `reconcile-respawn`), `recoveryNumbers` (resolves the config once per pass off `heartStore.config.workspaceRoot`; a config error records a `detect` action and applies NO counter rather than falling back to a literal), `countRetry` (counts, and calls `exhaust` on N through `engine.endingStore`), and `counterDisarmed` (the brake — action `skip-disarmed`). `countersFile` threads through `reconcileGoal` exactly as `registryFile` does, so a fixture never writes the daemon's ledger.

## Consequences
Deleted: `strike`, `stuckStands`, `STRIKE_LIMIT`, `getAttempt`/`putAttempt`/`clearAttempt`, `sendStuck` and the end-of-pass `sweepSeats` clear in `reconcile.js`; `ADMISSION_BRAKE_LIMIT`, `BRAKE_REASON_FLOOR`, `hashArgsFloor`, the whole enqueue-time brake block and the now-unused `crypto` require in `heart-store.js`; the dead `enq.braked` refusal branch in `supervisor/launch-door.js`. The `reconcile_attempts` table survives untouched but has no writer on this path any more. `reconcile.selftest.js`'s D34 / D40 / D44 arms were rewritten rather than dropped, and two expectations INVERTED with the ruling: a changed owed set no longer resets the count, and the `skip-stuck` action is now `skip-disarmed`.

## Verification
`node --test ignite/supervisor/attempt-counters.selftest.js` (7/7) and `node --test ignite/supervisor/relaunch-budget.selftest.js` (6/6), both driving N and both budget caps off a config file seeded into a throwaway workspace, never a literal. `node ignite/engine/reconcile.selftest.js` prints `reconcile.selftest OK` with three new red-by-mutation arms: restoring the evidence-driven reset, putting a volatile field back into the counter key (the tripwire must throw `E_ATTEMPT_COUNTER`), and disabling the disarm brake. `probe-suite --dir server/heart/probes` 23/23 GREEN, `--dir server/ticker/probes` 27/27 GREEN, `probe-reconcile` PASS, `probe-suite --selftest` 26/26. Not deployed — worktree branch `ignite/core-redesign`, pre-cutover.

## ATTENTION
1. The refusal text is NOT in `diagnostic`. `stampSystem` matches `attempt-counter exhaustion` byte for byte to find the disarmed row in `LISTED_INCOMPLETE`; decorating it makes the stamp refuse. Follow `evidence_pointer` to the ask record for the words.
2. A changed owed set is NOT progress any more. The counter survives it by design — a seat re-derived for the same reason class three times disarms even if the ledger content moved every pass. That inversion is spec-recovery §5, not an oversight.
3. `FROZEN_HOURLY_REPEAT` is a refusal, not a driver. Passing it to `countAttempt` throws; that is how the [C-5] exclusion is proven rather than promised.
4. `reconcile.js` reads the ending store from `engine.endingStore`, which most existing callers do not pass. Without it the counter still counts and reports `exit: 'no-ending-store'` — it does not throw, and it also does not stamp.
5. The counter ledger is gitignored runtime state. A committed `attempt-counters.json` would hand another box a count it never earned and disarm a lane nobody ran.
- the refusal text is on the ask record, never in the stored diagnostic
