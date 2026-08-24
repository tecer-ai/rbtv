---
description: One ending store — seat endings, goal words, open asks, and derived predicates.
---

# state-store

The ONE ignite ending store. Record shape and predicates are law in
`1-projects/build-ignite/redesign/specs/spec-state-store.md`. Tables live inside
the host `heart.db` opened by `ignite/server/heart/heart-store.js`. This folder
is the write/read API siblings consume.

Runtime file (workspace-relative, GENERAL): `.rbtv/runtime/ignite/heart.db`.

## APIs

Write: `stampSeatDeclare` · `stampSystem` · `replaceSeatEnding` · `writeGoalWord` ·
`insertAsk` · `postAsk` · `reapAndRelaunch` · `incrementRecoveryRelaunch` ·
`setLeaderAttemptUsed` · `fireNamedEvent`

Read: `getCurrentEnding` · `getGoalState` · `getAsk` · `seatWaitingOnOwner` ·
`goalWaitingOnOwner` · `countOpenAsks` · `isGoalPaused` · `isGoalRunning` ·
`isGoalFinished` · `isLaunchable` · `checkDoneOutputs` · `killClockPauses` ·
`endingStorePath`

Kit/engine door: `cli.js` (`--db` `--op` `--payload`). One-shot cutover copy:
`copy-home.js` (do not run against a live daemon).
