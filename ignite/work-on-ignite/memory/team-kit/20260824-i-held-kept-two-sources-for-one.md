# 20260824-i-held-kept-two-sources-for-one — HELD kept two sources for one owner-ask

kind: issue
component: team-kit
date: 2026-08-24
commit: cda50e86,3613cfca,4138b934
deployed: no
pin: ignite/engine/probes/probe-owner-ask-hold.js
components: engine,state-store,envelope

## Observed
On branch `ignite/core-redesign` in the redesign worktree, five engine probes were red —
`probe-owner-ask-hold`, `probe-cross-lane-resume`, `probe-daemon-lane-watch`, `probe-engine-library`,
`probe-foreground-carrier` — measured 2026-08-24 by the seat that closed the state-store periphery.
`probe-owner-ask-hold` printed the divergence in one line: `verdicts {"alpha":"HELD"} · blockedOnOwner []`.
Coord held a seat the engine thought was free. Nothing is deployed; the daemon runs the live tree,
so every reading here is the worktree's.

## Mechanism
Two independent causes, both left by an unfinished migration.

The first is the one the defect names. `team-kit/ready.py`'s `HELD` verdict derived from the BUS —
`coord.open_asks(messages.md, sender=<seat>, to=owner)` — while `engine/ending-reads.js#recordView`
derived the SAME fact from the `open_asks` table (`spec-state-store` §2.1). One fact, two sources,
which is the shape this redesign exists to end: a posted ask with no row in that room's `messages.md`
held the engine and not coord, and a bus ask nobody posted held coord and not the engine. The same
grep found the sibling row — `checkout.py`'s `fallback: block-and-queue` gate, which refused a `done`
check-out off the same bus predicate and re-derived the ferry's delivery ladder through
`ask_parked_at_gate` to decide whether the ask had been delivered at all.

The second was invisible until the first was fixed. `engine/ending-reads.js#bindEnding` bound
`heartStore.db` — whichever store the LANE held open, `<goal>/heart.db` under `rbtv run` and
`{data_root}/heart.db` under the daemon. §1.1 puts the ONE ending store at
`<workspace>/.rbtv/runtime/ignite/heart.db` and says in as many words that it is not per-goal and not
`{state_root}` after cutover. So a seat the attached lane finished read UNFINISHED to the daemon —
the exact cross-lane resume `probe-cross-lane-resume` is built to guarantee — and coord, whose own
door (`ending_store.py`) walks up for `.rbtv` and lands on the home, was already reading a third file
from the one either lane wrote.

Underneath both sat Row D's leftovers. `closeExecutionLocked` and `publishToRecord` keyed
"already closed" on the `outcome` column that Row D had emptied, so a blank cell read as "still open"
and every terminal row of every goal was re-closed and re-reported as non-clean on every tick,
forever; `nonClean` pushed CLEAN closes as non-clean because the word it tested no longer existed;
`ranSeats` answered "no lane ever ran any seat" for every goal in the build.

## Attempts
First attempt held — checked: the four state-store family entries (`server/20260824-c-ending-store-stamp-api`,
`engine/20260824-c-engine-reads-ending-store`, `team-kit/20260824-c-kit-endings-via-store-client`,
`bridges/20260824-i-open-asks-has-no-boundary-lega`), `spec-state-store` §1.1/§2.1/§5/§7, and the two
commits that left the seam (`795459fa`, `23d95ec3`). The bridges entry is what made the diagnosis
cheap and nearly made it wrong: it recorded `open_asks` as written by NOBODY, and concluded the
divergence "closes when the ask record does". That was true when written and false by the time this
sitting ran — the owner ruled option (a) the same day and `server/heart/ask-record.js` landed the
daemon-side writer, so the migration was legal after all. A memory entry states what was true at its
commit; the tree is what says whether it still is.

## Fix
`HELD` derives from the ending store. The new read is `listOpenAsks` — `seatWaitingOnOwner`'s WHERE
clause returned as rows rather than a boolean, so the row's `held-asks` and its `waiting_on_owner`
cannot disagree about one seat, which is the property the old shape lacked. It is hoisted ONCE per
goal beside every other hoist in that function, and it REPLACED a per-seat `node` subprocess:
`waiting_on_owner` was spending one process per seat on `seatWaitingOnOwner` while the hold read a
different surface entirely. The check-out gate moves the same way, and its parked-ask branch stops
re-deriving the ferry's ladder: §3's `posted` flag IS "the owner was told", so an unposted ask
notes-and-releases and a posted one refuses. That door refuses on a store error rather than
degrading — the opposite of `ready-seats`, whose broad `except` protects a fail-closed-per-goal
seeding pass that must never lose its other verdicts to one bad read.

`bindEnding` now derives the store from the goal folder's workspace root and opens it through a new
`state-store/open.js`. It could not be a second `HeartStore`: that class holds a process-wide writer
slot (`E_SECOND_WRITER`), so a lane already holding its own store could never open the home through
it. The handle is `node:sqlite` with heart-store's own pragma order and `tables.sql`, which is
`CREATE TABLE IF NOT EXISTS` throughout. The lane store survives as the fallback for a caller with no
goal folder, and that fallback is why `envelope/stamp.js` had to move too: every production caller
passes both a lane handle and a `workspaceRoot`, and preferring the handle wrote launch-refusals into
a file no reader consults.

Rejected: pointing the probes' kit at the engine's db with `ENDING_STORE_DB` (green fixtures over a
divergence still shipping), and copying endings into both stores (the dual write §7 forbids).

## Consequences
`ready.py` costs one `node` call per goal instead of one per seat for the wait predicate — but
`is_launchable` still shells out PER SEAT for a pure function with no db access, measured at ~80ms a
seat (1.03s for a three-seat `ready-seats` against 0.74s for one). On the daemon's seeding pass that
is paid per goal per cadence. It is left standing: collapsing it means either a second implementation
of §2.6 in Python or a new batch op, and neither is this sitting's row.

Seven probe fixtures were retargeted with the readers (`3613cfca`). Two of their arms had been
passing while measuring NOTHING — mutants built on `record.CLEAN`/`record.CRASHED`, constants Row D
deleted, so the regexes matched no byte and each mutant was identical to its control. Four fixtures
also lacked `<workspace>/.rbtv/mirror`, which `envelope/compiler.js` resolves into every launch plan;
without it every detached launch landed `failed` with no carrier and no session id, which reads like
a broken engine and is a missing directory.

Two probes went red on this change and were fixed with it: `probe-attached-status` and
`probe-frozen-frontier` stamped `heartStore.db`. `probe-cross-lane-resume`'s D3 arm then went red on
a NEIGHBOUR's ruling mid-sitting (`a94d6f61`, the ferry park deleted) and was retargeted in
`4138b934`.

## Verification
The five named probes run foreground against the worktree: `probe-owner-ask-hold` 23/23,
`probe-cross-lane-resume` 37/37, `probe-daemon-lane-watch` PASS, `probe-engine-library` 60/60,
`probe-foreground-carrier` green but for `B1j`'s wall-clock bar (3.1s against a 2000ms bound; three
`coord.py` invocations at 0.74s of interpreter startup each put that bar out of reach on this box,
before any store call — environment, not migration). The rest of `engine/probes/` is green in two
chunks, `state-store/ending-store.selftest.js` prints ALL PASS, `engine/reconcile.selftest.js` and
the three envelope selftests pass, `probe-checkout-disposition` is 11/11. The kit selftest still
aborts after 389 checks on `NameError: awaiting_path` — proven pre-existing by running
`probe-lifecycle-idents` against HEAD's three kit files (41/42, same failing arm), and `awaiting_path`
is referenced at `checkout.py:336` and defined nowhere at HEAD. `py_compile` on all three `.py`,
`node --check` on all 17 `.js`. Not deployed.

## ATTENTION
- The ending store is reached from the GOAL FOLDER's workspace, never from the store handle a lane happens to hold: `<workspace>/.rbtv/runtime/ignite/heart.db`. A writer that takes the caller's `heartStore` shortcut writes a file no reader consults, and the failure is silent — an ending nobody can see reads as a seat that never ended.
- It cannot be opened with `openHeartStore`. That class claims a process-wide writer slot, so a caller already holding a lane store gets `E_SECOND_WRITER`; use `state-store/open.js`.
- `held-asks` now carries `open_asks.ask_id` (a Slack thread id), NOT a bus message number, and the hold lifts on the REAP (§2.8) — not on a `send --type answer --re <n>`. A fixture that writes only `messages.md` will see an empty blocked set.
- A probe fixture's check-out is TWO acts since §4.1: the `sessions.csv` row AND the `seat_endings` stamp. The stamp is keyed by GOAL NAME, so `cpSync`-ing a goal folder to a new name carries the CSV and silently leaves the ending behind.
- `<workspace>/.rbtv/mirror` must exist in any fixture that launches a seat detached, or `composeCageFor` refuses the bind source and every launch lands `failed` with no carrier — which looks like a broken engine and is a missing directory.
- the ending store is keyed to the goal's WORKSPACE home, never the lane store a caller holds — a shortcut write is invisible to every reader
- held-asks are ask_ids and the hold lifts on the reap, not on a bus `--re`
- a fixture check-out is two acts (sessions.csv + seat_endings), and the stamp is keyed by goal NAME
