'use strict';

// API
// deliverPending(store, deps) → [{ id, delivered, channel?, ts?, error? }]
//   deps.slack.postMessage / uploadFile, deps.audio.speak when payload.audio.
//   payload.imUser is posted as the channel (Slack accepts a user id; slack.js has no open-DM call).
//   client_msg_id is the stored id, stable across retries. A row is marked delivered only after
//   postMessage returns channel and ts. Harness stdout is never read here.

const fs = require('node:fs');
const path = require('node:path');

const RETRY_MS = 5_000;

function voiceOf(store, home) {
  if (home) {
    try {
      const body = JSON.parse(fs.readFileSync(path.join(home, 'launch.json'), 'utf8'));
      if (body.voice) return body.voice;
    } catch {
      return store.getLaunchSetting()?.voice || null;
    }
  }
  return store.getLaunchSetting()?.voice || null;
}

function targetOf(row, conv) {
  const channel = row.payload?.imUser || conv.channel;
  const threadTs = row.as_root ? undefined : (conv.root_ts || undefined);
  return { channel, threadTs };
}

async function deliverOne(store, row, deps, now) {
  const conv = store.getConversation(row.conversation_key);
  if (!conv) {
    store.markDeliveryFailed(row.id, 'unknown conversation', { retryAt: now + RETRY_MS });
    return { id: row.id, delivered: false, error: 'unknown conversation' };
  }
  const { channel, threadTs } = targetOf(row, conv);
  const text = typeof row.payload?.text === 'string' ? row.payload.text : '';
  const files = Array.isArray(row.payload?.files) ? row.payload.files.slice() : [];
  try {
    if (row.payload?.audio) {
      if (typeof deps.audio?.speak !== 'function') throw new Error('audio.speak required');
      const voice = voiceOf(store, deps.home);
      files.push(await deps.audio.speak(text, voice ? { voice } : {}));
    }
    if (files.length && typeof deps.slack?.uploadFile !== 'function') throw new Error('slack.uploadFile required');
    for (const file of files) {
      await deps.slack.uploadFile({ channel, threadTs, file, text: text || undefined });
    }
    if (typeof deps.slack?.postMessage !== 'function') throw new Error('slack.postMessage required');
    const posted = await deps.slack.postMessage({
      channel,
      threadTs,
      text,
      clientMsgId: row.client_msg_id,
    });
    if (!posted?.channel || !posted?.ts) throw new Error('Slack did not confirm delivery');
    const saved = store.markDelivered(row.id, { channel: posted.channel, ts: posted.ts });
    return { id: row.id, delivered: true, channel: saved.channel, ts: saved.ts };
  } catch (error) {
    store.markDeliveryFailed(row.id, error.message, { retryAt: now + RETRY_MS });
    return { id: row.id, delivered: false, error: error.message };
  }
}

async function deliverPending(store, deps = {}) {
  const now = deps.now ? deps.now() : Date.now();
  const rows = store.pendingOutbox(now);
  const results = [];
  for (const row of rows) {
    results.push(await deliverOne(store, row, deps, now));
  }
  return results;
}

module.exports = { deliverPending, RETRY_MS };
