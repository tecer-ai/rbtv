# 20260831-i-crashed-daemon-lane-room-self — Crashed daemon-lane room self-heals with no leader chair

kind: issue
component: supervisor
date: 2026-08-31
commit: b10155e1
deployed: no
pin: ignite/supervisor/reconcile.selftest.js

## Observed
`goal-memory-management`, 2026-08-24 03:18Z: queue 1591's first fire failed
`spawn-failed: … no room of its own exists`, and the daemon's seed pass refused the goal
`E_GOAL_NOT_LIVE` (`coordination/messages.md` #1). A human patched it by hand:
`tmux new-session -d -s goal-memory-management -c <goal folder>`. On the 2026-08-31 tree,
`lane-watch.js#openGoalRoom` (commit 9cdb472e, 2026-08-27) already self-heals the FIRST-EVER room
for a daemon-lane goal, gated on `!loadSessions(goalFolder).length` (guard 4, "NOT A FIRST
SEEDING"). A goal whose seats HAVE run before and whose room later died — the crashed-dead case —
is deliberately left untouched by that opener (its own header: "that room was closed after seats
ran — the owed/rebuild path's subject"). `reconcile.js`'s `derived.owed && !leader` branch is that
subject, and on HEAD it did not rebuild anything: it logged one `warn`
("this goal's room is dead or empty and there is NO LEADER CHAIR to rebuild it under — the room is
NOT rebuilt") and left the room dead until a human staffed `leader` by hand. Reproduced with a
fixture (`fixtureNoLeader`, one worker seat, `exited` ending, no `leader` row): `reconcileGoal`
returned `{ kind: 'room-refused', error: 'no-leader-chair' }` and no tmux command was ever
composed.

## Mechanism
`reconcile.js`'s room block had two branches on `derived.owed`: with a leader chair present it
called `recoverRoom` (`recover-room.py --seat`, open the room AND boot a recovery seat under the
named chair); with none present it did nothing but log, because picking a substitute chair to
relaunch under was the B16 defect this same branch's split already forbids (`leaderSeat()` must
answer `null`, never `seats[0]`). The two questions — "is the room open" and "who gets relaunched
into it" — were conflated into one gate, so answering "nobody" to the second silently answered
"never" to the first too, even though opening an empty room costs nothing and blocks nothing.

## Attempts
First attempt held — checked: `20260827-i-daemon-lane-goal-s-first-room` (9cdb472e, the sibling
first-room opener; its own ATTENTION note explicitly defers the post-first-seeding case to this
file's owed/rebuild path, which is what THIS entry closes); `20260831-i-finished-goals-resurrected-aft`
(34d5b018, confirms `runLaneWatch`/`reconcileGoal` already skip paused and finished goals BEFORE
reaching the room block, so a dead room reaching this branch is never an owner-deliberate close);
`git log -p ignite/supervisor/reconcile.js` around the B16 leader-chair-fails-closed fix (the
`derived.owed && !leader` split itself) — it only ever suppressed the SEAT relaunch, never
re-examined the ROOM.

## Fix
Split "open the room" from "relaunch a seat into it". A new `openRoomOnly({ goal, goalFolder,
runTmux })` (reconcile.js) reuses `spawn/tmux.js#composeDetachedSession` — the SAME primitive
`lane-watch.js#openGoalRoom` uses (ONE opener, not a second copy) — and is called from the
`derived.owed && !leader` branch instead of only logging. It opens the room, spends no relaunch
grant, boots no seat, and lets the ordinary seed pass (`seeding.js`'s D9 gate) dispatch whatever
coord next answers READY. The `derived.owed && leader-present` branch (`recoverRoom`,
open+relaunch under the named chair) is UNCHANGED — relaunching a SPECIFIC seat under an absent
leader chair stays the separate, still-open "let room recovery restart its seat" item (owner
ruling D11), deliberately not touched here. Rejected: reusing `recover-room.py` for the no-leader
case too — it requires `--seat` and boots a recovery harness, which is exactly the D11 territory
this fix stays out of.

## Consequences
`reconcile.js` gained one new action kind, `room-reopened-no-leader`, and one new injectable seam,
`runTmux` (threaded through `reconcileGoal`, `recoverFn`'s own pattern — production passes
nothing, a probe/selftest substitutes a recorder). The B16 selftest (`reconcile.selftest.js`,
"a goal with NO `leader` row gets NO substitute leader") now injects `runTmux` as a recorder — it
previously ran with the REAL executor un-injected, and this fix would otherwise have made that
selftest shell a real `systemd-run … tmux new-session` on every run (a live side effect a selftest
must never carry). Two new selftest blocks were added beside it. `probe-lane-room-open.js`'s arm 6
comment and check label were reworded to state the discrimination this fix implements: that guard
protects against the LANE opener racing this one, not "the owner closed it" — a genuine owner
close is already filtered upstream (paused/finished checks) by the time either opener's guard is
reached.

## Verification
Standalone fixture script (`node /tmp/verify-task166.js`, since `reconcile.selftest.js` aborts
pre-existing at a stale D35 needle before reaching this file's own line — unrelated to this
change, confirmed by running the same suite with this diff stashed): 4/4 checks —
(1) owed + no leader + dead room → `room-reopened-no-leader`, exactly one
`systemd-run … tmux new-session -d -s <goal> -c <goalFolder>` argv (no window name), no seat
launched; (2) RED — reverting the fix hunk in-memory reproduces `room-refused`, zero tmux calls,
matching the pre-fix recurrence; (3) CONTROL — owed + leader PRESENT still takes the unchanged
`recoverRoom` path (`recoverFn` called once, for `leader`; `openRoomOnly` never invoked);
(4) the live-room guard (`!room.exists || room.empty`) is textually unchanged, so a live room is
never re-touched. `reconcile.selftest.js`'s new B16-adjacent blocks pass under the same fixture,
confirmed by running a scratch copy with only the pre-existing stale D35 assertion skipped.
`probe-lane-room-open.js` re-run after the comment edit: same pre-existing FAIL on the
"daemon-lane guard is dropped" mutant arm, confirmed present on HEAD before this change too (git
stash bisection) — unrelated, surfaced as a loose end, not fixed here. Commit `b10155e1` on
`ignite/core-daemon`. NOT DEPLOYED.

## ATTENTION
1. `openRoomOnly` is ROOM-ONLY, on purpose. Do not extend it to also relaunch a seat — that is the
   separate, still-open "let room recovery restart its seat" ruling (D11), and folding the two
   together here would silently pre-empt that decision.
2. The `derived.owed && leader-present` branch (`recoverRoom`) is untouched. Do not merge the two
   branches into one call — a leader chair's relaunch target is a NAMED seat; the no-leader branch
   deliberately boots nobody.
3. `probe-lane-room-open.js`'s "daemon-lane guard is dropped" mutant arm was found FAILING on HEAD
   before this change (confirmed via `git stash`), unrelated to lane-watch.js/reconcile.js — a
   pre-existing defect in the PAUSED-goal control of that mutation arm, not fixed here, surfaced as
   a loose end for whichever seat owns `lane-watch.js`'s paused-goal guard.
- openRoomOnly is room-only; do not fold in seat relaunch (D11 stays separate)
