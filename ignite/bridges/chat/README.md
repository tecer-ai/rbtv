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
dialogue only, no mid-turn interrupt / live TUI (that was the ttyd surface, retired at task 7.29 — a live TUI is now a tmux pane reached over SSH, not a daemon intent).

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

## One channel per goal (task 7.58, owner ruling `d-channel-per-goal`) — `goal-channel-map.js`

A goal's Slack surface is a **dedicated channel per goal**; the goal `thread` maps 1:1
onto it. The former per-goal chat-THREAD surface is superseded.

**Which surface a message arrived on decides how it routes**, and the bridge decides
that first (`chat-bridge.js` `routeOf`):

| Inbound | Route | Conversation id |
|---------|-------|-----------------|
| **DM** to the bot (`channel_type: 'im'`) | **master** traffic — cold contact, unchanged by the ruling. A DM has no goal, so it can never be attributed to one. | the Slack thread `channel:thread_ts` |
| Message in a **mapped goal channel** | **goal** traffic | the **channel id** — the goal thread IS the channel; sharding by `thread_ts` would split one goal thread into many |
| Message **mentioning the bot** (`<@BOTID>`) in an **unmapped** channel or group | **master** traffic (the *mention route*, owner ruling 2026-08-06). A mention **MINTS** the conversation. Replies always post **in-thread**, so each thread is its own parallel sitting and a new thread is a new sitting. | the Slack thread `channel:thread_ts` |
| An **unmentioned** message in an unmapped channel whose thread **already is a conversation** (`threadMap.has(channel:thread_ts)`) | **master** traffic — membership **CONTINUES** the sitting (it takes the follow-up leg). | the same Slack thread `channel:thread_ts` |
| An **unmentioned** message in a channel mapping to no goal and to no known conversation, or a group DM (`mpim`) | **refused**, nothing enqueued | — |

**Mint vs continue.** A mention is what makes traffic attributable, so it is what
*starts* a sitting — but requiring one on every subsequent turn made the owner re-mention
the bot to answer its own question (observed 2026-08-06, minutes after the mention route
deployed: the reply fell into the unmapped-channel refusal and got silence). So: a
**mention MINTS a conversation; membership in an existing one CONTINUES it**. The
continuation test is exactly `threadMap.has(<the id the mention route would assign>)`,
which is self-limiting by construction — a **top-level** message's conversation id is its
own `ts`, always brand new, so it can never match. Only replies inside a thread that
already IS a sitting continue without a mention; an unknown thread, a top-level message,
and the same `thread_ts` in a different channel all stay refused.

> ⚠ **Accepted limit — restart forgets the sittings.** The thread map is **in-memory**.
> After a bridge restart an un-mentioned reply in a pre-restart thread is **refused**
> until the owner re-mentions the bot, which re-mints the conversation. Not fixed by
> design: persisting the map is the upgrade path if restarts become frequent.

The mention route **fails closed**. The bot's own user id is resolved once at `start()`
via Slack `auth.test` on the bot token; if that fails the route is never armed and an
unmapped channel behaves exactly as it did before the ruling (refused) — a bot that
cannot say who it is must not guess who was meant. `app_mention` events stay ignored:
member-channel `message` events already carry the traffic, so **the bot must be a member
of the channel** for a mention there to reach the bridge. `mpim` (group DM) stays
refused even when mentioned — it is neither a goal channel nor the 1:1 owner DM the
master path assumes.

The surface gate runs **after** admission, not before: refusing earlier is no weaker,
but it would stop a non-admitted principal from ever reaching the allowlist's pairing
queue, and that queue is the DM-pairing feature (DEC-6).

**The two formerly-open points are settled** — reasoning, alternatives and the
registry-transcription flags are in `goal-channel-design.md`:

- **(a) Creation** — the **bridge** creates the channel, at **goal registration**,
  through one idempotent **name-derived** call (`bridge.registerGoal(goalId)` →
  `ensureChannel`). Only the bridge holds a chat credential. Name-derivation
  (`{prefix}{goalId}`, a bijection) is load-bearing, not cosmetic: the bridge's state
  is in-memory, so a restart rebuilds every binding from `conversations.list` alone
  (`recover()`, run at `start()`) — no persistence, no store handle. Slack's
  `name_taken` is therefore the **adopt** path, not an error. A goal id that does not
  derive cleanly is **refused, never sanitized** — sanitizing would break the inverse
  and let two goals share one channel.
- **(b) Close-time** — **archive, never delete** (`bridge.closeGoal(goalId)` →
  `retire`), idempotent (`already_archived` / `channel_not_found` are success). A
  refused archive **keeps** the binding: the channel is still live, and dropping it
  would leave goal traffic pointed at a channel nobody believes is in use.

**There is no `conversations.invite` code path anywhere in this module, and there must
never be one.** The bridge cannot add a member to a channel; membership is a human act
in the Slack UI. `probe-chat-goal-channel` asserts that absence against the source, so
"the owner is in no channel" is a mechanical guarantee rather than a procedural one.

**Reaching the current phase-owner voice** (CMP-8 § Thread-model routing) is the
SERVER's derivation, not the bridge's: a sender types its message and never addresses a
recipient. The bridge reaches that voice **by not addressing one** — it enqueues a
`send-message` carrying the goal thread. v1 has no phase-owner router yet, so the goal
thread collapses to the chain-stable `exec-<first exec_id>` (`concepts/thread.md` § v1
interim handle) and delivery reaches that chain's current turn.

**Operator surface:** `goal-channel-cli.js` (`whoami` · `ensure` · `list` · `members` ·
`post` · `retire`) is the stand-in caller until the goal-registration hook exists (task
7.63 `rbtv goal scaffold`). Same functions, same idempotence, invoked by hand rather
than by an event.

**Required Slack bot scopes:** `channels:manage` (create + archive), `channels:read`
(+ `groups:read`, for list/members), `chat:write`, `channels:history`, `im:history`.
Deliberately **not** required: any invite scope.

## The forward contract (D104/D105) — `forward-path.js`

One chat thread = one conversation. A message from an admitted principal becomes
exactly one gateway call, always `enqueue-job` (the bridge adds no new intent):

| Case | Forward |
|------|---------|
| **First** message in a new chat thread | `enqueue-job` naming a session-creating **launch-agent** function + a named launch profile (DEC-1 R3). The bridge never spawns; the ticker's Dispatch phase does. |
| **Follow-up** in a mapped thread | `enqueue-job` carrying a **`send-message`** action-type job addressed to the mapped turn-chain's thread (`exec-<first exec_id>`). Reply type `answer` on a pending `ask`, else `note` (closed CMP-8 vocabulary). |

**NEVER `send-to-session`** (D104): that leg was `session_mode: headed` + live only
(the pty keystroke rung). Chat rides the headless turn-boundary ceiling. There is
no send-to-session code path in this module, by construction — and since task 7.29
retired the intent, there is none anywhere: the constraint is now structural rather
than a discipline this module keeps.

### The prompt is the bare user text (owner ruling 2026-08-06)

A session-create carries `args: { profile, prompt, workdir }` where **`prompt` is the
user's message, verbatim** — on the master, mention and goal legs alike. The bridge
ships **zero behavioural text**: who a session is and how it answers travel with the
seat it is homed at, through that seat's `seat.md` and the auto-injected `CLAUDE.md`
chain above it. That keeps identity in one place its owner edits, and keeps
instance-specific paths out of repo source (the retired `MASTER_CHARTER` constant
carried an absolute `/home/…` path). `probe-chat-mention-route` asserts both — the
verbatim prompt, and the absence of any instance path in the runtime source.

### Where a session runs

| Leg | `args.workdir` |
|-----|----------------|
| master (DM) and mention | `config.workdir`, unchanged |
| **goal channel** | the goal's **`goal-master` seat**: `<workspace_root>/.rbtv/goals/<goalId>/runs/<open run-id>/seats/goal-master`, resolved per message from that goal's `runs.csv` row with `state=open` |

If `workspace_root` is unset, `runs.csv` is missing, no run is open, or the
`goal-master` seat directory does not exist, the bridge enqueues **nothing** and posts
the fixed notice `⚠ no goal-master seat is open for this goal — ask the run's owner to
seat one` on the goal's channel. There is deliberately **no fallback workdir**: a
session launched outside its seat would run with no descriptor and no goal identity at
all, which is worse than not running.

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
again shortly`) via `deliverToOwner`. The same mechanics carry the goal-channel
no-seat notice above. When the reply leg retires an exec undelivered
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
send_message_job_id, workdir, workspace_root, channel_prefix, master_profile,
goal_profile, allowlist: [chat-user-ids] }`.

`workspace_root` is the workspace whose `.rbtv/goals/` holds the goal runs — it is what
a goal-channel session's workdir is resolved from (below). Leaving it unset does not
affect DM or mention traffic; goal traffic then refuses loudly instead of launching
somewhere arbitrary.

## Validation (STAGED — ADX-33(2) / D106)

The spec's fidelity floor (a REAL Slack round-trip) needs an owner-provisioned Slack
app that does not exist at build time. Build-time validation exercises the spec's
probes against a **local stand-in**: a mock Socket-Mode server + a **throwaway**
in-process daemon (heart store + internal API + gateway) on an ephemeral loopback
port — never the live daemon, never port 7431. The real-transport round-trip
(Test Plan rows 1/2/4/6 at the real floor) runs at **p7-checkpoint** with the owner.

Run the probes through the counting runner — `node ../../deploy/probe-suite.js --dir
bridges/chat/probes` (or `--only probe-chat-<name>` for one). Never invoke a probe file
directly: that rewrites its capture with pure noise and the run is neither counted nor
graded for staleness (`ignite/CLAUDE.md` § probes). Evidence → `probe-chat-<name>.out`.

| Probe | Test Plan | Proves |
|-------|-----------|--------|
| `probe-chat-enqueue` | #1 | allowlisted user's message → validated job reaches gateway → queue (full mock-WS round-trip); redelivery legs (D108(C)): same event re-pushed under a new envelope is dropped — SAME-channel follow-up on a live chain (no double `send-message`), the `(channel, event_ts)` fallback key when `client_msg_id` is absent, and a negative control proving two DISTINCT messages both still enqueue |
| `probe-chat-allowlist` | #2 | non-allowlisted user refused, nothing enqueued; admitted user does enqueue |
| `probe-chat-outbound` | #3 | starting the bridge adds NO new inbound listener (`ss -tlnp` delta) |
| `probe-chat-outbound-msg` | #4 | owner output delivered outbound via `chat.postMessage` |
| `probe-chat-reply-leg` | #4 | the D110 driver, armed through the REAL inbound wiring (Slack event → forward path → arm): spawn captured from `recent_ticks` → `live:false` → LAST stream-json result line extracted (multi-page logs paged to the end) → posted to the conversation's channel+thread, text-EQUAL to the result string; no-result log delivers the fixed fallback (never the raw log); no exec delivered twice; a follow-up turn (new exec, same queue) delivers a second reply; a transient logs failure or refused post is retried (nothing burned), persistent failure retires the exec undelivered at a bounded attempt cap AND posts the honest give-up notice (D111 part 2) |
| `probe-chat-mention-route` | — | the 2026-08-06 rulings: a mention in an unmapped channel routes as master with a thread-scoped conversation and an in-thread reply address; an unmentioned (or someone-else-mentioning) message there stays refused with nothing enqueued; `mpim` stays refused even when mentioned; a failed `auth.test` DISABLES the mention route while the DM path keeps working; a goal session-create is homed at the open run's `goal-master` seat; each of the four unresolvable-seat states (no open run · run open but unseated · goal absent · `workspace_root` unset) enqueues nothing and posts the fixed no-seat notice; every session-create prompt equals the user text verbatim; the runtime source carries no instance path and no `MASTER_CHARTER`; and the **mint-vs-continue** rule — a mention mints, an un-mentioned reply in a KNOWN thread continues as a follow-up `send-message`, while an unknown thread, a top-level message, and the same `thread_ts` in another channel each stay refused with nothing enqueued |
| `probe-chat-boundary` | #5 | bridge source holds no spawn/queue handle, opens no server, imports no sibling |
| `probe-chat-followup` | #6 | follow-up forwards as `send-message` on the chain thread (NEVER send-to-session), reply type `answer`/`note`; queue_id → exec_id learned from ticker dispatch actions; **exec KNOWN but NOT live → derives `exec-<firstExecId>`** (D111 convention fallback); **first-exec immutability** (a later exec-id bind is ignored); **exec-id-unknown DECLINES** (nothing enqueued) and posts the exact decline notice to the mapped thread while an allowlist-refused user gets nothing; a failed notice post is logged and dropped (no retry loop) |

## Flagged seams (task-7.5 / p7-checkpoint — surfaced, not resolved here)

- **`send-message` catalogue row** must exist in the live jobs catalogue for the
  follow-up leg (dry-run validates `type` ∈ CMP-8 types + non-empty `thread`).
  Seeding it is a server/deployment concern **outside this task's write surface**;
  the probes seed it into the throwaway store.
- **`queue_id → exec_id` correlation — initial-learning gap CLOSED** (p7-2 review
  finding; closed by D108(B)). `inspect ticker` → `live_sessions[]` now exposes
  `queue_id` per row (the store's `jobs_log.queue_id` link, populated by
  `fireQueueRow`), and `thread-map.js` resolves in this tier order (see its
  RESOLUTION ORDER header):
  1. **queue_id → live session direct match** (reason `inspect-ticker-queue`) —
     TIME-INDEPENDENT: a live session resolves at ANY age, no ticks window. The
     hit also binds the first exec-id (first-wins preserved — it IS the first
     binding).
  2. **`recent_ticks[].actions[]` navigation** — `{ action: 'spawn', execId,
     queueId }` per fired row; still WINDOWED (last 10 ticks, ~100 s at default
     cadence). It remains the tier that covers a spawn whose session already
     ENDED (absent from `live_sessions[]`) but is still inside the window.
  3. **exec_id → thread via `live_sessions[]`** (reason `inspect-ticker`), else
     the `exec-<first exec_id>` convention derivation (reason
     `derived-convention`, D111).
  The formerly-flagged initial-learning window now bites ONLY the narrow case of a
  session that ENDED before the first follow-up AND whose spawn aged out of the
  ticks window — then resolution is honestly deferred (`exec-id-unknown`), never
  guessed. Once the first exec-id IS learned, it is remembered first-wins and
  EVERY later turn resolves by derivation regardless of liveness.
- **Registry convergence.** The settled model is channel → (1:1) goal thread →
  per-slot sub-thread → session; the v1 chat-thread ↔ turn-chain map is the v1
  stand-in until goals/threads-store land.
- **Registry `sender`** resolves to no registry record though load-bearing across
  the gateway/bridge design (task-7.5 reconciliation row).
