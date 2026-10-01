'use strict';

// parseBoard(text) checks the four-section form and caps; throws on refusal.
// writeBoard(file, text, { store?, now? }) changes subjects and watch-outs, then refreshes runtime fields when a store is supplied.
// closeSubject(file, title, outcome, { agent, thread?, now?, store? }) records a closure.
// boardPath(home) / migrateBoard(home) — canonical path; explicit install/update migration only.
// refreshBoard(home, store, now?) regenerates Timers and linked-thread Flags.
// All writes are checked before touching the file. No truncation or automatic pruning.

const fs = require('node:fs');
const path = require('node:path');
const { NOFOLLOW, safeWritePath, writeRoot, withMemoryLock } = require('./memory-write.js');

const HEADINGS = ['What matters now', 'Watch-outs', 'Timers', 'Recently closed'];
const CAPS = Object.freeze({ lines: 90, subjects: 8, watchOuts: 6, closed: 6 });
const EMPTY_BOARD = HEADINGS.map((heading) => `## ${heading}\n`).join('\n');
const LINK = /^\[[^\[\]\r\n]+\]\((https?:\/\/[^\s<>]+)\)$/;

function refuse(message) {
  throw new Error(`board refused: ${message}`);
}

function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function validLink(value) {
  const match = value.match(LINK);
  if (!match) return false;
  let depth = 0;
  for (const char of match[1]) {
    if (char === '(') depth++;
    if (char === ')' && --depth < 0) return false;
  }
  if (depth) return false;
  try { return Boolean(new URL(match[1]).hostname); } catch { return false; }
}

function checkUntil(line) {
  if (!/\buntil\b/i.test(line)) return;
  // Ordinary prose such as "wait until the owner replies" is not an expiry.
  if (/\buntil\s+\d{4}-/i.test(line)) {
    const match = line.match(/\buntil (\d{4}-\d{2}-\d{2})$/);
    if (!match || !validDate(match[1])) refuse('temporary facts must end with until YYYY-MM-DD');
  }
}

function checkProvenance(line, closed) {
  const match = line.match(/^- (.+) \((\d{4}-\d{2}-\d{2}) · ([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\/(.+))?\)$/);
  if (!match || !validDate(match[2]) || (match[4] && !validLink(match[4]))) {
    refuse('watch-outs and closed lines require (YYYY-MM-DD · agent[/[label](URL)]) provenance');
  }
  if (closed && !/^\S.* — \S.*$/.test(match[1])) refuse('closed lines require a subject — outcome');
  checkUntil(match[1]);
}

function checkTimers(lines) {
  if (!lines.length) return;
  const cells = lines.map((line) => {
    if (!line.startsWith('|') || !line.endsWith('|')) refuse('Timers must be a four-column table');
    const row = line.slice(1, -1).split('|').map((cell) => cell.trim());
    if (row.length !== 4) refuse('Timers must be a four-column table');
    return row;
  });
  if (cells[0].join('|') !== 'Fires|Timer|For|Subject' || !cells[1]?.every((cell) => /^:?-{3,}:?$/.test(cell))) {
    refuse('Timers requires Fires | Timer | For | Subject and a separator row');
  }
  for (const row of cells.slice(2)) {
    const fire = row[0].match(/^(\d{4}-\d{2}-\d{2}) ([01]\d|2[0-3]):[0-5]\d (\S+)$/);
    if (!fire || !validDate(fire[1]) || row.some((cell) => !cell)) refuse('Timers requires a next fire YYYY-MM-DD HH:MM IANA-zone and four non-empty cells');
    try {
      new Intl.DateTimeFormat('en', { timeZone: fire[3] });
    } catch {
      refuse('Timers requires an IANA time zone');
    }
  }
}

function parseBoard(text) {
  if (typeof text !== 'string') refuse('expected Markdown text');
  if (/[\r\0]/.test(text.replace(/\r\n/g, ''))) refuse('use LF or CRLF lines without NUL characters');
  const lines = text.split(/\r?\n/);
  const sections = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^## /.test(line)) {
      if (line !== `## ${HEADINGS[sections.length]}`) refuse('expected the four board headings in order');
      if (sections.length) sections[sections.length - 1].end = i;
      sections.push({ start: i, end: lines.length, rows: [] });
    } else if (line.trim()) {
      if (!sections.length) refuse('board must start with ## What matters now');
      sections[sections.length - 1].rows.push({ line, index: i });
    }
  }
  if (sections.length !== 4) refuse('all four board headings are required');
  const nonEmpty = lines.filter((line) => line.trim()).length - sections[2].rows.length;
  if (nonEmpty > CAPS.lines) refuse(`at most ${CAPS.lines} non-empty lines outside the Timers table`);

  const subjects = [];
  const rows = sections[0].rows;
  for (let i = 0; i < rows.length;) {
    const first = rows[i];
    const title = first.line.match(/^### (\S.*)$/)?.[1];
    if (!title || title.trim() !== title) refuse('subjects require a non-empty ### title');
    if (subjects.some((subject) => subject.title === title)) refuse('subject titles must be unique');
    const start = i++;
    while (i < rows.length && !rows[i].line.startsWith('### ')) i++;
    const body = rows.slice(start + 1, i).map((row) => row.line);
    const state = body.slice(0, -3);
    if (state.length < 1 || state.length > 3 || state.some((line) => /^(?:#|\||- (?:Threads|Detail|Flags|Timers):)/.test(line))) {
      refuse('each subject requires 1–3 state lines, then Threads, Detail, Flags');
    }
    state.forEach(checkUntil);
    const threads = body[body.length - 3].match(/^- Threads: (.+)$/)?.[1];
    const detail = body[body.length - 2].match(/^- Detail: (.+)$/)?.[1];
    const flags = body[body.length - 1].match(/^- Flags: (none|answered \d{4}-\d{2}-\d{2}|idle since \d{4}-\d{2}-\d{2})$/)?.[1];
    if (!threads || (threads !== 'none' && !threads.split(' · ').every(validLink))) refuse('Threads requires none or [label](URL) links separated by ·');
    if (!detail || (detail !== 'none' && !/^(?:[^<>]+\.md|\[[^\[\]]+\]\([^<>]+\.md\))$/.test(detail))) refuse('Detail requires none or a Markdown page path/link');
    if (!flags || (flags !== 'none' && !validDate(flags.slice(-10)))) refuse('Flags requires none, answered YYYY-MM-DD, or idle since YYYY-MM-DD');
    subjects.push({ title, state, threads, detail, flags, start: first.index, end: rows[i]?.index ?? sections[0].end });
  }
  if (subjects.length > CAPS.subjects) refuse(`at most ${CAPS.subjects} subjects`);
  const watchOuts = sections[1].rows.map((row) => row.line);
  const timers = sections[2].rows.map((row) => row.line);
  const closed = sections[3].rows.map((row) => row.line);
  if (watchOuts.length > CAPS.watchOuts) refuse(`at most ${CAPS.watchOuts} watch-outs`);
  if (closed.length > CAPS.closed) refuse(`at most ${CAPS.closed} Recently closed lines; archive old entries before closing another subject`);
  watchOuts.forEach((line) => checkProvenance(line, false));
  closed.forEach((line) => checkProvenance(line, true));
  checkTimers(timers);
  return { subjects, watchOuts, timers, closed, nonEmpty, lines, sections };
}

function readBoard(file) {
  try {
    return fs.readFileSync(file, 'utf8');
  } catch (error) {
    if (error.code === 'ENOENT') return EMPTY_BOARD;
    throw error;
  }
}

function boardPath(home) {
  return path.join(home, '_artifacts', 'board.md');
}

function migrateBoard(home) {
  return withMemoryLock(writeRoot(boardPath(home)), () => {
    safeWritePath(writeRoot(boardPath(home)), boardPath(home));
    const file = boardPath(home);
    const legacy = path.join(home, 'board.md');
    if (!fs.existsSync(file) && fs.existsSync(legacy)) {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      try {
        fs.copyFileSync(legacy, file, fs.constants.COPYFILE_EXCL);
      } catch (error) {
        if (error.code !== 'EEXIST') throw error;
      }
    }
    return file;
  });
}

function preflightBoard(home) {
  const file = boardPath(home);
  try {
    safeWritePath(writeRoot(file), file);
    parseBoard(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    refuse(`${file}: ${error.code === 'ENOENT' ? 'board is missing' : error.message.replace(/^board refused: /, '')}`);
  }
}

function timerCell(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/\|/g, '&#124;')
    .replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\r?\n/g, '<br>').trim() || 'none';
}

function timerRows(schedules, pending) {
  return ['| Fires | Timer | For | Subject |', '|---|---|---|---|', ...schedules
    .filter((row) => (row.enabled || pending.has(row.id)) && row.next_at != null)
    .sort((a, b) => a.next_at - b.next_at || a.id.localeCompare(b.id))
    .map((row) => {
      // Elapsed intervals and numeric offsets have no IANA zone; display their instant in UTC.
      const zone = row.cadence.startsWith('cron:') ? row.timezone : 'UTC';
      const parts = {};
      for (const part of new Intl.DateTimeFormat('en-US', {
        timeZone: zone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit',
      }).formatToParts(new Date(row.next_at))) parts[part.type] = part.value;
      const fire = `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute} ${zone}`;
      return `| ${fire} | ${timerCell(row.id)} | ${timerCell(row.note)} | ${timerCell(row.subject)} |`;
    })];
}

function threadFlags(subject, store, now) {
  let latestReply = null;
  let latestRoot = null;
  if (subject.threads === 'none') return subject.flags;
  for (const link of subject.threads.split(' · ')) {
    const url = new URL(link.match(LINK)[1]);
    if (url.hostname !== 'slack.com' && !url.hostname.endsWith('.slack.com')) continue;
    const match = url.pathname.match(/^\/archives\/([A-Z0-9]+)\/p(\d+)$/);
    if (!match || match[2].length <= 6) continue;
    const rootTs = url.searchParams.get('thread_ts') || `${match[2].slice(0, -6)}.${match[2].slice(-6)}`;
    if (!/^\d+\.\d+$/.test(rootTs)) continue;
    const root = Math.round(Number(rootTs) * 1000);
    if (!Number.isFinite(root) || root > now) continue;
    latestRoot = Math.max(latestRoot ?? root, root);
    const reply = store.lastOwnerReply(match[1], rootTs, now);
    if (reply != null) latestReply = Math.max(latestReply ?? reply, reply);
  }
  const since = latestReply ?? latestRoot;
  if (since == null) return subject.flags;
  const date = new Date(since).toISOString().slice(0, 10);
  if (now - since >= 7 * 86_400_000) return `idle since ${date}`;
  return latestReply == null ? 'none' : `answered ${date}`;
}

function renderBoard(text, store, now = Date.now()) {
  const board = parseBoard(text);
  const lines = board.lines.slice();
  for (const subject of board.subjects) {
    const index = lines.findIndex((line, i) => i > subject.start && i < subject.end && line.startsWith('- Flags: '));
    lines[index] = `- Flags: ${threadFlags(subject, store, now)}`;
  }
  const section = board.sections[2];
  lines.splice(section.start + 1, section.end - section.start - 1, '',
    ...timerRows(store.listSchedules(), new Set(store.pendingScheduleIds())), '');
  const rendered = lines.join(text.includes('\r\n') ? '\r\n' : '\n');
  parseBoard(rendered);
  return rendered;
}

function refreshBoard(home, store, now = Date.now()) {
  return withMemoryLock(writeRoot(boardPath(home)), () => {
    safeWritePath(writeRoot(boardPath(home)), boardPath(home));
    const file = boardPath(home);
    let text;
    try { text = fs.readFileSync(file, 'utf8'); }
    catch (error) {
      // Installation creates the board. A tick must not conceal a deleted board
      // with an empty one before turn-start memory recovery can load HEAD/alert.
      if (error.code === 'ENOENT') return { path: file, changed: false };
      throw error;
    }
    return saveBoard(file, renderBoard(text, store, now));
  });
}

// SQLite has already committed. A failed projection must not invite a mutation retry.
function refreshBoardAfterCommit(home, store, ids, now = Date.now()) {
  try { refreshBoard(home, store, now); return null; }
  catch { return `${ids.join(', ')} committed; board refresh pending`; }
}

function saveBoard(file, text) {
  parseBoard(text);
  const bytes = Buffer.from(text, 'utf8');
  let fd;
  try {
    safeWritePath(writeRoot(file), file);
    fd = fs.openSync(file, fs.constants.O_RDWR | NOFOLLOW);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    fs.mkdirSync(path.dirname(file), { recursive: true });
    safeWritePath(writeRoot(file), file);
    fd = fs.openSync(file, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | NOFOLLOW, 0o600);
  }
  try {
    // Compare exact bytes, and rewrite an existing file in place (Windows Hidden/System).
    if (fs.readFileSync(file).equals(bytes)) return { path: file, changed: false };
    fs.writeFileSync(fd, bytes);
    fs.ftruncateSync(fd, bytes.length);
  } finally {
    fs.closeSync(fd);
  }
  return { path: file, changed: true };
}

function writeBoard(file, text, { store = null, now = Date.now() } = {}) {
  return withMemoryLock(writeRoot(file), () => {
    safeWritePath(writeRoot(file), file);
    const next = parseBoard(text);
    const previous = parseBoard(readBoard(file));
    if (JSON.stringify(next.timers) !== JSON.stringify(previous.timers)) refuse('Timers is written by Ignite; keep its current rows');
    if (JSON.stringify(next.closed) !== JSON.stringify(previous.closed)) refuse('Recently closed is written by board close; keep its current rows');
    for (const subject of previous.subjects) {
      if (!next.subjects.some((row) => row.title === subject.title)) refuse('use board close to remove a subject');
    }
    for (const subject of next.subjects) {
      const old = previous.subjects.find((row) => row.title === subject.title);
      if (subject.flags !== (old?.flags ?? 'none')) refuse('Flags is written by Ignite; use none for new subjects and keep existing flags');
    }
    return saveBoard(file, store ? renderBoard(text, store, now) : text);
  });
}

function closeSubject(file, title, outcome, { agent, thread = null, now = Date.now(), store = null }) {
  return withMemoryLock(writeRoot(file), () => {
    safeWritePath(writeRoot(file), file);
    const text = readBoard(file);
    const board = parseBoard(text);
    const subject = board.subjects.find((row) => row.title === title);
    if (!subject) refuse('subject not found; use its exact title from the board');
    if (typeof outcome !== 'string' || !outcome.trim() || /[\r\n]/.test(outcome)) refuse('close requires a one-line outcome');
    if (typeof agent !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(agent)) refuse('close requires an agent slug');
    if (thread !== null && (typeof thread !== 'string' || !validLink(thread))) refuse('close thread must be a [label](URL) link');
    const date = new Date(now).toISOString().slice(0, 10);
    const entry = `- ${title} — ${outcome.trim()} (${date} · ${agent}${thread ? `/${thread}` : ''})`;
    const lines = board.lines.slice();
    while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
    lines.push(entry, '');
    lines.splice(subject.start, subject.end - subject.start);
    const next = lines.join(text.includes('\r\n') ? '\r\n' : '\n');
    return { ...saveBoard(file, store ? renderBoard(next, store, now) : next), subject: title };
  });
}

module.exports = { CAPS, EMPTY_BOARD, parseBoard, writeBoard, closeSubject, boardPath, migrateBoard, refreshBoard, refreshBoardAfterCommit, renderBoard, preflightBoard };
