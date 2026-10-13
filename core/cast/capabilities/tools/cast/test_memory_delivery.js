#!/usr/bin/env node
'use strict';

// Memory delivery: which cast launches and resumes are given prepared memory, and what the
// context holds. Fixture-only: every case builds its installation, HOME and harness stores in
// a fresh folder under os.tmpdir() and composes the launch with --dry-run; nothing is started.
//   node test_memory_delivery.js

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const CAST = path.join(__dirname, 'cast.js');
const SPARK = path.join(__dirname, '..', 'spark', 'spark.js');
const HARNESSES = { claude: ['sonnet-5-5', 'medium'], codex: ['gpt-6-luna', 'medium'], opencode: ['zai-coding-plan/glm-5.3', 'high'] };
const HEADER = 'Memory for this ongoing session';
const GOOD_BOARD = (watchOuts = []) => `## What matters now\n\n### Review\nReady.\n- Threads: none\n- Detail: none\n- Flags: none\n\n## Watch-outs\n\n${watchOuts.join('\n')}\n\n## Timers\n\n## Recently closed\n\n`;

const failed = [];
function test(name, fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'memory-delivery-'));
  try {
    fn(dir);
    process.stdout.write(`PASS ${name}\n`);
  } catch (e) {
    failed.push(name);
    process.stderr.write(`FAIL ${name}\n${e.stack}\n`);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

// One installation in `dir`: shared memory, a master board and a foreign board that must never
// travel, and the agent for `harness` at `where` ('inside' = .rbtv/agents/ada, 'outside' =
// plan/agents/coord). `personal` false leaves it without learned.md and a board.
function fixture(dir, harness, { where = 'inside', personal = true, task = false } = {}) {
  const root = dir;
  const memory = path.join(root, '.rbtv', 'memory');
  fs.mkdirSync(path.join(memory, '_artifacts'), { recursive: true });
  fs.mkdirSync(path.join(root, '.rbtv', 'config'), { recursive: true });
  fs.writeFileSync(path.join(root, '.rbtv', 'config', 'install.json'), '{}\n');
  fs.writeFileSync(path.join(memory, 'profile.md'), '# Profile — Sam\n\n## Who\n\n- Owner is SHARED-PROFILE (2026-10-01 · note)\n\n## Working with Sam\n\n- Brief (2026-10-01 · note)\n\n## Now\n\n- Busy (2026-10-01 · note)\n');
  fs.writeFileSync(path.join(memory, 'inbox.md'), '# Inbox\n');
  fs.writeFileSync(path.join(memory, '_artifacts', 'index.md'), '# Memory\n\n| Open | When |\n|---|---|\n| [facts](../knowledge/facts.md) | when reviewing facts |\n');
  for (const name of ['master', 'other']) {
    const own = path.join(root, '.rbtv', 'agents', name, '_artifacts');
    fs.mkdirSync(own, { recursive: true });
    fs.writeFileSync(path.join(own, 'board.md'), GOOD_BOARD([`- ${name.toUpperCase()}-BOARD-WATCH (2026-10-01 · ${name})`]));
  }
  const home = where === 'inside' ? path.join(root, '.rbtv', 'agents', 'ada') : path.join(root, 'plan', 'agents', 'coord');
  const [model, effort] = HARNESSES[harness];
  fs.mkdirSync(path.join(home, '_artifacts'), { recursive: true });
  fs.mkdirSync(path.join(home, 'memory'), { recursive: true });
  fs.writeFileSync(path.join(home, 'prompt.md'), 'You are an agent.\n');
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({ name: 'ada', harness, model, effort }));
  if (task) fs.writeFileSync(path.join(home, 'task.md'), 'Do the task.\n');
  if (personal) {
    fs.writeFileSync(path.join(home, 'memory', 'learned.md'), '# Learned rules — ada\n- [correction] OWN-LEARNED rule. Why: owner said so. (2026-10-01 · ada/[t](https://example.com/1))\n');
    fs.writeFileSync(path.join(home, '_artifacts', 'board.md'), GOOD_BOARD(['- OWN-BOARD-WATCH (2026-10-01 · ada)']));
  }
  spawnSync('git', ['init', '-q'], { cwd: root });
  spawnSync('git', ['add', '.'], { cwd: root });
  spawnSync('git', ['-c', 'user.email=t@example.com', '-c', 'user.name=t', 'commit', '-qm', 'init'], { cwd: root });
  const env = { ...process.env, HOME: dir, USERPROFILE: dir, XDG_DATA_HOME: path.join(dir, 'xdg'), RBTV_AGENT_HOME: path.join(dir, 'none') };
  return { root, home, memory, env };
}

// Runs `file args --dry-run` and parses its one JSON line.
function dry(file, args, fx, cwd = fx.root) {
  const res = spawnSync(process.execPath, [file, ...args, '--dry-run'], { encoding: 'utf8', env: fx.env, cwd });
  assert.strictEqual(res.status, 0, `exit ${res.status}: ${res.stderr}`);
  return JSON.parse(res.stdout.trim().split('\n').pop());
}
const launch = (fx, flags) => dry(CAST, ['--agent', fx.home, ...flags], fx);
// The text the composed launch passes in: the prompt argument of a headed one, else stdin.
const sent = (out) => out.stdin_preview ?? out.argv.join('\n');

// Records a headed launch of `harness` in `fx.home` in the handle registry and in the harness's
// own store, as a real one leaves them, and returns the session id.
function openedHeaded(fx, harness) {
  const id = `sess-${harness}`;
  const t0 = Date.now();
  fs.mkdirSync(path.join(fx.env.HOME, '.cast'), { recursive: true });
  fs.appendFileSync(path.join(fx.env.HOME, '.cast', 'handles.jsonl'),
    `${JSON.stringify({ pid: 1, start: null, harness, model: 'm', session: harness === 'claude' ? id : null, folder: fx.home, t0, code: 'ab', agent: fx.home })}\n`);
  if (harness === 'codex') {
    const now = new Date();
    const day = path.join(fx.env.HOME, '.codex', 'sessions', String(now.getUTCFullYear()), String(now.getUTCMonth() + 1).padStart(2, '0'), String(now.getUTCDate()).padStart(2, '0'));
    fs.mkdirSync(day, { recursive: true });
    fs.writeFileSync(path.join(day, 'rollout-x.jsonl'), `${JSON.stringify({ type: 'session_meta', timestamp: now.toISOString(), payload: { id, cwd: fx.home } })}\n`);
  }
  if (harness === 'opencode') {
    fs.mkdirSync(path.join(fx.env.XDG_DATA_HOME, 'opencode'), { recursive: true });
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(path.join(fx.env.XDG_DATA_HOME, 'opencode', 'opencode.db'));
    db.exec('create table session (id text, title text, directory text, time_created integer, time_updated integer, parent_id text)');
    db.prepare('insert into session values (?, ?, ?, ?, ?, null)').run(id, 't', fx.home, t0 + 10, t0 + 10);
    db.close();
  }
  return id;
}

for (const harness of Object.keys(HARNESSES)) {
  test(`headed agent launch carries the prepared bundle (${harness})`, (dir) => {
    const text = sent(launch(fixture(dir, harness), ['--headed']));
    for (const mark of [HEADER, 'SHARED-PROFILE', 'OWN-LEARNED', 'OWN-BOARD-WATCH', 'memory prepare --installation']) assert.ok(text.includes(mark), `missing ${mark}`);
  });

  test(`headed launch carries it with task.md present, the task after the bundle (${harness})`, (dir) => {
    const text = sent(launch(fixture(dir, harness, { task: true }), ['--headed']));
    assert.ok(text.includes(HEADER) && text.indexOf(HEADER) < text.indexOf('Do the task.'));
  });

  test(`eligible headed resume carries a fresh bundle (${harness})`, (dir) => {
    const fx = fixture(dir, harness, { task: true });
    const resume = () => dry(CAST, ['resume', harness, 'sess-1', fx.home, '--headed'], fx);
    assert.ok(sent(resume()).includes('SHARED-PROFILE'));
    fs.writeFileSync(path.join(fx.memory, 'profile.md'), fs.readFileSync(path.join(fx.memory, 'profile.md'), 'utf8').replace('SHARED-PROFILE', 'CHANGED-PROFILE'));
    const text = sent(resume());
    assert.ok(text.includes('CHANGED-PROFILE') && !text.includes('SHARED-PROFILE'), 'resume must prepare again');
    assert.ok(text.includes(HEADER) && text.includes('OWN-BOARD-WATCH'));
  });

  test(`headless resume of a session opened headed carries the bundle (${harness})`, (dir) => {
    const fx = fixture(dir, harness, { task: true });
    const id = openedHeaded(fx, harness);
    const out = dry(CAST, ['resume', harness, id, fx.home, '-p', 'next turn'], fx);
    assert.ok(out.stdin_preview.startsWith(HEADER), out.stdin_preview);
  });

  test(`task-carrying headless --agent launch carries none (${harness})`, (dir) => {
    const out = launch(fixture(dir, harness, { task: true }), []);
    assert.ok(!sent(out).includes('Memory for') && !sent(out).includes('SHARED-PROFILE'));
    // opencode's system text rides ahead of the task in the same message, past the preview
    if (harness !== 'opencode') assert.ok(out.stdin_preview.includes('Do the task.'));
  });

  test(`headless resume with no eligible agent identity carries none (${harness})`, (dir) => {
    const fx = fixture(dir, harness, { task: true });
    openedHeaded(fx, harness);
    // a worker resume of another session in the same agent folder, and a resume outside any agent folder
    const worker = dry(CAST, ['resume', harness, 'worker-session', fx.home, '-p', 'next turn'], fx);
    assert.strictEqual(worker.stdin_preview, 'next turn');
    const plain = path.join(dir, 'plain');
    fs.mkdirSync(plain);
    const outside = dry(CAST, ['resume', harness, 'sess-1', plain, '-p', 'next turn'], fx);
    assert.strictEqual(outside.stdin_preview, 'next turn');
  });
}

test('an agent folder outside .rbtv/agents/ gets its own memory', (dir) => {
  const fx = fixture(dir, 'claude', { where: 'outside' });
  const text = sent(launch(fx, ['--headed']));
  assert.ok(text.includes('OWN-LEARNED') && text.includes('OWN-BOARD-WATCH'));
  assert.ok(text.includes(`--agent-home ${fx.home}`));
});

test('a new plan agent without personal memory does not get the master board', (dir) => {
  const text = sent(launch(fixture(dir, 'claude', { where: 'outside', personal: false }), ['--headed']));
  assert.ok(!text.includes('MASTER-BOARD-WATCH'));
  assert.ok(text.includes('not master') && text.includes('SHARED-PROFILE'));
});

test('a foreign board is absent from the supplied context', (dir) => {
  const text = sent(launch(fixture(dir, 'claude'), ['--headed']));
  assert.ok(!text.includes('OTHER-BOARD-WATCH') && !text.includes('MASTER-BOARD-WATCH'));
});

test('an omitted watch-out produces the mandatory-read text', (dir) => {
  const fx = fixture(dir, 'claude');
  const long = (i) => `- Correction ${i} ${'x'.repeat(1100)} (2026-10-0${i + 1} · ada)`;
  fs.writeFileSync(path.join(fx.home, '_artifacts', 'board.md'), GOOD_BOARD([0, 1, 2, 3, 4, 5].map(long)));
  spawnSync('git', ['add', '.'], { cwd: fx.root });
  spawnSync('git', ['-c', 'user.email=t@example.com', '-c', 'user.name=t', 'commit', '-qm', 'board'], { cwd: fx.root });
  const text = sent(launch(fx, ['--headed']));
  assert.ok(/Omitted watch-outs \(\d+\): read .* before acting\. Mandatory\./.test(text), 'mandatory-read line missing');
  assert.ok(text.includes('memory board read --file') && text.includes('--section Watch-outs'));
  assert.ok(text.includes('This excerpt is not the board'));
});

test('a temporary worker in the coordinator folder gets none; the coordinator and its resume do', (dir) => {
  const fx = fixture(dir, 'claude', { where: 'outside', task: true });
  assert.ok(sent(launch(fx, ['--headed'])).includes('OWN-BOARD-WATCH'), 'coordinator');
  assert.ok(sent(dry(CAST, ['resume', 'claude', 'coord-1', fx.home, '--headed'], fx)).includes('OWN-BOARD-WATCH'), 'coordinator resume');
  const worker = launch(fx, []);
  assert.ok(worker.stdin_preview.includes('Do the task.') && !worker.stdin_preview.includes('Memory for'), 'worker');
  const workerResume = dry(CAST, ['resume', 'claude', 'worker-1', fx.home, '-p', 'more'], fx);
  assert.strictEqual(workerResume.stdin_preview, 'more');
});

// spark finds `cast` on PATH; the stand-in is a #!/bin/sh file, which Windows cannot start.
function sparkSameBundle(dir) {
  const fx = fixture(dir, 'claude', { where: 'outside', task: true });
  const bin = path.join(dir, 'bin');
  fs.mkdirSync(bin);
  fs.writeFileSync(path.join(bin, 'cast'), `#!/bin/sh\nexec "${process.execPath}" "${CAST}" "$@" --dry-run\n`, { mode: 0o755 });
  const env = { ...fx.env, PATH: `${bin}${path.delimiter}${process.env.PATH}` };
  const res = spawnSync(process.execPath, [SPARK, fx.home], { encoding: 'utf8', env, cwd: fx.root });
  assert.strictEqual(res.status, 0, res.stderr);
  const viaSpark = JSON.parse(res.stdout.trim().split('\n').pop());
  // claude's session id is minted per launch: the one argument that differs between two runs
  const same = (out) => out.argv.map((a, i) => (out.argv[i - 1] === '--session-id' ? '<id>' : a));
  assert.deepStrictEqual(same(viaSpark), same(launch(fx, ['--headed'])));
  assert.ok(sent(viaSpark).includes('OWN-BOARD-WATCH'));
}
if (process.platform === 'win32') {
  process.stdout.write('skip: spark passes the same bundle as headed cast is Linux-only: the stand-in cast on PATH is a #!/bin/sh script, which Windows cannot start\n');
} else test('spark passes the same bundle as headed cast', sparkSameBundle);

process.exit(failed.length ? 1 : 0);
