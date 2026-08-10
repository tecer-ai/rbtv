#!/usr/bin/env node
'use strict';

// hold-scenario.js — THE BLOCK-AND-QUEUE HOLD, driven end to end, printed as JSON.
//
// It is a SEPARATE FILE from `probe-block-and-queue-hold.js` for one reason: the probe runs it
// THREE times — once against this repo, and twice against MUTANT copies of `engine/` — and a
// mutation proof needs the scenario to be a thing that can be pointed at a different tree. `node
// hold-scenario.js <ignite-root> <tmpdir>` requires the engine from the root it is given.
//
// NOTHING SPAWNS. `engine.tick()` is deliberately never called: it would DISPATCH the seats this
// scenario enqueues, and what is under test is the seeding DECISION, not the ticker. The publish is
// the façade's own `publishRecord()` — the same `publishToRecord` the tick calls, and the same call
// the attached lane's adoption pass makes at boot. What is SUBSTITUTED, disclosed: the seats'
// PROCESSES. Their executions are synthesized into the store through the store's own writers, and
// the ask is appended to `coordination/messages.md` the way `coord.py send` appends it.

const fs = require('node:fs');
const path = require('node:path');

const IGNITE = path.resolve(process.argv[2]);
const TMP = path.resolve(process.argv[3]);

const { createEngine } = require(path.join(IGNITE, 'engine', 'index.js'));
const record = require(path.join(IGNITE, 'engine', 'execution-record.js'));
const yaml = require(path.join(IGNITE, 'node_modules', 'js-yaml'));

const isoNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');

// ── one spawn config, shared by every goal below ──────────────────────────────────────────────
const dataRoot = path.join(TMP, 'data');
fs.mkdirSync(dataRoot, { recursive: true });
const cfg = yaml.load(fs.readFileSync(path.join(IGNITE, 'config', 'spawn-profiles.yaml'), 'utf8'));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(TMP, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
cfg.profiles['probe-hold'] = {
  exec: { argv: ['true'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
const configPath = path.join(TMP, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

const workspace = path.join(TMP, 'workspace');

// A goal folder: alpha (the asking seat) then bravo, which follows it.
function makeGoal(goal, { arm }) {
  const dir = path.join(workspace, '.rbtv', 'goals', goal);
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(dir, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(dir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'taskforce.csv'), 'taskforce-id,seat,after\ntf-hold,alpha,\ntf-hold,bravo,alpha\n');
  fs.writeFileSync(path.join(dir, 'seats', 'alpha', 'seat.md'),
    `---\nseat: alpha\nhuman-interactive: yes\n${arm ? `fallback: ${arm}\n` : ''}---\n\nalpha\n`);
  fs.writeFileSync(path.join(dir, 'seats', 'bravo', 'seat.md'), '---\nseat: bravo\n---\n\nbravo\n');
  fs.writeFileSync(path.join(dir, 'execution-mode'), 'interactive\n');
  return dir;
}

// The bus, appended the way `coord.py send` appends it — `## <id> | from: … | to: … | type: … | ts`
// with a blank line after the body, and always newline-terminated (the ferry's torn-write rule).
let msgId = 0;
function bus(goalDir, { from, to, type, body }) {
  msgId += 1;
  fs.appendFileSync(path.join(goalDir, 'coordination', 'messages.md'),
    `## ${msgId} | from: ${from} | to: ${to} | type: ${type} | 2026-08-10 12:00\n${body}\n\n`);
  return msgId;
}

function withEngine(fn) {
  const engine = createEngine({
    dbPath: path.join(dataRoot, 'heart.db'),
    profiles: cfg.profiles,
    spawnConfigPath: configPath,
    userManager: false,
  });
  try { return fn(engine); } finally { engine.close(); }
}

// One session of a seat, synthesized: it starts, it runs whatever `during` does (that is where the
// ask is written — an agent asks DURING its turn), and it ends with the given turn status.
function runSession(engine, goal, goalDir, seat, { status = 'done', during = null } = {}) {
  const sessionId = `${goal}-${seat}-${Math.random().toString(16).slice(2, 10)}`;
  const exec = engine.heartStore.recordExecutionStart({
    jobId: `seat-${goal}-${seat}`,
    actionType: 'launch-agent',
    args: JSON.stringify({ profile: 'probe-hold' }),
    enqueuedBy: 'daemon',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
    sessionId,
    workdir: path.join(goalDir, 'seats', seat),
  });
  if (during) during(sessionId);
  if (status) {
    engine.heartStore.endTurnAndCloseSession(exec.exec_id, {
      turnStatus: status, sessionStatus: 'closed', endedAt: new Date(),
    });
  }
  return { sessionId, execId: exec.exec_id };
}

const rowsOf = (dir) => record.readExecutionRecord(dir).rows.map((r) => `${r.seat}=${r.outcome || 'open'}`);

// ── THE MAIN SCENARIO: ask → hold → answer → release ──────────────────────────────────────────
function scenario() {
  const goal = 'hold-goal';
  const dir = makeGoal(goal, { arm: 'block-and-queue' });
  const out = {};

  // 1. the wave starts: alpha is due, bravo waits on it
  const pass1 = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  out.seeded = pass1.enqueued;

  // 2. alpha's session: it ASKS THE OWNER on the bus, then exits 0 — the exact 7.626 shape
  withEngine((e) => runSession(e, goal, dir, 'alpha', {
    during: () => bus(dir, { from: 'alpha', to: 'owner', type: 'ask', body: 'which way?' }),
  }));
  withEngine((e) => e.publishRecord());
  out.recordAfterAsk = rowsOf(dir);

  // 3. THE HOLD: the next seeding pass must not start bravo
  const pass2 = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  out.enqueuedWhileHeld = pass2.enqueued;
  out.statesWhileHeld = pass2.states;
  out.blockedOnOwner = Object.keys(pass2.blockedOnOwner || {});

  // 4. THE ANSWER LANDS: the owner's reply mints a session at the ASKING SEAT'S OWN HOME
  //    (`forward-path.js`, route kind `agent`). While that revived session RUNS, bravo must STILL
  //    wait — the F6 concurrency the hold closes.
  const revival = withEngine((e) => runSession(e, goal, dir, 'alpha', { status: null }));
  withEngine((e) => e.publishRecord());
  out.recordDuringRevival = rowsOf(dir);
  const pass3 = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  out.enqueuedDuringRevival = pass3.enqueued;
  out.statesDuringRevival = pass3.states;

  // 5. the revived session finishes the work → the record's `done` releases the wave
  withEngine((e) => e.heartStore.endTurnAndCloseSession(revival.execId, {
    turnStatus: 'done', sessionStatus: 'closed', endedAt: new Date(),
  }));
  withEngine((e) => e.publishRecord());
  out.recordFinal = rowsOf(dir);
  const pass4 = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  out.enqueuedAfterAnswer = pass4.enqueued;
  out.statesAfterAnswer = pass4.states;

  // 6. THE RELAUNCH ESCAPE, on a goal held with no answer coming: the grant clears the hold the
  //    same way it clears a foreign one.
  const g2 = 'hold-goal-relaunch';
  const d2 = makeGoal(g2, { arm: 'block-and-queue' });
  withEngine((e) => e.seedGoal({ goalFolder: d2, goal: g2, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, g2, d2, 'alpha', {
    during: () => bus(d2, { from: 'alpha', to: 'owner', type: 'ask', body: 'anyone?' }),
  }));
  withEngine((e) => e.publishRecord());
  //    Measured as a PAIR against the same goal: without the grant it is held, with it it is not.
  out.relaunchWithout = withEngine((e) => e.seedGoal({ goalFolder: d2, goal: g2, profile: 'probe-hold' })).states;
  out.relaunchWith = withEngine((e) => {
    const { seedGoal } = require(path.join(IGNITE, 'engine', 'seeding.js'));
    return seedGoal({
      heartStore: e.heartStore, goalFolder: d2, goal: g2, profile: 'probe-hold',
      relaunch: new Set(['alpha']),
    });
  }).states;

  return out;
}

// ── THE CONTROLS: every neighbouring case must be UNTOUCHED ───────────────────────────────────
function control(name, { arm, ask = true, answeredBeforeExit = false }) {
  const goal = `ctl-${name}`;
  const dir = makeGoal(goal, { arm });
  withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, goal, dir, 'alpha', {
    during: () => {
      if (!ask) return;
      bus(dir, { from: 'alpha', to: 'owner', type: 'ask', body: 'which way?' });
      if (answeredBeforeExit) bus(dir, { from: 'charlie', to: 'alpha', type: 'answer', body: 'that way' });
    },
  }));
  withEngine((e) => e.publishRecord());
  const pass = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  return { record: rowsOf(dir), enqueued: pass.enqueued, states: pass.states };
}

const result = scenario();
result.controls = {
  'never-asked': control('never-asked', { arm: 'block-and-queue', ask: false }),
  'default-and-disclose': control('default-and-disclose', { arm: 'default-and-disclose' }),
  park: control('park', { arm: 'park' }),
  'no-arm-declared': control('no-arm-declared', { arm: null }),
  'answered-before-exit': control('answered-before-exit', { arm: 'block-and-queue', answeredBeforeExit: true }),
};
process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
