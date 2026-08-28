# 20260828-c-supervise-hold-a-leader-hold-t — supervise hold — a leader HOLD the reconcile pass honours

kind: creation
component: supervisor
date: 2026-08-28
commit: c29b2f43
deployed: no
pin: ignite/coord/probes/probe-leader-hold.py
components: state-store,coord,meta-leader

## Motivation
`owed-from-endings.js:12` classes any `failed` ending as `nonterm` and `reconcile.js:937,953-969`
answers a `nonterm` owed row by launching the LEADER — every ~5-min pass, for as long as the row
stays `failed`. The leader had exactly two acts that stop that (`supervise accept`, `supervise
instruct`), and both work by ENDING the row. Its third legitimate verdict — "I have read this and
it cannot be ruled until a named change happens" — existed only as a message, and the pass reads
rows and never mail. So a HOLD sitting was indistinguishable from a sitting that did nothing: the
pass counted it as a burned recovery attempt (`reconcile.js:1165-1178` → `attempt-counters.js
countAttempt`), N=3 disarmed the lane and opened grouped ask `recovery-e0db9b5e7fd9`, and the next
code-deploy re-arm wiped the counter and bought three more. On 2026-08-28 that produced nine
identical HOLD verdicts (messages #26–#34) on `goal-memory-management`'s leader across the 03:20Z /
03:55Z / 06:27Z deploys — nine paid opus-5 sittings, none of them honoured by anything.

## Design
A HOLD is now a ROW in the ONE workspace ending store, and the pass's owed computer reads it.

`seat_holds` (`state-store/tables.sql`) keys on (goal, seat) and carries `until`, `ask_id`,
`anchor`, `held_by`, `held_at` and an `ending_stamped_at` witness. A SIBLING TABLE and not a column
on `seat_endings`, for three reasons each fatal alone: a `failed` row's CHECK clauses pin it to
`who_stamped='system'` + a reason class from the closed seven + `armed IS NULL`, so a leader's
ruling fits no slot; every re-stamp archives the current ending into `seat_endings_log`, so a hold
carried there would be superseded away by the very re-stamp it waits for; and a hold's lifetime is
its own — it must survive a code-deploy re-arm, because a hold is a ruling and a re-arm clears
counters. It is in that FILE — `<workspace>/.rbtv/runtime/ignite/heart.db`, reached by
`openEndingStoreFor` and never `bind(heartStore.db)` — because the reader that must honour it is
the reconcile pass's ending read, and a second store is the defect `ending-reads.js`'s own header
exists to end.

`until` is a closed three-word vocabulary (`vocabulary.js#HOLD_UNTIL`) and each word is answered
from a row the store already keeps: `new-ending` (the ending's `stamped_at` still matches the
witness), `ask-answered:<ask-id>` (that `open_asks` row is still `open` — §2.1's own mechanism, so
an owner answer arriving through `reapAndRelaunch` releases the hold with NO second watcher), and
`release` (only `supervise release` deletes it). A message-number form was considered for the live
case (escalation #18 is a `messages.md` row, not an ask) and rejected: it would be a second watcher
over a different surface inside a store predicate that holds no goal folder. That case uses
`--until release`.

Rejected: reusing `seatWaitingOnOwner`. It answers a DIFFERENT question (is this seat blocked on an
open owner ask) and cannot express "the leader ruled this row unrulable until the seat is
re-stamped". It IS reused, as the `ask-answered` release condition.

## How it works
`supervise hold <seat> --until <change> --anchor "<evidence>" --go` and `supervise release <seat>
--go` (`coord/ruling.py#cmd_hold` / `#cmd_release`, parser in `coord/cli_main.py`, both added to
`SUPERVISION_COMMANDS` so `coordinate hold` is refused by name at the parser). The Python side
spells no SQL: it goes through `coord/ending_store.py` → `state-store/cli.js` ops `holdSeat` /
`releaseSeat` / `getSeatHold` / `seatHeld` / `listSeatHolds`. The release vocabulary is READ OFF
`state-store/vocabulary.js#HOLD_UNTIL` with a `node -e`, exactly as `instruction_kinds()` reads the
instruction list off `relaunch-budget.js` — a word this door accepted and the store refuses is a
ruling the leader believes it recorded and did not. Fail-closed: an unreadable list refuses.

`state-store/predicates.js#seatHeld` is the ONE liveness predicate and returns the hold row or
null. `supervisor/owed-from-endings.js#classifyOwed` calls it per seat and SKIPS a held seat in the
class-A loop — the same shape `dead` and `summoned` already have — so there is no launch target,
and therefore no leader launch AND no attempt counted, from one exclusion rather than two agreeing
rules. It also skips class E (a held row is not an unexplained frozen frontier). Class B is
untouched: mail to a chair is not the held row. `reconcile.js`'s `pass` journal line gained
`heldExcluded`, naming each held seat with its release condition; `nontermPayload` names the third
act, and so does `meta/leader/prompts/leader.md` §"Never relabel an unfinished row".

Liveness is re-evaluated on every pass, so a hold clears ITSELF the moment the named change is
observed — no sweep, no writer, no state machine — and the released row is worth exactly ONE leader
sitting, not a fresh N. Every unknown (an ask id that names no row, a word this build does not
know, a vanished ending) answers NOT HELD: a broken hold can only let the daemon do what it did
before holds existed, where the opposite default is a lane stopped forever by a typo.

## Consequences
Nothing was deleted and no existing behaviour changed for an unheld seat. `classifyOwed`'s return
gained `heldSeats` (and `owed.js`'s `EMPTY_LEDGER` the matching empty list). `holdSeat` is
idempotent on identical terms — the same hold twice returns the first row with `held_at` unmoved,
so two sittings reading the same mail do not restart the clock — and REPLACES on different terms,
because one hold per (goal, seat) is the primary key. `seat_holds` arrives on the live store with
no migration step: `tables.sql` is `CREATE TABLE IF NOT EXISTS` throughout and `open.js` runs it on
every open. Filed together with the `code-deploy` cause filter (commit a7603764), which is the
other half of the same owner ruling.

## Verification
`supervisor/reconcile.selftest.js` 41 ok, was 37 — four new arms and their red: a `failed` row
under a live hold yields no leader launch and no counter advance across two passes while the pass
NAMES the hold; `rearm(CODE_DEPLOY)` leaves the hold standing; `supervise release` returns the row
to class A for exactly one launch; and `--until new-ending` releases on the re-stamp for exactly
one launch. The RED injects a copy of `owed-from-endings.js` with the exclusion line deleted into
`require.cache` and drives the real `reconcileGoal` through it — the held row wakes the leader
again, so the arms discriminate. Measured on a scratch copy with the four documented pre-existing
red assertions neutralized identically in the HEAD and working trees (`:392`'s stale
`No runtime ruling instrument exists` needle, the brake mutant, the D24 mutant pair), because they
abort the file before any new arm can run.
`coord/probes/probe-leader-hold.py`, new, 14/14 EXIT=0: the dry run records no hold; a `--until`
word outside the list is refused WITH the list; `ask-answered` without an id, an id naming no open
ask, a missing `--anchor` and an unstaffed seat are each refused and leave nothing behind; `--go`
writes one live row; the same hold again is idempotent with `held_at` unmoved; different terms
replace; `release` reports then removes and is a no-op on an unheld seat; `coordinate hold` is
refused by name at the parser.
`state-store/ending-store.selftest.js` ALL PASS. `probe-inspect-asks` 28/28.
`probe-leader-wake-counter` 26/26. `probe-daemon-lane-watch` 1 failing check (L9 M9, documented
pre-existing). No nested `.rbtv/` created; tmux session list byte-identical.
NOT DEPLOYED at filing — the daemon restart is batched with the A-1 fix.

## ATTENTION
1. A HOLD SUPPRESSES THE WHOLE SEAT'S CLASS A, not just its `nonterm` row. That is deliberate — "the leader ruled this row is not to be re-driven" is as true of an `armed incomplete` relaunch of the seat itself — but it means holding a seat also stops its own recovery relaunch. Class B (mail to a chair) is NOT suppressed, so a held chair stays reachable.
2. `seatHeld` FAILS OPEN on every unknown, and the direction is load-bearing. A typo'd ask id, a word a future build removes, a vanished ending row: each reads NOT HELD and the daemon does what it did before holds existed. Inverting this to "hold on doubt" is how a lane stops forever with nobody able to say why.
3. THE `new-ending` WITNESS IS A `stamped_at` STRING CAPTURED AT WRITE TIME. If a future writer ever re-stamps an ending with an unchanged `stamped_at`, that hold never releases. The store's `nowIso()` makes that unreachable today; a caller passing an explicit `stamped_at` equal to the old one would reach it.
4. THIS IS NOT `hold-anchor` COMING BACK, and reading it as one will get it reverted. `hold-anchor` was a thirteenth column on `sessions.csv` under the grant-store authority model deleted whole [T2-R12, T1-R9]; `HELD` and `hold-anchor` are still refused words at the ending store's door and neither is written here. What was killed was a SECOND work-state writer beside the ending store. This is a row IN it, and it changes no ending.
5. A HOLD DOES NOT RE-ARM ANYTHING. Releasing one gives the leader ONE sitting on the counter it already had, not a fresh N — so a lane already at N stays disarmed through a hold and its release, and only a named re-arm event (`resume {goal}`, an owner/leader act) clears it. Do not read a release as an un-disarm.
- a hold suppresses the whole seat's class A and never re-arms a counter; releasing one buys ONE sitting on the count it already had
