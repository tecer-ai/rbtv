'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../server/heart/heart-store');
const {
  owedFromLedgers, reconcileGoal, summonedSeats,
} = require('./reconcile');
// The brake these arms used to measure (`strike`/`stuckStands`, bound by `STRIKE_LIMIT`) is
// DELETED [spec-recovery §5, C-4 kill map]. What they measure now is the attempt counter: N off a
// config file, a reason-class key, and a reset that only a named re-arm event can cause.
const counters = require('../supervisor/attempt-counters');
const { classifyEnding } = require('./owed-from-endings');
const { bind } = require('../state-store');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reconcile-selftest-'));

// -- THE COUNTER FIXTURE ------------------------------------------------------------------------
// A workspace with the packaged recovery config seeded into it, and a counter ledger of its own.
// N is READ BACK off that file, never typed as a literal in an arm below.
const { seedRecoveryConfig, loadRecoveryConfig } = require('../supervisor/recovery-config');

function counterFixture(name) {
  const root = fs.mkdtempSync(path.join(tmpRoot, `${name}-ws-`));
  seedRecoveryConfig(root);
  return {
    workspaceRoot: root,
    recovery: loadRecoveryConfig({ workspace: root }),
    countersFile: path.join(root, 'counters.json'),
  };
}
const lines = [];
function say(s) { lines.push(s); console.log(s); }

function writeSeat(goalFolder, seat, cast) {
  const dir = path.join(goalFolder, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  const fm = cast
    ? `---\nseat: ${seat}\nharness: bash\nmodel: probe-reconcile\n---\n\nbody\n`
    : `---\nseat: ${seat}\n---\n\nbody\n`;
  fs.writeFileSync(path.join(dir, 'seat.md'), fm);
}

function writeTaskforce(goalFolder, seats) {
  const rows = seats.map((s) => `tf,${s},,bash,probe-reconcile,high,35,`);
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${rows.join('\n')}\n`);
}

function endingFromLegacy(disp) {
  if (disp === 'done') return { ending: 'done', armed: null };
  if (disp === 'incomplete') return { ending: 'incomplete', armed: 1 };
  if (disp === 'unverified') return { ending: 'failed', armed: null, reason_class: 'outputs-missing' };
  return { ending: 'failed', armed: null, reason_class: 'crash' };
}

function endingsMap(pairs) {
  const m = new Map();
  for (const [seat, disp, armed] of pairs) {
    const spec = endingFromLegacy(disp);
    if (armed !== undefined) spec.armed = armed;
    m.set(seat, spec);
  }
  return m;
}

function stampEndings(store, goal, pairs) {
  const api = bind(store.db);
  for (const [seat, disp, armed] of pairs) {
    const spec = endingFromLegacy(disp);
    if (armed !== undefined) spec.armed = armed;
    const fields = {
      goal, seat, ending: spec.ending, evidence_pointer: `selftest:${seat}`, replace: true,
    };
    if (spec.ending === 'done') {
      api.stampSeatDeclare({ ...fields, declared_outputs: [] });
    } else if (spec.ending === 'incomplete' && Number(spec.armed) === 0) {
      api.stampSystem({ ...fields, armed: 0, diagnostic: 'blocked-on-human' });
    } else if (spec.ending === 'incomplete') {
      api.stampSeatDeclare({ ...fields, armed: 1, diagnostic: 'context full' });
    } else {
      api.stampSystem({ ...fields, reason_class: spec.reason_class });
    }
  }
}

function writeSessions(goalFolder, rows) {
  // coord.py SESSIONS_COLS, verbatim. There is no `incomplete-reason` column and never was —
  // reconcile's old class-(c) parse read one, which is why it never fired (D32/D33a).
  const cols = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
    'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
    'disposition-writer', 'execution', 'checkin', 'model', 'hold-anchor'];
  const linesOut = [cols.join(',')];
  for (const r of rows) {
    linesOut.push(cols.map((c) => (r[c] == null ? '' : String(r[c]).replace(/,/g, ' '))).join(','));
  }
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'), `${linesOut.join('\n')}\n`);
}

function writeMessages(goalFolder, blocks) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const parts = ['# messages\n'];
  for (const b of blocks) {
    parts.push(`## ${b.num} | from: ${b.sender} | to: ${b.to} | type: ${b.type} | ${b.ts || '2026-08-19 12:00'}`);
    parts.push('');
    parts.push(b.body || 'body');
    parts.push('');
  }
  fs.writeFileSync(path.join(dir, 'messages.md'), parts.join('\n'));
}

function openStore() {
  const dbPath = path.join(fs.mkdtempSync(path.join(tmpRoot, 'db-')), 'heart.db');
  return openHeartStore({ dbPath });
}

function fixtureA() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'a-'));
  writeSeat(goalFolder, 'leader', true);
  writeSeat(goalFolder, 'plan-planner', true);
  writeTaskforce(goalFolder, ['leader', 'plan-planner']);
  writeSessions(goalFolder, [
    { 'session-id': 'pp1', seat: 'plan-planner', started: '2026-08-13 13:25',
      ended: '2026-08-13 13:51', disposition: 'incomplete', 'disposition-writer': 'seat' },
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-13 12:00',
      ended: '2026-08-13 12:10', disposition: 'done', 'disposition-writer': 'seat' },
  ]);
  return goalFolder;
}

function fixtureB() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'b-'));
  writeSeat(goalFolder, 'leader', true);
  writeTaskforce(goalFolder, ['leader']);
  writeSessions(goalFolder, [
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'done', checkin: '2026-08-19 10:04' },
  ]);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00', body: 'please sit' },
  ]);
  return goalFolder;
}

// D33(a) · the three endings side by side in ONE goal. `incomplete` is the SEAT'S word for
// unfinished — the watcher relaunches that seat by name. `unverified` (checkout's D5 refusal,
// D32) and `exited` (the harness died) are nobody's to close but the leader's.
function fixtureSplit() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'split-'));
  for (const s of ['leader', 'writer', 'checker', 'runner']) writeSeat(goalFolder, s, true);
  writeTaskforce(goalFolder, ['leader', 'writer', 'checker', 'runner']);
  writeSessions(goalFolder, [
    { 'session-id': 'w1', seat: 'writer', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'incomplete', 'disposition-writer': 'seat' },
    { 'session-id': 'c1', seat: 'checker', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:06', disposition: 'unverified', 'disposition-writer': 'seat' },
    { 'session-id': 'r1', seat: 'runner', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:07', disposition: 'exited', 'disposition-writer': 'kit' },
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 09:00',
      ended: '2026-08-19 09:30', disposition: 'done', 'disposition-writer': 'seat',
      checkin: '2026-08-19 09:30' },
  ]);
  writeMessages(goalFolder, []);
  return goalFolder;
}

// D34 · one owed row the LEADER owns, so the strike count for `nonterm` is unambiguous.
// `rewrite` replays a leader ruling by rewriting the ledger between passes.
function fixtureBound() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'bound-'));
  for (const s of ['leader', 'worker-a', 'worker-b']) writeSeat(goalFolder, s, true);
  writeTaskforce(goalFolder, ['leader', 'worker-a', 'worker-b']);
  writeMessages(goalFolder, []);
  return goalFolder;
}

function boundRows(goalFolder, rows, store, goal) {
  writeSessions(goalFolder, [
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 09:00',
      ended: '2026-08-19 09:30', disposition: 'done', 'disposition-writer': 'seat',
      checkin: '2026-08-19 09:30' },
    ...rows.map(([seat, disposition, ended], i) => ({
      'session-id': `s${i}`, seat, started: '2026-08-19 10:00', ended: ended || '2026-08-19 10:05',
      disposition, 'disposition-writer': 'seat',
    })),
  ]);
  if (store && goal) {
    stampEndings(store, goal, [['leader', 'done'], ...rows.map(([seat, disposition]) => [seat, disposition])]);
  }
}

// D35 · one chair, three messages, and the check-in stamp moved around them.
function fixtureMail({ checkin, started = '2026-08-19 10:00', row = true }) {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'mail-'));
  writeSeat(goalFolder, 'leader', true);
  writeTaskforce(goalFolder, ['leader']);
  writeSessions(goalFolder, row ? [
    { 'session-id': 'ld1', seat: 'leader', started, ended: '2026-08-19 10:30',
      disposition: 'done', 'disposition-writer': 'seat', checkin },
  ] : []);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00' },
    { num: 2, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 12:00' },
    { num: 3, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 13:00' },
  ]);
  return goalFolder;
}

function fixtureUncast() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'u-'));
  writeSeat(goalFolder, 'leader', false);
  writeSeat(goalFolder, 'worker', true);
  writeTaskforce(goalFolder, ['leader', 'worker']);
  writeSessions(goalFolder, [
    { 'session-id': 'w1', seat: 'worker', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'unverified', 'disposition-writer': 'seat' },
  ]);
  writeMessages(goalFolder, []);
  return goalFolder;
}

// D24 · the summoned chair and a CONTROL staff chair in the IDENTICAL shape: both checked out
// non-terminal with no later sitting, both carrying unread mail. Only the summoned one is
// excluded — a leader relaunch on owed work is the watcher's whole purpose.
function fixtureSummoned() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 's-'));
  writeSeat(goalFolder, 'leader', true);
  writeSeat(goalFolder, 'goal-master', true);
  writeTaskforce(goalFolder, ['leader', 'goal-master']);
  writeSessions(goalFolder, [
    { 'session-id': 'gm1', seat: 'goal-master', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'incomplete', 'disposition-writer': 'seat',
      checkin: '2026-08-19 10:04' },
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'incomplete', 'disposition-writer': 'seat',
      checkin: '2026-08-19 10:04' },
  ]);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00' },
    { num: 2, sender: 'worker', to: 'goal-master', type: 'note', ts: '2026-08-19 11:01' },
  ]);
  return goalFolder;
}

const readyEmpty = { ready: new Map(), granted: new Map(), rows: [], reason: null };

say('── endings ──');
assert.strictEqual(classifyEnding({ ending: 'done' }), null);
assert.strictEqual(classifyEnding({ ending: 'incomplete', armed: 1 }).reason, 'incomplete');
assert.strictEqual(classifyEnding({ ending: 'incomplete', armed: 0 }), null);
assert.strictEqual(classifyEnding({ ending: 'failed' }).reason, 'nonterm');
say('ok  classifyEnding reads ending+armed (done/disarmed drop out; incomplete armed relaunches; failed is nonterm)');

say('── class (a) ──');
{
  const d = owedFromLedgers(fixtureA(), {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(),
    endings: endingsMap([['plan-planner', 'incomplete'], ['leader', 'done']]),
  });
  assert.strictEqual(d.classA.length, 1, JSON.stringify(d.classA));
  assert.strictEqual(d.classA[0].seat, 'plan-planner');
  assert.strictEqual(d.classA[0].ending, 'incomplete');
  assert.strictEqual(d.owed, true);
  say('ok  incomplete plan-planner with no later sitting is class (a)');
}

say('── F-1: a sitting that starts and ends inside ONE minute is still class (a) ──');
{
  // coord writes `started` at second precision and `ended` at minute precision. Verbatim shape
  // of the three meet rows that went invisible on 2026-08-20.
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'f1-'));
  writeSeat(goalFolder, 'plan-3-plan-check-edges', true);
  writeTaskforce(goalFolder, ['plan-3-plan-check-edges']);
  writeSessions(goalFolder, [
    { 'session-id': 'e1', seat: 'plan-3-plan-check-edges', started: '2026-08-20T05:38:40Z',
      ended: '2026-08-20 05:38', disposition: 'exited', 'disposition-writer': 'kit' },
  ]);
  writeMessages(goalFolder, []);
  const f1Endings = endingsMap([['plan-3-plan-check-edges', 'exited']]);
  const d = owedFromLedgers(goalFolder, {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: f1Endings,
  });
  assert.deepStrictEqual(d.classA.map((x) => x.seat), ['plan-3-plan-check-edges'],
    `same-minute sitting lost its class (a): ${JSON.stringify(d.classA)}`);
  assert.strictEqual(d.owed, true);
  say('ok  started 05:38:40Z / ended 05:38 is owed, not superseded by itself');

  const src = fs.readFileSync(path.join(__dirname, 'owed-from-endings.js'), 'utf8');
  const ANCHOR = '    if (!ended) continue;';
  assert.ok(src.includes(ANCHOR), 'F-1 anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'owed-from-endings.js'), null);
  mut.filename = path.join(__dirname, 'owed-from-endings.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, `${ANCHOR}\n    if (sessions.some((r) => (r.seat || '').trim() === seat && tsAfter(r.started, ended))) continue;`), mut.filename);
  const red = mut.exports.classifyOwed(goalFolder, {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: f1Endings,
    loadSessions: require('./reconcile').loadSessions,
    loadMessages: require('./reconcile').loadMessages,
    lastBySeat: (rows) => {
      const last = new Map();
      for (const r of rows) {
        const seat = (r.seat || '').trim();
        if (!seat) continue;
        const prev = last.get(seat);
        if (!prev || String(r.started) > String(prev.started)) last.set(seat, r);
      }
      return last;
    },
    liveSeatsFromLedgers: () => new Set(),
    checkinOf: () => '',
    tsAfter: (a, b) => String(a).replace('T', ' ').replace(/Z$/, '') > String(b).replace('T', ' ').replace(/Z$/, ''),
    STAFF_CHAIRS: ['leader', 'goal-master'],
    SYSTEM_MAIL_SENDER: 'ignite-daemon',
  });
  assert.deepStrictEqual(red.classA, [], `mutant kept the row: ${JSON.stringify(red.classA)}`);
  assert.strictEqual(red.owed, false);
  say('ok  RED: with laterSitting restored the same row vanishes (classA []), so the arm discriminates');
}

say('── class (b) ──');
{
  const d = owedFromLedgers(fixtureB(), { readyAnswer: readyEmpty, live: new Set(), queued: new Set() });
  assert.strictEqual(d.classB.length, 1, JSON.stringify(d.classB));
  assert.strictEqual(d.classB[0].seat, 'leader');
  assert.strictEqual(d.classB[0].unreadCount, 1);
  say('ok  unread staff mail with no live sitting is class (b)');
}

say('── D33(a): class (a) splits by WORD ──');
{
  const d = owedFromLedgers(fixtureSplit(), {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(),
    endings: endingsMap([
      ['writer', 'incomplete'], ['checker', 'unverified'], ['runner', 'exited'], ['leader', 'done'],
    ]),
  });
  const byWord = Object.fromEntries(d.classA.map((x) => [x.seat, `${x.ending}/${x.reason}`]));
  assert.deepStrictEqual(byWord, {
    writer: 'incomplete/incomplete',
    checker: 'failed/nonterm',
    runner: 'failed/nonterm',
  }, JSON.stringify(byWord));
  assert.strictEqual(d.classC, undefined, 'classC survived the D33(a) delete');
  say(`ok  ${JSON.stringify(byWord)} — and classC is gone`);
}

say('── D33(a): the incomplete seat is enqueued BY NAME; the leader once, with a NAMED payload ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureSplit();
    stampEndings(store, 'fx-split', [
      ['writer', 'incomplete'], ['checker', 'unverified'], ['runner', 'exited'], ['leader', 'done'],
    ]);
    const r = reconcileGoal({
      goal: 'fx-split', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'BOOT-PROMPT-BODY',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    const enq = r.actions.filter((a) => a.kind === 'enqueue');
    assert.deepStrictEqual(enq.map((a) => `${a.seat}:${a.reason}`).sort(),
      ['leader:nonterm', 'writer:incomplete'], JSON.stringify(r.actions));
    const q = Object.fromEntries(store.listQueue().map((row) => [row.job_id, JSON.parse(row.args)]));
    assert.deepStrictEqual(Object.keys(q).sort(), ['seat-fx-split-leader', 'seat-fx-split-writer'],
      JSON.stringify(Object.keys(q)));
    // BY NAME: the sitting is enqueued into the stranded seat's OWN folder, not the leader's.
    assert.ok(q['seat-fx-split-writer'].workdir.endsWith(`${path.sep}seats${path.sep}writer`),
      q['seat-fx-split-writer'].workdir);
    const payload = q['seat-fx-split-leader'].prompt;
    assert.ok(payload.startsWith('BOOT-PROMPT-BODY'), 'the boot prompt is no longer FIRST');
    // D39 · clearing and relaunching are TWO acts. The payload MUST name the second one, with
    // the real coord.py flag spelling (`launch --only <seat> --declare-only <anchor>`), and must
    // no longer claim a CLEAR re-arms an ordinary relaunch.
    assert.ok(!/ordinary relaunch/.test(payload), `payload still promises an ordinary relaunch: ${payload}`);
    // D42 · the payload must ALSO name the CRASHED row's own one-act door, and it keeps D39's
    // CLEAR-is-two-acts text for cleared rows. A wake that offers only the cleared row's path is
    // the F-3 defect: a tool advertising a return path that returns nothing. `rule-disposition`
    // (the ruling/HOLD verb) was deleted [T2-R12, T1-R9] — the payload must say so, not name it
    // as a live instrument.
    for (const needle of ['checker', 'failed', 'runner',
      'No runtime ruling instrument exists', '[T2-R12, T1-R9]',
      'launch --only <seat> --declare-only', 'CLEARING IS NOT A RELAUNCH',
      'launch --only <seat> --rerun', 'A CRASHED SEAT IS RE-RUN IN ONE ACT']) {
      assert.ok(payload.includes(needle), `leader payload never names ${needle}: ${payload}`);
    }
    // The payload MAY name `rule-disposition` to explain it is gone, but must never present it
    // as a runnable command (an indented command line, as every live verb above is shown).
    assert.ok(!/^ {4}rule-disposition\b/m.test(payload),
      `leader payload still presents rule-disposition as a runnable command: ${payload}`);
    assert.ok(!/^- `writer`/m.test(payload), `the by-name seat leaked into the leader payload: ${payload}`);
    say(`ok  writer workdir=…${q['seat-fx-split-writer'].workdir.slice(-20)}`);
    say(`ok  leader payload (${payload.length} chars) names checker/unverified, runner/exited, no rule-disposition`);
    say(payload.slice(payload.indexOf('## The watcher woke you')));
  } finally {
    store.close();
    closeHeartStore();
  }
}

// D42 · A RULED HOLD IS SKIPPED BY THE WATCHER, AND BY NOTHING ELSE.
// `meet/issues.md#G-leader-0820-1748`: a held row was byte-identical to an unattended owed row,
// so the leader was re-woken every 300s forever. The BEFORE/AFTER pair on ONE fixture is what
// makes this a measurement — an arm that only ran the held case would pass against a scan that
// dropped `unverified` rows for any reason at all.
say('── D42: a disarmed incomplete leaves class A ──');
{
  const goalFolder = fixtureSplit();
  const before = owedFromLedgers(goalFolder, {
    endings: endingsMap([
      ['writer', 'incomplete'], ['checker', 'unverified'], ['runner', 'exited'], ['leader', 'done'],
    ]),
  });
  assert.ok(before.classA.some((r) => r.seat === 'checker' && r.ending === 'failed'),
    `control: the unheld row is owed to start with: ${JSON.stringify(before.classA)}`);
  assert.ok(before.classA.some((r) => r.seat === 'runner' && r.ending === 'failed'),
    'control: the crashed row is owed to start with');

  const after = owedFromLedgers(goalFolder, {
    endings: endingsMap([
      ['writer', 'incomplete'], ['checker', 'incomplete', 0], ['runner', 'exited'], ['leader', 'done'],
    ]),
  });
  assert.ok(!after.classA.some((r) => r.seat === 'checker'),
    `the disarmed row is still owed: ${JSON.stringify(after.classA)}`);
  assert.ok(after.classA.some((r) => r.seat === 'runner' && r.ending === 'failed'),
    `the disarm leaked past its own row: ${JSON.stringify(after.classA)}`);
  say(`ok  checker disarmed -> out of class A (${after.classA.length} owed, was ${before.classA.length})`);
}

say('── dead seats excluded ──');
{
  const goalFolder = fixtureA();
  const d = owedFromLedgers(goalFolder, {
    readyAnswer: {
      ready: new Map(), granted: new Map(), reason: null,
      rows: [{ seat: 'plan-planner', dead: true }],
      endings: endingsMap([['plan-planner', 'incomplete'], ['leader', 'done']]),
    },
    live: new Set(), queued: new Set(),
  });
  assert.strictEqual(d.classA.length, 0, JSON.stringify(d.classA));
  assert.deepStrictEqual(d.deadSeats, ['plan-planner']);
  say('ok  dead:true seat is never owed');
}

say('── launch class (a): the incomplete seat, not deduped ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureA();
    stampEndings(store, 'fx-a', [['plan-planner', 'incomplete'], ['leader', 'done']]);
    const sent = [];
    const r = reconcileGoal({
      goal: 'fx-a', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(),
      promptFn: () => 'fixture prompt',
      sendFn: (x) => { sent.push(x); return { ok: true }; },
      recoverFn: () => ({ ok: true }),
    });
    const enq = r.actions.find((a) => a.kind === 'enqueue');
    assert.ok(enq, JSON.stringify(r.actions));
    assert.strictEqual(enq.seat, 'plan-planner');
    assert.ok(enq.enq && !enq.enq.deduped, JSON.stringify(enq.enq));
    const q = store.listQueue();
    assert.strictEqual(q.length, 1);
    assert.strictEqual(q[0].job_id, 'seat-fx-a-plan-planner');
    say(`ok  enqueued ${q[0].job_id} queue_id=${q[0].queue_id} deduped=${Boolean(enq.enq.deduped)}`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── class (b) enqueues staff chair ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureB();
    const r = reconcileGoal({
      goal: 'fx-b', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(),
      promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }),
      recoverFn: () => ({ ok: true }),
    });
    const enq = r.actions.find((a) => a.kind === 'enqueue');
    assert.ok(enq, JSON.stringify(r.actions));
    assert.strictEqual(enq.seat, 'leader');
    assert.ok(enq.enq && !enq.enq.deduped);
    say(`ok  class (b) enqueued ${enq.jobId} queue_id=${enq.enq.queue_id}`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── the attempt counter: N same-reason retries on a REFUSED launch, then the lane disarms ──');
{
  const store = openStore();
  const fx = counterFixture('n-refused');
  const N = fx.recovery.attempt_counter_n;
  try {
    const goalFolder = fixtureUncast();
    stampEndings(store, 'fx-u', [['worker', 'unverified']]);
    const passes = [];
    for (let i = 0; i < N + 2; i += 1) {
      passes.push(reconcileGoal({
        goal: 'fx-u', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(),
        promptFn: () => 'fixture prompt',
        recoverFn: () => ({ ok: true }),
        ...fx,
      }));
    }
    const refused = passes.map((p) => p.actions.find((a) => a.kind === 'launch-refused'));
    assert.ok(refused[0] && refused[0].error === 'E_UNCAST_SEAT', JSON.stringify(refused[0]));
    // Every pass up to N counts the SAME reason class - the refusal never changed, so neither did
    // the key. The old arm needed a byte-identical signature for this; the counter does not.
    for (let i = 0; i < N; i += 1) {
      assert.strictEqual(refused[i].attempts, i + 1, `pass ${i + 1} of ${N}: ${JSON.stringify(refused[i])}`);
    }
    assert.strictEqual(refused[N - 1].exhausted, true, 'the Nth retry exhausts the counter');

    // From N on the mechanical relaunch STOPS. Not because a message was sent - because the lane
    // is disarmed and waits for a named re-arm event.
    const after = passes.slice(N).map((p) => p.actions.find(
      (a) => a.seat === 'leader' && a.reason === 'nonterm'));
    assert.deepStrictEqual(after.map((a) => a.kind), ['skip-disarmed', 'skip-disarmed'],
      `a launch was still issued after N - ${JSON.stringify(after)}`);

    const row = counters.peekCounter({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'fx-u', seat: 'leader', reasonClass: 'nonterm',
    }, { countersFile: fx.countersFile });
    assert.strictEqual(Number(row.attempts), N, 'a disarmed lane counts nothing further');
    say(`ok  the lane disarms after N=${N} same-reason retries; passes ${N + 1}-${N + 2} issued NO launch`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── the count is durable across a store close and reopen ──');
{
  const dbDir = fs.mkdtempSync(path.join(tmpRoot, 'dur-'));
  const dbPath = path.join(dbDir, 'heart.db');
  const goalFolder = fixtureUncast();
  const fx = counterFixture('durable');
  const key = {
    driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'fx-d', seat: 'leader', reasonClass: 'nonterm',
  };
  let store = openHeartStore({ dbPath });
  const pass = () => reconcileGoal({
    goal: 'fx-d', goalFolder, engine: { heartStore: store },
    say: () => {}, force: true, readyAnswer: readyEmpty,
    live: new Set(), promptFn: () => 'x', recoverFn: () => ({ ok: true }),
    ...fx,
  });
  try {
    stampEndings(store, 'fx-d', [['worker', 'unverified']]);
    pass();
    pass();
    const before = counters.peekCounter(key, { countersFile: fx.countersFile });
    assert.strictEqual(Number(before.attempts), 2);
    say(`  before close: attempts=${before.attempts}`);
    store.close();
    closeHeartStore();
    store = openHeartStore({ dbPath });
    pass();
    const after = counters.peekCounter(key, { countersFile: fx.countersFile });
    assert.strictEqual(Number(after.attempts), 3, `expected 3 got ${after.attempts}`);
    say(`  after reopen+1: attempts=${after.attempts}`);
    say('ok  the counter survives a daemon restart - it is on disk, not in the process');
  } finally {
    store.close();
    closeHeartStore();
  }
}

// ── THE COUNTER MEASURES A SAME-REASON RETRY, AND ONLY A NAMED EVENT RESETS IT ────────────────
// This is the defect the redesign was built for. Every one of these passes LAUNCHES fine, so the
// old `clearAttempt`-on-`launched.ok` reset the count every time and the loop never ended; then
// D34's fix made the count survive a launch but still reset when the owed SIGNATURE drifted, and
// the signature drifted on volatile fields. Both resets are gone [spec-recovery §5].
function boundPass(store, goalFolder, fx) {
  reconcileGoal({
    goal: 'fx-bound', goalFolder, engine: { heartStore: store },
    say: () => {}, force: true, readyAnswer: readyEmpty,
    live: new Set(), promptFn: () => 'BOOT',
    recoverFn: () => ({ ok: true }),
    ...fx,
  });
  return counters.peekCounter({
    driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'fx-bound', seat: 'leader', reasonClass: 'nonterm',
  }, { countersFile: fx.countersFile });
}

say('── a successful launch does not clear the count, and neither does a CHANGED owed set ──');
{
  const store = openStore();
  const fx = counterFixture('same-reason');
  try {
    const goalFolder = fixtureBound();

    boundRows(goalFolder, [['worker-a', 'unverified']], store, 'fx-bound');
    const p1 = boundPass(store, goalFolder, fx);
    assert.strictEqual(Number(p1.attempts), 1, JSON.stringify(p1));
    say(`  pass 1 (owed a=unverified): attempts=${p1.attempts}`);

    const p2 = boundPass(store, goalFolder, fx);
    assert.strictEqual(Number(p2.attempts), 2, JSON.stringify(p2));
    say(`  pass 2 (owed UNCHANGED, launch succeeded): attempts=${p2.attempts}`);

    // THE INVERTED EXPECTATION, and the inversion IS the ruling. Under the deleted brake a changed
    // owed set was PROGRESS and reset the count to 1. It is not progress: the leader still owes the
    // same class of judgment, and the drifting content is exactly what kept the bound from firing.
    boundRows(goalFolder, [['worker-a', 'unverified'], ['worker-b', 'exited']], store, 'fx-bound');
    const p3 = boundPass(store, goalFolder, fx);
    assert.strictEqual(Number(p3.attempts), 3,
      `a changed owed set reset the counter - the byte-equality reset is back: ${JSON.stringify(p3)}`);
    say(`  pass 3 (owed CHANGED, same reason class): attempts=${p3.attempts} - NOT reset`);

    // The ONLY reset: a named re-arm event.
    const reset = counters.rearm({
      event: counters.RE_ARM.OWNER_LEADER_ACT, goal: 'fx-bound', seat: 'leader',
    }, { countersFile: fx.countersFile });
    assert.strictEqual(reset.reset.length, 1, JSON.stringify(reset));
    const p4 = boundPass(store, goalFolder, fx);
    assert.strictEqual(Number(p4.attempts), 1, `a named re-arm did not re-arm: ${JSON.stringify(p4)}`);
    say(`  pass 4 (after an owner/leader act): attempts=${p4.attempts} - re-armed`);
    say('ok  only a named re-arm event clears the count; no launch outcome and no content drift does');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── RED arm: restore the evidence-driven reset (the deleted byte-equality brake) ──');
{
  // The mutant puts an owed-content reset back into a COPY of the live source: the counter is
  // cleared whenever the pass's owed signature differs from the last one. If the arm above does
  // not discriminate, the mutant passes it too.
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = `    if (action.kind !== 'skip-disarmed') {`;
  assert.ok(src.includes(ANCHOR), 'the counting branch anchor is missing - the red arm has no anchor');
  const mutated = src.replace(ANCHOR, `    if (action.kind !== 'skip-disarmed') {
      // MUTANT: the deleted signature reset, restored.
      if (globalThis.__redLastSig !== t.signature) {
        counters.rearm({ event: 'owner-leader-act', goal, seat: t.seat }, { countersFile });
        globalThis.__redLastSig = t.signature;
      }`);
  assert.notStrictEqual(mutated, src);
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(mutated, mut.filename);
  const store = openStore();
  const fx = counterFixture('red-reset');
  let seen = null;
  try {
    const goalFolder = fixtureBound();
    const pass = () => mut.exports.reconcileGoal({
      goal: 'fx-bound', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'BOOT', recoverFn: () => ({ ok: true }),
      ...fx,
    });
    boundRows(goalFolder, [['worker-a', 'unverified']], store, 'fx-bound');
    pass();
    pass();
    boundRows(goalFolder, [['worker-a', 'unverified'], ['worker-b', 'exited']], store, 'fx-bound');
    pass();
    seen = counters.peekCounter({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'fx-bound', seat: 'leader', reasonClass: 'nonterm',
    }, { countersFile: fx.countersFile });
  } finally {
    delete globalThis.__redLastSig;
    store.close();
    closeHeartStore();
  }
  assert.strictEqual(Number(seen.attempts), 1,
    `the mutant did NOT reset on a changed signature, so the arm above proves nothing: ${JSON.stringify(seen)}`);
  say(`ok  RED: with the evidence-driven reset back, three passes leave attempts=${seen.attempts} - the arm discriminates`);
}

// ── THE CLASS-A `incomplete` RELAUNCH DRIVER [spec-recovery §5 row 3] ─────────────────────────
// `ended` advances on every re-checkout. D40 removed it from the owed signature for exactly the
// reason the whole brake was deleted: a volatile field in the key made an IDENTICAL give-up read
// as new work. The counter cannot regress that way at all - its key is the reason CLASS, and the
// key builder REFUSES a class carrying a timestamp, a uuid, a digest or a long id.
function incPass(store, goalFolder, fx) {
  reconcileGoal({
    goal: 'fx-inc', goalFolder, engine: { heartStore: store },
    say: () => {}, force: true, readyAnswer: readyEmpty,
    live: new Set(), promptFn: () => 'BOOT',
    recoverFn: () => ({ ok: true }),
    ...fx,
  });
  return counters.peekCounter({
    driver: counters.DRIVERS.RECONCILE_CLASS_A, goal: 'fx-inc', seat: 'worker-a', reasonClass: 'incomplete',
  }, { countersFile: fx.countersFile });
}

say('── class A: same seat, same word, DIFFERENT `ended` → the count still reaches N and disarms ──');
{
  const store = openStore();
  const fx = counterFixture('class-a');
  const N = fx.recovery.attempt_counter_n;
  try {
    const goalFolder = fixtureBound();
    const endeds = ['2026-08-19 10:05', '2026-08-19 14:47', '2026-08-19 18:12', '2026-08-19 21:30'];
    let row = null;
    for (let i = 0; i < N; i += 1) {
      // The seat was relaunched, worked, and gave up again: SAME word, a LATER `ended`.
      boundRows(goalFolder, [['worker-a', 'incomplete', endeds[i % endeds.length]]], store, 'fx-inc');
      row = incPass(store, goalFolder, fx);
      assert.strictEqual(Number(row.attempts), i + 1,
        `a moving \`ended\` reset the class-A counter: ${JSON.stringify(row)}`);
    }
    assert.strictEqual(Number(row.attempts), N);
    assert.strictEqual(row.reason_class, 'incomplete', 'the key is the reason CLASS, not the row content');
    say(`  the class-A relaunch counted to N=${N} across ${N} different \`ended\` stamps`);

    // The driver is its OWN spec §5 row: a class-A relaunch does not share a counter with the
    // cadence re-spawn, so exhausting one never disarms the other.
    assert.strictEqual(counters.peekCounter({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'fx-inc', seat: 'worker-a', reasonClass: 'incomplete',
    }, { countersFile: fx.countersFile }), null);
    say('ok  class A counts per (driver, lane, reason class) and survives a changed `ended`');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── RED arm: put the volatile field back INTO the counter key ──');
{
  // The pre-D40 defect, aimed at the counter instead of the signature: the reason class carries
  // the row's `ended`. The key builder must REFUSE it - which is what makes the arm above unable
  // to regress rather than merely un-regressed today.
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = 'driver, goal, seat, reasonClass: reason, n: config.attempt_counter_n, at,';
  assert.ok(src.includes(ANCHOR), 'the counter key anchor is missing - the red arm has no anchor');
  const mutated = src.replace(
    ANCHOR,
    'driver, goal, seat, reasonClass: `${reason}:${new Date().toISOString()}`, n: config.attempt_counter_n, at,',
  );
  assert.notStrictEqual(mutated, src);
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(mutated, mut.filename);
  const store = openStore();
  const fx = counterFixture('red-volatile');
  let threw = null;
  try {
    const goalFolder = fixtureBound();
    boundRows(goalFolder, [['worker-a', 'incomplete', '2026-08-19 10:05']], store, 'fx-inc');
    // `maybeReconcile` swallows a throw into the pass result; `reconcileGoal` does not, which is
    // what lets this arm see the refusal itself.
    try {
      mut.exports.reconcileGoal({
        goal: 'fx-inc', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT', recoverFn: () => ({ ok: true }),
        ...fx,
      });
    } catch (err) {
      threw = err;
    }
  } finally {
    store.close();
    closeHeartStore();
  }
  assert.ok(threw, 'a volatile counter key was ACCEPTED - the tripwire does not fire');
  assert.strictEqual(threw.code, 'E_ATTEMPT_COUNTER', JSON.stringify(threw.message));
  assert.match(threw.message, /volatile fingerprint/);
  say(`ok  RED: a volatile counter key is refused at the choke point - ${threw.message.slice(0, 60)}…`);
}

// ── D35 · unread mail is what was RECORDED AFTER the chair's last check-in ────────────────────
say('── D35: unread is a timestamp comparison, not a message number ──');
{
  const cases = [
    ['checkin between #2 and #3', { checkin: '2026-08-19 12:30' }, 1],
    ['checkin after #3', { checkin: '2026-08-19 13:30' }, 0],
    ['no checkin, started after #1', { checkin: '', started: '2026-08-19 11:30' }, 2],
    ['no row at all', { checkin: '', row: false }, 3],
  ];
  for (const [label, opts, want] of cases) {
    const d = owedFromLedgers(fixtureMail(opts), {
      readyAnswer: readyEmpty, live: new Set(), queued: new Set(),
    });
    const got = d.classB.length ? d.classB[0].unreadCount : 0;
    assert.strictEqual(got, want, `${label}: want ${want} got ${got} — ${JSON.stringify(d.classB)}`);
    say(`  ${label}: classB=${d.classB.length} unread=${got}`);
  }
  say('ok  D35: 1 / 0 / 2 / 3 — and an empty class (b) when the chair has read its mail');
}

say('── RED arm: restore the numeric mail cursor ──');
{
  const rec = require('./reconcile');
  const src = fs.readFileSync(path.join(__dirname, 'owed-from-endings.js'), 'utf8');
  const ANCHOR = '&& (!since || tsAfter(m.ts, since)));';
  assert.ok(src.includes(ANCHOR), 'class (b) unread anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'owed-from-endings.js'), null);
  mut.filename = path.join(__dirname, 'owed-from-endings.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, '&& m.num > (Number(since) || 0));'), mut.filename);
  const d = mut.exports.classifyOwed(fixtureMail({ checkin: '2026-08-19 13:30' }), {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(),
    loadSessions: rec.loadSessions,
    loadMessages: rec.loadMessages,
    lastBySeat: rec.lastBySeat,
    liveSeatsFromLedgers: rec.liveSeatsFromLedgers,
    checkinOf: rec.checkinOf,
    tsAfter: rec.tsAfter,
    STAFF_CHAIRS: rec.STAFF_CHAIRS,
    SYSTEM_MAIL_SENDER: 'ignite-daemon',
  });
  assert.strictEqual(d.classB.length, 1, JSON.stringify(d.classB));
  assert.strictEqual(d.classB[0].unreadCount, 3, JSON.stringify(d.classB));
  say('ok  red: Number(checkin) → NaN → cursor 0 → all 3 messages "unread" forever (238 on meet)');
}

say('── the dead class-(c) column is gone from the module ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  assert.ok(!src.includes('incomplete-reason'), 'reconcile.js still reads incomplete-reason');
  assert.ok(!src.includes('outputsUnverified'), 'reconcile.js still carries outputsUnverified');
  assert.ok(!/\bclassC\b/.test(src), 'reconcile.js still derives classC');
  say('ok  no `incomplete-reason`, no `outputsUnverified`, no `classC` in reconcile.js');
}

say('── paused goal is not reconciled ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureA();
    stampEndings(store, 'fx-pause', [['plan-planner', 'incomplete'], ['leader', 'done']]);
    fs.writeFileSync(path.join(goalFolder, 'execution-lane'), 'paused console\n');
    const logs = [];
    const r = reconcileGoal({
      goal: 'fx-pause', goalFolder, engine: { heartStore: store },
      say: (level, message) => { logs.push({ level, message }); },
      force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    assert.strictEqual(r.skipped, 'paused', JSON.stringify(r));
    assert.strictEqual(store.listQueue().length, 0, 'paused goal must not enqueue');
    assert.ok(logs.some((l) => l.message === 'reconcile: skipped — goal is paused'),
      JSON.stringify(logs));
    say('ok  paused console → skipped:paused, queue empty, skip log fired');

    fs.writeFileSync(path.join(goalFolder, 'execution-lane'), 'daemon\n');
    const unpaused = reconcileGoal({
      goal: 'fx-pause', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    const enq = unpaused.actions && unpaused.actions.find((a) => a.kind === 'enqueue');
    assert.ok(enq, JSON.stringify(unpaused.actions));
    assert.ok(enq.enq && !enq.enq.deduped, JSON.stringify(enq.enq));
    say(`ok  control: same folder unpaused enqueued ${enq.jobId || enq.seat}`);

    // ── ONE PAUSE RECORD: THE STORE ROW WINS OVER THE `execution-lane` MARKER ──────────────────
    //
    // Two records of "is this goal paused" used to exist and the FILE could win: the store answer
    // was consulted only for a TRUE, so a goal-state row reading `running` fell through to a stale
    // `paused` marker on disk and the goal stayed frozen against the record that had been updated.
    // Both halves are asserted, because a gate that only ever answers one way cannot be told from
    // a gate that reads nothing.
    fs.writeFileSync(path.join(goalFolder, 'execution-lane'), 'paused console\n');
    // ⚠ THE ROW IS WRITTEN THROUGH THE GATE'S OWN RESOLUTION, never through `store.db` directly:
    // `bindEnding` walks for a workspace root first and only falls back to the lane store, so a
    // hand-picked handle can be a DIFFERENT database and the arm would measure a store the gate
    // never reads.
    const { bindEnding, goalNameOf } = require('./ending-reads');
    const api = bindEnding(store, goalFolder);
    // ⚠ THE GATE KEYS THE ROW ON THE FOLDER BASENAME, not on the `goal` argument — `laneIsPaused`
    // takes no goal name and derives it with `goalNameOf(goalFolder)`. On a real goal the two are
    // the same string by construction (`<ws>/.rbtv/goals/<goal>`); in this flat fixture they are
    // not, so the row is written under the name the gate will actually look up.
    const pauseGoalId = goalNameOf(goalFolder);
    api.writeGoalWord({ goal: pauseGoalId, stored: 'running', who_stamped: 'system',
      evidence_pointer: 'selftest:one-pause-record' });
    const rowWins = reconcileGoal({
      goal: 'fx-pause', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    assert.notStrictEqual(rowWins.skipped, 'paused',
      `a stale \`paused\` marker beat the goal-state row: ${JSON.stringify(rowWins)}`);
    api.writeGoalWord({ goal: pauseGoalId, stored: 'paused', who_stamped: 'owner',
      evidence_pointer: 'selftest:one-pause-record' });
    fs.writeFileSync(path.join(goalFolder, 'execution-lane'), 'daemon\n');
    const rowPauses = reconcileGoal({
      goal: 'fx-pause', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    assert.strictEqual(rowPauses.skipped, 'paused',
      `the goal-state row said paused and the pass ran anyway: ${JSON.stringify(rowPauses)}`);
    say('ok  one pause record: row `running` beats a stale `paused` marker, row `paused` stops the pass');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── cadence skip ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureA();
    const first = reconcileGoal({
      goal: 'fx-cad', goalFolder, engine: { heartStore: store },
      say: () => {}, force: false, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'x',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
      now: Date.parse('2026-08-19T12:00:00Z'),
    });
    assert.ok(!first.skipped, JSON.stringify(first));
    const second = reconcileGoal({
      goal: 'fx-cad', goalFolder, engine: { heartStore: store },
      say: () => {}, force: false, readyAnswer: readyEmpty,
      now: Date.parse('2026-08-19T12:02:00Z'),
    });
    assert.strictEqual(second.skipped, 'cadence');
    say('ok  second pass inside 300s is cadence-skipped');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── red arm: mutation of the disarm brake ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = '  const row = counters.peekCounter(';
  assert.ok(src.includes(ANCHOR), 'the disarm brake anchor is missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  // MUTANT: the brake never reports a disarmed lane, so the mechanical relaunch runs forever -
  // which is the exact live defect the counter replaced.
  mut._compile(src.replace(ANCHOR, '  if (config) return false;\n  const row = counters.peekCounter('), mut.filename);
  const store = openStore();
  const fx = counterFixture('red-brake');
  const N = fx.recovery.attempt_counter_n;
  const kinds = [];
  try {
    const goalFolder = fixtureUncast();
    stampEndings(store, 'fx-red', [['worker', 'unverified']]);
    for (let i = 0; i < N + 2; i += 1) {
      const r = mut.exports.reconcileGoal({
        goal: 'fx-red', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'x', recoverFn: () => ({ ok: true }),
        ...fx,
      });
      const act = r.actions.find((a) => a.seat === 'leader' && a.reason === 'nonterm');
      kinds.push(act && act.kind);
    }
  } finally {
    store.close();
    closeHeartStore();
  }
  assert.ok(!kinds.includes('skip-disarmed'),
    `the mutant still braked, so the brake arm proves nothing: ${JSON.stringify(kinds)}`);
  say(`ok  red: without the brake, ${N + 2} passes never stop relaunching (${JSON.stringify(kinds)})`);
}

say('── red arm: mutation of the pause gate ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = 'if (goalFolder && laneIsPaused(goalFolder, heartStore))';
  assert.ok(src.includes(ANCHOR), 'pause gate anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, 'if (false && goalFolder && laneIsPaused(goalFolder, heartStore))'), mut.filename);
  const store = openStore();
  try {
    const goalFolder = fixtureA();
    stampEndings(store, 'fx-pause-red', [['plan-planner', 'incomplete'], ['leader', 'done']]);
    fs.writeFileSync(path.join(goalFolder, 'execution-lane'), 'paused console\n');
    const r = mut.exports.reconcileGoal({
      goal: 'fx-pause-red', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'x',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    assert.notStrictEqual(r.skipped, 'paused', JSON.stringify(r));
    const enq = r.actions && r.actions.find((a) => a.kind === 'enqueue');
    assert.ok(enq, `mutated pause gate did not enqueue: ${JSON.stringify(r.actions)}`);
    say('ok  red: deleting the pause gate enqueues a paused goal');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── D24: summoned seats are never owed ──');
{
  const summoned = summonedSeats();
  assert.ok(summoned.has('goal-master'),
    `coord names no summoned seat — read of SUMMONED_SEATS is broken: ${JSON.stringify([...summoned])}`);
  say(`ok  summoned list read off coord.py: ${JSON.stringify([...summoned])}`);

  const goalFolder = fixtureSummoned();

  // RED: the same fixture with NO summoned set — the pre-fix behaviour, and the shape that
  // relaunched meet's goal-master every cadence.
  const summonedEndings = endingsMap([
    ['goal-master', 'incomplete'], ['leader', 'incomplete'],
  ]);
  const red = owedFromLedgers(goalFolder, {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(), summoned: new Set(),
    endings: summonedEndings,
  });
  assert.ok(red.classA.some((x) => x.seat === 'goal-master'), JSON.stringify(red.classA));
  assert.ok(red.classB.some((x) => x.seat === 'goal-master'), JSON.stringify(red.classB));
  say('  red (summoned set empty): goal-master derives in BOTH class (a) and class (b)');

  const green = owedFromLedgers(goalFolder, {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(), summoned,
    endings: summonedEndings,
  });
  assert.ok(!green.classA.some((x) => x.seat === 'goal-master'), JSON.stringify(green.classA));
  assert.ok(!green.classB.some((x) => x.seat === 'goal-master'), JSON.stringify(green.classB));
  assert.ok(green.classA.some((x) => x.seat === 'leader'),
    `CONTROL leader lost its class (a): ${JSON.stringify(green.classA)}`);
  assert.ok(green.classB.some((x) => x.seat === 'leader'),
    `CONTROL leader lost its class (b): ${JSON.stringify(green.classB)}`);
  say('ok  green: goal-master in neither class; CONTROL leader still derives in both');
}

say('── D24: a full pass enqueues the leader and never the summoned chair ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureSummoned();
    stampEndings(store, 'fx-d24', [['goal-master', 'incomplete'], ['leader', 'incomplete']]);
    const r = reconcileGoal({
      goal: 'fx-d24', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    const seats = r.actions.filter((a) => a.kind === 'enqueue').map((a) => a.seat);
    assert.ok(!seats.includes('goal-master'), `enqueued the summoned chair: ${JSON.stringify(r.actions)}`);
    assert.ok(seats.includes('leader'), `CONTROL leader was not enqueued: ${JSON.stringify(r.actions)}`);
    const ids = store.listQueue().map((q) => q.job_id);
    assert.deepStrictEqual(ids, ['seat-fx-d24-leader'], JSON.stringify(ids));
    say(`ok  queue holds ${JSON.stringify(ids)} — no seat-fx-d24-goal-master`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── D24: an unreadable coord degrades to the OLD behaviour, not a silent hole ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = "const COORD_PY = path.join(__dirname, '..', 'team-kit', 'coord.py');";
  assert.ok(src.includes(ANCHOR), 'COORD_PY anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, "const COORD_PY = '/nonexistent/coord.py';"), mut.filename);
  const warns = [];
  const set = mut.exports.summonedSeats((level, message) => warns.push(`${level}:${message}`));
  assert.strictEqual(set.size, 0, JSON.stringify([...set]));
  assert.ok(warns.some((w) => w.startsWith('warn:')), JSON.stringify(warns));
  const goalFolder = fixtureSummoned();
  const d = mut.exports.owedFromLedgers(goalFolder, {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(), summoned: set,
    endings: endingsMap([['goal-master', 'incomplete'], ['leader', 'incomplete']]),
  });
  assert.ok(d.classB.some((x) => x.seat === 'goal-master'), JSON.stringify(d.classB));
  say('ok  unreadable coord → empty set + a warn, and derivation falls back to the old behaviour');
}

// ── THE SINGLE OWED COMPUTER, AND THE SINGLE ENQUEUE [spec-supervisor §5, T4-R7, C-15] ─────────
//
// The defect this guards is not a wrong answer, it is a SECOND ANSWERER: `seeding.js`
// `enqueueEligible` and `reconcile.js`'s ledger classifier both derived "this seat is owed a
// launch" and both called `heartStore.enqueue`, on two cadences, from two pictures, with nothing
// able to say which was right when they disagreed (CODE-GROUND-TRUTH §4).
//
// It is checked STRUCTURALLY because that is where the property lives: no fixture can prove the
// absence of a second path, but the source can. `liveEnqueueCalls` strips comments first — this
// file's own headers talk about `heartStore.enqueue` constantly, and a checker that counted those
// would be green for the wrong reason and would go red the day someone edited a comment.
say('── one owed computer, one enqueue: no second launch path may return ──');
{
  function liveEnqueueCalls(src) {
    const code = String(src)
      .replace(/\/\*[\s\S]*?\*\//g, '')      // block comments
      .split('\n')
      .map((line) => line.replace(/\/\/.*$/, ''))   // line comments
      .join('\n');
    return (code.match(/\.enqueue\s*\(/g) || []).length;
  }

  const seedingSrc = fs.readFileSync(path.join(__dirname, 'seeding.js'), 'utf8');
  const reconcileSrc = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const owedSrc = fs.readFileSync(path.join(__dirname, '..', 'supervisor', 'owed.js'), 'utf8');
  const doorSrc = fs.readFileSync(path.join(__dirname, '..', 'supervisor', 'launch-door.js'), 'utf8');

  // Neither owed computer may enqueue on its own [spec-supervisor §5].
  assert.strictEqual(liveEnqueueCalls(seedingSrc), 0,
    'engine/seeding.js calls .enqueue() again — the retired owed computer grew a launch path back');
  assert.strictEqual(liveEnqueueCalls(reconcileSrc), 0,
    'engine/reconcile.js calls .enqueue() again — deriveOwed must not enqueue on its own');
  assert.strictEqual(liveEnqueueCalls(owedSrc), 0,
    'supervisor/owed.js calls .enqueue() — an owed set is a statement, never an act');
  // …and the door is the ONE that may.
  assert.strictEqual(liveEnqueueCalls(doorSrc), 1,
    'supervisor/launch-door.js must hold exactly ONE enqueue — the only one on the owed path');

  // RED ARM. Re-introduce the second enqueue path in seeding's source and assert the guard above
  // actually fires on it. Without this, the four assertions are a check nobody has ever seen fail.
  const ANCHOR = '  const enqueued = [];';
  assert.ok(seedingSrc.includes(ANCHOR), 'seeding.js red-arm anchor missing');
  const secondPath = seedingSrc.replace(ANCHOR,
    `${ANCHOR}\n  heartStore.enqueue({ jobId: 'a-second-owed-path' });`);
  assert.strictEqual(liveEnqueueCalls(secondPath), 1,
    'the guard does NOT see a re-added enqueue — it would pass whatever the code did');

  // And the retired computer is gone as a SYMBOL, not merely quiet: an exported
  // `enqueueEligible` is a second owed-work computer whatever its body currently does.
  const seeding = require('./seeding');
  const attached = require('./attached-execution');
  assert.strictEqual(seeding.enqueueEligible, undefined,
    'seeding still exports enqueueEligible — the second owed computer is back');
  assert.strictEqual(attached.enqueueEligible, undefined,
    'attached-execution still exports enqueueEligible — the second owed computer is back');
  assert.strictEqual(typeof require('../supervisor/owed').deriveOwed, 'function',
    'the survivor deriveOwed is missing from the supervisor home');

  say('ok  seeding + reconcile + owed hold 0 enqueue calls; launch-door holds exactly 1; red arm fires');
}

// The one computer answers BOTH halves — the ledger half (classes A/B) and the graph-derived
// launchability half [T1-R3] (class R) — from a single call, which is what makes "one owed set"
// checkable at all rather than an assertion about two functions agreeing.
say('── deriveOwed answers both halves of the owed set from one call ──');
{
  const { deriveOwed } = require('../supervisor/owed');
  const rows = [{ seat: 'alpha', after: '' }, { seat: 'beta', after: 'alpha' }];
  const jobIdFor = (seat) => `job-${seat}`;
  const both = deriveOwed(fixtureA(), {
    readyAnswer: readyEmpty,
    live: new Set(),
    queued: new Set(),
    endings: endingsMap([['leader', 'incomplete']]),
    ledger: {
      loadSessions: require('./reconcile').loadSessions,
      loadMessages: require('./reconcile').loadMessages,
      lastBySeat: require('./reconcile').lastBySeat,
      liveSeatsFromLedgers: require('./reconcile').liveSeatsFromLedgers,
      checkinOf: require('./reconcile').checkinOf,
      tsAfter: require('./reconcile').tsAfter,
      STAFF_CHAIRS: require('./reconcile').STAFF_CHAIRS,
      SYSTEM_MAIL_SENDER: 'ignite-daemon',
    },
    graph: {
      rows,
      byJob: new Map(),
      queued: new Set(),
      view: null,
      ready: new Map([['alpha', []]]),
      jobIdFor,
      seatIsFinished: () => false,
      seatHasRun: () => false,
    },
  });
  assert.deepStrictEqual(both.classR.map((x) => x.seat), ['alpha'],
    `graph half wrong: ${JSON.stringify(both.classR)}`);
  assert.ok(Array.isArray(both.classA) && Array.isArray(both.classB),
    'ledger half missing from the same answer');
  assert.strictEqual(both.owed, true, 'an owed graph half must make the whole set owed');

  // A caller that hands in neither half gets an empty owed set — never a second derivation.
  const neither = deriveOwed(fixtureA(), {});
  assert.deepStrictEqual(neither.classR, []);
  assert.strictEqual(neither.owed, false);
  say('ok  one call, both halves; class R is the graph-derived launchability [T1-R3]');
}

fs.rmSync(tmpRoot, { recursive: true, force: true });
say('reconcile.selftest OK');
