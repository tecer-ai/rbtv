# 20260830-i-asks-read-from-the-private-sto — asks read from the private store, not the ending one

kind: issue
component: state-store
date: 2026-08-30
commit: 361a56f2
deployed: no
pin: ignite/runtime/internal-api/probes/probe-inspect-asks.js
components: runtime,supervisor,chat

## Observed
`inspect asks` (the daemon target the bridge's 2-hourly system digest reads through, and `ignite
status`'s surface) could not see an owner ask opened through the thirteenth intent
(`record-owner-ask`) whenever the daemon's own `heartStore` was not, coincidentally, the same file
as the workspace's ending store. Same shape for `start-execution`'s own approval check: an ask
genuinely opened and released could still be refused `no-approval-record`. Root cause, cited
before any edit: `ignite/state-store/heart/ask-record.js:104` (`openAsk`), `:132` (`reapAsk`),
`:189` (`listOpenAsks`) and `ignite/state-store/heart/start-execution.js:100`
(`refuseReason`'s `getAsk`) all did `bind(heartStore.db)` — binding whichever store the CALLER
already held. `dispatch.js`'s `heartStore` is the daemon's PRIVATE lane store; `open_asks` is one
of the four tables `state-store/open.js`'s own header states its ending-store handle is for
(`seat_endings`, `goal_states`, `open_asks`, `seat_holds`), resolved at
`<workspace>/.rbtv/runtime/ignite/heart.db` by `paths.js#endingStorePath`. This is the third site
of the exact cause `919be192` fixed and named as a sibling in its own closing paragraph
(`state-store/20260828-i-pause-wrote-a-store-the-lane-g`, ATTENTION carried forward): "A SIBLING
OF THE SAME CAUSE, SURFACED NOT FIXED: `start-execution.js:100` does
`bind(heartStore.db).getAsk(String(thread))`". Owner ruling D-5(a), 2026-08-30, ordered it fixed.

## Mechanism
Two writers/readers of `open_asks`, and two of the three call sites never checked which store they
were bound to. `record-owner-ask`'s daemon-side writer (`ask-record.js#openAsk`/`#reapAsk`) and the
digest's own read target (`ask-record.js#listOpenAsks`, spent by `dispatch.js`'s `inspect asks`
handler) all bound `heartStore.db` — the handle `createInternalApi({ heartStore, ... })` was
constructed with, which under the daemon is `{data_root}/heart.db`
(`StateDirectory=rbtv-ignite`), never the ending store the lane gate and every caged seat actually
read (`297765d8`'s file family). `start-execution.js#refuseReason` repeated the same bind for its
`getAsk` approval check. Every existing fixture (`probe-inspect-asks.js`, `probe-start-execution.js`)
handed the dispatcher `heartStore: { db }` where `db` IS the workspace's ending store, so a caller
bound to its own handle looked identical to one bound to the home — the exact reason `919be192`'s
own probe section (h) states for why the sibling shipped unmeasured.

## Attempts
First attempt at THIS fix held — the absence was reported, not corrected, three times before now.
Checked before building: `919be192` (`state-store/20260828-i-pause-wrote-a-store-the-lane-g`),
whose fix IS the pattern this change copies (`openEndingStoreFor(workspaceRoot)`, no store
parameter) and whose closing paragraph named `start-execution.js:100` as the surfaced-not-fixed
sibling; `c481e177` (`runtime/20260828-i-the-recovery-exit-s-ask-reache`), whose own Consequences
section named `ask-record.js`'s store-row half of the split explicitly as "surfaced, not fixed,
because `ask-record.js` is another component's"; `eb0e4828`
(`runtime/20260828-i-the-engine-never-held-the-endi`), which made `engine.endingStore` real so the
comparison in this fix has a genuine ending-store write to check against; `f9da72b7`
(`gateway/20260824-c-13th-intent-record-owner-ask`), the thirteenth intent's own landing, whose
"How it works" names `server/heart/ask-record.js` (now `state-store/heart/ask-record.js`) as the
daemon-side writer this fix corrects; and `a49f9df8`/`dae7b4f5`
(`gateway/20260824-c-14th-intent-start-execution`), `start-execution.js`'s own landing.

## Fix
`openAsk`, `reapAsk`, `listOpenAsks` (`ask-record.js`) and `refuseReason`/`startExecution`
(`start-execution.js`) now resolve `bind(openEndingStoreFor(workspaceRoot))` and take NO store
handle from their caller at all — `openAsk`/`reapAsk`/`refuseReason`/`startExecution` lost their
`heartStore` first parameter entirely, and `listOpenAsks(heartStore)` became
`listOpenAsks(workspaceRoot)`. `workspaceRoot` was already threaded through every one of these
calls (it is part of the `openAsk`/`reapAsk` options object, and `dispatch.js` already refuses
`start-execution`/`record-owner-ask`/`inspect asks` when `workspaceRoot` is absent), so no new
plumbing was needed — only the store resolution at the point of use. `bindEnding`
(`supervisor/ending-reads.js`) was rejected for the same reason `919be192` rejected it here: it is
the READER's fall-through resolver and falls back to the lane store when the home cannot be
opened, which is fail-safe for a reader and precisely the wrong answer for a writer — a writer
that cannot open its home must throw, not silently write elsewhere. `openEndingStoreFor` is the
one resolver both the write half (`openAsk`/`reapAsk`) and every read half
(`listOpenAsks`, `start-execution`'s approval check) now spend, matching `pause-resume.js`'s own
ending-store call. `dispatch.js`'s three call sites (`record-owner-ask`, `inspect asks`,
`start-execution`) were updated in the same change, since a signature change includes its callers.

## Consequences
`openAsk`/`reapAsk`/`refuseReason`/`startExecution`'s signatures changed from `(heartStore, opts)`
to `(opts)`; `listOpenAsks` changed from `(heartStore)` to `(workspaceRoot)`.
`recordOwnerAsk(heartStore, payload)` became `recordOwnerAsk(payload)`. `grep -rn
"openAsk(heartStore\|reapAsk(heartStore\|listOpenAsks(heartStore\|startExecution(heartStore\|recordOwnerAsk(heartStore"
ignite` returns nothing outside the two probes, both updated. `chat/glance.js` needed no change:
it calls a DIFFERENT, bridge-side `chat/ask-store.js#listOpenAsks()` — a gateway sender reaching
`inspect asks`, never this file's export directly — so the walls named it defensively and it turned
out to hold no call site of the changed signature. `supervisor/exhaustion.js` likewise needed no
change: its `recordGroupedAsk`/`listOpenGroupedAsks` write and read a separate, file-backed record
and were not part of this split (its `store.insertAsk` row is a different, unposted row that
`listOpenAsks`'s own `posted=1` default already excludes, by design, from this listing).

## Verification
Commit `361a56f2` on `ignite/core-daemon`.
`node --check` on all five edited files.
`runtime/internal-api/probes/probe-inspect-asks.js`: 20 → 35 checks, EXIT 0. New section H opens
an ask through the FIXED `openAsk` into a SECOND scratch workspace whose process also holds a
genuinely different, empty private store (never `endingStorePath`), and proves: the row lands in
the ending store and not the private one (H2); `listOpenAsks(workspaceRoot)` finds it (H3). A red
mutation beside the source (never touching the committed file) restores the pre-fix shape —
`openAsk(heartStore, …)` / `listOpenAsks(heartStore)` with `bind(heartStore.db)` — and run against
the SAME private store reproduces the live defect exactly: the ask lands in the private store, not
the ending store (M3), and the FIXED reader answers NOTHING for it while the mutant's own
private-store reader still sees it (M4) — that is the split, measured from a red mutant and a green
original in the same run.
`runtime/internal-api/probes/probe-start-execution.js`: 20 → 25 checks, EXIT 0. A new SPLIT section
opens and releases an approval ask through the fixed writer into a third scratch workspace, proves
a private store this SAME process also holds carries no such ask (SPLIT-2), and that
`startExecution` still finds the approval and births (SPLIT-3) — its `getAsk` resolved the ending
store, never the private one it was handed. A second red mutation (`SPLIT-MUTANT`) restores
`refuseReason(heartStore, …)`/`bind(heartStore.db)` and, handed the private store, refuses a
GENUINELY existing approval as `no-approval-record` (SPLIT-M2) — the live defect, reproduced.
Existing sections A-G / A-M in both probes are otherwise unchanged and green; both probes' prior
signature-bound call sites (`{ db }` as the removed first argument) were updated to match.
Regression sweep, each pristine before/after this change: `probe-pause-resume.js` 53/53 unchanged;
`probe-chat-glance.js` 30/30; `probe-chat-glance-wiring.js` 20/20; `probe-chat-approval.js` 24/24;
`probe-intent-drift.js` PASS; `probe-engine-ending-store.js` 14/14;
`supervisor/probes/probe-leader-wake-counter.js` 26/26; `state-store/ending-store.selftest.js` ALL
PASS; nine of ten `supervisor/*.selftest.js` files green. Unchanged, pre-existing reds (present
before this change and cited by earlier entries, NOT caused by it): `probe-chat-ask-release.js` E7
([T2-R14], a bus-ferry cursor question this change does not touch — same red
`chat/20260830-i-a-released-ask-showed-nothing` names); `probe-daemon-code-fingerprint.js` 29/30
(same pre-existing red `state-store/20260828-i-pause-wrote-a-store-the-lane-g` names);
`reconcile.selftest.js` aborts on an unrelated `BOOT-PROMPT-BODY` assertion (same five pre-existing
top-level asserts `runtime/20260828-i-the-engine-never-held-the-endi` measured). No tmux command
was run during this fix — session count untouched (still 19). NOT DEPLOYED at filing; the DAEMON
is the unit that must restart (`dispatch.js`, the executors, and both probes all boot from
`/home/henri/.local/state/rbtv-deploy`).

## ATTENTION
1. NONE OF THE FOUR FUNCTIONS TAKE A STORE HANDLE FROM THEIR CALLER, AND THAT ABSENCE IS THE FIX.
   Re-adding a `heartStore` parameter "for symmetry" to `openAsk`, `reapAsk`, `listOpenAsks` or
   `startExecution` re-opens exactly this defect: a caller's lane store is not the ending home, and
   an ask read or written there disagrees with every other reader of `open_asks`. The home is
   derived from `workspaceRoot` only, exactly as `pause-resume.js` already does.
2. DO NOT REACH FOR `bindEnding` HERE, for the reason `919be192` already gives: it is the READER's
   resolver and falls through to the lane store when the home cannot be opened — correct for a
   reader answering "nothing declared", wrong for a writer or for an approval check, both of which
   must throw rather than silently consult the wrong file.
3. `chat/glance.js`'s `askRecord.listOpenAsks()` is a DIFFERENT function in a DIFFERENT component
   (`chat/ask-store.js`, a bridge-side gateway sender) from this file's export. Do not conflate the
   two when tracing a future ask-surface defect — grep the actual `require` path, not the method
   name.
4. `recordGroupedAsk`'s store row is a SEPARATE record from what this fix touches: it is unposted
   by design (`posted: 0`), so `listOpenAsks`'s `posted = 1` default already excludes it regardless
   of which store it lands in. Its owner-visible surface is the FILE, read by
   `exhaustion.js#listOpenGroupedAsks` — untouched by this change and already merged into
   `inspect asks` by `c481e177`.
5. BOTH PROBES' FIXTURES STILL HAND THE DISPATCHER `heartStore: { db }` WHERE `db` IS THE SAME
   ENDING STORE, in every section except the new SPLIT/H sections. That is deliberate — those
   sections test the ordinary ladder — but it means only the new sections can ever catch a
   regression of this exact split. Collapsing them back into the shared fixture "to remove
   duplication" deletes the only measurement of the fact this entry fixes.
- none of the four functions take a store handle from their caller, and that absence is the fix — re-adding heartStore re-opens the split
