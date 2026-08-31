# 20260831-c-seat-abandonments-a-lane-s-sec — seat_abandonments: a lane's second terminal outcome

kind: creation
component: supervisor
date: 2026-08-31
commit: f1b7a2928cf904bebe351a7a7970cad7cb70f23a
deployed: no
pin: ignite/supervisor/owed-from-endings.selftest.js
components: state-store

## Motivation
`d-recovery-abandoned-is-an-ending` (owner ruling, 2026-08-31, decisions.md "the two dead recovery
replies get seated"): the owner's `drop-lane` recovery reply retires ONE lane — the `(goal, seat)`
pair — forever, with no undo. The ruling put the RECORD of that "where a lane's normal completion
is already recorded, as a second terminal outcome beside `done`". Two alternatives were rejected in
the same session: a per-lane event line in the goal log, and a column on `taskforce.csv`. Before
this change, nothing under `supervisor/`, `runtime/`, or `state-store/` read the word `abandoned`
at all (`GOAL_STATUSES` in `goal_cli.py` carries it, but that field is goal-scoped frontmatter,
never read by the daemon, and this outcome is lane-scoped).

## Design
`state-store/tables.sql` gets `seat_abandonments`, a SIBLING TABLE beside `seat_endings` — not a
widened `seat_endings.ending`. Two reasons, the first decisive and MEASURED against the live store,
not assumed: (1) `seat_endings.ending`'s CHECK is `IN ('done','incomplete','failed')`, `open.js`
runs `tables.sql` as `CREATE TABLE IF NOT EXISTS` (a no-op on a table that exists), and the LIVE
`heart.db` at this workspace was queried directly (`node:sqlite`, `.schema seat_endings`) and
confirmed to still carry exactly that three-word CHECK — widening the CHECK in this file would
change nothing on that database, and stamping `ending='abandoned'` against it raises
`SQLITE_CONSTRAINT`. (2) every re-stamp of `seat_endings` archives the current row into
`seat_endings_log`, so a value living there could be superseded away by a LATER stamp — and
"abandoned forever" cannot live somewhere a later write erases it. `seat_holds` (filed 2026-08-28,
`c29b2f43`) is the exact precedent: its own header in `tables.sql` gives the same two reasons for
being a sibling table. `seat_abandonments` differs from `seat_holds` in one respect: it carries NO
release vocabulary at all (`seat_holds.until` has three words; abandonment has none), because there
is nothing to release — the ruling's whole point is no undo. The writer never deletes or replaces a
row; a second `abandonSeat` call on an already-abandoned lane returns the FIRST row unchanged
(`idempotent: true`), even with a different `anchor` — never a second ruling.

## How it works
`writers.js#abandonSeat(db, {goal, seat, anchor, abandoned_by, abandoned_at, ask_id})` and
`#getSeatAbandonment(db, {goal, seat})`, bound onto the store API in `state-store/index.js#bind`
and exposed on the `ending-cli` door (`state-store/cli.js` `OPS`) alongside `holdSeat`/`getSeatHold`.
No separate predicate module (unlike `seatHeld`): there is no release condition to evaluate against
other rows, so the raw row's presence IS the answer.

`supervisor/owed-from-endings.js` gains `abandonedSeats(api, goal, seats)` (the same shape as the
existing `heldSeats`) and calls it once per `classifyOwed` pass, then excludes on it in all three
places the ruling named: the `pending` loop (feeds `classE`'s frontier report), the `classA` loop,
and the `classB` loop — the same three sites `dead`/`summoned`/`held` already gate. The return
object gained `abandonedSeats` (mirroring `heldSeats`/`deadSeats`), so a caller can NAME what was
excluded and why, same as a hold.

`supervisor/owed.js` gains the graph half: `seatState` takes an `abandoned` Set option and checks
it FIRST, before every other branch (including `done`) — returning the literal string `'abandoned'`,
never `'done'`. This is what stops a seat coord still marks READY (stale, because coord does not
know about the drop) from falling through to the `ready` return at the bottom and entering `classR`.
`deriveLaunchable` threads `view.abandoned` into `seatState`'s options exactly as it already threads
`view.done`/`view.foreign`/`view.notFinished`.

## Consequences
Nothing was deleted and no existing behaviour changed for a non-abandoned seat — `abandoned` is an
additive, backward-compatible option everywhere it was added (absent → `undefined.has` never called,
guarded by `abandoned &&`). Two things this change deliberately did NOT do, both stated to the
orchestrator as requirements for the seats that depend on this one: (1) `ending-reads.js#recordView`
(the function that builds `view` for `reconcile.js`/`seeding.js`) was NOT touched — it does not yet
populate `view.abandoned`, so class R's exclusion is a proven CAPABILITY (unit-tested directly) but
not yet live in the graph cadence; wiring `recordView` and passing the set through `reconcile.js`/
`lane-watch.js` is out of this seat's custody wall (`dl-reconcile-honour`). (2) The `dropLane` port
itself (`ignite/chat/recovery-thread.js`'s "did not run" message) was not touched — `abandonSeat` is
the primitive that door will call (`dl-teardown-wire`).

## Verification
`ignite/state-store/ending-store.selftest.js` ALL PASS (14 cases, +1 new: `abandonSeat` write/
read-back/idempotent-on-retry/never-overwrites). `ignite/supervisor/owed-from-endings.selftest.js`
ALL PASS (13 cases, +3 new): an abandoned lane excluded from `classA`+`classB` in one DB-backed
fixture with a non-abandoned CONTROL lane in the same pass still owed in both classes; an abandoned
lane excluded from the `pending` frontier (`classE`) with a control lane still pending; and a pure
unit test proving `seatState`/`deriveLaunchable` (class R) return the distinct `'abandoned'` state
and never enter `classR`, with a control seat still launchable. RED-first: all three new arms were
run BEFORE the production fix and failed exactly as expected (abandoned lane still counted). Live
storage decision verified against the running `heart.db` at this workspace's
`.rbtv/runtime/ignite/heart.db` (`.schema seat_endings`, confirmed the three-word CHECK, no
migration framework). `probe-reconcile.js` (`finish-gate.selftest.js` + `reconcile.selftest.js`) was
run and carries ONE pre-existing failure (`reconcile.selftest.js:846`, "class (b) unread anchor
missing") that reproduces byte-identically on the parent commit in a scratch `git worktree` before
this change — a stale mutation anchor (`&& (!since || tsAfter(m.ts, since)));`) that no longer
exists in `owed-from-endings.js` since an earlier cursor-based refactor (`fa89fa75`), unrelated to
this change. Committed but NOT deployed: `f1b7a2928cf904bebe351a7a7970cad7cb70f23a`.

## ATTENTION
1. THE LIVE `seat_endings.ending` CHECK CANNOT BE WIDENED BY EDITING `tables.sql` ALONE. `open.js` runs `CREATE TABLE IF NOT EXISTS` — a no-op against an existing table. Any future temptation to add `abandoned` as a fourth `ending` value must first prove the live store's CHECK actually changed (query `.schema seat_endings`), or it will pass on a fresh fixture and throw `SQLITE_CONSTRAINT` on every running workspace.
2. `abandonedSeats`/`heldSeats` in `owed-from-endings.js` are BOTH scoped by `seats` (`[...last.keys()]`, session-derived via `lastBySeat`). A chair (STAFF_CHAIRS) with NO session row yet is invisible to both exclusions even though the classB loop iterates `STAFF_CHAIRS` directly — a pre-existing characteristic of `held`, inherited rather than introduced here, and unlikely to matter in practice (a lane must have run at least once to be droppable) but worth knowing before debugging a "why didn't the exclusion fire" report.
3. `deriveLaunchable`'s `abandoned` option is WIRED BUT NOT FED IN PRODUCTION YET. `ending-reads.js#recordView` does not populate `view.abandoned`, so class R (the ~10s graph cadence via `seeding.js`) will not actually exclude an abandoned seat until that wiring lands — proven only by direct unit test here. Do not read the passing selftest as proof the daemon's fast cadence already honours drops.
4. `seat_abandonments` HAS NO RELEASE VOCABULARY, UNLIKE `seat_holds`. Do not add one without a new owner ruling — `d-recovery-drop-is-one-lane-permanent` is explicit that there is no undo, from Slack or a terminal, and an undo path is named as the most likely place "the dropped lane came back" would reappear.
- the live seat_endings.ending CHECK cannot be widened by editing tables.sql alone — CREATE TABLE IF NOT EXISTS is a no-op on an existing table
- class R (deriveLaunchable/seatState) accepts an abandoned set but ending-reads.js#recordView does not populate view.abandoned yet — the fast graph cadence does not honour drops until dl-reconcile-honour wires it
