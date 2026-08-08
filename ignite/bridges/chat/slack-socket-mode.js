'use strict';

// The ruled v1 transport: Slack SOCKET MODE (D105) — an OUTBOUND WebSocket to
// Slack (notes §7b). Socket Mode sidesteps the remote-endpoint problem entirely:
// the bridge opens ONLY outbound connections, so the daemon stays loopback/tailnet
// bound and NO public listener is added (chat-bridge-spec.md Behavior #4).
//
// ⚑ OUTBOUND-ONLY, BY CONSTRUCTION. This module creates NO server — no
// http.createServer, no net.createServer, no WebSocket server. It makes exactly
// two kinds of outbound call:
//   • `apps.connections.open` (HTTP POST, app-level token) → a `wss://` URL, then
//     an outbound WebSocket client to it, over which Slack pushes events;
//   • `chat.postMessage` (HTTP POST, bot token) to deliver owner output outbound.
// probe-chat-outbound proves (via `ss -tlnp`) that starting the bridge adds no
// inbound listener.
//
// ⚑ TURN-BOUNDARY CEILING (notes §7b): the bridge inherits the headless model's
// ceiling — turn-boundary dialogue only. No mid-turn interrupt / live TUI over
// chat (that was the ttyd surface, retired at task 7.29).
//
// Telegram (`getUpdates` long-poll) is ADDITIVE later — a second transport behind
// the same onMessage/sendToOwner shape and the same allowlist/pairing/mapping
// (DEC-3 "and/or"). It is NOT built here (D105: Slack for v1).

// Injectable WebSocket + fetch so a mock Socket-Mode server can drive the bridge
// at build time (ADX-33(2): validation is STAGED — a LOCAL mock stands in for the
// owner-provisioned Slack app, which does not exist at dispatch time).
function createSlackSocketMode({
  appToken,
  botToken,
  apiBase = 'https://slack.com/api',
  onMessage,
  logger = null,
  WebSocketImpl = globalThis.WebSocket,
  fetchImpl = globalThis.fetch,
}) {
  if (typeof onMessage !== 'function') throw new Error('createSlackSocketMode requires an onMessage callback');
  if (!WebSocketImpl) throw new Error('no WebSocket implementation available (Node 24 provides a global WebSocket)');

  let ws = null;
  let closedByUs = false;

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // Slack delivers events AT-LEAST-ONCE — after a reconnect or slow ack, the
  // same message event is re-pushed with a NEW envelope id. The bridge MUST drop
  // redelivered duplicates BEFORE the forward path, so one chat message can never
  // enqueue two jobs (D108(C)).
  //
  // Key: `client_msg_id` (user-authored messages carry a durable id), else the
  // (channel, event_ts) pair. The envelope id is NEVER the key — redelivery mints
  // a fresh envelope for the same event.
  const DEDUPE_MAX = 500;
  const dedupeCache = new Map();

  function dedupeKey(event) {
    if (!event) return null;
    if (event.client_msg_id) return `msg:${event.client_msg_id}`;
    if (event.channel && event.event_ts) return `ev:${event.channel}:${event.event_ts}`;
    return null;
  }

  function isDuplicate(event) {
    const key = dedupeKey(event);
    if (!key) return false;
    if (dedupeCache.has(key)) return true;
    dedupeCache.set(key, true);
    if (dedupeCache.size > DEDUPE_MAX) {
      const oldest = dedupeCache.keys().next().value;
      dedupeCache.delete(oldest);
    }
    return false;
  }

  async function slackPost(method, token, body) {
    const res = await fetchImpl(`${apiBase}/${method}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body || {}),
    });
    const json = await res.json();
    return json;
  }

  // Slack Socket Mode handshake: apps.connections.open returns a short-lived
  // `wss://` URL. The bridge opens an OUTBOUND WebSocket to it (no inbound port).
  async function openConnection() {
    if (!appToken) throw new Error('SLACK_APP_TOKEN (app-level token) is required to open a Socket Mode connection');
    const resp = await slackPost('apps.connections.open', appToken, {});
    if (!resp || !resp.ok || !resp.url) {
      throw new Error(`apps.connections.open failed: ${JSON.stringify(resp)}`);
    }
    return resp.url;
  }

  // A user message event → the transport-neutral shape the bridge consumes.
  //
  // The conversation id depends on WHICH SURFACE the message arrived on, and the
  // BRIDGE (not this transport) makes that call — so this function reports the raw
  // facts and leaves routing to chat-bridge.js (task 7.58, d-channel-per-goal):
  //   • DM (`channel_type: 'im'`) — cold-contact MASTER traffic, unchanged by that
  //     ruling. Its conversation is the Slack thread `channel:thread_ts`.
  //   • CHANNEL — GOAL traffic when the channel is a mapped goal channel. There the
  //     goal thread maps 1:1 onto the CHANNEL, so the channel itself is the
  //     conversation; `channel:thread_ts` would shard one goal thread into many.
  // `chatThreadId` below is the DM-shaped default; the bridge overrides it for goal
  // traffic. `_channelType` carries Slack's own surface discriminator.
  function toChatMessage(event) {
    if (!event || event.type !== 'message') return null;
    // Ignore bot echoes, edits/deletes, and joins — only genuine user text drives work.
    // Exception: `file_share` (a user message carrying an attachment) passes through —
    // the bridge does NOT ferry the bytes; it appends a pointer line per file so the
    // agent can pull it itself (stools download takes exactly channel + message ts).
    const files = Array.isArray(event.files) ? event.files : [];
    const isFileShare = event.subtype === 'file_share' && files.length > 0;
    if (event.bot_id || (event.subtype && !isFileShare) || typeof event.user !== 'string' || typeof event.text !== 'string') return null;
    let text = event.text;
    if (files.length > 0) {
      const fileLines = files.map((f) =>
        `[attachment: ${f.name || f.id || 'file'} (${f.mimetype || 'unknown type'}) — slack channel ${event.channel}, message ts ${event.ts} — download it yourself: stools download --channel ${event.channel} --ts ${event.ts} --output downloads]`);
      text = [event.text, ...fileLines].filter(Boolean).join('\n');
    }
    const rootTs = event.thread_ts || event.ts;
    return {
      chatUserId: event.user,
      chatThreadId: `${event.channel}:${rootTs}`,
      text,
      // Kept for the outbound reply address (chat.postMessage channel + thread_ts).
      _channel: event.channel,
      _threadTs: rootTs,
      _msgTs: event.ts,                          // the MESSAGE's own ts (reactions.add target)
      _channelType: event.channel_type || null,  // 'im' | 'channel' | 'group' | 'mpim'
      _inThread: Boolean(event.thread_ts),       // did the human post inside a Slack thread?
    };
  }

  function ackEnvelope(envelopeId) {
    if (ws && envelopeId) {
      try { ws.send(JSON.stringify({ envelope_id: envelopeId })); } catch (err) {
        log('warn', 'failed to ack Socket Mode envelope', { envelopeId, error: err.message });
      }
    }
  }

  async function handleFrame(raw) {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }
    switch (msg.type) {
      case 'hello':
        log('info', 'Socket Mode connection established (hello)', { numConnections: msg.num_connections });
        return;
      case 'disconnect':
        // Slack asks us to reconnect (token refresh / server cycling). Re-open.
        log('info', 'Socket Mode disconnect requested — reconnecting', { reason: msg.reason });
        reconnect();
        return;
      case 'events_api': {
        // ACK FIRST (Slack requires an ack within 3s), then process.
        ackEnvelope(msg.envelope_id);
        const event = msg.payload && msg.payload.event;
        if (isDuplicate(event)) {
          log('debug', 'duplicate slack event dropped (redelivery guard)', {
            client_msg_id: event && event.client_msg_id,
            channel: event && event.channel,
            event_ts: event && event.event_ts,
          });
          return;
        }
        const chatMsg = toChatMessage(event);
        if (chatMsg) {
          try {
            await onMessage(chatMsg);
          } catch (err) {
            log('error', 'onMessage handler threw', { error: err.message });
          }
        }
        return;
      }
      default:
        // slash_commands / interactive etc. — ack so Slack does not retry; v1
        // drives conversations through plain messages only.
        if (msg.envelope_id) ackEnvelope(msg.envelope_id);
        return;
    }
  }

  function attach(url) {
    const socket = new WebSocketImpl(url);
    ws = socket;
    socket.addEventListener('message', (ev) => {
      const data = typeof ev.data === 'string' ? ev.data : String(ev.data);
      handleFrame(data);
    });
    socket.addEventListener('close', () => {
      // Only the CURRENT socket's close triggers a reconnect — a stale socket
      // (already replaced by reconnect()) closing late must not churn the new one.
      if (!closedByUs && ws === socket) {
        log('warn', 'Socket Mode WebSocket closed — reconnecting');
        reconnect();
      }
    });
    socket.addEventListener('error', (ev) => {
      log('warn', 'Socket Mode WebSocket error', { message: ev && ev.message });
    });
  }

  // Reconnect with capped exponential backoff (1s → 60s). An unattended bridge
  // must survive a transient failure window (Slack outage, network blip) — one
  // failed attempt never leaves it silently dead — while never loop-hammering.
  const RETRY_BASE_MS = 1000;
  const RETRY_CAP_MS = 60000;
  let reconnecting = false;
  let retryDelayMs = RETRY_BASE_MS;
  let retryTimer = null;
  async function reconnect() {
    if (closedByUs || reconnecting) return;
    reconnecting = true;
    try {
      try { if (ws) ws.close(); } catch {}
      const url = await openConnection();
      attach(url);
      retryDelayMs = RETRY_BASE_MS; // reset the backoff on success
    } catch (err) {
      log('error', 'Socket Mode reconnect failed — retrying with backoff', { error: err.message, retryInMs: retryDelayMs });
      if (!closedByUs && !retryTimer) {
        retryTimer = setTimeout(() => { retryTimer = null; reconnect(); }, retryDelayMs);
        retryDelayMs = Math.min(retryDelayMs * 2, RETRY_CAP_MS);
      }
    } finally {
      reconnecting = false;
    }
  }

  async function start() {
    closedByUs = false;
    const url = await openConnection();
    attach(url);
    return { connected: true };
  }

  // Deliver worker/leader output to the owner OUTBOUND (chat-bridge-spec.md
  // Behavior #3): chat.postMessage on the conversation's channel + thread. Text
  // and (later) attachments; Slack size caps apply.
  async function sendToOwner({ channel, threadTs, text }) {
    if (!botToken) throw new Error('SLACK_BOT_TOKEN (bot token) is required to post owner output');
    const body = { channel, text };
    if (threadTs) body.thread_ts = threadTs;
    const resp = await slackPost('chat.postMessage', botToken, body);
    if (!resp || !resp.ok) {
      log('warn', 'chat.postMessage failed', { channel, error: resp && resp.error });
      return { delivered: false, error: resp && resp.error };
    }
    return { delivered: true, ts: resp.ts };
  }

  // React to / un-react a message: the ⏳ pending marker the bridge puts on an owner
  // message when its turn is accepted and takes off when the answer lands
  // (chat-bridge.js § pending marker; owner-directed 2026-08-06, one-marker
  // convergence 2026-08-07). Best-effort — a failed reaction never blocks the forward
  // or the reply; needs the `reactions:write` bot scope. `name` is always the
  // caller's: there is no default marker for this transport to assume.
  //
  // ⚑ ONE LOG LINE PER RUN, AT INFO. A missing scope fails EVERY reaction on EVERY
  // message, so a per-call warn would fill an unattended log with the same line and
  // read as a fault — reactions are cosmetic, and their absence degrades nothing.
  let reactionErrorLogged = false;
  async function reactCall(method, { channel, ts, name }) {
    if (!botToken || !channel || !ts) return { reacted: false };
    const resp = await slackPost(method, botToken, { channel, timestamp: ts, name });
    if (!resp || !resp.ok) {
      // already_reacted / no_reaction are expected no-ops (Slack redelivery, or a
      // marker already cleared); anything else is worth exactly one log line.
      const error = (resp && resp.error) || null;
      if (error !== 'already_reacted' && error !== 'no_reaction' && !reactionErrorLogged) {
        reactionErrorLogged = true;
        log('info', 'slack reaction call failed — reactions are cosmetic and best-effort; not logged again this run', { method, channel, error });
      }
      return { reacted: false, error };
    }
    return { reacted: true };
  }

  function react({ channel, ts, name }) {
    return reactCall('reactions.add', { channel, ts, name });
  }

  function unreact({ channel, ts, name }) {
    return reactCall('reactions.remove', { channel, ts, name });
  }

  // Who am I? `auth.test` on the bot token returns this bot's own user id, which is
  // what a human's `<@U…>` mention resolves to in message text. The bridge needs it to
  // recognise a mention in a channel it does not otherwise route (chat-bridge.js
  // routeOf, mention route). One outbound POST at start; the caller caches the result.
  async function authTest() {
    if (!botToken) return { ok: false, error: 'no-bot-token' };
    const resp = await slackPost('auth.test', botToken, {});
    if (!resp || !resp.ok || !resp.user_id) {
      return { ok: false, error: (resp && resp.error) || 'auth-test-failed' };
    }
    return { ok: true, userId: resp.user_id };
  }

  // Open (or fetch) the 1:1 DM channel with a user — `conversations.open` is
  // idempotent and returns the same `D…` id every time. The bus ferry (bus-ferry.js)
  // resolves it ONCE at start and caches it; posting then goes through the same
  // `sendToOwner` as everything else. Another outbound POST on the bot token — the
  // outbound-only property is untouched.
  async function openDm(userId) {
    if (!botToken) return { ok: false, error: 'no-bot-token' };
    if (!userId) return { ok: false, error: 'no-user-id' };
    const resp = await slackPost('conversations.open', botToken, { users: userId });
    if (!resp || !resp.ok || !resp.channel || !resp.channel.id) {
      log('warn', 'conversations.open failed', { userId, error: resp && resp.error });
      return { ok: false, error: (resp && resp.error) || 'open-dm-failed' };
    }
    return { ok: true, channel: resp.channel.id };
  }

  // ── The goal-channel ADMIN surface (task 7.58) ──────────────────────────────
  //
  // Three calls, and deliberately only three: create, list, archive. All are
  // OUTBOUND HTTP POSTs on the bot token — the outbound-only property this module
  // exists to preserve is untouched, and `probe-chat-outbound` still holds.
  //
  // ⚑ THERE IS NO `conversations.invite` CALL HERE, AND THERE MUST NEVER BE ONE.
  // The bridge never adds a member to a channel; membership is a human act in the
  // Slack UI. The run's `r-slack-etiquette` guard ("the owner is added to NO test
  // channel") is enforced by this ABSENCE, which a probe asserts against the source
  // — a guard that cannot be forgotten under pressure, unlike a policy.

  async function createChannel({ name, isPrivate = false }) {
    if (!botToken) throw new Error('SLACK_BOT_TOKEN is required to create a channel');
    const resp = await slackPost('conversations.create', botToken, { name, is_private: Boolean(isPrivate) });
    if (!resp || !resp.ok) {
      // `name_taken` is an expected, meaningful outcome (the adopt path) — logged at
      // info, not warn, so it does not read as a fault in an unattended log.
      log(resp && resp.error === 'name_taken' ? 'info' : 'warn', 'conversations.create did not create', { name, error: resp && resp.error });
      return { ok: false, error: resp && resp.error };
    }
    return { ok: true, channel: { id: resp.channel && resp.channel.id, name: resp.channel && resp.channel.name } };
  }

  async function listChannels({ cursor = null, excludeArchived = true, limit = 200 } = {}) {
    if (!botToken) throw new Error('SLACK_BOT_TOKEN is required to list channels');
    const body = {
      types: 'public_channel,private_channel',
      exclude_archived: Boolean(excludeArchived),
      limit,
    };
    if (cursor) body.cursor = cursor;
    const resp = await slackPost('conversations.list', botToken, body);
    if (!resp || !resp.ok) {
      log('warn', 'conversations.list failed', { error: resp && resp.error });
      return { ok: false, error: resp && resp.error };
    }
    const channels = Array.isArray(resp.channels)
      ? resp.channels.map((c) => ({ id: c.id, name: c.name, is_archived: Boolean(c.is_archived) }))
      : [];
    const nextCursor = (resp.response_metadata && resp.response_metadata.next_cursor) || null;
    return { ok: true, channels, nextCursor: nextCursor || null };
  }

  async function archiveChannel({ channel }) {
    if (!botToken) throw new Error('SLACK_BOT_TOKEN is required to archive a channel');
    const resp = await slackPost('conversations.archive', botToken, { channel });
    if (!resp || !resp.ok) {
      log(resp && resp.error === 'already_archived' ? 'info' : 'warn', 'conversations.archive did not archive', { channel, error: resp && resp.error });
      return { ok: false, error: resp && resp.error };
    }
    return { ok: true };
  }

  function stop() {
    closedByUs = true;
    if (retryTimer) { clearTimeout(retryTimer); retryTimer = null; }
    try { if (ws) ws.close(); } catch {}
    ws = null;
  }

  return {
    start, stop, sendToOwner, react, unreact, authTest, openDm, openConnection, toChatMessage,
    createChannel, listChannels, archiveChannel,
  };
}

module.exports = { createSlackSocketMode };
