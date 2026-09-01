# 20260901-c-owner-ask-letters-resolve-from — owner-ask letters resolve from the persisted row

kind: change
component: chat
date: 2026-09-01
commit: 548f1663
deployed: no
pin: ignite/chat/probes/probe-chat-ask-release.js
components: state-store

## Motivation
`ask-shape` (9488ebaa) gave every recovery/goal-disposition ask a letter->arm table and taught
`release()` to resolve a bare letter against it, but the table `release()` read was ONLY the
caller's `options` param -- `chat-bridge.js`'s in-process `askThreads` Map entry, filled ONLY inside
`postAsk` at post time. `ask-fields-carry` (6bfdcf84) separately made the SAME table durable as
`open_asks.options_json`. Measured by `asks-repost`: five live recovery asks it re-posted into their
existing threads (never through `postAsk`, since the thread already existed) carried a real
persisted table but no in-process Map entry, so a bare letter reply nacked "no lettered options" on
every one of them -- and would on EVERY open ask after a bridge restart, since a restarted process's
Map starts empty before any ask is re-touched. Two sources for one fact, and the durable one was
never read. This seat (`ask-options-from-row`) makes the persisted row authoritative.

## Design
`release()` still accepts the `options` param, but it is no longer authoritative -- it is now a
pure cache, read ONLY when the durable path cannot answer at all (`askRecord.listOpenAsks` not
wired as a function on the injected object, or an error/thrown call) or the row cannot be found by
id. The moment a row IS found, its `options` field wins outright, even when it is `null` ("this ask
has no table") and the in-memory param is non-empty -- a stale cache must never override a real
answer, or the design would still have two sources of truth for the case that actually matters.

Rejected: adding a new `getAsk`-by-id gateway call. `listOpenAsks` already reaches the bridge process
end to end with NO field allowlist on the read side (`dispatch.js`'s `inspect asks` target returns
`ask-record.js#listOpenAsks`'s rows verbatim, and `chat/ask-store.js#listOpenAsks` forwards
`res.result.rows` verbatim too) -- unlike `record-owner-ask`'s write-side payload, which has three
independent allowlists (`ask-fields-carry`'s own finding). Extending `listOpenAsks` to also carry
`options` reaches production the moment this commit deploys, with ZERO change needed in
`ask-store.js` or `dispatch.js` -- no companion crossing, no loose end left for a future seat on
this specific gap (contrast `ask-shape`'s own `kind`/`subject`/`options` write-side gap, which DID
need `ask-fields-carry`'s three-file fix).

`ask-record.js#listOpenAsks` parses `options_json` via a new local `optionsOf(row)` helper --
`null` on absent/corrupt JSON or a non-array, never `[]`, so a caller can still tell "no table" from
"a corrupt table" if it ever needs to. This is the ONLY place `options_json` is deserialized;
`ask-thread.js` never parses it a second time.

## How it works
`release()` on a lettered reply to a `recovery`/`goal-disposition` ask calls a new
`resolveOptionsTable(askId, cachedOptions)`: if `askRecord.listOpenAsks` is a function, call it,
find the row whose `id` matches this `askId` (string-compared), and return `Array.isArray(row.options)
? row.options : []` -- found-but-empty is `[]`, an authoritative "no table" nack, not a fall-through.
Only when `listOpenAsks` is missing, throws, or the row isn't found does it fall back to
`cachedOptions` (the existing `options` param). Everything downstream (arm lookup, re-parse through
the same `parseReply`, nack naming the resolved table's own letters) is unchanged from `ask-shape`'s
design.

## Consequences
`ask-record.js#listOpenAsks`'s returned row shape gained one field, `options` (array or `null`),
additive and backward compatible -- `system-digest.js#renderAskRow` and every other existing reader
of that row ignores an unknown field. `ask-thread.js#release()`'s `options` param is UNCHANGED in
signature but demoted from authoritative to fallback-only; `chat-bridge.js` (outside this seat's
custody) still passes `options: entry.options || null` at its one call site -- that argument is now
read only in the fallback branch, which is dead weight from THIS seat's own vantage but not a
violation this seat introduced (the Map field itself, and whether to keep populating it, is
`chat-bridge.js`'s call, outside custody -- surfaced, not touched). `createAskThreads`'s constructor
check (`askRecord.openAsk`/`.reapAsk` required) is UNCHANGED on purpose: `askRecord.listOpenAsks` is
treated as OPTIONAL at the door specifically so a caller that never wires it (any current fixture, or
a future embedder) keeps today's in-memory-only behavior instead of throwing at construction time --
the fallback exists for exactly this case.

## Verification
`node ignite/chat/probes/probe-chat-ask-release.js` -- 55/55 (was 52). RED-FIRST: the 3 new checks,
copied onto the pre-fix tree at commit `1810a174` in a scratch worktree
(`git worktree add /tmp/ask-options-from-row-red 1810a174`), failed exactly as predicted (2 nacked
where the fix releases, 1 released where the fix nacks); the identical fixture is green on the fixed
tree. New checks prove: (1) a bare letter resolves via the persisted row when the caller passes no
`options` at all (the restart/repost case); (2) a letter outside the persisted row's table nacks
naming THAT row's own real letters, with no in-memory table involved; (3) a row found with
`options: null` nacks even when the caller's stale in-memory `options` param is non-empty -- the
durable answer is never overridden. All 5 of `ask-shape`'s original letter cases (a/b/c on recovery,
keep/close by letter on disposition, no-table nack, outside-letter nack, ordinary-ask scope-limit)
still pass unchanged, via the same fallback branch, proving no regression to the in-process path.
Regression sweep: `node ignite/deploy/probe-suite.js --dir chat/probes` -- 32 passed / 3 quarantined
(`probe-chat-boundary.js`, `probe-chat-live-session.js`, `probe-owner-ask-hold.js`), 0 failed, GREEN
-- identical to the pre-existing baseline `ask-fields-carry` (6bfdcf84) measured. `node
ignite/deploy/probe-suite.js --dir state-store/heart/probes` -- 20 passed / 1 inoperative / 2
quarantined (`probe-seam-closed-set.js`, `g225-atomic-turn-session` arm P), GREEN -- identical to
`ask-shape`'s and `ask-fields-carry`'s own measured baseline. `node
ignite/state-store/ending-store.selftest.js` -- ALL PASS. Committed `548f1663` on `ignite/core-daemon`.
NOT DEPLOYED -- the daemon runs `~/.local/state/rbtv-deploy`, a separate deploy window this seat does
not open.

## ATTENTION
1. `askRecord.listOpenAsks` IS OPTIONAL at `createAskThreads`'s construction door, unlike
   `openAsk`/`reapAsk` -- a caller that never wires it (today's production `chat-bridge.js` injects
   `chat/ask-store.js`'s object, which DOES already have `listOpenAsks`, so this is live from this
   commit's deploy, not a gap) silently keeps the fallback-only, in-process-cache behavior instead of
   throwing. Do not assume every future `askRecord` implementation carries it.
2. `resolveOptionsTable` treats "a row was found" as authoritative even when `row.options` is
   `null` -- it returns `[]` (a real "no table" nack) rather than falling through to the cache. A
   future editor tempted to "improve" this by falling back to the cache whenever the row's own
   table is empty would silently resurrect the two-sources-of-truth bug this seat closes.
3. `open_asks.options_json` is deserialized in EXACTLY ONE place, `ask-record.js#optionsOf`. Any
   future reader of an `open_asks` row's options must call through `listOpenAsks` (or a future
   `getAsk`-shaped wrapper built the same way) rather than parsing `options_json` again -- a second
   parser is a second source for the SAME shape decision (array-or-null on corrupt JSON) this one
   already made.
4. `chat-bridge.js`'s `askThreads` Map still tracks `.options` per entry and still passes it into
   `release()` -- this is now read-path DEAD WEIGHT from this seat's own change (it is spent only in
   the fallback branch), but the Map and its population are outside this seat's custody and were
   surfaced, not touched, per the walls ("Custody is EXACTLY the files named").
- resolveOptionsTable treats a found row as authoritative even with options:null -- never falls back to the cache once a row is found
- askRecord.listOpenAsks is OPTIONAL at construction, unlike openAsk/reapAsk -- a caller without it silently keeps fallback-only behavior
