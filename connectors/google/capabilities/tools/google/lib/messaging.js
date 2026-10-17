'use strict';

// Gmail messaging adapter. The mailbox is the address Gmail's getProfile returns for
// `google --account`, compared with listeners.google.mailbox. From alone is not identity.
// Owner identity is google gmail read --verify-sender: trusted only when sender_verification
// says trusted for the configured owner. A poll runs only when the caller supplies a cadence.
// A reference's conversation is a Gmail thread id and its id a native message id: the two are
// validated against each other before any history read, draft or send. Paging follows the
// service's own page tokens (NEXT_PAGE_TOKEN of google gmail read), so the rest of a second
// with more messages than one page is never lost; the durable cursor is account-qualified and
// held items retry by id, isolated from newer mail.

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { spawnable } = require('../../../../../../core/cast/capabilities/tools/cast/lib/win-exec');
const { resolveReplyTarget, sameAddress } = require('./reply-target');

const PAGE = 100;
const MAX_PAGES = 5;
// A token-less full page only happens with a client that does not print NEXT_PAGE_TOKEN; the
// before: walk that serves it cannot see the rest of the boundary second.
const EMPTY_PAGE_LOOKAHEAD = 2;
// Must cover MAX_PAGES * PAGE plus the re-scanned boundary second, or a re-traversed row
// could be delivered twice.
const SEEN_LIMIT = 600;
const HELD_ATTEMPTS = 3;
const COMMAND_MS = 60_000;
const KILL_ESCALATE_MS = 5_000;

let children = new Set();

function fail(reason, message) {
  const error = new Error(message);
  if (reason) {
    error.reason = reason;
    error.code = reason;
  }
  return error;
}

function killTree(child, signalName = 'SIGTERM') {
  if (!child) return;
  if (process.platform === 'win32') {
    if (child.pid) {
      try { spawn('taskkill', ['/pid', String(child.pid), '/T', '/F']); } catch { /* best effort */ }
    }
    try { child.kill(); } catch { /* already gone */ }
    return;
  }
  if (child.pid) {
    try { process.kill(-child.pid, signalName); return; } catch { /* not a group leader */ }
  }
  try { child.kill(signalName); } catch { /* already gone */ }
}

function launch(command, args, spawnImpl, extra = {}) {
  const opts = { stdio: ['ignore', 'pipe', 'pipe'], ...extra };
  // A group of its own on POSIX, so a stop takes the wrapper's whole child tree, not just the
  // wrapper: google.py waits in subprocess.call on gtools, which holds the service socket.
  if (process.platform !== 'win32') opts.detached = true;
  if (typeof spawnImpl === 'function' && spawnImpl !== spawn) {
    return spawnImpl(command, args, opts);
  }
  const win = spawnable(command, args);
  return spawn(win.cmd, win.args, { ...opts, ...win.opts, ...extra });
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
    let killing = null;
    let escalation = null;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      clearTimeout(escalation);
      signal?.removeEventListener('abort', onAbort);
      children.delete(child);
      fn(value);
    };
    const stop = (cause) => {
      if (killing) return;
      killing = cause;
      killTree(child);
      // A child that ignores SIGTERM, or a grandchild holding the pipes: escalate, but the
      // promise still settles only on the process tree's own close, so an awaited stop drains.
      escalation = setTimeout(() => killTree(child, 'SIGKILL'), KILL_ESCALATE_MS);
      if (typeof escalation.unref === 'function') escalation.unref();
    };
    const timer = setTimeout(() => stop('timeout'), COMMAND_MS);
    const onAbort = () => stop('abort');
    signal?.addEventListener('abort', onAbort, { once: true });
    child.stdout.on('data', (chunk) => { out += chunk; });
    child.stderr.on('data', (chunk) => { err += chunk; });
    child.on('error', (error) => finish(reject, error));
    child.on('close', (code) => {
      if (killing === 'abort') finish(reject, fail(null, 'google command aborted'));
      else if (killing === 'timeout') finish(reject, fail(null, 'google command timed out'));
      else if (code !== 0) finish(reject, fail(null, `google answered ${err.trim() || `exit ${code}`}`));
      else finish(resolve, { out, err });
    });
  });
}

function abort() {
  for (const child of [...children]) {
    killTree(child);
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

function normalizedHeld(rows) {
  if (!Array.isArray(rows)) return [];
  return rows
    .filter((row) => row && row.id)
    .map((row) => ({
      id: String(row.id),
      internalDate: Number(row.internalDate) || 0,
      attempts: Number(row.attempts) || 0,
      lastError: row.lastError == null ? null : String(row.lastError),
    }));
}

function readCursor(file, section) {
  if (!file || !fs.existsSync(file)) return { account: section.account, mailbox: section.mailbox, afterMs: 0, seen: [], held: [], dropped: [] };
  let body;
  try { body = JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return { account: section.account, mailbox: section.mailbox, afterMs: 0, seen: [], held: [], dropped: [] }; }
  if (body.account !== section.account || !sameAddress(body.mailbox, section.mailbox)) {
    return { account: section.account, mailbox: section.mailbox, afterMs: 0, seen: [], held: [], dropped: [] };
  }
  return {
    account: section.account,
    mailbox: section.mailbox,
    afterMs: Number(body.afterMs) || 0,
    seen: Array.isArray(body.seen) ? body.seen.slice(-SEEN_LIMIT) : [],
    held: normalizedHeld(body.held),
    dropped: Array.isArray(body.dropped) ? body.dropped.slice(-20) : [],
  };
}

function writeCursor(file, cursor) {
  if (!file) return;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const next = { ...cursor, seen: (cursor.seen || []).slice(-SEEN_LIMIT), dropped: (cursor.dropped || []).slice(-20) };
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(next));
  fs.renameSync(tmp, file);
}

function queryOf(afterMs, ceilingMs) {
  const parts = ['in:inbox'];
  const second = Math.floor(afterMs / 1000);
  // One second of overlap: lossless whether the service reads after: as inclusive or exclusive;
  // the seen set absorbs the re-scan.
  if (second > 0) parts.push(`after:${second - 1}`);
  if (ceilingMs) parts.push(`before:${Math.floor(ceilingMs / 1000)}`);
  return parts.join(' ');
}

function rowsOf(stdout) {
  const body = JSON.parse(stdout);
  if (Array.isArray(body)) return body;
  if (Array.isArray(body.messages)) return body.messages;
  return body.id ? [body] : [];
}

async function search(section, query, token, spawnImpl, signal) {
  const args = [
    'gmail', 'read', '--account', section.account, '--query', query,
    '--verify-sender', section.owner, '--limit', String(PAGE), '--json',
  ];
  if (token) args.push('--page-token', token);
  const { out, err } = await run(args, spawnImpl, signal);
  const nextToken = /^NEXT_PAGE_TOKEN\s+(\S+)/m.exec(err || '')?.[1] || null;
  return { rows: rowsOf(out), nextToken };
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

async function resolveReply(ref, ctx = {}) {
  const section = ctx.section || {};
  return resolveReplyTarget({
    section,
    run: (args) => run(args, ctx.spawn, ctx.signal),
    readMessage: (id) => readMessage(section, id, ctx.spawn, ctx.signal),
  }, ref);
}

async function poll({ section, cursorFile, spawn: spawnImpl, onEvent, signal } = {}) {
  if (!section?.account || !section.mailbox || !section.owner) throw new Error('owner identity is not configured');
  if (typeof onEvent !== 'function') throw new Error('onEvent required');
  await confirmMailbox(section, spawnImpl, signal);
  const cursor = readCursor(cursorFile, section);
  const seen = new Set(cursor.seen || []);
  const held = [];
  const failures = [];
  const dropped = [];
  // Held items retry by id, each isolated: one unreadable message is recorded with its exact
  // failure and never blocks the rest of the poll. A judgment hold retries with no attempt
  // count; only a failed read counts, and after HELD_ATTEMPTS the item is dropped with
  // accounting instead of retried forever.
  const priorHeld = cursor.held || [];
  for (let index = 0; index < priorHeld.length; index += 1) {
    const row = priorHeld[index];
    if (signal?.aborted) {
      held.push(...priorHeld.slice(index));
      break;
    }
    let message;
    try {
      message = await readMessage(section, row.id, spawnImpl, signal);
    } catch (error) {
      const attempts = (Number(row.attempts) || 0) + 1;
      const entry = { id: row.id, internalDate: Number(row.internalDate) || 0, attempts, lastError: String(error.message || error) };
      failures.push(entry);
      if (attempts >= HELD_ATTEMPTS) dropped.push(entry);
      else held.push(entry);
      continue;
    }
    const delivered = await deliverEvent(message, section, onEvent);
    if (delivered.held) held.push({ id: message.id, internalDate: Number(message.internalDate) || 0 });
    else seen.add(message.id);
  }
  let afterMs = cursor.afterMs;
  let ceilingMs = null;
  let token = null;
  let pages = 0;
  let count = 0;
  let emptyStreak = 0;
  let highWater = afterMs;
  while (pages < MAX_PAGES && !signal?.aborted) {
    const query = queryOf(afterMs, ceilingMs);
    const page = await search(section, query, token, spawnImpl, signal);
    pages += 1;
    count += page.rows.length;
    token = page.nextToken;
    const heldIds = new Set(held.map((row) => row.id));
    const pending = page.rows.filter((row) => row?.id && !seen.has(row.id) && !heldIds.has(row.id));
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
    emptyStreak = pending.length ? 0 : emptyStreak + 1;
    // The high-water mark advances from every processed page, never past a held item's own
    // second (its retry is by id, but the query stays a backstop), and never over a row this
    // poll stopped before processing.
    const heldMs = held.map((row) => row.internalDate).filter((value) => value > 0);
    const heldCeiling = heldMs.length ? Math.min(...heldMs) - 1 : Number.MAX_SAFE_INTEGER;
    for (const row of page.rows) {
      const ms = Number(row.internalDate) || 0;
      if (ms > 0 && (seen.has(row.id) || heldIds.has(row.id) || held.some((item) => item.id === row.id))) {
        highWater = Math.max(highWater, Math.min(ms, heldCeiling));
      }
    }
    if (token) {
      if (emptyStreak >= EMPTY_PAGE_LOOKAHEAD) break;
      continue;
    }
    if (page.rows.length < PAGE) break;
    const oldest = Math.min(...page.rows.map((row) => Number(row.internalDate) || Number.MAX_SAFE_INTEGER));
    if (!Number.isFinite(oldest) || oldest === Number.MAX_SAFE_INTEGER || oldest === ceilingMs) break;
    ceilingMs = oldest;
  }
  afterMs = Math.max(afterMs, highWater);
  writeCursor(cursorFile, {
    account: section.account,
    mailbox: section.mailbox,
    afterMs,
    seen: [...seen],
    held,
    dropped: [...(cursor.dropped || []), ...dropped],
  });
  return {
    count,
    held: held.map((row) => row.id),
    failures,
    dropped: dropped.map(({ id, attempts, lastError }) => ({ id, attempts, lastError })),
  };
}

function sentIds(text) {
  const id = /Message ID:\s*(\S+)/.exec(text)?.[1];
  const thread = /Thread ID:\s*(\S+)/.exec(text)?.[1] || null;
  return { id, thread };
}

const operations = {
  async 'message.send'({ contact, group, thread, text } = {}, ctx = {}) {
    if (!text) throw fail(null, 'google answered no_text: the message is empty');
    const section = ctx.section || {};
    if (!section.account || !section.mailbox || !section.owner) throw fail(null, 'google account is not configured');
    await confirmMailbox(section, ctx.spawn, ctx.signal);
    let to = contact || null;
    let threadId = null;
    let replyTo = null;
    let recipientVerified = null;
    let subject = text.split('\n')[0].slice(0, 80) || 'message';
    if (!to && (thread || group)) {
      const target = await resolveReply({ id: thread || group, conversation: thread && group ? group : null }, ctx);
      to = target.to;
      threadId = target.threadId;
      replyTo = target.messageId;
      recipientVerified = target.verified;
      subject = target.subject ? (target.subject.startsWith('Re:') ? target.subject : `Re: ${target.subject}`) : subject;
    }
    if (!to) throw fail(null, 'google answered no_recipient: the thread has no address to reply to');
    const draftArgs = ['gmail', 'draft', '--account', section.account, '--to', to, '--subject', subject, '--body', text];
    if (threadId && replyTo) draftArgs.push('--thread-id', threadId, '--reply-to-message-id', replyTo);
    const drafted = await run(draftArgs, ctx.spawn, ctx.signal);
    const draftId = /id=(\S+)/.exec(drafted.out)?.[1];
    if (!draftId) throw fail(null, 'google did not confirm the draft');
    const sent = await run(['gmail', 'send', '--account', section.account, '--draft-id', draftId], ctx.spawn, ctx.signal);
    const ids = sentIds(sent.out);
    if (!ids.id || ids.id === 'ID:') throw fail(null, 'google did not confirm the message');
    return {
      conversation: ids.thread || threadId || ids.id,
      id: ids.id,
      thread: ids.thread || threadId || null,
      to,
      recipientVerified,
    };
  },
  async 'message.history'({ conversation, thread } = {}, ctx = {}) {
    const section = ctx.section || {};
    const id = thread || conversation;
    if (!section.account || !section.owner || !id) return { events: [] };
    await confirmMailbox(section, ctx.spawn, ctx.signal);
    let threadId = conversation || null;
    if (thread && thread !== conversation) {
      // The reference carries a native message id: resolve it, refuse a conversation it does
      // not belong to, and read the thread the service says it is in.
      const message = await readMessage(section, thread, ctx.spawn, ctx.signal);
      if (conversation && message.threadId && message.threadId !== conversation) {
        throw fail('thread', `google answered thread_mismatch: message ${thread} belongs to ${message.threadId}, not ${conversation}`);
      }
      threadId = message.threadId || conversation || thread;
    }
    if (!threadId) threadId = id;
    const { out } = await run([
      'gmail', 'read', '--account', section.account, '--thread-id', threadId,
      '--verify-sender', section.owner, '--json',
    ], ctx.spawn, ctx.signal);
    const body = JSON.parse(out);
    const messages = body.messages || [];
    return { events: messages.map((message) => eventOf(message, section)) };
  },
  async 'message.receive'() {
    throw new Error('google polling starts only when listeners.google.pollMs is set; this call starts no timer');
  },
};

module.exports = { operations, address, account, poll, eventOf, resolveReply, abort, PAGE };
