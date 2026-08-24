'use strict';

// cast — session-store readers (one per harness) and `cast sessions`.
// Split out of cast.js 2026-08-20 on the file's own section banners; the code below is
// unchanged from that file. Every composed argv and every stdout surface stayed
// byte-identical across the split (163-invocation corpus, both self-check suites).

const fs = require('fs');
const os = require('os');
const path = require('path');

const { HARNESSES, SESSIONS_USAGE, fail, resolveFolder } = require('./core');
const { claudeSlug } = require('./handles');


// Head of a jsonl file as lines, without reading a possibly-MBs transcript whole. The label
// lives in the first user message, which sits near the top; past the cap the label is just ''.
function headLines(file, cap = 262144) {
  const fd = fs.openSync(file, 'r');
  try {
    const buf = Buffer.alloc(cap);
    const n = fs.readSync(fd, buf, 0, cap, 0);
    return buf.toString('utf8', 0, n).split('\n');
  } finally {
    fs.closeSync(fd);
  }
}

function excerpt(text) {
  const t = text.replace(/\s+/g, ' ').trim();
  return t.length > 60 ? `${t.slice(0, 59)}…` : t;
}

// Human label = the first real user message. Lines starting '<' are skipped: both harnesses
// inject wrapper blocks (<system-reminder>, <environment_context>, ...) ahead of the prompt.
function claudeLabel(lines) {
  for (const line of lines) {
    let d;
    try { d = JSON.parse(line); } catch { continue; }
    if (d.type !== 'user' || d.isSidechain) continue;
    const c = d.message?.content;
    const text = typeof c === 'string' ? c
      : Array.isArray(c) ? (c.find((p) => p.type === 'text')?.text ?? '') : '';
    if (text && !text.startsWith('<')) return excerpt(text);
  }
  return '';
}

function codexLabel(lines) {
  for (const line of lines) {
    let d;
    try { d = JSON.parse(line); } catch { continue; }
    const p = d.payload || {};
    if (d.type !== 'response_item' || p.type !== 'message' || p.role !== 'user') continue;
    const text = (p.content || []).find((c) => c.type === 'input_text')?.text ?? '';
    if (text && !text.startsWith('<')) return excerpt(text);
  }
  return '';
}

// claude: ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl — the filename IS the id.
function claudeSessions(folder) {
  const dir = path.join(os.homedir(), '.claude', 'projects', claudeSlug(folder));
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith('.jsonl')).map((f) => {
    const file = path.join(dir, f);
    const st = fs.statSync(file);
    return {
      harness: 'claude',
      id: f.slice(0, -'.jsonl'.length),
      started: st.birthtimeMs || st.mtimeMs,
      label: claudeLabel(headLines(file)),
    };
  });
}

// codex: ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl, cwd + id in the first-line session_meta.
// Walked newest-date-first, stopping at `limit` matches, so cost tracks recency not history size.
function codexSessions(folder, limit) {
  const root = path.join(os.homedir(), '.codex', 'sessions');
  if (!fs.existsSync(root)) return [];
  const out = [];
  const desc = (dir) => fs.readdirSync(dir).sort().reverse();
  for (const y of desc(root)) {
    for (const m of desc(path.join(root, y))) {
      for (const d of desc(path.join(root, y, m))) {
        const day = path.join(root, y, m, d);
        for (const f of desc(day)) {
          if (!f.endsWith('.jsonl')) continue;
          const lines = headLines(path.join(day, f));
          let meta;
          try { meta = JSON.parse(lines[0]); } catch { continue; }
          if (meta.type !== 'session_meta' || meta.payload?.cwd !== folder) continue;
          // subagent threads land in the same store with the same cwd (11 present here) — the
          // cwd-only filter presented them as sessions. Absent field = user (every rollout on
          // this box back to the oldest, 2026-07-16, carries it).
          if ((meta.payload.thread_source ?? 'user') !== 'user') continue;
          out.push({
            harness: 'codex',
            id: meta.payload.id,
            file: path.join(day, f), // cast monitor watches this file's mtime as codex's progress signal
            started: Date.parse(meta.timestamp),
            label: codexLabel(lines.slice(1)),
          });
          if (out.length >= limit) return out;
        }
      }
    }
  }
  return out;
}

// opencode: a read-only query on its own store. Not `session list --format json` — that output
// carries no parent_id (measured), and subagent child sessions inherit the parent's directory, so
// via the CLI they are indistinguishable from real sessions. Private schema: absent store or a
// schema change reports on stderr and yields [], never a crash.
//
// directory match is exact OR the queried folder sits under the recorded directory (opencode
// stores the resolved project root, not the launch cwd). Descendants of the queried folder are
// not matches — `cast sessions` on a vault root must not dump every nested project session.
function opencodeStore() {
  return path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share'),
    'opencode', 'opencode.db');
}

function opencodeDirMatch(folder, directory) {
  return folder === directory || folder.startsWith(directory + path.sep);
}

function opencodeCandidates(folder) {
  const store = opencodeStore();
  if (!fs.existsSync(store)) return [];
  try {
    const { DatabaseSync } = require('node:sqlite');
    const rows = new DatabaseSync(store, { readOnly: true }).prepare(
      'select id, title, directory, time_created, time_updated from session where parent_id is null',
    ).all();
    return rows.filter((r) => opencodeDirMatch(folder, r.directory));
  } catch (e) {
    process.stderr.write(`cast: opencode session store unreadable (${e.message})\n`);
    return [];
  }
}

function opencodeSessions(folder, limit) {
  return opencodeCandidates(folder)
    .sort((a, b) => b.time_created - a.time_created)
    .slice(0, limit)
    .map((r) => ({
      harness: 'opencode', id: r.id, started: r.time_created, label: excerpt(r.title ?? ''),
    }));
}

function fmtTime(ms) {
  const d = new Date(ms);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

// cast sessions: which sessions ran in a folder, per harness or across all three, newest first.
function runSessions(rawArgv) {
  let json = false;
  let limit = 10;
  const positional = [];
  for (let i = 0; i < rawArgv.length; i++) {
    const a = rawArgv[i];
    if (a === '--json') {
      json = true;
    } else if (a === '-n') {
      const val = rawArgv[++i];
      limit = Number(val);
      if (!Number.isInteger(limit) || limit < 1) fail(`-n must be a positive integer, got: ${val}`);
    } else if (a.startsWith('-')) {
      fail(`refused: unknown flag '${a}'\nusage: ${SESSIONS_USAGE}`);
    } else {
      positional.push(a);
    }
  }
  if (positional.length > 2) fail(`usage: ${SESSIONS_USAGE}`);
  let harness = null;
  let folderArg = '.';
  if (positional.length === 2) {
    [harness, folderArg] = positional;
  } else if (positional.length === 1) {
    if (HARNESSES.includes(positional[0])) harness = positional[0];
    else folderArg = positional[0];
  }
  if (harness && !HARNESSES.includes(harness)) {
    fail(`refused: '${harness}' is not a known harness\nknown: ${HARNESSES.join(', ')}`);
  }
  const folder = resolveFolder(folderArg);

  // -n caps PER HARNESS, so one busy store can't crowd the others out of the merged view
  const wanted = harness ? [harness] : ['claude', 'codex', 'opencode'];
  const rows = [];
  if (wanted.includes('claude')) {
    rows.push(...claudeSessions(folder).sort((a, b) => b.started - a.started).slice(0, limit));
  }
  if (wanted.includes('codex')) rows.push(...codexSessions(folder, limit));
  if (wanted.includes('opencode')) rows.push(...opencodeSessions(folder, limit));
  rows.sort((a, b) => b.started - a.started);

  if (json) {
    process.stdout.write(`${JSON.stringify(rows.map((r) => ({
      harness: r.harness, id: r.id, started: new Date(r.started).toISOString(), label: r.label,
    })))}\n`);
  } else if (rows.length === 0) {
    process.stdout.write(`no sessions recorded for ${folder}\n`);
  } else {
    const width = Math.max(...rows.map((r) => r.id.length));
    for (const r of rows) {
      const line = `${r.harness.padEnd(8)}  ${r.id.padEnd(width)}  ${fmtTime(r.started)}  ${r.label}`;
      process.stdout.write(`${line.trimEnd()}\n`);
    }
  }
  process.exit(0);
}

module.exports = {
  headLines, excerpt, claudeLabel, codexLabel,
  claudeSessions, codexSessions, opencodeStore, opencodeDirMatch,
  opencodeCandidates, opencodeSessions, fmtTime, runSessions,
};
