# 20260831-c-16th-intent-drop-lane-permanen — 16th intent: drop-lane, permanently abandon a lane

kind: creation
component: gateway
date: 2026-08-31
commit: 8c1023afeaa45474f85a0f3a09a25ecc266e61ed
deployed: no
pin: ignite/chat/probes/probe-chat-recovery-dispatch.js
components: runtime,state-store,chat

## Motivation
`d-recovery-drop-stops-live-work` / `d-recovery-abandoned-is-an-ending` (owner rulings, 2026-08-31,
`redesign-continue-1`): the owner's `drop-lane` recovery reply parsed, settled the ask, and posted an
honest "did not run" — `abandonSeat` (`dl-abandoned-outcome`, f1b7a292) landed the WRITE with no wire
path to it at all, same wall every daemon effect in `chat/` hits (`probe-chat-boundary.js`: no store
handle, no child process, no sibling require).

## Design
A NEW intent, `drop-lane` — the SIXTEENTH — not a third `pause-resume` verb. `pause-resume`'s own
header keeps its verb a CLOSED two-member enum on purpose (one grammar, one NACK, for a MECHANICAL,
REVERSIBLE pair); dropping a lane is neither (it answers one specific recovery ask, and it is
permanent), and `dispatch.js`'s own rule is that new capability is ADDED BY NAME, never by widening
an existing intent's payload semantics — the same shape the 13th/14th/15th intents already took
(confirmed against this component's own `_creations.md`). Payload is `{goal, seat, ask_id?}` — no
free-text field, same "unknown key is a refusal" discipline `pause-resume` set. Authorization is a
DEDICATED `authz.js#canDropLane` (bridge-only), never `canPauseResume` reused — mirrors that file's
own repeated comment: each bridge-only intent tests `sender.kind` directly so no decision is
silently widened by another ruling's grant.

## How it works
`parse.js#parseDropLane` (SHAPE ONLY) -> `dispatch.js#handleDropLane` (re-validates, strict-schema,
`authz.canDropLane`, requires `workspaceRoot`) -> `state-store/heart/drop-lane.js#dropLane`, which
resolves the ending store from `workspaceRoot` (`openEndingStoreFor`, same file the lane gate reads
— never the daemon's private store, `pause-resume.js`'s own "THE ENDING HOME" precedent), checks the
goal is in the live-goal roster (reusing `pause-resume.js#liveGoals`, no second roster reader), and
calls `store.abandonSeat({goal, seat, anchor, abandoned_by:'owner', ask_id})` — the ONE marking path,
nothing re-implemented. STOPPING the lane's live work is NOT this intent's job: `chat-bridge.js`'s
`dropLane` port (component `chat`) does that FIRST, over the wire, through the pre-existing `inspect`
(target `ticker`) + `kill-session` intents, and only calls `drop-lane` once the stop succeeded or
found nothing live.

## Consequences
Nothing existing changed shape: `pause-resume`'s verb enum, payload and authz are untouched; `inspect`
and `kill-session` are untouched (this intent reuses them read/write, adds no field to either).
`abandonSeat`'s idempotency (dl-abandoned-outcome) is inherited unchanged — a retry after a failed
mark, or a drop on an already-abandoned lane, succeeds as a no-op through this same intent, no new
retry logic added here.

## Verification
`node ignite/runtime/internal-api/probes/probe-intent-drift.js` — PASS, 16 intents in lockstep across
gateway/parse.js INTENTS, dispatch.js INTENTS, and the dispatch() switch (was 15 before this change).
`node ignite/chat/probes/probe-chat-recovery-dispatch.js` (new probe, component `chat`) exercises this
intent end-to-end through a fake forwarder: order (inspect -> kill-session -> drop-lane), nothing-live
no-op, half-completion, retry, idempotency, and the pause-goal control. `node ignite/state-store/
ending-store.selftest.js` and `node ignite/supervisor/owed-from-endings.selftest.js` still ALL PASS
(this change calls `abandonSeat`/`liveGoals`, never edits them). Committed, not deployed
(8c1023afeaa45474f85a0f3a09a25ecc266e61ed) — `chat`/`runtime`/`state-store` are pinned to the deploy
worktree (R10).

## ATTENTION
1. THIS INTENT MARKS ONLY. It has no execution-lane / heart-store handle and does not re-check
   liveness — re-deriving that here would be a second copy of the one fact `chat-bridge.js`'s
   `dropLane` port already establishes by calling `inspect`/`kill-session` first. A future caller of
   `drop-lane` that skips the stop step will mark a lane abandoned while it is still running.
2. `ask_id` ON THE WIRE IS EVIDENCE ONLY, never verified against a real open ask — same discipline
   `abandonSeat`'s own `anchor` already carries (`writers.js`: "recorded, never verified").
3. `authz.canDropLane` is a straight copy of `canPauseResume`'s `sender.kind === 'bridge'` shape,
   deliberately NOT unified with it — widening a shared predicate would silently loosen a decision
   the pause-resume ruling never touched, the same reason every sibling `canXxx` in `authz.js` gives
   for staying separate.
4. `dispatch.js` and `authz.js` are NOT named in this seat's own custody wall (`redesign-continue-1/
   seats/dl-teardown-wire/seat.md`'s R2 list only names `chat-bridge.js`/`recovery-thread.js`/
   `gateway/parse.js`/`pause-resume.js`) — they were touched anyway because no existing intent could
   reach `abandonSeat` without a dispatch.js case, and the wall list appears to have been an
   oversight rather than a deliberate exclusion. Disclosed in the seat's own report.
- drop-lane marks only — it has no liveness handle and trusts the caller stopped live work first
