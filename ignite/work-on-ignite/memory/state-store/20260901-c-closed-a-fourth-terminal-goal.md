# 20260901-c-closed-a-fourth-terminal-goal — closed — a fourth terminal goal word, close-goal intent

kind: creation
component: state-store
date: 2026-09-01
commit: 96acd304
deployed: no
pin: ignite/chat/probes/probe-disposition-post.js
components: chat,runtime,supervisor

## Motivation
`d-goal-closed-word` (owner ruling, 2026-09-01, `redesign-continue-1`), following `disposition-post`'s
(756e29d5) own stop condition: the close-or-keep ask's `close` reply released the ask but performed
no daemon-side act — `state-store/vocabulary.js#GOAL_WORDS` was a closed three-word enum
(`running`/`paused`/`finished`), `finished` is the ONLY terminal word and every downstream reader
treats it as ordinary success, and `d-recovery-last-lane-asks` forbids a given-up goal ever reading
that way. `disposition-thread.js#closeGoal` shipped `null` on purpose, the same shape
`dropLane`/`retryWithChange` carried before their own seats built them.

## Design
`GOAL_WORDS` gains a fourth, TERMINAL word `closed`, owner-stamped exactly like `paused`
(`writers.js#writeGoalWord` refuses it from `who_stamped !== 'owner'`) but with no resume path,
unlike `paused`. Rejected: a sibling table (the `seat_abandonments`/`seat_holds` precedent
`dl-abandoned-outcome`/leader-hold used) — that shape fits a genuinely SECOND fact type; `closed`
is the FOURTH value of the SAME column `GOAL_WORDS` already names, and the ruling's own words
("GOAL_WORDS gains a fourth word") plus every reader's `stored === 'X'` shape both require it
live in `goal_states.stored` itself, not a second table splitting one fact in two
(`no-duplicate`). The daemon-path skip is modeled on `paused`, NOT `finished`: `finished`'s skip
reads an append-only EVENT (`finishEvent`, `messages.md`'s `FINISH_MARKER`) because nothing
reliably stamps `stored='finished'` in production (live heart.db had zero such rows before this
change — `20260831-i-finished-goals-resurrected-aft`); `closed` has no such reliability gap
(`close-goal`'s executor is the ONE writer, exactly like `pause-resume.js` is for `paused`), so
`reconcile.js`/`lane-watch.js` trust the stored word directly via a new `laneIsClosed` reader,
sibling to `laneIsPaused` minus its legacy-prefix migration (which is pause-specific history that
does not apply to a brand-new word).

The `close` reply's daemon-side act is a NEW, SEVENTEENTH gateway intent, `close-goal`
(`state-store/heart/close-goal.js`) — not a third `pause-resume` verb (that door's own header
keeps its verb enum closed to a mechanical, reversible pair; closing answers a specific
disposition ask and has no undo) and not a call the bridge makes in-process (`chat/
probes/probe-chat-boundary.js` forbids `chat/` reaching the store — `openHeartStore`/`heart-store`
are literally forbidden-pattern hits there). Mirrors `drop-lane`'s full wiring shape exactly:
`gateway/parse.js#parseCloseGoal` + `INTENTS`, `internal-api/dispatch.js#handleCloseGoal` +
`INTENTS`, `internal-api/authz.js#canCloseGoal` (bridge-only, same shape as `canDropLane`/
`canPauseResume`), the executor `bind(openEndingStoreFor(workspaceRoot))` (the file the lane gate
actually reads — `pause-resume.js`'s "THE ENDING HOME" note is the full argument for why NOT
`heartStore.db`).

## How it works
An owner `close` reply → `disposition-thread.js#dispatch` → `chat-bridge.js`'s `closeGoal` port →
`forwarder.forward('close-goal', {goal, ask_id})` → `handleCloseGoal` validates + authorizes
(`canCloseGoal`, `sender.kind === 'bridge'`) → `close-goal.js#closeGoal` checks the live-goal
roster (`liveGoals`, `goals.csv`), refuses if already `finished` (nothing to close), no-ops
idempotently if already `closed`, else `store.writeGoalWord({stored:'closed', who_stamped:'owner',
evidence_pointer: 'owner close reply · disposition ask <id>'})`. `reconcile.js`/`lane-watch.js`
gained a THIRD skip check (after `paused`, before the `finishEvent` skip in lane-watch's ordering;
after `finished` in reconcile's), `laneIsClosed(goalFolder, heartStore)`, returning
`{skipped:'closed', goal}` — a closed goal is never rebuilt and no chair launches for it again.

## Consequences
**The SQLite CHECK-widening trap, hit and fixed.** `state-store/tables.sql` runs as `CREATE TABLE
IF NOT EXISTS` (`open.js`), so widening `goal_states`'s CHECK in source changes NOTHING on this
vault's own LIVE `heart.db` — measured directly: `SELECT sql FROM sqlite_master WHERE
name='goal_states'` on `/home/henri/ht-wkdir/second-brain/.rbtv/runtime/ignite/heart.db` showed the
original three-word CHECK, and an `INSERT ... stored='closed'` against it raised
`SQLITE_CONSTRAINT: CHECK constraint failed: stored IN ('running','paused','finished')` (RED,
reproduced on a scratch copy, never the live file). SQLite cannot `ALTER` a CHECK, so
`open.js#migrateGoalStatesClosed` performs the standard non-destructive rebuild (rename old table
out of the way, create the new shape fresh — byte-identical to `tables.sql`'s own block — copy
every row, drop the renamed-out original), run inside its own transaction, idempotent via
detecting the widened CHECK clause itself (never a bare `'closed'` substring — the table's own new
comment quotes the word too, `MIGRATION_ENQUEUE_LOG_BRAKED`'s own trap). Proven GREEN on a scratch
copy of the live db: 13 rows preserved, CHECK widened, idempotent re-run, `who_stamped` pairing
constraint enforced (a `stored='closed', who_stamped='system'` insert correctly still fails).

`disposition-thread.js`'s header comment (stale the moment this landed — it said "GOAL_WORDS is a
closed three-word enum") was rewritten in the same change; leaving it would have misled the next
reader into believing `close` was still unwired.

`probe-disposition-post.js`'s STAGE B `close` checks (C1-C5) flipped from asserting an honest
`ok:false`/"no closeGoal port is wired" refusal to asserting `ok:true`/`action:close` — that stage
runs against a GENERIC fake forwarder ack, so it proves the DISPATCH plumbing (the right intent,
the right payload, the right posted text), not the real store write. A new STAGE C was added for
that: the real `closeGoal()` executor against a real ending store, plus a real `reconcileGoal()`
skip proof (with a running/owed CONTROL fixture, same shape `finish-gate.selftest.js` proves the
`finished` skip with), plus `isGoalFinished`/`isGoalPaused`/`isGoalRunning` all proven `false` for a
closed goal (with a genuinely-`finished` control row proving the predicate itself discriminates).

No pre-existing code was deleted or replaced. `owed.js`/`owed-from-endings.js` were deliberately
NOT touched — their `finishEvent` gate exists because the STORED `finished` word is unreliable in
production, a problem `closed` does not share (see Design); adding a redundant `closed` check there
would duplicate the goal-level skip lane-watch/reconcile already perform before either module's
owed computation is ever reached for a closed goal.

## Verification
Red-first: unmigrated live-db schema copy rejects `stored='closed'` with `SQLITE_CONSTRAINT`
(quoted above). `node ignite/chat/probes/probe-disposition-post.js` → 34/34 PASS, exit=0 (STAGE A
posting unchanged, STAGE B dispatch-plumbing checks updated, new STAGE C: real executor + real
reconcile skip + control + isGoalFinished-never-true proof). `node ignite/deploy/probe-suite.js
--only <name>` GREEN for: `probe-disposition-post`, `probe-reconcile` (carries
`finish-gate.selftest.js`, proving the pre-existing `paused`/`finished` skips are unbroken),
`probe-drop-lane`, `probe-chat-pause-resume`, `probe-console-resume-rearm`, `probe-pause-resume`,
`probe-engine-ending-store`, `probe-frozen-driver`, `probe-goal-paused-gate`,
`probe-intent-drift` (the closed-set drift guard — proves `parse.js`/`dispatch.js`'s two `INTENTS`
copies stayed in sync for the new `close-goal` name), `probe-authz-seat`, `probe-gateway-boundary`,
`probe-cli-authfail`, `probe-chat-boundary` (still red ONLY at the pre-existing `bus-answer.js`
`execFile` hit; the new/changed chat files show zero forbidden-capability hits). Plain `node`:
`ignite/state-store/ending-store.selftest.js` ALL PASS, `ignite/supervisor/lane-skip.selftest.js`
7/7 PASS (including its own `laneIsPaused` arm, proving the new `laneIsClosed` sibling did not
disturb it). Committed on `ignite/core-daemon`, NOT deployed — `ignite/chat/`, `ignite/runtime/`,
`ignite/state-store/` and `ignite/supervisor/` are pinned to the deploy worktree.

## ATTENTION
1. **The live-db migration lives in `state-store/open.js#migrateGoalStatesClosed`, NOT in
   `heart/migrations.js`.** Two independent openers touch the SAME physical file in different
   contexts: `bindEnding`'s primary branch (used by every daemon-path caller with a real
   `.rbtv/goals/<goal>` folder — reconcile, lane-watch, the new `close-goal` executor) resolves via
   `openEndingStoreFor` → `open.js`, which has NO `heart/migrations.js` involvement at all; only a
   caller with NO goal folder falls through to `heartStore.db`. `pause-resume.js`'s own "THE ENDING
   HOME" note is the full evidence trail for why the workspace-scoped file, not the daemon's
   private one, is what actually matters. A future schema change to `goal_states` must land its
   migration in `open.js`, not assume `heart/migrations.js`'s `MIGRATION_ENDING_STORE` (a
   `CREATE TABLE IF NOT EXISTS` no-op) covers it.
2. **`laneIsClosed`/`laneIsPaused` resolve the goal NAME from the fixture folder's basename**
   (`ending-reads.js#goalNameOf`, no override argument) — a test fixture must be named EXACTLY the
   goal it represents (`path.join(tmpRoot, GOAL)`, not an `mkdtempSync` random sibling), or the
   goal-state row and the read never line up. `finishEvent`-based tests (e.g.
   `finish-gate.selftest.js`) do not have this trap because `finishEvent` reads `messages.md`
   straight off the folder, never through `goalNameOf`.
3. **`owed.js`/`owed-from-endings.js` are deliberately NOT gated on `closed`** — only
   `reconcile.js`/`lane-watch.js` are. This mirrors `paused`'s own existing shape (also ungated
   there) and is correct because both watchers `continue`/return before either module's owed
   computation is ever reached for a skipped goal. Do not add a redundant `closed` check inside
   `owed.js`/`owed-from-endings.js` on the assumption it is missing — it would be dead code, never
   reached for a goal already skipped one layer up.
4. **`approvalPorts.closeGoal` (`chat-bridge.js` line ~205, `approval-thread.js`) is a DIFFERENT,
   still-unwired port** — a planning-goal "reject-and-close" outcome, unrelated to `GOAL_WORDS` or
   this ruling. Do not conflate the two `closeGoal` names; this change touches ONLY
   `disposition-thread.js`'s.
- The live-db migration lives in open.js#migrateGoalStatesClosed, NOT heart/migrations.js — bindEnding's primary daemon-path branch never touches the migrations framework
- laneIsClosed/laneIsPaused resolve the goal name from the fixture folder's basename (goalNameOf, no override arg) — name test folders exactly the goal
- owed.js/owed-from-endings.js are deliberately NOT gated on closed, mirroring paused's own shape — do not add a redundant, unreachable check there
- approvalPorts.closeGoal (approval-thread.js) is a DIFFERENT, still-unwired port — do not conflate with disposition-thread.js's closeGoal
