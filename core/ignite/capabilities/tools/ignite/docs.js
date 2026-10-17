'use strict';

// Docs of the /agent panel: the Markdown documents an agent's turns reported as outputs, and the one document open in
// the agent's channel canvas (owner decision, 2026-10-17: on Slack's free plan a channel has one canvas, and it holds
// the open document). The repository file stays the source: opening writes a copy into the canvas; saving writes the
// edited canvas as a file in the agent's output/ignite/canvas/, headed by the path of the document it came from, for
// the agent to bring into that document and then delete. A canvas edited since it was opened or saved is never
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
// saveDoc({ slack, store, home, now? }) → null when no document is open; else { source, saved, edited, comments,
//   markdown }: when the canvas changed since it was opened or last saved, saved is the file written, relative to home,
//   and the canvas as it is now becomes the baseline, so the next open no longer refuses; unchanged, saved is null and
//   nothing is written.
// pendingSaves(home) → [{ file, source, savedAt }] newest first: the saves in output/ignite/canvas/ not yet deleted.

const fs = require('fs');
const path = require('path');

const { canvasMarkdown } = require('../../../../../connectors/slack/capabilities/tools/slack/lib/canvas-markdown.js');

const KEY = 'docs_canvas';
const SAVES = path.join('output', 'ignite', 'canvas');

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
      return { refused: 'edited', path: record.path, why: `${record.path} was edited in the canvas since it was opened or last saved` };
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

// A save's header: the document it came from, when, and which canvas, as YAML values JSON-quoted.
function saveText(record, now, markdown, comments) {
  const head = [['source', record.path], ['saved_at', new Date(now).toISOString()], ['canvas', record.canvasId], ['comments', comments]];
  return `---\n${head.map(([key, value]) => `${key}: ${JSON.stringify(value)}`).join('\n')}\n---\n\n${markdown}`;
}

async function saveDoc({ slack, store, home, now = Date.now() }) {
  const record = openDocument(store);
  if (!record) return null;
  const canvas = await canvasNow(slack, record.canvasId, record.path);
  const result = { source: record.path, saved: null, edited: canvas.markdown !== record.baseline, comments: canvas.comments, markdown: canvas.markdown };
  if (!result.edited) return result;
  const stamp = new Date(now).toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
  const saved = path.join(SAVES, `${stamp}-${path.basename(record.path)}`);
  const file = path.join(home, saved);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(`${file}.tmp`, saveText(record, now, canvas.markdown, canvas.comments));
  fs.renameSync(`${file}.tmp`, file);
  store.setSetting(KEY, { ...record, baseline: canvas.markdown });
  return { ...result, saved: saved.split(path.sep).join('/') };
}

function pendingSaves(home) {
  const folder = path.join(home, SAVES);
  if (!fs.existsSync(folder)) return [];
  return fs.readdirSync(folder).filter((name) => name.endsWith('.md')).sort().reverse().map((name) => {
    const head = fs.readFileSync(path.join(folder, name), 'utf8').split('\n---\n')[0];
    const value = (key) => { try { return JSON.parse((head.match(new RegExp(`^${key}: (.*)$`, 'm')) || [])[1]); } catch { return null; } };
    return { file: [...SAVES.split(path.sep), name].join('/'), source: value('source'), savedAt: value('saved_at') };
  });
}

module.exports = { recentDocs, openDocument, openDoc, saveDoc, pendingSaves, forCanvas };
