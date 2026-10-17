'use strict';

// The Slack block pieces Ignite's panels build their views from, and the escape for text they did not write.
//
// API
// plain(text) → a plain_text object, cut to 150 characters (Slack's limit for a button or a title is lower; callers cut those).
// section(text) / context(text) → a section or context block of mrkdwn, cut to Slack's 3000 characters.
// modal(callbackId, title, blocks, { submit?, close?, metadata? }) → a modal view; metadata is its private_metadata.
// esc(value) → text an agent, a bank or a file supplied, shown as mrkdwn: no link, mention or markup of its own.

const plain = (text) => ({ type: 'plain_text', text: String(text).slice(0, 150) });
const section = (text) => ({ type: 'section', text: { type: 'mrkdwn', text: String(text).slice(0, 3000) } });
const context = (text) => ({ type: 'context', elements: [{ type: 'mrkdwn', text: String(text).slice(0, 3000) }] });

function esc(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function modal(callbackId, title, blocks, { submit = null, close = 'Close', metadata = '' } = {}) {
  return {
    type: 'modal',
    callback_id: callbackId,
    title: plain(title),
    close: plain(close),
    ...(submit ? { submit: plain(submit) } : {}),
    ...(metadata ? { private_metadata: metadata } : {}),
    blocks,
  };
}

module.exports = { plain, section, context, esc, modal };
