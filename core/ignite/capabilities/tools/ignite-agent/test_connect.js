#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { main } = require('./cli.js');
const { Store } = require('./store.js');
const { EMPTY_BOARD, boardPath, parseBoard } = require('./board.js');
const { acquireMemoryLock } = require('./memory-write.js');

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
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
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
    ], { slack, now: () => Date.parse('2026-10-01T12:00:00Z') });
    assert.equal(result.code, 0, result.out + result.err);
    const board = fs.readFileSync(boardPath(home), 'utf8');
    assert.equal(fs.existsSync(path.join(home, 'board.md')), false);
    const store = new Store(path.join(home, 'state.sqlite'));
    try {
      const rows = store.listSchedules();
      assert.equal(rows.length, 1);
      assert.equal(rows[0].note, 'read the board');
      assert.deepEqual(parseBoard(board).timers, ['| Fires | Timer | For | Subject |', '|---|---|---|---|',
        `| 2026-10-05 09:00 UTC | ${rows[0].id} | read the board | none |`]);
      assert.match(result.out, new RegExp(rows[0].id));
    } finally {
      store.close();
    }
  });

  await test('connect ignores a legacy board and rerenders a reused timer without replacing subjects', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    const text = EMPTY_BOARD.replace('## What matters now\n', '## What matters now\n\n### Café\nReview it.\n- Threads: none\n- Detail: none\n- Flags: none\n');
    fs.writeFileSync(boardPath(home), text.replace(/\n/g, '\r\n'), 'utf8');
    fs.writeFileSync(path.join(home, 'board.md'), 'invalid legacy board', 'utf8');
    const schedule = path.join(dir, 'schedule.json');
    fs.writeFileSync(schedule, JSON.stringify({ every: '1h', tz: 'fixed', note: 'First check' }), 'utf8');
    const args = ['connect', 'probe', '--dm', '--schedule-json', schedule, '--workspace', dir, '--json'];
    const deps = { slack: fakeSlack(), now: () => Date.parse('2026-10-01T12:00:00Z') };
    // Numeric intervals in connection files use the same elapsed-time cadence as the CLI.
    const first = await run(args, deps);
    const id = JSON.parse(first.out).scheduleId;
    fs.writeFileSync(path.join(home, 'board.md'), 'obsolete', 'utf8');
    fs.writeFileSync(schedule, JSON.stringify({ cron: '0 9 * * *', tz: 'Europe/Lisbon', note: 'Second check' }), 'utf8');
    const second = await run(args, deps);
    assert.equal(JSON.parse(second.out).scheduleId, id);
    const board = parseBoard(fs.readFileSync(boardPath(home), 'utf8'));
    assert.equal(board.subjects[0].title, 'Café');
    assert.equal(board.timers.length, 3);
    assert.match(board.timers[2], /2026-10-02 09:00 Europe\/Lisbon.*Second check \| none/);
    assert.equal(fs.readFileSync(path.join(home, 'board.md'), 'utf8'), 'obsolete');
  });

  await test('connect without a schedule never recreates a deleted canonical board', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    fs.unlinkSync(boardPath(home));
    fs.writeFileSync(path.join(home, 'board.md'), 'invalid legacy board', 'utf8');
    const result = await run(['connect', 'probe', '--dm', '--workspace', dir], { slack: fakeSlack() });
    assert.equal(result.code, 0);
    assert.equal(fs.existsSync(boardPath(home)), false);
  });

  for (const state of ['deleted', 'invalid']) {
    for (const existing of [false, true]) await test(`connection timer refuses a ${state} board with ${existing ? 'existing' : 'absent'} SQLite unchanged`, async () => {
      const dir = workspace();
      writeConfig(dir);
      const home = installAgent(dir);
      const file = boardPath(home);
      const db = path.join(home, 'state.sqlite');
      try {
        if (existing) {
          const store = new Store(db);
          try {
            store.upsertConversation({ key: 'T1:UOWNER:board', agent: 'probe', workspace: 'T1', channel: 'UOWNER', rootTs: 'board' });
            store.upsertSchedule({ id: 'existing', conversationKey: 'T1:UOWNER:board', cadence: 'every:1h', timezone: 'fixed', nextAt: 1000, note: 'Original' });
          } finally { store.close(); }
        }
        const before = existing ? fs.readFileSync(db) : null;
        fs.writeFileSync(path.join(home, 'board.md'), EMPTY_BOARD, 'utf8');
        if (state === 'deleted') fs.unlinkSync(file);
        else fs.writeFileSync(file, 'invalid board café\r\n', 'utf8');
        const schedule = path.join(dir, 'schedule.json');
        fs.writeFileSync(schedule, JSON.stringify({ every: '2h', tz: 'fixed', note: 'Changed' }), 'utf8');
        await assert.rejects(() => run(['connect', 'probe', '--dm', '--schedule-json', schedule, '--workspace', dir], { slack: fakeSlack() }),
          (error) => error.message.startsWith(`board refused: ${file}: `)
            && (state !== 'deleted' || error.message === `board refused: ${file}: board is missing`));
        if (existing) assert.deepEqual(fs.readFileSync(db), before);
        assert.deepEqual(fs.readdirSync(home).filter((name) => name.startsWith('state.sqlite')), existing ? ['state.sqlite'] : []);
        if (state === 'deleted') assert.equal(fs.existsSync(file), false);
        else assert.equal(fs.readFileSync(file, 'utf8'), 'invalid board café\r\n');
      } finally { fs.rmSync(dir, { recursive: true, force: true }); }
    });
  }

  for (const state of ['invalid', 'deleted']) await test(`connect and disconnect refuse a ${state} board before changing schedules`, async () => {
    const dir = workspace();
    writeConfig(dir, { dmAgent: 'probe' });
    const home = installAgent(dir);
    const store = new Store(path.join(home, 'state.sqlite'));
    try {
      store.upsertConversation({ key: 'k', agent: 'probe', workspace: 'T1', channel: 'C1' });
      store.upsertSchedule({ id: 'existing', conversationKey: 'k', cadence: 'every:1h', timezone: 'fixed', nextAt: 1000 });
      const before = store.listSchedules();
      if (state === 'deleted') fs.unlinkSync(boardPath(home));
      else fs.writeFileSync(boardPath(home), 'invalid board', 'utf8');
      const schedule = path.join(dir, 'schedule.json');
      fs.writeFileSync(schedule, JSON.stringify({ every: '1h', tz: 'fixed', note: 'Check' }), 'utf8');
      for (const args of [['connect', 'probe', '--dm', '--schedule-json', schedule], ['disconnect', 'probe']]) {
        await assert.rejects(() => run([...args, '--workspace', dir], { slack: fakeSlack() }), /board refused/);
        assert.deepEqual(store.listSchedules(), before);
      }
    } finally { store.close(); fs.rmSync(dir, { recursive: true, force: true }); }
  });

  for (const json of [false, true]) {
    for (const action of ['add', 'change', 'cancel']) await test(`connection timer ${action} reports committed with refresh pending in ${json ? 'JSON' : 'text'} mode`, async () => {
      const dir = workspace();
      writeConfig(dir);
      const home = installAgent(dir);
      const schedule = path.join(dir, 'schedule.json');
      fs.writeFileSync(schedule, JSON.stringify({ every: '1h', tz: 'fixed', note: 'Original' }), 'utf8');
      const args = ['connect', 'probe', '--dm', '--schedule-json', schedule, '--workspace', dir];
      const deps = { slack: fakeSlack() };
      const store = new Store(path.join(home, 'state.sqlite'));
      const method = action === 'cancel' ? 'deleteSchedule' : 'upsertSchedule';
      const original = Store.prototype[method];
      let release;
      try {
        let existing;
        if (action !== 'add') {
          const first = await run([...args, '--json'], deps);
          existing = JSON.parse(first.out).scheduleId;
        }
        const before = fs.readFileSync(boardPath(home), 'utf8');
        fs.writeFileSync(schedule, JSON.stringify({ every: '2h', tz: 'fixed', note: 'Changed' }), 'utf8');
        // Acquire only after the preflight and the real SQLite mutation.
        Store.prototype[method] = function (...values) {
          const result = original.apply(this, values);
          if (json) release = acquireMemoryLock(dir);
          else fs.writeFileSync(boardPath(home), 'changed to invalid after preflight', 'utf8');
          return result;
        };
        const result = await run([...(action === 'cancel' ? ['disconnect', 'probe', '--workspace', dir] : args), ...(json ? ['--json'] : [])], deps);
        assert.equal(result.code, 0);
        assert.equal(result.err, '');
        const rows = store.listSchedules();
        assert.equal(rows.length, action === 'cancel' ? 0 : 1);
        const id = action === 'cancel' ? existing : rows[0].id;
        if (action !== 'add') assert.equal(id, existing);
        if (action !== 'cancel') assert.equal(rows[0].note, 'Changed');
        const warning = `${id} committed; board refresh pending`;
        if (json) {
          const body = JSON.parse(result.out);
          assert.equal(body.warning, warning);
          assert.equal(body.error, undefined);
          if (action === 'cancel') assert.deepEqual(body.timers, [id]);
          else assert.equal(body.scheduleId, id);
          assert.equal(fs.readFileSync(boardPath(home), 'utf8'), before);
        } else assert.ok(result.out.includes(warning));
        if (release) { release(); release = null; }
        Store.prototype[method] = original;
        if (!json) fs.writeFileSync(boardPath(home), before, 'utf8');
        const candidate = path.join(dir, 'candidate.md');
        fs.writeFileSync(candidate, before, 'utf8');
        const next = await run(['board', 'write', '--file', candidate], { env: { IGNITE_AGENT_HOME: home } });
        assert.equal(next.code, 0, next.err);
        const timers = parseBoard(fs.readFileSync(boardPath(home), 'utf8')).timers;
        assert.equal(timers.length, action === 'cancel' ? 2 : 3);
        if (action !== 'cancel') assert.ok(timers[2].includes(`| ${id} | Changed |`));
      } finally {
        Store.prototype[method] = original;
        if (release) release();
        store.close();
        fs.rmSync(dir, { recursive: true, force: true });
      }
    });
  }

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
      assert.equal(parseBoard(fs.readFileSync(boardPath(home), 'utf8')).timers.length, 2);
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
