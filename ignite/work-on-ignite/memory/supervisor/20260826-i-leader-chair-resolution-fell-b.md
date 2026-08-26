# 20260826-i-leader-chair-resolution-fell-b — Leader chair resolution fell back to seats[0]

kind: issue
component: supervisor
date: 2026-08-26
commit: 4ed8acc8
deployed: no
pin: ignite/supervisor/reconcile.selftest.js

## Observed
On every reconcile pass over `goal-memory-management`, the daemon printed `"leader":"distill-ignite-memory"` — the goal's single WORKER, named as its leader. That goal's `taskforce.csv` carries exactly one row, the worker; there is no `leader` row. The consequence was measured on both sides at once: the worker was woken for class-A `nonterm` rows (endings only a leader may close) and named as the seat the tmux room is rebuilt under, while 979 journal lines carried `"seat":"leader"` and none of them was a launch for this goal — the real target's seat folder does not exist, so `launchSitting` returned `{ok:false,error:'no-seat-folder'}` (`reconcile.js:339`). `_channel-master/taskforce.csv` is absent entirely (`ls` → No such file or directory, re-checked 2026-08-26). Recorded as role-action-program matrix rows M50/M51, build entry B16.

## Mechanism
`reconcile.js#leaderSeat(goalFolder)` read the taskforce and answered `if (seats.includes('leader')) return 'leader'; return seats[0] || 'leader';`. `taskforce.csv` IS the register of who holds which chair — `seeding.js#readTaskforce` validates it at load, and the staffing pass in `planning/materialize-seats.py` is its only writer of a `leader` row. A goal with no such row therefore has no leader, and the fallback answered a question the register does not hold by promoting whichever row happened to sort first. The `catch` arm was worse in kind: an UNREADABLE taskforce returned the literal string `leader`, i.e. a chair asserted from a file nobody could read. Nothing downstream could tell a real chair from a substitute — `leaderSeat` returns a bare string — so the wrong seat was woken, logged and rebuilt-under with no signal anywhere that a substitution had happened.

## Attempts
First attempt held — checked: `git log --oneline -- ignite/supervisor/reconcile.js`; the grep floor over `memory/*/_issues.md` and `_creations.md` for `reconcile.js|leaderSeat`; `rbtv embed-search` over the memory store for leader-seat resolution. The neighbouring D33(a)/D39/D42 work (`engine/20260820-c-relaunch-instrument-rerun`, `engine/20260820-i-cleared-row-relaunch-is-two-ac`) rewrote what the leader is TOLD when woken and never touched which seat is resolved as the leader. The staffing half was separately examined in the CP-1 panel revision and ruled NOT a build: the backfill already exists and is documented as such at `materialize-seats.py:5070-5073`, with a warning path for every refusal at `:5303-5309`.

## Fix
`leaderSeat` now returns `{seat: 'leader'}` or `{seat: null, why, detail}` — never a substitute — with `why` one of `no-leader-row` (naming the rows that DO exist) or `taskforce-unreadable` (carrying the reader's message). Fail-closed was chosen over any repair-in-place because the repair is a staffing act that belongs to `materialize-seats.py`'s backfill, which already exists; running it against live goals is a CP-2 operational step and was explicitly out of this seat's scope. Returning a shaped answer rather than a bare `null` was chosen so each consumer can name the reason in the journal instead of reporting a generic absence. Every consumer refuses: the pass's `leader` field is `null` and one `warn` fires per pass naming the reason; the class-A `nonterm` wake pushes `{kind:'no-leader-chair'}` and wakes nobody, leaving the rows standing; the room rebuild pushes `{kind:'room-refused', error:'no-leader-chair'}` and does not shell `recover-room.py`; the B11 budget handoff records `budget-exhausted-no-handoff`. The warn fires on EVERY pass deliberately — this is a staffing state only a `materialize` clears, and the alternative it replaces was promoting a worker in silence, so a memo like `lane-watch`'s was rejected here.

## Consequences
A goal with no `leader` row now gets NO room rebuild where it previously got one under the worker's name. That is intended (rebuilding a room under a seat the register never seated is the same substitution) but it is a behaviour change on live goals: `goal-memory-management` will stop having its room rebuilt until its `leader` row is backfilled. Draining that goal's stale mail (matrix M55, formerly build entry B18) still depends on this plus the missing ruling instrument (B9) and is a CP-2 operational check, not a build. Composes with B11 in the same commit: an exhausted relaunch budget on a goal with no chair records the refusal instead of handing the payload nowhere.

## Verification
Commit `4ed8acc8`. `reconcile.selftest.js` gained a fixture reproducing the live shape exactly — one worker row, no leader row, last ending `exited` (kit-written, a class only the leader may close) — and asserts four things: `r.leader === null`, the worker is not in any `enqueue` action, at least one `warn` matching `NO LEADER CHAIR` carrying `why: 'no-leader-row'`, and the actions carry both `why: 'no-leader-row'` and `kind: 'no-leader-chair'`. A RED arm recompiles `reconcile.js` in a fresh `Module` with `if (seats[0]) return { seat: seats[0] };` restored after the real branch and asserts `rr.leader === 'distill-ignite-memory'` — the defect, reproduced on demand. `node reconcile.selftest.js` → `reconcile.selftest OK`, exit 0; all 13 supervisor selftests exit 0; `probes/probe-reconcile.js` exit 0. NOT deployed: `ignite/` JS is inert until `rbtv ignite daemon deploy`, and this seat was walled from restarts.

## ATTENTION
- The room rebuild is now REFUSED on a goal with no `leader` row. That is a live behaviour change, not only a logging one: `recover-room.py` is not shelled at all. Backfill the chair (`rbtv goal materialize <goal>`) before expecting a dead room to come back.
- `leaderSeat` no longer returns a string. Any new caller that treats the return value as a seat name will silently get an object; read `.seat` and handle `null`.
- The `warn` fires on EVERY pass by design (~288/day/goal at the 300 s cadence). It is not a memo bug — quiet here is what let a worker sit in the chair unnoticed. Do not add a `shouldShout`-style memo without replacing the signal with something an operator actually reads.
- `taskforce-unreadable` and `no-leader-row` are DIFFERENT states with the same consequence. Do not collapse them: the first is a file to fix, the second is a chair to staff.
- The staffing backfill is NOT in this component. `planning/materialize-seats.py:5070-5073` mints the missing chairs on the next materialize that touches the goal; adding a second staffing path here would be the two-writers defect this system keeps closing.
- leaderSeat no longer returns a string - read .seat and handle null
