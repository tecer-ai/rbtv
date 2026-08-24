# 20260824-c-durable-slack-outbox — durable Slack outbox

kind: creation
component: bridges
date: 2026-08-24
commit: 99ba0fc8,4c8f1a57
deployed: no
pin: ignite/bridges/chat/probes/probe-chat-outbox.js

## Motivation
Slack delivery is the last rung and can fail silently [C-17]. A post that Slack never acked used to vanish, and a delivery failure could be read as a seat strike. The redesign pins a durable outbox: every post starts `pending-delivery` and flips `delivered` only on Slack's own ack.

## Design
A cohesive `outbox.js` in `bridges/chat/` (map home `ignite/chat/` is still absent; same landing grammar used). Persistence is a JSON file at `.rbtv/runtime/ignite/outbox.json` — the state-store runtime home — written tmp+rename. `node:sqlite` / `heart-store` were rejected because `probe-chat-boundary` forbids a store driver in this relocatable subtree. Record fields and the two-state machine are exactly spec-owner-io §7.1. A retry of the same pending key (or an explicit `outbox_id`) increments `attempt_count` and never mints a second record. Injected `send` is the transport; the module never talks to Slack itself.

## How it works
`createOutbox({ storePath, send })` returns `post` / `query` / `get`. `post` writes `pending-delivery` first, calls `send`, and on ack sets `delivered` + `slack_ts` + `delivered_at`; on `ok:false` or a thrown network error it keeps `pending-delivery` and records `last_error`. `query` filters by `state` / `kind` / `channel_id` / `goal_id` / `ask_id` and returns newest-first. `chat-bridge.js` builds one outbox per bridge and posts every former `transport.sendToOwner` site through it (`kind: notification` for existing traffic). `bus-ferry.js` does the same; the escalation last-ditch DM is `kind: alarm`. `reply-leg.js` has no send of its own — it already posts via `deliverToOwner`.

## Consequences
Existing call sites still see `{ delivered, ts, error }`. No strike increment exists on the failure path. Later slack seats (ask-release, approval-pause, glance) must post through this API with their own `kind` — do not add a third state or a parallel send. `goal-channel-cli.js` still posts directly (operator CLI, not a bridge post path). `probe-chat-live-session` failed in this sitting with `E_LAUNCH_REFUSED unresolved …/scratch` from the parallel envelope-launch seat; it does not go through the outbox.

## Verification
`probe-chat-outbox.js` 16/16 PASS (ok:false retain, retry same id, ack flip, network error, every §7.2 filter, newest-first, get-by-id, no strike). `node --check` on `outbox.js`, `chat-bridge.js`, `bus-ferry.js` exit 0. Chat probe-suite 21/22 PASS; the one FAIL is live-session launch-refuse, not an outbox path. Not deployed (`deployed: no`).

## ATTENTION
- A Slack send that bypasses `outbox.post` is a silent loss again: the record is the only proof Slack was asked. `sendToOwner` on the transport is the implementation the outbox calls, not a second door for product posts.
- Retries must reuse the pending record (same kind/channel/thread/payload/goal/ask, or `outbox_id`). Minting a new row per attempt makes "did Slack get it?" unanswerable.
- Delivery failure must never increment a seat strike. The outbox has no strike field; do not add one at a caller to "explain" a failed post.
- A Slack send that bypasses outbox.post is a silent loss again: the record is the only proof Slack was asked. sendToOwner on the transport is the implementation the outbox calls, not a second door for product posts.
- Retries must reuse the pending record (same kind/channel/thread/payload/goal/ask, or outbox_id). Minting a new row per attempt makes did-Slack-get-it unanswerable.
- Delivery failure must never increment a seat strike. The outbox has no strike field; do not add one at a caller to explain a failed post.
