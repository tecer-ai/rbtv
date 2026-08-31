# 20260831-c-owner-dm-escalation-legs-retir — owner-DM escalation legs retired, system-channel alarm

kind: change
component: chat
date: 2026-08-31
commit: b9c014f3
deployed: no
pin: ignite/chat/probes/probe-chat-bus-ferry.js

## Motivation
Owner ruling `d-escalation-surface` (2026-08-31 interview, register `G-goal-master-0831-1839`)
part 4: the owner's DM carries NO goal traffic at all, ever — not an escalation, not an alarm, not
a pointer. `bus-ferry.js` held two owner-DM legs that violated this: `deliverEscalationInFull`
(the content-bearing dump, reached from a [T2-R14]-terminal-refusal branch and the attempt cap)
and a content-free missing-channel notice at `NOTICE_AT_ATTEMPT`. Part 6: an unreachable goal
channel is a system fault, retried without a cap, raised as a daemon-level alarm in the system
channel after a short window — nothing ever abandoned.

## Design
Both DM legs are deleted and unified into ONE mechanism, `postUnreachableChannelAlarm`, firing to
a newly-injected `systemChannelId` (mirroring `dmChannel`/`postGoalChannel` — the ferry still
holds no channel knowledge of its own). It fires at the SAME `n === NOTICE_AT_ATTEMPT` exact-match
guard the old DM notice used (so it is naturally once-per-row, no new persisted state), broadened
from `error === 'no-channel'` to `no-channel || resolve-failed` (the old notice left a
`resolve-failed` row silently unreported past the threshold — a real gap, closed here). The
[T2-R14]-terminal-refusal branch (`deliverEscalationInFull`'s first caller) is provably DEAD in
production since `esc-door-split`'s fix (`kind: 'escalation'` bypasses [T2-R14] at the ask door
unconditionally, so `seat-not-interact` can never combine with `isEscalation`) — deleted along
with the `terminalRefusal` variable and its disposal block, not merely left commented.

The uncapped-retry half is SCOPED, not blanket: only escalations whose persistent error is
`no-channel`/`resolve-failed` skip the `maxAttempts` cap. Traced the transport path first —
`goalChannelFor` (chat-bridge.js) short-circuits BEFORE any `outbox.post`/transport call in both
`postOwnerAsk` and `routeToAgentThread` when the channel does not resolve — so retrying that
specific failure class forever is provably safe (no message can ever have landed to duplicate).
Every OTHER persistent failure on an escalation (channel resolves, the post itself keeps failing)
keeps the ORDINARY cap: that path DOES reach `outbox.post`, whose dedup is an exact
`(kind, channel, thread_ts, goal_id, ask_id, payload)` match in `pending-delivery` state — not
proof against a transport call Slack accepted but the process read as failed.
`dup-idempotency`'s per-message key does not cover ferry/ask-thread posts (its own memory entry
says so; re-verified here by reading both call sites), so uncapping that residual is NOT done.

## How it works
`createBusFerry({ systemChannelId = null, ... })`, injected by `chat-bridge.js` from
`config.systemChannelId` (`RBTV_SYSTEM_CHANNEL_ID`, already resolved by `config.js` and already
read by `glance.js`). `postUnreachableChannelAlarm({ goalId, seat, reason, isEscalation, key,
msgId })` posts via the existing `postOwner`/`outbox.post` path (`kind: 'alarm'`, an existing
outbox kind — no schema change), naming the goal and the blocked seat, and rendering `reason ===
'resolve-failed'` as "Slack did not answer... NOT evidence the channel is missing" vs `no-channel`
as "the channel does not exist in the workspace" — the exact `goal-channel-map.js#resolveChannel`
distinction. The retry-ladder's `if (n >= maxAttempts)` gains one guard:
`!(isEscalation && channelUnreachable)`, so that combination alone falls through to the ordinary
"will retry next pass" tail forever, reusing the existing `sizes.delete(key)`/`stuckAt` bookkeeping
— no new persistence, per the seat's own constraint ("behind the existing `jumped` persistence and
the outbox key that exists today").

Also wired in the same commit (owed by `esc-one-at-a-time`'s own memory entry, sharing this
custody row): `listOpenAsks: () => askRecord.listOpenAsks()` in `chat-bridge.js`'s
`createBusFerry` call — without it, the one-open-escalation-per-goal gate that seat built was a
documented no-op in production.

## Consequences
Deleted: `deliverEscalationInFull` (both callers), the `terminalRefusal` variable and its dead
disposal block, the owner-DM missing-channel notice. `README.md`/`component.md`'s "the owner's DM
is the escalation/alarm surface" statements corrected (the DM remains what the owner opens
himself). `probe-chat-bus-ferry.js`'s W8-C/W8-D rewritten for the new surface (fires-once,
never-abandoned, both `no-channel`/`resolve-failed` variants, using a REAL `routeToAgentThread`
via a direct `buildBridge` call — the file's usual `makeBridge` helper force-nulls it, which would
have hidden the very propagation this fix depends on). `probe-chat-agent-thread.js` test 5/5b
broke on this change (asserted the old DM notice for an ORDINARY, non-escalation row — the alarm
applies to any row past the threshold, not escalations only) — fixed in the same commit: its
fixture now wires `systemChannelId`, and 5b's assertion is IMPROVED (previously a `resolve-failed`
row got no owner notification at all past the threshold; now it gets the alarm too).

## Verification
Red-first: a throwaway script (`buildBridge` + a real channel-capable mock Slack whose target
goal's channel is never created) against the pre-fix commit shows the missing-channel DM notice at
attempt 3 and the `deliverEscalationInFull` dump at attempt 20, both landing in the owner DM.
Against the fix: zero DM posts across 20 ticks, exactly one system-channel alarm, cursor never
advances (row still on the bus). `resolve-failed` variant (an unwired `listChannels` failure)
renders the distinct text. `node ignite/chat/probes/probe-chat-bus-ferry.js` — PASS, 75 checks.
`node ignite/chat/probes/probe-chat-agent-thread.js` — PASS, 83 checks (was RED on this change
before the fixture/assertion update, confirmed by diffing against the pre-fix worktree).
`node ignite/deploy/probe-suite.js --dir chat/probes` — 26/29 PASS; the 3 failures
(`probe-chat-boundary`, `probe-chat-live-session`, `probe-owner-ask-hold`) reproduce identically
on the pre-fix tree — pre-existing, unrelated. NOT DEPLOYED: `rbtv-chat-bridge` must restart, and
`RBTV_SYSTEM_CHANNEL_ID` must be set for the alarm to have a destination (it logs a warning and no-ops otherwise, never crashing).

## ATTENTION
- The escalation retry-forever residual is NARROW, not blanket: only `no-channel`/`resolve-failed`
  bypass the cap. A future change to the ask-thread/`outbox.post` call site that starts a transport
  call BEFORE channel resolution (unlikely, but would invalidate the safety proof) must re-derive
  this guard, not assume it still holds.
- The `terminalRefusal`/`seat-not-interact && isEscalation` branch was deleted as PROVABLY DEAD,
  not merely unused — the proof rests on `ask-thread.js#postAsk`'s `kind !== 'escalation' && kind
  !== 'recovery' && !seatIsInteractive(...)` gate (esc-door-split's fix). If that gate is ever
  rewritten to admit `kind: 'escalation'` conditionally, this deletion's premise breaks silently.
- `systemChannelId` unwired (any embedder that wires nothing, most probes) makes the alarm a
  logged no-op — never a wrong surface, never a crash. Do not add a DM fallback "just in case" if
  you ever see this warning live; that is exactly the retired design.
- the escalation retry-forever residual is narrow (no-channel/resolve-failed only), not blanket
- the deleted terminalRefusal branch's dead-code proof rests on ask-thread.js's kind:escalation bypass — re-verify if that gate changes
