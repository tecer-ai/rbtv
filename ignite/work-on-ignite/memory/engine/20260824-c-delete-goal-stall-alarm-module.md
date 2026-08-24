# 20260824-c-delete-goal-stall-alarm-module — delete goal-stall-alarm module [T4-R10]

kind: change
component: engine
date: 2026-08-24
commit: 2d7b0da0
deployed: no
pin: NONE
components: server

## Motivation
Design-baseline v2 [T4-R10] settles alarms behind ONE schema-enforced emitter; goal-stall-alarm.js
(the Q3a owner-alarm module, an ad-hoc Slack alarmer with an in-memory dedup Map that does not
survive a daemon restart) is superseded. This seat (del-observers) deletes the four settled-dead
observer subsystems from the D19 deletion batch; this entry covers the goal-stall-alarm removal.

## Design
Delete `server/ticker/goal-stall-alarm.js` outright (stallAlarmDecision, conditionOf, STALL_MS,
alarmState). Strip its require and every `alarmOnStall` call site from `engine/lane-watch.js`
(the LE-13 pre-seeding freeze branches: taskforce-unreadable, unbuilt-seats, cast-unreadable,
uncast-seats, seed-failed, and the post-seedGoal readiness call) and the owner-escalation call from
`engine/reconcile.js`'s `strike()`. `goalPeriodicFailureStreaks` in lane-watch.js is deleted too —
its only caller was the deleted `alarmOnStall`. No replacement alarm is built here; the new
schema-enforced emitter is impl-alarms' surface, and the dedup design may be copied later but is
not ported now.

## How it works
`strike()` in reconcile.js still runs the mechanical-attempt counter and the `sendStuck` escalation
to the leader at STRIKE_LIMIT attempts (D15) — that scheduling is untouched, only the further
owner-alarm leg beyond stuck (`OWNER_AFTER_STUCK`, now deleted as dead) is gone. lane-watch.js's
per-goal loop still logs `warn`/`debug` lines for every freeze condition via `shouldShout`'s
once-per-marker memo; only the Slack post is gone. `pickup.frozen` object literals built solely to
feed the deleted alarm were deleted with their call sites (nothing else read `pickup.frozen`).

## Consequences
`engine/probes/probe-enqueue-record.js` imported the deleted module for Arm C (posted/dedup
decision) and Arm D (condition-clears check). Arm C now asserts directly on
`pickup.enqueueUnfired` naming the seat; Arm D asserts `pickup.enqueueUnfired` is empty after the
fire — both now read the raw seedGoal record instead of routing through the deleted
conditionOf/stallAlarmDecision. `ticker.js#ensureGoalChannel`'s `{ decision }` calling convention
(added for this alarm's `perform({ decision })` call) is now unreached — left in place as
reusable plumbing a future emitter may use; not deleted here since ticker.js is not a named file
for this deletion and the convention is generic, not alarm-specific code.

## Verification
`node ignite/engine/probes/probe-enqueue-record.js` — PASS (all arms green). `node
ignite/engine/reconcile.selftest.js` — PASS. `node ignite/engine/probes/probe-daemon-lane-watch.js`
— PASS (all L1-L9 arms + mutation reds). `node --check` on lane-watch.js, reconcile.js,
probe-enqueue-record.js. Deployed: no (worktree only, `5-workbench/rbtv-redesign`,
branch ignite/core-redesign; live repo untouched).

## ATTENTION
1. `pickup.frozen`/`periodicFailureJobs` shapes are gone from lane-watch.js's producer branches —
   a future emitter reading old memory entries that cite `pickup.frozen` will not find it; it must
   re-derive its own alarm-input shape from `pickup` (states, skewed, readinessRefused, etc.),
   not resurrect the deleted producer literals.
2. `strike()` in reconcile.js dropped its `engine`/`pickup`/`now` parameters (unused once the
   alarm call was removed) — a caller adding them back without a consumer is dead plumbing again.
3. `ticker.js#ensureGoalChannel`'s `{ decision }` branch is now unreached at HEAD — do not assume
   it is exercised by any current caller; the only caller (`{ job }`) never sets it.
