#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
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

function spawnDaemon(dir) {
  const child = spawn(process.execPath, [daemonPath, '--workspace', dir], {
    env: { ...process.env, IGNITE_DAEMON_FAKE: '1' },
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
  const runtime = await start({
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
  try {
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
    runtime.stop('test');
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
  const runtime = await start({
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
  try {
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
    runtime.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
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
