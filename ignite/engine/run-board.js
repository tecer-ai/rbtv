'use strict';

// The human live view for `rbtv run`: a three-column seat board plus a happening log.
// Empty ticks move only the tick number; a seat start / finish / fail / ask / unblock
// is the only thing that appends to happening. `--json` never comes here.

const { executionsByJob, jobIdFor } = require('./seeding');

const OFF = '\x1b[0m';
const BOLD = '\x1b[1m';
const DIM = '\x1b[2m';
const RED = '\x1b[31m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const CYAN = '\x1b[36m';
const ANSI_RE = /\x1b\[[0-9;]*m/g;
const TICK_CHATTER = /^tick \d+ (start|end)/;

function visibleLen(s) {
  return String(s).replace(ANSI_RE, '').length;
}

function clip(s, width) {
  if (width <= 0) return '';
  if (visibleLen(s) <= width) return s;
  if (width === 1) return '…';
  let out = '';
  let vis = 0;
  for (const chunk of String(s).split(/(\x1b\[[0-9;]*m)/)) {
    if (chunk.startsWith('\x1b')) {
      out += chunk;
      continue;
    }
    const room = width - 1 - vis;
    if (room <= 0) break;
    out += chunk.slice(0, room);
    vis += Math.min(chunk.length, room);
    if (vis >= width - 1) break;
  }
  return `${out}…${OFF}`;
}

function padEndVis(s, width) {
  const n = visibleLen(s);
  if (n >= width) return clip(s, width);
  return s + ' '.repeat(width - n);
}

function elapsedSince(iso, nowMs) {
  if (!iso) return '';
  const s = Math.max(0, Math.floor((nowMs - Date.parse(iso)) / 1000));
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  return h ? `${h}h${String(m % 60).padStart(2, '0')}m`
    : m ? `${m}m${String(s % 60).padStart(2, '0')}s`
      : `${s}s`;
}

function hhmm(d) {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function afterList(row) {
  return String(row.after || '').split(',').map((s) => s.trim()).filter(Boolean);
}

function seatNameOf(jobId) {
  const m = /^seat-(.+)$/.exec(jobId || '');
  return m ? m[1] : null;
}

function isChatter(m) {
  const msg = String((m && m.message) || '');
  return TICK_CHATTER.test(msg) || msg === 'tick skipped: already running';
}

function snapshotFrom(heartStore, rows, {
  isHeld = null, view, ready = null, tick, goal, asks = [],
} = {}) {
  const running = new Map();
  for (const status of ['launching', 'running', 'stalled']) {
    for (const ex of heartStore.listExecutionsByStatus(status)) {
      const seat = seatNameOf(ex.job_id);
      if (seat) running.set(seat, { since: ex.started_at || ex.fired_at || null, status });
    }
  }
  const queued = new Set();
  for (const q of heartStore.listQueue()) {
    const seat = seatNameOf(q.job_id);
    if (seat) queued.add(seat);
  }
  const byJob = executionsByJob(heartStore);
  const finishedSet = (view && view.finished) || new Set();
  const blockedMap = (view && view.blocked) || new Map();
  const foreignMap = (view && view.foreign) || new Map();

  const blocked = [];
  const live = [];
  const finished = [];

  for (const row of rows) {
    const seat = row.seat;
    const unmet = afterList(row).filter((a) => !finishedSet.has(a));
    const held = Boolean(isHeld && isHeld(seat));

    if (running.has(seat)) {
      const info = running.get(seat);
      live.push({
        seat,
        kind: info.status === 'stalled' ? 'stalled' : 'running',
        since: info.since,
        held,
      });
      continue;
    }
    if (finishedSet.has(seat)) {
      finished.push({ seat, kind: 'done' });
      continue;
    }
    const execs = byJob.get(jobIdFor(seat)) || [];
    const last = execs[execs.length - 1];
    if (last && (last.status === 'failed' || last.status === 'killed')) {
      finished.push({ seat, kind: last.status });
      continue;
    }
    if (blockedMap.has(seat)) {
      blocked.push({ seat, waitingOn: ['you'] });
      continue;
    }
    if (foreignMap.has(seat)) {
      const ev = String(foreignMap.get(seat) || '');
      if (/still OPEN/.test(ev)) live.push({ seat, kind: 'other', since: null, held: false });
      else finished.push({ seat, kind: 'failed' });
      continue;
    }
    if (ready && ready.has(seat)) {
      live.push({ seat, kind: 'ready', since: null, held });
      continue;
    }
    if (queued.has(seat)) {
      live.push({ seat, kind: 'queued', since: null, held });
      continue;
    }
    blocked.push({ seat, waitingOn: unmet });
  }

  return {
    goal: goal || '',
    tick: Number.isFinite(tick) ? tick : 0,
    blocked,
    live,
    finished,
    asks: asks.slice(),
  };
}

function boardKey(snap) {
  if (!snap) return '';
  const pack = (xs, extra) => xs.map((s) => `${s.seat}:${s.kind || ''}:${extra(s)}`).join(',');
  return [
    pack(snap.blocked, (s) => (s.waitingOn || []).join('+')),
    pack(snap.live, (s) => s.kind),
    pack(snap.finished, (s) => s.kind),
    (snap.asks || []).map((a) => a.msgId).join(','),
  ].join('|');
}

function eventsFrom(prev, next) {
  const events = [];
  if (!next) return events;

  const prevAsk = new Set((prev && prev.asks ? prev.asks : []).map((a) => a.msgId));
  for (const a of next.asks || []) {
    if (prevAsk.has(a.msgId)) continue;
    const body = String(a.corpus || '').split('\n')[0].slice(0, 80);
    events.push(`${a.sender || 'seat'} asked: ${body}`);
  }

  if (!prev) return events;

  const prevBy = new Map();
  for (const s of prev.blocked) prevBy.set(s.seat, { col: 'blocked', ...s });
  for (const s of prev.live) prevBy.set(s.seat, { col: 'live', ...s });
  for (const s of prev.finished) prevBy.set(s.seat, { col: 'finished', ...s });

  const describeBlocked = (s) => {
    const waiting = s.waitingOn || [];
    if (waiting.includes('you')) return `${s.seat} held for you`;
    const w = waiting.join(', ');
    return w ? `${s.seat} waiting on ${w}` : `${s.seat} waiting`;
  };

  const consider = (s, col) => {
    const was = prevBy.get(s.seat);
    if (!was) {
      if (col === 'live' && (s.kind === 'running' || s.kind === 'other')) events.push(`${s.seat} started`);
      else if (col === 'live' && s.kind === 'ready') events.push(`${s.seat} ready`);
      else if (col === 'live' && s.kind === 'queued') events.push(`${s.seat} queued`);
      else if (col === 'live' && s.kind === 'stalled') events.push(`${s.seat} stalled`);
      else if (col === 'finished' && s.kind === 'done') events.push(`${s.seat} finished`);
      else if (col === 'finished') events.push(`${s.seat} ${s.kind}`);
      else if (col === 'blocked') events.push(describeBlocked(s));
      return;
    }
    if (was.col === col && (was.kind || '') === (s.kind || '')) {
      if (col === 'blocked' && (was.waitingOn || []).join() !== (s.waitingOn || []).join()) {
        events.push(describeBlocked(s));
      }
      return;
    }
    if (col === 'live' && (s.kind === 'running' || s.kind === 'other') && was.kind !== 'running') {
      events.push(`${s.seat} started`);
    } else if (col === 'live' && s.kind === 'ready' && was.col === 'blocked') {
      events.push(`${s.seat} unblocked`);
    } else if (col === 'live' && s.kind === 'stalled') {
      events.push(`${s.seat} stalled`);
    } else if (col === 'finished' && s.kind === 'done') {
      events.push(`${s.seat} finished`);
    } else if (col === 'finished') {
      events.push(`${s.seat} ${s.kind}`);
    } else if (col === 'blocked') {
      events.push(describeBlocked(s));
    }
  };

  for (const s of next.blocked) consider(s, 'blocked');
  for (const s of next.live) consider(s, 'live');
  for (const s of next.finished) consider(s, 'finished');
  return events;
}

function paintCell(s, col, { color, nowMs }) {
  const c = color
    ? { dim: DIM, off: OFF, red: RED, green: GREEN, yellow: YELLOW }
    : { dim: '', off: '', red: '', green: '', yellow: '' };
  if (col === 'blocked') {
    const waiting = s.waitingOn || [];
    const dep = waiting.length ? `  ← ${waiting.join(', ')}` : '';
    return `${s.seat}${c.dim}${dep}${c.off}`;
  }
  if (col === 'live') {
    if (s.kind === 'running') {
      const up = elapsedSince(s.since, nowMs);
      return `${c.green}${s.seat}${c.off}${up ? `${c.dim}  ${up}${c.off}` : ''}`;
    }
    if (s.kind === 'stalled') {
      return `${c.yellow}${s.seat}${c.off}${c.dim}  stalled${c.off}`;
    }
    if (s.kind === 'other') {
      return `${s.seat}${c.dim}  other lane${c.off}`;
    }
    const tag = s.kind === 'queued' ? 'queued' : 'ready';
    const you = s.held ? ' · you' : '';
    return `${c.dim}${s.seat}  ${tag}${you}${c.off}`;
  }
  if (s.kind === 'failed' || s.kind === 'killed') {
    return `${c.red}${s.seat}  ✕${c.off}`;
  }
  return `${c.dim}${s.seat}${c.off}`;
}

function renderBoard(snapshot, { cols = 80, rows = 24, color = false, events = [], nowMs = Date.now() } = {}) {
  const c = color
    ? { bold: BOLD, dim: DIM, off: OFF, yellow: YELLOW, green: GREEN, cyan: CYAN }
    : { bold: '', dim: '', off: '', yellow: '', green: '', cyan: '' };
  const width = Math.max(40, cols);
  const gutter = 2;
  const colW = Math.max(12, Math.floor((width - 2 - gutter * 2) / 3));

  const tick = String(snapshot.tick);
  const left = `${c.bold}rbtv run${c.off}  ·  ${snapshot.goal}`;
  const right = `${c.dim}tick${c.off} ${c.bold}${tick}${c.off}`;
  const gap = Math.max(2, width - 2 - visibleLen(left) - visibleLen(right));
  const header = clip(`  ${left}${' '.repeat(gap)}${right}`, width);

  const heads = [
    `${c.bold}${c.yellow}BLOCKED${c.off}`,
    `${c.bold}${c.green}LIVE${c.off}`,
    `${c.bold}${c.dim}FINISHED${c.off}`,
  ].map((h) => padEndVis(h, colW)).join(' '.repeat(gutter));

  const columns = {
    blocked: snapshot.blocked || [],
    live: snapshot.live || [],
    finished: snapshot.finished || [],
  };
  const headerLines = 3;
  const happenHead = 2;
  const minHappen = 4;
  const maxBoard = Math.max(1, rows - headerLines - happenHead - minHappen - 1);
  const needed = Math.max(columns.blocked.length, columns.live.length, columns.finished.length, 1);
  const boardH = Math.min(maxBoard, needed);

  const sliceCol = (xs) => {
    if (xs.length <= boardH) return xs.slice();
    const keep = boardH - 1;
    return xs.slice(0, keep).concat([{ _more: xs.length - keep }]);
  };
  const blocked = sliceCol(columns.blocked);
  const live = sliceCol(columns.live);
  const finished = sliceCol(columns.finished);

  const boardLines = [];
  for (let i = 0; i < boardH; i += 1) {
    const cell = (item, col) => {
      if (!item) return padEndVis('', colW);
      if (item._more) return padEndVis(`${c.dim}+${item._more} more${c.off}`, colW);
      return padEndVis(paintCell(item, col, { color, nowMs }), colW);
    };
    boardLines.push(`  ${cell(blocked[i], 'blocked')}${' '.repeat(gutter)}${cell(live[i], 'live')}${' '.repeat(gutter)}${cell(finished[i], 'finished')}`);
  }

  const used = headerLines + boardLines.length + happenHead;
  const happenRoom = Math.max(minHappen, rows - used - 1);
  const shown = events.slice(-happenRoom);
  const happenTitle = `  ${c.dim}── happening ──${c.off}`;
  const happenLines = shown.length
    ? shown.map((e) => clip(`  ${c.dim}${e.at}${c.off}  ${e.text}`, width))
    : [clip(`  ${c.dim}quiet${c.off}`, width)];

  return [header, '', `  ${heads}`, ...boardLines, '', happenTitle, ...happenLines]
    .map((line) => clip(line, width));
}

function createBoard({ goal, stream, tty, now = () => new Date() } = {}) {
  const color = Boolean(tty) && !process.env.NO_COLOR;
  let snapshot = { goal: goal || '', tick: 0, blocked: [], live: [], finished: [], asks: [] };
  let events = [];
  const seenLog = new Set();
  let suspended = false;
  let cursorHidden = false;

  function size() {
    return {
      cols: (stream && stream.columns) || (process.stdout && process.stdout.columns) || 80,
      rows: (stream && stream.rows) || (process.stdout && process.stdout.rows) || 24,
    };
  }

  function hideCursor() {
    if (tty && stream && !cursorHidden) {
      stream.write('\x1b[?25l');
      cursorHidden = true;
    }
  }

  function showCursor() {
    if (cursorHidden && stream) {
      stream.write('\x1b[?25h');
      cursorHidden = false;
    }
  }

  function paint() {
    if (suspended || !stream) return;
    const { cols, rows } = size();
    const lines = renderBoard(snapshot, { cols, rows, color, events, nowMs: now().getTime() });
    if (tty) {
      hideCursor();
      stream.write(`\x1b[H\x1b[2J${lines.join('\n')}\n`);
    } else {
      stream.write(`${lines.join('\n')}\n`);
    }
  }

  return {
    get tty() { return Boolean(tty); },
    get events() { return events.slice(); },
    get snapshot() { return snapshot; },
    update(next) {
      const virgin = snapshot.tick === 0
        && !snapshot.blocked.length && !snapshot.live.length && !snapshot.finished.length;
      const fresh = eventsFrom(virgin ? null : snapshot, next);
      const changed = boardKey(snapshot) !== boardKey(next) || fresh.length;
      events.push(...fresh.map((text) => ({ at: hhmm(now()), text })));
      if (events.length > 200) events = events.slice(-200);
      snapshot = next;
      if (tty || changed) paint();
    },
    repaint() {
      if (tty) paint();
    },
    ingestLog(m) {
      if (isChatter(m)) return;
      const seat = m.seat ? ` [${m.seat}]` : '';
      const why = m.evidence ? ` — ${String(m.evidence).split('\n')[0].slice(0, 120)}` : '';
      const text = `${m.message || ''}${seat}${why}`;
      const key = `${m.seat || ''}|${m.message || ''}`;
      if (seenLog.has(key)) return;
      seenLog.add(key);
      events.push({ at: hhmm(now()), text });
      if (!suspended) paint();
    },
    suspend(seat) {
      suspended = true;
      showCursor();
      if (!stream) return;
      if (tty) stream.write('\x1b[H\x1b[2J');
      stream.write(`entering ${seat} — the board returns when this seat exits\n`);
    },
    resume() {
      suspended = false;
      paint();
    },
    close() {
      showCursor();
    },
  };
}

module.exports = {
  snapshotFrom,
  eventsFrom,
  renderBoard,
  createBoard,
  isChatter,
  boardKey,
  clip,
  visibleLen,
  elapsedSince,
};
