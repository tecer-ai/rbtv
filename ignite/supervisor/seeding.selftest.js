'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { readySeats, seedGoal, VERDICT_DOOR, seatHasRun, seatState } = require('./seeding');
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

// ── TASK 165 · a spawn-refused row (no `pid` ever assigned) must not park seeding as `live` ──────
//
// Measured 2026-08-23 on `goal-memory-management`: exec 31629 was spawn-REFUSED for its model pin
// before any process existed (`jobs_log.pid` never set), and `seatHasRun`'s OLD body — any row at
// all — read that `failed` row as `live` FOREVER (`jobIdFor` is fixed per goal+seat, so the row
// never ages out). With no re-offer the seat sat parked until a human removed its queue row by
// hand (`decisions.md` 10:40Z). `seatState` is the ONE state predicate (`owed.js`'s graph half),
// re-exported unchanged from here — this exercises the REAL function, not a stub.
function caseSpawnRefusedRowIsNotParkedLive() {
  try {
    const row = { seat: 'alpha', after: '' };
    const queued = new Set();
    const readyMap = new Map([['alpha', []]]);
    const opts = { ready: readyMap };

    // 1 · AFTER FIX: a `failed` row with NO pid (refused before any process existed) does not
    //     count as "has run" — the seat is offered `ready` again, never parked `live`.
    const byJobRefused = new Map([['seat-g-alpha', [
      { status: 'failed', pid: null, exec_id: 1 },
    ]]]);
    assertOk(seatHasRun(byJobRefused.get('seat-g-alpha')) === false,
      'a pid-less failed row still counts as "has run"');
    const stateAfterRefusal = seatState(row, byJobRefused, queued, { ...opts, goal: 'g' });
    assertOk(stateAfterRefusal === 'ready',
      `spawn-refused row still parks the seat: state=${stateAfterRefusal}`);

    // 2 · DISCRIMINATING CONTROL: a `failed` row that DID carry a pid (a real process that later
    //     crashed) still counts as "has run" — that seat stays `live` and is NOT re-offered here;
    //     it is `reconcile.js`'s class A / D42 "crashed seat is re-run in ONE act", a leader-ruled
    //     path this fast graph pass must not race.
    const byJobCrashed = new Map([['seat-g-alpha', [
      { status: 'failed', pid: 4242, exec_id: 2 },
    ]]]);
    assertOk(seatHasRun(byJobCrashed.get('seat-g-alpha')) === true,
      'a genuinely-spawned (pid-bearing) failed row no longer counts as "has run"');
    const stateAfterCrash = seatState(row, byJobCrashed, queued, { ...opts, goal: 'g' });
    assertOk(stateAfterCrash === 'live',
      `a genuinely crashed seat was re-offered instead of staying live: state=${stateAfterCrash}`);

    // 3 · CONTROL: a genuinely LIVE row (still running) stays `live` — unaffected by this fix.
    const byJobRunning = new Map([['seat-g-alpha', [
      { status: 'running', pid: 4243, exec_id: 3 },
    ]]]);
    const stateRunning = seatState(row, byJobRunning, queued, { ...opts, goal: 'g' });
    assertOk(stateRunning === 'live', `a running seat was not reported live: state=${stateRunning}`);

    // 4 · RED (revert-the-fix) arm: with the OLD body restored (any row at all counts as "has
    //     run"), the spawn-refused row from (1) DOES park the seat as `live` — proving this test
    //     actually discriminates the fix rather than passing regardless.
    const src = fs.readFileSync(path.join(__dirname, 'seeding.js'), 'utf8');
    const ANCHOR = 'function seatHasRun(rows) {\n  return Boolean(rows) && rows.some((r) => !isRefusedBeforeSpawn(r));\n}';
    assertOk(src.includes(ANCHOR), 'task 165 mutation anchor missing from seeding.js');
    const Module = require('node:module');
    const p = path.join(__dirname, 'seeding.js');
    const mut = new Module(p, null);
    mut.filename = p;
    mut.paths = Module._nodeModulePaths(__dirname);
    mut._compile(src.replace(ANCHOR, 'function seatHasRun(rows) {\n  return Boolean(rows) && rows.length > 0;\n}'), p);
    const redState = mut.exports.seatState(row, byJobRefused, queued, { ...opts, goal: 'g' });
    assertOk(redState === 'live', `RED arm did not reproduce the park: state=${redState}`);

    pass('a spawn-refused row (no pid) is re-offered, a crashed/running seat stays live, RED arm reproduces the park');
  } catch (err) { fail('spawn-refused row not parked live', err); }
}

function caseDaemonLanePlacementEnqueue() {
  const ws = fs.mkdtempSync(path.join(tmpRoot, 'place-'));
  const goal = 'test-place';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  const seat = 'worker';
  const workdir = path.join(goalFolder, 'seats', seat);
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.mkdirSync(workdir, { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), 'taskforce-id,seat,after\ntf,worker,\n');
  fs.writeFileSync(path.join(workdir, 'seat.md'),
    '---\nseat: worker\nharness: bash\nmodel: probe-live\n---\n\nbody\n');
  fs.writeFileSync(path.join(goalFolder, 'coordination', 'placement-requests.json'),
    `${JSON.stringify({ worker: { kind: 'daemon-lane', requested_at: '2026-08-31 17:00', workdir } }, null, 2)}\n`);
  const heartStore = openHeartStore({ dbPath: path.join(ws, 'heart.db') });
  const rows = [{ seat, verdict: 'RENEWING', reason: 'successor pending', seed: [] }];
  try {
    const pickup = seedGoal({
      heartStore, goalFolder, goal, rows,
      promptFn: () => ({ prompt: 'boot', reason: null }),
    });
    assertOk((pickup.enqueued || []).includes(seat), `not enqueued: ${JSON.stringify(pickup.enqueued)}`);
    const q = heartStore.listQueue();
    const jobId = `seat-${goal}-${seat}`;
    const row = q.find((r) => r.job_id === jobId);
    assertOk(row, `no queue row job_id=${jobId}: ${JSON.stringify(q)}`);
    assertOk(row.session_mode === 'headless', `session_mode=${row.session_mode}`);
    const args = JSON.parse(row.args);
    assertOk(args.workdir === workdir, `workdir=${args.workdir}`);
    assertOk(!Object.prototype.hasOwnProperty.call(args, 'tmux') && !String(row.args).includes('tmux'),
      `tmux leaked: ${row.args}`);
    assertOk(row.enqueued_by === 'attached-execution', `enqueued_by=${row.enqueued_by}`);
    const left = JSON.parse(fs.readFileSync(path.join(goalFolder, 'coordination', 'placement-requests.json'), 'utf8'));
    assertOk(!left.worker, `request not consumed: ${JSON.stringify(left)}`);
    const spawnSrc = fs.readFileSync(path.join(__dirname, 'spawn', 'spawn.js'), 'utf8');
    assertOk(spawnSrc.includes('buildBwrapArgv') && spawnSrc.includes('composeCageFor'),
      'spawn.js no longer composes bwrap at dispatch');
    pass('seedGoal consumes daemon-lane placement: job_id seat-<goal>-<seat>, headless, seat workdir, no tmux');
  } catch (err) { fail('daemon-lane placement enqueue', err); }
  finally { heartStore.close(); }
}

function caseRenewingWithoutPlacementIsNotEnqueued() {
  const ws = fs.mkdtempSync(path.join(tmpRoot, 'nop-'));
  const goal = 'g';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  const seat = 'worker';
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'seats', seat), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), 'taskforce-id,seat,after\ntf,worker,\n');
  fs.writeFileSync(path.join(goalFolder, 'seats', seat, 'seat.md'),
    '---\nseat: worker\nharness: bash\nmodel: probe-live\n---\n\nbody\n');
  const heartStore = openHeartStore({ dbPath: path.join(ws, 'heart.db') });
  try {
    const pickup = seedGoal({
      heartStore, goalFolder, goal,
      rows: [{ seat, verdict: 'RENEWING', reason: 'successor pending', seed: [] }],
      promptFn: () => ({ prompt: 'boot', reason: null }),
    });
    assertOk(!(pickup.enqueued || []).includes(seat), `RENEWING without request enqueued: ${JSON.stringify(pickup.enqueued)}`);
    pass('RENEWING without a placement request is not enqueued');
  } catch (err) { fail('RENEWING without placement', err); }
  finally { heartStore.close(); }
}

caseDoorTable();
caseReadySeatsHonoursKit();
caseSeedGoalJournalsAndDoesNotEnqueue();
caseReadyContradictedByDoneEnding();
caseRedIgnoringVerdict();
caseSpawnRefusedRowIsNotParkedLive();
caseDaemonLanePlacementEnqueue();
caseRenewingWithoutPlacementIsNotEnqueued();

fs.rmSync(tmpRoot, { recursive: true, force: true });
if (failed) {
  process.stdout.write(`FAIL ${failed} case(s)\n`);
  process.exit(1);
}
process.stdout.write('ALL PASS\n');
process.exit(0);
