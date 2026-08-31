# 20260831-c-reconcile-lane-watch-honour-a — reconcile+lane-watch honour a dropped lane's abandonment

kind: change
component: supervisor
date: 2026-08-31
commit: 4196440e
deployed: no
pin: ignite/supervisor/reconcile.selftest.js,ignite/supervisor/lane-skip.selftest.js

## Motivation
`d-recovery-abandoned-is-an-ending` (owner ruling, 2026-08-31) made `abandoned` a lane's second
terminal outcome and taught the owed-counter computers (`owed.js`, `owed-from-endings.js`) to
exclude it (`dl-abandoned-outcome`, commit f1b7a292). That landing explicitly did NOT wire the
reconcile pass or lane-watch — a lane can be resurrected by a pass that never asks the counters
the same question, which is a separate property from "is this lane owed".

## Design
Re-verified all four sites the ruling named against the current tree (post-refactor, `engine/` →
`supervisor/`) rather than trusting the cited lines. Two were already correct by inheritance: the
`laneIsPaused`/`finishEvent` whole-pass gates and the `taskforce.csv`-exists gate are goal-scoped
by design and must stay so (abandonment is lane-scoped; collapsing a whole goal over one dropped
lane strands every working sibling). The two room-resurrection branches (`reconcile.js`, gated on
`derived.owed`) already inherit the exclusion because `derived.owed` is computed via
`classifyOwed`, which `dl-abandoned-outcome` already fixed.

One genuine gap remained, ROOT-CAUSED to a single function: `leaderSeat()` resolved the `leader`
chair off taskforce-row presence alone, never checking whether that SPECIFIC lane had been
dropped. Since `leader` is a literal, fixed chair name (not a seat picked per-pass), dropping it
via `drop-lane` is a real scenario, and every downstream consumer of `leader` (the nonterm-judgment
wake, and the room-rebuild's `recoverRoom({seat: leader})`) would still treat it as staffed —
resurrecting exactly the lane the owner said was gone forever, with no undo. Fixed AT THE SOURCE
(`leaderSeat`), reusing 100% of the existing `seat: null` fail-closed handling every consumer
already has for "no leader row" — not taught twice at each call site.

Second gap: `lane-watch.js`'s existing per-lane skip map (`laneSkips`, C-9 — already excludes
unbuilt/uncast seats before `seedGoal`/`launchOwed` enqueues) had no abandoned-seat exclusion. The
seeding graph half (`launchOwed`'s classR, via `recordView`) never populates `view.abandoned`
(a pre-existing gap in `recordView`/`ending-reads.js`, OUTSIDE this component's row — surfaced,
not fixed), so a seat coord still marks READY (stale) could reach `classR` on that path alone.
Added abandoned seats to `laneSkips`, mirroring the unbuilt-seat/uncast-seat precedent exactly —
an independent backstop regardless of which owed-half let the seat through.

## How it works
`ignite/supervisor/reconcile.js#leaderSeat(goalFolder, {heartStore, goal})`: after confirming the
`leader` row exists, calls `bindEnding(heartStore, goalFolder).getSeatAbandonment({goal, seat:
'leader'})`; a row present returns `{seat: null, why: 'leader-abandoned', detail}`, same shape as
`no-leader-row`. `reconcileGoal` passes `{heartStore, goal}` at the one call site.

`ignite/supervisor/lane-watch.js#runLaneWatch`: right after the existing `uncastOnly` block fills
`laneSkips`, computes `abandonedSeats(bindEnding(engine.heartStore, goalFolder), goalNameOf(...),
<taskforce seats>)` (reusing `owed-from-endings.js#abandonedSeats`, the same function
`classifyOwed` already calls) and adds each to `laneSkips` with reason `'abandoned'`. This backstop
also makes `openGoalRoom`'s first-room seat picker skip a dropped lane, for free (it already
filters on `laneSkips`).

## Consequences
No deletions and nothing pre-existing was replaced — both changes are pure additions on top of
`dl-abandoned-outcome`'s landed storage. Nothing DUPLICATE: reused `bindEnding`, `goalNameOf`,
`abandonedSeats`, `getSeatAbandonment` verbatim rather than re-deriving the abandonment lookup a
second time in either file. `leaderSeat()`'s call signature grew an options object
(`{heartStore, goal}`); its one production call site was updated in the same change, and the one
existing selftest anchored on its old single-line body was updated (B16 red arm) rather than left
to silently stop discriminating.

## Verification
`ignite/supervisor/reconcile.selftest.js` — new arms (fixtureLeaderAbandoned): a real
`reconcileGoal` pass over a fixture with `leader` abandoned and two live siblings (a direct
`incomplete` relaunch and a `nonterm` judgment row) proves: `leader===null`,
`why:'leader-abandoned'`, the dropped chair is never enqueued nor `recoverFn`'d, the room is
reopened room-only (task 166's own fallback) not rebuilt-under-it, AND the CONTROL sibling
(`worker-incomplete`) is still enqueued in the SAME pass. A second, forced pass (not
`skipped:'cadence'`) proves no later-pass resurrection either. A mutation red arm (disables the
`if (abandonment)` branch only) reproduces the historic resurrection: `leader==='leader'`,
enqueued, `recoverFn` called with `seat:'leader'`, `room-rebuilt`.

`ignite/supervisor/lane-skip.selftest.js` — new arm drives `launchOwed` with a `laneSkips` entry
computed the same way `runLaneWatch` now computes it (`abandonedSeats` off a real `abandonSeat`
row), proving the sibling launches while the dropped lane does not; extended the existing
source-shape RED arm to assert the new `for (const seat of abandonedOnly) laneSkips.set(...)` line
survives in `lane-watch.js`.

Full reconcile.selftest.js could not be run end-to-end (two PRE-EXISTING, unrelated broken RED
arms earlier in that 1879-line file — stale mutation anchors in `owed-from-endings.js`/elsewhere,
confirmed present on baseline via git stash, not touched by this change) — new arms verified via
an isolated script requiring the real `reconcile.js` directly (exit 0, RED+GREEN+CONTROL+re-arm
all confirmed) since the shared file could not reach them in one run.
`finish-gate.selftest.js` green (exit 0). `probe-daemon-lane-watch.js` and (via `probe-reconcile.js`)
`reconcile.selftest.js`'s pre-existing failures are IDENTICAL with and without this change
(confirmed via git stash on both files) — not introduced or worsened here. Not yet deployed.

## ATTENTION
1. `recordView` (`ending-reads.js`) never populates `view.abandoned` for `launchOwed`'s classR —
   `seatState`'s own abandoned check can never fire on that path. Independently covered by the
   `laneSkips` backstop here, but the gap itself is unfixed and belongs to `ending-reads.js`/
   `seeding.js`, outside this row.
2. `reconcile.selftest.js` has at least two unrelated, pre-existing broken RED arms (a stale
   `owed-from-endings.js` mutation anchor around line 846, and a `paused`/`unpaused` assertion
   around line 906) that stop the WHOLE file at the first `assert` throw — every arm after them,
   including the new ones this entry adds, cannot run via a plain `node reconcile.selftest.js`
   invocation until those are fixed.
3. `probe-reconcile.js` only gates its own exit code on `finish-gate.selftest.js`'s exit status —
   `reconcile.selftest.js`'s exit code is captured and printed but never fails the probe. The probe
   reads GREEN today even though `reconcile.selftest.js` itself exits 1.
- recordView never sets view.abandoned for launchOwed's classR — the graph-half exclusion is dark, independently covered by laneSkips
- reconcile.selftest.js has pre-existing unrelated broken RED arms (~line 846, ~906) that stop the file before reaching these new arms
- probe-reconcile.js's own exit code ignores reconcile.selftest.js's exit status entirely
