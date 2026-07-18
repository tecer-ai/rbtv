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
// chat (that is the ttyd surface, Batch 6).
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

  // A user message event → the transport-neutral shape the forward path consumes.
  // One chat thread = one conversation (D105): the conversation id is the Slack
  // thread — `channel:thread_ts` (the parent-message ts roots the thread; a
  // top-level message roots its own).
  function toChatMessage(event) {
    if (!event || event.type !== 'message') return null;
    // Ignore bot echoes, edits/deletes, and joins — only genuine user text drives work.
    if (event.bot_id || event.subtype || typeof event.user !== 'string' || typeof event.text !== 'string') return null;
    const rootTs = event.thread_ts || event.ts;
    return {
      chatUserId: event.user,
      chatThreadId: `${event.channel}:${rootTs}`,
      text: event.text,
      // Kept for the outbound reply address (chat.postMessage channel + thread_ts).
      _channel: event.channel,
      _threadTs: rootTs,
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

  function stop() {
    closedByUs = true;
    if (retryTimer) { clearTimeout(retryTimer); retryTimer = null; }
    try { if (ws) ws.close(); } catch {}
    ws = null;
  }

  return { start, stop, sendToOwner, openConnection, toChatMessage };
}

module.exports = { createSlackSocketMode };
