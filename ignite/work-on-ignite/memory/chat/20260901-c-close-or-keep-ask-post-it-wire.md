# 20260901-c-close-or-keep-ask-post-it-wire — close-or-keep ask: post it, wire close/keep reply

kind: creation
component: chat
date: 2026-09-01
commit: 756e29d5
deployed: no
pin: ignite/chat/probes/probe-disposition-post.js
components: supervisor,gateway,runtime,ignite-cli

## Motivation
`d-hold4-wire-disposition-post` (this plan's ruling, following `judge-recovery`'s named fix
path) + the underlying `d-recovery-last-lane-asks`: `ignite/supervisor/last-lane-ask.js#
mintLastLaneAsk` writes a `goal-disposition` ask (`close`/`keep`) to disk and to `open_asks`
with `posted:0`, and nothing posted it to Slack or parsed a reply — `chat-bridge.js` carried
zero `goal-disposition` matches (re-verified: `grep -n "goal-disposition\|last-lane\|disposition"
ignite/chat/chat-bridge.js ignite/chat/ask-thread.js ignite/chat/reply-grammar.js` → zero, at
this seat's start). The result was a goal whose shutdown clock correctly suspends (the row exists)
but whose question the owner is never asked — a genuinely stuck, invisible-to-the-owner goal. This
seat builds the JOIN only: posting the already-minted ask, and parsing its reply.

## Design
Mirrors `chat/recovery-poster.js`'s already-proven shape for a DIFFERENT reason than reuse alone:
`supervisor/exhaustion.js`'s `listUnpostedLanes`/`markLanePosted` are shaped around a `record.lanes`
array (grouped-by-signature, many lanes per record); `mintLastLaneAsk`'s record is one row PER GOAL
with no `.lanes` array, so it needed its own reader/marker pair
(`last-lane-ask.js#listUnpostedDispositions`/`#markDispositionPosted`), not a call into the
lane-shaped ones. Discovered mid-build that the `record-owner-ask` gateway handler already calls
`markLanePosted` unconditionally whenever `payload.label === 'recovery'` — since the disposition
ask reuses that same label (mirroring `recordGroupedAsk`'s own choice), `markLanePosted` harmlessly
no-ops on a disposition record (no `.lanes` to match), so adding a second, disposition-shaped stamp
call beside it was correct and safe rather than a redesign.

`kind: 'goal-disposition'` joins `escalation`/`recovery` in `ask-thread.js`'s interactive bypass
(line ~199) for the same reason `recovery` is there: the daemon is reporting a system-decided fact
(a goal's last lane was dropped), never a seat's own decision to start a conversation.
`reply-grammar.js` gets its own kind-gated ladder (`close`/`keep`), isolated from `APPROVAL_TOKENS`'
own `close` outcome by `kind` alone, never by the token — the same isolation `kind:'recovery'`
already relies on.

`disposition-thread.js` (new, sibling to `recovery-thread.js`, not added into it — one file, one
outcome ladder, `no-monolith`) discovered mid-build that `keep` needs NO injected port at all:
`ask-thread.js#release` already reaps/settles the ask BEFORE dispatch ever runs, so "keep" IS
already true the moment the reply parses; the dispatch only posts the confirmation. `close` was
investigated for a real daemon-side act and found to have NONE: `state-store/vocabulary.js#
GOAL_WORDS` is a closed three-word enum (`running`/`paused`/`finished`), `finished` is the ONLY
terminal word and every downstream reader (`isGoalFinished`, reconcile.js, dashboards) treats it as
ordinary success. Stamping `finished` for a goal the owner gave up on would violate
`d-recovery-last-lane-asks`'s own words ("a goal given up on must never read as done"). A fourth
terminal word is a state-store vocabulary decision with its own blast radius across every goal-state
reader — outside a chat-wiring seat's scope to invent, and the seat's own Discipline names exactly
this stop condition ("If the dispatch half turns out to be its own design surface, STOP... do not
half-build it"). `closeGoal` therefore ships `null` (unwired) in `chat-bridge.js`, the SAME shape
`dropLane`/`retryWithChange` carried before their own seats built them — the dispatch reports the
honest refusal into the thread, never a fabricated success.

## How it works
`chat-bridge.js#releaseAskFor` now narrows `ask-thread.js#release`'s grammar to `kind:
'goal-disposition'` for a disposition thread (mirroring the existing `kind:'recovery'` narrowing on
the same line) and, on release, routes to `dispositionDispatch.dispatch` exactly where the recovery
block already routes to `recoveryDispatch.dispatch`. `disposition-poster.js` (new, mirrors
`recovery-poster.js` 1:1) polls `inspect disposition-asks` (a THIRD inspect target added in lockstep
across `gateway/parse.js`, `internal-api/dispatch.js`, AND `ignite-cli/commands/inspect.js` —
`probe-inspect-asks.js`'s A4 check and `probe-inspect-executions.js` independently enforce all three
stay identical; missing the CLI copy failed A4 on the first run, fixed in the same commit) and posts
each unposted disposition record through `chat-bridge.js#postOwnerAsk({kind:'goal-disposition',
label:'recovery', ...})` — the SAME `record-owner-ask` intent + `ask-thread.js#postAsk` a recovery
ask uses, which mints a NEW `open_asks` row keyed by the real Slack thread id (`ask_id` IS the
thread [T5-R7]) and flips IT to `posted:1`. The ORIGINAL mint-time row (`disposition-<hash>`, from
`mintLastLaneAsk`'s `store.insertAsk`) stays `posted:0` forever — an intentional orphan, the exact
same shape `exhaustion.js`'s recovery-lane rows already carry (documented at length in
`exhaustion.js`'s "POSTED LANES" header), not a new defect. `countOpenAsks` only needs ONE posted
row for the goal to suspend the shutdown clock, so the orphan costs nothing behaviourally.
`disposition-poster.js` is wired into `chat/index.js#buildBridge`/`#main` exactly beside
`recoveryPoster` (construction, `.start()`, `.stop()` on shutdown).

## Consequences
No existing behaviour was replaced or deleted. `record-owner-ask`'s dispatch handler
(`internal-api/dispatch.js`) grew one more best-effort stamp call beside `markLanePosted`, guarded
the same way (try/catch, warn-and-continue on failure, never changes the recorded outcome). Three
inspect-target enum copies grew one member each. No probe or selftest assertion was edited.

## Verification
New `chat/probes/probe-disposition-post.js` (24 checks, auto-discovered by
`ignite/deploy/probe-suite.js`), two stages: STAGE A mints a REAL disposition record via the
already-proven `mintLastLaneAsk` (not rebuilt), then runs `disposition-poster.js#checkAndPost`
through a fake gateway forwarder whose `inspect`/`record-owner-ask` handlers call the REAL
`listUnpostedDispositions`/`recordOwnerAsk`/`markDispositionPosted` in-process against the SAME real
ending store — proves the posted Slack text carries the goal id + both options in plain words, the
NEW `open_asks` row is `state=open, posted=1`, the original row stays `posted=0`, idempotency (a
second pass posts nothing), and the suspension chain (`countOpenAsks`) goes live. STAGE B, a full
`buildBridge` harness (`probe-chat-recovery-dispatch.js`'s own shape): `keep` releases + posts
confirmation, ok:true; `close` releases (ask settled) but dispatch reports `ok:false` naming the
unwired port honestly, NEVER a silent success; a discriminating control (`banana`) does not release
the ask and gets the disposition ladder's own NACK. `node ignite/deploy/probe-suite.js --only
probe-last-lane-ask,probe-drop-lane,probe-chat-recovery-dispatch,probe-reconcile,probe-disposition-post`
(run individually per `--only`'s own single-target contract) all GREEN, exit=0.
`probe-chat-boundary.js` still red — PRE-EXISTING (`bus-answer.js:55,158` `execFile`, unrelated to
this change; the new `disposition-poster.js`/`disposition-thread.js` files themselves show ZERO
forbidden-capability hits in that probe's own scan). `probe-inspect-asks.js`/
`probe-inspect-executions.js` both green after the CLI copy was added (their own drift guard,
`A4`/lockstep check, caught the omission on first run — fixed in the same commit, not a follow-up).
Committed `756e29d5`, not deployed — `ignite/chat/` and `ignite/runtime/` are pinned to the deploy
worktree; inert until a deploy window the orchestrator owns.

## ATTENTION
1. **The disposition ask's `open_asks` row is TWO rows, permanently, and that is correct.** The
   mint-time row (`ask_id = disposition-<hash>`) never gets posted; the REAL, answerable row is a
   SECOND one minted at post time, keyed by the Slack thread id. Do not "fix" the orphan — it is the
   same shape `exhaustion.js`'s recovery-lane rows already carry, and `countOpenAsks` only needs one
   posted row per goal regardless.
2. **`close` has NO daemon-side act.** `chat-bridge.js` wires `closeGoal: null` on purpose:
   `state-store/vocabulary.js#GOAL_WORDS` (`running`/`paused`/`finished`) has no "closed, not a
   success" terminal word, and `finished` is read as success everywhere. Whoever builds `close` for
   real must design that vocabulary addition (and sweep every `isGoalFinished`-style reader) FIRST —
   do not stamp `finished` as a shortcut; that is the exact silent-success `d-recovery-last-lane-asks`
   forbids.
3. **The inspect-target closed set has a THIRD copy nobody names in the two-copy comments.**
   `gateway/parse.js` and `internal-api/dispatch.js` say "THREE copies" in their own headers, but the
   third — `ignite/ignite-cli/commands/inspect.js#TARGETS` (plus its HELP text and its routing
   `if`) — is easy to miss because it lives in a different tree (`ignite-cli/`, not `runtime/`).
   `probe-inspect-asks.js`'s `A4` check is the only thing that catches a miss; it caught this seat's
   first pass.
4. **`markLanePosted` and `markDispositionPosted` are BOTH called, unconditionally, on every
   `label:'recovery'` post** — each is a safe no-op on the other's record shape (one has no `.lanes`,
   the other's `askIdForGoal` lookup finds nothing for a recovery signature id). Do not "simplify" by
   trying to detect which kind of record it is before calling either; the no-op IS the simplification.
- the mint-time open_asks row (disposition-<hash>) never gets posted — a SECOND row, keyed by the real Slack thread id, is the answerable one; do not fix the orphan
- close has no daemon-side act: state-store/vocabulary.js GOAL_WORDS has no closed-not-success terminal word; closeGoal ships unwired on purpose
- the inspect-target closed set has a THIRD copy at ignite-cli/commands/inspect.js#TARGETS, easy to miss since it lives outside runtime/
