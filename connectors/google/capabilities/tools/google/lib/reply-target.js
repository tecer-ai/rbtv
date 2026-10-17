'use strict';

// Internal helper of the Gmail messaging adapter: resolves where a reply goes. Given a
// reference's conversation (the Gmail thread id it claims) and id (a native message id or the
// thread id itself), it reads the real service through the adapter's own command runner and
// returns { to, verified, threadId, messageId, subject }. `to` is the canonical recipient: the
// sender address Gmail authenticated (sender_verification.trusted), never a bare display From,
// which anyone can type. `verified` says whether Gmail authenticated that address as the
// configured owner; the port command authorizes on it before any draft exists. messaging.js
// binds this to its runner and re-exports it as resolveReply.

function fail(code, message) {
  const error = new Error(message);
  if (code) {
    error.reason = code;
    error.code = code;
  }
  return error;
}

function emailOf(header) {
  const text = String(header || '');
  const wrapped = /<([^<>\s]+@[^<>\s]+)>/.exec(text);
  if (wrapped) return wrapped[1];
  const bare = /[^\s@]+@[^\s@]+/.exec(text);
  return bare ? bare[0] : '';
}

function sameAddress(left, right) {
  return String(left || '').trim().toLowerCase() === String(right || '').trim().toLowerCase();
}

async function resolveReplyTarget(deps, ref = {}) {
  const { section, run, readMessage } = deps;
  const id = ref.id || null;
  const expected = ref.conversation || null;
  let resolved = null;
  if (id && expected && id !== expected) {
    // A native message id: resolve it and refuse a reference whose conversation is not the
    // thread the message actually belongs to, before anything is drafted or sent.
    resolved = await readMessage(id);
    if (resolved.threadId && resolved.threadId !== expected) {
      throw fail('thread', `google answered thread_mismatch: message ${id} belongs to ${resolved.threadId}, not ${expected}`);
    }
  }
  let threadId = resolved?.threadId || expected || id;
  let messages = [];
  if (threadId) {
    try {
      const { out } = await run([
        'gmail', 'read', '--account', section.account, '--thread-id', threadId,
        '--verify-sender', section.owner, '--json',
      ]);
      const body = JSON.parse(out);
      messages = Array.isArray(body?.messages) ? body.messages : [];
    } catch (error) {
      if (!resolved) throw error;
    }
  }
  if (!messages.length && resolved) messages = [resolved];
  if (!messages.length) throw fail('thread', `google answered thread_not_found: no thread ${threadId || id}`);
  const mine = String(section.mailbox || '').toLowerCase();
  const other = [...messages].reverse().find((row) => emailOf(row.from).toLowerCase() !== mine) || messages.at(-1);
  if (!other) throw fail(null, 'google answered no_recipient: the thread has no message to answer');
  const verification = other.sender_verification || {};
  let to = verification.trusted && verification.address ? verification.address : emailOf(other.from);
  if (to && to.toLowerCase() === mine) to = emailOf(other.to);
  if (!to) throw fail(null, 'google answered no_recipient: the thread has no address to reply to');
  return {
    to,
    verified: Boolean(verification.trusted && sameAddress(verification.address, to)),
    threadId: other.threadId || threadId,
    messageId: other.id,
    subject: other.subject || '',
  };
}

module.exports = { resolveReplyTarget, emailOf, sameAddress };
