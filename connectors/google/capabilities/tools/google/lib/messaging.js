'use strict';

// Gmail messaging adapter. The mailbox is the configured account (google --account), never a From header.
// Owner identity is google gmail read --verify-sender: trusted only when that command's sender_verification
// says trusted for the configured owner address. From alone is not identity. A poll runs only when the
// caller supplies a cadence; this module starts no timer.

const { spawn } = require('node:child_process');
const fs = require('node:fs');

function fail(reason, message) {
  const error = new Error(message);
  if (reason) error.reason = reason;
  return error;
}

function run(args, spawnImpl = spawn) {
  return new Promise((resolve, reject) => {
    const child = spawnImpl('google', args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '';
    let err = '';
    child.stdout.on('data', (chunk) => { out += chunk; });
    child.stderr.on('data', (chunk) => { err += chunk; });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) reject(fail(null, `google answered ${err.trim() || `exit ${code}`}`));
      else resolve(out);
    });
  });
}

function address(value) {
  const text = String(value || '').trim();
  if (/^[^\s@]+@[^\s@]+$/.test(text) && !text.includes(':')) return { contact: text };
  const error = new Error("google addresses are a mail address");
  error.code = 'address';
  throw error;
}

async function account(ctx = {}) {
  const mailbox = ctx.mailbox || ctx.section?.mailbox;
  if (typeof mailbox !== 'string' || !mailbox.trim() || mailbox.includes(':')) {
    throw new Error('the connector did not confirm its account identity');
  }
  return mailbox;
}

function eventOf(message, section) {
  const verification = message.sender_verification || {};
  const trusted = verification.trusted === true && String(verification.address || '').toLowerCase() === String(section.owner).toLowerCase();
  return {
    connector: 'google',
    account: section.mailbox,
    id: message.id,
    at: Date.parse(message.date) || Date.now(),
    from: trusted ? section.owner : (verification.address || ''),
    group: null,
    conversation: message.threadId || message.id,
    thread: message.threadId && message.threadId !== message.id ? message.threadId : null,
    text: message.body_plain || message.snippet || '',
    files: [],
    isSelf: false,
    identity: { verified: trusted, method: 'gmail-account', owner: trusted },
  };
}

async function poll({ section, cursorFile, spawn: spawnImpl, onEvent } = {}) {
  if (!section?.account || !section.mailbox || !section.owner) throw new Error('owner identity is not configured');
  const cursor = cursorFile && fs.existsSync(cursorFile) ? JSON.parse(fs.readFileSync(cursorFile, 'utf8')) : {};
  const query = cursor.after ? `after:${cursor.after}` : 'newer_than:1d';
  const out = await run([
    '--json', 'gmail', 'read', '--account', section.account, '--query', query,
    '--verify-sender', section.owner, '--limit', '20',
  ], spawnImpl);
  const body = JSON.parse(out);
  const messages = Array.isArray(body) ? body : (body.messages || []);
  let newest = cursor.after || 0;
  const held = [];
  for (const message of messages) {
    if (!message?.id || (cursor.ids || []).includes(message.id)) continue;
    const event = eventOf(message, section);
    try {
      const result = await onEvent(event);
      if (result?.ignored === 'judgment-error') {
        held.push(message.id);
        continue;
      }
    } catch (error) {
      held.push(message.id);
      continue;
    }
    const at = event.at;
    if (at > newest) newest = at;
  }
  if (cursorFile) {
    const seen = new Set([...(cursor.ids || []), ...messages.map((row) => row.id).filter((id) => id && !held.includes(id))]);
    fs.mkdirSync(require('node:path').dirname(cursorFile), { recursive: true });
    fs.writeFileSync(cursorFile, JSON.stringify({ after: Math.floor(newest / 1000), ids: [...seen] }));
  }
  return { count: messages.length, held };
}

const operations = {
  async 'message.send'({ contact, text } = {}, ctx = {}) {
    if (!contact || !text) throw fail(null, 'google answered no_text: the message is empty');
    const section = ctx.section;
    if (!section?.account) throw fail(null, 'google account is not configured');
    const drafted = await run([
      'gmail', 'draft', '--account', section.account, '--to', contact, '--subject', text.split('\n')[0].slice(0, 80) || 'message', '--body', text,
    ], ctx.spawn);
    const draftId = /id=(\S+)/.exec(drafted)?.[1];
    if (!draftId) throw fail(null, 'google did not confirm the draft');
    const sent = await run(['gmail', 'send', '--account', section.account, '--draft-id', draftId], ctx.spawn);
    const id = /message(?:_id)?[=: ]+(\S+)/i.exec(sent)?.[1] || draftId;
    return { conversation: id, id, thread: null };
  },
  async 'message.history'({ conversation, thread } = {}, ctx = {}) {
    const section = ctx.section;
    if (!section?.account || !thread) return { events: [] };
    const out = await run([
      '--json', 'gmail', 'read', '--account', section.account, '--thread-id', thread,
      '--verify-sender', section.owner,
    ], ctx.spawn);
    const body = JSON.parse(out);
    const messages = body.messages || [];
    return { events: messages.map((message) => eventOf(message, section)) };
  },
  async 'message.receive'() {
    throw new Error('google polling starts only when listeners.google.pollMs is set; this call starts no timer');
  },
};

module.exports = { operations, address, account, poll, eventOf };
