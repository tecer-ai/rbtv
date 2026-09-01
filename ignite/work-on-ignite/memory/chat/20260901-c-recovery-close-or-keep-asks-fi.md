# 20260901-c-recovery-close-or-keep-asks-fi — recovery + close-or-keep asks fill the ruled template

kind: creation
component: chat
date: 2026-09-01
commit: 45fa2c44
deployed: no
pin: ignite/chat/probes/probe-recovery-post.js
components: supervisor

## Motivation
`owner-ask-redesign.md` §5.2(b)/(c) rules ONE template for every daemon-authored ask: a plain-words
subject, a three-line body (`What happened:` / `Its last words:` / `Question:`), and a lettered
options table with a recommendation — replacing the machine-shaped `LANE:`/`driver:`/`reason:`/
`attempts:` text the owner could not read or answer. `recovery-poster.js#composeRecoveryBody` (the
recovery ask) and the goal's close-or-keep ask (`last-lane-ask.js` → `disposition-poster.js`) are the
two daemon-authored kinds this seat owns; escalation/approval composers already write agent prose and
are out of scope (`redesign-continue-1` §5.5, disclosed scope limit).

## Design
Both composers produce the SAME contract shape — `{subject, body, options, more}` — that
`chat-bridge.js#postOwnerAsk`/`ask-thread.js#postAsk` (a sibling seat's parallel work against the
same fixed interface) render into the reserved first line + lettered table + `ref` footer. Neither
composer builds Slack markup itself; `ask-thread.js#openingLine` owns the reserved
`❓ NEEDS YOUR ANSWER —` line exclusively.

`recovery-poster.js`: `subjectFor`/`whatHappenedFor`/`lastWordsLine`/`optionsFor` are small pure
functions over the lane row `exhaustion.js#listUnpostedLanes` already shapes — the `unread` driver's
"(none — it never got far enough to say anything)" line falls out of a single check
(`lane.last_words` present or not), never a per-driver branch, since `unread`/`room`/other
non-seat-authored drivers all structurally lack seat words the same way. The old hand-duplicated
`OPTIONS_LINE` constant (a plain sentence, "Reply with one word: …") is replaced by
`RECOVERY_OPTIONS`, the ONE source for the lettered table — `exhaustion.js#ASK_OPTIONS` remains the
arm-token source (`chat/` may not `require()` `supervisor/`, `probe-chat-boundary.js`), so
`RECOVERY_OPTIONS`'s `arm` values are kept byte-identical to it by inspection, proven by a new probe
check rather than a shared import.

`last-lane-ask.js`/`disposition-poster.js`: mirrors the recovery ladder's OWN mint-vs-post split
(`exhaustion.js`'s header: "NO SLACK... This module writes a RECORD and stops"). Before this change,
`mintLastLaneAsk` baked a flat body STRING into the record at MINT time (`composeBody`), and
`disposition-poster.js` just forwarded `row.body` verbatim — a SECOND, earlier composition point that
would have drifted from the ruled template the moment either side changed. `composeBody` is deleted;
`mintLastLaneAsk` now stores the RAW abandoned-seat rows (`seat`, `anchor`, `abandoned_by`,
`abandoned_at`), and the new `disposition-poster.js#composeDispositionBody` composes the contract
shape fresh at POST time, exactly once, from those raw fields — one composition point, matching
recovery's.

The recommendation rule (DoD 4: recommend `keep` unless every lane was dropped BY THE OWNER) reads
`abandoned_by` off each abandoned-seat row — `state-store/writers.js#abandonSeat` REFUSES to write a
row without it, and `drop-lane.js` is the only producer, always stamping `'owner'` (an owner's own
reply to a recovery ask). So in the system as it exists today, this condition is always true when the
ask fires — a design note, not a bug: the rule is written for the general case (`abandoned_by` could
in principle carry another value if a future producer exists) and costs nothing to check generically.

## How it works
`composeRecoveryBody(lane)` → `{subject, body, options, more}`; called from
`recovery-poster.js#checkAndPost` in place of the old flat-body call, spreading the four fields into
`postOwnerAsk`. `composeDispositionBody(row)` → same shape, called from
`disposition-poster.js#checkAndPost`; `more` is `.rbtv/goals/<goal>` (already workspace-relative,
never absolute — no path math needed, unlike the recovery ask's transcript pointer). Switching
`abandoned_seats` from bare seat-name strings to full row objects (needed for the recommendation
rule) would have silently broken `disposition-poster.js`'s existing `seatName: row.abandoned_seats[0]`
line — it read the array's first element directly as a seat name, which the OLD string shape made
correct and the new object shape would have made `"[object Object]"`. Caught and fixed in the same
change (`seatName: firstAbandoned.seat`), not a follow-up — a violation this seat's own edit would
have created, fixed inline per the coding skill's rule 1.

## Consequences
`exhaustion.js`'s lane field rename (`refusal_text` → `last_words` + `evidence_pointer`/`first_at`/
`last_at`/`outcome`, filed under `component: supervisor`) is what feeds `listUnpostedLanes`, which
this composer consumes — see that entry for the producer side. `last-lane-ask.selftest.js`'s one
assertion on `record.abandoned_seats`'s shape was updated (plain seat-name strings → the full row
objects) in the same commit.

## Verification
New `chat/probes/probe-recovery-post.js` (17 checks, STAGE A mints a REAL exhausted lane via the
real `exhaustion.js#exhaust` against a real ending store, posts it through `recovery-poster.js#
checkAndPost` via a fake gateway forwarder whose handlers call the REAL `listUnpostedLanes`/
`recordOwnerAsk`/`markLanePosted` in-process — `probe-disposition-post.js`'s own evidence class —
plus 4 unit checks on `composeRecoveryBody`'s `unread`/`launch-refused`/options-source branches).
Proves, against the sibling seat's ALREADY-LANDED `ask-thread.js`/`chat-bridge.js` contract
rendering (uncommitted in this same tree at verification time): the reserved first line, the
plain-words subject, the seat's quoted diagnostic, the lettered table with `c` recommended at 3
attempts, and the vault-relative `More:` pointer, all appear in the actual posted Slack text — not
merely in the composer's return value. `probe-disposition-post.js` re-run green (34 checks, all
pre-existing) after this seat's `last-lane-ask.js`/`disposition-poster.js` edits.
`probe-chat-recovery-dispatch.js` re-run green (21 checks, unaffected — it posts its own literal
body string, never through `recovery-poster.js`). `probe-chat-boundary.js` still red — PRE-EXISTING
(`bus-answer.js` `execFile`, unrelated; `recovery-poster.js`/`disposition-poster.js` themselves show
ZERO forbidden-capability hits in that probe's own scan, confirmed in this seat's run). Committed
`45fa2c44`, not deployed — `ignite/chat/` is deploy-pinned; inert until the orchestrator's deploy
window.

## ATTENTION
1. **`RECOVERY_OPTIONS`'s `arm` values are a HAND-KEPT second copy of `exhaustion.js#ASK_OPTIONS`,
   deliberately** — `chat/` cannot `require()` `supervisor/` (`probe-chat-boundary.js`'s own wall).
   `probe-recovery-post.js`'s U4 check is what catches drift; do not delete it as "redundant."
2. **The recommendation rule (`keep` unless every lane dropped by owner) is currently a near-tautology**
   — every producer of `abandoned_by` stamps `'owner'` today, so `close` is always the recommended
   letter in practice. This is not a bug to "simplify away" — the rule is written correctly for a
   system where a second abandonment producer (e.g. a system auto-drop) could exist later.
3. **`abandoned_seats` changed shape (seat-name strings → full row objects) in this same change** —
   any OTHER reader of `record.abandoned_seats`/`row.abandoned_seats` added later must expect
   `{seat, anchor, abandoned_by, abandoned_at}` objects, never bare strings; `disposition-poster.js`'s
   own `seatName` line was the one place this bit, fixed in the same commit.
- RECOVERY_OPTIONS mirrors exhaustion.js#ASK_OPTIONS by hand — chat/ cannot require() supervisor/, probe-recovery-post.js U4 catches drift
