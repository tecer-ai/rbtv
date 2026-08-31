# 20260831-i-spawn-refused-row-parked-seedi — Spawn-refused row parked seeding as live forever

kind: issue
component: supervisor
date: 2026-08-31
commit: b10155e1
deployed: no
pin: ignite/supervisor/seeding.selftest.js

## Observed
`goal-memory-management`, 2026-08-23: daemon seed 04:46:21Z spawn REFUSED (exec 31629) because the
seat declared a model spelling no launch spec carried. `decisions.md` 10:40Z: "the failed row then
read as `live` to every later seeding pass ('coord says READY, store says live')" — the same
residual filed again 10:40Z after the model was hand-fixed: "a spawn-refused row parks the seeding
path as `live` with no re-offer." The only way out on record was a human removing queue 1591 and
editing the model pin by hand. Reproduced on HEAD with a fixture execution row
`{ status: 'failed', pid: null }` under a fixed `jobId` (`seat-<goal>-<seat>`, `jobIdFor` never
changes it on relaunch): `seatState` answered `live` — permanently, since nothing ever removes or
ages out a `jobs_log` row.

## Mechanism
`seatHasRun(rows)` (`seeding.js`) answered `Boolean(rows) && rows.length > 0` — ANY execution row
at all, including a `failed` row minted before a process ever existed. `owed.js#seatState` reads
`seatHasRun(byJob.get(jobId))` first, ahead of the `queued`/`ready` checks, so a single spawn
refusal made that seat's fixed `jobId` answer `live` forever, no matter what coord answers on any
later pass. Task 7.776 (`owed.js`'s own "THE DISAGREEMENT IS NOT A SILENT DROP" comment) turned the
resulting coord-says-READY/store-says-live disagreement into a NAMED launch-door refusal
(`storeDisagreeRefusal`, logged at `info` every pass) — visible, but still a dead end: the
disagreement loop in `seeding.js#launchOwed` never counts a retry, never escalates, never marks
anything terminal. The seat just sits, logged, forever — the exact residual the seed task names.
`doors.js#refuseLaunch`'s own invariant already states the fix's shape: "a refused launch is not a
dead seat" — `jobs_log.pid` is nullable and IS the existing, unused signal for exactly that
distinction: a row with no `pid` never became a real process.

## Attempts
First attempt held — checked: `owed.js`'s own header comment and the `disagreements`/
`storeDisagreeRefusal` wiring (task 7.776) — that fix NAMES the disagreement but does not resolve
the park, which is why the residual was filed again in the SAME 10:40Z decision rather than closed;
`doors.js#refuseLaunch` and `envelope/stamp.js#stampLaunchRefused` — considered stamping a goal-side
ending for every spawn-time refusal so `reconcile.js`'s class A could pick it up, REJECTED as
broader than needed and reaching outside this seat's assigned files (`spawn.js`), when the
`jobs_log.pid` signal already available in `owed.js`/`seeding.js` resolves the fast-path park on
its own without touching spawn-time stamping at all.

## Fix
`seatHasRun` now excludes a `failed` row that never carried a `pid`
(`isRefusedBeforeSpawn(row) = row.status === 'failed' && row.pid == null`) — such a row no longer
counts as "has run", so `seatState` falls through to `ready`/`queued`/`waiting` per coord's own
answer instead of reading `live` forever. A row that DID carry a `pid` (a real process, later
crashed) is UNCHANGED — it still counts as "has run" and stays `live` here, deferring to
`reconcile.js`'s class A / D42 "crashed seat is re-run in ONE act" (a leader-ruled path this fast
10 s graph pass must not race). Nothing in `spawn.js`, `owed-from-endings.js` or the ending store
was touched — the fix is entirely inside the existing `pid`-nullable column and the ONE function
(`seatHasRun`) both the fast graph half (`owed.js#seatState`) and the disagreement-naming loop
(`launchOwed`) already share.

## Consequences
A spawn-refused seat is now re-offered `ready`/`waiting` the very next pass coord re-answers it,
rather than needing a human to delete a queue row. The `store-disagree` refusal path
(`storeDisagreeRefusal`, `launchOwed`) still exists and still fires for the OTHER disagreement
shape it was built for (coord says READY while a genuinely live/crashed execution — one WITH a
`pid` — exists) — unaffected. No change to `seatIsFinished`, `owed-from-endings.js`'s class A, or
any ending-store consumer.

## Verification
`node ignite/supervisor/seeding.selftest.js` ALL PASS, including the new case
"a spawn-refused row (no pid) is re-offered, a crashed/running seat stays live, RED arm reproduces
the park": (1) a `{status:'failed', pid:null}` row → `seatHasRun` false → `seatState` returns
`ready` (coord's `ready` map has the seat); (2) DISCRIMINATING CONTROL — the same row WITH a `pid`
→ `seatHasRun` true → `seatState` `live`, not re-offered; (3) a genuinely `running` row (real `pid`)
→ `live`, unaffected; (4) RED — an in-memory mutant restoring the old `seatHasRun` body
(`rows.length > 0`) reproduces the permanent `live` park on the SAME pid-less fixture row, proving
the test discriminates the fix rather than passing regardless. Regression:
`node ignite/supervisor/owed-from-endings.selftest.js` ALL PASS (class A/B untouched — this fix is
entirely in the graph half). `node ignite/supervisor/probes/probe-enqueue-record.js` EXIT 0
(Arm A's `live-turn` suppression fixture uses a `running`, `pid`-bearing row — unaffected). Commit
`b10155e1` on `ignite/core-daemon`. NOT DEPLOYED.

## ATTENTION
1. The discriminator is `pid == null` on a `failed` row, NOT the `reason_class`/error text. Do not
   special-case specific refusal messages (model-pin spelling, cage refusal, carrier failure) —
   `pid` absence already covers every "refused before any process existed" shape uniformly, and a
   message-text match would miss whichever one is not yet on the list.
2. A `failed` row WITH a `pid` (a real process that later crashed) still reads `live` here on
   purpose — do not widen the exclusion to cover it. That case is `reconcile.js`'s class A / D42
   leader-ruled relaunch, a slower and deliberately gated path this fast graph pass must not race.
3. This does NOT touch whether a spawn-time refusal gets an ending stamped in the goal's own ending
   store (`envelope/stamp.js#stampLaunchRefused` is wired only to cage-refusal callbacks inside
   `spawn.js`, not to the launch-spec/model-pin refusal path that produced the ORIGINAL 2026-08-23
   incident) — `reconcile.js`'s class A therefore still cannot see this seat's history at all,
   because it also requires a `sessions.csv` row with a non-empty `ended`, which a refusal that
   never reached a real session never gets. That gap is real and unfixed by this entry; it only
   matters for the SLOW leader-ruled path, and the fast-path park this entry closes no longer
   depends on it.
- pid-nullable failed row = refused, not crashed; do not widen to pid-bearing rows
