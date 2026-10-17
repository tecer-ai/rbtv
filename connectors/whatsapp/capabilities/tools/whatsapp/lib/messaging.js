'use strict';

// WhatsApp messaging adapter. Inbound is a localhost receiver. Ignite starts
// `whatsapp sync --follow` on the installation store and points it at that receiver.
// wacli signs the body with HMAC-SHA256 in X-Wacli-Signature. A missing or wrong
// signature is refused before dispatch. The owner is the configured phone, never a body field.
// The linked session is `wacli auth status`: its phone must match the configured account.

const http = require('node:http');
const crypto = require('node:crypto');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { spawnable } = require('../../../../../../core/cast/capabilities/tools/cast/lib/win-exec');

const HEADER = 'x-wacli-signature';
const HOST = '127.0.0.1';
const MAX_BODY = 64 * 1024;
const COMMAND_MS = 60_000;
const READY_MS = 15_000;
const HISTORY_PAGE = 200;
const HISTORY_MAX_PAGES = 25;
const RESTART_MS = 2_000;

function fail(reason, message) {
  const error = new Error(message);
  if (reason) error.reason = reason;
  return error;
}

function digits(value) {
  return String(value || '').split('@')[0].replace(/\D/g, '');
}

function same(given, wanted) {
  const a = Buffer.from(String(given ?? ''), 'utf8');
  const b = Buffer.from(String(wanted), 'utf8');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function signature(secret, body) {
  return crypto.createHmac('sha256', secret).update(body).digest('hex');
}

function signed(secret, header, body) {
  if (!secret || !header) return false;
  const given = String(header).trim().replace(/^sha256=/i, '');
  return same(given, signature(secret, body));
}

function launch(args, spawnImpl, extra = {}) {
  if (typeof spawnImpl === 'function' && spawnImpl !== spawn) {
    return spawnImpl('whatsapp', args, { stdio: ['ignore', 'pipe', 'pipe'], ...extra });
  }
  const win = spawnable('whatsapp', args);
  return spawn(win.cmd, win.args, { stdio: ['ignore', 'pipe', 'pipe'], ...win.opts, ...extra });
}

function run(args, spawnImpl) {
  return new Promise((resolve, reject) => {
    const child = launch(args, spawnImpl);
    let out = '';
    let err = '';
    const timer = setTimeout(() => {
      child.kill();
      reject(fail(null, 'whatsapp command timed out'));
    }, COMMAND_MS);
    child.stdout.on('data', (chunk) => { out += chunk; });
    child.stderr.on('data', (chunk) => { err += chunk; });
    child.on('error', (error) => { clearTimeout(timer); reject(error); });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (code !== 0) reject(fail(null, `whatsapp answered ${(err || out).trim() || `exit ${code}`}`));
      else resolve(out);
    });
  });
}

function envelope(text) {
  const body = JSON.parse(text);
  if (body.success === false) throw fail(null, `whatsapp answered ${body.error || 'error'}`);
  return body.data && typeof body.data === 'object' ? body.data : body;
}

function storeOf(ctx = {}) {
  if (ctx.store) return ctx.store;
  const root = ctx.installation || ctx.workspace;
  if (!root) return null;
  return path.join(root, '.rbtv', 'runtime', 'whatsapp');
}

function globalArgs(ctx) {
  const store = storeOf(ctx);
  return store ? ['--store', store] : [];
}

function jidOf(value) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (typeof value.String === 'function') return value.String();
  if (value.User && value.Server) return `${value.User}@${value.Server}`;
  return String(value);
}

function payloadOf(body) {
  const parsed = JSON.parse(body.toString('utf8'));
  if (parsed.EventType && parsed.EventType !== 'message') return { ignore: true };
  const message = parsed.Message && typeof parsed.Message === 'object' ? parsed.Message : parsed;
  const chat = jidOf(message.Chat || message.ChatJID || message.chat);
  const id = message.ID || message.MsgID || message.id || null;
  const reply = message.ReplyToID || message.quoted_msg_id || null;
  return {
    id: id ? String(id) : null,
    chat: chat || null,
    sender: jidOf(message.SenderJID || message.sender) || '',
    text: message.Text || message.text || '',
    fromMe: Boolean(message.FromMe || message.from_me),
    at: Date.parse(message.Timestamp) || Number(message.timestamp) || Date.now(),
    replyTo: reply ? String(reply) : null,
  };
}

function eventOf(fields, { owner, account }) {
  const sender = digits(fields.sender);
  const ownerDigits = digits(owner);
  const group = fields.chat && String(fields.chat).includes('@g.us') ? fields.chat : null;
  const at = Number(fields.at) || Date.now();
  return {
    connector: 'whatsapp',
    account,
    id: String(fields.id),
    at: at > 1e12 ? at : at * 1000,
    from: sender || String(fields.sender || ''),
    claimedFrom: sender || String(fields.sender || ''),
    group,
    conversation: fields.chat,
    thread: fields.replyTo || null,
    text: fields.text || '',
    files: [],
    isSelf: fields.fromMe || sender === digits(account),
    identity: {
      verified: true,
      method: 'webhook-secret',
      owner: Boolean(ownerDigits) && sender === ownerDigits && !fields.fromMe,
      claimed: sender || String(fields.sender || ''),
    },
  };
}

function listen({ secret, owner, account, port = 8791, onEvent, onReject, host = HOST } = {}) {
  if (host !== HOST) throw new Error('the WhatsApp receiver listens on 127.0.0.1 only');
  if (!secret) throw new Error('webhook secret is not configured');
  if (!owner || !account) throw new Error('owner identity is not configured');
  const server = http.createServer((req, res) => {
    const done = (status, body) => {
      if (res.writableEnded) return;
      const data = JSON.stringify(body);
      res.writeHead(status, { 'content-type': 'application/json', 'content-length': Buffer.byteLength(data) });
      res.end(data);
    };
    if (req.url.split('?')[0] !== '/whatsapp') return done(404, { error: 'not found' });
    if (req.method !== 'POST') return done(405, { error: 'POST only' });
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY) req.destroy();
      else chunks.push(chunk);
    });
    req.on('end', () => {
      const raw = Buffer.concat(chunks);
      if (!signed(secret, req.headers[HEADER], raw)) {
        if (typeof onReject === 'function') onReject({ reason: 'unverified', connector: 'whatsapp' });
        return done(401, { error: 'unverified' });
      }
      let fields;
      try { fields = payloadOf(raw); } catch {
        return done(400, { error: 'bad json' });
      }
      if (fields.ignore) return done(200, { ok: true });
      if (!fields.id || !fields.chat) return done(400, { error: 'id and chat required' });
      const event = eventOf(fields, { owner, account });
      Promise.resolve(typeof onEvent === 'function' ? onEvent(event) : null)
        .then(() => done(200, { ok: true }))
        .catch((error) => done(500, { error: error.message }));
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, () => resolve({
      port: server.address().port,
      close: () => new Promise((done) => server.close(() => done())),
    }));
  });
}

async function sessionStatus(ctx = {}) {
  const store = storeOf(ctx);
  if (!store) throw new Error('the connector did not confirm its account identity');
  const out = await run([...globalArgs(ctx), '--json', '--read-only', 'auth', 'status'], ctx.spawn);
  const data = envelope(out);
  return data;
}

async function account(ctx = {}) {
  const wanted = ctx.account || ctx.section?.account;
  if (!wanted) throw new Error('the connector did not confirm its account identity');
  const status = await sessionStatus({ ...ctx, account: wanted, section: ctx.section });
  const phone = status.phone || digits(status.linked_jid);
  if (!status.authenticated || !phone || digits(phone) !== digits(wanted)) {
    throw new Error('the connector did not confirm its account identity');
  }
  return digits(wanted);
}

function address(value) {
  const text = String(value || '');
  if (/@g\.us$/.test(text)) return { group: text };
  if (/^\d{8,15}$/.test(digits(text)) && !text.includes('@')) return { contact: digits(text) };
  const error = new Error('whatsapp addresses are a number with country code or a group id ending @g.us');
  error.code = 'address';
  throw error;
}

function confirmed(data, to, thread) {
  const id = data.id || data.MsgID;
  if (!id) throw fail(null, 'whatsapp did not confirm the message');
  return { conversation: data.to || data.ChatJID || to, id: String(id), thread: thread || null };
}

function supervise({ store, secret, port, account, spawn: spawnImpl, onLog, onState } = {}) {
  if (!store || !secret || !port || !account) throw new Error('owner identity is not configured');
  let child = null;
  let stopping = false;
  let timer = null;
  let state = 'starting';
  let stableTimer = null;
  let readyResolve = null;
  const ready = new Promise((resolve) => { readyResolve = resolve; });
  const log = (reason) => { if (typeof onLog === 'function') onLog(reason); };
  const settle = (next) => {
    if (state === next) return;
    state = next;
    if (typeof onState === 'function') onState(next);
    if (next === 'ready' || next === 'failed' || next === 'stopped') readyResolve();
  };
  const args = ['--store', store, '--events', 'sync', '--follow', '--webhook', `http://${HOST}:${port}/whatsapp`, '--webhook-secret', secret, '--webhook-allow-private'];
  function killTree(signal = 'SIGTERM') {
    if (!child?.pid) return;
    try {
      if (process.platform === 'win32') child.kill(signal);
      else process.kill(-child.pid, signal); // the wrapper leads its own group, so wacli dies with it
    } catch { /* already gone */ }
  }
  function startChild() {
    settle('starting');
    // The session is revalidated on every (re)start: a respawn after the store's account changed must
    // not deliver events for the configured account from another session.
    sessionStatus({ store, spawn: spawnImpl }).then((status) => {
      const phone = status.phone || digits(status.linked_jid);
      if (!status.authenticated || !phone || digits(phone) !== digits(account)) {
        throw new Error('whatsapp session does not match the configured account');
      }
      if (!stopping) spawnSync();
    }, (error) => {
      if (stopping) return;
      log(`whatsapp session could not be confirmed: ${error.message}`);
      scheduleRestart();
    }).catch((error) => {
      // An account mismatch is permanent: never supervise another account's session.
      log(error.message);
      settle('failed');
    });
  }
  function spawnSync() {
    child = launch(args, spawnImpl, { detached: process.platform !== 'win32' });
    let err = '';
    child.stderr.on('data', (chunk) => {
      err = (err + chunk).slice(-4096);
      for (const line of String(chunk).split(/\r?\n/)) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event.event === 'connected') settle('ready');
          if (event.event === 'logged_out') log('whatsapp session logged out');
        } catch { /* not a lifecycle event line */ }
      }
    });
    child.stdout.on('data', () => {});
    child.on('error', (error) => {
      child = null;
      if (stopping) return;
      log(`whatsapp sync did not start: ${error.message}`);
      scheduleRestart();
    });
    child.on('exit', (code) => {
      child = null;
      if (stableTimer) clearTimeout(stableTimer);
      if (stopping) return;
      log(`whatsapp sync exited ${code}${err ? `: ${err.trim().split(/\r?\n/).pop()}` : ''}`);
      scheduleRestart();
    });
    // wacli reports readiness as an NDJSON lifecycle event; a process still alive past this window is
    // treated as running (connected or reconnecting), never as failed.
    stableTimer = setTimeout(() => { if (child && !stopping) settle('ready'); }, READY_MS);
    if (typeof stableTimer.unref === 'function') stableTimer.unref();
  }
  function scheduleRestart() {
    settle('failed');
    if (stopping) return;
    if (timer) clearTimeout(timer);
    timer = setTimeout(startChild, RESTART_MS);
    if (typeof timer.unref === 'function') timer.unref();
  }
  startChild();
  return {
    whenReady: () => ready,
    state: () => state,
    async stop() {
      stopping = true;
      settle('stopped');
      if (timer) clearTimeout(timer);
      if (stableTimer) clearTimeout(stableTimer);
      if (!child) return;
      const drained = new Promise((resolve) => { child.once('exit', () => resolve()); });
      killTree('SIGTERM');
      const force = setTimeout(() => killTree('SIGKILL'), READY_MS);
      if (typeof force.unref === 'function') force.unref();
      await Promise.race([drained, new Promise((resolve) => setTimeout(resolve, READY_MS))]);
      clearTimeout(force);
    },
  };
}

// One page of a chat's messages, newest first, older than beforeSecond (a unix second, re-included
// whole: wacli's --before is exclusive and one second can hold several messages).
async function historyPage(conversation, beforeSecond, ctx) {
  const args = [...globalArgs(ctx), '--json', 'messages', 'list', '--chat', conversation, '--limit', String(HISTORY_PAGE)];
  if (beforeSecond != null) args.push('--before', new Date((beforeSecond + 1) * 1000).toISOString());
  const data = envelope(await run(args, ctx.spawn));
  return Array.isArray(data.messages) ? data.messages : [];
}

const secondOf = (row) => {
  const ms = Date.parse(row.Timestamp);
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null;
};

// The root of the reply chain the id belongs to, or null while ancestry continues past what is fetched.
function rootOf(rows, id) {
  let current = rows.get(String(id));
  if (!current) return null;
  const walked = new Set([String(id)]);
  while (current.quoted_msg_id && !walked.has(String(current.quoted_msg_id))) {
    const parent = rows.get(String(current.quoted_msg_id));
    if (!parent) return null;
    walked.add(String(parent.MsgID));
    current = parent;
  }
  return current;
}

// The chat's messages this history needs, paged newest-first until the thread's root and everything
// down to it is in hand (a root older than one page is reachable), bounded by HISTORY_MAX_PAGES.
async function chatHistory(conversation, thread, ctx) {
  const rows = new Map();
  let before = null;
  for (let page = 0; page < HISTORY_MAX_PAGES; page += 1) {
    const batch = await historyPage(conversation, before, ctx);
    if (!batch.length) break;
    let fresh = 0;
    for (const row of batch) {
      if (row.MsgID == null || rows.has(String(row.MsgID))) continue;
      rows.set(String(row.MsgID), row);
      fresh += 1;
    }
    const oldest = Math.min(...batch.map(secondOf).filter((value) => value != null));
    if (!Number.isFinite(oldest)) break; // no row names a time the next page could page from
    if (thread) {
      const root = rootOf(rows, thread);
      if (root && oldest <= secondOf(root)) break;
    }
    if (!fresh) break; // no progress: one second holds more than a page
    before = oldest;
  }
  return rows;
}

function historyEvents(conversation, thread, rows, ctx) {
  const owner = ctx.owner || ctx.section?.owner || '';
  const account = ctx.account || '';
  const event = (row) => eventOf({
    id: row.MsgID, chat: row.ChatJID || conversation, sender: row.SenderJID || '', text: row.Text || '',
    fromMe: row.FromMe, at: Date.parse(row.Timestamp) || Date.now(), replyTo: row.quoted_msg_id || null,
  }, { owner, account });
  if (!thread) {
    // The whole chat, oldest first (wacli pages newest first; one Map keeps first-seen order).
    return [...rows.values()].map(event).sort((a, b) => a.at - b.at || (a.id < b.id ? -1 : 1));
  }
  const root = rootOf(rows, thread);
  if (!root) {
    const error = fail(null, `whatsapp answered thread_not_found for ${thread} in ${conversation}`);
    error.code = 'thread';
    throw error;
  }
  // The connected reply tree: the root and every message whose reply chain reaches it, oldest first
  // (a tie keeps a parent before its child).
  const children = new Map();
  for (const row of rows.values()) {
    const parent = row.quoted_msg_id ? String(row.quoted_msg_id) : null;
    if (!parent || !rows.has(parent)) continue;
    if (!children.has(parent)) children.set(parent, []);
    children.get(parent).push(row);
  }
  const depth = new Map([[String(root.MsgID), 0]]);
  const kept = [root];
  for (let at = 0; at < kept.length; at += 1) {
    const current = kept[at];
    for (const child of children.get(String(current.MsgID)) || []) {
      if (depth.has(String(child.MsgID))) continue;
      depth.set(String(child.MsgID), depth.get(String(current.MsgID)) + 1);
      kept.push(child);
    }
  }
  return kept.map(event).sort((a, b) => a.at - b.at || depth.get(a.id) - depth.get(b.id));
}

const operations = {
  async 'message.send'({ group, contact, thread, text } = {}, ctx = {}) {
    const to = group || contact;
    if (!to || !text) throw fail(null, 'whatsapp answered no_text: the message is empty');
    await account(ctx);
    const args = [...globalArgs(ctx), '--json', 'send', 'text', '--to', to, '--message', text];
    if (thread) args.push('--reply-to', thread);
    const data = envelope(await run(args, ctx.spawn));
    return confirmed(data, to, thread || null);
  },
  async 'message.file'({ send } = {}, ctx = {}) {
    if (!send?.file) throw fail(null, 'whatsapp needs a file to send');
    const to = send.conversation || send.contact;
    await account(ctx);
    const args = [...globalArgs(ctx), '--json', 'send', 'file', '--to', to, '--file', send.file];
    if (send.thread) args.push('--reply-to', send.thread);
    const data = envelope(await run(args, ctx.spawn));
    if (!data.id) throw fail(null, 'whatsapp did not confirm the file');
    return { id: String(data.id), conversation: data.to || to, thread: send.thread || null };
  },
  async 'message.history'({ conversation, thread } = {}, ctx = {}) {
    if (!conversation) return { events: [] };
    await account(ctx);
    const rows = await chatHistory(conversation, thread || null, ctx);
    return { events: historyEvents(conversation, thread || null, rows, ctx) };
  },
  async 'message.receive'({ onEvent, secret, owner, account: linked, port, installation, spawn: spawnImpl } = {}) {
    const listening = await listen({ secret, owner, account: linked, port, onEvent });
    const store = storeOf({ installation, account: linked });
    const sync = store ? supervise({ store, secret, port: listening.port, account: linked, spawn: spawnImpl }) : null;
    return { stop: async () => { if (sync) await sync.stop(); await listening.close(); } };
  },
};

module.exports = {
  operations, address, account, listen, signed, signature, eventOf, payloadOf, supervise, sessionStatus, HEADER, HOST,
};
