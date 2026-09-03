# 20260901-i-reconcile-selftest-l907-stale — reconcile.selftest L907 stale unpause fixture (store-truth)

kind: issue
component: supervisor
date: 2026-09-01
commit: 513d7d39,dabdeb68
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
UPDATE 2026-09-01 (commit `dabdeb68`, same day): a resume on this exact task found the L907 fix
alone was not sufficient — the suite still died further down, and the leader-abandonment arms
(`dl-reconcile-honour`) had NOT actually executed in the run this entry originally claimed they
had (unverified inference, corrected by a judge re-run). Three MORE stale mutation anchors, all the
same shape as L907 (a refactor moved or reshaped the code an anchor targeted; the anchor kept
matching syntactically-but-wrongly, or stopped matching, so the arm ran a no-op mutation or aborted
its own guard), were found and fixed in the same follow-up commit:

- **L1030, "mutation of the disarm brake":** `counters.peekCounter(` appears TWICE in `reconcile.js`
  (`announceDisarm` at :543, inert for this arm; the real brake `counterDisarmed` at :671). The old
  anchor was a bare non-unique substring; a non-global `.replace()` silently mutated the wrong
  (first) occurrence, so the "mutant" kept braking and the arm's own "proves nothing" guard fired.
  Fixed by anchoring on `counterDisarmed`'s own unique `if (!config) return false;` guard line.
- **"D24: an unreadable coord degrades to the OLD behaviour":** mutated `reconcile.js`'s OWN
  `COORD_PY` constant, but `summonedSeats` (and the `COORD_PY` it actually reads) lives in
  `seeding.js` — `reconcile.js` only re-exports the import and carries an unrelated same-named
  constant of its own (a `--coord` subprocess arg, used only at reconcile.js:323). The mutation was
  completely inert: the real function kept reading the live `coord.py` and returned a non-empty set.
  Fixed by mutating `seeding.js` directly and calling ITS `summonedSeats`; `owedFromLedgers` never
  touches `COORD_PY` so the already-imported real one is reused unmutated.
- **Two RED arms ("stop honouring the hold", class A and class B):** both anchors paired the
  `holdMap.has(...)` exclusion with the line immediately following it. `dl-reconcile-honour`
  (2026-08-31, commit `4196440e`) inserted an `abandonedMap.has(...)` check BETWEEN the hold check
  and that line in BOTH the class-A and class-B loops of `owed-from-endings.js`, so neither anchor
  matched and neither arm ran. The class-B case is the IDENTICAL drift `probe-suite-green` already
  fixed once in `supervisor/probes/probe-hold-classb.js` on 2026-09-01 (commit `4d4aae4d`) — this
  selftest's own copy of the same anchor was missed by that fix. Both re-anchored on the
  abandonedMap-sandwiched text, mutating out only the `holdMap` line.

Each fixed anchor also gained a `src.split(ANCHOR).length - 1 === 1` uniqueness assertion so a
future refactor that makes an anchor ambiguous again fails loudly instead of silently mutating the
wrong spot. `reconcile.js` and `owed-from-endings.js` PRODUCT code are unchanged throughout — every
fix across both commits is confined to the selftest's own mutation anchors.

## Verification
`node ignite/supervisor/reconcile.selftest.js` → **exit 0, 53 `ok` checks, `reconcile.selftest OK`**
— confirmed on TWO consecutive runs (determinism check). Includes explicit `ok` lines for the
leader-abandonment arms: `dl-reconcile-honour: a dropped leader chair is never woken, never
rebuilt-under, in ONE pass` (both the control pass and the forced second pass) and its RED arm
(`without the abandonment check, the dropped leader chair IS resurrected`).
`node ignite/deploy/probe-suite.js --only probe-reconcile` → `PASS exit=0`,
`SUITE-COMPLETE verdict=GREEN exit=0`. NOT DEPLOYED at filing (commits `513d7d39`, `dabdeb68`).

## ATTENTION
1. `reconcile.selftest.js` NOW RUNS CLEAN END-TO-END (exit 0) — the "still does not run clean"
   warning this entry originally carried is RESOLVED as of `dabdeb68`. Do not re-open on stale
   information; re-run before assuming otherwise.
2. FOUR STALE MUTATION ANCHORS IN ONE FILE, ALL FROM THE SAME REFACTOR WINDOW. Any selftest or
   probe anchor written against `owed-from-endings.js` or `reconcile.js` predating
   `dl-reconcile-honour` (4196440e, 2026-08-31) or the counter/coord refactors is suspect — grep for
   OTHER copies of `holdMap.has(...)`-adjacent or `counters.peekCounter(`-adjacent anchors across
   `supervisor/probes/` and `supervisor/*.selftest.js` before assuming this sweep was exhaustive.
3. A LEGACY `paused ` FILE-PREFIX MIGRATION IS ONE-WAY AND PERMANENT. Any fixture (or production
   caller) that still writes `execution-lane`'s legacy prefix to simulate pause must resume through
   the store (`writeGoalWord`/`applyResume`), never by editing the file back — the file write is
   inert once a store row exists.
4. DO NOT TRUST "runs past line N" AS PROOF A LATER ARM EXECUTED without quoting that arm's OWN
   `ok` line. This entry originally claimed the leader-abandonment arms ran based on line-number
   proximity alone; they had not (a judge re-run caught it) — the suite was dying at L1030 BEFORE
   reaching them, in the same run that produced the (correct, but incomplete) L907 fix.
- reconcile.selftest.js now runs clean end-to-end (exit 0, 53 ok) as of dabdeb68 — the file's other stale mutation anchors (disarm brake, D24 coord, class-A/B hold) are fixed too.
- a legacy execution-lane paused-prefix migration into the store row is one-way; a fixture/caller must resume via writeGoalWord, never by editing the file back.
