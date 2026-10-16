'use strict';

// The one send function: Ignite's outbox.js and the `message send` command both deliver through it, so
// the two cannot diverge (phase 2 of the connector architecture, test 1). It holds the policy both callers
// need and no connector should: post the text once, send a text over MAX_TEXT characters as a file named
// message.md with no text, upload each file after the text with no caption, return every id. It holds no
// retry and no store.
//
// API
// send(operations, input) → Promise<{ conversation, id, files, textAsFile }>
//   operations — the messaging contract's Adapter shape: operations['message.send'] and operations['message.file'],
//   one async function each (connectors/messaging/capabilities/methods/messaging-contract.md).
//   input — the contract's message.send input plus the files: { group | contact, thread, text, files, as, clientId }.
//   conversation and id are the connector's values for the first message delivered (the text, or the first
//   file when there is no text); files is one { path, id } per attachment in order, or { path, id: null, error }
//   for one the connector refused (the text stays delivered: the caller decides what a partial means);
//   textAsFile is null, or { chars } when the text went as a file. A text the connector refuses throws.
// MAX_TEXT — 12,000 characters, the contract's ceiling for a message's text.
// senderOf(home) → { name, avatar } from an agent folder's agent.json, or undefined without one: the display
//   name is external_name when set, else the name with a capital first letter.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const MAX_TEXT = 12_000;

function senderOf(home) {
  if (!home) return undefined;
  let agent;
  try {
    agent = JSON.parse(fs.readFileSync(path.join(home, 'agent.json'), 'utf8'));
  } catch {
    return undefined;
  }
  if (!agent || typeof agent.name !== 'string' || !agent.name) return undefined;
  const external = typeof agent.external_name === 'string' && agent.external_name.trim() ? agent.external_name.trim()
    : typeof agent.externalName === 'string' && agent.externalName.trim() ? agent.externalName.trim() : null;
  const name = external || agent.name.charAt(0).toUpperCase() + agent.name.slice(1);
  return { name, avatar: agent.avatar };
}

function textFile(text) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'message-text-'));
  const file = path.join(dir, 'message.md');
  fs.writeFileSync(file, text, 'utf8');
  return file;
}

async function send(operations, input) {
  if (typeof operations?.['message.send'] !== 'function') throw new Error("the connector has no operations['message.send']");
  const { thread = null, as, clientId } = input;
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
    let conversation = input.group || null;
    let id = null;
    if (text || !files.length) {
      const posted = await operations['message.send']({ group: input.group, contact: input.contact, thread, text, as, clientId });
      if (!posted?.conversation || !posted?.id) throw new Error('the connector did not confirm the message');
      conversation = posted.conversation;
      id = posted.id;
    }
    if (files.length && typeof operations['message.file'] !== 'function') throw new Error("the connector has no operations['message.file']");
    const sent = [];
    for (const file of files) {
      const target = conversation ? { conversation } : { contact: input.contact };
      try {
        const uploaded = await operations['message.file']({ send: { ...target, thread, file, as } });
        if (!uploaded?.id) throw new Error('the connector did not confirm the file');
        sent.push({ path: file, id: uploaded.id });
        if (!id) id = uploaded.id;
        if (!conversation && uploaded.conversation) conversation = uploaded.conversation;
      } catch (error) {
        sent.push({ path: file, id: null, error: error.message || String(error) });
      }
    }
    return { conversation, id, files: sent, textAsFile };
  } finally {
    if (temporary) {
      try { fs.rmSync(path.dirname(temporary), { recursive: true, force: true }); } catch { /* a temp file */ }
    }
  }
}

module.exports = { send, senderOf, MAX_TEXT };
