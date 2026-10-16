'use strict';

// The Slack connector's messaging adapter: the messaging port's operations this connector performs for the
// `message` port command, through slack.com/api (connectors/messaging/capabilities/methods/messaging-contract.md,
// Adapter section). Ignite's own Slack client (core/ignite/.../slack.js) still carries Ignite's calls until
// phase 4 moves Ignite onto this module. Pure Node, no dependency: fetch is Node's.
//
// Token: the variable TOKEN_ENV (SLACK_BOT_TOKEN), read inside each operation from the process environment,
// then from the installation's .rbtv/config/env/.env (the installation found from the working folder upward
// by .rbtv/config/install.json), read literally: never when the module loads, never printed.
//
// API
// operations['message.send']({ group | contact, thread, text, as, clientId }) → { conversation, id, thread }
//   A contact (U…/W…) is resolved to its direct conversation with conversations.open; the text goes as
//   markdown_text with the thread, the client id and the agent's name and avatar. A thread is posted to at its
//   root: conversations.replies on the given id says whether it is the root or a reply (its thread_ts), and the
//   result's thread is that root, null for a message that starts a thread. UNVERIFIED against the live API
//   (stub only): that conversations.replies on a reply's ts returns that reply with its thread_ts.
// operations['message.file']({ send: { conversation | contact, thread, file, as } }) → { id, conversation, thread }
//   files.getUploadURLExternal, the bytes, files.completeUploadExternal into the thread's root; id is the share's ts.
// operations['message.history']({ conversation, thread }) → { events }: conversations.replies of the thread's
//   root, oldest first, each in the contract's inbound event shape; a reply's id reads its whole thread.
// operations['message.react']({ conversation, id, name, add }) → {}: reactions.add or reactions.remove.
// operations['group.manage']({ create: { name } } | { join: { group } } | { invite: { group, contact } } | { archive: { group } }) → { group }
// operations['approval.secure']({ post | update | whisper | open | push | change }) → { conversation, id } for a post or an
//   update, {} otherwise: chat.postMessage with blocks, chat.update, chat.postEphemeral, views.open, views.push, views.update.
// operations['message.receive'] — refused until phase 4 moves Ignite's listener onto this module: Ignite's own client
//   keeps the Socket Mode session today, so the function throws naming that.
// address(value) → { contact } for a user id, { group } for a channel id (C…, G…, or a D… conversation);
//   anything else throws an Error with code 'address' and the sentence the port command prints as why.
// account() → the team id of the token's workspace (auth.test), cached for the process.
// An error from Slack is an Error 'slack answered <code>' whose reason is the bare <code> (file_too_large), with
// code 'thread' for a thread Slack does not find.

const fs = require('node:fs');
const path = require('node:path');
const { envValue } = require('../../../../../../core/ignite/capabilities/tools/ignite/config.js');

const API = process.env.SLACK_API_URL || 'https://slack.com/api';
const TOKEN_ENV = 'SLACK_BOT_TOKEN';
const SELF_SUBTYPES = new Set(['message_changed', 'message_deleted', 'channel_join', 'group_join', 'bot_message']);

function fail(code, message, reason) {
  const error = new Error(message);
  if (code) error.code = code;
  if (reason) error.reason = reason;
  return error;
}

function installation(start = process.cwd()) {
  let dir = path.resolve(start);
  for (;;) {
    if (fs.existsSync(path.join(dir, '.rbtv', 'config', 'install.json'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function token() {
  const root = installation(process.env.RBTV_AGENT_HOME || process.cwd()) || installation();
  // Keep the connector's process-token trimming; file values retain their literal quoted contents.
  const value = envValue(root, TOKEN_ENV, { [TOKEN_ENV]: process.env[TOKEN_ENV]?.trim() });
  if (value) return value;
  throw fail(null, `slack: ${TOKEN_ENV} is not set in the environment or .rbtv/config/env/.env`);
}

async function api(method, body = {}, { form = true } = {}) {
  const bearer = token();
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(body)) {
    if (value == null) continue;
    params.set(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
  }
  const response = await fetch(`${API}/${method}`, {
    method: 'POST',
    headers: { authorization: `Bearer ${bearer}`, 'content-type': 'application/x-www-form-urlencoded' },
    body: form ? params.toString() : body,
  });
  if (!response.ok) throw fail(null, `slack answered HTTP ${response.status} on ${method}`);
  const data = await response.json();
  if (!data.ok) {
    const code = data.error || 'unknown_error';
    throw fail(code === 'thread_not_found' ? 'thread' : null, `slack answered ${code}${body.thread_ts ? ` for ${body.thread_ts} in ${body.channel}` : body.ts ? ` for ${body.ts} in ${body.channel}` : ''}`, code);
  }
  return data;
}

let identity = null;
async function whoami() {
  if (!identity) {
    const data = await api('auth.test');
    identity = { team: data.team_id || null, botUserId: data.user_id || null, botId: data.bot_id || null };
  }
  return identity;
}

function sender(as) {
  const out = {};
  if (typeof as?.name === 'string' && as.name.trim()) out.username = as.name.trim();
  const avatar = typeof as?.avatar === 'string' ? as.avatar.trim() : '';
  if (/^:[^:\s]+:$/.test(avatar)) out.icon_emoji = avatar;
  else if (/^https?:\/\/\S+$/i.test(avatar)) out.icon_url = avatar;
  return out;
}

function address(value) {
  const id = String(value || '').trim();
  if (/^[UW][A-Z0-9]+$/.test(id)) return { contact: id };
  if (/^[CGD][A-Z0-9]+$/.test(id)) return { group: id };
  throw fail('address', `slack addresses are a user id (U...) or a channel id (C...); ${id.includes('@') ? 'a mail address is google\'s' : `${id} is neither`}`);
}

async function conversationOf({ group, contact }) {
  if (group) return group;
  if (!contact) throw fail(null, 'slack needs a group or a contact');
  const data = await api('conversations.open', { users: contact });
  if (!data.channel?.id) throw fail(null, 'slack answered no channel for conversations.open');
  return data.channel.id;
}

// The root of the thread a message id names: the id itself when it is a root, else the thread_ts of the reply it
// names. One conversations.replies call on that id alone; a thread Slack does not find fails with code 'thread'.
async function rootOf(conversation, ts) {
  const data = await api('conversations.replies', { channel: conversation, ts, limit: 1 });
  const first = (data.messages || [])[0];
  if (!first) throw fail('thread', `slack answered no message for ${ts} in ${conversation}`, 'thread_not_found');
  return first.thread_ts || first.ts;
}

function fileRef(file) {
  if (!file?.id) return null;
  return { id: file.id, ...(file.name ? { name: file.name } : {}), ...(file.mimetype ? { mimetype: file.mimetype } : {}) };
}

function event(message, conversation, who) {
  const ts = message.ts;
  const thread = message.thread_ts && message.thread_ts !== ts ? message.thread_ts : null;
  const direct = message.channel_type === 'im' || /^D/.test(conversation);
  return {
    connector: 'slack',
    account: who.team,
    id: ts,
    at: Math.round(Number(ts) * 1000),
    from: message.user || message.bot_id || '',
    group: direct ? null : conversation,
    conversation,
    thread,
    text: message.text || '',
    files: Array.isArray(message.files) ? message.files.map(fileRef).filter(Boolean) : [],
    isSelf: Boolean((who.botUserId && message.user === who.botUserId) || (who.botId && message.bot_id === who.botId) || SELF_SUBTYPES.has(message.subtype)),
    raw: message,
  };
}

const operations = {
  async 'message.send'({ group, contact, thread, text, as, clientId }) {
    if (typeof text !== 'string' || !text.trim()) throw fail(null, 'slack answered no_text: the message is empty');
    const channel = await conversationOf({ group, contact });
    const root = thread ? await rootOf(channel, thread) : null;
    const data = await api('chat.postMessage', {
      channel, markdown_text: text, ...(root ? { thread_ts: root } : {}), ...(clientId ? { client_msg_id: clientId } : {}), ...sender(as),
    });
    return { conversation: data.channel || channel, id: data.ts, thread: root };
  },

  async 'message.file'({ send } = {}) {
    if (!send?.file) throw fail(null, 'slack needs a file to send');
    const channel = await conversationOf({ group: send.conversation, contact: send.contact });
    const root = send.thread ? await rootOf(channel, send.thread) : null;
    const stat = fs.statSync(send.file);
    if (!stat.isFile() || stat.size === 0) throw fail(null, `slack cannot send ${send.file}: not a file, or empty`);
    const filename = path.basename(send.file);
    const granted = await api('files.getUploadURLExternal', { filename, length: stat.size });
    if (!granted.upload_url || !granted.file_id) throw fail(null, 'slack answered no upload_url');
    const put = await fetch(granted.upload_url, { method: 'POST', headers: { 'content-type': 'application/octet-stream' }, body: fs.readFileSync(send.file) });
    if (!put.ok) throw fail(null, `slack answered HTTP ${put.status} on the file upload`);
    const done = await api('files.completeUploadExternal', {
      files: [{ id: granted.file_id, title: filename }], channel_id: channel, ...(root ? { thread_ts: root } : {}), ...sender(send.as),
    });
    const uploaded = (done.files || [])[0] || {};
    let id = null;
    for (const scope of Object.values(uploaded.shares || {})) {
      const rows = scope?.[channel] || Object.values(scope || {})[0] || [];
      if (rows[0]?.ts) { id = rows[0].ts; break; }
    }
    if (!id) throw fail(null, 'slack answered no message for the uploaded file');
    return { id, conversation: channel, thread: root };
  },

  async 'message.history'({ conversation, thread } = {}) {
    if (!conversation || !thread) throw fail(null, 'slack needs the conversation and the thread');
    const who = await whoami();
    const read = async (ts) => {
      const messages = [];
      let cursor = null;
      do {
        const data = await api('conversations.replies', { channel: conversation, ts, limit: 200, ...(cursor ? { cursor } : {}) });
        messages.push(...(data.messages || []));
        cursor = data.response_metadata?.next_cursor || null;
      } while (cursor);
      return messages;
    };
    const messages = await read(await rootOf(conversation, thread));
    const events = messages.map((m) => event(m, conversation, who)).sort((a, b) => String(a.id).localeCompare(String(b.id)));
    return { events };
  },
};

operations['message.react'] = async ({ conversation, id, name, add = true } = {}) => {
  if (!conversation || !id || !name) throw fail(null, 'slack needs the conversation, the message id and the reaction name');
  await api(add ? 'reactions.add' : 'reactions.remove', { channel: conversation, timestamp: id, name });
  return {};
};

operations['group.manage'] = async (input = {}) => {
  if (input.create) {
    const data = await api('conversations.create', { name: input.create.name, is_private: false });
    if (!data.channel?.id) throw fail(null, 'slack answered no channel for conversations.create');
    return { group: data.channel.id };
  }
  if (input.join) { await api('conversations.join', { channel: input.join.group }); return { group: input.join.group }; }
  if (input.invite) { await api('conversations.invite', { channel: input.invite.group, users: input.invite.contact }); return { group: input.invite.group }; }
  if (input.archive) { await api('conversations.archive', { channel: input.archive.group }); return { group: input.archive.group }; }
  throw fail(null, 'slack needs one of create, join, invite or archive');
};

operations['approval.secure'] = async (input = {}) => {
  if (input.post) {
    const { conversation, thread, text, blocks } = input.post;
    const data = await api('chat.postMessage', { channel: conversation, text, blocks, ...(thread ? { thread_ts: thread } : {}) });
    return { conversation: data.channel || conversation, id: data.ts };
  }
  if (input.update) {
    const { conversation, id, text, blocks } = input.update;
    const data = await api('chat.update', { channel: conversation, ts: id, text, blocks });
    return { conversation: data.channel || conversation, id: data.ts || id };
  }
  if (input.whisper) { await api('chat.postEphemeral', { channel: input.whisper.conversation, user: input.whisper.contact, text: input.whisper.text }); return {}; }
  if (input.open) { await api('views.open', { trigger_id: input.open.trigger, view: input.open.view }); return {}; }
  if (input.push) { await api('views.push', { trigger_id: input.push.trigger, view: input.push.view }); return {}; }
  if (input.change) { await api('views.update', { view_id: input.change.viewId, view: input.change.view }); return {}; }
  throw fail(null, 'slack needs one of post, update, whisper, open, push or change');
};

operations['message.receive'] = async () => {
  throw fail(null, "slack: message.receive is delivered by Ignite's own Slack client until phase 4 of the connector architecture moves the listener onto this adapter");
};

module.exports = { operations, address, account: async () => (await whoami()).team, TOKEN_ENV };
