#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { main } = require('./cli.js');
const { Store } = require('./store.js');

const failures = [];

async function test(name, fn) {
  try {
    await fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  }
}

function workspace() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-connect-'));
}

function writeConfig(dir, extra = {}) {
  const folder = path.join(dir, '.rbtv', 'config', 'ignite');
  fs.mkdirSync(folder, { recursive: true });
  const body = {
    slack: {
      team: 'T1',
      botUserId: 'UBOT',
      ownerUserId: 'UOWNER',
      appTokenEnv: 'SLACK_APP_TOKEN',
      botTokenEnv: 'SLACK_BOT_TOKEN',
      ownerTokenEnv: 'SLACK_OWNER_TOKEN',
      stoolsWorkspace: 'ignite',
    },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' },
    routes: {},
    ...extra,
  };
  fs.writeFileSync(path.join(folder, 'config.json'), `${JSON.stringify(body, null, 2)}\n`);
  return path.join(folder, 'config.json');
}

function installAgent(dir, name = 'probe') {
  const home = path.join(dir, '.rbtv', 'agents', name);
  fs.mkdirSync(path.join(home, 'conversations'), { recursive: true });
  fs.writeFileSync(path.join(home, 'agent.md'), `---\nname: ${name}\ndescription: fixture\n---\n\n## Role\n\nFixture.\n`);
  fs.writeFileSync(path.join(home, 'launch.json'), '{"harness":"claude","model":"m","effort":"high"}\n');
  fs.writeFileSync(path.join(home, 'conversations', 'kept.md'), 'history\n');
  return home;
}

function readConfig(dir) {
  return JSON.parse(fs.readFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), 'utf8'));
}

function fakeSlack() {
  const calls = [];
  return {
    calls,
    async createChannel(name) {
      calls.push(['create', name]);
      return { id: 'CNEW', name };
    },
    async joinChannel(id) {
      calls.push(['join', id]);
      return { id };
    },
    async inviteUser(id, user) {
      calls.push(['invite', id, user]);
      return { id };
    },
    async archiveChannel(id) {
      calls.push(['archive', id]);
      return { ok: true };
    },
  };
}

async function run(argv, extra = {}) {
  const out = [];
  const err = [];
  const code = await main(argv, {
    stdout: (text) => out.push(text),
    stderr: (text) => err.push(text),
    ...extra,
  });
  return { code, out: out.join(''), err: err.join('') };
}

(async () => {
  await test('connect channel writes the route and does not print a token', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    const slack = fakeSlack();
    const secret = 'xoxb-do-not-print';
    process.env.SLACK_BOT_TOKEN = secret;
    try {
      const result = await run(['connect', 'probe', '--channel-name', 'probe', '--workspace', dir], { slack });
      assert.equal(result.code, 0, result.out + result.err);
      assert.equal(result.out.includes(secret), false);
      assert.equal(readConfig(dir).routes.CNEW, 'probe');
      assert.deepEqual(slack.calls.map((call) => call[0]), ['create', 'join', 'invite']);
      assert.equal(slack.calls[2][2], 'UOWNER');
      assert.match(result.out, /route: CNEW -> probe/);
      assert.match(result.out, /bot=joined owner=invited/);
      assert.match(result.out, /link: https:\/\/slack.com\/app_redirect\?channel=CNEW&team=T1/);
      assert.equal(fs.existsSync(path.join(home, 'agent.md')), true);
    } finally {
      delete process.env.SLACK_BOT_TOKEN;
    }
  });

  await test('connect dm sets dmAgent and does not create a channel', async () => {
    const dir = workspace();
    writeConfig(dir);
    installAgent(dir);
    const slack = fakeSlack();
    const result = await run(['connect', 'probe', '--dm', '--workspace', dir, '--json'], { slack });
    assert.equal(result.code, 0, result.out + result.err);
    const body = JSON.parse(result.out);
    assert.equal(body.dmAgent, 'probe');
    assert.equal(body.link, null);
    assert.equal(readConfig(dir).dmAgent, 'probe');
    assert.deepEqual(readConfig(dir).routes, {});
    assert.equal(slack.calls.length, 0);
  });

  await test('connect schedule records the timer and the board check', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    const schedule = path.join(dir, 'schedule.json');
    fs.writeFileSync(schedule, JSON.stringify({ cron: '0 9 * * 1', tz: 'UTC', note: 'read the board' }));
    const slack = fakeSlack();
    const result = await run([
      'connect', 'probe', '--channel-name', 'probe', '--schedule-json', schedule, '--workspace', dir,
    ], { slack });
    assert.equal(result.code, 0, result.out + result.err);
    assert.match(fs.readFileSync(path.join(home, 'board.md'), 'utf8'), /read the board/);
    const store = new Store(path.join(home, 'state.sqlite'));
    try {
      const rows = store.listSchedules();
      assert.equal(rows.length, 1);
      assert.equal(rows[0].note, 'read the board');
      assert.match(result.out, new RegExp(rows[0].id));
    } finally {
      store.close();
    }
  });

  await test('connect re-run reuses a routed channel', async () => {
    const dir = workspace();
    writeConfig(dir);
    installAgent(dir);
    const slack = fakeSlack();
    const first = await run(['connect', 'probe', '--channel-name', 'probe', '--workspace', dir], { slack });
    assert.equal(first.code, 0, first.out + first.err);
    const second = await run(['connect', 'probe', '--channel-name', 'probe', '--workspace', dir], { slack });
    assert.equal(second.code, 0, second.out + second.err);
    assert.equal(slack.calls.filter((call) => call[0] === 'create').length, 1);
    assert.equal(readConfig(dir).routes.CNEW, 'probe');
    assert.match(second.out, /route: CNEW -> probe/);
  });

  await test('connect routes a new channel at once, so a failure after it reuses the channel', async () => {
    const dir = workspace();
    writeConfig(dir);
    installAgent(dir);
    const slack = fakeSlack();
    const first = await run(['connect', 'probe', '--channel-name', 'probe', '--workspace', dir], {
      slack,
      afterChannel() {
        const error = new Error('injected');
        error.exitCode = 1;
        throw error;
      },
    }).catch((error) => error);
    assert.equal(first.message, 'injected');
    assert.deepEqual(readConfig(dir).routes, { CNEW: 'probe' });
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe', 'setup.json')), false);
    assert.equal(slack.calls.filter((call) => call[0] === 'create').length, 1);
    const second = await run(['connect', 'probe', '--channel-name', 'probe', '--workspace', dir], { slack });
    assert.equal(second.code, 0, second.out + second.err);
    assert.equal(slack.calls.filter((call) => call[0] === 'create').length, 1);
    assert.equal(readConfig(dir).routes.CNEW, 'probe');
  });

  await test('disconnect removes the route, cancels timers, keeps the folder', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    const schedule = path.join(dir, 'schedule.json');
    fs.writeFileSync(schedule, JSON.stringify({ cron: '0 9 * * 1', tz: 'UTC', note: 'read the board' }));
    const slack = fakeSlack();
    const created = await run([
      'connect', 'probe', '--channel-name', 'probe', '--schedule-json', schedule, '--workspace', dir,
    ], { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const removed = await run(['disconnect', 'probe', '--archive-channel', '--workspace', dir], { slack });
    assert.equal(removed.code, 0, removed.out + removed.err);
    assert.deepEqual(readConfig(dir).routes, {});
    assert.equal(readConfig(dir).dmAgent, undefined);
    assert.equal(slack.calls.some((call) => call[0] === 'archive' && call[1] === 'CNEW'), true);
    assert.equal(fs.existsSync(path.join(home, 'agent.md')), true);
    assert.equal(fs.readFileSync(path.join(home, 'conversations', 'kept.md'), 'utf8'), 'history\n');
    assert.match(removed.out, /home: kept/);
    const store = new Store(path.join(home, 'state.sqlite'));
    try {
      assert.equal(store.listSchedules().length, 0);
    } finally {
      store.close();
    }
  });

  await test('disconnect without archive does not archive and clears dmAgent', async () => {
    const dir = workspace();
    writeConfig(dir);
    installAgent(dir);
    const slack = fakeSlack();
    const created = await run(['connect', 'probe', '--dm', '--workspace', dir], { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const removed = await run(['disconnect', 'probe', '--workspace', dir], { slack });
    assert.equal(removed.code, 0, removed.out + removed.err);
    assert.equal(readConfig(dir).dmAgent, undefined);
    assert.equal(slack.calls.some((call) => call[0] === 'archive'), false);
    assert.match(removed.out, /archived: no/);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe', 'agent.md')), true);
  });

  await test('connect refuses a missing config and does not create it', async () => {
    const dir = workspace();
    installAgent(dir);
    const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
    const result = await run(['connect', 'probe', '--dm', '--workspace', dir]).catch((error) => error);
    assert.match(result.message, /config[/\\]ignite[/\\]config\.json/);
    assert.match(result.message, /core\/ignite\/capabilities\/runbook\.md/);
    assert.equal(fs.existsSync(file), false);
  });

  await test('connect refuses an agent that is not installed', async () => {
    const dir = workspace();
    writeConfig(dir);
    const result = await run(['connect', 'probe', '--dm', '--workspace', dir]).catch((error) => error);
    assert.match(result.message, /not installed/);
    assert.match(result.message, /launch\.json/);
    assert.match(result.message, /ignite-agent install/);
    assert.equal(readConfig(dir).dmAgent, undefined);
  });

  await test('connect refuses a bad channel name', async () => {
    const dir = workspace();
    writeConfig(dir);
    installAgent(dir);
    const slack = fakeSlack();
    const before = fs.readFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), 'utf8');
    const result = await run(['connect', 'probe', '--channel-name', 'Bad Name', '--workspace', dir], { slack }).catch((error) => error);
    assert.match(result.message, /channel name/);
    assert.equal(slack.calls.length, 0);
    assert.equal(fs.readFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), 'utf8'), before);
  });

  await test('create is not a command', async () => {
    const result = await run(['create', '--remove']).catch((error) => error);
    assert.match(result.message, /unknown command: create/);
  });

  if (failures.length) {
    console.log(`FAILED ${failures.length}`);
    process.exit(1);
  }
  console.log('ok');
})().catch((error) => {
  console.log(`FAIL runner: ${error.stack || error.message}`);
  process.exit(1);
});
