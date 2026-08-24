# 20260824-c-one-pause-record-the-goal-stat — One pause record: the goal-state row wins

kind: change
component: engine
date: 2026-08-24
commit: a0d7e42c
deployed: no
pin: NONE

## Motivation
Two records of "is this goal paused" existed and the FILE could win. `laneIsPaused` (`engine/lane-watch.js`) — the reader `reconcileGoal`'s pause gate and the ticker's dispatch gate both spend — consulted the ending store's goal-state row ONLY for a TRUE, then fell through to the first word of the `execution-lane` marker. So a goal whose stored row had been moved to `running` stayed frozen behind a stale `paused` word on disk, against the record that had actually been updated. Same shape as the two owed-work computers one function over (`20260824-c-one-owed-work-computer-one-lau`), and the family's brief named it as the convergence to make.

## Design
The row is the record: a goal the store knows about is answered by the store, and the marker is demoted to a shim for goals the store has never recorded.

`isGoalPaused` could not carry that, and the reason is the whole design decision: it flattens two different answers into one `false` — "the row says running" and "there is no row at all". Only the first is an answer. So the goal-state row is read directly through `api.getGoalState` and its EXISTENCE is the test; a row with a `stored` word decides, present or absent from `paused`. Absent or unreadable remains NOT paused on both surfaces, which is the pre-existing fail-safe direction and the reason `rbtv-goal pause` can still arm a goal that has no row yet.

Rejected: widening `isGoalPaused` to a tri-state (it is read by other callers who want the boolean, and changing its answer shape to fix one caller is how a predicate acquires two meanings); deleting the file shim outright (it would un-pause every goal predating the goal-state table at the moment of the change).

## How it works
`laneIsPaused(goalFolder, heartStore)` binds through `ending-reads.js#bindEnding` — which resolves the WORKSPACE store when the folder is a real `<ws>/.rbtv/goals/<goal>` and falls back to the lane store otherwise — reads `getGoalState(goalNameOf(goalFolder))`, and returns `row.stored === 'paused'` whenever a row with a stored word exists. Only a store that could not be asked at all reaches the `execution-lane` read below it.

## Consequences
Nothing was deleted: the marker path is intact and is still what `readLane` flattens for seeding. What changed is which surface wins when they disagree. The selftest arm also records a pre-existing quirk of the gate rather than hiding it: `laneIsPaused` takes no goal name and derives one with `goalNameOf(goalFolder)`, i.e. the folder basename. On a real goal that IS the goal name by construction; on a flat fixture it is not, and a row written under the caller's `goal` argument is invisible to the gate.

## Verification
`engine/reconcile.selftest.js` gains a two-armed row: with the marker reading `paused` and the goal-state row reading `running` the pass must NOT skip, and with the row reading `paused` and the marker reading `daemon` it must. One arm alone cannot tell a converged gate from a gate that reads nothing. The pre-existing "paused goal is not reconciled" row and its mutation red arm (deleting the pause gate enqueues a paused goal) both stay green. `engine/probes` after the change: 14 of 15, the one red being `probe-foreground-carrier`, which is red before and after and red on a pristine `git archive HEAD` checkout of the same tree. Not deployed — `ignite/core-redesign` worktree.

## ATTENTION
- `isGoalPaused` answers `false` for "no row" as well as for "running". Any caller converging a second surface onto the store must read the ROW, not that predicate, or it will treat an unrecorded goal as an authoritative not-paused.
- `laneIsPaused` keys the goal-state lookup on the folder BASENAME, not on any goal argument. A fixture whose folder name differs from its goal name writes rows the gate cannot see.
