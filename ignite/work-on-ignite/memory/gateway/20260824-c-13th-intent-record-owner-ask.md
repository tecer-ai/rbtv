# 20260824-c-13th-intent-record-owner-ask — 13th intent: record-owner-ask

kind: creation
component: gateway
date: 2026-08-24
commit: f9da72b7
deployed: no
pin: bridges/chat/probes/probe-chat-boundary.js
components: bridges,server,team-kit

## Motivation
`spec-state-store` §3 makes the daemon-owned `open_asks` table in `heart.db` the ONE record of an
owner ask, so a seat's wait on the owner is DERIVED at read (§2.1: an ask that is `posted` and still
`open`) instead of stored in a per-goal JSON file a second component owns. The bridge could not
perform that migration itself, and the wall it hit was real on both sides: `bridges/chat` runs as a
SEPARATE PROCESS reaching the daemon only over the gateway, `probes/probe-chat-boundary.js` forbids
a store handle / child process / sibling require in that subtree, and a write from that process
would be a second WRITER PROCESS into `heart.db` — which §7's "one writer path per row" forbids for
exactly the reason the wall exists. Both rules were right; the spec row had no legal implementation.
An earlier attempt to migrate `ask-store.js` directly onto the store was caught by the boundary
probe and reverted whole (16fdc15f), and the gap was surfaced for a ruling rather than bent.

## Design
The owner ruled option (a) on 2026-08-24 (`redesign-implementation/decisions.md`): ask-writes get
their own gateway intent, the bridge sends the record through it, and a daemon-side writer stamps
the table. `record-owner-ask` is that intent — the THIRTEENTH — and it cites its ruling the way the
twelfth (`record-bus-answer`, ruling 2026-08-11) cites its own, because a new intent widens the
daemon's authenticated surface and is therefore an owner act, not an implementation detail.

ONE intent with two acts (`open` / `reap`) rather than two intents: they are one fact's lifecycle,
authorized identically and refused identically. Their FIELD SETS differ and are validated per-act
rather than unioned — `open` carries the ask's words and its label, `reap` carries neither, because
resolution is not a place to restate the question and a corpus accepted on a reap would let the
reaping call rewrite the body the digest renders. Per-act sets mean a mistake is a refusal instead
of a silently ignored key.

Two things the payload deliberately does NOT have. There is no `ask_id` field: `ask_id` IS the Slack
thread [T5-R7], so a caller cannot point an open or a reap at an ask its own conversation does not
own. And there is no `text` column anywhere in the store: §3 defines `evidence_pointer` as the
thread permalink or an on-disk copy, so the daemon writes one file per ask under the goal's
`coordination/asks/` and stores its path. Deleting the body would have made the owed-answers digest
and the boot-prompt re-inject useless; adding a column would have put prose in a store the spec
keeps free of it.

## How it works
The bridge's `ask-store.js` is now a SENDER and nothing else — `createAskRecord({forwarder, logger})`
returning `openAsk` / `reapAsk`, holding no fs and no store handle. `forward-path.js#onChatMessage`
calls `openAsk` where it used to write the file (goal route only, and only after the forward landed,
which is what lets the daemon mark the row `posted` at insert — §2.1 reads that flag, so an unposted
row would be an ask nobody is waiting on). `chat-bridge.js#deliverToOwner` calls `reapAsk` with the
thread the reply landed in.

`gateway/parse.js` registers the intent and checks SHAPE only. `internal-api/dispatch.js`'s
`handleRecordOwnerAsk` runs the same ladder every sibling uses — strict schema, shape, authorization,
act — and `authz.canRecordOwnerAsk` is BRIDGE-ONLY. `server/heart/ask-record.js` performs the write:
`insertAsk` then `postAsk` on open, `reapAndRelaunch` on reap (which reaps the row and signals the
bound seat's relaunch in ONE transaction, §2.8 — no orphan ask, no twin relaunch). The three names
are re-checked THERE against `bus-ferry#isSafeName` and the goal folder is checked on disk — the
questions the gateway holds no handle for and must not grow one.

A second owner message in a thread that already carries an open ask refreshes the body and leaves
the ROW alone, so a reopened conversation cannot resurrect an ask the owner already answered.

## Consequences
`owner-asks.json` is gone from live code; the four surviving greps are prose saying so.
`launch.py#unanswered_ask_block` and `owed-answers.py#collect_unanswered_asks` now read the store
through `ending_store.list_open_asks` — a peer session's helper, reused rather than duplicated, so
the digest and the scheduler cannot disagree about which asks are open. `engine/probes/
probe-owner-ask-hold.js` went GREEN with this landing: it was red because the derived §2.1 predicate
had no writer feeding it.

Two bridge probe fixtures broke and were fixed at the cause: their fake forwarders logged EVERY
forward into an array named for job enqueues, then asserted its length as a count of jobs — true
only while `enqueue-job` was the sole intent those routes reached. Split into a job log and a call
log so each new intent cannot shift counts that are supposed to measure routing.

⚠ While writing this I destroyed a peer session's UNCOMMITTED addition of `list_open_asks` to
`ending_store.py` with a `git checkout <path>` (which restores from the INDEX). Caught within a
minute by a live failure and restored verbatim from a diff captured moments earlier; the peer was
notified. See ATTENTION.

## Verification
`probe-chat-boundary` PASS — the bridge subtree holds no store handle, no child process and no
sibling require. Chunked suite re-run with `RBTV_IGNITE_SRC` on the worktree: bridges+gateway+cli+
internal-api 50/50 GREEN; server/heart+server+seat-identity+lease+engine 41/45 (the 4 reds are the
engine §5 rows a peer session is migrating); spawn+ticker 60/60 GREEN; team-kit+capabilities 34/40
(2 baseline exceptions, 1 cross-tree INOPERATIVE, 3 kit reds unchanged and independently diagnosed).
Standalone: `reconcile.selftest` OK, `ending-store.selftest` ALL PASS, `probe-suite --selftest` 26/26,
`probe-self-isolate` ok, `owed-answers --selfcheck` OK. An end-to-end exercise of the writer proved
open / same-thread-idempotent / §2.1 true / reap / §2.1 false / reap-idempotent, plus four refusals
(path traversal, absent goal, bad label, ask bound to a different pair). Not deployed — worktree
branch `ignite/core-redesign`.

## ATTENTION
1. `git checkout -- <path>` restores from the INDEX and silently destroys a CONCURRENT session's uncommitted work in a shared worktree. It is not a safe way to drop your own hunk when others are editing the same file. Re-apply your own delta by hand instead, and commit early so peers cannot lose yours.
2. A new gateway intent is an OWNER ACT, not an implementation detail — both the twelfth and this thirteenth cite a dated ruling in `parse.js` and `dispatch.js`. An intent added without one widens the daemon's authenticated surface on an agent's judgement.
3. A probe's fake forwarder that logs EVERY call into an array named for one intent will silently mis-count the moment a second intent rides the same forwarder — and it fails as a ROUTING regression, which is the wrong place to look. Name call logs and job logs differently.
4. `ask_id` IS the Slack thread. There is no allocator and no per-seat queue, so "settle the oldest open ask" has no successor — a reap without a thread is refused, deliberately, because guessing is how a reply to one question closes another.
5. Backticks inside a double-quoted `git commit -m` argument are shell-substituted. One word was eaten out of this change's commit message prose; the code comment carries the full statement.
- git checkout -- <path> restores from the INDEX and destroys a concurrent session's uncommitted work in a shared worktree

2026-08-31 addendum: superseded on the store location — since 361a56f2, openAsk/reapAsk/listOpenAsks resolve the workspace ending store (`<workspace>/.rbtv/runtime/ignite/heart.db`); the lane-store `open_asks` copy was drained (rows copied over, table emptied) on 2026-08-31. Read the store location from `ask-record.js`, not from this note.
