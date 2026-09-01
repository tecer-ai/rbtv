# 20260901-i-reconcile-selftest-l907-stale — reconcile.selftest L907 stale unpause fixture (store-truth)

kind: issue
component: supervisor
date: 2026-09-01
commit: 513d7d39
deployed: no
pin: ignite/supervisor/reconcile.selftest.js
components: state-store

## Observed
`ignite/supervisor/reconcile.selftest.js` aborted at `assert.ok(enq)` (L907) in the "paused goal
is not reconciled" arm's "control: same folder unpaused enqueued" step — measured on
`ignite/core-daemon` HEAD `b20016c0` (before this fix), 2026-09-01. Confirmed pre-existing: already
named in `20260831-c-reconcile-lane-watch-honour-a`'s ATTENTION-2 as one of two broken RED arms
blocking the whole file ("a paused/unpaused assertion around line 906"), and unaffected by two
intervening fixes (`reconcile-needle` 069f6803 fixed a different D33(a) needle; `probe-suite-green`
fixed a different stale D35 `tsAfter` anchor) — those two moved the abort DOWN from higher up in
the file to this arm but never touched it.

## Mechanism
The arm's control step wrote `'daemon\n'` to the goal's `execution-lane` file, expecting that to
unpause `fx-pause`, then asserted `reconcileGoal` returned an `enqueue` action. It never did.
Pause truth migrated off `execution-lane` onto the ending-store's `goal_states` row when
`state-store/heart/pause-resume.js` landed ("ONE PAUSE RECORD... The `execution-lane` file is the
lane word (daemon/console) and is not a pause surface", pause-resume.js:73-77). The arm's own
FIRST step (writing `'paused console\n'` and calling `reconcileGoal`) already drove
`lane-watch.js#laneIsPaused` through its legacy-migration branch (no `row.stored` yet + a legacy
file prefix present → writes `stored:'paused'` into the store AND strips the prefix from the
file), which durably parks the store's row at `paused`. From then on `laneIsPaused` hits its FIRST
branch (`row && row.stored === 'paused'` → true, lane-watch.js:124) regardless of the file's
contents, so clearing the file to `'daemon\n'` was a no-op and every subsequent
`reconcileGoal` call kept returning `skipped:'paused'` — `unpaused.actions` was `undefined`,
`.find(...)` threw nothing but returned `undefined`, and `assert.ok(enq)` threw.

## Attempts
First attempt held on this exact arm — checked: `20260831-c-reconcile-lane-watch-honour-a` (named
the break, did not fix it — out of that seat's walls); `20260828-c-laneispaused-two-pause-writers`
(the OR-gate design this arm's era assumed — since superseded by the store-first branch read here);
`20260828-i-pause-wrote-a-store-the-lane-g` (the store-split fix for the PRODUCTION writer —
confirmed the product side is correct; this was a fixture-only defect).

## Fix
Updated the fixture: after clearing `execution-lane`, the arm now calls the real resume mechanism
directly — `bindEnding(store, goalFolder).writeGoalWord({goal, stored:'running', ...})` — mirroring
`applyResume`'s ROW 4 in `pause-resume.js` and the identical pattern this same selftest file's own
later "ONE PAUSE RECORD" arm already uses (`bindEnding(...).writeGoalWord(...)`). Rejected: touching
`lane-watch.js`/`pause-resume.js` — the product's contract is correct and already documented
verbatim in `pause-resume.js`; bending the assertion to accept `skipped:'paused'` would have hidden
a real fixture bug behind a weakened check, which the mission explicitly ruled out.

## Consequences
The suite now runs past L907, through the leader-abandonment arms (~1382), and further — it
aborts later, at L1030, on a SEPARATE pre-existing bug: `reconcile.js` has two
`counters.peekCounter(` call sites (`announceDisarm` at :543 and the real brake `counterDisarmed`
at :671); the "red arm: mutation of the disarm brake" selftest anchor does a plain (non-global)
`String.replace(ANCHOR, ...)`, which only ever touches the FIRST textual occurrence — landing the
mutation inside `announceDisarm` (inert for this arm's purpose) while the real brake
(`counterDisarmed`) stays unmutated and keeps braking correctly, so the arm's own "the mutant
proves nothing" check fires. Confirmed pre-existing and untouched by this fix (`git diff` on
`reconcile.js` is empty). NOT fixed here — different cause, out of this seat's scope; surfaced for
a follow-up seat.

## Verification
`node ignite/supervisor/reconcile.selftest.js` — runs past L907 (both the control-unpause arm and
the "one pause record" arm now `ok`), through leader-abandonment (~1382), aborting at L1030 on the
unrelated pre-existing bug above (exit 1, was ALSO exit 1 before this fix but at L907 instead).
`node ignite/deploy/probe-suite.js --only probe-reconcile` → `PASS exit=0`,
`SUITE-COMPLETE verdict=GREEN exit=0` (probe-reconcile gates only on `finish-gate.selftest.js`'s
exit status per `20260831-c-reconcile-lane-watch-honour-a` ATTENTION-3, unaffected either way).
NOT DEPLOYED at filing (commit 513d7d39).

## ATTENTION
1. `reconcile.selftest.js` STILL DOES NOT RUN CLEAN END-TO-END. A future seat fixing the L1030
   disarm-brake mutation-anchor collision should expect the file to run further still and may
   surface a THIRD unrelated break — check with a fresh run, don't assume L1030 is the last one.
2. THE L1030 BUG IS A DUPLICATE-ANCHOR COLLISION, NOT A LOGIC BUG. `counterDisarmed` (the real
   brake) is correct and unmutated; the fix belongs in the SELFTEST's anchor-selection (disambiguate
   the two `counters.peekCounter(` sites, e.g. anchor on the enclosing function name or use the
   `if (!config) return false;` guard already unique to `counterDisarmed`), not in `reconcile.js`.
3. A LEGACY `paused ` FILE-PREFIX MIGRATION IS ONE-WAY AND PERMANENT. Any fixture (or production
   caller) that still writes `execution-lane`'s legacy prefix to simulate pause must resume through
   the store (`writeGoalWord`/`applyResume`), never by editing the file back — the file write is
   inert once a store row exists.
- reconcile.selftest.js still aborts later at L1030 on an UNRELATED pre-existing bug (duplicate peekCounter anchor) — not fixed here.
- a legacy execution-lane paused-prefix migration into the store row is one-way; a fixture/caller must resume via writeGoalWord, never by editing the file back.
