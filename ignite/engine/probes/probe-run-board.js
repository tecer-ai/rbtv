'use strict';

// probe-run-board — the live `rbtv run` board (three columns + happening).
//
// WHAT IT GUARDS:
//   1. Classification: ready → LIVE dim; failed → FINISHED ✕; waiting-on-after → BLOCKED with dep.
//   2. Events: first picture is quiet (no flood); a transition appends; tick chatter never does.
//   3. Frame: tick sits in the header; happening only carries events; every line fits the width.
//   4. TTY paint uses a home+clear; non-TTY does not.

const fs = require('node:fs');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-run-board.out');
const lines = [];
const emit = (s) => { lines.push(s); };
const failures = [];
function check(name, ok, detail) {
  emit(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok || detail === undefined ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(name);
}

const {
  snapshotFrom, eventsFrom, renderBoard, createBoard, isChatter, clip, visibleLen,
} = require('../run-board');

function fakeStore({ live = [], history = [], queue = [] } = {}) {
  return {
    listExecutionsByStatus(status) {
      return [...live, ...history].filter((e) => e.status === status);
    },
    listQueue: () => queue,
  };
}

const iso = '2026-08-18T12:00:00Z';
const rows = [
  { seat: 'planner', after: '' },
  { seat: 'writer', after: 'planner' },
  { seat: 'researcher', after: '' },
  { seat: 'reviewer', after: 'planner' },
  { seat: 'lint', after: '' },
  { seat: 'tester', after: 'planner' },
  { seat: 'held', after: '' },
];
const view = {
  finished: new Set(['lint']),
  blocked: new Map([['held', 'unanswered ask']]),
  foreign: new Map(),
};
const store = fakeStore({
  live: [{ job_id: 'seat-researcher', status: 'running', started_at: iso }],
  history: [{ job_id: 'seat-writer', status: 'failed' }],
  queue: [],
});
const snap = snapshotFrom(store, rows, {
  isHeld: (s) => s === 'reviewer',
  view,
  ready: new Set(['reviewer']),
  tick: 47,
  goal: 'planning-the-forge',
  asks: [],
});

const byCol = {
  blocked: snap.blocked.map((s) => s.seat),
  live: snap.live.map((s) => `${s.seat}:${s.kind}`),
  finished: snap.finished.map((s) => `${s.seat}:${s.kind}`),
};

check('BLOCKED holds the unmet-after seat and the owner-held seat',
  byCol.blocked.includes('planner') && byCol.blocked.includes('tester')
    && byCol.blocked.includes('held')
    && !byCol.blocked.includes('reviewer') && !byCol.blocked.includes('writer'),
  JSON.stringify(byCol.blocked));
check('BLOCKED shows the dependency, and owner-hold as you',
  (snap.blocked.find((s) => s.seat === 'tester') || {}).waitingOn.join() === 'planner'
    && (snap.blocked.find((s) => s.seat === 'held') || {}).waitingOn.join() === 'you',
  JSON.stringify(snap.blocked));
check('LIVE carries the running seat and the ready-but-not-started seat (dim-ready)',
  byCol.live.includes('researcher:running') && byCol.live.includes('reviewer:ready'),
  JSON.stringify(byCol.live));
check('ready interactive is marked held',
  (snap.live.find((s) => s.seat === 'reviewer') || {}).held === true);
check('FINISHED carries done and failed — failed is not LIVE or BLOCKED',
  byCol.finished.includes('lint:done') && byCol.finished.includes('writer:failed')
    && !byCol.live.some((s) => s.startsWith('writer:'))
    && !byCol.blocked.includes('writer'),
  JSON.stringify(byCol.finished));

const first = eventsFrom(null, snap);
check('the first picture emits no board flood — only new asks (none here)',
  first.length === 0, JSON.stringify(first));

const later = snapshotFrom(store, rows, {
  isHeld: (s) => s === 'reviewer',
  view: { finished: new Set(['lint', 'planner']), blocked: new Map(), foreign: new Map() },
  ready: new Set(['reviewer']),
  tick: 48,
  goal: 'planning-the-forge',
  asks: [{ msgId: 3, sender: 'writer', corpus: 'which file?\nmore' }],
});
const moved = eventsFrom(snap, later);
check('a newly finished seat and a new ask become happening lines',
  moved.includes('planner finished') && moved.some((e) => /writer asked: which file\?/.test(e)),
  JSON.stringify(moved));

const started = eventsFrom(
  { ...snap, live: snap.live.filter((s) => s.seat !== 'researcher') },
  snap,
);
check('a seat entering running emits started',
  started.includes('researcher started'), JSON.stringify(started));

check('tick start/end is chatter and is not an event',
  isChatter({ message: 'tick 12 start' }) && isChatter({ message: 'tick 12 end' })
    && !isChatter({ message: 'researcher started' }));

const frame = renderBoard(snap, {
  cols: 80, rows: 24, color: false, nowMs: Date.parse('2026-08-18T12:03:12Z'),
  events: [{ at: '12:04', text: 'researcher started' }, { at: '12:05', text: 'planner finished' }],
}).join('\n');
check('the frame carries the three column headers and the tick in the header',
  /BLOCKED/.test(frame) && /LIVE/.test(frame) && /FINISHED/.test(frame)
    && /tick 47/.test(frame) && /rbtv run/.test(frame)
    && /planning-the-forge/.test(frame),
  frame.split('\n')[0]);
check('happening lists events and not a rolling tick line',
  /happening/.test(frame) && /researcher started/.test(frame)
    && !/tick 47 start/.test(frame) && !/tick 47 end/.test(frame));
check('blocked owner-hold shows ← you, failed shows ✕, ready is labelled',
  /held/.test(frame) && /← you/.test(frame) && /writer/.test(frame) && /✕/.test(frame)
    && /reviewer/.test(frame) && /ready/.test(frame),
  frame);
check('every painted line fits the width (a wrap would scroll the tick off)',
  frame.split('\n').every((l) => visibleLen(l) <= 80),
  frame.split('\n').map((l) => visibleLen(l)).join(','));
check('clip is ANSI-aware and never exceeds the width',
  visibleLen(clip('abcdefghij', 5)) <= 5 && visibleLen(clip('\x1b[32mabcdefghij\x1b[0m', 5)) <= 5);

const chunks = [];
const fakeTty = { write: (s) => { chunks.push(s); }, columns: 80, rows: 24 };
const ttyBoard = createBoard({
  goal: 'planning-the-forge',
  stream: fakeTty,
  tty: true,
  now: () => new Date('2026-08-18T12:04:00Z'),
});
ttyBoard.update(snap);
check('TTY paint homes and clears so the tick stays in one cell',
  chunks.some((s) => s.includes('\x1b[H\x1b[2J')),
  chunks[0] ? chunks[0].slice(0, 40) : 'no write');
ttyBoard.close();

const plain = [];
const fakePlain = { write: (s) => { plain.push(s); }, columns: 80, rows: 24 };
const plainBoard = createBoard({
  goal: 'planning-the-forge',
  stream: fakePlain,
  tty: false,
  now: () => new Date('2026-08-18T12:04:00Z'),
});
plainBoard.update(snap);
plainBoard.ingestLog({ message: 'tick 9 start' });
plainBoard.ingestLog({ message: 'tick 9 end' });
check('non-TTY paint does not home+clear, and tick chatter does not append',
  plain.every((s) => !s.includes('\x1b[H\x1b[2J'))
    && !plainBoard.events.some((e) => /tick \d+ (start|end)/.test(e.text)),
  JSON.stringify(plainBoard.events));
plainBoard.ingestLog({ level: 'warn', message: 'execution record NOT published this tick', seat: 'x' });
check('a real engine warning does land in happening, once',
  plainBoard.events.filter((e) => /NOT published/.test(e.text)).length === 1);
plainBoard.ingestLog({ level: 'warn', message: 'execution record NOT published this tick', seat: 'x' });
check('…and the same warning is not repeated every tick',
  plainBoard.events.filter((e) => /NOT published/.test(e.text)).length === 1);

const exitCode = failures.length ? 1 : 0;
emit('');
emit(exitCode
  ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
  : 'RESULT: PASS — the live board classifies ready/failed/blocked, logs only events, and keeps the tick in one cell.');
emit(`WALL_MS ${Date.now() - start}`);
emit(`EXIT ${exitCode}`);
fs.writeFileSync(outPath, `${lines.join('\n')}\n`);
process.stdout.write(`${lines.join('\n')}\n`);
process.exit(exitCode);
