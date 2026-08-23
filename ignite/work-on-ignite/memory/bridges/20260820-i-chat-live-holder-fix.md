# 20260820-i-chat-live-holder-fix — chat-live-holder-fix

kind: issue
component: bridges
date: 2026-08-20
commit: 63413504,22301f66
deployed: yes
pin: NONE
seeded: true

## Observed
Two same-day owner-visible chat-bridge failures, both already claimed delivered.

At 2026-08-20 01:20:35Z on `meet-transcript-summarizer` (Slack C0BPXLYN0N5), a top-level owner post found a live sitting at the goal-master seat (exec 30026, status running). `createForwardPath`'s live-holder branch logged "writing the bus and nudging", got `no-warm-session` back from `nudgeLiveSitting`, logged "bus write still stands", and returned `forwarded:true`. A whole-goal-folder walk found no trace of the owner's text. Closed as the roles sitting-5 loose end at 01:40Z (`redesign-plan/loose-ends.md`).

At ~03:50Z the same day the owner reported both goal channels had already received their real replies (execs 30193 at 03:46:54Z and 30188 at 03:47:04Z) and then still got "⏳ still working — 5 minutes so far" about three minutes later. That path is `createReplyLeg`'s delivery-success branch.

JS under `ignite/bridges/` is inert until `rbtv ignite daemon deploy`; the live bridge was still running the pre-fix tree when both symptoms were measured.

## Mechanism
The live-holder branch treated two independent non-deliveries as success. `recordBusAnswer` is `kind:'agent'` only — a top-level post in a GOAL channel is the owner initiating, and recording an `answer` would falsely clear goal-master's open ask — so on the goal route it returned `null` before writing. `nudgeLiveSitting` only feeds a WARM session; goal traffic rides the headless model, so `no-warm-session` is its ordinary answer. Neither path wrote, queued, or mapped a thread. The function still returned `forwarded:true` and the two log lines claimed the bus write stood. Without `threadMap.create` plus `bindSessionExecId`, the reply leg also had no `exec-<exec_id>` address to ferry an answer back on.

Independently, the delivery-success branch reset `p.armedAt` / `p.revives` / `p.compacted` / `p.disarmedAt` but never touched `p.slowNoticed`. The P3 slow-notice rung fires at `turnStartedAt + 300s` gated only by that flag being false, so an already-answered turn whose clock crossed five minutes still posted the hourglass.

## Attempts
First attempt held — checked: `missed_trials_source` empty; no RCA in `seeding/map.csv` (sources are the two commit messages only); `git log --before=2026-08-20T01:38:04 -- ignite/bridges/chat/forward-path.js` (30 commits since 2026-07-18) for a prior live-holder false-success fix — closest are `ce587d24` (2026-08-17, hung-seat auto-recovery / lossless queueing) and `bd59e6c7` (2026-08-17, seat-busy FIFO deadlock), which built the queue the fall-through now uses but did not touch the live-holder success claim; `91e287ca` (2026-08-20 01:17:41Z, 21 minutes earlier) is a sibling `forward-path.js` fix on the exec-id-unknown follow-up path, not this branch. For the hourglass: `git log --before=2026-08-20T03:58:19 -- ignite/bridges/chat/reply-leg.js` — closest is `7d51cadb` (2026-08-10, every disarm posts a dead-air notice), which never spent `slowNoticed` on the delivery-success branch. Watcher sitting 4 / `61ce15d9` the same morning stopped reconcile from manufacturing phantom live-holders; that reduced how often this branch was hit, it did not fix the branch.

## Fix
`63413504` (2026-08-20 01:38:04Z) made the nudge an optimisation with two honest outcomes. After `findLiveHolder`, the branch now calls `nudgeLiveSitting` then `recordBusAnswer` and returns `forwarded:true` only on proof: a bus row with `recorded === true` (agent route — the seat reads its inbox at the next checkin, no map needed) or `nudge.nudged` (live turn consumed the text — then `threadMap.create` + `bindSessionExecId` so the reply leg has the chain-stable `exec-<exec_id>` address). Neither proof → fall through to the ordinary `session-create` whose `on_seat_busy: 'queue'` holds the row until the seat frees — the path that delivered on the sibling goal the same minute. The two log lines were rewritten to say NOTHING was delivered. Recording an answer on the goal route was rejected because it would falsely clear goal-master's open ask. Always skipping the nudge was rejected because a FED warm session is the cheaper correct path when it works.

`22301f66` (2026-08-20 03:58:19Z) set `p.slowNoticed = true` in the delivery-success branch only. Broader rework of the notice budget was rejected: `arm()` already re-opens the flag on the next real owner turn. No D-id or E-id rules this pair; D28 (owner, 03:15Z) postdates `63413504` and is a downstream boundary, not the cause.

## Consequences
The live-holder branch no longer short-circuits; a NOT-FED busy seat now also takes the queued session-create, so a later summon on the same message would double-deliver. D28 Fix 2 (owner, 2026-08-20 03:15Z) therefore keeps the note path for live-holder cases — "no double-delivery — the roles sitting-5 arm7 lesson". `d491c8f0` (03:36:28Z) implements that: `forwardFollowUp` summons on a failed tail only when "no live sitting holds the seat (the live-holder branch owns that case — 63413504 / arm7)". The sibling entry `20260820-i-chat-resume-crash-fix.md` cites this file for that boundary.

Same-day later edits (`0a3a14d2` D57/D75 owner-ask ferry; `607014d4` D89 Q4 ask-list widen; `01f61350` stale-comment) touch `forward-path.js` / `reply-leg.js` but do not rewrite the proof-of-delivery checks or the `p.slowNoticed = true` line. No revert of either commit through 2026-08-22. The hourglass fix does not silence unanswered turns: control arm u3 in `probe-chat-reply-leg.js` still requires the notice.

## Verification
`probe-chat-live-holder.js` (new in `63413504`) drives real `createForwardPath` with a stub forwarder: arm 1, nudge refused → session-create enqueued and thread mapped; arm 2, nudge accepted → no enqueue, thread mapped and bound to holder exec 30026; arm 3 mutates a copy to cut the fall-through and requires arm 1 to go red.

`probe-chat-reply-leg.js` arm t3 (`22301f66`) stale-clocks an already-delivered turn 6 minutes past the P3 threshold and asserts no additional notice; control u3 (unanswered turn still gets the notice) stayed green.

Roles sitting 5 closed the live-holder loose end at 01:40Z with `63413504` deployed and the bridge restarted. `22301f66` landed at 03:58:19Z the same day; header `deployed: yes`. The prior seeded body dated a later tree snapshot (rbtv HEAD `ac1c08d8`, 2026-08-21 18:14:37Z); pin remains NONE.

## ATTENTION
- The live-holder branch in `forward-path.js` must not return `forwarded:true` without one of the two proofs (a `recordBusAnswer` row with `recorded === true` on the agent route, or `nudge.nudged` after a warm feed). Dropping either check returns the silent loss: both the bus write and the nudge can honestly fail, and the old logs will not tell you.
- A FED nudge is not enough by itself: the same branch must `threadMap.create` and `bindSessionExecId` to the holder's exec-id, or the reply leg has no `exec-<exec_id>` address and the owner still gets no answer.
- Any new delivery/success branch in `reply-leg.js` must set `p.slowNoticed = true`. A delivered reply does not spend that budget by itself; only `arm()` resets it, and only on the next real owner turn. Forgetting the flag re-posts "⏳ still working" after the answer has landed.
- `forwardFollowUp`'s summon-on-failed-tail (D28 / `d491c8f0`) is deliberately skipped when a live sitting holds the seat. Widening that summon onto the live-holder case double-delivers one owner message (roles sitting-5 arm7).
