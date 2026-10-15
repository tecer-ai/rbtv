#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { start } = require('./daemon.js');
const { checkMemory } = require('./memory.js');
const { FIXED_TZ } = require('./schedule.js');
const { EMPTY_BOARD, boardPath, parseBoard } = require('./board.js');

const daemonPath = path.join(__dirname, 'daemon.js');
const failures = [];
const pending = [];

// Every folder and every daemon process of this run has one owner, released however the run ends.
// A run killed outright (SIGKILL, or any kill on Windows, which delivers no signal) leaves this one folder.
const runRoot = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-daemon-')));
const daemons = new Set();
process.on('exit', () => {
  for (const child of daemons) if (child.exitCode == null) child.kill('SIGKILL');
  fs.rmSync(runRoot, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
});
for (const signal of ['SIGTERM', 'SIGINT', 'SIGHUP']) process.on(signal, () => process.exit(1));

function launchDaemon(dir, env) {
  const child = spawn(process.execPath, [daemonPath, '--installation', dir], {
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  daemons.add(child);
  child.once('exit', () => daemons.delete(child));
  return child;
}

function test(name, fn) { pending.push([name, fn]); }

// A test of the waking program's Linux-only side: on Windows it is skipped by name, with the reason.
function linuxOnly(name, why, fn) {
  pending.push([name, process.platform === 'win32' ? null : fn, why]);
}

function waitFor(fn, ms = 4000) {
  const startAt = Date.now();
  return new Promise((resolve, reject) => {
    const timer = setInterval(() => {
      try {
        if (fn()) {
          clearInterval(timer);
          resolve();
        } else if (Date.now() - startAt > ms) {
          clearInterval(timer);
          reject(new Error('timeout'));
        }
      } catch (error) {
        clearInterval(timer);
        reject(error);
      }
    }, 20);
  });
}

function configFile(dir) {
  return path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
}

function workspace() {
  const dir = fs.mkdtempSync(path.join(runRoot, 'w-'));
  const agents = path.join(dir, '.rbtv', 'agents');
  fs.mkdirSync(path.dirname(configFile(dir)), { recursive: true });
  fs.mkdirSync(agents, { recursive: true });
  const body = {
    slack: {
      team: 'T1',
      botUserId: 'UBOT',
      ownerUserId: 'UOWNER',
      appTokenEnv: 'IGNITE_APP_TOKEN',
      botTokenEnv: 'IGNITE_BOT_TOKEN',
      ownerTokenEnv: 'IGNITE_OWNER_TOKEN',
      stoolsWorkspace: 'ignite',
    },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' },
    dmAgent: 'master',
    routes: {},
  };
  fs.writeFileSync(configFile(dir), JSON.stringify(body));
  const home = path.join(agents, 'master');
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({
    harness: 'claude', model: 'example-model', effort: 'low',
  }));
  fs.writeFileSync(path.join(home, 'prompt.md'), '---\nname: master\n---\n', 'utf8');
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  fs.mkdirSync(path.join(home, 'memory'));
  fs.writeFileSync(path.join(home, 'memory', 'learned.md'), '# Learned rules — master\n', 'utf8');
  const memory = path.join(dir, '.rbtv', 'memory');
  fs.mkdirSync(path.join(memory, '_artifacts'), { recursive: true });
  fs.writeFileSync(path.join(memory, 'profile.md'), '# Profile — Sam\n\n## Who\n\n## Working with Sam\n\n## Now\n', 'utf8');
  fs.writeFileSync(path.join(memory, 'inbox.md'), '# Inbox — waiting to be filed\n', 'utf8');
  fs.writeFileSync(path.join(memory, '_artifacts', 'index.md'), '# Memory index\n| Open | When |\n|---|---|\n', 'utf8');
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.close();
  return { dir, home };
}

function fakeCast(dir) {
  const stub = path.join(dir, 'fake-cast.js');
  const control = path.join(dir, 'control.json');
  const seen = path.join(dir, 'seen.jsonl');
  fs.writeFileSync(control, JSON.stringify({
    agent: {
      disposition: 'completed',
      summary: 'sum',
      nextStep: null,
      workers: [],
      outputs: [],
      replies: [{ text: 'reply-once', audio: false, files: [] }],
    },
    sessionId: 'ses-test',
  }));
  fs.writeFileSync(seen, '');
  fs.writeFileSync(stub, `#!/usr/bin/env node
'use strict';
const fs = require('fs');
const args = process.argv;
const request = JSON.parse(fs.readFileSync(args[args.indexOf('--request') + 1], 'utf8'));
const resultFile = args[args.indexOf('--result') + 1];
const control = JSON.parse(fs.readFileSync(process.env.FAKE_CAST_CONTROL, 'utf8'));
// holdUntil: the turn runs until that file exists.
while (control.holdUntil && !fs.existsSync(control.holdUntil)) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 20);
fs.appendFileSync(process.env.FAKE_CAST_SEEN, JSON.stringify({ prompt: request.prompt }) + '\\n');
const prompt = request.prompt || '';
const resultLine = prompt.split('\\n').find((line) => line.startsWith('RESULT_FILE: '));
const agentFile = resultLine ? resultLine.slice('RESULT_FILE: '.length) : null;
const nonce = prompt.split('\\n').find((line) => line.startsWith('NONCE: ')).slice('NONCE: '.length);
fs.writeFileSync(agentFile, JSON.stringify({ ...control.agent, nonce }));
fs.writeFileSync(resultFile, JSON.stringify({
  ok: true, harness: request.harness, model: request.model, effort: request.effort,
  sessionId: 'ses-test', exitCode: 0, pid: process.pid, pidStart: '1',
}));
process.exit(0);
`);
  fs.chmodSync(stub, 0o755);
  return {
    stub,
    seen,
    env: { FAKE_CAST_CONTROL: control, FAKE_CAST_SEEN: seen },
  };
}

function fakeSlack() {
  const slack = {
    posts: [],
    downloads: [],
    async postMessage(args) {
      slack.posts.push(args);
      return { channel: args.channel, ts: `9.${slack.posts.length}` };
    },
    async addReaction() {},
    async downloadFile() { return slack.downloads; },
  };
  return slack;
}

function fakeSocket() {
  const socket = {
    onEvent: null,
    stopped: false,
    acks: 0,
    async connect(onEvent, onInteraction) { socket.onEvent = onEvent; socket.onInteraction = onInteraction; },
    stop() { socket.stopped = true; },
    async inject(event) {
      const result = await socket.onEvent(event);
      socket.acks += 1;
      return result;
    },
  };
  return socket;
}

function harnessBin(dir, names) {
  const bin = path.join(dir, 'bin');
  fs.mkdirSync(bin, { recursive: true });
  for (const name of names) {
    const file = path.join(bin, name);
    fs.writeFileSync(file, '#!/bin/sh\nexit 0\n');
    fs.chmodSync(file, 0o755);
  }
  return bin;
}

function spawnDaemon(dir, pathEnv = harnessBin(dir, ['claude', 'ignite'])) {
  const child = launchDaemon(dir, { ...process.env, IGNITE_DAEMON_FAKE: '1', PATH: pathEnv });
  let stderr = '';
  let stdout = '';
  child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  return { child, stderr: () => stderr, stdout: () => stdout };
}

// Six withdrawal validation calls at once from their own process, which prints each one's answer and time in ms.
const SIX_CALLS = `
const body = JSON.stringify({ type: 'TRANSFER', transfer: { id: 'tr_7', value: 1, externalReference: 'P-0001', bankAccount: { pixAddressKey: 'kenu@example.com' } } });
Promise.all(Array.from({ length: 6 }, async () => {
  const started = Date.now();
  try {
    const res = await fetch('http://127.0.0.1:' + process.argv[1] + '/asaas/withdrawal-validation', { method: 'POST', body,
      headers: { 'content-type': 'application/json', 'asaas-access-token': 'daemon-test-token' }, signal: AbortSignal.timeout(5000) });
    return { ms: Date.now() - started, body: await res.json() };
  } catch (error) {
    return { ms: Date.now() - started, body: { error: error.message } };
  }
})).then((answers) => process.stdout.write(JSON.stringify(answers)));
`;

test('with a payments section the service answers each withdrawal validation within 1 s from its own thread, routes /payments to the owner panel and sends approvals once', async () => {
  const { dir } = workspace();
  const cfg = JSON.parse(fs.readFileSync(configFile(dir), 'utf8'));
  fs.writeFileSync(configFile(dir), JSON.stringify({ ...cfg, payments: {} }));
  const { Gate } = require('./payments.js');
  const gate = new Gate({ workspace: dir });
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000 } });
  const socket = fakeSocket();
  const runs = [];
  const prevPath = process.env.PATH;
  const prevToken = process.env.ASAAS_WEBHOOK_TOKEN;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prevPath || ''}`;
  process.env.ASAAS_WEBHOOK_TOKEN = 'daemon-test-token';
  let runtime;
  try {
    runtime = await start({
      workspace: dir, slack: fakeSlack(), socket, signals: false, tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000,
      webhookPort: 0, paymentMs: 30,
      paymentRun: async (command, args, input) => {
        runs.push({ command, args, id: JSON.parse(input).id });
        return { code: 0, stdout: '{"provider_id":"tr_7","status":"PENDING","receipt_url":null}', stderr: '' };
      },
    });
    assert.deepEqual(socket.onInteraction.ack('slash_commands', { command: '/payments', user_id: 'UOTHER', team_id: 'T1' }),
      { text: 'Only the owner can open /payments. Nothing changed.' });
    const row = gate.request({ agent: 'master', conversationKey: 'T1:D1:1.1', provider: 'asaas', method: 'pix',
      recipient: { name: 'KENU', key: 'kenu@example.com' }, amountCents: 100, note: 'test' });
    assert.equal(row.state, 'approved');
    await waitFor(() => gate.get(row.id).state === 'sent');
    await new Promise((resolve) => setTimeout(resolve, 120));
    assert.deepEqual(runs, [{ command: 'asaas', args: ['--json', 'pay', 'execute', 'P-0001'], id: 'P-0001' }]);
    const answer = await fetch(`http://127.0.0.1:${runtime.webhookPort}/asaas/withdrawal-validation`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'asaas-access-token': 'daemon-test-token' },
      body: JSON.stringify({ type: 'TRANSFER', transfer: { id: 'tr_7', value: 1, externalReference: 'P-0001', bankAccount: { pixAddressKey: 'kenu@example.com' } } }),
    });
    assert.deepEqual(await answer.json(), { status: 'APPROVED' });
    // The re-review's probe: another process holds the ledger and six calls arrive at once from a separate process.
    // spawnSync also blocks the service's main thread for the whole run: each answer comes from the listener's own
    // thread, within 1 s of its call.
    const { DatabaseSync } = require('node:sqlite');
    const holder = new DatabaseSync(path.join(dir, '.rbtv', 'runtime', 'ignite', 'payments.sqlite'));
    holder.exec('PRAGMA busy_timeout=0; BEGIN IMMEDIATE');
    const client = spawnSync(process.execPath, ['-e', SIX_CALLS, String(runtime.webhookPort)], { encoding: 'utf8', timeout: 15_000 });
    holder.exec('ROLLBACK');
    holder.close();
    const answers = JSON.parse(client.stdout || '[]');
    assert.deepEqual(answers.map((a) => a.body), Array(6).fill({ status: 'REFUSED', refuseReason: 'the ledger is busy (database is locked): nothing was approved' }));
    for (const answer of answers) assert.equal(answer.ms < 1000, true, `answered in ${answer.ms} ms`);
    const port = runtime.webhookPort;
    await runtime.stop('test');
    runtime = null;
    await assert.rejects(fetch(`http://127.0.0.1:${port}/asaas/withdrawal-validation`, { method: 'POST', body: '{}' }));
  } finally {
    process.env.PATH = prevPath;
    if (prevToken === undefined) delete process.env.ASAAS_WEBHOOK_TOKEN;
    else process.env.ASAAS_WEBHOOK_TOKEN = prevToken;
    if (runtime) await runtime.stop('test');
    gate.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('lock-refusal', async () => {
  const { dir } = workspace();
  const holder = spawnDaemon(dir);
  try {
    await waitFor(() => holder.stdout().includes('"event":"ready"') && holder.child.exitCode == null);
    assert.match(holder.stdout(), /"event":"ready".*"installation":/);
    const second = spawnDaemon(dir);
    const code = await new Promise((resolve) => second.child.once('exit', resolve));
    assert.notEqual(code, 0);
    assert.match(second.stderr(), /daemon already running/);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'modules', 'ignite')), false);
  } finally {
    holder.child.kill('SIGTERM');
    await new Promise((resolve) => holder.child.once('exit', resolve));
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('dm-delivered-once', async () => {
  const { dir } = workspace();
  const cast = fakeCast(dir);
  const slack = fakeSlack();
  const socket = fakeSocket();
  const prevPath = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prevPath || ''}`;
  let runtime;
  try {
  runtime = await start({
    workspace: dir,
    slack,
    socket,
    turnCommand: [process.execPath, cast.stub],
    castEnv: cast.env,
    signals: false,
    tickMs: 60_000,
    sweepMs: 60_000,
    drainMs: 50,
  });
    const saved = await socket.inject({
      team: 'T1',
      channel: 'D1',
      channelType: 'im',
      ts: '1.100000',
      threadTs: '1.100000',
      user: 'UOWNER',
      text: 'hello',
      files: [],
      isBotOrSelf: false,
      mentionsBot: false,
    });
    assert.equal(saved.queued, true);
    assert.equal(socket.acks, 1);
    await waitFor(() => slack.posts.length === 1);
    await new Promise((resolve) => setTimeout(resolve, 200));
    assert.equal(slack.posts.length, 1);
    assert.equal(slack.posts[0].text, 'reply-once');
    assert.equal(slack.posts[0].channel, 'D1');
  } finally {
    process.env.PATH = prevPath;
    if (runtime) runtime.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('daemon ticks and ingress leave a missing board visible to recovery and owner delivery', async () => {
  const { dir, home } = workspace();
  fs.unlinkSync(boardPath(home));
  fs.writeFileSync(path.join(home, 'board.md'), 'invalid legacy board', 'utf8');
  const cast = fakeCast(dir);
  const slack = fakeSlack();
  const socket = fakeSocket();
  const prevPath = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prevPath || ''}`;
  let runtime;
  try {
    runtime = await start({ workspace: dir, slack, socket, turnCommand: [process.execPath, cast.stub], castEnv: cast.env,
      signals: false, tickMs: 60_000, sweepMs: 60_000, drainMs: 50 });
    assert.equal(fs.existsSync(boardPath(home)), false);
    await socket.inject({ team: 'T1', channel: 'D1', channelType: 'im', ts: '1.100000', threadTs: '1.100000',
      user: 'UOWNER', text: 'hello', files: [], isBotOrSelf: false, mentionsBot: false });
    await waitFor(() => slack.posts.length === 2);
    assert.ok(slack.posts.some((row) => row.text.includes('Memory alert:') && row.text.includes('board.md')));
    assert.ok(slack.posts.some((row) => row.text === 'reply-once'));
    assert.match(JSON.parse(fs.readFileSync(cast.seen, 'utf8').trim()).prompt, /MISSING MEMORY: .*board\.md/);
    assert.equal(fs.existsSync(boardPath(home)), false);
  } finally {
    process.env.PATH = prevPath;
    if (runtime) runtime.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('due-schedule-one-wake', async () => {
  const { dir, home } = workspace();
  const cast = fakeCast(dir);
  const now = Date.parse('2026-01-01T00:00:00Z');
  const key = 'T1:D1:1.1';
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'D1', rootTs: '1.1', activated: true });
  store.upsertSchedule({
    id: 'due-1',
    conversationKey: key,
    cadence: 'every:1h',
    timezone: FIXED_TZ,
    nextAt: now - 1000,
    note: 'look',
    report: 'when-useful',
  });
  store.close();
  const prevPath = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prevPath || ''}`;
  let runtime;
  try {
  runtime = await start({
    workspace: dir,
    slack: fakeSlack(),
    socket: fakeSocket(),
    turnCommand: [process.execPath, cast.stub],
    castEnv: cast.env,
    now: () => now,
    signals: false,
    tickMs: 40,
    sweepMs: 60_000,
    drainMs: 60_000,
  });
    const count = () => {
      const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
      try {
        return check.db.prepare("SELECT COUNT(*) AS n FROM queue WHERE kind='schedule'").get().n;
      } finally {
        check.close();
      }
    };
    await waitFor(() => count() === 1);
    await new Promise((resolve) => setTimeout(resolve, 120));
    assert.equal(count(), 1);
  } finally {
    process.env.PATH = prevPath;
    if (runtime) runtime.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

linuxOnly('a timer with a check wakes nobody when its check finds nothing, beside a timer without one that wakes as before',
  'the check tool is started as a program, which the waking service does on Linux only', async () => {
  const { dir, home } = workspace();
  const cast = fakeCast(dir);
  const now = Date.parse('2026-01-01T00:00:00Z');
  const key = 'T1:D1:1.1';
  const tool = path.join(home, 'idle-check.js');
  fs.writeFileSync(tool, `#!/usr/bin/env node\nrequire('fs').appendFileSync(__filename + '.runs', 'run\\n');\nprocess.stdout.write('{"new":false}');\n`);
  fs.chmodSync(tool, 0o755);
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'D1', rootTs: '1.1', activated: true });
  for (const [id, checkTool] of [['plain', null], ['checked', './idle-check.js']]) {
    store.upsertSchedule({ id, conversationKey: key, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: now - 1000, note: 'look', checkTool });
  }
  store.close();
  const prevPath = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prevPath || ''}`;
  let runtime;
  try {
    runtime = await start({
      workspace: dir, slack: fakeSlack(), socket: fakeSocket(), turnCommand: [process.execPath, cast.stub], castEnv: cast.env,
      now: () => now, signals: false, tickMs: 40, sweepMs: 60_000, drainMs: 60_000,
    });
    const state = () => {
      const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
      try {
        return {
          wakes: check.db.prepare("SELECT id FROM queue WHERE kind='schedule' ORDER BY id").all().map((row) => row.id),
          checked: check.getSchedule('checked'),
        };
      } finally {
        check.close();
      }
    };
    await waitFor(() => state().checked.next_at === now + 3_600_000);
    await new Promise((resolve) => setTimeout(resolve, 120));
    assert.deepEqual(state().wakes, [`schedule:plain:${now - 1000}`]);
    assert.equal(state().checked.check_tool, './idle-check.js');
    assert.equal(fs.readFileSync(`${tool}.runs`, 'utf8'), 'run\n');
  } finally {
    process.env.PATH = prevPath;
    if (runtime) runtime.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('starts-at-boot', () => {
  const unit = fs.readFileSync(path.join(__dirname, 'units', 'rbtv-ignite-agents.service'), 'utf8');
  assert.match(unit, /^\[Install\]$/m);
  assert.match(unit, /^WantedBy=default\.target$/m);
  const deploy = fs.readFileSync(path.join(__dirname, 'deploy.sh'), 'utf8');
  const enableAt = deploy.indexOf('systemctl --user enable rbtv-ignite-agents.service');
  const restartAt = deploy.indexOf('systemctl --user restart rbtv-ignite-agents.service');
  assert.ok(enableAt >= 0 && restartAt > enableAt);
});

linuxOnly('sigterm-clean', 'the service is stopped with SIGTERM, a signal Windows does not deliver', async () => {
  const { dir } = workspace();
  const holder = spawnDaemon(dir);
  const lock = path.join(dir, '.rbtv', 'runtime', 'ignite', 'daemon.lock');
  try {
    await waitFor(() => holder.stdout().includes('"event":"ready"') && holder.child.exitCode == null);
    assert.equal(fs.existsSync(lock), true, 'the running daemon holds its lock under .rbtv/runtime/ignite/');
    holder.child.kill('SIGTERM');
    const code = await new Promise((resolve) => holder.child.once('exit', resolve));
    assert.equal(code, 0);
    assert.equal(fs.existsSync(lock), false);
  } finally {
    if (holder.child.exitCode == null) holder.child.kill('SIGKILL');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

function fillUnit(pathValue, linkBin) {
  const deploy = fs.readFileSync(path.join(__dirname, 'deploy.sh'), 'utf8');
  const marker = 'const [src, dst, deploy, installation, envFile, pathValue, linkBin]';
  const at = deploy.indexOf(marker);
  assert.ok(at > 0);
  const open = deploy.lastIndexOf("node -e '", at);
  const close = deploy.indexOf("' \"$unit_src\"", at);
  const program = deploy.slice(open + "node -e '".length, close);
  const dst = path.join(os.tmpdir(), `ignite-unit-${process.pid}-${Date.now()}.service`);
  const result = spawnSync(process.execPath, [
    '-e', program,
    path.join(__dirname, 'units', 'rbtv-ignite-agents.service'),
    dst,
    '/opt/deploy',
    '/opt/workspace',
    '/opt/env/.env',
    pathValue,
    linkBin,
  ], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const filled = fs.readFileSync(dst, 'utf8');
  fs.rmSync(dst, { force: true });
  return filled;
}

linuxOnly('unit-path-filled', 'it runs the program inside deploy.sh that fills the systemd unit', () => {
  const filled = fillUnit('/usr/bin:/opt/harness-bin', '/opt/harness-bin');
  assert.match(filled, /^Environment=PATH=\/usr\/bin:\/opt\/harness-bin$/m);
  assert.equal(filled.includes('@PATH@'), false);
  assert.equal(/@[A-Z_]+@/.test(filled), false);
});

linuxOnly('unit-path-has-link-bin', 'it runs the program inside deploy.sh that fills the systemd unit', () => {
  const linkBin = '/opt/rbtv-bin';
  const filled = fillUnit('/usr/bin', linkBin);
  assert.match(filled, /^Environment=PATH=\/opt\/rbtv-bin:\/usr\/bin$/m);
  assert.equal(filled.includes('@PATH@'), false);
});

test('launch-json-drives-preflight', async () => {
  const { dir, home } = workspace();
  const launchPath = path.join(home, 'agent.json');
  const launch = JSON.parse(fs.readFileSync(launchPath, 'utf8'));
  launch.harness = 'missing-home';
  fs.writeFileSync(launchPath, JSON.stringify(launch));
  const side = path.join(dir, '.rbtv', 'agents', 'side');
  fs.mkdirSync(side, { recursive: true });
  fs.writeFileSync(path.join(side, 'agent.json'), JSON.stringify({
    harness: 'missing-side', model: 'm', effort: 'low',
  }));
  fs.writeFileSync(path.join(side, 'prompt.md'), '---\nname: side\n---\n', 'utf8');
  const empty = fs.mkdtempSync(path.join(dir, 'empty-'));
  const child = launchDaemon(dir, { ...process.env, IGNITE_DAEMON_FAKE: '1', PATH: empty });
  let stdout = '';
  let stderr = '';
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
  try {
    const code = await new Promise((resolve) => child.once('exit', resolve));
    assert.notEqual(code, 0);
    assert.match(stdout, /"event":"error"/);
    assert.match(stdout, /missing-home/);
    assert.match(stdout, /missing-side/);
    assert.equal(stdout.includes('missing-default'), false);
    const loggedPath = JSON.stringify(empty).slice(1, -1);
    assert.match(stdout, new RegExp(loggedPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.equal(stdout.includes('"event":"ready"'), false);
    assert.match(stderr, /harness not on PATH: missing-home/);
    assert.match(stderr, /harness not on PATH: missing-side/);
  } finally {
    if (child.exitCode == null) child.kill('SIGKILL');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('a folder still holding the old prompt name is logged at start, once, with the rename command', async () => {
  const { dir } = workspace();
  const old = path.join(dir, '.rbtv', 'agents', 'old');
  fs.mkdirSync(old, { recursive: true });
  fs.writeFileSync(path.join(old, 'agent.json'), JSON.stringify({ harness: 'claude', model: 'm', effort: 'low' }));
  fs.writeFileSync(path.join(old, 'agent.md'), '---\nname: old\n---\n', 'utf8');
  const empty = fs.mkdtempSync(path.join(dir, 'empty-'));
  const child = launchDaemon(dir, { ...process.env, IGNITE_DAEMON_FAKE: '1', PATH: empty });
  let stdout = '';
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  try {
    await new Promise((resolve) => child.once('exit', resolve));
    const home = path.join(fs.realpathSync(dir), '.rbtv', 'agents', 'old');
    const logged = stdout.split('\n').filter(Boolean).map((line) => JSON.parse(line)).filter((line) => line.slug === 'old');
    assert.deepEqual(logged.map(({ event, slug, message }) => ({ event, slug, message })), [{
      event: 'error',
      slug: 'old',
      message: `${path.join(home, 'prompt.md')} is missing. This folder still has agent.md, the old name of the prompt file. If another machine already renamed it, pull first; otherwise rename it with: git mv agent.md prompt.md (inside ${home}), and change any .gitignore line that names agent.md.`,
    }]);
  } finally {
    if (child.exitCode == null) child.kill('SIGKILL');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('unset-token-refuses', async () => {
  const { dir } = workspace();
  const appName = `IGNITE_W5A_APP_${process.pid}`;
  const botName = `IGNITE_W5A_BOT_${process.pid}`;
  const secret = 'xoxb-do-not-print-w5a';
  const cfgPath = configFile(dir);
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  cfg.slack.appTokenEnv = appName;
  cfg.slack.botTokenEnv = botName;
  fs.writeFileSync(cfgPath, JSON.stringify(cfg));
  const envDir = path.join(dir, '.rbtv', 'config', 'env');
  fs.mkdirSync(envDir, { recursive: true });
  fs.writeFileSync(path.join(envDir, '.env'), `${botName}=${secret}\n`);
  const env = { ...process.env, PATH: harnessBin(dir, ['claude', 'ignite']) };
  delete env.IGNITE_DAEMON_FAKE;
  delete env[appName];
  delete env[botName];
  const child = launchDaemon(dir, env);
  let stdout = '';
  let stderr = '';
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
  try {
    const code = await new Promise((resolve) => child.once('exit', resolve));
    assert.notEqual(code, 0);
    assert.match(stderr, new RegExp(appName));
    assert.equal(stderr.includes(secret), false);
    assert.equal(stdout.includes(secret), false);
    assert.equal(stdout.includes('"event":"ready"'), false);
  } finally {
    if (child.exitCode == null) child.kill('SIGKILL');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('stools-workspace-missing', async () => {
  const { dir } = workspace();
  const cfgPath = configFile(dir);
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  delete cfg.slack.stoolsWorkspace;
  fs.writeFileSync(cfgPath, JSON.stringify(cfg));
  const child = launchDaemon(dir, { ...process.env, IGNITE_DAEMON_FAKE: '1' });
  let stdout = '';
  let stderr = '';
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
  try {
    const code = await new Promise((resolve) => child.once('exit', resolve));
    assert.notEqual(code, 0);
    assert.match(stderr, /stoolsWorkspace required/);
    assert.equal(stdout.includes('"event":"ready"'), false);
  } finally {
    if (child.exitCode == null) child.kill('SIGKILL');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('ignite-missing', async () => {
  const { dir } = workspace();
  const bin = harnessBin(dir, ['claude']);
  const child = launchDaemon(dir, { ...process.env, IGNITE_DAEMON_FAKE: '1', PATH: bin });
  let stdout = '';
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  child.stderr.resume();
  try {
    const code = await new Promise((resolve) => child.once('exit', resolve));
    assert.notEqual(code, 0);
    assert.match(stdout, /"event":"error"/);
    assert.match(stdout, /ignite not on PATH/);
    assert.equal(stdout.includes('"event":"ready"'), false);
  } finally {
    if (child.exitCode == null) child.kill('SIGKILL');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('harness-ready', async () => {
  const { dir } = workspace();
  const holder = spawnDaemon(dir, harnessBin(dir, ['claude', 'ignite']));
  try {
    await waitFor(() => holder.stdout().includes('"event":"ready"') && holder.child.exitCode == null);
    assert.equal(holder.stdout().includes('"event":"error"'), false);
  } finally {
    if (holder.child.exitCode == null) holder.child.kill('SIGTERM');
    await new Promise((resolve) => holder.child.once('exit', resolve));
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

function setRoutes(dir, routes) {
  const file = configFile(dir);
  const body = JSON.parse(fs.readFileSync(file, 'utf8'));
  body.routes = routes;
  fs.writeFileSync(file, JSON.stringify(body));
}

function mention(channel, text = 'hello') {
  return {
    team: 'T1',
    channel,
    channelType: 'channel',
    ts: `${channel}.1`,
    threadTs: `${channel}.1`,
    user: 'UOWNER',
    text,
    files: [],
    isBotOrSelf: false,
    mentionsBot: true,
  };
}

function started(dir, overrides = {}) {
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  const socket = overrides.socket || fakeSocket();
  const slack = overrides.slack || fakeSlack();
  const options = {
    workspace: dir,
    slack,
    socket,
    signals: false,
    tickMs: 60_000,
    sweepMs: 60_000,
    drainMs: 60_000,
  };
  if (overrides.audio) options.audio = overrides.audio;
  return start(options).then((runtime) => ({
    runtime,
    socket,
    slack,
    // Settles when the stopped service has closed every agent's database.
    restore() {
      process.env.PATH = prev;
      return runtime.stop('test');
    },
  }));
}

test('transcription detail is service-log-only', async () => {
  const { dir, home } = workspace();
  setRoutes(dir, { CAUDIO: 'master' });
  const detail = 'audio keys file: /configured/audio-keys.json';
  const audio = { async transcribe() { throw new Error(detail); } };
  const box = await started(dir, { audio });
  box.slack.downloads = [{ name: 'note.m4a', path: '/tmp/note.m4a' }];
  const lines = [];
  const write = process.stdout.write;
  process.stdout.write = (chunk) => { lines.push(String(chunk)); return true; };
  try {
    const saved = await box.socket.inject({
      ...mention('CAUDIO'),
      files: [{ name: 'note.m4a', mimetype: 'audio/mp4', filetype: 'm4a' }],
    });
    assert.equal(saved.queued, true);
    await waitFor(() => box.slack.posts.length === 1 && lines.some((line) => line.includes('transcription-failed')));
    assert.equal(box.slack.posts[0].text, 'I could not transcribe that voice note; please send it as text.');
    const logged = lines.filter((line) => line.includes('transcription-failed'));
    assert.equal(logged.length, 1);
    assert.match(logged[0], /audio-keys\.json/);
    const history = fs.readFileSync(path.join(home, 'runtime', 'ignite', 'conversations', 'T1-CAUDIO-CAUDIO.1', 'history.md'), 'utf8');
    assert.equal(history.includes('/configured/audio-keys.json'), false);
  } finally {
    process.stdout.write = write;
    box.restore();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('route-after-start', async () => {
  const { dir } = workspace();
  const box = await started(dir);
  try {
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    fs.mkdirSync(home, { recursive: true });
    fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({
      harness: 'claude', model: 'example-model', effort: 'low',
    }));
    fs.writeFileSync(path.join(home, 'prompt.md'), '---\nname: probe\n---\n', 'utf8');
    setRoutes(dir, { CNEW: 'probe' });
    const saved = await box.socket.inject(mention('CNEW'));
    assert.equal(saved.queued, true);
    assert.equal(saved.agent, 'probe');
  } finally {
    await box.restore();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('ignored-logged', async () => {
  const { dir } = workspace();
  const box = await started(dir);
  const lines = [];
  const write = process.stdout.write;
  process.stdout.write = (chunk, ...rest) => {
    lines.push(String(chunk));
    return write.call(process.stdout, chunk, ...rest);
  };
  try {
    const saved = await box.socket.inject(mention('CABSENT', 'SECRET_TEXT'));
    assert.equal(saved.ignored, 'unconfigured');
    const hit = lines.filter((line) => line.includes('"event":"ignored"') && line.includes('unconfigured'));
    assert.equal(hit.length, 1);
    assert.equal(hit[0].includes('SECRET_TEXT'), false);
    assert.match(hit[0], /CABSENT/);
  } finally {
    process.stdout.write = write;
    box.restore();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('half-written-config', async () => {
  const { dir } = workspace();
  setRoutes(dir, { COLD: 'master' });
  const box = await started(dir);
  try {
    fs.writeFileSync(configFile(dir), '{');
    const saved = await box.socket.inject(mention('COLD'));
    assert.equal(saved.queued, true);
    assert.equal(saved.agent, 'master');
    const again = await box.socket.inject({ ...mention('COLD'), ts: 'COLD.2', threadTs: 'COLD.2' });
    assert.equal(again.queued, true);
    assert.equal(again.agent, 'master');
  } finally {
    await box.restore();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('daemon marks idle on ticks and answered on owner ingress even while held', async () => {
  const { dir, home } = workspace();
  const now = Date.parse('2026-10-03T12:00:00Z');
  const rootTs = `${(now - 8 * 86_400_000) / 1000}.000000`;
  const text = EMPTY_BOARD.replace('## What matters now\n', `## What matters now\n\n### Review\nWaiting.\n- Threads: [review](https://example.slack.com/archives/D1/p${rootTs.replace('.', '')})\n- Detail: none\n- Flags: none\n`);
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), text, 'utf8');
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.db.prepare('INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)')
    .run('agent_hold', JSON.stringify({ reason: 'test', at: now }), now);
  store.close();
  const socket = fakeSocket();
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  try {
    runtime = await start({ workspace: dir, slack: fakeSlack(), socket, signals: false, now: () => now,
      tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000 });
    const flags = () => parseBoard(fs.readFileSync(boardPath(home), 'utf8')).subjects[0].flags;
    assert.equal(flags(), 'idle since 2026-09-25');
    const input = { team: 'T1', channel: 'D1', channelType: 'im', threadTs: rootTs,
      ts: `${now / 1000}.000000`, user: 'UOWNER', text: 'Reviewed', files: [], isBotOrSelf: false };
    assert.equal((await socket.inject(input)).queued, true);
    assert.equal(flags(), 'answered 2026-10-03');
    assert.equal((await socket.inject(input)).ignored, 'duplicate');
    assert.equal(flags(), 'answered 2026-10-03');
    const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    try { assert.equal(check.agentHold().reason, 'test'); assert.equal(check.getActiveRun(), null); }
    finally { check.close(); }
    // A malformed board must not lose owner ingress or modify the board's bytes.
    fs.writeFileSync(boardPath(home), 'invalid café\r\n', 'utf8');
    assert.equal((await socket.inject({ ...input, ts: `${now / 1000}.000001` })).queued, true);
    assert.equal(fs.readFileSync(boardPath(home), 'utf8'), 'invalid café\r\n');
  } finally {
    process.env.PATH = prev;
    runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('the service shows each owner message\'s live status in Slack and makes no call for one that shows its state', async () => {
  const { dir, home } = workspace();
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  // Held, so no turn runs: the message stays queued. An older message showed its state before the restart.
  store.db.prepare('INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)')
    .run('agent_hold', JSON.stringify({ reason: 'test', at: Date.now() }), Date.now());
  store.upsertConversation({ key: 'T1:D1:1.000001', agent: 'master', workspace: 'T1', channel: 'D1', rootTs: '1.000001' });
  store.setLiveStatus({ conversationKey: 'T1:D1:1.000001', channel: 'D1', ts: '1.000001', system: 'running', task: 'done' });
  store.setLiveShown('D1', '1.000001', { order: ['large_green_circle', 'white_check_mark'], unsure: [], lastAddAt: null, gone: false });
  store.close();
  const calls = [];
  const slack = {
    ...fakeSlack(),
    async addReaction(channel, ts, name) { calls.push(`add ${ts} ${name}`); },
    async removeReaction(channel, ts, name) { calls.push(`remove ${ts} ${name}`); },
  };
  const socket = fakeSocket();
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  try {
    runtime = await start({ workspace: dir, slack, socket, signals: false,
      tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000, statusMs: 20 });
    const input = { team: 'T1', channel: 'D1', channelType: 'im', ts: '2.000001', threadTs: '2.000001',
      user: 'UOWNER', text: 'hello', files: [], isBotOrSelf: false };
    assert.equal((await socket.inject(input)).queued, true);
    for (let i = 0; i < 100 && !calls.length; i++) await new Promise((resolve) => setTimeout(resolve, 20));
    await new Promise((resolve) => setTimeout(resolve, 100));
    assert.deepEqual(calls, ['add 2.000001 hourglass_flowing_sand']);
  } finally {
    process.env.PATH = prev;
    runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

// An owner message accepted before the service starts, as ingress stores it.
function queueOwner(home, ts) {
  const live = require('./live-status.js');
  const key = `T1:D1:${ts}`;
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  try {
    store.acceptOwnerInput({
      key, agent: 'master', workspace: 'T1', channel: 'D1', rootTs: ts, activated: true,
      message: { id: key, role: 'owner', text: 'hello', team: 'T1', channel: 'D1', ts },
      payload: { text: 'hello', ts, threadTs: ts },
    });
    live.received(store, { conversationKey: key, channel: 'D1', ts });
  } finally {
    store.close();
  }
}

function reactionSlack(calls, answered = null) {
  return {
    ...fakeSlack(),
    async addReaction(channel, ts, name) { calls.push(`add ${ts} ${name}`); if (answered) await answered; },
    async removeReaction(channel, ts, name) { calls.push(`remove ${ts} ${name}`); },
  };
}

test('live status runs from the start: a turn the first scheduling pass runs shows while it runs', async () => {
  const { dir, home } = workspace();
  queueOwner(home, '1.000001');
  const cast = fakeCast(dir);
  const release = path.join(dir, 'release');
  const control = JSON.parse(fs.readFileSync(cast.env.FAKE_CAST_CONTROL, 'utf8'));
  fs.writeFileSync(cast.env.FAKE_CAST_CONTROL, JSON.stringify({ ...control, holdUntil: release }));
  const calls = [];
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  // start() returns only once that first pass, and so the whole turn, has ended.
  const starting = start({ workspace: dir, slack: reactionSlack(calls), socket: fakeSocket(), signals: false,
    turnCommand: [process.execPath, cast.stub], castEnv: cast.env,
    tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000, statusMs: 20 });
  let runtime;
  try {
    await waitFor(() => calls.includes('add 1.000001 clock12'), 8000);
    assert.equal(fs.readFileSync(cast.seen, 'utf8'), '', 'the turn is still running');
    assert.deepEqual(calls.filter((call) => !call.includes('hourglass')), ['add 1.000001 large_green_circle', 'add 1.000001 clock12']);
    fs.writeFileSync(release, '');
    runtime = await starting;
    await waitFor(() => calls.includes('add 1.000001 white_check_mark'), 8000);
  } finally {
    fs.writeFileSync(release, '');
    runtime = runtime || await starting.catch(() => null);
    process.env.PATH = prev;
    await runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('a start that fails stops the live status it started and releases the lock', async () => {
  const { dir, home } = workspace();
  const calls = [];
  const socket = { async connect() { throw new Error('socket refused'); }, stop() {} };
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  try {
    await assert.rejects(start({ workspace: dir, slack: reactionSlack(calls), socket, signals: false,
      tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000, statusMs: 20 }), /socket refused/);
    // A ticker left running would show this message.
    queueOwner(home, '1.000001');
    await new Promise((resolve) => setTimeout(resolve, 300));
    assert.deepEqual(calls, []);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'runtime', 'ignite', 'daemon.lock')), false);
  } finally {
    process.env.PATH = prev;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('a stop releases the lock only once the live status call in flight is answered; the pace is kept', async () => {
  const { dir, home } = workspace();
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.db.prepare('INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)')
    .run('agent_hold', JSON.stringify({ reason: 'test', at: Date.now() }), Date.now());
  store.close();
  const runtimeDir = path.join(dir, '.rbtv', 'runtime', 'ignite');
  let answer;
  const answered = new Promise((resolve) => { answer = resolve; });
  const calls = [];
  const socket = fakeSocket();
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  try {
    runtime = await start({ workspace: dir, slack: reactionSlack(calls, answered), socket, signals: false,
      tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000, statusMs: 20 });
    await socket.inject({ team: 'T1', channel: 'D1', channelType: 'im', ts: '2.000001', threadTs: '2.000001',
      user: 'UOWNER', text: 'hello', files: [], isBotOrSelf: false });
    await waitFor(() => calls.length === 1);
    const closed = runtime.stop('test');
    await new Promise((resolve) => setTimeout(resolve, 100));
    assert.equal(fs.existsSync(path.join(runtimeDir, 'daemon.lock')), true, 'held while Slack has not answered');
    answer();
    await closed;
    assert.equal(fs.existsSync(path.join(runtimeDir, 'daemon.lock')), false);
    assert.deepEqual(calls, ['add 2.000001 hourglass_flowing_sand']);
    const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    try { assert.deepEqual(JSON.parse(check.getLiveStatus('D1', '2.000001').shown).order, ['hourglass_flowing_sand']); }
    finally { check.close(); }
    const pace = JSON.parse(fs.readFileSync(path.join(runtimeDir, 'live-status-pace.json'), 'utf8'));
    assert.deepEqual([pace.pausedUntil, pace.adds.length], [0, 1]);
  } finally {
    answer();
    process.env.PATH = prev;
    await runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('a stop aborts the live status call Slack has not answered before the lock is released; the next service removes its name first', async () => {
  const { dir, home } = workspace();
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.db.prepare('INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)')
    .run('agent_hold', JSON.stringify({ reason: 'test', at: Date.now() }), Date.now());
  store.close();
  const lock = path.join(dir, '.rbtv', 'runtime', 'ignite', 'daemon.lock');
  // Slack answers this add later than a stop's 5 s drain. As with fetch, the add lands only if its
  // request is still live when Slack answers; an abort rejects it at once.
  const onMessage = [];
  const calls = [];
  let held = null;
  const slow = {
    ...fakeSlack(),
    addReaction(channel, ts, name, { signal } = {}) {
      calls.push(`add ${ts} ${name}`);
      return new Promise((resolve, reject) => {
        held = { signal, abortedWithLock: null, land() { if (!signal?.aborted) { onMessage.push(name); resolve(); } } };
        signal?.addEventListener('abort', () => { held.abortedWithLock = fs.existsSync(lock); reject(signal.reason); });
      });
    },
    async removeReaction(channel, ts, name) { calls.push(`remove ${ts} ${name}`); },
  };
  const socket = fakeSocket();
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  const opts = { workspace: dir, signals: false, tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000, statusMs: 20 };
  let runtime;
  try {
    runtime = await start({ ...opts, slack: slow, socket });
    await socket.inject({ team: 'T1', channel: 'D1', channelType: 'im', ts: '2.000001', threadTs: '2.000001',
      user: 'UOWNER', text: 'hello', files: [], isBotOrSelf: false });
    await waitFor(() => calls.length === 1);
    const began = Date.now();
    const stopping = runtime.stop('test');
    await waitFor(() => !fs.existsSync(lock), 8000);
    const waited = Date.now() - began;
    // Slack's answer comes after the lock is released: the request was aborted, so nothing lands.
    held.land();
    assert.deepEqual(onMessage, []);
    assert.equal(held.signal?.aborted, true);
    assert.equal(held.abortedWithLock, true);
    assert.ok(waited < 5000, `the stop held the lock ${waited} ms`);
    await stopping;
    runtime = null;
    const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    try {
      const shown = JSON.parse(check.getLiveStatus('D1', '2.000001').shown);
      assert.deepEqual([shown.order, shown.unsure], [[], ['hourglass_flowing_sand']]);
    } finally {
      check.close();
    }
    // The next owner of the lock removes the uncertain name before it shows the state.
    const next = [];
    runtime = await start({ ...opts, slack: reactionSlack(next), socket: fakeSocket() });
    await waitFor(() => next.length === 2);
    assert.deepEqual(next, ['remove 2.000001 hourglass_flowing_sand', 'add 2.000001 hourglass_flowing_sand']);
  } finally {
    held?.land();
    process.env.PATH = prev;
    await runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

linuxOnly('the nightly check wakes only on {"new":true,...}', 'the check tool is started as a program', async () => {
  const { dir, home } = workspace();
  const tool = path.join(home, 'nightly-check.js');
  fs.writeFileSync(tool, `#!/usr/bin/env node
const fs = require('fs');
const n = fs.existsSync(__filename + '.n') ? Number(fs.readFileSync(__filename + '.n', 'utf8')) : 0;
fs.writeFileSync(__filename + '.n', String(n + 1));
process.stdout.write(n === 0 ? '{"new":false}' : '{"new":true,"details":{"reasons":["evidence"]}}');
`);
  fs.chmodSync(tool, 0o755);
  const now = Date.parse('2026-01-02T06:00:00Z');
  const key = 'T1:CALBERT:board';
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'CALBERT', rootTs: 'board', activated: true });
  store.upsertSchedule({ id: 'albert-nightly', conversationKey: key, cadence: 'cron:0 3 * * *', timezone: 'America/Sao_Paulo', nextAt: now - 1000, note: 'nightly memory check', checkTool: './nightly-check.js' });
  store.close();
  const { createChecks } = require('./timer-check.js');
  const checks = createChecks({ log() {}, now: () => now });
  const opened = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  const quiet = await checks.run({ slug: 'master', home, store: opened, schedule: opened.getSchedule('albert-nightly') });
  assert.equal(quiet.answer, 'nothing');
  assert.equal(quiet.wake, null);
  opened.close();
  const again = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  const woken = await checks.run({ slug: 'master', home, store: again, schedule: again.getSchedule('albert-nightly') });
  assert.equal(woken.answer, 'new');
  assert.equal(woken.wake.inserted, true);
  again.close();
  fs.rmSync(dir, { recursive: true, force: true });
});

linuxOnly('the watchdog timer fires when watchdog says so while the consolidation turn never runs', 'the check tool is started as a program', async () => {
  const { dir, home } = workspace();
  const tool = path.join(home, 'watchdog-check.js');
  fs.writeFileSync(tool, `#!/usr/bin/env node
const fs = require('fs');
fs.writeFileSync(__filename + '.fired', 'fired\\n');
process.stdout.write('{"new":false}');
`);
  fs.chmodSync(tool, 0o755);
  const now = Date.parse('2026-01-02T15:00:00Z');
  const key = 'T1:CALBERT:board';
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'CALBERT', rootTs: 'board', activated: true });
  store.upsertSchedule({ id: 'albert-watchdog', conversationKey: key, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: now - 1000, note: 'memory watchdog', checkTool: './watchdog-check.js' });
  store.close();
  const cast = fakeCast(dir);
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  try {
    runtime = await start({ workspace: dir, slack: fakeSlack(), socket: fakeSocket(), turnCommand: [process.execPath, cast.stub], castEnv: cast.env, now: () => now, signals: false, tickMs: 40, sweepMs: 60_000, drainMs: 60_000 });
    await waitFor(() => fs.existsSync(`${tool}.fired`));
    await new Promise((resolve) => setTimeout(resolve, 150));
    const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    try {
      assert.equal(check.db.prepare("SELECT COUNT(*) AS n FROM queue WHERE kind='schedule'").get().n, 0);
    } finally { check.close(); }
    assert.equal(fs.readFileSync(cast.seen, 'utf8'), '');
  } finally {
    process.env.PATH = prev;
    if (runtime) runtime.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

linuxOnly('the third failed check queues one notice in Albert\'s channel and none to the direct-message agent', 'the check tool is started as a program', async () => {
  const { dir, home } = workspace();
  const dm = path.join(dir, '.rbtv', 'agents', 'dm');
  fs.mkdirSync(path.join(dm, 'runtime', 'ignite'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), JSON.stringify({
    ...JSON.parse(fs.readFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), 'utf8')),
    dmAgent: 'dm',
  }));
  const tool = path.join(home, 'fail-check.js');
  fs.writeFileSync(tool, '#!/usr/bin/env node\nprocess.exit(1);\n');
  fs.chmodSync(tool, 0o755);
  const now = Date.parse('2026-01-02T06:00:00Z');
  const key = 'T1:CALBERT:board';
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'CALBERT', rootTs: 'board', activated: true });
  store.upsertSchedule({ id: 'albert-nightly', conversationKey: key, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: now - 1000, note: 'nightly memory check', checkTool: './fail-check.js' });
  store.close();
  new Store(path.join(dm, 'runtime', 'ignite', 'state.sqlite')).close();
  const { createChecks } = require('./timer-check.js');
  for (let i = 0; i < 3; i += 1) {
    const checks = createChecks({ log() {}, now: () => now + i });
    const opened = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    opened.db.prepare('UPDATE schedules SET next_at=? WHERE id=?').run(now - 1000, 'albert-nightly');
    const schedule = opened.getSchedule('albert-nightly');
    await checks.run({ slug: 'master', home, store: opened, schedule });
    opened.close();
  }
  const albertStore = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  const dmStore = new Store(path.join(dm, 'runtime', 'ignite', 'state.sqlite'));
  try {
    const notices = albertStore.pendingOutbox();
    assert.equal(notices.length, 1);
    assert.match(notices[0].payload.text, /failed 3 times/);
    assert.equal(dmStore.pendingOutbox().length, 0);
  } finally {
    albertStore.close();
    dmStore.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('the Friday timer is at 08:45 America/Sao_Paulo', () => {
  const { nextOccurrence } = require('./schedule.js');
  const next = nextOccurrence('cron:45 8 * * 5', 'America/Sao_Paulo', Date.parse('2026-01-01T00:00:00Z'));
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo', weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(next)).filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]));
  assert.equal(parts.weekday, 'Fri');
  assert.equal(parts.hour, '08');
  assert.equal(parts.minute, '45');
  assert.equal(process.env.TZ, process.env.TZ);
});

// ignite deploy --after-turn, from the daemon's side: the deploy waits for the turn, starts once,
// and its log line comes back as a wake in the conversation that asked (waiting_workers), or as a
// post when that work no longer waits.
for (const waits of [true, false]) {
  test(`deploy-after-turn-${waits ? 'wakes' : 'posts'}`, async () => {
    const deferred = require('./deferred-deploy.js');
    const { dir } = workspace();
    const cast = fakeCast(dir);
    const control = JSON.parse(fs.readFileSync(cast.env.FAKE_CAST_CONTROL, 'utf8'));
    control.agent = { ...control.agent, disposition: waits ? 'waiting_workers' : 'completed',
      workers: waits ? [{ ref: 'deploy:c1e5b34574d6', kind: 'deploy' }] : [], replies: [{ text: 'deploying', audio: false, files: [] }] };
    fs.writeFileSync(cast.env.FAKE_CAST_CONTROL, JSON.stringify(control));
    const slack = fakeSlack();
    const socket = fakeSocket();
    const commit = 'c1e5b34574d62d9173a37ae5bbf266ba32932be3';
    const starts = [];
    const log = path.join(dir, '.rbtv', 'runtime', 'ignite', 'deploys.jsonl');
    const prevPath = process.env.PATH;
    process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prevPath || ''}`;
    let runtime;
    try {
      runtime = await start({ workspace: dir, slack, socket, turnCommand: [process.execPath, cast.stub], castEnv: cast.env,
        signals: false, tickMs: 50, sweepMs: 60_000, drainMs: 50,
        deployStart(req) {
          starts.push(req);
          fs.appendFileSync(log, `${JSON.stringify({ time: new Date().toISOString(), commitAsked: req.commit, outcome: 'ok' })}\n`);
          return { ok: true };
        } });
      await socket.inject({ team: 'T1', channel: 'D1', channelType: 'im', ts: '1.100000', threadTs: '1.100000',
        user: 'UOWNER', text: 'deploy it', files: [], isBotOrSelf: false, mentionsBot: false });
      await waitFor(() => slack.posts.some((row) => row.text === 'deploying'));
      const key = fs.readFileSync(cast.seen, 'utf8').trim().split('\n').map((line) => JSON.parse(line))[0]
        .prompt.match(/^HISTORY_FILE: .*conversations\/([^/]+)\/history\.md$/m)[1].replace(/-/g, ':');
      fs.mkdirSync(path.dirname(log), { recursive: true });
      control.agent = { ...control.agent, disposition: 'completed', workers: [], replies: [{ text: 'confirmed', audio: false, files: [] }] };
      fs.writeFileSync(cast.env.FAKE_CAST_CONTROL, JSON.stringify(control));
      deferred.request({ installation: dir, commit, deployFolder: '/deploy', agent: 'master', conversation: key });
      if (waits) {
        await waitFor(() => slack.posts.some((row) => row.text === 'confirmed'));
        const prompts = fs.readFileSync(cast.seen, 'utf8').trim().split('\n').map((line) => JSON.parse(line).prompt);
        assert.match(prompts.at(-1), new RegExp(`^\\[wake\\] Deploy of ${commit} \\(asked with ignite deploy --after-turn\\) finished: ok\\.`, 'm'));
      } else {
        await waitFor(() => slack.posts.some((row) => row.text.startsWith(`Deploy of ${commit}`)));
        assert.equal(slack.posts.some((row) => row.text === 'confirmed'), false, 'no turn: the line is posted');
      }
      assert.equal(starts.length, 1);
      assert.equal(fs.existsSync(deferred.requestFile(dir)), false);
    } finally {
      process.env.PATH = prevPath;
      if (runtime) runtime.stop('test');
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
}

async function runAll() {
  for (const [name, fn, why] of pending) {
    if (!fn) { console.log(`skip: ${name} is Linux-only: ${why}`); continue; }
    try {
      await fn();
      console.log(`PASS ${name}`);
    } catch (error) {
      failures.push(name);
      console.log(`FAIL ${name}: ${error.stack || error.message}`);
    }
  }
  if (failures.length) {
    console.log(`${failures.length} failed`);
    process.exit(1);
  }
  console.log('all daemon tests passed');
}

runAll();
