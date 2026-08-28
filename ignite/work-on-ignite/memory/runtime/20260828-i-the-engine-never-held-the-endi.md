# 20260828-i-the-engine-never-held-the-endi — The engine never held the ending store

kind: issue
component: runtime
date: 2026-08-28
commit: eb0e4828
deployed: no
pin: ignite/runtime/probes/probe-engine-ending-store.js
components: supervisor,state-store

## Observed
Every production reconcile pass ran with NO ending store, and had since the field was introduced.
Measured 2026-08-28 05:16-05:49Z against deployed HEAD 26f4510e (repo HEAD identical), while the
acceptance wave's test 14 ran `scratch-death-recovery-1-exec`. Three consequences were live on the
box at once. First, `<workspace>/.rbtv/runtime/ignite/leader-instructions/` held FOUR pending
answers — `cp2-verify-scratch--goal-master.json` (13:24Z 08-27),
`goal-memory-management--distill-ignite-memory.json` (11:51Z 08-27),
`scratch-tool-reach-note--plan-verifier.json` (19:36Z 08-27) and
`scratch-death-recovery-1-exec--cadence-writer.json` (05:28Z 08-28) — against ZERO
`LEADER INSTRUCTION was applied/REFUSED` lines in the daemon journal for the whole wave: four
leaders had ruled and no ruling had ever been executed. Second, the one ask record on disk
(`asks/recovery-e0db9b5e7fd9.json`, opened 2026-08-27T19:33:20Z) carries, on both of its lanes,
the refusal text `the lane could NOT be stamped (no ending store on the pass)`, and `seat_endings`
held not one `incomplete`/`disarmed` row for either — the disarm existed only as a counter row in
`supervisor/attempt-counters.json`. Third, all 40 rows of the ending store read
`recovery_relaunch_count = 0` and `leader_attempt_used = 0`, so the `relaunch_budget_failures: 2`
/ `relaunch_budget_total: 5` caps seeded in `recovery.json` had never counted anything.
Three earlier fix seats had each disclosed the same absence without owning it: 348ebf7e ("the exit
at N never ran"), 5aa80168 ("a disarmed lane exists only as a counter row"), and
`20260825-c-attempt-counter-replaces-both` ATTENTION 4.

## Mechanism
`supervisor/reconcile.js:794-796` resolves `const endingStore = (engine && engine.endingStore) || null;`
and gates SEVEN branches on it — the B11 leader-instruction drain (`:835`), the relaunch-budget
question and its leader handoff (`:1010`, `:1027`), the disarm announcement's `stamped` flag
(`:1099-1104`), the recovery-budget spend (`:1130-1133`) and both `countRetry` calls (`:1179`,
`:1222`). `runtime/engine.js`'s `createEngine` is the composition root that builds the object that
read names, and it mentioned `endingStore` ZERO times: it opened the LANE store
(`openHeartStore({dbPath})`, the daemon's `{data_root}/heart.db`), threaded three facts onto
`heartStore.config` — `workdirRoot`, `launchSpecs` and `workspaceRoot` (`:97`, `:101`, `:105`,
the last from `spawnManager.workspaceRoot`) — and returned `{heartStore, spawnManager, ticker,
dbPath, tick, …}` with no such key. `grep -rn "endingStore\s*=" ignite/runtime ignite/supervisor`
returned that single READ and no write anywhere.

The contract REQUIRES the value rather than permitting its absence — `reconcile.js:794` names
`engine.endingStore` as "the ONE store the exhaustion exit stamps through [spec-state-store §1.1]",
and every consumer is written to spend it — so the wrong value is born at the producer that never
produced it, not at any consumer. The absence was invisible to the whole probe estate for a
structural reason worth naming: every existing fixture INJECTS `engine: { heartStore, endingStore }`
by hand into `reconcileGoal` (`reconcile.selftest.js:1387`, `:1433`;
`probe-leader-wake-counter.js`), so a suite that supplies the very fact production lacked can be
green while production is dark. `reconcile.selftest.js` cannot even reach those arms today: it
aborts at `:392` and, measured here for the first time, at `:1017`, `:1123`, `:1124` and `:1130`
as well — five pre-existing top-level asserts, so the B11 drain arm has never run since it landed.

## Attempts
First attempt at the FIX held; the absence had been REPORTED three times without being closed, and
each report is checked here. 348ebf7e (`20260827-i-new-staff-mail-counted-as-a-re`) made the disarm
AUDIBLE and explicitly routed the `no-ending-store` branch through `announceDisarm` — it made the
dark branch speak rather than removing the dark branch, deliberately, because its walls were the
counter. 5aa80168 (`20260827-c-the-four-named-re-arm-events-g`) made `rearmScope`'s `store`
OPTIONAL for the same stated reason ("nothing in the deployed tree sets `engine.endingStore`"),
which is a workaround the store's arrival does not invalidate — `rearmOnCodeDeploy` still passes no
store, so the boot re-arm still performs only the counter half. 4ed8acc8
(`20260826-c-the-retry-budget-handoff-to-th`) BUILT the drain and gated it on a store nobody
supplied. 919be192 (`20260828-i-pause-wrote-a-store-the-lane-g`) is the closest prior art and the
one that settles the design question here: it fixed the SAME class of defect for
`state-store/heart/pause-resume.js` by deleting the caller-supplied store handle and resolving
`openEndingStoreFor(workspaceRoot)` instead. Also checked: `20260825-c-attempt-counter-replaces-both`
(ATTENTION 4 recorded the gap), `20260828-c-laneispaused-two-pause-writers`, and spec-recovery §5.

## Fix
`createEngine` binds the ending store immediately after it learns the workspace root, and hands it
out as `engine.endingStore`. The whole change is one `try` around
`bind(openEndingStoreFor(heartStore.config.workspaceRoot))` plus one key on the returned object —
placed at the composition root because that is where the reconcile contract says the engine holds
it, and because BOTH attachments (the daemon and `rbtv run`) pass through this one function.

`openEndingStoreFor` and NOT `supervisor/ending-reads.js#bindEnding`, and that is the load-bearing
choice. `bindEnding` is the READER's resolver: when the home cannot be opened it FALLS THROUGH to
the caller's lane store, which is the fail-safe direction for "nothing declared" and precisely the
wrong file for the WRITER this handle is — `stampSystem`, `insertAsk` and `incrementRecoveryRelaunch`
all ride it, and a writer bound to the lane store reports success while changing a file no reader
reads. That is the 919be192 defect exactly, and its ATTENTION 2 forbids the reuse by name.
`openEndingStoreFor` is the shared half both sides already resolve through
(`state-store/paths.js#endingStorePath` underneath), so there is ONE resolution and not a third.

An unopenable home yields `null` and ONE `error` log line, never a throw — the opposite direction
from 919be192's writer, and deliberately so: `pauseResume` answers a single owner verb and can
honestly refuse it, whereas this is the daemon's boot. Every consumer is already written for
absence (each `reconcile.js` branch gates on the store; `countRetry` reports `exit: 'no-ending-store'`),
so the degraded daemon is exactly today's behaviour, and a boot that died here would trade a
degraded recovery path for no daemon at all. Rejected: threading the store in from
`runtime/index.js` as a fourth argument — the engine already holds `workspaceRoot` and a second
resolution site is the thing 919be192 removed. Rejected: closing the handle in `engine.close()` —
`state-store/open.js` caches ONE handle per file per PROCESS and `bindEnding` hands out that same
handle on every lane pass, so closing it from the engine would take the store out from under every
other reader in the daemon.

## Consequences
Nothing was deleted and no signature changed; `createEngine` gained one key. The blast radius is
the FIRST BOOT, and it was enumerated against the live ledger before the commit. The lane-pause
gate (`reconcile.js:812`) runs BEFORE the drain, and seven of the eight goals carrying state read
`paused daemon` in their `execution-lane` file — so of the four pending leader answers exactly ONE
drains: `goal-memory-management--distill-ignite-memory.json`, kind `escalate`, which records a
signature-grouped ask and moves the file to `done/`. It stamps no seat and relaunches nothing. The
budget branch cannot fire on any live lane (max `failure_strike_count` = 1 against a cap of 2, max
`recovery_relaunch_count` = 0 against 5), and there is not one `incomplete` row in `seat_endings`,
so no class-A relaunch and no `spendRecoveryRelaunch` is owed. The disarm branch stamps nothing on
the first pass either, and for a reason that is NOT this change: `rearmOnCodeDeploy` fires on any
deploy and clears all five counter rows, so both disarmed lanes re-arm and count from zero again —
`goal-memory-management`'s leader will be woken on the ordinary cadence and will reach N=3 in
roughly three passes, and THAT disarm is the first one that stamps for real.

Two siblings of the same cause are surfaced and NOT fixed here, both outside these walls.
`runtime/code-deploy-rearm.js:81` still calls `rearmScope` with no `store`, so the boot re-arm
performs the counter half and leaves any `disarmed` ending row standing; the store it needs is now
available at `index.js:738`, one argument away. And `state-store/heart/ask-record.js#listOpenAsks`
binds `heartStore.db` — the daemon's PRIVATE lane store — while `recordGroupedAsk` now inserts its
`open_asks` row into the ENDING store, so the two ask tables are split exactly as pause/resume was;
the workspace `open_asks` table is empty today and the private one holds 8 rows.

## Verification
Commit `eb0e4828` on `ignite/core-daemon`. `runtime/probes/probe-engine-ending-store.js`, new,
14/14 EXIT=0, offline: a scratch workspace whose LANE store is a different file from the ending
home (the split section (h) of `probe-pause-resume` exists for the same reason — a fixture that
passes the home in as `dbPath` cannot tell the two bindings apart). It proves the key exists and
carries the writer half; that the home was created at `<workspace>/.rbtv/runtime/ignite/heart.db`
and is NOT the lane store; that a `stampSystem` disarmed row and a `writeGoalWord` goal word
written through the engine's handle are read back OUT OF THE FILE by a second, independent handle;
that `close()` leaves that handle open; and that an unopenable home (the parent made a regular
file) and an unresolvable workspace each yield `null` plus exactly one error line with the engine
otherwise whole. Red mutation on a discarded copy: removing the `endingStore` key reddens 7 of the
14 arms, green again on restore.

Unchanged before and after, each measured on a pristine `git archive`-equivalent copy of 26f4510e
first: `probe-start-execution` 20/20, `probe-pause-resume` 53/53, `probe-intent-drift` PASS,
`probe-code-deploy-rearm` 13, `probe-leader-wake-counter` 26/26, `probe-chat-glance-wiring` 20,
`probe-chat-glance` 30, `state-store/ending-store.selftest` EXIT 0, and 12 of 13 supervisor
selftests EXIT 0. `reconcile.selftest.js` is EXIT 1 before and after with byte-identical output
apart from the tree path. Run with the five pre-existing aborting asserts neutralized on a scratch
copy, it reaches `reconcile.selftest OK` with 37 ok lines at BOTH trees, and the two B11 arms — the
budget handoff and `leader-instruction-applied` after a real drain — pass identically. tmux session
list byte-identical (18 sessions, diff empty). NOT DEPLOYED at filing; the DAEMON is the unit that
must restart, because the engine, the dispatcher and the reconcile pass all boot from
`/home/henri/.local/state/rbtv-deploy`.

## ATTENTION
1. THE STORE IS RESOLVED FROM `workspaceRoot`, NEVER HANDED IN, and `bindEnding` must not be
   reached for here. `bindEnding` falls through to the caller's LANE store when the home cannot be
   opened — correct for a reader answering "nothing declared", fatal for this handle, which stamps
   endings, inserts asks and increments the recovery budget. A writer pointed at the lane store
   reports applied and changes a file no reader reads; that is the whole of 919be192.
2. `null` IS A SUPPORTED VALUE AND EVERY CONSUMER STILL GATES ON IT. The engine must not throw when
   the home is unopenable: this is the daemon's boot path, and a hard failure here costs the whole
   daemon to save a recovery path that was inert for weeks. Any future edit that makes the store
   mandatory must first prove no reachable configuration lacks a workspace root.
3. THE ENDING HANDLE IS PROCESS-CACHED AND SHARED. `state-store/open.js` keeps one handle per file
   per process and `bindEnding` returns that same handle on every lane pass. Adding
   `closeEndingStores()` to `engine.close()` "for symmetry with `heartStore.close()`" would close
   the store out from under `laneIsPaused`, `readyFromEndings` and the pause-resume executor.
4. A GREEN RECONCILE FIXTURE PROVES NOTHING ABOUT THIS. Every reconcile probe and selftest injects
   `engine: { endingStore }` by hand, which is exactly how the estate stayed green for weeks while
   production ran dark. The composition root is measured by `probe-engine-ending-store.js` and by
   nothing else; deleting it removes the only arm that can see this class of defect.
5. `reconcile.selftest.js` ABORTS AT FIVE PLACES, NOT ONE. `:392`, `:1017`, `:1123`, `:1124` and
   `:1130` are top-level asserts, so everything below the first one — including both B11 arms — has
   never run in an ordinary invocation. Reading "reconcile.selftest EXIT 1" as one known red
   understates it by four, and any claim that a B11 arm is green must say how it was reached.
- createEngine resolves the ending store from workspaceRoot only — bindEnding's lane-store fall-through is a READER's fail-safe and must never be reused here
