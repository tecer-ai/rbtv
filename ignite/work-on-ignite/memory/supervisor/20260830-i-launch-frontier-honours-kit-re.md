# 20260830-i-launch-frontier-honours-kit-re — launch frontier honours kit READY verdict

kind: issue
component: supervisor
date: 2026-08-30
commit: 7070ba59
deployed: no
pin: ignite/supervisor/probes/probe-seed-gates.js

## Observed
Owner ruling D-12 (a), 2026-08-30 (`live-acceptance-tests/checkpoints/wave-close-decisions.md`, report row D-12, family B-9): the daemon's "which seats may launch" pass ignored the coordination kit's per-row verdict and only excluded summoned seats by name. A seat the kit ruled HELD, STOPPED, UNDECLARED, SKEW, RUNNING or IDLE could still be launched if the ending ledger and `after` read clean. Measured at `ignite/supervisor/seeding.js#readySeats` calling `ending-reads.js#readyFromEndings`. Deployed vs HEAD: the defect is on `ignite/core-daemon`; this sitting did not deploy.

## Mechanism
`readyFromEndings` rebuilt the launchable Map from `isLaunchable` over the ending store plus each row's `after` column and read nothing off the row's `verdict`. `seeding.js` already trusted that verdict for waitable-work comments and for pending classification, and distrusted it for launch. The 2026-08-27 D24 patch (`91da4a8d`) then deleted summoned names from that ledger-derived Map, which closed IDLE only for chairs on `SUMMONED_SEATS` and left every other refused verdict launchable.

## Attempts
The narrow fix is `91da4a8d` (filed `20260827-i-summoned-goal-master-chair-see`). Its ATTENTION 1 said `readyFromEndings` still ignores coord's `verdict` and that honouring the field wholesale belonged in its own change — this sitting is that change. Also checked: `ready.py#ready_seat_rows` docstring (precedence SKEW > HELD > DONE / RENEWING / RENEW-BLOCKED > RUNNING > UNBUILT > UNDECLARED > STOPPED > BLOCKED > READY, plus IDLE for on-demand chairs) and the comment at `seeding.js` that named this as the seam every frontier consumer passes through.

## Fix
The launchable set is `{ rows with verdict === READY }`, carrying each row's `seed`. `readyFromEndings` keeps the name and becomes the CROSS-CHECK it can honestly be: a READY row whose current ending is `done` is omitted (a SKEW the kit should have raised) and journalled, not launched. The summoned-name delete is gone; IDLE is honoured at the door. `summonedExcluded` stays on the return and is derived from IDLE rows so the journal field stays true (`reconcile.js` pass line now reads `readyAnswer.summonedExcluded`). `VERDICT_DOOR` in `seeding.js` is the one table `probe-verdict-vocabulary.js` binds to every live `ready.py` assignment — only READY is launchable. Rejected: keeping the name-delete beside a READY filter (two answers to one question); a second waitable table.

## Consequences
A staff `leader` with no mail is IDLE and is no longer cold-seeded (W3); `probe-seed-gates` arm 8b's control is now the root plan seat, not `leader`. Summoned IDLE chairs keep the D24 journal line; other refused verdicts are journalled once per process with the kit's reason. The freeze-alarm waitable filter still uses `isPendingWork`, not `VERDICT_DOOR.waitable` — left as-is so `probe-frozen-frontier`'s D22 anchor stayed. NOT DEPLOYED: DAEMON must restart after deploy; this sitting did neither.

## Verification
`seeding.selftest.js` (new) ALL PASS — door table, READY-only frontier, journalled refusals, READY+done SKEW, red map that would have launched the refused seats. `probe-seed-gates.js` EXIT 0 including arms 8a–8e and arm 9 (HELD/STOPPED/UNDECLARED/IDLE/SKEW/RUNNING none enqueued; READY seed; done-ending contradiction; red mutation ignoring verdict). `probe-verdict-vocabulary.js` 73/73 (was 45/45) binds every live kit word. `probe-daemon-lane-watch.js` D-12 arms ok; L9 M9 still red (pre-existing). All `ignite/supervisor/*.selftest.js` still green except pre-existing `reconcile.selftest.js:392`. `probe-lane-watch-yield.js` PASS. Four paused real goals untouched. Deployed: no.

## ATTENTION
1. `readyFromEndings` now means "READY rows, minus a done-ending contradiction". A caller that still thinks it recomputes the DAG from `after` will launch the wrong set — the DAG lives in `ready.py`.
2. Honouring IDLE stops cold-seeding `leader`. Mail is the wake for staff chairs (`reconcile.js` class B); do not put `leader` back on the seeding frontier to make a probe green.
3. `VERDICT_DOOR.waitable` is the contract `probe-verdict-vocabulary` binds; the freeze alarm still filters through `isPendingWork`. Editing one without the other reopens the D25 IDLE-as-pending false positive.
4. `summonedExcluded` is IDLE seats, not `SUMMONED_SEATS`. A journal consumer that treats the field as "goal-master only" will now also see an idle `leader`.
- readyFromEndings now means READY rows minus a done-ending contradiction. A caller that still thinks it recomputes the DAG from after will launch the wrong set — the DAG lives in ready.py.
- Honouring IDLE stops cold-seeding leader. Mail is the wake for staff chairs (reconcile.js class B); do not put leader back on the seeding frontier to make a probe green.
- VERDICT_DOOR.waitable is the contract probe-verdict-vocabulary binds; the freeze alarm still filters through isPendingWork. Editing one without the other reopens the D25 IDLE-as-pending false positive.
- summonedExcluded is IDLE seats, not SUMMONED_SEATS. A journal consumer that treats the field as goal-master only will now also see an idle leader.
