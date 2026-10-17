'use strict';

// Docs of the /agent panel: the Markdown documents an agent's turns reported as outputs, and the one document open in
// the agent's channel canvas (owner decision, 2026-10-17: on Slack's free plan a channel has one canvas, and it holds
// the open document). The repository file stays the source: opening writes a copy into the canvas; pulling returns
// the canvas as Markdown for the agent to bring into the file. A canvas edited since it was opened or pulled is never
// replaced unless asked, so edits are not lost.
//
// API
// recentDocs(store, workspace, limit = 15) → [{ path, at }] newest first: each .md output of a finished turn that is a
//   file inside the installation; path is relative to the installation.
// openDocument(store) → the open document's record { canvasId, channel, path, openedAt, baseline } or null.
// openDoc({ slack, store, workspace, channel, path, force? }) → { opened: path, canvasId } or { refused, path, why }; path
//   is relative to the installation and must name a Markdown file inside it, else it throws:
//   refused 'edited' when the canvas changed since it was opened or last pulled, 'untracked' when the channel's canvas
//   holds something Ignite did not open; force replaces it anyway.
// forCanvas(markdown) → the Markdown a canvas accepts: links to targets other than http(s) and mailto escaped.
// pullDoc({ slack, store }) → { path, markdown, edited, comments } or null when no document is open; the canvas as it
//   is now becomes the baseline, so the next open no longer refuses.

const fs = require('fs');
const path = require('path');

const { canvasMarkdown } = require('../../../../../connectors/slack/capabilities/tools/slack/lib/canvas-markdown.js');

const KEY = 'docs_canvas';

// A canvas refuses a link Slack cannot open, such as a link to another repository file (observed 2026-10-17:
// "Unsupported target for link"). Such a link goes in escaped, so the canvas shows it as written and a pull returns it
// unchanged; code spans and fenced code are left alone.
function forCanvas(markdown) {
  return markdown.split(/(```[\s\S]*?```|`[^`\n]*`)/).map((piece, i) => (i % 2 ? piece
    : piece.replace(/\[([^\]\n]*)\]\((?!https?:\/\/|mailto:)([^)\n]*)\)/g, '\\[$1\\]($2)'))).join('');
}

function recentDocs(store, workspace, limit = 15) {
  const root = path.resolve(workspace);
  const seen = new Map();
  for (const run of store.finishedOutputs()) {
    for (const output of run.outputs) {
      const full = path.resolve(root, output);
      if (!full.endsWith('.md') || !full.startsWith(`${root}${path.sep}`) || seen.has(full)) continue;
      if (!fs.existsSync(full) || !fs.statSync(full).isFile()) continue;
      seen.set(full, { path: path.relative(root, full).split(path.sep).join('/'), at: run.endedAt });
    }
  }
  return [...seen.values()].slice(0, limit);
}

function openDocument(store) {
  return store.getSetting(KEY);
}

// The canvas as Markdown now. Its first heading is its title, the path Ignite named it with: files.info's own title
// lags a rename by up to a second (observed 2026-10-17), so the path is what the heading is compared with.
async function canvasNow(slack, canvasId, title) {
  const read = await slack.canvasRead(canvasId);
  return { markdown: canvasMarkdown(read.html, { title }), comments: read.comments };
}

async function openDoc({ slack, store, workspace, channel, path: wanted, force = false }) {
  const root = path.resolve(workspace);
  const file = path.resolve(root, wanted);
  if (!file.endsWith('.md') || !file.startsWith(`${root}${path.sep}`)) throw new Error(`${wanted} is not a Markdown file inside the installation`);
  const markdown = forCanvas(fs.readFileSync(file, 'utf8'));
  const record = openDocument(store);
  let canvasId = await slack.channelCanvas(channel);
  if (canvasId && !force) {
    if (!record || record.canvasId !== canvasId) {
      return { refused: 'untracked', path: null, why: 'the channel canvas holds something Ignite did not open' };
    }
    const now = await canvasNow(slack, canvasId, record.path);
    if (now.markdown !== record.baseline) {
      return { refused: 'edited', path: record.path, why: `${record.path} was edited in the canvas since it was opened; bring the edits in first` };
    }
  }
  if (canvasId) {
    await slack.canvasEdit({ canvasId, markdown });
    await slack.canvasRename({ canvasId, title: wanted });
  } else {
    ({ canvasId } = await slack.canvasCreate({ channel, markdown, title: wanted }));
  }
  const baseline = (await canvasNow(slack, canvasId, wanted)).markdown;
  store.setSetting(KEY, { canvasId, channel, path: wanted, openedAt: Date.now(), baseline });
  return { opened: wanted, canvasId };
}

async function pullDoc({ slack, store }) {
  const record = openDocument(store);
  if (!record) return null;
  const now = await canvasNow(slack, record.canvasId, record.path);
  store.setSetting(KEY, { ...record, baseline: now.markdown });
  return { path: record.path, markdown: now.markdown, edited: now.markdown !== record.baseline, comments: now.comments };
}

module.exports = { recentDocs, openDocument, openDoc, pullDoc, forCanvas };
