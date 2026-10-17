'use strict';

// API
// deliverPending(store, deps) → [{ id, delivered, stopped?, channel?, ts?, error? }]
//   deps.slack.postMessage / uploadFile, deps.audio.speak when payload.audio.
//   Every post and upload carries the agent's name and avatar from agent.json (deps.home), named by the one
//   sender routine the shared send function exports (sendModule.senderOf: external_name when set, else the
//   name with a capital first letter).
//   A user id target (payload.imUser, or a DM agent's board channel) is opened with slack.openIm and
//   posted to the returned DM: Slack may route a post addressed to a user id to the Slackbot DM.
//   A board conversation (root ts "board") is posted as a new root and markDelivered rekeys it.
//   Pending rows are reloaded before delivery so later replies follow the newly bound thread.
//   The post and the uploads go through the one send function the `message` port command uses too,
//   connectors/messaging/capabilities/tools/message/lib/send.js (sendModule, exported for the test that
//   fails when the two callers diverge), with an operations object built from this client: postMessage
//   behind 'message.send', uploadFile behind 'message.file', until phase 4 puts the Slack adapter there.
//   That function posts the text once, sends a text over 12,000 characters as a file, uploads each file,
//   including a synthesized voice file, with no caption as a message of the text's thread (a root post's
//   files follow it into the thread it starts), reports each file it could not send and fails as a whole
//   when nothing was delivered. A files-only reply skips the empty post and confirms from the upload ts. A
//   retry of a row whose text is confirmed sends the files only, into that text's thread. A confirmed post is
//   rememberPost'd before the failure of a later upload is raised, so a retry does not post it again;
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

const path = require('node:path');
const { MAX_ATTEMPTS } = require('./store.js');
const live = require('./live-status.js');
const { readAgent } = require('../../../../cast/capabilities/tools/cast/lib/agent');
const sendModule = require('../../../../../connectors/messaging/capabilities/tools/message/lib/send.js');

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

// The messaging contract's operations over this Slack client, for the shared send function: a group is
// posted to as given (a user id was already opened to its DM by deliverOne, as the contract's connector
// would), a file is uploaded with no caption.
function connectorOf(store, conv) {
  try {
    const rows = store.db.prepare('SELECT metadata FROM messages WHERE conversation_key=? ORDER BY created_at DESC, id DESC').all(conv.key);
    for (const row of rows) {
      const meta = JSON.parse(row.metadata || 'null');
      if (meta?.connector) return meta.connector;
    }
  } catch { /* a conversation with no connector stays on the Slack client */ }
  return 'slack';
}

function operationsFor(name, deps) {
  if (name === 'slack' || !name) return operationsOf(deps.slack);
  if (deps.messaging?.[name]) return deps.messaging[name];
  const adapter = require(path.join(__dirname, '..', '..', '..', '..', '..', 'connectors', name, 'capabilities', 'tools', name, 'lib', 'messaging.js'));
  const section = deps.listeners?.[name] || null;
  return {
    async 'message.send'(input) { return adapter.operations['message.send'](input, { section, spawn: deps.spawn, account: section?.account, mailbox: section?.mailbox }); },
    async 'message.file'(input) { return adapter.operations['message.file'](input, { section, spawn: deps.spawn, account: section?.account }); },
  };
}

function operationsOf(slack) {
  return {
    async 'message.send'({ group, contact, thread, text, as, clientId }) {
      if (typeof slack?.postMessage !== 'function') throw new Error('slack.postMessage required');
      const channel = group || (typeof slack.openIm === 'function' ? await slack.openIm(contact) : contact);
      const posted = await slack.postMessage({ channel, threadTs: thread || undefined, text, clientMsgId: clientId, as });
      if (!posted?.channel || !posted?.ts) throw new Error('Slack did not confirm delivery');
      return { conversation: posted.channel, id: posted.ts };
    },
    async 'message.file'({ send: { conversation, thread, file, as } }) {
      if (typeof slack?.uploadFile !== 'function') throw new Error('slack.uploadFile required');
      const uploaded = await slack.uploadFile({ channel: conversation, threadTs: thread || undefined, file, as });
      return { id: uploaded?.ts || null, conversation };
    },
  };
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
  const as = sendModule.senderOf(deps.home);
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
    // A retry of a row whose text Slack confirmed sends the files only, into that text's thread.
    const sent = await sendModule.send(operationsFor(connectorOf(store, conv), deps), {
      group: channel, thread: threadTs || (confirmed ? confirmed.ts : null), text: confirmed ? '' : text, files, as, clientId: row.client_msg_id,
    });
    if (!confirmed && sent.id && (text || !files.length || sent.textAsFile)) {
      const posted = { channel: sent.conversation, ts: sent.id };
      // The text's own message; a files-only reply confirms from its first upload below.
      if (!sent.files.length || sent.files[0].id !== sent.id) {
        store.rememberPost(row.id, posted);
        confirmed = posted;
      }
    }
    for (const file of sent.files) {
      if (!file.id) continue;
      store.rememberUpload(row.id, file.id);
      if (!confirmed) confirmed = { channel: sent.conversation, ts: file.id };
    }
    const refused = sent.files.find((file) => file.error);
    if (refused) throw new Error(refused.detail || refused.error);
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

module.exports = { deliverPending, RETRY_MS, MAX_ATTEMPTS, sendModule };
