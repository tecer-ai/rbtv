'use strict';

// WhatsApp messaging adapter. Inbound is a localhost receiver: wacli sync --webhook posts JSON signed
// with HMAC-SHA256 in X-Wacli-Signature (wacli sync --help). A missing or wrong signature is refused
// before any event is dispatched. The owner is the configured phone, never a field of the body.

const http = require('node:http');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const HEADER = 'x-wacli-signature';
const HOST = '127.0.0.1';
const MAX_BODY = 64 * 1024;

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

function payloadOf(body) {
  const parsed = JSON.parse(body.toString('utf8'));
  const message = parsed && typeof parsed.message === 'object' && parsed.message ? parsed.message : parsed;
  return {
    id: message.id || message.message_id || null,
    chat: message.chat_jid || message.chat || message.conversation || null,
    sender: message.sender_jid || message.sender || message.from || '',
    text: message.text || message.body || '',
    fromMe: Boolean(message.from_me || message.fromMe),
    at: Number(message.timestamp || message.at) || Date.now(),
  };
}

function eventOf(fields, { owner, account }) {
  const sender = digits(fields.sender);
  const ownerDigits = digits(owner);
  const group = fields.chat && String(fields.chat).includes('@g.us') ? fields.chat : null;
  return {
    connector: 'whatsapp',
    account,
    id: String(fields.id),
    at: fields.at > 1e12 ? fields.at : fields.at * 1000,
    from: sender || String(fields.sender || ''),
    group,
    conversation: fields.chat,
    thread: null,
    text: fields.text || '',
    files: [],
    isSelf: fields.fromMe || sender === digits(account),
    identity: {
      verified: true,
      method: 'webhook-secret',
      owner: Boolean(ownerDigits) && sender === ownerDigits && !fields.fromMe,
    },
  };
}

function listen({ secret, owner, account, port = 8791, onEvent, onReject, host = HOST } = {}) {
  if (host !== HOST) throw new Error('the WhatsApp receiver listens on 127.0.0.1 only');
  if (!secret) throw new Error('webhook secret is not configured');
  if (!owner || !account) throw new Error('owner identity is not configured');
  const server = http.createServer((req, res) => {
    const done = (status, body) => {
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
      if (size > MAX_BODY) {
        req.destroy();
        return;
      }
      chunks.push(chunk);
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

function run(args, spawnImpl = spawn) {
  return new Promise((resolve, reject) => {
    const child = spawnImpl('wacli', args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '';
    let err = '';
    child.stdout.on('data', (chunk) => { out += chunk; });
    child.stderr.on('data', (chunk) => { err += chunk; });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) reject(fail(null, `whatsapp answered ${err.trim() || `exit ${code}`}`));
      else resolve(out);
    });
  });
}

function address(value) {
  const text = String(value || '');
  if (/@g\.us$/.test(text)) return { group: text };
  if (/^\d{8,15}$/.test(digits(text)) && !text.includes('@')) return { contact: digits(text) };
  const error = new Error('whatsapp addresses are a number with country code or a group id ending @g.us');
  error.code = 'address';
  throw error;
}

async function account(ctx = {}) {
  if (ctx.account) return ctx.account;
  throw new Error('the connector did not confirm its account identity');
}

const operations = {
  async 'message.send'({ group, contact, thread, text, clientId } = {}, ctx = {}) {
    const to = group || contact;
    if (!to || !text) throw fail(null, 'whatsapp answered no_text: the message is empty');
    const args = ['--json', 'send', 'text', '--to', to, '--message', text];
    if (thread) args.push('--reply-to', thread);
    if (clientId) args.push('--message-id', clientId);
    const out = await run(args, ctx.spawn);
    let body = {};
    try { body = JSON.parse(out); } catch { body = {}; }
    const id = body.id || body.message_id;
    if (!id) throw fail(null, 'whatsapp did not confirm the message');
    return { conversation: body.chat_jid || body.chat || to, id, thread: thread || null };
  },
  async 'message.file'({ send } = {}, ctx = {}) {
    if (!send?.file) throw fail(null, 'whatsapp needs a file to send');
    const to = send.conversation || send.contact;
    const args = ['--json', 'send', 'file', '--to', to, '--file', send.file];
    if (send.thread) args.push('--reply-to', send.thread);
    const out = await run(args, ctx.spawn);
    let body = {};
    try { body = JSON.parse(out); } catch { body = {}; }
    if (!body.id) throw fail(null, 'whatsapp did not confirm the file');
    return { id: body.id, conversation: body.chat_jid || to, thread: send.thread || null };
  },
  async 'message.history'({ conversation, thread } = {}, ctx = {}) {
    if (!conversation || !thread) return { events: [] };
    const out = await run(['--json', 'messages', 'search', '--chat', conversation, '--query', thread], ctx.spawn);
    let body = {};
    try { body = JSON.parse(out); } catch { body = {}; }
    const rows = Array.isArray(body.messages) ? body.messages : [];
    return {
      events: rows.map((row) => eventOf({
        id: row.id, chat: conversation, sender: row.sender_jid || row.sender || '', text: row.text || '', fromMe: row.from_me, timestamp: row.timestamp,
      }, { owner: ctx.owner || '', account: ctx.account || '' })),
    };
  },
  async 'message.receive'({ onEvent, secret, owner, account, port } = {}) {
    const listening = await listen({ secret, owner, account, port, onEvent });
    return { stop: () => listening.close() };
  },
};

module.exports = { operations, address, account, listen, signed, signature, eventOf, HEADER, HOST };
