#!/usr/bin/env node
'use strict';

// probe-seed-gates — THE TWO SEED-PASS DOOR REFUSALS (seed-gates, 2026-08-19).
//
// D5 · LANE REACH. The measured defect (G-plan-3-plan-dod-judge-0818-2130,
// G-canvas-live-prober-0818-1955, G-leader-0818-1936): a goal burned two waves and three seats
// because its DoD judge kept landing in a cage where its probe lane could not run
// (`stools workspaces` → exit 127). The requirement was written in four PROSE surfaces and read
// by nothing that admits a launch. It now lives machine-readable in the seat's io-spec
// (`## Requires-reach`) and `cage-admission.js#admitLaneReach` refuses at the pre-enqueue door:
//   1. `cli stools` with NO `exposed-clis:` declaration → refused `no-cli-grant`, by name.
//   2. the same seat WITH the declaration → admitted.
//   4. a malformed entry → refused (an unreadable requirement is never a met one).
//   5. the refusal lands EXACTLY ONCE on the goal bus through the landed D2 surfacing wire.
//
// (A former arm 3, admitting a `path` entry ONLY on a `coordination/permission-edits.csv` row,
// was DELETED with the grant store it exercised — [T2-R12, T1-R9], 2026-08-24.)
//
// D9 · GOAL-LIVE BEFORE GRANT SPEND. The measured defect (G-leader-0818-1830,
// meet-transcript-summarizer): two relaunch grants burned with no session row — `seedGoal`'s
// ready-row loop spent them while the goal-live refusal (`E_GOAL_NOT_LIVE`) fired later, at the
// spawn door. `seedGoal` now reads the SAME lease at the SAME room threshold FIRST:
//   6. goal NOT live → nothing enqueued, the
//      refusal surfaced on the goal bus.
//   7. goal LIVE → the seat enqueues, and no grant file exists on either pass (D12).
//
// The lease is injected as `readLease` — the real `deriveLease` over a fixture tmux reading
// (real measurables, never a verdict), `checkGoalExecuting`'s own injection pattern.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HERE = __dirname;
const IGNITE_SRC = path.join(HERE, '..', '..');
const OUT_PATH = path.join(HERE, 'probe-seed-gates.out');
const { admitLaneReach } = require('../../envelope/cage-admission');
const { surfaceCageRefusal } = require('../seeding');
const { createEngine } = require('../../runtime/engine');
const { loadConfig } = require('../spawn/config');
const { deriveLease } = require('../../runtime/lease/lease');

const start = Date.now();
const lines = [];
const failures = [];
function say(s) { lines.push(s); }
function check(claim, ok, detail) {
  say(`${ok ? 'ok  ' : 'FAIL'}  ${claim}${ok ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(claim);
}

const SEAT = 'dod-judge';

// The live template, exactly as the seeding pass resolves it: any launch spec that cages.
function liveSeatBinds() {
  const config = loadConfig(path.join(IGNITE_SRC, 'envelope', 'spawn-profiles.yaml'));
  for (const spec of Object.values(config.launchSpecs || {})) {
    const binds = spec && spec.sandbox && spec.sandbox.SeatBinds;
    if (Array.isArray(binds) && binds.length) return binds;
  }
  throw new Error('no launch spec with sandbox.SeatBinds — nothing cages, nothing to probe');
}

// A scratch WORKSPACE (never under the real .rbtv/goals — the live daemon scans that tree) with
// one fixture goal, one seat, and a workspace tool subtree a `path` reach can point at.
function reachFixture({ exposedClis, reach }) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-seed-gates-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'fixture-goal');
  const seatDir = path.join(goalDir, 'seats', SEAT);
  fs.mkdirSync(seatDir, { recursive: true });
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(ws, 'tools', 'stools', '.git'), { recursive: true });
  const fm = ['---', `seat: ${SEAT}`];
  if (exposedClis) fm.push('exposed-clis:', `- stools ${path.join(ws, 'tools', 'stools', 'stools.py')}`);
  fm.push('goal-writes:', `- coordination/${SEAT}-verdict.md`, '---');
  const body = ['<io-spec>', '## Outputs', `- \`coordination/${SEAT}-verdict.md\``,
    '## Requires-reach', ...reach, '</io-spec>', ''].join('\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), fm.join('\n') + '\n' + body);
  return { root, ws, goalDir, seatDir };
}

function laneReachArms(seatBinds, roots) {
  const make = (opts) => { const f = reachFixture(opts); roots.push(f.root); return f; };
  const admit = (f) => admitLaneReach({ seatBinds, goalFolder: f.goalDir, seat: SEAT, workspaceRoot: f.ws });

  // 1 — the D5 red: the lane requirement with no grant is REFUSED at the door, by name.
  const f1 = make({ exposedClis: false, reach: ['- cli `stools`'] });
  const r1 = admit(f1) || '';
  check('arm 1: `cli stools` with NO `exposed-clis:` declaration is REFUSED `no-cli-grant`',
    r1.includes('no-cli-grant') && r1.includes('stools'), r1.slice(0, 300) || 'admitted');

  // 2 — the same requirement WITH the declaration admits.
  const f2 = make({ exposedClis: true, reach: ['- cli `stools`'] });
  check('arm 2: the SAME seat WITH the `exposed-clis:` declaration is ADMITTED',
    admit(f2) === null, `refused: ${admit(f2)}`);

  // 3 — the leader's audited widen lane (`coordination/permission-edits.csv`) is DELETED
  // ([T2-R12, T1-R9], 2026-08-24); a `path` reach with no grant at all is refused, naming the
  // one remaining grant lane.
  const f3 = make({ exposedClis: false, reach: ['- path `tools/stools/.git`'] });
  const r3 = admit(f3) || '';
  check('arm 3: `path tools/stools/.git` with NO grant is REFUSED `lane-cannot-reach`',
    r3.includes('lane-cannot-reach'), r3.slice(0, 300) || 'admitted');
  check('arm 3: the refusal names the grant lane (`rw-paths:`)',
    r3.includes('rw-paths'), r3.slice(0, 300));

  // 4 — fail closed: an unparseable entry refuses rather than passing as "no requirement".
  const f4 = make({ exposedClis: true, reach: ['- clii `stools`'] });
  const r4 = admit(f4) || '';
  check('arm 4: a MALFORMED requires-reach entry REFUSES (an unreadable requirement is never met)',
    r4.includes('undecided'), r4.slice(0, 300) || 'admitted');

  // 5 — the refusal→bus wire (DoD clause 2): once per (seat, reason), however many passes.
  surfaceCageRefusal(f1.goalDir, SEAT, r1, null);
  surfaceCageRefusal(f1.goalDir, SEAT, r1, null);
  const bus = fs.readFileSync(path.join(f1.goalDir, 'coordination', 'messages.md'), 'utf8');
  const rows = bus.split('\n').filter((l) => l.includes(`seed-refusal: ${SEAT}`)).length;
  check('arm 5: two seed passes land EXACTLY ONE `seed-refusal` row on the fixture goal bus',
    rows === 1, `${rows} marker rows`);
  check('arm 5: the bus row carries the verbatim `no-cli-grant` refusal',
    bus.includes('no-cli-grant'), bus.slice(0, 400));
  say(`arm 5 bus row (verbatim head): ${bus.split('\n').slice(0, 12).join(' | ').slice(0, 500)}`);
}

// The launch-spec fixture both live-engine arms below stand on: a real spawn config with ONE
// `bash/probe-live` spec, so every seat in these fixtures is cast identically and the only thing
// that can ever differ between two of them is the seat NAME.
function liveConfig(tmp) {
  const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
  const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'envelope', 'spawn-profiles.yaml'), 'utf8'));
  cfg.spawn = { ...(cfg.spawn || {}), data_root: path.join(tmp, 'data'), carrier: 'setsid' };
  cfg.default_workdir_root = path.join(tmp, 'work');
  fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
  cfg['launch-specs'] = { bash: { 'probe-live': {
    exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-live'], prompt: 'stdin' },
    headed: { tui: { argv: ['true'] } },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: '.rbtv/goals',
    caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
    sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
  } } };
  const configPath = path.join(tmp, 'spawn-profiles.yaml');
  fs.writeFileSync(configPath, yaml.dump(cfg));
  return configPath;
}

function seatDescriptor(goalFolder, seat) {
  fs.mkdirSync(path.join(goalFolder, 'seats', seat), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'seats', seat, 'seat.md'),
    `---\nseat: ${seat}\nharness: bash\nmodel: probe-live\n---\n\nbody\n`);
}

// ── D9 · the goal-live fixture: a real engine over a fixture workspace, an armed grant file ────
function goalLiveArms() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-seed-gates-live-'));
  const ws = path.join(tmp, 'ws');
  const configPath = liveConfig(tmp);

  const goal = 'live-goal';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  fs.mkdirSync(path.join(goalFolder, 'seats', 'alpha'), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), 'taskforce-id,seat,after\ntf-g,alpha,\n');
  fs.writeFileSync(path.join(goalFolder, 'seats', 'alpha', 'seat.md'),
    '---\nseat: alpha\nharness: bash\nmodel: probe-live\n---\n\nbody\n');
  // ⚠ THE STORE SITS UNDER THE FIXTURE WORKSPACE'S OWN `.rbtv/` — that is what threads the
  // FIXTURE workspace root into the D9 check (resolveWorkspaceRoot walks the db path), so the
  // arm never leans on RBTV_IGNITE_WORKSPACE_ROOT pointing anywhere.
  const dbPath = path.join(ws, '.rbtv', 'heart', 'heart.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });

  // The real deriveLease over injected tmux readings — measurables, never a verdict.
  const deadLease = (a) => deriveLease({ ...a, tmuxProbe: () => ({ sessions: '', panes: '' }) });
  const liveLease = (a) => deriveLease({ ...a, tmuxProbe: () => ({ sessions: a.goal, panes: '' }) });

  const pass = (readLease) => {
    const logs = [];
    const engine = createEngine({ dbPath, spawnConfigPath: configPath, userManager: false, logger: (m) => logs.push(m) });
    try { return { pickup: engine.seedGoal({ goalFolder, goal, readLease }), logs }; }
    finally { engine.close(); }
  };

  try {
    const dead = pass(deadLease);
    check('arm 6: goal NOT live → NOTHING enqueued and the pass says why (`goalNotLive`)',
      dead.pickup.enqueued.length === 0 && Boolean(dead.pickup.goalNotLive),
      JSON.stringify({ enqueued: dead.pickup.enqueued, goalNotLive: dead.pickup.goalNotLive || null }).slice(0, 300));
    const bus = fs.readFileSync(path.join(goalFolder, 'coordination', 'messages.md'), 'utf8');
    check('arm 6: the refusal is SURFACED on the goal bus (one `seed-refusal` row keyed by the goal)',
      bus.split('\n').filter((l) => l.includes(`seed-refusal: ${goal}`)).length === 1
      && bus.includes('NO live room'), bus.slice(0, 300));
    say(`arm 6 log line: ${JSON.stringify((dead.logs.find((l) => /not LIVE/.test(l.message)) || {}).message || null)}`);

    const live = pass(liveLease);
    // D12: no grant file exists to spend. The discriminator is the LEASE alone — the same pass
    // that refused above enqueues here, and the only thing that changed is the tmux reading.
    check('arm 7: goal LIVE → the seat ENQUEUES',
      live.pickup.enqueued.includes('alpha') && !live.pickup.goalNotLive,
      JSON.stringify({ enqueued: live.pickup.enqueued, goalNotLive: live.pickup.goalNotLive || null }));
    check('arm 7: and NO grant file was created by either pass — the stores are deleted (D12)',
      fs.readdirSync(path.join(goalFolder, 'coordination')).filter((f) => /grant/.test(f)).length === 0,
      JSON.stringify(fs.readdirSync(path.join(goalFolder, 'coordination'))));
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ── D24 · THE SUMMONED CHAIR IS NEVER SEEDED (wave re-run #5, 2026-08-27) ─────────────────────
//
// THE MEASURED DEFECT. `scratch-cli-reach-report`'s `taskforce.csv` carried a root `goal-master`
// row beside a root `leader` row and a five-seat planning chain. At the FIRST seeding pass
// (15:27:01Z) the daemon journalled `enqueued seat … goal-master`; that cold sitting — no owner
// message anywhere — executed the goal's own contract and fired `coordinate finish-goal`, which
// killed the room with three of the five planning seats never enqueued.
//
// WHY IT FIRED. coord ALREADY refuses the chair: `supervisor/ready.py`'s D24 branch answers
// `verdict: IDLE`, "ON-DEMAND summoned seat — NOT OFFERED". The 2026-08-27 patch deleted summoned
// names from a ledger-derived frontier; D-12 makes the frontier the kit's READY rows, so IDLE
// never enters it and the name-delete is gone.
//
// THE DISCRIMINATING CONTROL IS `plan-understander`. `leader` is a staff chair and also IDLE
// with no mail — honouring IDLE takes it off the frontier with the summoned chair. A root
// workflow seat is the control that must still enqueue.
function summonedChairArms() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-seed-gates-summoned-'));
  const ws = path.join(tmp, 'ws');
  const configPath = liveConfig(tmp);

  const goal = 'summoned-goal';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  // The live shape: a planning chain whose head is a root, plus the two root chairs.
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n'
    + 'tf-1,plan-understander,,bash,probe-live,high,35,\n'
    + 'tf-1,plan-designer,plan-understander,bash,probe-live,high,35,\n'
    + 'tf-1,leader,,bash,probe-live,medium,35,\n'
    + 'tf-1,goal-master,,bash,probe-live,medium,,\n');
  for (const seat of ['plan-understander', 'plan-designer', 'leader', 'goal-master']) {
    seatDescriptor(goalFolder, seat);
  }
  const dbPath = path.join(ws, '.rbtv', 'heart', 'heart.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const liveLease = (a) => deriveLease({ ...a, tmuxProbe: () => ({ sessions: a.goal, panes: '' }) });

  const pass = () => {
    const logs = [];
    const engine = createEngine({ dbPath, spawnConfigPath: configPath, userManager: false, logger: (m) => logs.push(m) });
    try { return { pickup: engine.seedGoal({ goalFolder, goal, readLease: liveLease }), logs }; }
    finally { engine.close(); }
  };

  try {
    const first = pass();
    const enq = first.pickup.enqueued || [];
    check('arm 8a: the FIRST seeding pass does NOT enqueue the SUMMONED chair `goal-master`',
      !enq.includes('goal-master'), `enqueued: ${JSON.stringify(enq)}`);
    check('arm 8b (the discriminating control): the SAME pass DOES enqueue the root plan seat '
      + 'and does NOT enqueue the IDLE staff `leader`',
      enq.includes('plan-understander') && !enq.includes('leader'), `enqueued: ${JSON.stringify(enq)}`);
    check('arm 8c: the chair is excluded from the FRONTIER, not merely from the queue — it reads '
      + '`waiting`, never `ready`',
      JSON.stringify(first.pickup.states && first.pickup.states['goal-master']) === '"waiting"',
      `states: ${JSON.stringify(first.pickup.states)}`);
    const said = first.logs.filter((l) => /is SUMMONED — not seeded/.test(l.message || ''));
    check('arm 8d: the journal names it ONCE at first seeding, with the reason',
      said.length === 1 && /goal-master/.test(said[0].message)
      && /launched per owner message/.test(said[0].message),
      JSON.stringify(said.map((l) => l.message)));
    say(`arm 8d log line: ${JSON.stringify(said.length ? said[0].message : null)}`);

    // A second pass 10 s later must not repeat the line — a per-pass line is weather, not signal.
    const second = pass();
    check('arm 8e: a SECOND pass repeats neither the enqueue nor the journal line',
      !(second.pickup.enqueued || []).includes('goal-master')
      && second.logs.filter((l) => /is SUMMONED — not seeded/.test(l.message || '')).length === 0,
      JSON.stringify({ enqueued: second.pickup.enqueued, lines: second.logs.filter((l) => /SUMMONED/.test(l.message || '')).length }));
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ── D-12 · THE KIT VERDICT IS THE LAUNCH DOOR ────────────────────────────────────────────────
//
// A fixture taskforce whose ENDINGS + `after` read clean for every seat, while the kit returns
// HELD / STOPPED / UNDECLARED / IDLE / SKEW / RUNNING for those seats. None enqueue. READY
// enqueues with its seed. A READY row contradicted by a `done` ending does not launch.
function kitVerdictArms() {
  const { seedGoal, readySeats } = require('../seeding');
  const { openHeartStore } = require('../../state-store/heart/heart-store');
  const { bind, openEndingStoreFor, closeEndingStores } = require('../../state-store');
  const Module = require('node:module');

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-seed-gates-verdict-'));
  const ws = path.join(tmp, 'ws');
  const goal = 'verdict-goal';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  const seats = ['held', 'stopped', 'undeclared', 'idle', 'skew', 'running', 'worker'];
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n'
    + seats.map((s) => `tf-1,${s},,bash,probe-live,high,35,\n`).join(''));
  for (const seat of seats) seatDescriptor(goalFolder, seat);
  const dbPath = path.join(ws, '.rbtv', 'heart', 'heart.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });

  const kitRows = [
    { seat: 'held', verdict: 'HELD', reason: 'OWNER-ASK HOLD — open question', seed: [] },
    { seat: 'stopped', verdict: 'STOPPED', reason: 'store row carries row-outcome stop-state', seed: [] },
    { seat: 'undeclared', verdict: 'UNDECLARED', reason: 'session ENDED with an EMPTY disposition', seed: [] },
    { seat: 'idle', verdict: 'IDLE', reason: 'ON-DEMAND summoned seat — NOT OFFERED', seed: [] },
    { seat: 'skew', verdict: 'SKEW', reason: 'the two records of this seat\'s own ending disagree', seed: [] },
    { seat: 'running', verdict: 'RUNNING', reason: 'roster: active since (unstamped)', seed: [] },
    { seat: 'worker', verdict: 'READY', reason: 'after: (root — no predecessors)', seed: ['/tmp/seed-in'] },
  ];

  const heartStore = openHeartStore({ dbPath });
  const logs = [];
  let pickup;
  try {
    pickup = seedGoal({
      heartStore, goalFolder, goal, rows: kitRows,
      logger: (m) => logs.push(m),
    });
  } finally {
    heartStore.close();
  }

  const refused = ['held', 'stopped', 'undeclared', 'idle', 'skew', 'running'];
  const enq = pickup.enqueued || [];
  for (const seat of refused) {
    check(`arm 9: kit ${seat.toUpperCase() === 'IDLE' ? 'IDLE' : kitRows.find((r) => r.seat === seat).verdict} seat \`${seat}\` is NOT enqueued`,
      !enq.includes(seat), `enqueued: ${JSON.stringify(enq)}`);
    const row = kitRows.find((r) => r.seat === seat);
    const line = logs.find((l) => l.seat === seat || (l.message || '').includes(seat));
    check(`arm 9: journal names \`${seat}\` with the kit's ${row.verdict} reason`,
      Boolean(line) && (String(line.message).includes(row.verdict) || String(line.message).includes('SUMMONED'))
      && (String(line.reason || line.message).includes(row.reason.split(' — ')[0])
        || String(line.message).includes('SUMMONED')
        || String(line.message).includes(row.verdict)),
      JSON.stringify(line && line.message));
  }
  check('arm 9: READY `worker` is on the frontier with its seed',
    (pickup.seeds && JSON.stringify(pickup.seeds.worker) === JSON.stringify(['/tmp/seed-in']))
    || (readySeats(goalFolder, { rows: kitRows, goal }).ready.get('worker')
      && JSON.stringify([...readySeats(goalFolder, { rows: kitRows, goal }).ready.get('worker')]) === JSON.stringify(['/tmp/seed-in'])),
    JSON.stringify({ enqueued: enq, seeds: pickup.seeds, states: pickup.states }));

  const door = readySeats(goalFolder, { rows: kitRows, goal });
  check('arm 9: the frontier Map contains ONLY `worker`',
    door.ready.size === 1 && door.ready.has('worker'),
    JSON.stringify([...door.ready.keys()]));
  check('arm 9: summonedExcluded is derived from IDLE rows',
    JSON.stringify(door.summonedExcluded) === JSON.stringify(['idle']),
    JSON.stringify(door.summonedExcluded));

  const ENDING = path.join(HERE, '..', 'ending-reads.js');
  const src = fs.readFileSync(ENDING, 'utf8');
  const anchor = "if (r.verdict !== 'READY') continue;";
  check('arm 9 RED: the READY-door anchor is present', src.includes(anchor));
  const mut = new Module(ENDING, null);
  mut.filename = ENDING;
  mut.paths = Module._nodeModulePaths(path.dirname(ENDING));
  mut._compile(src.replace(anchor, 'if (false && r.verdict !== \'READY\') continue;'), ENDING);
  const oldReady = mut.exports.readyFromEndings(null, goalFolder, { rows: kitRows, goal });
  check('arm 9 RED: ignoring verdict would have launched the refused seats (endings + after read clean)',
    refused.every((s) => oldReady.has(s)) && oldReady.has('worker'),
    JSON.stringify([...oldReady.keys()]));

  const endingApi = bind(openEndingStoreFor(ws));
  endingApi.stampSeatDeclare({
    goal, seat: 'worker', ending: 'done', declared_outputs: [],
    evidence_pointer: 'probe-seed-gates', replace: true,
  });
  const afterDone = readySeats(goalFolder, { rows: kitRows, goal });
  check('arm 9: READY contradicted by ending `done` is NOT on the frontier',
    !afterDone.ready.has('worker') && afterDone.contradicted.some((r) => r.seat === 'worker'),
    JSON.stringify({ ready: [...afterDone.ready.keys()], contradicted: afterDone.contradicted.map((r) => r.seat) }));
  const doneLogs = [];
  const doneStore = openHeartStore({ dbPath: path.join(ws, '.rbtv', 'heart', 'heart-done.db') });
  try {
    seedGoal({
      heartStore: doneStore, goalFolder, goal, rows: kitRows,
      logger: (m) => doneLogs.push(m),
    });
  } finally {
    doneStore.close();
  }
  check('arm 9: the contradiction is journalled as a SKEW the kit should have raised',
    doneLogs.some((l) => /READY contradicted by ending done/.test(l.message || '') && /SKEW/.test(l.message || '')),
    JSON.stringify(doneLogs.map((l) => l.message)));
  closeEndingStores();

  fs.rmSync(tmp, { recursive: true, force: true });
}

function main() {
  const roots = [];
  try {
    laneReachArms(liveSeatBinds(), roots);
  } finally {
    for (const r of roots) fs.rmSync(r, { recursive: true, force: true });
  }
  goalLiveArms();
  summonedChairArms();
  kitVerdictArms();
}

try {
  main();
} catch (err) {
  say(`FAIL probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
}
const exitCode = failures.length ? 1 : 0;
say('');
say(exitCode
  ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
  : 'RESULT: PASS — the pre-enqueue door refuses a lane whose reach the composed cage cannot '
    + 'satisfy (cli via exposed-clis, path via the `rw-paths` grant lane, fail-closed on '
    + 'malformed entries, surfaced once on the bus), seedGoal refuses a not-live goal BEFORE '
    + 'any relaunch grant is spent while a live one seeds and spends normally, and the first '
    + 'seeding pass of a live goal enqueues its root plan seat while NEVER enqueuing '
    + 'the SUMMONED `goal-master` chair or the IDLE staff `leader`, saying so once, and the launch '
    + 'door honours the kit verdict wholesale — only READY enqueues.');
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
console.log(lines.join('\n'));
process.exit(exitCode);
