# 20260902-c-end-to-end-escalation-replay-p — end-to-end escalation replay probe (door to wake)

kind: creation
component: chat
date: 2026-09-02
commit: 9ea4244e562e4ffb3192fea69893627b6f2181fa
deployed: yes
pin: ignite/chat/probes/probe-esc-replay.js

## Motivation
The escalation surface (a non-interactive staff seat escalating to the owner: door → Slack channel
post → thread → `open_asks` record → digest row → shutdown clock → owner reply → seat wake) had
been fixed piecemeal across several commits, but nothing proved the WHOLE chain end to end against
real code. The 2026-08-31 incident (an escalation leaked into the owner's Slack DM instead of the
goal's channel) was exactly the kind of gap a per-file check cannot catch. The owner's own
acceptance bar for closing the escalation-surface cluster in plan `redesign-continue-1` required a
single run that observes all ten joins in the chain, plus a negative control proving the fix
actually changes behaviour relative to the pre-fix code.

## Design
`ignite/chat/probes/probe-esc-replay.js`: drives the REAL modules (`createChatBridge`,
`ask-thread.js#postAsk`, `bus-ferry.js`, `system-digest.js#renderDigest`) against a throwaway
daemon and a mock Socket-Mode Slack server (`lib.js`), rather than asserting against fixtures or
mocked modules — a fixture-level probe could pass while the real wiring between these files stayed
broken. The failure arm re-runs the identical replay against `ignite/chat/*` checked out at
`d2093ebf` (the commit before any kind/label bypass of [T2-R14] existed) inside a throwaway `git
worktree` — never a shared-tree stash — so the negative control is real code, not a hand-written
"what if" branch.

## How it works
The probe seeds a goal with a bound channel and a non-interactive staff seat, lands a
`type: escalation` row on the goal's message bus, and observes ten checkpoints in one run: the
door admits it (no `[T2-R14]` refusal), a top-level channel post appears, a threaded reply carries
the reasoning, an `open_asks` row is written (`posted:1`, `state:"open"`), the goal's open-ask
count is 1, the digest renders the row, the shutdown clock reports `waitingOnOwner:true`, the owner
DM receives ZERO posts, an owner reply in the same thread releases the ask (`reaped:true`), and the
goal's ask state flips to `closed` with the reply text persisted to
`coordination/asks/<id>.reply.txt` for the relaunched seat to read. `lib.js` gained two
backward-compatible extensions the replay needed: `startThrowawayDaemon` threads `workspaceRoot`
into `createInternalApi` (the `record-owner-ask`/`inspect-asks` intents resolve the `open_asks`
store off that value), and the mock Slack server gained `conversations.open` (the bus ferry's own
`start()` precondition), `chat.update` (the ask's §3 line rewrite), and a real monotonic `ts`
stamped onto `sentMessages` so the probe can assert the ask-id round-trip a real Slack thread
carries.

## Consequences
No `ignite/chat/*.js` runtime file is edited — only the probe and its shared test helper
(`lib.js`). Against the fixed code the replay is a clean PASS (0 failures / 25 checks) on all ten
joins. Against the pre-fix commit `d2093ebf`, the door REFUSES
(`REFUSED — this seat is not designated to reach the owner [T2-R14]`) and the old
`bus-ferry.js#deliverEscalationInFull` dumps the full escalation into the owner DM
(`dmPostCount: 1`) — reproducing the 2026-08-31 incident exactly. The probe surfaced (not fixed) a
real observability gap: `ask-thread.js#createAskThreads`'s `askDoor` is constructed with no
`logger` in `chat-bridge.js`, so its own log lines (including the `[T2-R14]` refusal) are silently
dropped; the probe worked around this by reading `bus-ferry.js`'s wired logger instead.

## Verification
`node ignite/deploy/probe-suite.js --dir chat/probes` counts and runs the probe:
`chat/probes/probe-esc-replay.js PASS exit=0 wall_ms=2002 capture=fresh`, suite discovered=30. Full
suite run at commit time: `discovered:30 attempted:30 passed:27 failed:3`; the 3 reds
(`probe-chat-live-session.js`, `probe-owner-ask-hold.js`, `probe-chat-boundary.js`) are
pre-existing and unrelated (verified independently — `probe-chat-live-session.js` fails
identically with this commit's `lib.js` delta temporarily removed; the other two reference neither
`lib.js` nor `probe-esc-replay.js`). Committed `9ea4244e`, deployed on branch `ignite/core-daemon`
(live tree `e8524c31` carries this commit) — a manual live rehearsal against a real throwaway Slack
channel is still owed (see ATTENTION 3), not yet run as of this filing.

## ATTENTION
1. `askDoor` in `chat-bridge.js` is built with no `logger` — its `[T2-R14]` refusal and "owner ask
   posted" lines are silently dropped. A future editor debugging the door should read
   `bus-ferry.js`'s logger output instead, or wire `askDoor`'s own logger, rather than assuming
   its log calls are reaching anywhere.
2. `probe-esc-replay.js` is real-module, not fixture-level — it is the one probe in this suite
   that proves the door→channel→thread→record→digest→DM→reply→wake WIRING, not just each file in
   isolation. Do not delete it as "redundant" with a narrower unit probe; no other probe covers
   the full chain.
3. The manual live rehearsal (`READY-TO-DEPLOY` block in the seat's own report,
   `1-projects/build-ignite/build/redesign-continue-1/seats/esc-replay/report.md`) against a real
   throwaway goal and Slack channel was never run — this entry covers the code-level replay only.
- askDoor built with no logger (its refusals dropped)
- this probe proves the door-to-wake WIRING, keep it
- manual live rehearsal never run
