'use strict';

// API
// deliverPending(store, deps) → [{ id, delivered, stopped?, channel?, ts?, error? }]
//   deps.slack.postMessage / uploadFile, deps.audio.speak when payload.audio.
//   Every post and upload carries the agent's name and avatar from agent.json (deps.home).
//   A user id target (payload.imUser, or a DM agent's board channel) is opened with slack.openIm and
//   posted to the returned DM: Slack may route a post addressed to a user id to the Slackbot DM.
//   A board conversation (root ts "board") is posted as a new root and markDelivered rekeys it.
//   Pending rows are reloaded before delivery so later replies follow the newly bound thread.
//   The reply text is posted once (postMessage). Each file, including a synthesized voice file,
//   is uploaded with no caption. A files-only reply skips the empty post and confirms from the
//   upload ts. A confirmed post is rememberPost'd before uploads, so a retry does not post it again;
//   each confirmed upload is rememberUpload'd, so the row keeps the ts of every message of the reply.
//   client_msg_id is the stored id, stable across retries. A row is marked delivered only after
//   Slack confirms channel and ts. Harness stdout is never read here.
//   Transient failures retry MAX_ATTEMPTS times (the same few-then-stop bound as a turn), then
//   stopOutbox plus one hold: notice. A permanent Slack error stops on the first failure.
//   A row delivered into its conversation's thread becomes messages of that conversation's live
//   status (live-status.js delivered), one per message Slack confirmed for it, and the status
//   follows the thread's latest message. A row with
//   payload.mark { channel, ts, runId?, task? } is a reply of the turn that answered that owner
//   message: once every row of that turn (its runId; channel and ts for a mark without one) is
//   delivered, the last one keeps the task, which replaces the turn's agent state; when one gives up,
//   the live system state is failed and nothing moves. Each is written in the transaction that
//   records the delivery or the give-up.

const { MAX_ATTEMPTS } = require('./store.js');
const live = require('./live-status.js');
const { readAgent } = require('../../../../cast/capabilities/tools/cast/lib/agent');

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
  return readAgent(home).agent?.voice || null;
}

// The agent's name and avatar from its agent.json, shown as the sender of every post and upload.
// The name is stored lowercase; the owner sees it with a capital first letter.
// An external_name, when set, is shown instead: the agent keeps its internal name.
function senderOf(home) {
  if (!home) return undefined;
  const agent = readAgent(home).agent;
  if (!agent) return undefined;
  const name = agent.externalName || agent.name.charAt(0).toUpperCase() + agent.name.slice(1);
  return { name, avatar: agent.avatar };
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

function isUserId(channel) {
  return /^[UW][A-Z0-9]+$/.test(String(channel || ''));
}

function markOf(row) {
  const mark = row.payload?.mark;
  return mark?.channel && mark?.ts ? mark : null;
}

// The turn a delivered row answers, as live-status.js delivered takes it: { ts, runId?, task? }, with
// the task once every row of that turn is delivered; null for a row with no mark.
function answerOf(store, mark) {
  const answer = { ts: mark.ts, ...(mark.runId && { runId: mark.runId }) };
  if (!mark.task) return answer;
  const sameRun = mark.runId ? " AND json_extract(payload, '$.mark.runId')=?" : '';
  const open = store.db.prepare(`SELECT COUNT(*) AS n FROM outbox WHERE state!='delivered'
    AND json_extract(payload, '$.mark.channel')=? AND json_extract(payload, '$.mark.ts')=?${sameRun}`)
    .get(mark.channel, mark.ts, ...(mark.runId ? [mark.runId] : [])).n;
  return open ? answer : { ...answer, task: mark.task };
}

function showDelivered(store, row, saved, target, deps) {
  // A row posted as a new root is not a message of the thread the status follows.
  if (target.asRoot) return;
  const mark = markOf(row);
  let answer = null;
  try {
    answer = mark ? answerOf(store, mark) : null;
  } catch {
    return; // A status never breaks a delivery that Slack already confirmed.
  }
  const reply = {
    conversationKey: saved.conversationKey || row.conversation_key,
    channel: saved.channel,
    messages: [...new Set([saved.ts, ...saved.posted])],
  };
  live.delivered(store, reply, answer, deps.log);
}

function giveUp(store, row, message, deps) {
  const conv = store.getConversation(row.conversation_key);
  store.transaction(() => {
    store.stopOutbox(row.id, message);
    const mark = markOf(row);
    if (mark) live.deliveryFailed(store, { ...mark, conversationKey: row.conversation_key }, deps.log);
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
  const { threadTs } = target;
  let { channel } = target;
  const text = typeof row.payload?.text === 'string' ? row.payload.text : '';
  const files = Array.isArray(row.payload?.files) ? row.payload.files.slice() : [];
  const as = senderOf(deps.home);
  try {
    if (isUserId(channel)) {
      if (typeof deps.slack?.openIm !== 'function') throw new Error('slack.openIm required');
      channel = await deps.slack.openIm(channel);
    }
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
        as,
      });
      if (!posted?.channel || !posted?.ts) throw new Error('Slack did not confirm delivery');
      store.rememberPost(row.id, posted);
      confirmed = posted;
    }
    for (const file of files) {
      const uploaded = await deps.slack.uploadFile({ channel, threadTs, file, as });
      if (!uploaded?.ts) continue;
      store.rememberUpload(row.id, uploaded.ts);
      if (!confirmed) confirmed = { channel, ts: uploaded.ts };
    }
    if (!confirmed?.channel || !confirmed?.ts) throw new Error('Slack did not confirm delivery');
    const saved = store.transaction(() => {
      const marked = store.markDelivered(row.id, {
        channel: confirmed.channel,
        ts: confirmed.ts,
        asRoot: target.asRoot,
      });
      showDelivered(store, row, marked, target, deps);
      return marked;
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
      giveUp(store, row, message, deps);
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
