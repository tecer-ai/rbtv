'use strict';

// Checked turn memory and append-only owner notes. Recovery never overwrites the
// working file: save rejected bytes beside it, then inject the checked HEAD copy.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { parseBoard } = require('./board.js');

function workspaceFromHome(home) {
  const agents = path.dirname(path.resolve(home));
  const dot = path.dirname(agents);
  return path.basename(agents) === 'agents' && path.basename(dot) === '.rbtv' ? path.dirname(dot) : null;
}

function refuse(message) { throw new Error(`memory check failed: ${message}`); }

function datedRecord(line) {
  const match = line.match(/^- (.+) \((\d{4}-\d{2}-\d{2}) · (.+)\)$/);
  if (!match || !Number.isFinite(Date.parse(`${match[2]}T00:00:00Z`)) ||
      new Date(`${match[2]}T00:00:00Z`).toISOString().slice(0, 10) !== match[2]) {
    refuse('bullets require dated provenance');
  }
  return match;
}

// The workspace template uses a YAML string list, inline or indented. No YAML
// dependency or interpretation of arbitrary frontmatter is needed here.
function workspacePaths(text) {
  const front = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)?.[1];
  if (front == null) refuse('workspace requires frontmatter');
  const rows = front.split(/\r?\n/);
  const declarations = rows.filter((row) => /^paths:/.test(row));
  if (declarations.length !== 1) refuse('workspace requires one paths list');
  const index = rows.indexOf(declarations[0]);
  const value = declarations[0].slice(6).trim();
  let items;
  if (value.startsWith('[') && value.endsWith(']')) {
    const inner = value.slice(1, -1);
    items = [];
    const item = /\s*("(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^,"'\[\]]+?)\s*(?:,|$)/gy;
    let end = 0;
    let match;
    while ((match = item.exec(inner))) { items.push(match[1]); end = item.lastIndex; }
    if (end !== inner.length || /,\s*$/.test(inner)) refuse('invalid paths list');
  } else if (!value) {
    items = [];
    for (const row of rows.slice(index + 1)) {
      if (!row.trim()) continue;
      const item = row.match(/^\s+-\s+(.+)$/);
      if (!item) break;
      items.push(item[1]);
    }
  } else refuse('paths must be a list');
  const paths = items.map((item) => {
    let value = item.trim();
    if (value.startsWith('"')) {
      try { value = JSON.parse(value); } catch { refuse('invalid quoted path'); }
    } else if (value.startsWith("'")) {
      if (!value.endsWith("'")) refuse('invalid quoted path');
      value = value.slice(1, -1).replace(/''/g, "'");
    }
    if (!value || path.posix.isAbsolute(value) || path.win32.isAbsolute(value) || /^[A-Za-z]:/.test(value) ||
        /[\0\r\n]/.test(value) || value.split(/[\\/]/).includes('..')) {
      refuse('paths must be installation-relative folders');
    }
    return value;
  });
  if (!paths.length) refuse('paths must not be empty');
  return paths;
}

function workspaceMatches(workspace, cwd, paths, platformPath = path) {
  return paths.some((folder) => {
    const root = platformPath.resolve(workspace, folder.replace(/[\\/]/g, platformPath.sep));
    const relative = platformPath.relative(root, platformPath.resolve(cwd));
    return relative === '' || (!platformPath.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${platformPath.sep}`));
  });
}

function checkMemory(kind, text) {
  if (kind === 'board') return parseBoard(text);
  if (typeof text !== 'string' || /[\0\r]/.test(text.replace(/\r\n/g, ''))) refuse('expected UTF-8 text with LF or CRLF lines');
  if (kind === 'workspace') {
    const paths = workspacePaths(text);
    if ([...text].length > 3000) refuse('workspace exceeds 3000 characters');
    if (!/^type:\s*workspace\s*$/m.test(text)) refuse('workspace type required');
    const body = text.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
    const lines = body.split(/\r?\n/).filter((line) => line.trim());
    if (!/^# \S/.test(lines[0] || '')) refuse('workspace heading required');
    for (const line of lines.slice(1)) {
      if (/^- Shared docs: \[[^\]]+\]\(.+\)$/.test(line)) continue;
      datedRecord(line);
    }
    return paths;
  }
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  const bullets = lines.filter((line) => line.startsWith('- '));
  if (kind === 'inbox') {
    // No cap here: even an overfull inbox must reach every agent. Headerless
    // lists allow a first append to be one atomic write with no creation race.
    if (lines.some((line, i) => !(i === 0 && /^# Inbox\b/.test(line)) && !line.startsWith('- '))) refuse('inbox requires one record per line');
    bullets.forEach(datedRecord);
    return;
  }
  if (!lines.length || !/^# \S/.test(lines[0])) refuse('heading required');
  if (kind !== 'workspace' && (text.startsWith('---') || text.includes('<!--'))) refuse('injected memory has no frontmatter or comments');
  if (kind === 'profile') {
    if ([...text].length > 4000) refuse('profile exceeds 4000 characters');
    const headings = lines.filter((line) => line.startsWith('## '));
    if (!/^# Profile — \S/.test(lines[0]) || headings.length !== 3 || headings[0] !== '## Who' ||
        !/^## Working with \S/.test(headings[1]) || headings[2] !== '## Now') refuse('profile requires Who, Working with owner, Now');
  } else if (kind === 'learned') {
    if (!/^# Learned rules — \S/.test(lines[0]) || bullets.length > 30) refuse('learned rules require a heading and at most 30 rules');
    for (const bullet of bullets) {
      const record = datedRecord(bullet);
      if (!/^- \[(correction|inferred)\] \S.+ Why: \S/.test(bullet)) refuse('rules require a marker and Why clause');
      const links = [...record[3].matchAll(/\[[^\]]+\]\((https?:\/\/[^\s]+?)\)/g)].map((match) => match[1]);
      if (links.length < 1 || (bullet.startsWith('- [inferred]') && new Set(links).size < 2)) refuse('inferred rules need two distinct conversation links; corrections need one');
    }
  } else if (kind === 'index') {
    const rows = lines.filter((line) => line.startsWith('|'));
    if (rows[0]?.replace(/\s/g, '') !== '|Open|When|' || !/^\|\s*:?-{3,}:?\s*\|\s*:?-{3,}:?\s*\|$/.test(rows[1] || '') ||
        rows.slice(2).some((row) => !/^\|\s*\[[^\]]+\]\([^\s]+\)\s*\|\s*\S.*\|$/.test(row))) refuse('index requires an Open | When table');
    return;
  } else refuse('unknown memory kind');
  if (lines.slice(1).some((line) => !line.startsWith('## ') && !line.startsWith('- '))) refuse('one fact per bullet');
  bullets.forEach(datedRecord);
}

function git(cwd, args) {
  // Decode strictly, including HEAD bytes: malformed UTF-8 must not silently
  // become replacement characters in an otherwise well-shaped memory record.
  const result = spawnSync('git', ['-C', cwd, ...args], { encoding: 'buffer', timeout: 5000, maxBuffer: 8 * 1024 * 1024, windowsHide: true });
  if (result.error || result.status !== 0) throw new Error('HEAD copy unavailable');
  return new TextDecoder('utf-8', { fatal: true }).decode(result.stdout);
}

function headPath(file) {
  // Walk to an existing parent so a deleted directory can still recover from git.
  let dir = path.dirname(file);
  while (!fs.existsSync(dir) && path.dirname(dir) !== dir) dir = path.dirname(dir);
  const root = git(dir, ['rev-parse', '--show-toplevel']).trim();
  return { root, relative: path.relative(root, file).split(path.sep).join('/') };
}

function headText(file) {
  const { root, relative } = headPath(file);
  return git(root, ['show', `HEAD:${relative}`]);
}

function workspaceFiles(dir) {
  const names = new Set();
  try { for (const name of fs.readdirSync(dir)) names.add(name); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  try {
    const { root, relative } = headPath(path.join(dir, 'unused'));
    for (const name of git(root, ['ls-tree', '--name-only', '-z', `HEAD:${path.posix.dirname(relative)}`]).split('\0')) names.add(name);
  } catch { /* An installation may not have its first memory commit yet. */ }
  return [...names].filter((name) => name.endsWith('.md') && !/[\\/]/.test(name)).sort().map((name) => path.join(dir, name));
}

function readMemory(file, kind, alerts) {
  let bytes;
  let reason;
  try {
    bytes = fs.readFileSync(file);
    const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    const paths = checkMemory(kind, text);
    return { text, paths, source: 'working' };
  } catch (error) { reason = error.code || error.message; }
  let saved = '';
  if (bytes) {
    const backup = `${file}.broken-${randomUUID()}`;
    try { fs.writeFileSync(backup, bytes, { flag: 'wx' }); saved = ` Broken copy saved: ${backup}.`; }
    catch { saved = ' Could not save the broken copy; the original is unchanged.'; }
  }
  try {
    const text = headText(file);
    const paths = checkMemory(kind, text);
    alerts.push(`Memory alert: ${file} (${reason}).${saved} Loaded checked HEAD copy; working file unchanged.`);
    return { text, paths, source: 'HEAD' };
  } catch {
    const text = `[MISSING MEMORY: ${file}; no valid HEAD copy available. The turn continues without this memory.]`;
    alerts.push(`Memory alert: ${file} (${reason}).${saved} No valid HEAD copy available; turn continues with a missing note.`);
    return { text, source: null };
  }
}

function remember(workspace, text, { agent, thread = null, now = Date.now() }) {
  const file = path.join(workspace, '.rbtv', 'memory', 'inbox.md');
  const fact = text.replace(/[\r\n\u2028\u2029]+/g, ' ').trim();
  const line = `- ${fact} (${new Date(now).toISOString().slice(0, 10)} · ${agent}${thread ? `/${thread}` : ''})\n`;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  let fd;
  try { fd = fs.openSync(file, fs.constants.O_RDWR | fs.constants.O_APPEND); }
  catch (error) {
    if (error.code !== 'ENOENT') throw error;
    try { fd = fs.openSync(file, fs.constants.O_RDWR | fs.constants.O_APPEND | fs.constants.O_CREAT | fs.constants.O_EXCL, 0o600); }
    catch (race) {
      if (race.code !== 'EEXIST') throw race;
      fd = fs.openSync(file, fs.constants.O_RDWR | fs.constants.O_APPEND);
    }
  }
  try {
    const size = fs.fstatSync(fd).size;
    const last = Buffer.alloc(1);
    if (size) fs.readSync(fd, last, 0, 1, size - 1);
    const bytes = Buffer.from(`${size && last[0] !== 10 ? '\n' : ''}${line}`, 'utf8');
    // One O_APPEND write: simultaneous agents cannot overwrite each other's line.
    if (fs.writeSync(fd, bytes) !== bytes.length) throw new Error('inbox append incomplete');
  } finally { fs.closeSync(fd); }
  let lines = null;
  let warning = null;
  try {
    const rows = fs.readFileSync(file, 'utf8').split(/\r?\n/);
    if (rows.at(-1) === '') rows.pop();
    lines = rows.length;
    if (lines > 20) warning = `Memory inbox has ${lines} lines (over 20); the dreamer needs to file them.`;
  } catch { warning = 'Memory saved, but inbox length could not be checked.'; }
  return { path: file, appended: true, lines, warning };
}

module.exports = { workspaceFromHome, workspacePaths, workspaceMatches, checkMemory, readMemory, workspaceFiles, remember };
