# 20260824-c-one-owed-work-computer-one-lau — One owed-work computer + one launch door

kind: creation
component: engine
date: 2026-08-24
commit: c44d79a2
deployed: no
pin: engine/probes/probe-verdict-vocabulary.js
components: server,team-kit

## Motivation
Two functions answered "is this seat owed a launch?" and both called `heartStore.enqueue` (CODE-GROUND-TRUTH §4). `engine/seeding.js` `enqueueEligible` ran a ~10 s graph pass (whose `after` is satisfied, who has never fired) behind five pre-queue gates of its own; `engine/reconcile.js`'s ledger classifier ran a ~300 s pass over class A (non-terminal ending) and class B (unread mail). They read different pictures and could disagree, and when they did nothing could adjudicate: a seat "not owed" by one and "owed" by the other simply behaved differently depending on which cadence fired next. spec-supervisor §5 rules the survivor [T4-R7, C-15]: `deriveOwed`, supervisor-owned, carrying graph-derived launchability [T1-R3].

## Design
`ignite/supervisor/owed.js` holds `deriveOwed(goalFolder, opts)` — one function, three classes. Classes A and B come from `classifyOwed` with the watcher's ledger readers handed in; class R is the graph half, which is `seatState` and the ready loop MOVED out of `enqueueEligible` rather than re-derived. Both halves are optional because the two cadences ask different questions of the same computer: the watcher hands in `ledger` and reads A/B, seeding hands in `graph` and reads R. Two callers of one computer is the design; two computers was the defect. The record readers are injected rather than required because they live under `engine/` and a top-level require from `supervisor/` closes a load cycle through `seeding.js`.

`ignite/supervisor/launch-door.js` holds what the retired computer left behind. Its gates became refusals on the wrapped spawn, never a second owed set: a refusal answers "this launch does not happen", never "this seat is not owed work", so the seat stays owed and the next cadence asks again. `launchThroughDoor` is the one enqueue on the owed path; it CALLS `heartStore.enqueue` and reads its verdict rather than replacing it, because D52's admission brake lives inside `enqueue()` and is fail-closed with no opt-out.

Rejected: deleting `enqueueEligible` outright and letting the ~300 s watcher cover first launches (it would have moved every first launch from a 10 s cadence to a 300 s one); giving seeding's launches a `reason` token (it would silently widen their admission-brake budget away from the merged `door:__enqueue` floor they have always shared); re-exporting `deriveOwed` from `reconcile.js` (a second address for the survivor is how a second computer comes back, and `probe-verdict-vocabulary` now refuses it).

## How it works
`seedGoal` still runs its own cadence and still owns its reporting — the frozen-frontier arithmetic, the four held-for-a-reason sets, the seed map. What it no longer does is compute or enqueue: `launchOwed` (`engine/seeding.js`, formerly `enqueueEligible`) asks `deriveOwed` for class R, runs each seat through `admitLaunch`, and launches through `launchThroughDoor`. `reconcileGoal` calls `owedFromLedgers` (`engine/reconcile.js`), which is `deriveOwed` with the ledger readers, and `launchSitting` now composes the request and hands it to the same door.

Refusal kinds, in the order the gates always ran: `store-disagree` (coord ruled READY while this store holds an unfinished execution row — the store may decline, never promote), `hold`, `cage-admit`, `lane-reach`, `boot-prompt`, then the store's own `store-dedup` and `braked` on the far side. `enqueued_by` is read off `doors.js`'s door list by the caller and passed through, so it can only ever be a value `doorForLauncher` turns back into a door name at the pid moment.

`probe-verdict-vocabulary.js` changed shape with this: `deriveOwed` moved from banned-outright in engine product files to banned-as-a-DEFINITION. An engine file may sit on the require line that names `supervisor/owed`, or call it; a `function deriveOwed`, an assignment or a re-export is the second computer coming back.

## Consequences
`enqueueEligible` is gone as a symbol — `engine/attached-execution.js` and five engine probes were swept to `launchOwed` in the same change, and `doors.js`'s seeding chokepoint string and `heart-store.js`'s grammar comment were repointed with them. `seatState` now lives in `supervisor/owed.js` and is re-exported from `seeding.js` with its old four-argument signature, so no caller of the wave predicate learned a new name. Seeding's suppression path gained the `braked` verdict it never handled: a braked enqueue used to fall through and be counted as enqueued.

`reconcile.js` no longer exports a `classifyOwedFromLedgers`; the name is `owedFromLedgers`, and `reconcile.selftest.js`'s twelve call sites moved with it.

## Verification
`reconcile.selftest.js` carries the guard and it is red-able: `seeding.js`, `reconcile.js` and `supervisor/owed.js` must hold ZERO live `.enqueue(` calls and `launch-door.js` exactly one, with comments stripped first (this repo's headers discuss `heartStore.enqueue` constantly and a checker counting those would be green for the wrong reason). The red arm re-adds a second enqueue to seeding's source and asserts the checker sees it. A second arm drives `deriveOwed` with both halves and asserts class R is the graph answer while A and B come back from the same call. The exported-symbol arm asserts `seeding.enqueueEligible` and `attached.enqueueEligible` are `undefined`.

Full worktree suite after the change, chunked: 200 discovered, 193 passed, 5 failed, 2 inoperative. All seven non-green rows attributed to causes older than this change — `probe-foreground-carrier` (B1a/B1j wall-clock arms, reproduced RED on a pristine `git archive HEAD` checkout), the two `probe-coord-selftest` probes (red at handover), `probe-lifecycle-idents` (reproduced RED on the same pristine checkout), `probe-bindings` and `probe-master-profile` (both recorded non-green in the run's own baseline), and `probe-execution-mode-birth` (INOPERATIVE on the pristine checkout too). Every `*.selftest.js` in the tree passes. Not deployed: this is the `ignite/core-redesign` worktree and the cutover seat owns the restart.

## ATTENTION
- `deriveOwed` MUST NOT enqueue, and the ban is structural rather than stylistic: an owed set is a statement, not an act, and the moment the computer can also launch a second launch path exists by construction. `reconcile.selftest.js`'s single-computer arm is what holds it.
- Do NOT route the owed path around `HeartStore.enqueue()`. D52's admission brake lives inside it, is fail-closed and has no opt-out; a direct queue write or a trusted-caller flag reopens the 356-sitting burn (`20260822-c-admission-brake-door`).
- Seeding's launches deliberately carry NO `reason`, so they share the merged `door:__enqueue` brake floor. Adding one is looser, not tidier, and changes a live budget.
- The graph half is class R of the ONE computer, not a seeding-local predicate. Re-deriving readiness inside `engine/` — even "just to filter first" — recreates the two-computers shape this entry exists to close.
