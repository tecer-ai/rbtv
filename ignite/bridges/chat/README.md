# ignite chat bridge — outbound-only thin sender

The owner interacts with the running ignite system from anywhere via chat. The
bridge receives messages over an **outbound-only** connection (no public ingress),
allowlists the chat-user identity, and forwards validated requests to the gateway
as an **ordinary authenticated sender** — never a privileged path.

Design authority: `…/phase-7-plan/specs/chat-bridge-spec.md` (**ruled**, D105). Realizes
DEC-3's chat clause. This module is the task-7.2 build.

## What it is (and is not)

- One authenticated gateway **sender** — a `kind: bridge` row in the daemon's
  senders registry; its per-sender token is the primary gate (D89). It holds a
  bridge token and the gateway client, and **NOTHING else**: no queue handle, no
  spawn path, no store connection (chat-bridge-spec.md Behavior #5).
- **Outbound-only.** It opens ONLY outbound connections — a WebSocket to Slack
  (Socket Mode) and outbound HTTP to the gateway (loopback/tailnet). It adds **no
  inbound public listener**; the daemon stays loopback/tailnet-bound (Behavior #4).
- The chat-user **allowlist + DM pairing** is the bridge's OWN admission gate
  (D77(B)). It decides which chat principals may drive the bridge; it mints no
  daemon-side principal and does not repair the deliberately-weak v1 authz (D65(B)).

## Transport — Slack Socket Mode (v1, ruled D105)

Slack **Socket Mode**: `apps.connections.open` (app-level token) returns a `wss://`
URL; the bridge opens an outbound WebSocket to it and receives events, acking each.
Owner output is delivered outbound via `chat.postMessage` (bot token). Telegram
(`getUpdates` long-poll) is additive later — a second transport behind the same
`onMessage`/`sendToOwner` shape (DEC-3 "and/or"); not built here.

Turn-boundary ceiling (notes §7b): chat rides the headless model — turn-boundary
dialogue only, no mid-turn interrupt / live TUI (that is the ttyd surface, Batch 6).

### Slack event dedupe (at-least-once redelivery guard, D108(C))

Slack Socket Mode delivers events AT-LEAST-ONCE — after a reconnect or slow ack,
the same message event is re-pushed with a NEW envelope id. The bridge drops
redelivered duplicates BEFORE the forward path (allowlist/thread-map/forward),
so one chat message can never enqueue two jobs.

The dedupe key is the message EVENT's identity: `client_msg_id` when present,
else `(channel, event_ts)`. The envelope id is never the key (redelivery mints
a new envelope for the same event). The cache is a bounded in-memory insertion-
ordered `Map` (max ~500 entries, oldest evicted) — consistent with the bridge's
in-memory-by-design architecture (sessions-are-cattle; no persistence).

## The forward contract (D104/D105) — `forward-path.js`

One chat thread = one conversation. A message from an admitted principal becomes
exactly one gateway call, always `enqueue-job` (the bridge adds no new intent):

| Case | Forward |
|------|---------|
| **First** message in a new chat thread | `enqueue-job` naming a session-creating **launch-agent** function + a named launch profile (DEC-1 R3). The bridge never spawns; the ticker's Dispatch phase does. |
| **Follow-up** in a mapped thread | `enqueue-job` carrying a **`send-message`** action-type job addressed to the mapped turn-chain's thread (`exec-<first exec_id>`). Reply type `answer` on a pending `ask`, else `note` (closed CMP-8 vocabulary). |

**NEVER `send-to-session`** (D104): that leg is `session_mode: headed` + live only
(the pty keystroke rung). Chat rides the headless turn-boundary ceiling. There is
no send-to-session code path in this module, by construction.

## The reply leg (D110) — `reply-leg.js`

The outbound production driver that closes Behavior #3. On every FORWARDED turn the
bridge arms a per-conversation PENDING-REPLY state; a single driver loop (default
~3 s) then, over the `inspect` read surface only:

1. **captures** the turn's `execId` from `inspect ticker` → `recent_ticks[].actions[]`
   spawn rows matching the conversation's queue id (a conversation sees one exec per
   turn — every not-yet-delivered spawn is a turn to deliver);
2. **waits for turn-end** by polling `inspect status {execId}` until `live === false`
   — NEVER on `status === 'done'` (the daemon's crash sweep mislabels clean detached
   successes `failed`, so the live flag is the only trustworthy signal);
3. **extracts** the reply from `inspect logs {execId}`, paging the bounded surface
   to the log's END (`nextOffset`/`eof`) — the LAST stream-json
   `{ type:'result', result }` line; a log read to eof with no parseable result
   line → a fixed fallback (`⚠ agent run ended without a parseable reply`), the
   raw log is NEVER posted;
4. **delivers** via `deliverToOwner` (markAsk false — plain agent output, D105 note;
   ask-detection is out of scope for v1), marking the exec delivered ONLY on a
   confirmed delivery, so it is never posted twice — and so a TRANSIENT logs/
   transport/Slack failure never burns the reply: the exec is retried next pass,
   bounded per exec; at the attempt cap it is retired undelivered with a warn AND a
   fixed give-up notice to the owner (D111 part 2 — honest non-delivery, never a
   silent success or a fallback posted over a blip).

In-memory v1 (D110 floor): a restart forgets pending state, matching the thread-map.
A pending conversation whose spawn never appears within a bounded window, or whose
status polling errors persistently, is disarmed with a warn (no crash, no unbounded
retry, no unbounded state growth).

Thread ↔ turn-chain mapping (`thread-map.js`) keys the chain by its chain-stable
thread id `exec-<first exec_id>` (D24 Q3a). The bridge navigates
`job-id → exec-id → chain-thread id` via the gateway `inspect` intent (D69) — it
never conflates id spaces and never forwards a follow-up with an unresolved thread.
The `exec-id → chain-thread` step has **two settled resolutions** (D111): the
authoritative `live_sessions[].thread` when the chain's session is currently live,
else the chain-stable **convention** `exec-<first exec_id>` derived from the KNOWN
first exec-id when the session is not live — the turn-boundary reality, since short
v1 turns end between the owner's messages (a running chain has no live session
between turns). Deriving by that fixed convention is a resolution, not a guess;
`sessionExecId` is **first-wins immutable** so the derived id always names the
chain's real thread. Only when NO first exec-id can be established at all
(`exec-id-unknown` — nothing dispatched, or the spawn aged out of the window) is
resolution honestly deferred and the follow-up declined.

### Honest owner notices (D111 part 2)

The bridge never drops an owner-visible reply path in **silence** on a MAPPED
conversation. When a follow-up cannot reach the running work — chain unresolved
(`exec-id-unknown`) or the gateway refused the enqueue — the forward path posts a
fixed decline notice (`⚠ couldn't route your reply to the running work — please try
again shortly`) via `deliverToOwner`. When the reply leg retires an exec undelivered
at its attempt cap, it posts a fixed give-up notice (`⚠ the agent finished but its
reply couldn't be delivered`). Notices carry NO internals, are **best-effort** (a
failed post is logged and dropped, never retried into a loop), and are posted ONLY
for mapped conversations — never on an allowlist/pairing refusal (unpaired users get
nothing, by security posture).

## Files

| File | Role |
|------|------|
| `index.js` | process entry + `buildBridge()` composition |
| `chat-bridge.js` | wires transport + allowlist + thread-map + forward-path + reply-leg; inbound + outbound |
| `forward-path.js` | the D104/D105 forward contract (session-create / follow-up / reply type) |
| `reply-leg.js` | the D110 outbound driver: worker turn finishes → fetch its answer via `inspect` → `deliverToOwner` into the Slack thread |
| `slack-socket-mode.js` | Slack Socket Mode transport (outbound WS + chat.postMessage) |
| `allowlist.js` | chat-user allowlist + DM pairing (admission control) |
| `thread-map.js` | chat-thread ↔ turn-chain map + two-tier chain-thread resolution (live_sessions, else the `exec-<first exec_id>` convention derivation; first-wins immutable exec-id) |
| `gateway-forwarder.js` | outbound HTTP client to the gateway (self-contained; no sibling import) |
| `config.js` | config + secret resolution (secrets from env only) |
| `probes/` | the spec's Test Plan probes (see below) |

Relocatable subtree (ignite/CLAUDE.md rule 4): the runtime source imports NO sibling
module (`server/`, `gateway/`, `cli/`) — it reaches the daemon only over the gateway
HTTP interface. `probes/` is test harness and MAY reach siblings.

## Configuration (secrets from the environment only — D27)

| Env var | Meaning |
|---------|---------|
| `IGNITE_GATEWAY_ADDR` | daemon gateway address (host[:port]) |
| `IGNITE_BRIDGE_TOKEN` | **secret** — this bridge's `kind: bridge` sender token |
| `SLACK_APP_TOKEN` | **secret** — Socket Mode app-level token (`xapp-…`) |
| `SLACK_BOT_TOKEN` | **secret** — bot token for `chat.postMessage` (`xoxb-…`) |
| `SLACK_API_BASE` | Slack Web API base override (tests point it at a mock) |
| `IGNITE_CHAT_BRIDGE_CONFIG` | path to the non-secret JSON config (allowlist, job/profile names) |

Non-secret JSON config shape: `{ gateway_addr, session_job_id, session_profile,
send_message_job_id, workdir, allowlist: [chat-user-ids] }`.

## Validation (STAGED — ADX-33(2) / D106)

The spec's fidelity floor (a REAL Slack round-trip) needs an owner-provisioned Slack
app that does not exist at build time. Build-time validation exercises the spec's
probes against a **local stand-in**: a mock Socket-Mode server + a **throwaway**
in-process daemon (heart store + internal API + gateway) on an ephemeral loopback
port — never the live daemon, never port 7431. The real-transport round-trip
(Test Plan rows 1/2/4/6 at the real floor) runs at **p7-checkpoint** with the owner.

Run the probes: `node probes/probe-chat-<name>.js` (evidence → `probe-chat-<name>.out`).

| Probe | Test Plan | Proves |
|-------|-----------|--------|
| `probe-chat-enqueue` | #1 | allowlisted user's message → validated job reaches gateway → queue (full mock-WS round-trip); redelivery legs (D108(C)): same event re-pushed under a new envelope is dropped — SAME-channel follow-up on a live chain (no double `send-message`), the `(channel, event_ts)` fallback key when `client_msg_id` is absent, and a negative control proving two DISTINCT messages both still enqueue |
| `probe-chat-allowlist` | #2 | non-allowlisted user refused, nothing enqueued; admitted user does enqueue |
| `probe-chat-outbound` | #3 | starting the bridge adds NO new inbound listener (`ss -tlnp` delta) |
| `probe-chat-outbound-msg` | #4 | owner output delivered outbound via `chat.postMessage` |
| `probe-chat-reply-leg` | #4 | the D110 driver, armed through the REAL inbound wiring (Slack event → forward path → arm): spawn captured from `recent_ticks` → `live:false` → LAST stream-json result line extracted (multi-page logs paged to the end) → posted to the conversation's channel+thread, text-EQUAL to the result string; no-result log delivers the fixed fallback (never the raw log); no exec delivered twice; a follow-up turn (new exec, same queue) delivers a second reply; a transient logs failure or refused post is retried (nothing burned), persistent failure retires the exec undelivered at a bounded attempt cap AND posts the honest give-up notice (D111 part 2) |
| `probe-chat-boundary` | #5 | bridge source holds no spawn/queue handle, opens no server, imports no sibling |
| `probe-chat-followup` | #6 | follow-up forwards as `send-message` on the chain thread (NEVER send-to-session), reply type `answer`/`note`; queue_id → exec_id learned from ticker dispatch actions; **exec KNOWN but NOT live → derives `exec-<firstExecId>`** (D111 convention fallback); **first-exec immutability** (a later exec-id bind is ignored); **exec-id-unknown DECLINES** (nothing enqueued) and posts the exact decline notice to the mapped thread while an allowlist-refused user gets nothing; a failed notice post is logged and dropped (no retry loop) |

## Flagged seams (task-7.5 / p7-checkpoint — surfaced, not resolved here)

- **`send-message` catalogue row** must exist in the live jobs catalogue for the
  follow-up leg (dry-run validates `type` ∈ CMP-8 types + non-empty `thread`).
  Seeding it is a server/deployment concern **outside this task's write surface**;
  the probes seed it into the throwaway store.
- **`queue_id → exec_id` correlation — WINDOWED, not absent** (p7-2 review
  finding). The inspect surface DOES expose the correlation: `inspect ticker` →
  `recent_ticks[].actions[]` carries `{ action: 'spawn', execId, queueId }` per
  fired row (the store's `jobs_log.queue_id` holds the same link), and
  `thread-map.js` navigates it (queue_id → exec_id via dispatch actions, then
  exec_id → thread via `live_sessions[]`, else the `exec-<first exec_id>` convention
  derivation, D111). The residual gap is the WINDOW for *learning the first exec-id*:
  the surface returns only the last 10 ticks (~100 s at default cadence), so a spawn
  older than that ages out before the first follow-up learns its exec-id — then
  resolution is honestly deferred (`exec-id-unknown`), never guessed. Once the first
  exec-id IS learned (within the window, or bound directly), it is remembered
  first-wins and EVERY later turn resolves by derivation regardless of liveness — the
  window no longer bites per-turn. A direct `jobs_log` lookup (e.g. exposing
  `queue_id` on `live_sessions[]`) would close the initial-learning gap too; that is
  a server-surface change outside this task's write surface.
- **Registry convergence.** The settled model is channel → (1:1) goal thread →
  per-slot sub-thread → session; the v1 chat-thread ↔ turn-chain map is the v1
  stand-in until goals/threads-store land.
- **Registry `sender`** resolves to no registry record though load-bearing across
  the gateway/bridge design (task-7.5 reconciliation row).
