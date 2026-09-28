'use strict';

// Exported API — other seats treat this file as read-only.
// Slack({ botToken, appToken?, workspace?, toolsWrapper?, python?, fetch?, WebSocket?, run?, schedule?, cancel?, log? })
// auth() → { team, botUserId, botId }
// normalize(event, { team, botUserId, botId }) →
//   { team, channel, channelType, ts, threadTs, user, text, files, isBotOrSelf, mentionsBot }
//   throws unless botUserId and botId are both set. mentionsBot: <@botUserId> outside `code`
//   and ```fences```. isBotOrSelf: user === botUserId, OR bot_id === botId (a different bot_id
//   is not self), OR subtype message_changed / message_deleted / channel_join / group_join.
// connect(onEvent): Socket Mode via app token. ACK only after onEvent resolves; no ACK if it
//   rejects. Backoff 1s→60s, reset only on hello. disconnect envelopes close and reconnect.
// postMessage({ channel, threadTs?, text, clientMsgId? }) → { channel, ts }  (mrkdwn: true)
// addReaction(channel, ts) → reactions.add name=eyes
// threadHistory(channel, threadTs) → normalized messages, oldest first (conversations.replies)
// createChannel(name) → { id, name }
// joinChannel(id) → { id }   (already_in_channel is success)
// inviteUser(id, userId) → { id }   (already_in_channel is success)
// archiveChannel(id)   (already_archived is success)
// uploadFile({ channel, threadTs?, file, text? }) → { ts, files }
//   files.getUploadURLExternal + POST bytes + files.completeUploadExternal (returns message ts;
//   stools upload does not).
// downloadFile({ channel, ts, threadTs?, dir }) → [{ path, name }]  via stools download
// canvasCreate({ channel, markdown, title? }) → { canvasId }   bot token, conversations.canvases.create
// canvasEdit({ canvasId, markdown, operation? }) → { canvasId }   bot token, canvases.edit
// stop()

const fs = require('node:fs/promises');
const path = require('node:path');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');

const SELF_SUBTYPES = new Set(['message_changed', 'message_deleted', 'channel_join', 'group_join']);
const API = 'https://slack.com/api';

function escapeReg(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function stripCode(text) {
  return String(text || '').replace(/```[\s\S]*?```/g, ' ').replace(/`[^`]*`/g, ' ');
}

function mentionsBot(text, botUserId) {
  if (!botUserId) return false;
  return new RegExp(`<@${escapeReg(botUserId)}(?:\\|[^>]*)?>`).test(stripCode(text));
}

function fileRef(file) {
  if (!file || typeof file !== 'object') return null;
  return {
    id: file.id || null,
    name: file.name || null,
    mimetype: file.mimetype || null,
    filetype: file.filetype || null,
  };
}

function normalize(event, identity, extra = {}) {
  if (!identity?.botUserId || !identity?.botId) {
    throw new Error('normalize requires botUserId and botId');
  }
  const botUserId = identity.botUserId;
  const botId = identity.botId;
  const files = Array.isArray(event?.files) ? event.files.map(fileRef).filter(Boolean) : [];
  const ts = event?.ts || null;
  return {
    team: identity.team || event?.team || null,
    channel: event?.channel || extra.channel || null,
    channelType: event?.channel_type || extra.channelType || null,
    ts,
    threadTs: event?.thread_ts || ts,
    user: event?.user || null,
    text: event?.text || '',
    files,
    isBotOrSelf: Boolean(
      (botUserId && event?.user === botUserId) ||
      (botId && event?.bot_id === botId) ||
      SELF_SUBTYPES.has(event?.subtype)
    ),
    mentionsBot: mentionsBot(event?.text, botUserId),
  };
}

function shareTs(file, channel) {
  const shares = file?.shares || {};
  for (const scope of Object.values(shares)) {
    const rows = (channel && scope?.[channel]) || [];
    if (rows[0]?.ts) return rows[0].ts;
    for (const list of Object.values(scope || {})) {
      if (Array.isArray(list) && list[0]?.ts) return list[0].ts;
    }
  }
  return null;
}

function downloadPaths(stdout, dir) {
  const found = [];
  for (const line of String(stdout || '').split('\n')) {
    const match = line.match(/^\[\d+\/\d+\]\s+(?:\[IMG\]\s+)?(.+?)\s+\(/);
    if (!match) continue;
    const name = match[1];
    const image = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico'].includes(path.extname(name).toLowerCase());
    found.push({ name, path: image ? path.join(dir, '_images', name) : path.join(dir, name) });
  }
  return found;
}

class Slack {
  constructor(config = {}) {
    if (!config.botToken) throw new Error('Slack requires botToken');
    this.config = config;
    this.fetch = config.fetch || globalThis.fetch;
    this.WebSocket = config.WebSocket || globalThis.WebSocket;
    this.run = config.run || promisify(execFile);
    this.schedule = config.schedule || setTimeout;
    this.cancel = config.cancel || clearTimeout;
    this.log = config.log || (() => {});
    this.socket = null;
    this.stopped = false;
    this.retryTimer = null;
    this.retryMs = 1000;
    this.identity = null;
    this.pending = Promise.resolve();
    this.onEvent = null;
  }

  async api(method, body = {}, token = this.config.botToken) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(body)) {
      if (value == null) continue;
      params.set(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
    }
    const response = await this.fetch(`${this.config.apiBase || API}/${method}`, {
      method: 'POST',
      headers: {
        authorization: `Bearer ${token}`,
        'content-type': 'application/x-www-form-urlencoded',
      },
      body: params.toString(),
    });
    if (!response.ok) throw new Error(`Slack ${method}: HTTP ${response.status}`);
    const data = await response.json();
    if (!data.ok) throw new Error(`Slack ${method}: ${data.error || 'unknown_error'}`);
    return data;
  }

  tolerated(error, code) {
    return String(error?.message || '').endsWith(code);
  }

  async auth() {
    const data = await this.api('auth.test');
    if (!data.user_id || !data.bot_id) throw new Error('Slack auth.test returned no user_id or bot_id');
    this.identity = { team: data.team_id || null, botUserId: data.user_id, botId: data.bot_id };
    return this.identity;
  }

  normalize(event) {
    return normalize(event, this.identity);
  }

  async postMessage({ channel, threadTs, text, clientMsgId } = {}) {
    if (!channel) throw new Error('postMessage requires channel');
    const data = await this.api('chat.postMessage', {
      channel,
      text: text || '',
      mrkdwn: true,
      ...(threadTs ? { thread_ts: threadTs } : {}),
      ...(clientMsgId ? { client_msg_id: clientMsgId } : {}),
    });
    return { channel: data.channel || channel, ts: data.ts };
  }

  async addReaction(channel, ts) {
    if (!channel || !ts) throw new Error('addReaction requires channel and ts');
    return this.api('reactions.add', { channel, timestamp: ts, name: 'eyes' });
  }

  async threadHistory(channel, threadTs) {
    if (!channel || !threadTs) throw new Error('threadHistory requires channel and threadTs');
    if (!this.identity) await this.auth();
    const messages = [];
    let cursor;
    const seen = new Set();
    do {
      const data = await this.api('conversations.replies', {
        channel,
        ts: threadTs,
        limit: 200,
        ...(cursor ? { cursor } : {}),
      });
      messages.push(...(data.messages || []));
      cursor = data.response_metadata?.next_cursor || null;
      if (cursor && seen.has(cursor)) break;
      if (cursor) seen.add(cursor);
    } while (cursor);
    return messages
      .map((message) => normalize({ ...message, channel: message.channel || channel }, this.identity))
      .sort((a, b) => String(a.ts).localeCompare(String(b.ts)));
  }

  async createChannel(name) {
    if (!name) throw new Error('createChannel requires name');
    const data = await this.api('conversations.create', { name });
    return { id: data.channel?.id, name: data.channel?.name || name };
  }

  async joinChannel(channel) {
    if (!channel) throw new Error('joinChannel requires channel');
    try {
      const data = await this.api('conversations.join', { channel });
      return { id: data.channel?.id || channel };
    } catch (error) {
      if (this.tolerated(error, 'already_in_channel')) return { id: channel };
      throw error;
    }
  }

  async inviteUser(channel, user) {
    if (!channel || !user) throw new Error('inviteUser requires channel and user');
    try {
      const data = await this.api('conversations.invite', { channel, users: user });
      return { id: data.channel?.id || channel };
    } catch (error) {
      if (this.tolerated(error, 'already_in_channel')) return { id: channel };
      throw error;
    }
  }

  async archiveChannel(channel) {
    if (!channel) throw new Error('archiveChannel requires channel');
    try {
      return await this.api('conversations.archive', { channel });
    } catch (error) {
      if (this.tolerated(error, 'already_archived')) return { ok: true, already_archived: true };
      throw error;
    }
  }

  async stools(...args) {
    if (!this.config.toolsWrapper) throw new Error('Slack requires toolsWrapper');
    if (!this.config.workspace) throw new Error('Slack requires workspace');
    const { stdout } = await this.run(this.config.python || 'python3', [
      this.config.toolsWrapper, ...args, '--workspace', this.config.workspace,
    ], { maxBuffer: 8 * 1024 * 1024 });
    return stdout;
  }

  async downloadFile({ channel, ts, threadTs, dir } = {}) {
    if (!channel || !ts) throw new Error('downloadFile needs channel and ts');
    if (!dir) throw new Error('downloadFile needs dir');
    await fs.mkdir(dir, { recursive: true });
    const stdout = await this.stools('download', '--channel', channel, '--ts', ts,
      ...(threadTs ? ['--thread-ts', threadTs] : []), '--output', dir);
    return downloadPaths(stdout, dir);
  }

  async uploadFile({ channel, threadTs, file, text } = {}) {
    if (!channel || !file) throw new Error('uploadFile requires channel and file');
    const stat = await fs.stat(file);
    if (!stat.isFile() || stat.size === 0) throw new Error('uploadFile requires a non-empty file');
    const filename = path.basename(file);
    const granted = await this.api('files.getUploadURLExternal', { filename, length: stat.size });
    if (!granted.upload_url || !granted.file_id) throw new Error('Slack files.getUploadURLExternal returned no upload_url');
    const bytes = await fs.readFile(file);
    const put = await this.fetch(granted.upload_url, {
      method: 'POST',
      headers: { 'content-type': 'application/octet-stream' },
      body: bytes,
    });
    if (!put.ok) throw new Error(`Slack file upload: HTTP ${put.status}`);
    const done = await this.api('files.completeUploadExternal', {
      files: [{ id: granted.file_id, title: filename }],
      channel_id: channel,
      ...(threadTs ? { thread_ts: threadTs } : {}),
      ...(text ? { initial_comment: text } : {}),
    });
    const uploaded = (done.files || [])[0] || {};
    return {
      ts: shareTs(uploaded, channel),
      files: [{ id: uploaded.id || granted.file_id, name: uploaded.name || filename }],
    };
  }

  async canvasCreate({ channel, markdown, title } = {}) {
    if (!channel || !markdown) throw new Error('canvasCreate requires channel and markdown');
    const data = await this.api('conversations.canvases.create', {
      channel_id: channel,
      document_content: { type: 'markdown', markdown },
      ...(title ? { title } : {}),
    });
    if (!data.canvas_id) throw new Error('Slack conversations.canvases.create returned no canvas_id');
    return { canvasId: data.canvas_id };
  }

  async canvasEdit({ canvasId, markdown, operation = 'replace' } = {}) {
    if (!canvasId || !markdown) throw new Error('canvasEdit requires canvasId and markdown');
    await this.api('canvases.edit', {
      canvas_id: canvasId,
      changes: [{ operation, document_content: { type: 'markdown', markdown } }],
    });
    return { canvasId };
  }

  async connect(onEvent) {
    if (typeof onEvent !== 'function') throw new Error('connect requires onEvent');
    if (!this.config.appToken) throw new Error('connect requires appToken');
    if (!this.WebSocket) throw new Error('WebSocket is unavailable');
    this.stopped = false;
    this.onEvent = onEvent;
    await this.auth();
    await this.openSocket();
  }

  async openSocket() {
    const data = await this.api('apps.connections.open', {}, this.config.appToken);
    if (!data.url) throw new Error('Slack Socket Mode returned no URL');
    const socket = new this.WebSocket(data.url);
    this.socket = socket;
    socket.addEventListener('message', (event) => {
      const job = this.handleFrame(event.data, socket);
      this.pending = job.catch((error) => this.log('error', error.message));
    });
    socket.addEventListener('close', () => {
      if (!this.stopped && this.socket === socket) this.reconnect();
    });
    socket.addEventListener('error', (error) => this.log('warn', error?.message || 'socket error'));
  }

  async handleFrame(raw, socket) {
    let envelope;
    try { envelope = JSON.parse(String(raw)); } catch { return; }
    if (envelope.type === 'disconnect') {
      socket.close();
      return;
    }
    if (envelope.type === 'hello') {
      this.retryMs = 1000;
      return;
    }
    const event = envelope.payload?.event;
    const deliver = envelope.type === 'events_api' && event &&
      (event.type === 'message' || event.type === 'app_mention');
    if (deliver) await this.onEvent(normalize(event, this.identity));
    if (envelope.envelope_id && socket === this.socket && !socket.closed) {
      socket.send(JSON.stringify({ envelope_id: envelope.envelope_id }));
    }
  }

  reconnect() {
    if (this.stopped || this.retryTimer) return;
    const delay = this.retryMs;
    this.retryMs = Math.min(delay * 2, 60000);
    this.retryTimer = this.schedule(() => {
      this.retryTimer = null;
      if (this.stopped) return;
      this.openSocket().catch((error) => {
        this.log('warn', `Slack reconnect failed: ${error.message}`);
        this.reconnect();
      });
    }, delay);
  }

  stop() {
    this.stopped = true;
    if (this.retryTimer) this.cancel(this.retryTimer);
    this.retryTimer = null;
    if (this.socket) this.socket.close();
    this.socket = null;
  }
}

module.exports = { Slack, normalize };
