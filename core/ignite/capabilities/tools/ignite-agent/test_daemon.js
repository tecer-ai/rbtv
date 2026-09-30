#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { start } = require('./daemon.js');
const { FIXED_TZ } = require('./schedule.js');

const daemonPath = __filename.replace(/test_daemon\.js$/, 'daemon.js');
const failures = [];
const pending = [];

function test(name, fn) { pending.push([name, fn]); }

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

function workspace() {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-daemon-')));
  const agents = path.join(dir, '.rbtv', 'agents');
  fs.mkdirSync(agents, { recursive: true });
  const body = {
    workspace: dir,
    slack: {
      team: 'T1',
      botUserId: 'UBOT',
      ownerUserId: 'UOWNER',
      botTokenFile: path.join(dir, 'bot.json'),
      appTokenSource: 'SLACK_APP_TOKEN',
      ownerTokenFile: path.join(dir, 'owner.json'),
      stoolsWorkspace: 'ignite',
    },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' },
    defaultLaunch: { harness: 'claude', model: 'm', effort: 'low' },
    dmAgent: 'master',
    routes: {},
  };
  fs.writeFileSync(path.join(agents, 'ignite.json'), JSON.stringify(body));
  const home = path.join(agents, 'master');
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, 'launch.json'), JSON.stringify({
    harness: 'claude', model: 'sonnet-5', effort: 'low',
  }));
  fs.writeFileSync(path.join(home, 'board.md'), 'board\n');
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
    async postMessage(args) {
      slack.posts.push(args);
      return { channel: args.channel, ts: `9.${slack.posts.length}` };
    },
    async addReaction() {},
  };
  return slack;
}

function fakeSocket() {
  const socket = {
    onEvent: null,
    stopped: false,
    acks: 0,
    async connect(onEvent) { socket.onEvent = onEvent; },
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

function spawnDaemon(dir, pathEnv = harnessBin(dir, ['claude', 'ignite-agent'])) {
  const child = spawn(process.execPath, [daemonPath, '--workspace', dir], {
    env: { ...process.env, IGNITE_DAEMON_FAKE: '1', PATH: pathEnv },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stderr = '';
  let stdout = '';
  child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  return { child, stderr: () => stderr, stdout: () => stdout };
}

test('lock-refusal', async () => {
  const { dir } = workspace();
  const holder = spawnDaemon(dir);
  try {
    await waitFor(() => holder.stdout().includes('"event":"ready"') && holder.child.exitCode == null);
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
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite-agent'])}${path.delimiter}${prevPath || ''}`;
  let runtime;
  try {
  runtime = await start({
    workspace: dir,
    slack,
    socket,
    castCmd: cast.stub,
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

test('due-schedule-one-wake', async () => {
  const { dir, home } = workspace();
  const cast = fakeCast(dir);
  const now = Date.parse('2026-01-01T00:00:00Z');
  const key = 'T1:D1:1.1';
  const store = new Store(path.join(home, 'state.sqlite'));
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
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite-agent'])}${path.delimiter}${prevPath || ''}`;
  let runtime;
  try {
  runtime = await start({
    workspace: dir,
    slack: fakeSlack(),
    socket: fakeSocket(),
    castCmd: cast.stub,
    castEnv: cast.env,
    now: () => now,
    signals: false,
    tickMs: 40,
    sweepMs: 60_000,
    drainMs: 60_000,
  });
    const count = () => {
      const check = new Store(path.join(home, 'state.sqlite'));
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

test('starts-at-boot', () => {
  const unit = fs.readFileSync(path.join(__dirname, 'units', 'rbtv-ignite-agents.service'), 'utf8');
  assert.match(unit, /^\[Install\]$/m);
  assert.match(unit, /^WantedBy=default\.target$/m);
  const deploy = fs.readFileSync(path.join(__dirname, 'deploy.sh'), 'utf8');
  const enableAt = deploy.indexOf('systemctl --user enable rbtv-ignite-agents.service');
  const restartAt = deploy.indexOf('systemctl --user restart rbtv-ignite-agents.service');
  assert.ok(enableAt >= 0 && restartAt > enableAt);
});

test('sigterm-clean', async () => {
  const { dir } = workspace();
  const holder = spawnDaemon(dir);
  const lock = path.join(dir, '.rbtv', 'agents', '.daemon.lock');
  try {
    await waitFor(() => holder.stdout().includes('"event":"ready"') && holder.child.exitCode == null);
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
  const marker = 'const [src, dst, deploy, workspace, envFile, pathValue, linkBin]';
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

test('unit-path-filled', () => {
  const filled = fillUnit('/usr/bin:/opt/harness-bin', '/opt/harness-bin');
  assert.match(filled, /^Environment=PATH=\/usr\/bin:\/opt\/harness-bin$/m);
  assert.equal(filled.includes('@PATH@'), false);
  assert.equal(/@[A-Z_]+@/.test(filled), false);
});

test('unit-path-has-link-bin', () => {
  const linkBin = '/opt/rbtv-bin';
  const filled = fillUnit('/usr/bin', linkBin);
  assert.match(filled, /^Environment=PATH=\/opt\/rbtv-bin:\/usr\/bin$/m);
  assert.equal(filled.includes('@PATH@'), false);
});

test('harness-missing', async () => {
  const { dir, home } = workspace();
  const cfgPath = path.join(dir, '.rbtv', 'agents', 'ignite.json');
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  cfg.defaultLaunch.harness = 'missing-default';
  fs.writeFileSync(cfgPath, JSON.stringify(cfg));
  const launchPath = path.join(home, 'launch.json');
  const launch = JSON.parse(fs.readFileSync(launchPath, 'utf8'));
  launch.harness = 'missing-home';
  fs.writeFileSync(launchPath, JSON.stringify(launch));
  const empty = fs.mkdtempSync(path.join(dir, 'empty-'));
  const child = spawn(process.execPath, [daemonPath, '--workspace', dir], {
    env: { ...process.env, IGNITE_DAEMON_FAKE: '1', PATH: empty },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stdout = '';
  let stderr = '';
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
  try {
    const code = await new Promise((resolve) => child.once('exit', resolve));
    assert.notEqual(code, 0);
    assert.match(stdout, /"event":"error"/);
    assert.match(stdout, /missing-default/);
    assert.match(stdout, /missing-home/);
    assert.match(stdout, new RegExp(empty.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.equal(stdout.includes('"event":"ready"'), false);
    assert.match(stderr, /harness not on PATH/);
  } finally {
    if (child.exitCode == null) child.kill('SIGKILL');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('stools-workspace-missing', async () => {
  const { dir } = workspace();
  const cfgPath = path.join(dir, '.rbtv', 'agents', 'ignite.json');
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  delete cfg.slack.stoolsWorkspace;
  fs.writeFileSync(cfgPath, JSON.stringify(cfg));
  const child = spawn(process.execPath, [daemonPath, '--workspace', dir], {
    env: { ...process.env, IGNITE_DAEMON_FAKE: '1' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
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

test('ignite-agent-missing', async () => {
  const { dir } = workspace();
  const bin = harnessBin(dir, ['claude']);
  const child = spawn(process.execPath, [daemonPath, '--workspace', dir], {
    env: { ...process.env, IGNITE_DAEMON_FAKE: '1', PATH: bin },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stdout = '';
  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  child.stderr.resume();
  try {
    const code = await new Promise((resolve) => child.once('exit', resolve));
    assert.notEqual(code, 0);
    assert.match(stdout, /"event":"error"/);
    assert.match(stdout, /ignite-agent not on PATH/);
    assert.equal(stdout.includes('"event":"ready"'), false);
  } finally {
    if (child.exitCode == null) child.kill('SIGKILL');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('harness-ready', async () => {
  const { dir } = workspace();
  const holder = spawnDaemon(dir, harnessBin(dir, ['claude', 'ignite-agent']));
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
  const file = path.join(dir, '.rbtv', 'agents', 'ignite.json');
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

function started(dir) {
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite-agent'])}${path.delimiter}${prev || ''}`;
  const socket = fakeSocket();
  return start({
    workspace: dir,
    slack: fakeSlack(),
    socket,
    signals: false,
    tickMs: 60_000,
    sweepMs: 60_000,
    drainMs: 60_000,
  }).then((runtime) => ({
    runtime,
    socket,
    restore() {
      process.env.PATH = prev;
      runtime.stop('test');
    },
  }));
}

test('route-after-start', async () => {
  const { dir } = workspace();
  const box = await started(dir);
  try {
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    fs.mkdirSync(home, { recursive: true });
    fs.writeFileSync(path.join(home, 'launch.json'), JSON.stringify({
      harness: 'claude', model: 'sonnet-5', effort: 'low',
    }));
    setRoutes(dir, { CNEW: 'probe' });
    const saved = await box.socket.inject(mention('CNEW'));
    assert.equal(saved.queued, true);
    assert.equal(saved.agent, 'probe');
  } finally {
    box.restore();
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
    fs.writeFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), '{');
    const saved = await box.socket.inject(mention('COLD'));
    assert.equal(saved.queued, true);
    assert.equal(saved.agent, 'master');
    const again = await box.socket.inject({ ...mention('COLD'), ts: 'COLD.2', threadTs: 'COLD.2' });
    assert.equal(again.queued, true);
    assert.equal(again.agent, 'master');
  } finally {
    box.restore();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

async function runAll() {
  for (const [name, fn] of pending) {
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
