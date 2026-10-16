'use strict';

// The one send function: Ignite's outbox.js and the `message send` command both deliver through it, so
// the two cannot diverge (phase 2 of the connector architecture, test 1). It holds the policy both callers
// need and no connector should: post the text once, send a text over MAX_TEXT characters as a file named
// message.md with no text, upload each file after the text with no caption as a message of the text's
// thread, return every id, and fail as a whole when nothing was delivered. It holds no retry and no store.
//
// API
// send(operations, input) → Promise<{ conversation, id, thread, files, textAsFile }>
//   operations — the messaging contract's Adapter shape: operations['message.send'] and operations['message.file'],
//   one async function each (connectors/messaging/capabilities/methods/messaging-contract.md).
//   input — the contract's message.send input plus the files: { group | contact, thread, text, files, as, clientId }.
//   conversation and id are the connector's values for the first message delivered (the text, or the first
//   file when there is no text). thread is the thread every message joined: null when input.thread was null
//   (the first message starts the thread the later ones join), else the thread's root as the connector
//   resolved it (a reply's id names its thread; the connector answers with the root), or input.thread when the
//   connector names none. files is one { path, id } per attachment in order, or { path, id: null, error, detail }
//   for one the connector refused: error is the service's bare answer (file_too_large) when the connector
//   gives one (error.reason), else its message; detail is the connector's sentence. A refused file beside a
//   delivered message is a partial the caller reports; when nothing at all was delivered the function throws
//   the first refusal, so no caller prints a reference for a message that does not exist. textAsFile is null,
//   or { chars } when the text went as a file. A text the connector refuses throws.
// MAX_TEXT — 12,000 characters, the contract's ceiling for a message's text.
// senderOf(home) → { name, avatar } from an agent folder, read by cast's readAgent, or undefined without one:
//   the name people see is external_name when set, else the name with a capital first letter. The one routine
//   both callers name the sender with.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { readAgent } = require('../../../../../../core/cast/capabilities/tools/cast/lib/agent');

const MAX_TEXT = 12_000;

function senderOf(home) {
  if (!home) return undefined;
  const agent = readAgent(home).agent;
  if (!agent) return undefined;
  const name = agent.externalName || agent.name.charAt(0).toUpperCase() + agent.name.slice(1);
  return { name, avatar: agent.avatar };
}

function textFile(text) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'message-text-'));
  const file = path.join(dir, 'message.md');
  fs.writeFileSync(file, text, 'utf8');
  return file;
}

function refusalOf(file, error) {
  const detail = error?.message || String(error);
  return { path: file, id: null, error: error?.reason || detail, detail };
}

async function send(operations, input) {
  if (typeof operations?.['message.send'] !== 'function') throw new Error("the connector has no operations['message.send']");
  const { as, clientId } = input;
  const given = input.thread ?? null;
  let thread = given;
  let text = typeof input.text === 'string' ? input.text : '';
  const files = Array.isArray(input.files) ? input.files.slice() : [];
  let textAsFile = null;
  let temporary = null;
  if ([...text].length > MAX_TEXT) {
    textAsFile = { chars: [...text].length };
    temporary = textFile(text);
    files.unshift(temporary);
    text = '';
  }
  try {
    if (files.length && typeof operations['message.file'] !== 'function') throw new Error("the connector has no operations['message.file']");
    let conversation = input.group || null;
    let id = null;
    if (text || !files.length) {
      const posted = await operations['message.send']({ group: input.group, contact: input.contact, thread, text, as, clientId });
      if (!posted?.conversation || !posted?.id) throw new Error('the connector did not confirm the message');
      conversation = posted.conversation;
      id = posted.id;
      // The later messages join the text's thread: the root the connector resolved, or the text itself.
      thread = given == null ? id : (posted.thread ?? thread);
    }
    const sent = [];
    let firstError;
    for (const file of files) {
      const target = conversation ? { conversation } : { contact: input.contact };
      try {
        const uploaded = await operations['message.file']({ send: { ...target, thread, file, as } });
        if (!uploaded?.id) throw new Error('the connector did not confirm the file');
        sent.push({ path: file, id: uploaded.id });
        if (!id) {
          id = uploaded.id;
          thread = given == null ? uploaded.id : (uploaded.thread ?? thread);
        }
        if (!conversation && uploaded.conversation) conversation = uploaded.conversation;
      } catch (error) {
        if (firstError === undefined) firstError = error;
        sent.push(refusalOf(file, error));
      }
    }
    if (id == null) {
      // Nothing was delivered: a failure of the whole send, never a partial with no reference.
      if (firstError !== undefined) throw firstError;
      throw new Error('the connector did not confirm the message');
    }
    return { conversation, id, thread: given == null ? null : thread, files: sent, textAsFile };
  } finally {
    if (temporary) {
      try { fs.rmSync(path.dirname(temporary), { recursive: true, force: true }); } catch { /* a temp file */ }
    }
  }
}

module.exports = { send, senderOf, MAX_TEXT };
