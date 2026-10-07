#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { start, expiredUntilDate } = require('./daemon.js');
const { runDreamer, getState } = require('./dreamer.js');
const { checkMemory } = require('./memory.js');
const { FIXED_TZ } = require('./schedule.js');
const { EMPTY_BOARD, boardPath, parseBoard } = require('./board.js');

const daemonPath = __filename.replace(/test_daemon\.js$/, 'daemon.js');
const failures = [];
const pending = [];

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
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-daemon-')));
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
    dreamer: { enabled: true, model: { harness: 'codex', model: 'example-model', effort: 3 } },
    routes: {},
  };
  fs.writeFileSync(configFile(dir), JSON.stringify(body));
  const home = path.join(agents, 'master');
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({
    harness: 'claude', model: 'sonnet-5-5', effort: 'low',
  }));
  fs.writeFileSync(path.join(home, 'agent.md'), '---\nname: master\n---\n', 'utf8');
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  fs.mkdirSync(path.join(home, 'memory'));
  fs.writeFileSync(path.join(home, 'memory', 'learned.md'), '# Learned rules — master\n', 'utf8');
  const memory = path.join(dir, '.rbtv', 'memory');
  fs.mkdirSync(path.join(memory, '_artifacts'), { recursive: true });
  fs.writeFileSync(path.join(memory, 'profile.md'), '# Profile — Sam\n\n## Who\n\n## Working with Sam\n\n## Now\n', 'utf8');
  fs.writeFileSync(path.join(memory, 'inbox.md'), '# Inbox — waiting to be filed\n', 'utf8');
  fs.writeFileSync(path.join(memory, '_artifacts', 'index.md'), '# Memory index\n| Open | When |\n|---|---|\n', 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  store.db.prepare("INSERT INTO settings(key, value, updated_at) VALUES ('dreamer', ?, ?)")
    .run(JSON.stringify({ cursor: 0, lastSuccessAt: Date.now(), commit: null }), Date.now());
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

function spawnDaemon(dir, pathEnv = harnessBin(dir, ['claude', 'ignite'])) {
  const child = spawn(process.execPath, [daemonPath, '--installation', dir], {
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

function addOwnerMessage(home, text = 'Please remember this.') {
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    const key = 'T1:D1:1.000000';
    store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'D1', rootTs: '1.000000' });
    store.recordMessage(key, { id: `owner-${Date.now()}`, role: 'owner', text, metadata: { source: 'slack' } });
  } finally { store.close(); }
}

function setDreamerState(home, value) {
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    store.db.prepare(`INSERT INTO settings(key,value,updated_at) VALUES ('dreamer',?,?)
      ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at`)
      .run(JSON.stringify(value), Date.now());
  } finally { store.close(); }
}

function dreamerState(home) {
  const store = new Store(path.join(home, 'state.sqlite'));
  try { return getState(store); } finally { store.close(); }
}

for (const enabled of [undefined, false]) test(`disabled dreamer gates the startup slot and watchdog (${enabled})`, async () => {
  const { dir, home } = workspace();
  const config = JSON.parse(fs.readFileSync(configFile(dir), 'utf8'));
  if (enabled === undefined) delete config.dreamer;
  else config.dreamer = { enabled };
  fs.writeFileSync(configFile(dir), JSON.stringify(config), 'utf8');
  const previous = { cursor: 0, lastSuccessAt: null, commit: null };
  setDreamerState(home, previous);
  addOwnerMessage(home);
  const slack = fakeSlack();
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  let calls = 0;
  let now = Date.parse('2026-10-01T06:00:00Z');
  try {
    runtime = await start({ workspace: dir, slack, socket: fakeSocket(), signals: false, now: () => now,
      tickMs: 20, sweepMs: 60_000, runDreamer: async () => { calls++; return { ok: true }; } });
    now += 7 * 86400_000;
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(calls, 0);
    assert.equal(slack.posts.length, 0);
    assert.deepEqual(dreamerState(home), previous);
  } finally {
    runtime?.stop('test'); process.env.PATH = prev;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('watchdog excludes disabled time, resets on re-enable and survives an enabled restart', async () => {
  const { dir, home } = workspace();
  const day = 86400_000;
  let now = Date.parse('2026-10-01T12:00:00Z'); // Outside the nightly slot.
  // The running service picks up `ignite dreamer enable|disable` on its next tick.
  const enable = async (enabled) => {
    const code = await require('./cli.js').main(['dreamer', enabled ? 'enable' : 'disable', '--installation', dir], { stdout: () => {} });
    assert.equal(code, 0);
    assert.equal(JSON.parse(fs.readFileSync(configFile(dir), 'utf8')).dreamer.enabled, enabled);
  };
  const since = () => {
    const store = new Store(path.join(home, 'state.sqlite'));
    try { return JSON.parse(store.db.prepare("SELECT value FROM settings WHERE key='dreamer_enabled_at'").get()?.value || 'null'); }
    finally { store.close(); }
  };
  setDreamerState(home, { cursor: 0, lastSuccessAt: now - 10 * day, commit: null });
  const slack = fakeSlack();
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  const opts = { workspace: dir, slack, socket: fakeSocket(), signals: false, now: () => now, tickMs: 20, sweepMs: 60_000 };
  let runtime;
  try {
    runtime = await start(opts);
    assert.equal(slack.posts.length, 0); // Old success cannot count disabled time.
    now += day;
    await enable(false);
    await waitFor(() => since() === null);
    now += 10 * day;
    await enable(true);
    await waitFor(() => since() === now);
    const enabledAt = now;
    now += day;
    runtime.stop('restart');
    runtime = await start(opts);
    assert.equal(since(), enabledAt);
    now = enabledAt + 2 * day;
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(slack.posts.length, 0);
    now++;
    await waitFor(() => slack.posts.length === 1);
    assert.match(slack.posts[0].text, /48 hours/);
    await enable(false);
    await waitFor(() => since() === null);
    now += 10 * day;
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(slack.posts.length, 1);
  } finally {
    runtime?.stop('test'); process.env.PATH = prev;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('dreamer runs once at 03:00 Sao Paulo for unread owner messages', async () => {
  const { dir, home } = workspace();
  const now = Date.parse('2026-10-01T06:00:00Z');
  addOwnerMessage(home);
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  let calls = 0;
  try {
    runtime = await start({ workspace: dir, slack: fakeSlack(), socket: fakeSocket(), signals: false, now: () => now,
      tickMs: 20, sweepMs: 60_000, drainMs: 60_000,
      runDreamer: async ({ openStore, now: runAt }) => {
        calls += 1;
        const store = openStore('master');
        store.db.prepare("UPDATE settings SET value=?, updated_at=? WHERE key='dreamer'")
          .run(JSON.stringify({ cursor: 0, lastSuccessAt: runAt, commit: null }), runAt);
        return { ok: true, changed: false, digest: null, alert: null };
      },
    });
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(calls, 1);
  } finally {
    process.env.PATH = prev;
    runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

for (const watch of ['', '- Send one PDF. (2026-09-30 · master)',
  '- Send one PDF. (2026-09-30 · master/[thread](https://app.slack.com/archives/D1/p1000000))']) {
  test(`two quiet nights record success directly with deferred watch-out=${watch || 'none'}`, async () => {
    const { dir, home } = workspace();
    const night = Date.parse('2026-10-01T06:00:00Z');
    const day = 24 * 60 * 60_000;
    let now = night - 1000;
    const homes = [home, path.join(dir, '.rbtv', 'agents', 'alpha')];
    const config = JSON.parse(fs.readFileSync(configFile(dir), 'utf8'));
    config.routes = { C1: 'alpha' };
    fs.writeFileSync(configFile(dir), JSON.stringify(config), 'utf8');
    const original = EMPTY_BOARD.replace('## Watch-outs', `## Watch-outs\n\n${watch}`)
      .replace('## Timers\n\n', '## Timers\n\n| Fires | Timer | For | Subject |\n|---|---|---|---|\n\n').replaceAll('\n', '\r\n');
    const previous = { cursor: 1, lastSuccessAt: night - day, commit: 'existing-commit', reportedConflicts: ['Prior conflict.'] };
    for (const agentHome of homes) {
      fs.mkdirSync(path.join(agentHome, '_artifacts'), { recursive: true });
      fs.mkdirSync(path.join(agentHome, 'memory'), { recursive: true });
      fs.writeFileSync(boardPath(agentHome), original, 'utf8');
      fs.writeFileSync(path.join(agentHome, 'memory', 'learned.md'), `# Learned rules — ${path.basename(agentHome)}\n`, 'utf8');
      addOwnerMessage(agentHome);
      setDreamerState(agentHome, previous);
    }
    const inboxFile = path.join(dir, '.rbtv', 'memory', 'inbox.md');
    const inbox = fs.readFileSync(inboxFile);
    const slack = fakeSlack();
    const prev = process.env.PATH;
    process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
    let runtime;
    let calls = 0;
    try {
      runtime = await start({ workspace: dir, slack, socket: fakeSocket(), signals: false, now: () => now,
        tickMs: 20, sweepMs: 60_000, drainMs: 60_000,
        runDreamer: async () => { calls++; throw new Error('quiet slot must bypass consolidation'); },
      });
      for (const runAt of [night, night + day]) {
        now = runAt;
        await waitFor(() => homes.every((agentHome) => dreamerState(agentHome).lastSuccessAt === runAt));
        now += 30_000;
        await new Promise((resolve) => setTimeout(resolve, 70));
        for (const agentHome of homes) {
          assert.deepEqual(dreamerState(agentHome), { ...previous, lastSuccessAt: runAt });
          assert.equal(fs.readFileSync(boardPath(agentHome), 'utf8'), original);
        }
      }
      now = night + 2 * day - 1000;
      await new Promise((resolve) => setTimeout(resolve, 70));
      assert.equal(calls, 0);
      assert.deepEqual(fs.readFileSync(inboxFile), inbox);
      assert.deepEqual(slack.posts, []);
    } finally {
      process.env.PATH = prev;
      runtime?.stop('test');
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
}

for (const ending of ['\n', '\r\n']) test(`dreamer runs for expiry-only work with valid provenance (${JSON.stringify(ending)})`, async () => {
  const { dir } = workspace();
  const now = Date.parse('2026-10-01T06:00:00Z');
  const file = path.join(dir, '.rbtv', 'memory', 'profile.md');
  const text = `${fs.readFileSync(file, 'utf8')}- Temporary access until 2026-09-30. (2026-09-01 · master/[thread](https://app.slack.com/archives/C1/p1000000001))\n`.replaceAll('\n', ending);
  checkMemory('profile', text);
  fs.writeFileSync(file, text, 'utf8');
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  let calls = 0;
  let model;
  try {
    runtime = await start({ workspace: dir, slack: fakeSlack(), socket: fakeSocket(), signals: false, now: () => now,
      tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000,
      runDreamer: async ({ openStore, now: runAt, model: proposalModel }) => {
        calls += 1;
        model = proposalModel;
        openStore('master').db.prepare("UPDATE settings SET value=?, updated_at=? WHERE key='dreamer'")
          .run(JSON.stringify({ cursor: 0, lastSuccessAt: runAt, commit: null }), runAt);
        return { ok: true, changed: false, digest: null, alert: null };
      },
    });
    assert.equal(calls, 1);
    assert.equal(model, undefined, 'expiry must use the consolidation model, not the quiet-night proposal');
  } finally {
    process.env.PATH = prev;
    runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

for (const ending of ['\n', '\r\n']) test(`inbox-only work runs the model once, then the next night is quiet (${JSON.stringify(ending)})`, async () => {
  const { dir, home } = workspace();
  const night = Date.parse('2026-10-01T06:00:00Z'); const day = 24 * 60 * 60_000;
  let now = night;
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const inboxPath = '.rbtv/memory/inbox.md'; const profilePath = '.rbtv/memory/profile.md';
  const line = '- Prefers café. (2026-10-01 · master)';
  fs.writeFileSync(path.join(dir, inboxPath), `# Inbox${ending}${line}${ending}`, 'utf8');
  const git = (...args) => {
    const result = spawnSync('git', ['-C', dir, ...args], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr); return result.stdout.trim();
  };
  git('init', '-q'); git('config', 'user.name', 'Memory test');
  git('config', 'user.email', 'memory-test@example.invalid'); git('config', 'commit.gpgsign', 'false');
  git('config', 'core.autocrlf', 'false');
  git('add', '--', '.rbtv/memory', '.rbtv/agents/master/memory', '.rbtv/agents/master/_artifacts/board.md');
  git('commit', '-qm', 'Fixture');
  const head = git('rev-parse', 'HEAD');
  const slack = fakeSlack(); const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime; let calls = 0;
  try {
    runtime = await start({ workspace: dir, slack, socket: fakeSocket(), signals: false, now: () => now,
      tickMs: 20, sweepMs: 60_000, drainMs: 60_000,
      runDreamer: async (args) => {
        calls++; assert.equal(args.model, undefined, 'inbox work must select the real proposal call');
        return runDreamer({ ...args, model: (input) => {
          assert.deepEqual(input.messages, []);
          return { operations: [
            { op: 'supersede', path: profilePath, text: `${input.files[profilePath]}${line}\n`, sources: [line], reason: 'file', explanation: 'Owner asked to remember this.' },
            { op: 'supersede', path: inboxPath, text: '# Inbox\n', sources: [line], reason: 'file', explanation: 'Filed the request.',
              removals: [{ text: line, to: profilePath, replacement: line }] },
          ], conflicts: [] };
        } });
      },
    });
    now += 30_000;
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(calls, 1); assert.equal(slack.posts.length, 1);
    assert.match(slack.posts[0].text, /^Memory consolidation/);
    assert.equal(fs.readFileSync(path.join(dir, inboxPath), 'utf8'), `# Inbox${ending}`);
    assert.ok(fs.readFileSync(path.join(dir, profilePath), 'utf8').includes(line));
    assert.equal(dreamerState(home).lastSuccessAt, night);
    const commit = dreamerState(home).commit; assert.ok(commit); assert.notEqual(commit, head);
    now = night + day;
    await waitFor(() => dreamerState(home).lastSuccessAt === now);
    now = night + 2 * day - 1000;
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(calls, 1); assert.equal(slack.posts.length, 1);
    assert.equal(dreamerState(home).commit, commit); assert.equal(dreamerState(home).cursor, 0);
    assert.equal(git('rev-list', '--count', `${head}..HEAD`), '1');
  } finally {
    process.env.PATH = prev;
    runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

for (const ending of ['\n', '\r\n']) test(`expiry uses the final record body and Sao Paulo date (${JSON.stringify(ending)})`, () => {
  const { dir, home } = workspace();
  const profileFile = path.join(dir, '.rbtv', 'memory', 'profile.md');
  const header = fs.readFileSync(profileFile, 'utf8');
  const tail = ' (2026-09-01 · master/[thread](https://app.slack.com/archives/C1/p1000000001))';
  try {
    for (const [body, expected] of [
      ['Temporary access until 2026-09-30.', true],
      ['See (2026-01-01 · verbal) until 2026-09-30.', true],
      ['See (2026-01-01 · verbal) until 2026-10-01.', false],
      ['Temporary access until 2026-09-30', true],
      ['Temporary access until 2026-10-01.', false],
      ['Temporary access until 2026-10-02.', false],
      ['Temporary access until 2026-02-30.', false],
      ['Temporary access until 2026-13-01.', false],
      ['Temporary access until 2026-09-30, pending review.', false],
      ['Temporary access since 2026-09-30.', false],
    ]) {
      const text = `${header}- ${body}${tail}\n`.replaceAll('\n', ending);
      checkMemory('profile', text);
      fs.writeFileSync(profileFile, text, 'utf8');
      assert.equal(expiredUntilDate(dir, ['master'], Date.parse('2026-10-01T06:00:00Z')), expected, body);
    }
    fs.writeFileSync(profileFile, `${header}- Temporary access until 2026-09-30.${tail}\n`.replaceAll('\n', ending), 'utf8');
    assert.equal(expiredUntilDate(dir, ['master'], Date.parse('2026-10-01T02:59:59Z')), false);
    assert.equal(expiredUntilDate(dir, ['master'], Date.parse('2026-10-01T03:00:00Z')), true);
    fs.writeFileSync(profileFile, header, 'utf8');
    fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
    for (const [body, expected] of [
      ['Temporary access until 2026-09-30', true],
      ['Temporary access until 2026-10-01', false],
      ['Temporary access until 2026-10-02', false],
    ]) {
      const text = EMPTY_BOARD.replace('## What matters now', `## What matters now\n\n### Access\n${body}\n- Threads: none\n- Detail: none\n- Flags: none`).replaceAll('\n', ending);
      parseBoard(text);
      fs.writeFileSync(boardPath(home), text, 'utf8');
      assert.equal(expiredUntilDate(dir, ['master'], Date.parse('2026-10-01T06:00:00Z')), expected, body);
    }
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('a failed nightly run leaves success unchanged and a missed slot crosses the 48-hour watchdog threshold', async () => {
  const { dir, home } = workspace();
  const night = Date.parse('2026-10-01T06:00:00Z');
  let now = night;
  addOwnerMessage(home);
  const previous = { cursor: 0, lastSuccessAt: night - 60 * 60_000, commit: null };
  setDreamerState(home, previous);
  const enabledStore = new Store(path.join(home, 'state.sqlite'));
  enabledStore.db.prepare("INSERT INTO settings(key,value,updated_at) VALUES ('dreamer_enabled_at',?,?)")
    .run(JSON.stringify(previous.lastSuccessAt), now);
  enabledStore.close();
  const slack = fakeSlack();
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  const logs = [];
  const write = process.stdout.write;
  process.stdout.write = (text) => { logs.push(JSON.parse(text)); return true; };
  try {
    runtime = await start({ workspace: dir, slack, socket: fakeSocket(), signals: false, now: () => now,
      tickMs: 20, sweepMs: 60_000, drainMs: 60_000,
      runDreamer: async () => ({ ok: false, changed: false, digest: null, alert: 'Dreamer failed: model failed.' }),
    });
    assert.equal(slack.posts.length, 1);
    assert.match(slack.posts[0].text, /^Memory alert: Dreamer failed: model failed\.$/);
    assert.deepEqual(dreamerState(home), previous);
    now = previous.lastSuccessAt + 48 * 60 * 60_000;
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(slack.posts.length, 1);
    now += 1;
    await waitFor(() => slack.posts.length === 2);
    assert.match(slack.posts[1].text, /has not completed a successful run in 48 hours/);
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(slack.posts.length, 2);
    assert.equal(slack.posts[1].threadTs, '9.1');
    const watchdog = logs.find((row) => row.event === 'dreamer-watchdog');
    assert.equal(watchdog.noticeQueued, true);
    assert.equal(watchdog.digestQueued, false);
    assert.equal(watchdog.delivered, true);
    assert.deepEqual(dreamerState(home), previous);
  } finally {
    process.env.PATH = prev;
    runtime?.stop('test');
    process.stdout.write = write;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

for (const [diagnostic, cause] of [
  ['Insufficient credits', 'model out of credits or spending limit'],
  ['Rate limit 429', 'model rate limited'],
  ['Timed out', 'model timed out'],
  ['Unauthorized 401', 'model authentication failed'],
  ['Access denied', 'model failed (exit 1)'],
]) for (const deliver of [false, true]) test(`cast failure (${diagnostic}) reaches the log and ${deliver ? 'delivered' : 'queued'} notice without stderr`, async () => {
  const { dir, home } = workspace();
  const { loadConfig } = require('./config.js');
  const { runInstalledDreamer } = require('./daemon.js');
  addOwnerMessage(home);
  const previous = dreamerState(home);
  const cast = path.join(dir, 'failed cast.js');
  const stderr = `${diagnostic}\r\napi_key synthetic-space-value; api_key=synthetic-equals-value; ` +
    '"api_key": "synthetic-json-value"; Bearer synthetic-bearer-value; Basic synthetic-basic-value; ' +
    'sk-synthetic-provider-value; xoxb-synthetic-slack-value; unlabelled-synthetic-value\r\n';
  fs.writeFileSync(cast, `process.stderr.write(${JSON.stringify(stderr)}); process.exitCode = 1;\n`, 'utf8');
  const config = loadConfig(dir); config.tools.cast = cast;
  const logs = []; const slack = fakeSlack();
  try {
    const result = await runInstalledDreamer({ config, log: (row) => logs.push(row),
      slack: deliver ? slack : null, depsFor: () => ({ slack, home }) });
    assert.equal(result.ok, false); assert.equal(result.digestQueued, false);
    assert.equal(result.noticeQueued, true); assert.equal(result.delivered, deliver);
    assert.equal(result.conflictsSaved, false); assert.equal(result.error, null);
    assert.equal(result.alert, `Dreamer failed: ${cause}.`);
    assert.equal(logs.find((row) => row.event === 'dreamer').message, result.alert);
    const store = new Store(path.join(home, 'state.sqlite'));
    try {
      const notice = deliver ? slack.posts[0].text : store.pendingOutbox()[0].payload.text;
      assert.equal(notice, `Memory alert: ${result.alert}`);
      assert.equal(JSON.stringify({ result, logs, notice, posts: slack.posts }).includes('synthetic'), false);
      assert.deepEqual(dreamerState(home), previous);
    } finally { store.close(); }
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('an installation with no memory or runtime folder yet has no inbox work', async () => {
  const { dir } = workspace();
  const { loadConfig } = require('./config.js');
  const { runInstalledDreamer } = require('./daemon.js');
  fs.rmSync(path.join(dir, '.rbtv', 'memory'), { recursive: true });
  assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'runtime')), false);
  const logs = []; let calls = 0;
  try {
    const result = await runInstalledDreamer({ config: loadConfig(dir), log: (row) => logs.push(row),
      runDreamer: () => { calls++; return { ok: true, changed: false, digest: null, alert: null }; } });
    assert.equal(calls, 0); assert.equal(result.ok, true); assert.equal(result.changed, false);
    assert.equal(logs.some((row) => row.event === 'dreamer-check'), false);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'memory')), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

for (const deliver of [false, true]) test(`cap refusal names only the path and sizes in the log and ${deliver ? 'delivered' : 'queued'} notice`, async () => {
  const { dir, home } = workspace();
  const { loadConfig } = require('./config.js');
  const { runInstalledDreamer } = require('./daemon.js');
  addOwnerMessage(home);
  const previous = dreamerState(home);
  const name = '.rbtv/memory/knowledge/facts.md';
  const text = '---\ndescription: when reviewing facts\ntype: facts\naliases: []\n---\n# Facts\n' + 'private-fixture-content'.repeat(200);
  const logs = []; const slack = fakeSlack();
  try {
    const result = await runInstalledDreamer({ config: loadConfig(dir), log: (row) => logs.push(row),
      slack: deliver ? slack : null, depsFor: () => ({ slack, home }),
      runDreamer: (options) => runDreamer({ ...options, model: (input) => ({ conflicts: [], operations: [{
        op: 'add', path: name, text, sources: input.messages.map((row) => row.rowid),
        reason: 'owner', explanation: 'private-fixture-explanation',
      }] }) }),
    });
    const alert = `Dreamer failed: ${name}: knowledge cap exceeded (${[...text].length}/3000 characters).`;
    assert.equal(result.ok, false); assert.equal(result.alert, alert);
    assert.equal(result.noticeQueued, true); assert.equal(result.digestQueued, false); assert.equal(result.delivered, deliver);
    assert.equal(logs.find((row) => row.event === 'dreamer').message, alert);
    const store = new Store(path.join(home, 'state.sqlite'));
    try {
      const notice = deliver ? slack.posts[0].text : store.pendingOutbox()[0].payload.text;
      assert.equal(notice, `Memory alert: ${alert}`);
      assert.equal(JSON.stringify({ result, logs, notice, posts: slack.posts }).includes('private-fixture'), false);
      assert.deepEqual(dreamerState(home), previous);
      assert.equal(fs.existsSync(path.join(dir, name)), false);
    } finally { store.close(); }
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('dreamer digests reuse the direct-message thread', async () => {
  const { dir, home } = workspace();
  const firstNight = Date.parse('2026-10-01T06:00:00Z');
  addOwnerMessage(home);
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  try {
    const first = fakeSlack();
    const digest = async ({ openStore, now }) => {
      openStore('master').db.prepare("UPDATE settings SET value=?, updated_at=? WHERE key='dreamer'")
        .run(JSON.stringify({ cursor: 0, lastSuccessAt: now, commit: null }), now);
      return { ok: true, changed: true, digest: { text: 'Memory consolidation' }, alert: null };
    };
    runtime = await start({ workspace: dir, slack: first, socket: fakeSocket(), signals: false, now: () => firstNight,
      tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000, runDreamer: digest });
    assert.equal(first.posts.length, 1);
    assert.equal(first.posts[0].threadTs, undefined);
    runtime.stop('first');
    runtime = null;
    const second = fakeSlack();
    runtime = await start({ workspace: dir, slack: second, socket: fakeSocket(), signals: false,
      now: () => firstNight + 24 * 60 * 60_000, tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000, runDreamer: digest });
    assert.equal(second.posts.length, 1);
    assert.equal(second.posts[0].threadTs, '9.1');
  } finally {
    process.env.PATH = prev;
    runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

for (const delivery of ['drain', 'pump']) test(`manual digests reuse the thread confirmed by daemon ${delivery}`, async () => {
  const { dir, home } = workspace();
  const { loadConfig } = require('./config.js');
  const { runInstalledDreamer } = require('./daemon.js');
  const config = JSON.parse(fs.readFileSync(configFile(dir), 'utf8'));
  config.dreamer.enabled = false;
  fs.writeFileSync(configFile(dir), JSON.stringify(config), 'utf8');
  addOwnerMessage(home);
  const cast = fakeCast(dir);
  const slack = fakeSlack();
  const post = slack.postMessage;
  slack.postMessage = (args) => post({ ...args, channel: 'D1' });
  const socket = fakeSocket();
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  const store = new Store(path.join(home, 'state.sqlite'));
  let runtime;
  try {
    runtime = await start({ workspace: dir, slack, socket, signals: false,
      turnCommand: [process.execPath, cast.stub], castEnv: cast.env,
      tickMs: 60_000, sweepMs: 60_000, drainMs: delivery === 'drain' ? 20 : 60_000,
    });
    for (let run = 1; run <= 2; run++) {
      const result = await runInstalledDreamer({ config: loadConfig(dir),
        runDreamer: async () => ({ ok: true, changed: false, alert: null,
          digest: { text: `Memory consolidation ${run}`, conflicts: ['Clarify the preference.'] } }),
      });
      assert.equal(result.digestQueued, true);
      assert.equal(result.delivered, false);
      assert.equal(result.conflictsSaved, false);
      const queued = store.pendingOutbox();
      assert.equal(queued.length, 1);
      if (run === 1) {
        assert.match(queued[0].conversation_key, /^pending:dreamer:/);
        assert.equal(store.db.prepare("SELECT value FROM settings WHERE key='dreamer_digest'").get(), undefined);
      } else {
        assert.equal(queued[0].conversation_key, 'T1:D1:9.1');
      }
      if (delivery === 'pump') {
        await socket.inject({ team: 'T1', channel: 'D1', channelType: 'im', ts: `2.${run}00000`,
          threadTs: '1.000000', user: 'UOWNER', text: 'hello', files: [], isBotOrSelf: false, mentionsBot: false });
      }
      await waitFor(() => store.db.prepare('SELECT state FROM outbox WHERE id=?').get(queued[0].id)?.state === 'delivered');
      const saved = store.db.prepare("SELECT value FROM settings WHERE key='dreamer_digest'").get();
      assert.ok(saved, 'daemon delivery must persist the Dreamer conversation');
      assert.equal(JSON.parse(saved.value).conversationKey, 'T1:D1:9.1');
      assert.equal(getState(store).reportedConflicts, undefined, 'ordinary delivery has no conflict metadata');
    }
    const digests = slack.posts.filter((row) => row.text.startsWith('Memory consolidation'));
    assert.equal(digests.length, 2);
    assert.equal(digests[0].threadTs, undefined);
    assert.equal(digests[1].channel, 'D1');
    assert.equal(digests[1].threadTs, '9.1');
  } finally {
    runtime?.stop('test');
    store.close();
    process.env.PATH = prev;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('a busy nightly slot retries after the installation lock is released', async () => {
  const { dir, home } = workspace();
  const { acquireMemoryLock } = require('./memory-write.js');
  addOwnerMessage(home);
  const release = acquireMemoryLock(dir);
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  let calls = 0;
  try {
    runtime = await start({ workspace: dir, slack: fakeSlack(), socket: fakeSocket(), signals: false,
      now: () => Date.parse('2026-10-01T06:00:00Z'), tickMs: 20, sweepMs: 60_000, drainMs: 60_000,
      runDreamer: async () => {
        calls++;
        return { ok: true, changed: false, digest: null, alert: null };
      },
    });
    assert.equal(calls, 0);
    release();
    await waitFor(() => calls === 1);
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(calls, 1);
  } finally {
    release();
    runtime?.stop('test');
    process.env.PATH = prev;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('conflicts are saved only after delivery succeeds and the following run is silent', async () => {
  const { dir, home } = workspace();
  const night = Date.parse('2026-10-01T06:00:00Z');
  const day = 24 * 60 * 60_000;
  const conflict = 'Owner preference needs clarification.';
  addOwnerMessage(home);
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const slack = fakeSlack();
  const post = slack.postMessage;
  let failDelivery = true;
  let attempts = 0;
  slack.postMessage = async (args) => {
    if (args.text.startsWith('Memory consolidation')) {
      attempts++;
      assert.deepEqual(dreamerState(home).reportedConflicts, []);
      if (failDelivery) throw new Error('channel_not_found');
    }
    return post(args);
  };
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  let calls = 0;
  try {
    for (let run = 0; run < 3; run++) {
      failDelivery = run === 0;
      runtime = await start({ workspace: dir, slack, socket: fakeSocket(), signals: false,
        now: () => night + run * day, tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000,
        runDreamer: (args) => runDreamer({ ...args, model: (input) => {
          calls++;
          assert.deepEqual(input.reportedConflicts, run === 2 ? [conflict] : []);
          return { operations: [], conflicts: [conflict, conflict] };
        } }),
      });
      assert.equal(calls, run + 1);
      assert.equal(attempts, run === 0 ? 1 : 2);
      assert.deepEqual(dreamerState(home).reportedConflicts, run === 0 ? [] : [conflict]);
      assert.equal(slack.posts.filter((item) => item.text.startsWith('Memory consolidation')).length, run === 0 ? 0 : 1);
      assert.equal(dreamerState(home).lastSuccessAt, night + run * day);
      assert.equal(dreamerState(home).cursor, 0);
      runtime.stop('night');
      runtime = null;
    }
  } finally {
    process.env.PATH = prev;
    runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('manual run and the nightly slot share runInstalledDreamer without consuming the slot', async () => {
  const { dir, home } = workspace();
  const daemonApi = require('./daemon.js');
  const { loadConfig } = require('./config.js');
  const original = daemonApi.runInstalledDreamer;
  let calls = 0;
  daemonApi.runInstalledDreamer = async () => {
    calls += 1;
    return { ok: true, changed: false, digest: null, alert: null };
  };
  let now = Date.parse('2026-10-01T12:00:00Z');
  const prev = process.env.PATH;
  process.env.PATH = `${harnessBin(dir, ['claude', 'ignite'])}${path.delimiter}${prev || ''}`;
  let runtime;
  try {
    await original({
      config: loadConfig(dir), now,
      runDreamer: async () => { throw new Error('quiet night must not consolidate'); },
    });
    assert.equal(calls, 0);
    assert.equal(dreamerState(home).lastSuccessAt, now);
    runtime = await start({ workspace: dir, slack: fakeSlack(), socket: fakeSocket(), signals: false, now: () => now,
      tickMs: 20, sweepMs: 60_000, drainMs: 60_000,
      runDreamer: async () => { throw new Error('slot runner must be the shared function'); },
    });
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(calls, 0);
    now = Date.parse('2026-10-01T06:00:00Z');
    await waitFor(() => calls === 1);
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.equal(calls, 1);
    const store = new Store(path.join(home, 'state.sqlite'));
    try { assert.equal(store.db.prepare("SELECT value FROM settings WHERE key='dreamer_slot'").get(), undefined); }
    finally { store.close(); }
  } finally {
    daemonApi.runInstalledDreamer = original;
    process.env.PATH = prev;
    runtime?.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('runInstalledDreamer releases the installation lock before consolidation and returns busy on entry contention', async () => {
  const { dir, home } = workspace();
  const daemonApi = require('./daemon.js');
  const { loadConfig } = require('./config.js');
  const { acquireMemoryLock } = require('./memory-write.js');
  addOwnerMessage(home);
  const lock = path.join(dir, '.rbtv', 'runtime', 'ignite', 'memory.lock');
  let held = false;
  const ran = await daemonApi.runInstalledDreamer({
    config: loadConfig(dir),
    runDreamer: async () => {
      held = fs.existsSync(lock);
      return { ok: true, changed: true, digest: { text: 'Memory consolidation\nUpdated memory.', conflicts: ['Still open.'] }, alert: null };
    },
  });
  assert.equal(held, false);
  assert.equal(fs.existsSync(lock), false);
  assert.equal(ran.digestQueued, true);
  assert.equal(ran.noticeQueued, false);
  assert.equal(ran.delivered, false);
  assert.equal(ran.conflictsSaved, false);
  const queued = new Store(path.join(home, 'state.sqlite'));
  try {
    assert.match(queued.pendingOutbox()[0].payload.text, /^Memory consolidation/);
    assert.equal(getState(queued).reportedConflicts, undefined);
  } finally { queued.close(); }
  const release = acquireMemoryLock(dir);
  try {
    const busy = await daemonApi.runInstalledDreamer({
      config: loadConfig(dir),
      runDreamer: async () => { throw new Error('must not run'); },
    });
    assert.equal(busy.ok, false);
    assert.equal(busy.busy, true);
    assert.equal(busy.digestQueued, false);
    assert.equal(busy.noticeQueued, false);
    assert.match(busy.error, /lock busy/);
  } finally {
    release();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

for (const ending of ['\n', '\r\n']) test(`board, remember and schedule checks succeed during a paused model call (${JSON.stringify(ending)})`, async () => {
  const { dir, home } = workspace();
  const { runInstalledDreamer } = require('./daemon.js');
  const { loadConfig } = require('./config.js');
  const now = Date.parse('2026-10-01T12:00:00Z');
  const lock = path.join(dir, '.rbtv', 'runtime', 'ignite', 'memory.lock');
  const inboxPath = '.rbtv/memory/inbox.md'; const profilePath = '.rbtv/memory/profile.md';
  const relativeBoard = '.rbtv/agents/master/_artifacts/board.md';
  const git = (...args) => {
    const result = spawnSync('git', ['-C', dir, ...args], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr); return result.stdout.trim();
  };
  const command = (...args) => {
    const result = spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), '--installation', dir, '--agent', 'master', '--json', ...args], {
      encoding: 'utf8', timeout: 15_000,
      env: { ...process.env, RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: '' },
    });
    assert.equal(result.status, 0, result.stderr || result.stdout);
    assert.doesNotMatch(result.stdout + result.stderr, /lock busy/);
    assert.equal(fs.existsSync(lock), false, 'each command releases its own write lock');
    return JSON.parse(result.stdout);
  };
  let finishModel;
  const paused = new Promise((resolve) => { finishModel = resolve; });
  let calls = 0; let running; let currentBoard;
  try {
    addOwnerMessage(home);
    fs.writeFileSync(boardPath(home), EMPTY_BOARD.replace(/\r?\n/g, ending), 'utf8');
    fs.writeFileSync(path.join(dir, inboxPath), `# Inbox${ending}`, 'utf8');
    git('init', '-q'); git('config', 'user.name', 'Memory test');
    git('config', 'user.email', 'memory-test@example.invalid'); git('config', 'commit.gpgsign', 'false');
    git('config', 'core.autocrlf', 'false');
    git('add', '--', '.rbtv/memory', '.rbtv/agents/master/memory', relativeBoard);
    git('commit', '-qm', 'Fixture');
    const head = git('rev-parse', 'HEAD');
    const store = new Store(path.join(home, 'state.sqlite'));
    try {
      store.upsertSchedule({ id: 'check-report', conversationKey: 'T1:D1:1.000000', cadence: 'every:1h',
        timezone: FIXED_TZ, nextAt: now, note: 'Review the report.' });
    } finally { store.close(); }
    running = runInstalledDreamer({ config: loadConfig(dir), now,
      runDreamer: (args) => runDreamer({ ...args, model: async (input) => {
        if (++calls === 1) {
          await paused;
          return { operations: [], conflicts: [] };
        }
        assert.equal(fs.existsSync(lock), false, 'retry also releases the snapshot lock');
        assert.equal(input.files[relativeBoard], currentBoard);
        const lines = input.files[inboxPath].split(/\r?\n/).filter((line) => line.startsWith('- '));
        assert.equal(lines.length, 1); assert.match(lines[0], /Prefers café/);
        return { operations: [
          { op: 'supersede', path: profilePath, text: `${input.files[profilePath]}${lines[0]}\n`, sources: lines, reason: 'file', explanation: 'Filed the request.' },
          { op: 'supersede', path: inboxPath, text: '# Inbox\n', sources: lines, reason: 'file', explanation: 'Filed the request.',
            removals: [{ text: lines[0], to: profilePath, replacement: lines[0] }] },
        ], conflicts: [] };
      } }),
    });
    await waitFor(() => calls === 1);
    const candidate = path.join(dir, 'board candidate.md');
    fs.writeFileSync(candidate, EMPTY_BOARD.replace('## Watch-outs', '### Report\nReview is pending.\n- Threads: none\n- Detail: none\n- Flags: none\n\n## Watch-outs').replace(/\r?\n/g, ending), 'utf8');
    assert.equal(command('board', 'write', '--file', candidate).changed, true);
    assert.equal(command('remember', 'Prefers café.').appended, true);
    assert.equal(command('schedules-due', '--now', new Date(now).toISOString()).results[0].inserted, true);
    assert.deepEqual(command('schedules-due', '--now', new Date(now).toISOString()).results, []);
    currentBoard = fs.readFileSync(boardPath(home), 'utf8');
    assert.equal(parseBoard(currentBoard).subjects[0].title, 'Report');
    assert.match(currentBoard, /check-report/);
    assert.equal(calls, 1, 'commands finish before the model is allowed to return');
    finishModel();
    const result = await running;
    assert.equal(result.ok, true, result.alert || result.error);
    assert.equal(result.changed, true); assert.equal(calls, 2);
    assert.equal(fs.readFileSync(boardPath(home), 'utf8'), currentBoard);
    assert.match(fs.readFileSync(path.join(dir, profilePath), 'utf8'), /Prefers café/);
    assert.equal(fs.readFileSync(path.join(dir, inboxPath), 'utf8'), `# Inbox${ending}`);
    assert.equal(dreamerState(home).cursor, 1);
    assert.equal(git('rev-list', '--count', `${head}..HEAD`), '1');
    assert.equal(fs.existsSync(lock), false);
  } finally {
    finishModel();
    if (running) await running;
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
  fs.writeFileSync(path.join(side, 'agent.md'), '---\nname: side\n---\n', 'utf8');
  const empty = fs.mkdtempSync(path.join(dir, 'empty-'));
  const child = spawn(process.execPath, [daemonPath, '--installation', dir], {
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
  const child = spawn(process.execPath, [daemonPath, '--installation', dir], {
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
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
  const child = spawn(process.execPath, [daemonPath, '--installation', dir], {
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

test('ignite-missing', async () => {
  const { dir } = workspace();
  const bin = harnessBin(dir, ['claude']);
  const child = spawn(process.execPath, [daemonPath, '--installation', dir], {
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
    restore() {
      process.env.PATH = prev;
      runtime.stop('test');
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
    const history = fs.readFileSync(path.join(home, 'conversations', 'T1-CAUDIO-CAUDIO.1', 'history.md'), 'utf8');
    assert.equal(history.includes('/configured/audio-keys.json'), false);
  } finally {
    process.stdout.write = write;
    box.restore();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

linuxOnly('route-after-start', 'the stopped service keeps its database open while a turn runs, and Windows cannot delete an open file', async () => {
  const { dir } = workspace();
  const box = await started(dir);
  try {
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    fs.mkdirSync(home, { recursive: true });
    fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({
      harness: 'claude', model: 'sonnet-5-5', effort: 'low',
    }));
    fs.writeFileSync(path.join(home, 'agent.md'), '---\nname: probe\n---\n', 'utf8');
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

linuxOnly('half-written-config', 'the stopped service keeps its database open while a turn runs, and Windows cannot delete an open file', async () => {
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
    box.restore();
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
  const store = new Store(path.join(home, 'state.sqlite'));
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
    const check = new Store(path.join(home, 'state.sqlite'));
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
