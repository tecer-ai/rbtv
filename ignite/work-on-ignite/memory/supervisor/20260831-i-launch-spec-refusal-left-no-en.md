# 20260831-i-launch-spec-refusal-left-no-en — Launch-spec refusal left no ending in the goal's store

kind: issue
component: supervisor
date: 2026-08-31
commit: 0d7c8df3
deployed: no
pin: ignite/envelope/envelope-launch.selftest.js
components: envelope

## Observed
`goal-memory-management`, 2026-08-23: a spawn refused at launch-spec resolution (a seat's `model:`
did not match the launch-specs table) got NO ending stamped into the goal's own ending store —
`reconcile.js`'s leader-ruled class-A recovery path had nothing to read for that seat, confirmed by
`refusal-ending-stamp`'s own red-first fixture (`/var/tmp/refusal-stamp-fixture.js`, run against a
worktree pinned to HEAD before this fix): `spawnSeat()` refused `E_UNMAPPED_BINDING` on a
short-alias `model:` and `owedFromLedgers(...).classA` returned `[]` for that seat even though its
`sessions.csv` carried a prior, finished sitting. The `model:` short-alias case became common after
`859b8428` made `cast seat`/`specForSeatCast` refuse a non-verbatim model pin; two seats in the
`redesign-continue-1` run (`coord-mail-route`, `done-gate-grammar`) hit exactly this refusal within
minutes of each other. `20260831-i-spawn-refused-row-parked-seedi.md`'s ATTENTION §3 already named
this gap while fixing a sibling problem (the FAST seeding path's permanent-`live` park) and
deliberately left it open as out of that seat's assigned files.

## Mechanism
`ignite/envelope/stamp.js#stampLaunchRefused` is the ONE function that stamps a `failed` ending with
`reason_class` into the goal's ending store on a launch refusal. Both spawn doors
(`spawn()`/`spawnSeat()` in `ignite/supervisor/spawn/spawn.js`) wire it ONLY into the `stamp`
callback passed to `composeCageFor` — the cage/grant-composition refusal family. Neither door wired
it into the `catch` block around `launchSpecForSeat(...)` (the seat's declared `harness:`/`model:`
resolving against the launch-specs table via `specForSeatCast` in
`ignite/supervisor/launch-profiles/catalog.js`), which throws `E_UNCAST_SEAT` (no cast declared) or
`E_UNMAPPED_BINDING` (a cast the table doesn't carry — the short-alias shape) well before
`composeCageFor` is ever reached. So that whole refusal family — launch-spec resolution — reached no
stamping seam at all: a second stamping site (the cage callback) existed, but the sibling family
that fails one step earlier in the SAME function had none.

## Attempts
First attempt held — checked: `20260831-i-spawn-refused-row-parked-seedi.md`'s own "Attempts"
section, which considered stamping a goal-side ending for every spawn-time refusal and REJECTED it
as broader than that seat's assigned files (it fixed the fast seeding-graph park via `jobs_log.pid`
instead, untouched here). No other prior attempt at this specific gap found via
`grep -rn 'stampLaunchRefused\|launch-spec' ignite/work-on-ignite/memory/*/_issues.md`.

## Fix
Both `launchSpecForSeat` catch blocks (the headless `spawn()` door and the paned `spawnSeat()` door)
now call `stampLaunchRefused` before re-throwing, guarded on the refusal being a REAL seat (a
`parseSeatPath`/`parseServiceSeatPath` match) — a seatless-dispatch or not-a-seat-folder refusal
still gets no ending, correctly, since there is no (goal, seat) to stamp one against. The stamp uses
the SAME function every cage refusal already uses (`stampLaunchRefused`) rather than a new stamping
site, with one addition: `stampLaunchRefused` now accepts an optional `reasonClass` (default
`'launch-refused'`, unchanged for every existing caller) so this new call site can pass
`'configuration-error'` — a value the CLOSED `REASON_CLASSES` vocabulary
(`ignite/state-store/vocabulary.js`) already carries — distinguishing a spec-resolution refusal from
a cage refusal in the same store without widening that vocabulary. Rejected: inventing a new
`reason_class` string (would have thrown `E_BAD_ENDING` — the vocabulary is a closed list validated
at write time, discovered the hard way when the first attempt used a non-member string and the
fixture's ending-store row came back `null`).

## Consequences
No change to the refusal DECISIONS themselves (an uncast/unmapped seat still refuses exactly as
before, same error codes and messages) — only an ending now lands in the store first. No change to
`reconcile.js`'s recovery logic: it already treats any `failed` ending as a `nonterm` class-A row
via `classifyEnding` (`owed-from-endings.js`), regardless of `reason_class`, so the leader-ruled wake
now fires for this seat exactly as it already does for a cage-refused one. Does NOT touch the
sibling fast-seeding-park fix (`isRefusedBeforeSpawn`/`jobs_item.pid`, `b10155e1`) — that path still
resolves independently via `jobs_log.pid`, unaffected.

## Verification
Red-first fixture (`/var/tmp/refusal-stamp-fixture.js`, scratch-only): a seat with a `sessions.csv`
history and a short-alias `model:` refused at `spawnSeat(..., dryRun:true)`. Against a `git worktree`
pinned to HEAD (pre-fix): `code=E_UNMAPPED_BINDING`, `classA rows = []`, `ending store row = null`.
Against the fixed tree: SAME refusal code, `classA rows = [{"seat":"s1","ending":"failed",...,
"reason":"nonterm"}]`, ending store row carries `"reason_class":"configuration-error"`. Regression:
`node ignite/envelope/envelope-launch.selftest.js` ALL PASS (cage-refusal fixture unaffected, still
stamps `reason_class: launch-refused`). `node ignite/supervisor/owed-from-endings.selftest.js` ALL
PASS. `node ignite/supervisor/reconcile.selftest.js` reaches the SAME pre-existing abort point at
line 841 (`reconcile.selftest.js:841` greps a source string `fa89fa75` deleted, per loose-ends.md —
unrelated to this change; every arm before it passes). Spawn probes
`probe-workdir-gate.js`/`probe-dispatch-door.js`/`probe-seat-launch-gate.js`/
`probe-profile-halves-refusal.js` ALL PASS unchanged (none of their refused legs are a real,
materialized seat hitting `E_UNCAST_SEAT`/`E_UNMAPPED_BINDING`, so none exercise the new stamp call,
and none assert on ending-store side effects). Commit: see this filing's `--commit`. NOT DEPLOYED.

## ATTENTION
1. `reason_class` is validated against a CLOSED vocabulary (`state-store/vocabulary.js#REASON_CLASSES`)
   at write time — `stampLaunchRefused` throws `E_BAD_ENDING` on any value not already a member. Pick
   an existing member (`configuration-error` fits "seat declares a cast the table won't run"); do not
   invent a new string without also widening the vocabulary deliberately.
2. Class-A visibility ALSO requires a `sessions.csv` row for the seat (`owed-from-endings.js`'s `last`
   map is built solely from that file) — a seat's FIRST-EVER launch attempt, refused before any
   session id exists, still will not appear in `classA` no matter how the ending store is stamped.
   This fix only restores visibility for a seat that already has session history (the common
   incident shape: a seat that ran before and is now being RE-launched with a bad cast) — a
   never-launched seat refused at spec resolution is a residual this entry does NOT close.
3. Neither spawn door writes a `sessions.csv` row before `launchSpecForSeat` resolves (that write
   happens much later, after cage composition succeeds) — so this refusal family, like the cage
   refusal family before it, never gets a `sessions.csv` row of its own. Do not assume stamping the
   ending store is sufficient in general; it is sufficient only combined with point 2's pre-existing
   session history.
- reason_class is a closed vocabulary — E_BAD_ENDING on any non-member string
