# 20260901-i-record-owner-ask-dropped-kind — record-owner-ask dropped kind/subject/options at 3 doors

kind: issue
component: chat
date: 2026-09-01
commit: 6bfdcf84
deployed: no
pin: ignite/chat/probes/probe-ask-fields-carry.js
components: runtime,state-store

## Observed
Every live-posted owner ask persisted `open_asks.kind`/`.subject`/`.options_json` as empty, even
after seat `ask-shape` (9488ebaa) added the columns and taught `ask-thread.js#postAsk` to forward
`kind`/`subject`/`options` to its injected `askRecord.openAsk(...)`. Measured against the tree at
`e39360ef` (ask-shape's own memory-filing commit) in a scratch worktree, before any edit of this
seat's own: a full `postAsk` -> `ask-store` -> real gateway `parseRequest` -> real
`internal-api/dispatch.js` -> a scratch ending store round trip landed the row with
`kind:'' subject:'' options_json:''`, identical to a pre-migration row, while the ask itself still
posted and recorded successfully (`recorded: true`) — the gap was silent, never a refusal.

## Mechanism
Three independent drop points, not the two ask-shape's own memory entry (ATTENTION 2) named.
`ignite/chat/ask-store.js#openAsk` (:97-106 pre-fix) destructured only
`{goalId, seat, chatThreadId, text, label}` and built the wire payload as exactly
`{act:'open', goal, seat, thread, corpus, label}` — `kind`/`subject`/`options` were never read off
the caller. Even had it forwarded them, TWO more copies of the same closed field-set independently
dropped them on the live path: `ignite/runtime/gateway/parse.js#parseRecordOwnerAsk` (:741-775) runs
BEFORE dispatch (`gateway.js:103` calls `parseRequest` ahead of `dispatch`) — its `allowed` Set for
`act:'open'` was `{act,goal,seat,thread,corpus,label}` and `rejectUnknownKeys` would have THROWN had
the fields arrived, and its own hand-built return object (:767-774) re-dropped them regardless. And
`ignite/runtime/internal-api/dispatch.js#handleRecordOwnerAsk` (:1575-1615) carried the identical
allowlist (defense-in-depth, DEC-3's re-validation) plus a THIRD hand-built object — its call to
`recordOwnerAsk({...})` — that omitted the three fields even from the internal call into
`state-store/heart/ask-record.js#openAsk`, whose own `kind='' subject='' options=null` defaults
would then fire regardless of what the payload carried.

## Attempts
First attempt at THIS crossing held — the absence was reported, not corrected, exactly once before
now, and named precisely: `chat/20260901-c-owner-ask-reserved-shape-lette` (9488ebaa), whose own
Consequences section and ATTENTION 2 name the two-file gap (`ask-store.js`, `dispatch.js`) as
"outside this seat's custody" and left unbuilt on purpose. That entry did not know about the THIRD
drop point (`gateway/parse.js`) because it never traced the live call path past `dispatch.js`'s own
allowlist — this seat's read of `gateway/gateway.js:103` (`parseRequest` runs before `dispatch`) is
what surfaced it. Also checked: `gateway/20260824-c-13th-intent-record-owner-ask` (f9da72b7), the
intent's own landing, whose "How it works" states the field-set-per-act design (open carries the
ask's words and label, reap carries neither) that this fix extends rather than replaces — confirmed
this is a PAYLOAD change on the existing `record-owner-ask`/`open` act, no new intent, no new act.

## Fix
Widened the SAME closed field set in lockstep across all three drop points: `ask-store.js#openAsk`
now accepts `kind`/`subject`/`options` and adds them to the wire payload only when present (never
inventing a second `options_json` serialization — that stays `ask-record.js#openAsk`'s job, exactly
as the interface already divided it); `gateway/parse.js#parseRecordOwnerAsk`'s `allowed` Set and
return object both gained the three OPEN-only keys, with SHAPE validation (`kind`/`subject` string,
`options` array-or-null) mirroring the existing `label` check immediately above it;
`dispatch.js#handleRecordOwnerAsk`'s allowlist gained the same three (DEC-3 re-validation, unchanged
in spirit) and its `recordOwnerAsk({...})` call now threads them through to
`ask-record.js#openAsk`. The `reap` act's field set is UNTOUCHED — the closed-set discipline
`record-owner-ask`'s own design states (open carries the words, reap carries neither) holds exactly
as before.

Caught and fixed in the SAME change, before commit: the first version of the `ask-store.js` guard
used `if (subject !== undefined)`, but `ask-thread.js#postAsk`'s own "field not passed" sentinel is
`null`, not `undefined` (`subject = null, options = null` are its actual default parameters — every
sibling default in that file uses `null`, never a bare absent key). A caller that passes no subject
(escalation, ordinary, approval — "not reshaped in this cluster") therefore called `openAsk` with
`subject: null`, and `!== undefined` let it through: `String(null)` put the literal 4-character
string `"null"` into the wire payload and then into `open_asks.subject` — TRUTHY, which defeated
`system-digest.js#renderAskRow`'s empty-subject fallback to the `goal · seat · label · #id` shape
for every escalation. `probe-esc-replay.js`'s own regression sweep caught this (check J6: "the
escalation appears as a row in the rendered digest, identifiable as an escalation" — it stopped
matching once `subject` read `"null"` instead of `""`). Fixed by switching all three guards
(`ask-store.js`) to loose `!= null`, which catches both sentinels; `gateway/parse.js` and
`dispatch.js`'s own guards were already `!== undefined` against the WIRE payload, where an absent
field really is `undefined` (JSON has no way to carry a bare `null` key that differs from an absent
one once `ask-store.js` no longer sends it) — those two needed no change.

## Consequences
`ask-store.js#openAsk`'s signature gained three optional destructured params (`kind, subject,
options`, no defaults — presence is checked with `!= null` against the caller's actual value, which
may itself default to `null` upstream). `parseRecordOwnerAsk`'s and `handleRecordOwnerAsk`'s
`allowed` sets both grew by three entries, OPEN-act only; `reap`'s set is untouched, so a
reap payload carrying any of the three still refuses exactly as before (closed-set discipline
preserved). No other file needed a change: `authz.canRecordOwnerAsk({sender})` checks only the
sender's kind, never payload fields, and `gateway/parse.js#INTENTS`/`dispatch.js#INTENTS` (the
15-intent closed set `probe-intent-drift.js` guards) are untouched — this is a payload-shape change
on the existing `record-owner-ask` intent, not a new intent, confirmed by `probe-intent-drift.js`
staying green.

## Verification
Commit `6bfdcf84` on `ignite/core-daemon`. `node --check` on all four touched/added files.
New `ignite/chat/probes/probe-ask-fields-carry.js` (8 checks, EXIT 0) — RED-FIRST over the LIVE
path, not a direct store call: drives `ask-thread.js#postAsk` -> the REAL `chat/ask-store.js` sender
-> the REAL `gateway/parse.js#parseRequest` -> the REAL `internal-api/dispatch.js` (`createInternalApi`,
same in-process pattern `probe-inspect-asks.js` uses) -> a scratch ending store, and reads the row
back with `kind`/`subject`/`options_json` all populated and correctly shaped; confirms the digest's
own `listOpenAsks(workspaceRoot)` read sees them too; confirms a lettered reply (`a`) on the
live-posted ask still resolves through `release()` to its mapped arm carrying the owner's comment,
and the reap leg (act: reap, none of the three fields sent) still closes the row — no regression to
either half `ask-shape` already proved by direct call. Carries an in-probe RED CONTROL: a mutant of
`ask-store.js#openAsk` with the fix's three forwarding lines removed reproduces the live defect
exactly (ask still posts/records, `kind`/`subject`/`options_json` land empty) against the SAME real
crossing. Reproduced red authoritatively BEFORE building, against the actual pre-fix commit
`e39360ef` in a scratch worktree (`git worktree add /tmp/ask-fields-carry-red e39360ef`, this new
probe copied in and run there): 5 of 8 checks failed exactly as predicted (`kind`/`subject`/
`options_json` all empty), while the letter-resolution and reap checks passed unchanged (in-process
map, independent of the store fields) — confirms the fix is additive and the letter path was never
broken.
Regression sweep, `node ignite/deploy/probe-suite.js --dir <dir>` (never the full suite —
`rbtv-probe-suite.timer`): `chat/probes` 32/35 GREEN, 3 pre-existing quarantined
(`probe-chat-boundary.js` — a `bus-answer.js` `execFile` violation, unrelated to `ask-store.js`;
`probe-chat-live-session.js`; `probe-owner-ask-hold.js` — a pre-existing `TypeError` on `null.find`),
0 failed — all 3 quarantines reproduced byte-identically against a scratch worktree at `e39360ef`
with `node_modules` symlinked in, confirming pre-existing and unrelated.
`runtime/internal-api/probes` 15/16 GREEN, 1 pre-existing failed (`probe-inspect-asks.js` M1: a
mutation-testing needle against `state-store/heart/ask-record.js`'s OLD single-line `openAsk`
signature, made stale by `ask-shape`'s own `9488ebaa` landing before this seat touched anything —
reproduced identically at `e39360ef`, confirmed pre-existing, not filed here as it is another
component's probe). `runtime/gateway/probes` 5/5 GREEN. `state-store/heart/probes` 20 passed / 1
inoperative / 2 quarantined GREEN — identical to `ask-shape`'s own measured baseline
(`seam-closed-set`, `g225-atomic-turn-session` arm P). `node ignite/state-store/ending-store.selftest.js`
ALL PASS. NOT DEPLOYED — the daemon runs `~/.local/state/rbtv-deploy`, a separate deploy window this
seat does not open.

## ATTENTION
1. `ask-thread.js#postAsk`'s "not passed" SENTINEL FOR `subject`/`options` IS `null`, NEVER
   `undefined` (`subject = null, options = null` are the actual default parameters, matching every
   sibling optional field in that file). Any FUTURE forwarding site that copies this pattern and
   guards with `!== undefined` instead of `!= null` will leak `String(null)` — the literal 4-char
   string `"null"` — onto the wire, which is TRUTHY and silently defeats every downstream
   empty-field fallback (measured here: `system-digest.js#renderAskRow`'s subject fallback,
   caught by `probe-esc-replay.js` J6).
2. THIS INTENT HAS THREE INDEPENDENT COPIES OF ITS FIELD ALLOWLIST, NOT TWO. `ask-shape`'s own
   memory entry (`chat/20260901-c-owner-ask-reserved-shape-lette`) named only `ask-store.js` and
   `dispatch.js`; `gateway/parse.js#parseRecordOwnerAsk` is a THIRD, and it runs FIRST on the live
   path (`gateway.js:103` calls `parseRequest` before `dispatch`) — a field added to `dispatch.js`'s
   allowlist alone would still be silently stripped by the gateway before dispatch ever saw it. Any
   future field added to `record-owner-ask`'s `open` act must move in ALL THREE files in the same
   change, or the live path silently drops it while a probe that only exercises `dispatch.js`
   directly (never `parseRequest`) would report green.
3. `reap`'s FIELD SET IS DELIBERATELY UNCHANGED AND MUST STAY THAT WAY. `kind`/`subject`/`options`
   are `open`-only in all three copies, for the same reason `corpus`/`label` already were: a reap is
   resolution, not a place to restate the question's shape. Widening `reap`'s allowed set to accept
   any of the three would let a reaping call rewrite facts about an ask it did not open.
4. `probe-inspect-asks.js`'s `M1` red-proof check is a PRE-EXISTING, UNRELATED red (a mutation
   needle against `ask-record.js`'s pre-`9488ebaa` single-line `openAsk` signature, stale since that
   commit landed) — do not attribute it to this fix or to any future `record-owner-ask` change; it
   is `runtime`/`state-store`'s own probe to repair.
5. A NEW PROBE THAT DRIVES THE LIVE CROSSING (real `parseRequest` + real `dispatch.js` +
   a scratch store, no fake forwarder) is what caught both the original gap AND the `String(null)`
   regression; `probe-chat-ask-release.js`'s own fixtures use a HAND-ROLLED fake `askRecord`/
   forwarder and could not have caught either — a fake that never checks the wire shape proves the
   module's own decisions, never the crossing between modules. Future changes to this crossing
   should extend `probe-ask-fields-carry.js`, not the release probe's fakes.
- ask-thread.js#postAsk's not-passed sentinel for subject/options is null, never undefined — a !== undefined guard leaks String(null) onto the wire
- record-owner-ask's open act has THREE independent field-allowlist copies (ask-store.js, gateway/parse.js, dispatch.js), not two — gateway/parse.js runs first on the live path and must move in the same change
