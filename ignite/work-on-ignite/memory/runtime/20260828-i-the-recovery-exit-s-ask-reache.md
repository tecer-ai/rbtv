# 20260828-i-the-recovery-exit-s-ask-reache — The recovery exit's ask reached no owner surface

kind: issue
component: runtime
date: 2026-08-28
commit: c481e177
deployed: no
pin: ignite/runtime/internal-api/probes/probe-inspect-asks.js
components: supervisor,chat,gateway

## Observed
A lane that reaches the attempt bound opens an ask the owner never sees. Measured 2026-08-28
05:20-06:00Z against deployed HEAD 26f4510e (repo HEAD identical). Two lanes disarmed during the
acceptance wave — `goal-memory-management/leader` at 04:09:00Z and
`scratch-death-recovery-1-exec/leader` at 05:27:16Z — and each wrote its lane into
`<workspace>/.rbtv/runtime/ignite/asks/recovery-e0db9b5e7fd9.json`, the signature-grouped record
opened 2026-08-27T19:33:20Z for the signature `reconcile-respawn:nonterm`. Nothing rendered either
one: the chat bridge's journal carries no digest line for either disarm, and the record has sat
unread on disk for eleven hours. `inspect asks` — the daemon target the bridge's 2-hourly system
digest reads through, and the one `ignite status` surfaces — answered 8 rows at that moment, all
of them thread-recorded owner asks out of `open_asks`, and not the recovery record.

## Mechanism
Two records, one surface, and the surface only knew about one of them.
`supervisor/exhaustion.js#recordGroupedAsk` writes the recovery exit's ask as a FILE
(`writeAskRecord`, `:82-89`, called at `:119`) under `asksDir(workspaceRoot)` =
`<workspace>/.rbtv/runtime/ignite/asks/`, plus — when a store is present — one `open_asks` row.
`runtime/internal-api/dispatch.js:980` answered `inspect asks` with
`listOpenAsks(heartStore)` and nothing else, and that function
(`state-store/heart/ask-record.js:188`) binds `heartStore.db` and reads the `open_asks` TABLE. The
file was never read by anything.

The store row could not close the gap either, for two independent reasons. It was never written at
all until now, because `recordGroupedAsk`'s `store` argument is `engine.endingStore`, which nothing
set (filed as `20260828-i-the-engine-never-held-the-endi`) — the workspace `open_asks` table is
empty today. And once written it lands in the ENDING store while `listOpenAsks` binds the daemon's
PRIVATE lane store, so the two would still not meet.

The contract makes this a defect and not a gap. spec-recovery §5 states the reason the
byte-equality brake was deleted — "it had no owner-visible exit" — and specifies the replacement:
"On N=3: stamp the lane `incomplete:`, `disarmed`, carrying the refusal text; open ONE
signature-grouped ask (one ask per failure signature, never per lane)." spec-owner-io §5 gives that
ask exactly one renderer, the ONE system digest, whose order line begins "(1) open ❓ asks
(`display_suffix`, seat, one-liner, age, link)"; and `dispatch.js:977-979` declares this target IS
"the digest's own port shape (`chat/system-digest.js` § readOpenAsks)". The value the contract
requires is the whole waiting set; the consumer that rejected half of it is `inspect asks`, so the
defect is born at `dispatch.js:980`.

## Attempts
First attempt at THIS problem held — the surface had never been asked to carry the record. Checked
before building: `20260825-c-inspect-asks-the-read-half-of` (537ecb87, the target's own creation,
whose ATTENTION 1 and 3 constrain this change and whose §Design rules that a read-only store query
extends `inspect` rather than minting an intent); `20260827-i-new-staff-mail-counted-as-a-re`
(348ebf7e, which routed the silent disarm onto `recordGroupedAsk` as "the same signature-grouped
ask record plus `open_asks` row the exit at N writes" — it added the WRITE and could not add the
read, whose walls were the counter); `20260826-c-the-retry-budget-handoff-to-th` (4ed8acc8, whose
`escalate` instruction records through the same door); `20260824-i-open-asks-has-no-boundary-lega`
(16fdc15f, why the bridge may not read the store directly and every read must cross the gateway);
and `20260828-i-pause-wrote-a-store-the-lane-g` (919be192), whose closing paragraph named
`start-execution.js:100` as a third site of the same store split.

## Fix
`exhaustion.js` gains `listOpenGroupedAsks(workspaceRoot)`, a READ-ONLY lister beside `asksDir`,
and `dispatch.js:980` merges its rows with `listOpenAsks(heartStore)`, sorted oldest-first.

A DIRECTORY read and not a store read, which is the design decision. The record is the durable
fact — it exists whether or not the pass held a store, it carries the lanes the table row cannot
(one row binds one seat; the record carries all of them), and it is what `evidence_pointer`
already points at. Reading the table instead would have meant reaching the ENDING store's
`open_asks` from the dispatcher, which holds only the lane store, and would have rendered nothing
for every ask written before the store arrived.

The row shape is `listOpenAsks`'s, key for key — `id`, `goal`, `seat`, `label`, `one_liner`,
`opened_at`, `evidence_pointer` — so the digest's renderer, the CLI and `ignite status` read ONE
list and cannot tell which record a row came out of. The one-liner is the FIRST LANE's own
`refusal_text`, first non-empty line, truncated at 120, with `(+N more lanes)` appended when the
ask carries more: the text is the producer's, never a sentence assembled here from the goal and
seat names, which is the trap ATTENTION 3 of `20260825-c-inspect-asks-the-read-half-of` names; and
the count is a fact OF the record, whose omission would render a ten-lane ask as one lane's
problem — the per-lane ask the grouping rule exists to forbid.

Rejected: a new Slack poster, explicitly out of scope and forbidden by `exhaustion.js`'s own header
("a recovery path that could post is a recovery path that silently becomes the notifier"). Rejected:
a fifteenth intent or a second target — ce-5/D3 says a read-only query extends `inspect`, and
`inspect asks` is already the digest's port, so a second port would give the owner two waiting sets.
Rejected: sorting with `Date.parse` — the two records carry different timestamp FORMATS
(`ask-record`'s coord stamp `2026-08-28 06:01` versus the record's ISO `2026-08-20T04:00:00Z`), and
parsing the former as local time against the latter as UTC would introduce a timezone skew into an
age the owner reads. A lexical sort is stable and honest; its one wart is that within a single
calendar day the ISO row sorts after the coord-stamped one, which costs ordering and no data.

## Consequences
Nothing was replaced or deleted; `inspect asks` gained rows and no key. The target set is untouched
in all four of its copies (gateway, core, CLI Set, CLI HELP), so no drift guard moves. The bridge
half needs no change and gets none: `chat/glance.js:180` calls `askRecord.listOpenAsks()`, which is
a gateway sender, so a DAEMON restart alone changes what the digest reads — the bridge is not the
unit that restarts. The digest posts on CHANGE, so the added row moves the snapshot once and then
rides the baseline rather than re-pinging.

An honest limit this does not close: there is no reaper for the grouped ask FILE. The `open_asks`
row has one (`reapAndRelaunch`); the record does not, so a listed recovery ask stays listed until an
owner act removes the file. Building a reaper needs a ruled owner act on the three-option ladder
(`retry-with-change` / `drop-lane` / `pause-goal`) and is not this change's to invent. And the
store-row half of `recordGroupedAsk` still lands in the ENDING store while `listOpenAsks` binds the
daemon's PRIVATE lane store — surfaced, not fixed, because `ask-record.js` is another component's.

## Verification
Commit `c481e177` on `ignite/core-daemon`.
`runtime/internal-api/probes/probe-inspect-asks.js` 28/28 EXIT=0 (was 20/20 at 26f4510e). The eight
new checks are a section (G) that writes the record through `exhaustion.js`'s OWN writer — never
hand-rolled JSON, because a fixture that invents the record shape proves the reader agrees with the
fixture and not with the producer — and then proves: the grouped record is in the listing; a
TWO-lane ask is exactly ONE row; the row shape key by key; the one-liner is the record's first
refusal line plus `(+1 more lane)`; `evidence_pointer` is the record file and it exists; the
thread-recorded owner asks are still there beside it (a merge, not a replacement); and the order is
oldest-first ACROSS both records. G8 is an in-probe red control that parks the asks directory and
asserts the grouped row disappears while the owner asks remain. External red mutation on a
discarded copy: removing `listOpenGroupedAsks` from the dispatch line reddens five arms (23/28),
green again on restore.

Unchanged before and after, each measured first on a pristine copy of 26f4510e:
`probe-chat-glance-wiring` 20 checks, `probe-chat-glance` 30, `probe-intent-drift` PASS,
`probe-start-execution` 20/20, `probe-pause-resume` 53/53, `probe-leader-wake-counter` 26/26,
`probe-code-deploy-rearm` 13, 12 of 13 supervisor selftests EXIT 0 with `reconcile.selftest.js`
EXIT 1 identically before and after. tmux session list byte-identical (18 sessions). NOT DEPLOYED
at filing; the DAEMON is the unit that must restart.

## ATTENTION
1. THE LISTER READS A DIRECTORY AND MUST STAY READ-ONLY. It opens no store, writes no file and
   mints no record. Giving it a store handle "so it can report the row's posted state" would put a
   second writer path into the ask surface and would make a READ able to fail the way a WRITE fails
   — the digest would then render an outage as an empty waiting set.
2. THE ONE-LINER COMES OFF THE RECORD, AND `null` IS THE HONEST ANSWER. A record with no refusal
   text gets no sentence. Filling it from the goal, the seat or the signature would put words on
   the owner's phone that nobody wrote, which is the same trap `20260825-c-inspect-asks-the-read-half-of`
   ATTENTION 3 records for the table half.
3. ONE ROW PER RECORD, NEVER ONE PER LANE. The whole of "signature-grouped" is that ten lanes
   failing the same way are ONE ask. Expanding the `lanes` array into one row each here would
   restore the per-lane ask [T1-R8, D-2-ruling] forbids, on the surface the owner actually reads.
4. THERE IS NO REAPER FOR THE RECORD FILE. A grouped ask listed here stays listed until the file is
   removed by hand or by a future owner-act door. Do not read a persistent row as a new alarm, and
   do not "fix" it by having the lister filter on the `open_asks` row — that table is in a
   different store from the one the record's row is written to.
5. THE TWO RECORDS CARRY DIFFERENT TIMESTAMP FORMATS and the merge sorts them lexically. Switching
   the comparator to `Date.parse` looks like a tidy-up and silently mixes a local-time coord stamp
   with a UTC ISO stamp, which shifts the AGE the digest renders by the box's UTC offset.
- one row per signature-grouped RECORD, never one per lane — expanding the lanes array restores the per-lane ask the grouping rule forbids
