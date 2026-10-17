'use strict';

// Gmail messaging adapter. The mailbox is the address Gmail's getProfile returns for
// `google --account`, compared with listeners.google.mailbox. From alone is not identity.
// Owner identity is google gmail read --verify-sender: trusted only when sender_verification
// says trusted for the configured owner. A poll runs only when the caller supplies a cadence.

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { spawnable } = require('../../../../../../core/cast/capabilities/tools/cast/lib/win-exec');

const PAGE = 100;
const MAX_PAGES = 5;
const COMMAND_MS = 60_000;
const SEEN_LIMIT = 500;

let children = new Set();

function fail(reason, message) {
  const error = new Error(message);
  if (reason) error.reason = reason;
  return error;
}

function launch(command, args, spawnImpl, extra = {}) {
  if (typeof spawnImpl === 'function' && spawnImpl !== spawn) {
    return spawnImpl(command, args, { stdio: ['ignore', 'pipe', 'pipe'], ...extra });
  }
  const win = spawnable(command, args);
  return spawn(win.cmd, win.args, { stdio: ['ignore', 'pipe', 'pipe'], ...win.opts, ...extra });
}

function run(args, spawnImpl, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(fail(null, 'google command aborted'));
      return;
    }
    const child = launch('google', args, spawnImpl);
    children.add(child);
    let out = '';
    let err = '';
    let settled = false;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      children.delete(child);
      fn(value);
    };
    const timer = setTimeout(() => {
      child.kill();
      finish(reject, fail(null, 'google command timed out'));
    }, COMMAND_MS);
    const onAbort = () => {
      child.kill();
      finish(reject, fail(null, 'google command aborted'));
    };
    signal?.addEventListener('abort', onAbort, { once: true });
    child.stdout.on('data', (chunk) => { out += chunk; });
    child.stderr.on('data', (chunk) => { err += chunk; });
    child.on('error', (error) => finish(reject, error));
    child.on('close', (code) => {
      signal?.removeEventListener('abort', onAbort);
      if (code !== 0) finish(reject, fail(null, `google answered ${err.trim() || `exit ${code}`}`));
      else finish(resolve, { out, err });
    });
  });
}

function abort() {
  for (const child of children) {
    try { child.kill(); } catch { /* already gone */ }
  }
}

function address(value) {
  const text = String(value || '').trim();
  if (/^[^\s@]+@[^\s@]+$/.test(text) && !text.includes(':')) return { contact: text };
  const error = new Error('google addresses are a mail address');
  error.code = 'address';
  throw error;
}

function mailboxOf(stdout, stderr) {
  const marked = /^MAILBOX\s+(\S+)/m.exec(stderr || '');
  if (marked) return marked[1];
  let body;
  try { body = JSON.parse(stdout || ''); } catch { return null; }
  if (body && typeof body.mailbox === 'string') return body.mailbox;
  const rows = Array.isArray(body) ? body : (body?.messages || []);
  return rows[0]?.sender_verification?.mailbox || null;
}

function sameAddress(left, right) {
  return String(left || '').trim().toLowerCase() === String(right || '').trim().toLowerCase();
}

async function confirmMailbox(section, spawnImpl, signal) {
  const alias = section?.account;
  const wanted = section?.mailbox;
  if (!alias || !wanted || String(alias).includes(':') || String(wanted).includes(':')) {
    throw new Error('the connector did not confirm its account identity');
  }
  const { out, err } = await run([
    'gmail', 'read', '--account', alias, '--query', 'in:inbox', '--verify-sender', wanted,
    '--limit', '1', '--json',
  ], spawnImpl, signal);
  const actual = mailboxOf(out, err);
  if (!actual || !sameAddress(actual, wanted)) {
    throw new Error('the connector did not confirm its account identity');
  }
  return wanted;
}

async function account(ctx = {}) {
  const section = ctx.section || {};
  const mailbox = await confirmMailbox({
    account: ctx.account || section.account,
    mailbox: ctx.mailbox || section.mailbox,
  }, ctx.spawn);
  return mailbox;
}

function emailOf(header) {
  const text = String(header || '');
  const wrapped = /<([^<>\s]+@[^<>\s]+)>/.exec(text);
  if (wrapped) return wrapped[1];
  const bare = /[^\s@]+@[^\s@]+/.exec(text);
  return bare ? bare[0] : '';
}

function eventOf(message, section) {
  const verification = message.sender_verification || {};
  const trusted = verification.trusted === true && sameAddress(verification.address, section.owner);
  const claimed = String(message.from || '');
  const internal = Number(message.internalDate);
  return {
    connector: 'google',
    account: section.mailbox,
    id: message.id,
    at: Number.isFinite(internal) && internal > 0 ? internal : Date.now(),
    from: trusted ? section.owner : claimed,
    claimedFrom: claimed,
    group: null,
    conversation: message.threadId || message.id,
    thread: message.threadId && message.threadId !== message.id ? message.threadId : null,
    text: message.body_plain || message.snippet || '',
    files: [],
    isSelf: false,
    identity: { verified: trusted, method: 'gmail-account', owner: trusted, claimed },
  };
}

function readCursor(file, section) {
  if (!file || !fs.existsSync(file)) return { account: section.account, mailbox: section.mailbox, afterMs: 0, ceilingMs: null, seen: [], held: [] };
  let body;
  try { body = JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return { account: section.account, mailbox: section.mailbox, afterMs: 0, ceilingMs: null, seen: [], held: [] }; }
  if (body.account !== section.account || !sameAddress(body.mailbox, section.mailbox)) {
    return { account: section.account, mailbox: section.mailbox, afterMs: 0, ceilingMs: null, seen: [], held: [] };
  }
  return {
    account: section.account,
    mailbox: section.mailbox,
    afterMs: Number(body.afterMs) || 0,
    ceilingMs: Number(body.ceilingMs) || null,
    seen: Array.isArray(body.seen) ? body.seen.slice(-SEEN_LIMIT) : [],
    held: Array.isArray(body.held) ? body.held : [],
  };
}

function writeCursor(file, cursor) {
  if (!file) return;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const next = { ...cursor, seen: (cursor.seen || []).slice(-SEEN_LIMIT) };
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(next));
  fs.renameSync(tmp, file);
}

function queryOf(cursor) {
  const parts = ['in:inbox'];
  if (cursor.afterMs) parts.push(`after:${Math.floor(cursor.afterMs / 1000)}`);
  if (cursor.ceilingMs) parts.push(`before:${Math.floor(cursor.ceilingMs / 1000)}`);
  return parts.join(' ');
}

function rowsOf(stdout) {
  const body = JSON.parse(stdout);
  if (Array.isArray(body)) return body;
  if (Array.isArray(body.messages)) return body.messages;
  return body.id ? [body] : [];
}

async function search(section, query, spawnImpl, signal) {
  const { out } = await run([
    'gmail', 'read', '--account', section.account, '--query', query,
    '--verify-sender', section.owner, '--limit', String(PAGE), '--json',
  ], spawnImpl, signal);
  return rowsOf(out);
}

async function readMessage(section, id, spawnImpl, signal) {
  const { out } = await run([
    'gmail', 'read', '--account', section.account, '--message-id', id,
    '--verify-sender', section.owner, '--json',
  ], spawnImpl, signal);
  return JSON.parse(out);
}

function heldResult(result) {
  return result?.ignored === 'judgment-error' || result?.ignored === 'subscriptions-invalid';
}

async function deliverEvent(message, section, onEvent) {
  const event = eventOf(message, section);
  try {
    const result = await onEvent(event);
    return { event, held: heldResult(result) };
  } catch {
    return { event, held: true };
  }
}

async function poll({ section, cursorFile, spawn: spawnImpl, onEvent, signal } = {}) {
  if (!section?.account || !section.mailbox || !section.owner) throw new Error('owner identity is not configured');
  if (typeof onEvent !== 'function') throw new Error('onEvent required');
  await confirmMailbox(section, spawnImpl, signal);
  const cursor = readCursor(cursorFile, section);
  const seen = new Set(cursor.seen || []);
  const held = [];
  for (const row of cursor.held || []) {
    if (signal?.aborted) break;
    const message = await readMessage(section, row.id, spawnImpl, signal);
    const delivered = await deliverEvent(message, section, onEvent);
    if (delivered.held) held.push({ id: message.id, internalDate: Number(message.internalDate) || 0 });
    else seen.add(message.id);
  }
  let ceilingMs = cursor.ceilingMs;
  let afterMs = cursor.afterMs;
  let pages = 0;
  let count = 0;
  while (pages < MAX_PAGES && !signal?.aborted) {
    const query = queryOf({ afterMs, ceilingMs });
    const summaries = await search(section, query, spawnImpl, signal);
    count += summaries.length;
    pages += 1;
    const pending = summaries.filter((row) => row?.id && !seen.has(row.id) && !held.some((item) => item.id === row.id));
    const full = [];
    for (const row of pending) {
      if (signal?.aborted) break;
      const message = row.body_plain != null && row.internalDate ? row : await readMessage(section, row.id, spawnImpl, signal);
      full.push(message);
    }
    full.sort((left, right) => Number(left.internalDate || 0) - Number(right.internalDate || 0));
    for (const message of full) {
      const delivered = await deliverEvent(message, section, onEvent);
      if (delivered.held) held.push({ id: message.id, internalDate: Number(message.internalDate) || 0 });
      else seen.add(message.id);
    }
    if (summaries.length < PAGE) {
      ceilingMs = null;
      const heldMs = held.map((row) => row.internalDate).filter((value) => value > 0);
      if (!heldMs.length) {
        const done = full.map((row) => Number(row.internalDate) || 0).filter((value) => value > 0);
        if (done.length) afterMs = Math.max(afterMs, Math.max(...done));
      }
      break;
    }
    const oldest = Math.min(...summaries.map((row) => Number(row.internalDate) || Number.MAX_SAFE_INTEGER));
    if (!Number.isFinite(oldest) || oldest === Number.MAX_SAFE_INTEGER || oldest === ceilingMs) break;
    ceilingMs = oldest;
  }
  writeCursor(cursorFile, {
    account: section.account,
    mailbox: section.mailbox,
    afterMs,
    ceilingMs,
    seen: [...seen],
    held,
  });
  return { count, held: held.map((row) => row.id) };
}

function sentIds(text) {
  const id = /Message ID:\s*(\S+)/.exec(text)?.[1];
  const thread = /Thread ID:\s*(\S+)/.exec(text)?.[1] || null;
  return { id, thread };
}

async function replyTarget(section, id, spawnImpl) {
  let body;
  try {
    const { out } = await run([
      'gmail', 'read', '--account', section.account, '--thread-id', id,
      '--verify-sender', section.owner, '--json',
    ], spawnImpl);
    body = JSON.parse(out);
  } catch {
    body = await readMessage(section, id, spawnImpl);
  }
  const messages = body.messages || [body];
  const mine = section.mailbox.toLowerCase();
  const other = [...messages].reverse().find((row) => emailOf(row.from).toLowerCase() !== mine) || messages.at(-1);
  if (!other) throw fail(null, 'google answered no_text: the message is empty');
  const from = emailOf(other.from);
  const to = from.toLowerCase() === mine ? emailOf(other.to) : from;
  if (!to) throw fail(null, 'google answered no_text: the message is empty');
  return { to, threadId: other.threadId || body.threadId || id, messageId: other.id, subject: other.subject || '' };
}

const operations = {
  async 'message.send'({ contact, group, thread, text } = {}, ctx = {}) {
    if (!text) throw fail(null, 'google answered no_text: the message is empty');
    const section = ctx.section || {};
    if (!section.account || !section.mailbox || !section.owner) throw fail(null, 'google account is not configured');
    await confirmMailbox(section, ctx.spawn);
    let to = contact || null;
    let threadId = null;
    let replyTo = null;
    let subject = text.split('\n')[0].slice(0, 80) || 'message';
    if (!to && (thread || group)) {
      const target = await replyTarget(section, thread || group, ctx.spawn);
      to = target.to;
      threadId = target.threadId;
      replyTo = target.messageId;
      subject = target.subject ? (target.subject.startsWith('Re:') ? target.subject : `Re: ${target.subject}`) : subject;
    }
    if (!to) throw fail(null, 'google answered no_text: the message is empty');
    const draftArgs = ['gmail', 'draft', '--account', section.account, '--to', to, '--subject', subject, '--body', text];
    if (threadId && replyTo) draftArgs.push('--thread-id', threadId, '--reply-to-message-id', replyTo);
    const drafted = await run(draftArgs, ctx.spawn);
    const draftId = /id=(\S+)/.exec(drafted.out)?.[1];
    if (!draftId) throw fail(null, 'google did not confirm the draft');
    const sent = await run(['gmail', 'send', '--account', section.account, '--draft-id', draftId], ctx.spawn);
    const ids = sentIds(sent.out);
    if (!ids.id || ids.id === 'ID:') throw fail(null, 'google did not confirm the message');
    return { conversation: ids.thread || threadId || ids.id, id: ids.id, thread: ids.thread || threadId || null };
  },
  async 'message.history'({ conversation, thread } = {}, ctx = {}) {
    const section = ctx.section || {};
    const id = thread || conversation;
    if (!section.account || !section.owner || !id) return { events: [] };
    await confirmMailbox(section, ctx.spawn);
    const { out } = await run([
      'gmail', 'read', '--account', section.account, '--thread-id', id,
      '--verify-sender', section.owner, '--json',
    ], ctx.spawn);
    const body = JSON.parse(out);
    const messages = body.messages || [];
    return { events: messages.map((message) => eventOf(message, section)) };
  },
  async 'message.receive'() {
    throw new Error('google polling starts only when listeners.google.pollMs is set; this call starts no timer');
  },
};

module.exports = { operations, address, account, poll, eventOf, abort, PAGE };
