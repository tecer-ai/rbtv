# 20260828-i-pause-wrote-a-store-the-lane-g — pause wrote a store the lane gate never reads

kind: issue
component: state-store
date: 2026-08-28
commit: 919be192
deployed: no
pin: ignite/runtime/internal-api/probes/probe-pause-resume.js
components: runtime,supervisor,gateway

## Observed
The owner's Slack `pause {goal}` was INERT and `resume {goal}` lied. Measured 2026-08-28
03:37-03:39Z by the acceptance wave's re-run of tests 8/9/10 on the fixture goal
`channel-master-diag-test` (a half-born daemon-lane goal with NO `taskforce.csv`), against a
daemon booted from deployed HEAD 509358e9. After `pause channel-master-diag-test` the daemon's
private store `/home/henri/.local/state/rbtv-ignite/heart.db` held
`{"stored":"paused","who_stamped":"owner","stamped_at":"2026-08-28T03:37:02.781Z"}` while the
workspace ending store `<ws>/.rbtv/runtime/ignite/heart.db` answered `null` to `getGoalState`
before AND after, and five daemon lane cadences journaled zero paused-skips: the lane pass kept
running the goal. Then `resume` faulted — journal 03:39:07Z `"internal API fault",
"intent":"pause-resume"`, `ReferenceError: Cannot access 'seat' before initialization` — and the
owner was told `resume … was NOT applied — INTERNAL: server-core fault` while the store had
already been flipped to `running` (that row, stamped 03:39:07.885Z, is still in the private store
today). Third, a `pause-resume` refused for an unknown slug left NO line in the daemon journal at
all; only the bridge journaled it, which reads on inspection as "the verb never reached the
daemon". Deployed HEAD and repo HEAD were the same commit for all three.

## Mechanism
Two of the three are one line each in `ignite/state-store/heart/pause-resume.js`, minted five
hours earlier by 4a032354.

The store split: `pauseResume` did `const store = bind(heartStore.db)` — it bound whichever store
the CALLER already held. Under the daemon that is `{data_root}/heart.db`, i.e.
`~/.local/state/rbtv-ignite/heart.db` from the unit's `StateDirectory=rbtv-ignite`. The reader the
pause exists for resolves a different file: `supervisor/lane-watch.js#laneIsPaused` binds through
`supervisor/ending-reads.js#bindEnding`, which is `bind(openEndingStoreFor(root))` — spec-state-store
§1.1's ONE ending store at `<workspace>/.rbtv/runtime/ignite/heart.db`, the same file family 8 of
the envelope (297765d8) binds rw into every caged seat. Writer and reader therefore disagreed on
the FILE, and the wrong value was born at the writer. `20260828-c-laneispaused-two-pause-writers`
made `laneIsPaused` an OR over the goal row and the `execution-lane` marker on the same day; that
guard was correct and never fired, because the row it reads was being written elsewhere.

The half-applied resume: the seat loop head was
`for (const seat of seatsOf(goalDir, (level, message, fields) => log(level, message, { seat, ...fields })))`.
The logger closure captures the loop variable `seat` declared in the same head. `seatsOf` calls
that logger from its own `catch`, and `supervisor/seeding.js#readTaskforce:525-530` THROWS when
`taskforce.csv` is absent — so on any goal without a readable taskforce the closure ran in the
temporal dead zone of `seat` and threw a `ReferenceError` out of a function whose entire contract
is that a missing taskforce is reported, never thrown. It threw AFTER row 4 (the `paused→running`
goal-word write) had already committed, so the answer and the store disagreed by construction.

The silent refusal: `runtime/internal-api/dispatch.js#handlePauseResume` logged only on the applied
path; the `if (!out.found) throw new InternalApiError(NOT_FOUND, …)` branch wrote nothing.

## Attempts
First attempt held — checked: 4a032354 (the intent's own landing, entry
`20260828-c-15th-intent-pause-resume-the-m`, whose "How it works" states `bind(heartStore.db)` as
the ending-store port and is the sentence this fix corrects); 8b44d806 (the bridge half — untouched
here); `20260828-c-laneispaused-two-pause-writers` (the OR gate, same day, unchanged by this fix);
`20260827-i-the-ending-store-was-unwritabl` (297765d8, which made the SAME workspace file writable
from caged seats and is why the daemon and the seats agree on it); a0d7e42c (the earlier
convergence onto the goal row); `20260825-c-the-js-side-of-ignite-goes-com` (the component layout
this file sits in).

## Fix
`pauseResume` now binds `bind(openEndingStoreFor(workspaceRoot))` and takes NO store handle from
its caller at all — the first positional `heartStore` parameter is deleted, and its two callers
(`dispatch.js`, the probe) updated. Removing the parameter is the point: it is the only channel
through which the wrong file could arrive, so the defect cannot be reintroduced by a caller.
`openEndingStoreFor` is the same resolver the reader spends (`state-store/paths.js#endingStorePath`
underneath both), so there is ONE resolution, not a third. `bindEnding` itself was rejected as the
call for two reasons: it lives in `supervisor/`, which this component may not require (supervisor
requires state-store, not the reverse), and it deliberately FALLS THROUGH to the lane store when
the home cannot be opened — the fail-safe direction for a READER ("nothing declared", a seat with
no ending stays launchable) and precisely the wrong file for a WRITER. So an unopenable home now
throws, and it throws BEFORE any write: the caller answers INTERNAL and nothing was applied, which
is honest. Writing somewhere else and reporting success is the one outcome this verb may not
produce. Verified first that the daemon PROCESS can write the file: `systemctl --user show
rbtv-ignite` reports `ProtectHome=no ProtectSystem=no ReadWritePaths=` (empty) and
`/proc/316681/root -> /`, and the live daemon already holds fds 26/27/28 as `lrwx` on
`<ws>/.rbtv/runtime/ignite/heart.db` plus its `-wal`/`-shm` — it opens the home read-write on every
lane pass through `bindEnding`.

The lane roster is enumerated ONCE, `const seats = seatsOf(goalDir, log)`, at the TOP of
`applyResume` — above row 1 (the counter half) and above row 4 (the goal word), not merely above
the loop. That ordering is the fix, not tidying: it removes the closure capture AND puts the only
failure the roster can produce ahead of every write, so an unreadable taskforce can no longer
half-apply the verb. `log` is passed plainly, because an enumeration that failed has no seat to
name — which is exactly what the closure was pretending otherwise. Honest bound: this does not make
`applyResume` atomic and no claim is made that it is. A store fault inside `writeGoalWord`, or a
`require` fault in `laneFileParks`, can still throw after the counter half has run; there is no
transaction spanning a sqlite store, a JSON counter ledger and a lane file, and inventing a
compensating rollback across three surfaces (each of which can itself fail) was rejected for the
same reason it was rejected in 297765d8. What is fixed is the failure that actually fires, on every
resume of every taskforce-less goal.

The refusal now journals: one `info` line naming verb, goal and the executor's refusal reason,
immediately before the `NOT_FOUND` throw.

## Consequences
`pauseResume`'s signature changed from `(heartStore, opts)` to `(opts)`; both call sites moved in
the same commit and there are no others (`grep -rn pauseResume ignite/`). The bridge half 8b44d806
is untouched — it is a sender and reads only `actions`/`refusals`, which are unchanged, so the
owner's rendered line is byte-identical for every case that already worked.

A LOOSE END this fix does not clear, deliberately: the stray `running` row for
`channel-master-diag-test` written by test 9 at 03:39:07.885Z still sits in the daemon's PRIVATE
store. After this fix the only readers of `goal_states` outside the state-store component are
`lane-watch.js#laneIsPaused:137` and `#frozenFactsFor:290`, and BOTH bind through `bindEnding`,
which resolves the workspace home for any real goal folder — so the private row is unread. It can
be reached only by `bindEnding`'s own fall-through (`ending-reads.js:42-49`, taken when
`openEndingStoreFor` throws), and its value is `running`, which is the non-blocking direction in
both readers: it can cause a pause to be missed, never a goal to be frozen. Clearing it is an
operator act on a live store and is not this seat's to make.

A SIBLING of the same cause, surfaced not fixed (out of this change's walls):
`state-store/heart/start-execution.js:100` does `bind(heartStore.db).getAsk(String(thread))` — the
fourteenth intent reads `open_asks` out of the caller's lane store by the same pattern. Whether
that is wrong depends on which store the approval ask was posted to; it was not measured here.

## Verification
`node ignite/runtime/internal-api/probes/probe-pause-resume.js` → `RESULT: PASS — 53/53 checks`,
`EXIT 0` (38/38 before). The 15 new checks are a section (h) that finally makes the split
MEASURABLE: sections (a)-(g) hand the dispatcher `heartStore: { db }` where `db` IS the workspace
store, so they could not tell the two bindings apart — which is exactly how the probe read 38/38
green while production was split. (h) runs a SECOND scratch workspace in which the ending home is a
pre-existing file (a donor store, WAL-checkpointed and byte-copied to `endingStorePath()`, so the
arms measure a writer opening a store that was already there) and the daemon's `heartStore` is a
DIFFERENT file under `lane-state/`. h1 proves the two files are apart; h2/h3 that pause writes the
home and NOT the lane store; h4 that `laneIsPaused` — the reader itself, holding the lane store —
answers true; h5/h6/h7 that resume on a goal with no `taskforce.csv` is `applied:true` with a warn
naming the goal and the store reading `running`, no throw; h8 that a seated goal still gets its
table (`disarmed→armed`) out of the home; h9 that a `no-such-goal` refusal is `NOT_FOUND` AND
leaves the journal line. Four new red mutations on discarded copies beside the source: R4/R4b
restore `bind(heartStore.db)` and its parameter — pause reports applied, the home never changes,
the lane store takes the write and `laneIsPaused` answers FALSE, the live defect reproduced; R5/R5b
restore the loop-head closure — resume on the taskforce-less goal throws
`Cannot access 'seat' before initialization` with the goal row ALREADY flipped, the half-application
reproduced.

Unchanged before and after: `probe-chat-pause-resume` 23/23 EXIT 0, `probe-intent-drift` PASS (all
three copies of the closed intent set at 15), `supervisor/lane-skip.selftest.js` 6/6,
`probe-start-execution` 20/20, `probe-daemon-code-fingerprint` 29/30 (the same pre-existing red).
`node --check` on all three edited JS files. tmux session list byte-identical before and after
(16 sessions, diff empty). NOT DEPLOYED at filing (commit 919be192 on `ignite/core-daemon`); the
DAEMON is the unit that must restart, because the executor and the dispatcher both boot from
`/home/henri/.local/state/rbtv-deploy`.

## ATTENTION
1. THE EXECUTOR TAKES NO STORE HANDLE, AND THAT ABSENCE IS THE FIX. Re-adding a `heartStore`
   parameter "for symmetry with its siblings" re-opens the exact defect: a caller's lane store is
   not the ending home, and a pause written there is invisible to `laneIsPaused` while still
   reporting `applied: true` to the owner. The home is derived from `workspaceRoot` only.
2. DO NOT REACH FOR `bindEnding` HERE. It is the READER's resolver and it falls through to the lane
   store when the home cannot be opened — correct for a reader answering "nothing declared", fatal
   for a writer, which would then silently write the wrong file again. A writer must throw instead;
   `openEndingStoreFor` is the shared half both sides resolve through.
3. THE LANE ENUMERATION MUST STAY ABOVE EVERY WRITE. It is not stylistic hoisting: `readTaskforce`
   throws on a missing `taskforce.csv`, and any enumeration failure placed after row 1 or row 4
   leaves the store changed and the owner told it was not — the exact 03:39:07Z fault. A future edit
   that moves the goal-word write above `const seats = …` restores it.
4. SECTION (h) OF THE PROBE IS THE ONLY ARM THAT CAN SEE A STORE SPLIT. Every other section passes
   the workspace store in as `heartStore`, so a writer bound to the caller's handle looks identical
   to one bound to the home. Collapsing (h) back into the shared fixture "to remove duplication"
   deletes the measurement and returns the probe to reporting 38/38 on a broken verb.
5. A STRAY `goal_states` ROW FOR `channel-master-diag-test` STILL SITS IN THE DAEMON'S PRIVATE
   `~/.local/state/rbtv-ignite/heart.db` READING `running`. Nothing reads it after this fix except
   `bindEnding`'s unopenable-home fall-through, where `running` is the non-blocking answer — but
   anyone diagnosing that goal from the private store will read a pause history that never applied.
- the executor takes NO store handle: the home comes from workspaceRoot only, and bindEnding's lane-store fall-through must never be reused by a writer
