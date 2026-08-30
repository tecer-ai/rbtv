'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { readySeats, seedGoal, VERDICT_DOOR } = require('./seeding');
const { readyFromEndings } = require('./ending-reads');
const { openHeartStore } = require('../state-store/heart/heart-store');
const { bind, openEndingStoreFor, closeEndingStores } = require('../state-store');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'seeding-verdict-'));
let failed = 0;
function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.stack ? err.stack : err}\n`);
}
function assertOk(cond, msg) { if (!cond) throw new Error(msg); }

const REFUSED = ['HELD', 'STOPPED', 'UNDECLARED', 'IDLE', 'SKEW', 'RUNNING'];

function kitRows() {
  return [
    { seat: 'held', verdict: 'HELD', reason: 'OWNER-ASK HOLD — open question', seed: [] },
    { seat: 'stopped', verdict: 'STOPPED', reason: 'store row carries row-outcome stop-state', seed: [] },
    { seat: 'undeclared', verdict: 'UNDECLARED', reason: 'session ENDED with an EMPTY disposition', seed: [] },
    { seat: 'idle', verdict: 'IDLE', reason: 'ON-DEMAND summoned seat — NOT OFFERED', seed: [] },
    { seat: 'skew', verdict: 'SKEW', reason: 'the two records of this seat\'s own ending disagree', seed: [] },
    { seat: 'running', verdict: 'RUNNING', reason: 'roster: active since (unstamped)', seed: [] },
    { seat: 'worker', verdict: 'READY', reason: 'after: (root — no predecessors)', seed: ['/seed/a'] },
  ];
}

function caseDoorTable() {
  try {
    const launchable = Object.entries(VERDICT_DOOR).filter(([, v]) => v.launchable).map(([k]) => k);
    assertOk(launchable.length === 1 && launchable[0] === 'READY', `launchable=${launchable}`);
    for (const word of REFUSED.concat(['DONE', 'BLOCKED', 'UNBUILT', 'RENEWING', 'RENEW-BLOCKED'])) {
      assertOk(VERDICT_DOOR[word] && VERDICT_DOOR[word].launchable === false, `${word} must not launch`);
    }
    pass('VERDICT_DOOR: only READY is launchable');
  } catch (err) { fail('VERDICT_DOOR', err); }
}

function caseReadySeatsHonoursKit() {
  const ws = fs.mkdtempSync(path.join(tmpRoot, 'ws-'));
  const goal = 'g';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  fs.mkdirSync(goalFolder, { recursive: true });
  try {
    const rows = kitRows();
    const out = readySeats(goalFolder, { goal, rows });
    assertOk(out.ready.size === 1 && out.ready.has('worker'), `ready=${[...out.ready.keys()]}`);
    assert.deepStrictEqual(out.ready.get('worker'), ['/seed/a']);
    for (const word of REFUSED) {
      const seat = rows.find((r) => r.verdict === word).seat;
      assertOk(!out.ready.has(seat), `${word} ${seat} was launchable`);
    }
    assert.deepStrictEqual(out.summonedExcluded, ['idle']);
    pass('readySeats: only READY is on the frontier; IDLE fills summonedExcluded');
  } catch (err) { fail('readySeats honours kit', err); }
}

function caseSeedGoalJournalsAndDoesNotEnqueue() {
  const ws = fs.mkdtempSync(path.join(tmpRoot, 'enq-'));
  const goal = 'g';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  const rows = kitRows();
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    'taskforce-id,seat,after\n' + rows.map((r) => `tf,${r.seat},\n`).join(''));
  for (const r of rows) {
    fs.mkdirSync(path.join(goalFolder, 'seats', r.seat), { recursive: true });
    fs.writeFileSync(path.join(goalFolder, 'seats', r.seat, 'seat.md'),
      `---\nseat: ${r.seat}\nharness: bash\nmodel: probe-live\n---\n\nbody\n`);
  }
  const dbPath = path.join(ws, 'heart.db');
  const heartStore = openHeartStore({ dbPath });
  const logs = [];
  try {
    const pickup = seedGoal({
      heartStore, goalFolder, goal, rows, logger: (m) => logs.push(m),
    });
    for (const r of rows.filter((x) => x.verdict !== 'READY')) {
      assertOk(!(pickup.enqueued || []).includes(r.seat), `${r.verdict} ${r.seat} enqueued: ${JSON.stringify(pickup.enqueued)}`);
      const line = logs.find((l) => (l.message || '').includes(r.seat));
      assertOk(line, `no journal line for ${r.seat}: ${JSON.stringify(logs.map((l) => l.message))}`);
      assertOk(
        String(line.message).includes(r.verdict) || String(line.message).includes('SUMMONED'),
        `journal for ${r.seat} missing verdict: ${line.message}`,
      );
    }
    pass('seedGoal: refused verdicts are not enqueued and each is journalled with the kit reason');
  } catch (err) { fail('seedGoal journal', err); }
  finally { heartStore.close(); }
}

function caseReadyContradictedByDoneEnding() {
  const ws = fs.mkdtempSync(path.join(tmpRoot, 'done-'));
  const goal = 'g';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  fs.mkdirSync(goalFolder, { recursive: true });
  try {
    const api = bind(openEndingStoreFor(ws));
    api.stampSeatDeclare({
      goal, seat: 'worker', ending: 'done', declared_outputs: [],
      evidence_pointer: 'seeding.selftest', replace: true,
    });
    const rows = [{ seat: 'worker', verdict: 'READY', reason: 'after: (root — no predecessors)', seed: ['/seed/a'] }];
    const out = readySeats(goalFolder, { goal, rows });
    assertOk(!out.ready.has('worker'), `READY+done still launchable: ${[...out.ready.keys()]}`);
    assertOk(out.contradicted.some((r) => r.seat === 'worker'), `contradicted=${JSON.stringify(out.contradicted)}`);
    const logs = [];
    const heartStore = openHeartStore({ dbPath: path.join(ws, 'heart.db') });
    try {
      fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
      fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), 'taskforce-id,seat,after\ntf,worker,\n');
      seedGoal({ heartStore, goalFolder, goal, rows, logger: (m) => logs.push(m) });
    } finally { heartStore.close(); }
    assertOk(
      logs.some((l) => /READY contradicted by ending done/.test(l.message || '') && /SKEW/.test(l.message || '')),
      JSON.stringify(logs.map((l) => l.message)),
    );
    pass('READY contradicted by ending done is not launched and is journalled as SKEW');
  } catch (err) { fail('READY+done skew', err); }
  finally { closeEndingStores(); }
}

function caseRedIgnoringVerdict() {
  const ws = fs.mkdtempSync(path.join(tmpRoot, 'red-'));
  const goal = 'g';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  fs.mkdirSync(goalFolder, { recursive: true });
  try {
    const rows = kitRows();
    const neu = readyFromEndings(null, goalFolder, { rows, goal });
    assertOk([...neu.keys()].join() === 'worker', `new frontier=${[...neu.keys()]}`);
    const old = new Map();
    for (const r of rows) old.set(r.seat, r.seed || []);
    assertOk(REFUSED.every((w) => old.has(rows.find((r) => r.verdict === w).seat)), 'old map missing a refused seat');
    pass('RED: the ending-clean map would have launched every refused seat');
  } catch (err) { fail('RED ignoring verdict', err); }
}

caseDoorTable();
caseReadySeatsHonoursKit();
caseSeedGoalJournalsAndDoesNotEnqueue();
caseReadyContradictedByDoneEnding();
caseRedIgnoringVerdict();

fs.rmSync(tmpRoot, { recursive: true, force: true });
if (failed) {
  process.stdout.write(`FAIL ${failed} case(s)\n`);
  process.exit(1);
}
process.stdout.write('ALL PASS\n');
process.exit(0);
