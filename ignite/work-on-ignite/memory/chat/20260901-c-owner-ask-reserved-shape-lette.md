# 20260901-c-owner-ask-reserved-shape-lette — owner-ask reserved shape, letter->arm mapping, R-A1 fallback

kind: change
component: chat
date: 2026-09-01
commit: 9488ebaa
deployed: no
pin: ignite/chat/probes/probe-chat-ask-release.js
components: state-store

## Motivation
Owner ruling `d-owner-ask-shape` (interview 2026-09-01, `owner-ask-redesign.md`): the owner could
not act on daemon-generated owner-facing Slack asks ("it did not ask no clear question, and it did
not give any actual context"). §5.2's design gave every ask a reserved first line, a shaped body,
lettered options and a trailing id, and gave the OWNER a way to answer by letter instead of typing
the exact verb word — this seat (`ask-shape`, combining the design's `ask-marker-footer` +
`ask-letters` custody rows) is the one choke point every ask kind already passes through
(`chat-bridge.js#postOwnerAsk` -> `ask-thread.js#postAsk`) that R-A3's reserved marker and R-A5's
letter table are enforced at.

## Design
`ask-thread.js#openingLine`/`composeThreadOpener` render `<MARKER_ASK> NEEDS YOUR ANSWER —
<subject>`, then the body, then `a) <text>` per option (recommended one carrying its `why`), then
`More: <pointer>`, then `ref <suffix>` as the LAST line — every line consecutive (no blank
separator, matching the owner's phone-read example in §5.2b verbatim). `subject`/`options`/`more`
are new OPTIONAL params on `postAsk`; absent, `openingLine` falls back to `<seat> needs your
answer` and no letter/More lines render — this is what keeps escalation/ordinary/approval
(explicitly "not reshaped in this cluster", §5.5's closing note) posting correctly with zero
changes to their own composers. `MARKER_NOTE` (💭) is UNCHANGED — R-A3 names ❓ only.

`release()`'s letter->arm mapping is SCOPED to `kind: 'recovery'`/`'goal-disposition'` only — the
two kinds this design actually attaches an `options` table to. It never touches `reply-grammar.js`
(one parser, unchanged): a lettered reply is detected by re-probing `parseReply(text, {kind:
null})` when the kind-gated first call failed (recovery/disposition's own closed-vocabulary
branches never try a letter at all), the matched letter is looked up in `options`, and the
RESOLVED arm text (`${arm}${comment}`) is fed back through `parseReply(armText, {kind})` — the
SAME call a typed verb takes, so every downstream consumer (mechanical check, reap, `chat-
bridge.js#releaseAskFor`'s existing `entry.kind === 'recovery'`/`'goal-disposition'` dispatch
branches) sees an identical shape and needed ZERO changes. An unresolved letter (no table, or a
letter outside it) NACKs naming THIS ask's own real letters.

Rejected: extending the same mapping to `kind: null` (ordinary/approval/escalation) letters.
`probe-chat-approval.js` proved this wrong live: a `reject-and-pause`d approval thread's own
dispatch (`approval-thread.js`) already gives a bare letter real, deliberate meaning — "not one of
my three exit keys", reported in-thread without exiting the pause — and a blanket "no table ->
NACK" would have silently pre-empted that existing, working behavior. Scoping the mapping to the
two kinds that actually carry a table was the fix; ordinary/approval letters are untouched by this
seat, exactly as the interface contract's scope-limit states.

`chat-bridge.js#postOwnerAsk` implements R-A1 (channel-less fallback): when `goalChannelFor`
answers no channel AND `kind` is `recovery`/`goal-disposition`, it posts into
`config.systemChannelId` with the goal name prefixed to the subject (`<goal>: <subject>`) instead
of today's `{posted:false}` + retry forever (`inv-ask-paths` Held-but-dropped #1). Escalation's own
`postUnreachableChannelAlarm` mechanism is untouched — the fallback is scoped to exactly the two
kinds R-A1 names.

The ask's own `options` table is kept on `chat-bridge.js`'s existing in-process `askThreads` Map
entry (added at post time, read at release time) rather than round-tripped through the gateway/DB —
`inv-reply-grammar`'s own warning against a global letter budget is why this has to be per-ask, and
the map already is. It rides the existing additive state-file persistence
(`STATE_VERSION` unchanged) so a bridge restart between posting and the owner's reply does not
drop the table.

`open_asks` gains `kind`/`subject`/`options_json` (TEXT NOT NULL DEFAULT ''), added via a plain
`ALTER TABLE ... ADD COLUMN` migration (`state-store/open.js#migrateOpenAsksShape`, detected via
`PRAGMA table_info`) — unlike `goal_states.stored` gaining `closed`, none of the three carry a
CHECK, so the `migrateGoalStatesClosed` rename-rebuild dance does not apply; a plain ADD COLUMN is
the whole fix. `ask-record.js#openAsk` (daemon-side) accepts and stores them when supplied;
`listOpenAsks` enriches `listAllOpenAsks`'s row (`predicates.js`, outside this seat's custody, an
explicit column list that predates the two new columns) with a second per-row `getAsk` call
(`writers.js`, `SELECT *`, already returns them) rather than widening `predicates.js` — open-ask
counts are small and this is the 2-hourly digest's own read, never a hot path.

## How it works
Composer -> `chat-bridge.js#postOwnerAsk({..., subject, options, more})` -> `ask-thread.js#postAsk`
renders + posts, then calls `askRecord.openAsk({..., kind, subject, options})` (daemon-side
persistence, forward-compatible) -> owner replies a letter in-thread -> `chat-bridge.js#releaseAskFor`
passes `entry.options` into `askDoor.release({..., options})` -> `release()` maps letter to arm,
re-parses, reaps, and the EXISTING recovery/disposition dispatch branches in `releaseAskFor` fire
unchanged on the resolved `outcome`.

## Consequences
`ask-thread.js#openingLine`'s signature gained `subject`; `composeThreadOpener` gained
`subject`/`options`/`more` — both backward compatible (all optional, notes untouched).
`chat-bridge.js#postOwnerAsk`'s signature gained the same three plus the fallback logic; its one
caller inside this file (`postAsk: (args) => postOwnerAsk(args)`, wired to `bus-ferry.js`) is
unaffected since it forwards whatever object it is given. `probe-chat-ask-release.js` rewritten in
the places that hardcoded the OLD opening-line shape (`❓ <suffix> · <seat> · <label>`) — 26 checks
grew to 52.

NOT DEPLOYED — the daemon runs `~/.local/state/rbtv-deploy` (separate deploy window, this seat does
not open it).

**Known, disclosed gap — not built here, outside this seat's custody (Walls: "Custody is EXACTLY
the files named"):** `kind`/`subject`/`options` are forwarded from `ask-thread.js#postAsk` to
`askRecord.openAsk(...)` (the object `chat-bridge.js` builds from `ignite/chat/ask-store.js`'s
`createAskRecord`), but `ask-store.js#openAsk`'s own JS signature only destructures
`{goalId, seat, chatThreadId, text, label}` and builds a payload of exactly
`{act, goal, seat, thread, corpus, label}` for the `record-owner-ask` gateway intent — it silently
drops all three today. Even if it forwarded them, `runtime/internal-api/dispatch.js
#handleRecordOwnerAsk`'s strict payload allowlist (`['act','goal','seat','thread','corpus','label']`
for `act: 'open'`) would throw `VALIDATION_FAILED: unknown payload field`. Both files are outside
this seat's custody. Effect: on a LIVE post, `open_asks.kind`/`.subject`/`.options_json` land empty
today, identically to a pre-existing (pre-migration) row — the schema/storage capability is fully
built and proven (direct-call test, see Verification), but the crossing that would fill it on a
live post needs a two-file, two-line change (widen `ask-store.js#openAsk`'s destructured params +
built payload; widen `dispatch.js`'s `allowed` array + the `recordOwnerAsk({...})` call) that is
NOT this seat's to make.

## Verification
`node ignite/chat/probes/probe-chat-ask-release.js` — 52/52 checks, EXIT 0 (was 26). New: the
reserved-line render (with and without subject), the full R-A4 template render (direct-call,
matches §5.2b's example verbatim), the R-A5 letter matrix (`a`->retry-with-change carrying the
owner's comment, `b`->drop-lane, `c`->pause-goal, `keep`/`close` via letter on a disposition ask,
letter-with-no-table NACK, letter-outside-table NACK naming the ask's own real letters, an ordinary
ask's bare letter proven UNCHANGED — still reaps, never nacked), and R-A1 (posts to the system
channel with the goal-prefixed subject, plus a scope-limit check that an ordinary ask on the same
channel-less goal still gets `{posted:false}`).
Ran the full `ignite/chat/probes/` + `ignite/state-store/heart/probes/` dirs via
`node ignite/deploy/probe-suite.js --dir <dir> [--only ...]` (never the full suite —
`rbtv-probe-suite.timer`): 20/20 chat probes GREEN including `probe-chat-approval.js` (this caught
a real regression mid-build — see ATTENTION 1); state-store: 20 passed, 1 inoperative, 2
quarantined (`seam-closed-set`, `g225-atomic-turn-session` arm P) — identical pre-existing reds,
unrelated to this change, tracked under `probe-suite-green/2026-09-01/`.
`node ignite/state-store/ending-store.selftest.js` — ALL PASS, before and after.
Direct-call proof of the migration (idempotent ADD COLUMN against a simulated pre-migration
`open_asks`, existing row reads `kind:'' subject:'' options_json:''` after, CHECK constraints on
`label`/`state` still enforced) and of `ask-record.js#openAsk`/`listOpenAsks` round-tripping
`kind`/`subject`/`options` end to end — both ad hoc, not committed as probes (the schema/persistence
capability is proven; the gap is the crossing that would exercise it live, named above).
Committed `9488ebaa` on `ignite/core-daemon`.

## ATTENTION
1. The letter->arm mapping in `release()` is SCOPED to `kind === 'recovery' || kind ===
   'goal-disposition'` on purpose — do NOT widen it to `kind: null` (ordinary/approval/escalation).
   `probe-chat-approval.js`'s `reject-and-pause` arm ("D2: a recognized token that is NOT one of the
   three keys... says so in-thread") depends on a bare letter parsing as `family: 'lettered'` and
   reaching `approval-thread.js`'s own dispatch un-intercepted; a blanket NACK-on-no-table there
   silently breaks that arm (measured mid-build, this seat).
2. `ask-store.js`/`dispatch.js`'s two-file gap (Consequences, above) means `kind`/`subject`/
   `options_json` read EMPTY on every live-posted ask until that crossing is built — do not assume a
   populated `open_asks` row proves the render path; check the DEPLOYED `ask-store.js` first.
3. The per-ask `options` table lives ONLY in `chat-bridge.js`'s in-process `askThreads` Map (state-
   file persisted) — `release()` never re-derives it from the DB. A caller resolving a letter outside
   this bridge process (a console tool, a CLI settle door) has no access to it and must not assume
   letters resolve there.
4. `openingLine`'s ❓ shape carries NO id at all — the id moved to the LAST line (`ref <suffix>`).
   Any future reader that greps a Slack message's FIRST line for the ask id (the OLD shape) will find
   nothing; the id is now only in the last line and in the thread's own `thread_ts`.
5. `predicates.js#listAllOpenAsks`'s explicit column list was left untouched on purpose (outside
   custody) — `ask-record.js#listOpenAsks` compensates with a second `getAsk` call per row. A future
   editor tempted to "simplify" by having `listAllOpenAsks` select `*` should confirm no OTHER caller
   of that function assumes its old, narrower row shape first.
- letter->arm mapping is scoped to kind recovery/goal-disposition only — widening to kind:null breaks approval's reject-and-pause not-an-exit-key reporting
- ask-store.js + dispatch.js's payload allowlist drop kind/subject/options on every live post today — a 2-file gap outside this seat's custody, not yet built
- the per-ask options table lives only in chat-bridge.js's in-process askThreads map — release() never re-derives it from the DB
