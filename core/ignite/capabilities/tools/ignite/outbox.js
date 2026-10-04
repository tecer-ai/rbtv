'use strict';

// API
// deliverPending(store, deps) → [{ id, delivered, stopped?, channel?, ts?, error? }]
//   deps.slack.postMessage / uploadFile, deps.audio.speak when payload.audio.
//   payload.imUser is posted as the channel (Slack accepts a user id; slack.js has no open-DM call).
//   A board conversation (root ts "board") is posted as a new root and markDelivered rekeys it.
//   Pending rows are reloaded before delivery so later replies follow the newly bound thread.
//   The reply text is posted once (postMessage). Each file, including a synthesized voice file,
//   is uploaded with no caption. A files-only reply skips the empty post and confirms from the
//   upload ts. A confirmed post is rememberPost'd before uploads, so a retry does not post it again.
//   client_msg_id is the stored id, stable across retries. A row is marked delivered only after
//   Slack confirms channel and ts. Harness stdout is never read here.
//   Transient failures retry MAX_ATTEMPTS times (the same few-then-stop bound as a turn), then
//   stopOutbox plus one hold: notice. A permanent Slack error stops on the first failure.

const fs = require('node:fs');
const path = require('node:path');
const { MAX_ATTEMPTS } = require('./store.js');

const RETRY_MS = 5_000;
const PERMANENT = new Set([
  'invalid_thread_ts',
  'channel_not_found',
  'thread_not_found',
  'not_in_channel',
  'is_archived',
  'account_inactive',
]);

function voiceOf(store, home) {
  if (!home) return null;
  try {
    return JSON.parse(fs.readFileSync(path.join(home, 'agent.json'), 'utf8')).voice || null;
  } catch {
    return null;
  }
}

function isBoard(conv) {
  return conv?.root_ts === 'board' || String(conv?.key || '').endsWith(':board');
}

function permanentError(message) {
  const text = String(message || '');
  for (const code of PERMANENT) {
    if (text.includes(code)) return true;
  }
  return false;
}

function targetOf(row, conv) {
  const channel = row.payload?.imUser || conv.channel;
  const asRoot = Boolean(row.as_root) || isBoard(conv);
  const threadTs = asRoot ? undefined : (conv.root_ts || undefined);
  return { channel, threadTs, asRoot };
}

function giveUp(store, row, message) {
  const conv = store.getConversation(row.conversation_key);
  store.transaction(() => {
    store.stopOutbox(row.id, message);
    if (String(row.id).startsWith('hold:') || !conv) return;
    store.enqueueOutbox({
      id: `hold:delivery:${row.id}`,
      conversationKey: row.conversation_key,
      payload: { text: `Delivery is on hold. ${message} Repair: ignite post` },
      asRoot: Boolean(row.as_root) || isBoard(conv),
    });
  });
}

async function deliverOne(store, row, deps, now) {
  let conv = store.getConversation(row.conversation_key);
  if (!conv) {
    row = store._outbox(store.db.prepare('SELECT * FROM outbox WHERE id=?').get(row.id)) || row;
    conv = store.getConversation(row.conversation_key);
  }
  if (!conv) {
    store.stopOutbox(row.id, 'unknown conversation');
    return { id: row.id, delivered: false, stopped: true, error: 'unknown conversation' };
  }
  const target = targetOf(row, conv);
  const { channel, threadTs } = target;
  const text = typeof row.payload?.text === 'string' ? row.payload.text : '';
  const files = Array.isArray(row.payload?.files) ? row.payload.files.slice() : [];
  try {
    if (row.payload?.audio) {
      if (typeof deps.audio?.speak !== 'function') throw new Error('audio.speak required');
      const voice = voiceOf(store, deps.home);
      files.push(await deps.audio.speak(text, voice ? { voice } : {}));
    }
    if (files.length && typeof deps.slack?.uploadFile !== 'function') throw new Error('slack.uploadFile required');
    let confirmed = row.channel && row.ts ? { channel: row.channel, ts: row.ts } : null;
    if ((text || !files.length) && !confirmed) {
      if (typeof deps.slack?.postMessage !== 'function') throw new Error('slack.postMessage required');
      const posted = await deps.slack.postMessage({
        channel,
        threadTs,
        text,
        clientMsgId: row.client_msg_id,
      });
      if (!posted?.channel || !posted?.ts) throw new Error('Slack did not confirm delivery');
      store.rememberPost(row.id, posted);
      confirmed = posted;
    }
    for (const file of files) {
      const uploaded = await deps.slack.uploadFile({ channel, threadTs, file });
      if (!confirmed && uploaded?.ts) confirmed = { channel, ts: uploaded.ts };
    }
    if (!confirmed?.channel || !confirmed?.ts) throw new Error('Slack did not confirm delivery');
    const saved = store.markDelivered(row.id, {
      channel: confirmed.channel,
      ts: confirmed.ts,
      asRoot: target.asRoot,
    });
    return { id: row.id, delivered: true, channel: saved.channel, ts: saved.ts, conversationKey: saved.conversationKey };
  } catch (error) {
    const message = error.message || String(error);
    if (!store.getConversation(row.conversation_key)) {
      store.stopOutbox(row.id, message);
      return { id: row.id, delivered: false, stopped: true, error: message };
    }
    const failed = store.markDeliveryFailed(row.id, message, { retryAt: now + RETRY_MS });
    if (permanentError(message) || failed.attempts >= MAX_ATTEMPTS) {
      giveUp(store, row, message);
      return { id: row.id, delivered: false, stopped: true, error: message };
    }
    return { id: row.id, delivered: false, error: message };
  }
}

async function deliverPending(store, deps = {}) {
  const now = deps.now ? deps.now() : Date.now();
  const rows = store.pendingOutbox(now);
  const results = [];
  for (const row of rows) {
    const current = store._outbox(store.db.prepare('SELECT * FROM outbox WHERE id=?').get(row.id));
    results.push(await deliverOne(store, current, deps, now));
  }
  return results;
}

module.exports = { deliverPending, RETRY_MS, MAX_ATTEMPTS };
