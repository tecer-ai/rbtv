'use strict';

// parseBoard(text) checks the four-section form and caps; throws on refusal.
// writeBoard(file, text) changes subjects and watch-outs, preserving runtime fields.
// closeSubject(file, title, outcome, { agent, thread?, now? }) records a closure.
// All writes are checked before touching the file. No truncation or automatic pruning.

const fs = require('node:fs');
const path = require('node:path');

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

function saveBoard(file, text) {
  parseBoard(text);
  const bytes = Buffer.from(text, 'utf8');
  let fd;
  try {
    fd = fs.openSync(file, 'r+');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fd = fs.openSync(file, 'wx');
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

function writeBoard(file, text) {
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
  return saveBoard(file, text);
}

function closeSubject(file, title, outcome, { agent, thread = null, now = Date.now() }) {
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
  return { ...saveBoard(file, lines.join(text.includes('\r\n') ? '\r\n' : '\n')), subject: title };
}

module.exports = { CAPS, EMPTY_BOARD, parseBoard, writeBoard, closeSubject };
