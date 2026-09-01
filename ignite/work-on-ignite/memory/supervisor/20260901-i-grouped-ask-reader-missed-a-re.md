# 20260901-i-grouped-ask-reader-missed-a-re — grouped-ask reader missed a record-level posted stamp

kind: issue
component: supervisor
date: 2026-09-01
commit: d72538e0
deployed: no
pin: NONE
components: chat,state-store

## Observed
`inspect asks` (the system digest's read target) listed four ghost rows — `disposition-a195c85c0e34`
(`test-disp-close-w5`), `disposition-2b5c15cbd3c7` (`test-disp-keep-w5`), `disposition-c4aa162c7b6a`
(`test-disp-close-w6`), `disposition-812e79ca60cb` (`test-disp-keep-w6`) — for asks that had already
been posted to Slack and answered; the digest kept re-rendering them "waiting" forever. Measured
2026-09-01 23:00Z against the live workspace's `.rbtv/runtime/ignite/asks/disposition-*.json`: all
four carry `kind: 'goal-disposition'`, a top-level `posted_ask_id` (their real Slack thread ts), and
`lanes: null`.

## Mechanism
`exhaustion.js#listOpenGroupedAsks` (:224-242) synthesizes a single empty lane `[{}]` when
`record.lanes` is missing or empty (:227) so a lane-less record still renders one row while unposted
— correct, since a `goal-disposition` record (`last-lane-ask.js#mintLastLaneAsk`) never writes a
`.lanes` array by design. But the posted-skip at :229 checked ONLY `lane.posted_ask_id`. On the
synthesized `{}` that field is always `undefined`, so the check never fires for a disposition
record. The record's actual posted stamp lives at the RECORD's own top level
(`last-lane-ask.js#markDispositionPosted` sets `record.posted_ask_id`, never a lane field) — the
reader never looked there, so a posted-and-closed disposition ask kept satisfying "unposted" and
was re-emitted on every digest render.

## Attempts
First attempt at THIS problem held — checked before building: `runtime/20260828-i-the-recovery-exit-s-ask-reache`
(c481e177, `listOpenGroupedAsks`'s own creation, whose header states the contract "a POSTED lane is
skipped here entirely" and whose ATTENTION 4 forbids fixing this by cross-checking the `open_asks`
store row instead of the file); `chat/20260901-c-close-or-keep-ask-post-it-wire` (756e29d5, which
built `markDispositionPosted`/`record.posted_ask_id` and explicitly notes disposition records have
no `.lanes` array, needing their own reader pair rather than `exhaustion.js`'s lane-shaped ones — but
did not touch `listOpenGroupedAsks` itself, since its own read path is `inspect disposition-asks` via
`last-lane-ask.js#listUnpostedDispositions`, a different target); `state-store/20260830-i-asks-read-from-the-private-sto`
(361a56f2, ATTENTION 4: confirms `recordGroupedAsk`'s file-backed record is untouched by the store
split and is `exhaustion.js#listOpenGroupedAsks`'s own to fix, never a store-side dedup).

## Fix
`listOpenGroupedAsks`'s posted-skip now reads `record.posted_ask_id || lane.posted_ask_id` — one
source rule at the reader: a recovery record's own lanes carry the posted stamp, a disposition
record's top level does, and both are checked in the same line rather than branching on `record.kind`.
Rejected: filtering by cross-checking the live `open_asks` DB row for a matching, now-closed ask —
`runtime/20260828-i-the-recovery-exit-s-ask-reache` ATTENTION 4 names this exact move as a trap
("that table is in a different store from the one the record's row is written to"); the DB's
`open_asks` rows for a grouped/disposition ask are `posted=1`+real-thread-keyed rows that
`listOpenAsks` already includes or excludes correctly on its own, and `dispatch.js`'s union
(`internal-api/dispatch.js:1019`) is a plain concat with no dedup — verified it needs none, since a
closed DB row was never the source of the ghost (the DB side was already correct; only the file
reader was wrong).

## Consequences
Nothing removed or replaced. `listUnpostedLanes` (:261-286, the recovery-poster's own read) was
already unaffected — it iterates `record.lanes` directly with no `[{}]` fallback, so a lane-less
disposition record already produced zero rows there. No signature change; no caller outside this
file touches `listOpenGroupedAsks`'s return shape.

## Verification
Commit `d72538e0` on `ignite/core-daemon`. `node --check ignite/supervisor/exhaustion.js` clean.
Red-first: a scratch worktree at pristine HEAD (`429be888`) vs the fixed working tree, both fed the
SAME scratch asks dir (one disposition record, posted, no lanes; one recovery record with a posted
lane and an unposted lane) — pre-fix emits the disposition row, post-fix does not; the recovery
record's per-lane behaviour (posted lane suppressed, unposted lane rendered) is byte-identical
before and after. Against the LIVE workspace, read-only: `listOpenGroupedAsks('/home/henri/ht-wkdir/second-brain')`
now returns 0 rows (was emitting the four ghost ids). Regression, each run fresh: `node
ignite/supervisor/reconcile.selftest.js` 54/54 OK exit 0 (identical to pre-change); `node
ignite/deploy/probe-suite.js --dir chat/probes` 35 discovered, 32 PASS, 3 QUARANTINE (suite-tracked
known reds: `chat-live-session-epipe`, `owner-ask-hold` — both pre-existing, unrelated to
`exhaustion.js`), verdict GREEN exit 0; `node ignite/runtime/internal-api/probes/probe-inspect-asks.js`
31/32, ONE pre-existing red (`M1` — a source-text mutation-needle check against
`state-store/heart/ask-record.js`'s exact function signature line-wrapping, unrelated to this file
and unrelated to any DB/file split; the needle string predates a line-wrap in that other file and was
never touched by this change). No `ignite/supervisor` dedicated probe exists for `exhaustion.js`
(none discovered under `ignite/supervisor/probes/` naming it) — none run or created; the fix is
covered by the ad-hoc scratch-dir proof above plus the regression sweep. NOT DEPLOYED: `ignite/` is
pinned to the deploy worktree at `~/.local/state/rbtv-deploy`; inert until a deploy window.

## ATTENTION
1. **The synthesized `[{}]` fallback (:227) is intentional, not the bug.** A lane-less
   `goal-disposition` record must still render ONE row while genuinely unposted — do not remove the
   fallback chasing this fix; the missing half was the posted-CHECK, not the synthesis.
2. **Never dedup this reader against the `open_asks` DB row.** `runtime/20260828-i-the-recovery-exit-s-ask-reache`
   ATTENTION 4 already forbids it: the record's file IS the source of truth for this lister, the DB
   row lives in a different store, and `dispatch.js`'s union is a plain concat that needs no dedup
   because the DB side already excludes what it should via its own `posted`/`state` filtering.
3. **A future third record shape with neither `.lanes` nor a top-level `posted_ask_id`** (some new ask
   kind) would silently re-open this exact gap — any new grouped-ask record kind must either use
   `.lanes` with per-lane `posted_ask_id`, or stamp `record.posted_ask_id` at post time, or this
   reader needs a third check added deliberately, not assumed.
- the [{}] fallback for a lane-less record is intentional — the posted CHECK was the missing half, not the synthesis
- never dedup listOpenGroupedAsks against the open_asks DB row — it is a different store and the file is this reader's own source of truth
