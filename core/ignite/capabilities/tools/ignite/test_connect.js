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
  fs.mkdirSync(path.join(home, 'runtime', 'ignite', 'conversations'), { recursive: true });
  fs.writeFileSync(path.join(home, 'prompt.md'), `---\nname: ${name}\n---\n\n## Role\n\nFixture.\n`);
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({
    name, description: 'fixture', harness: 'claude', model: 'm', effort: 'high',
    files: ['fixture/a#one', 'fixture/a#two', 'fixture/a#web'], packs: ['research-kit'],
  }) + '\n');
  fs.writeFileSync(path.join(home, 'runtime', 'ignite', 'conversations', 'kept.md'), 'history\n');
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  return home;
}

const IGNITE_FILES = ['core/ignite#a', 'core/ignite#b', 'core/ignite#c', 'core/ignite#d', 'core/ignite#e', 'core/ignite#f', 'core/ignite#g', 'core/ignite#h'];

// Mirrors the installer's JSON for a pack change: the files after it, and the files it added (add)
// or removed (remove). The count before the change is not in that JSON; ignite derives it.
function fakeInstaller(calls = []) {
  return (args) => {
    calls.push(args);
    const home = args[2];
    const dryRun = args.includes('--dry-run');
    const state = JSON.parse(fs.readFileSync(path.join(home, 'agent.json'), 'utf8'));
    const packs = new Set(state.packs);
    const files = new Set(state.files);
    const adding = args[1] === 'add';
    const extra = args.filter((arg, index) => index > 2 && !arg.startsWith('--') && arg.includes('#'));
    const changed = IGNITE_FILES.filter((file) => files.has(file) !== adding);
    if (adding) {
      packs.add('ignite');
      for (const file of IGNITE_FILES) files.add(file);
      for (const file of extra) if (!files.has(file)) changed.push(file);
      for (const file of extra) files.add(file);
    } else {
      packs.delete('ignite');
      for (const file of IGNITE_FILES) files.delete(file);
      for (const file of extra) if (files.delete(file)) changed.push(file);
    }
    const next = { ...state, packs: [...packs].sort(), files: [...files].sort() };
    if (!dryRun) fs.writeFileSync(path.join(home, 'agent.json'), `${JSON.stringify(next)}\n`);
    const change = adding ? { added: changed } : { files_removed: changed };
    return { status: 0, stdout: JSON.stringify({ files: next.files, packs: next.packs, ...change }) };
  };
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
    ...(extra.realInstaller ? {} : { install: fakeInstaller() }),
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
      const result = await run(['connect', 'probe', '--channel-name', 'probe', '--installation', dir], { slack });
      assert.equal(result.code, 0, result.out + result.err);
      assert.equal(result.out.includes(secret), false);
      assert.equal(readConfig(dir).routes.CNEW, 'probe');
      assert.deepEqual(slack.calls.map((call) => call[0]), ['create', 'join', 'invite']);
      assert.equal(slack.calls[2][2], 'UOWNER');
      assert.match(result.out, /route: CNEW -> probe/);
      assert.match(result.out, /bot=joined owner=invited/);
      assert.match(result.out, /link: https:\/\/slack.com\/app_redirect\?channel=CNEW&team=T1/);
      assert.equal(fs.existsSync(path.join(home, 'prompt.md')), true);
    } finally {
      delete process.env.SLACK_BOT_TOKEN;
    }
  });

  await test('connect dm sets dmAgent and does not create a channel', async () => {
    const dir = workspace();
    writeConfig(dir);
    installAgent(dir);
    const slack = fakeSlack();
    const result = await run(['connect', 'probe', '--dm', '--installation', dir, '--json'], { slack });
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
      'connect', 'probe', '--channel-name', 'probe', '--schedule-json', schedule, '--installation', dir,
    ], { slack, now: () => Date.parse('2026-10-01T12:00:00Z') });
    assert.equal(result.code, 0, result.out + result.err);
    const board = fs.readFileSync(boardPath(home), 'utf8');
    assert.equal(fs.existsSync(path.join(home, 'board.md')), false);
    const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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

  await test('connect schedule JSON gives the first timer its check tool and seeds the board conversation for the next', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    const schedule = path.join(dir, 'schedule.json');
    const now = () => Date.parse('2026-10-01T12:00:00Z');
    const args = ['connect', 'probe', '--channel-name', 'probe', '--schedule-json', schedule, '--installation', dir];
    fs.writeFileSync(schedule, JSON.stringify({ every: '5m', tz: 'fixed', note: 'new mail', check: 'tools\\mail-check.js' }));
    const plan = await run([...args, '--dry-run'], { slack: fakeSlack(), now });
    assert.match(plan.out, /schedule: every:5m fixed check=tools\/mail-check\.js\n/);
    assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
    const result = await run([...args, '--json'], { slack: fakeSlack(), now });
    assert.equal(result.code, 0, result.out + result.err);
    const { scheduleId } = JSON.parse(result.out);
    const env = { RBTV_AGENT_HOME: home };
    const second = await run(['schedule', 'add', '--every', '5m', '--note', 'transcripts', '--check', 'meeting-check',
      '--conversation', 'T1:CNEW:board', '--json'], { env, now });
    assert.equal(JSON.parse(second.out).schedule.check_tool, 'meeting-check');
    const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    try {
      const first = store.getSchedule(scheduleId);
      assert.deepEqual([first.check_tool, first.note, first.conversation_key], ['tools/mail-check.js', 'new mail', 'T1:CNEW:board']);
      assert.equal(store.listSchedules().length, 2);
    } finally {
      store.close();
    }
  });

  await test('connect re-run without a check keeps the bound timer\'s check; a timer bound without one has none', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    const schedule = path.join(dir, 'schedule.json');
    const args = ['connect', 'probe', '--dm', '--schedule-json', schedule, '--installation', dir, '--json'];
    const bound = () => {
      const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
      try { return store.listSchedules(); } finally { store.close(); }
    };
    fs.writeFileSync(schedule, JSON.stringify({ every: '1h', tz: 'fixed', note: 'plain' }));
    await run(args, { slack: fakeSlack() });
    assert.deepEqual(bound().map((row) => [row.note, row.check_tool]), [['plain', null]]);
    fs.writeFileSync(schedule, JSON.stringify({ every: '1h', tz: 'fixed', note: 'checked', check: './check.py' }));
    await run(args, { slack: fakeSlack() });
    assert.deepEqual(bound().map((row) => [row.note, row.check_tool]), [['checked', './check.py']]);
    fs.writeFileSync(schedule, JSON.stringify({ every: '2h', tz: 'fixed', note: 'cadence only' }));
    await run(args, { slack: fakeSlack() });
    assert.deepEqual(bound().map((row) => [row.note, row.cadence, row.check_tool]), [['cadence only', 'every:2h', './check.py']]);
  });

  await test('connect refuses an invalid schedule check before it writes or calls Slack', async () => {
    for (const bad of ['/usr/bin/x', 'C:\\x.exe', '../x', 'tools/', '', 5]) {
      const dir = workspace();
      const configFile = writeConfig(dir);
      const home = installAgent(dir);
      const schedule = path.join(dir, 'schedule.json');
      fs.writeFileSync(schedule, JSON.stringify({ every: '5m', tz: 'fixed', note: 'mail', check: bad }));
      const slack = fakeSlack();
      const calls = [];
      const config = fs.readFileSync(configFile, 'utf8');
      const agent = fs.readFileSync(path.join(home, 'agent.json'), 'utf8');
      await assert.rejects(() => run(['connect', 'probe', '--channel-name', 'probe', '--schedule-json', schedule, '--installation', dir],
        { slack, install: fakeInstaller(calls) }), /--schedule-json check must/, JSON.stringify(bad));
      assert.equal(slack.calls.length, 0);
      assert.equal(calls.length, 0);
      assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
      assert.equal(fs.readFileSync(configFile, 'utf8'), config);
      assert.equal(fs.readFileSync(path.join(home, 'agent.json'), 'utf8'), agent);
      fs.rmSync(dir, { recursive: true, force: true });
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
    const args = ['connect', 'probe', '--dm', '--schedule-json', schedule, '--installation', dir, '--json'];
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

  await test('connect creates a missing canonical board without a schedule', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    fs.unlinkSync(boardPath(home));
    fs.writeFileSync(path.join(home, 'board.md'), 'invalid legacy board', 'utf8');
    const result = await run(['connect', 'probe', '--dm', '--installation', dir], { slack: fakeSlack() });
    assert.equal(result.code, 0);
    assert.equal(fs.existsSync(boardPath(home)), true);
  });

  for (const state of ['deleted', 'invalid']) {
    for (const existing of [false, true]) await test(`connection timer ${state === 'deleted' ? 'creates' : 'refuses'} a ${state} board with ${existing ? 'existing' : 'absent'} SQLite`, async () => {
      const dir = workspace();
      writeConfig(dir);
      const home = installAgent(dir);
      const file = boardPath(home);
      const db = path.join(home, 'runtime', 'ignite', 'state.sqlite');
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
        if (state === 'deleted') {
          const result = await run(['connect', 'probe', '--dm', '--schedule-json', schedule, '--installation', dir], { slack: fakeSlack() });
          assert.equal(result.code, 0, result.out + result.err);
          assert.equal(fs.existsSync(file), true);
        } else {
          await assert.rejects(() => run(['connect', 'probe', '--dm', '--schedule-json', schedule, '--installation', dir], { slack: fakeSlack() }),
            (error) => error.message.includes(`board refused: ${file}: `));
          if (existing) assert.deepEqual(fs.readFileSync(db), before);
          assert.equal(fs.readFileSync(file, 'utf8'), 'invalid board café\r\n');
        }
      } finally { fs.rmSync(dir, { recursive: true, force: true }); }
    });
  }

  for (const state of ['invalid', 'deleted']) await test(`disconnect refuses a ${state} board before changing schedules`, async () => {
    const dir = workspace();
    writeConfig(dir, { dmAgent: 'probe' });
    const home = installAgent(dir);
    const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    try {
      store.upsertConversation({ key: 'k', agent: 'probe', workspace: 'T1', channel: 'C1' });
      store.upsertSchedule({ id: 'existing', conversationKey: 'k', cadence: 'every:1h', timezone: 'fixed', nextAt: 1000 });
      const before = store.listSchedules();
      if (state === 'deleted') fs.unlinkSync(boardPath(home));
      else fs.writeFileSync(boardPath(home), 'invalid board', 'utf8');
      const schedule = path.join(dir, 'schedule.json');
      fs.writeFileSync(schedule, JSON.stringify({ every: '1h', tz: 'fixed', note: 'Check' }), 'utf8');
      await assert.rejects(() => run(['disconnect', 'probe', '--installation', dir], { slack: fakeSlack() }), /board refused/);
      assert.deepEqual(store.listSchedules(), before);
    } finally { store.close(); fs.rmSync(dir, { recursive: true, force: true }); }
  });

  for (const json of [false, true]) {
    for (const action of ['add', 'change', 'cancel']) await test(`connection timer ${action} reports committed with refresh pending in ${json ? 'JSON' : 'text'} mode`, async () => {
      const dir = workspace();
      writeConfig(dir);
      const home = installAgent(dir);
      const schedule = path.join(dir, 'schedule.json');
      fs.writeFileSync(schedule, JSON.stringify({ every: '1h', tz: 'fixed', note: 'Original' }), 'utf8');
      const args = ['connect', 'probe', '--dm', '--schedule-json', schedule, '--installation', dir];
      const deps = { slack: fakeSlack() };
      const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
        const result = await run([...(action === 'cancel' ? ['disconnect', 'probe', '--installation', dir] : args), ...(json ? ['--json'] : [])], deps);
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
        const next = await run(['board', 'write', '--file', candidate], { env: { RBTV_AGENT_HOME: home } });
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
    const first = await run(['connect', 'probe', '--channel-name', 'probe', '--installation', dir], { slack });
    assert.equal(first.code, 0, first.out + first.err);
    const second = await run(['connect', 'probe', '--channel-name', 'probe', '--installation', dir], { slack });
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
    const first = await run(['connect', 'probe', '--channel-name', 'probe', '--installation', dir], {
      slack,
      afterChannel() {
        const error = new Error('injected');
        error.exitCode = 1;
        throw error;
      },
    }).catch((error) => error);
    assert.match(first.message, /Slack failed: injected/);
    assert.deepEqual(readConfig(dir).routes, { CNEW: 'probe' });
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe', 'setup.json')), false);
    assert.equal(slack.calls.filter((call) => call[0] === 'create').length, 1);
    const second = await run(['connect', 'probe', '--channel-name', 'probe', '--installation', dir], { slack });
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
      'connect', 'probe', '--channel-name', 'probe', '--schedule-json', schedule, '--installation', dir,
    ], { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const removed = await run(['disconnect', 'probe', '--archive-channel', '--installation', dir], { slack });
    assert.equal(removed.code, 0, removed.out + removed.err);
    assert.deepEqual(readConfig(dir).routes, {});
    assert.equal(readConfig(dir).dmAgent, undefined);
    assert.equal(slack.calls.some((call) => call[0] === 'archive' && call[1] === 'CNEW'), true);
    assert.equal(fs.existsSync(path.join(home, 'prompt.md')), true);
    assert.equal(fs.readFileSync(path.join(home, 'runtime', 'ignite', 'conversations', 'kept.md'), 'utf8'), 'history\n');
    assert.match(removed.out, /home: kept/);
    const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
    const created = await run(['connect', 'probe', '--dm', '--installation', dir], { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const removed = await run(['disconnect', 'probe', '--installation', dir], { slack });
    assert.equal(removed.code, 0, removed.out + removed.err);
    assert.equal(readConfig(dir).dmAgent, undefined);
    assert.equal(slack.calls.some((call) => call[0] === 'archive'), false);
    assert.match(removed.out, /archived: no/);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe', 'prompt.md')), true);
  });

  await test('connect dry-run calls the real installer with the ignite pack and writes nothing', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    const statePath = path.join(home, 'agent.json');
    const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    fs.writeFileSync(statePath, `${JSON.stringify({ ...state, files: [], packs: [] })}\n`);
    const bin = path.join(dir, 'bin');
    fs.mkdirSync(bin);
    // The shape `cast models list --supported --json` prints, for the one model of this agent.
    const castModels = '{"models":[{"harness":"claude","model":"m","mode":"cli","rungs":["high"],"effort_numbers":{"high":1},"selected":true}]}';
    const cast = path.join(bin, process.platform === 'win32' ? 'cast.cmd' : 'cast');
    fs.writeFileSync(cast, process.platform === 'win32'
      ? `@echo ${castModels}\r\n`
      : `#!/bin/sh\nprintf '%s\\n' '${castModels}'\n`);
    if (process.platform !== 'win32') fs.chmodSync(cast, 0o755);
    const before = fs.readFileSync(statePath, 'utf8');
    const oldPath = process.env.PATH;
    process.env.PATH = `${bin}${path.delimiter}${oldPath}`;
    try {
      const result = await run(['connect', 'probe', '--dm', '--installation', dir, '--dry-run'], { realInstaller: true });
      assert.equal(result.code, 0, result.out + result.err);
      const planned = new Set([
        ...JSON.parse(fs.readFileSync(path.join(__dirname, '../../../packs/ignite.json'), 'utf8')).files,
        ...JSON.parse(fs.readFileSync(path.join(__dirname, '../../../../rbtv/packs/foundations.json'), 'utf8')).files,
      ]);
      assert.match(result.out, /pack: ignite/);
      assert.match(result.out, new RegExp(`files: 0 -> ${planned.size}`));
      assert.equal(fs.readFileSync(statePath, 'utf8'), before);
      assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
    } finally {
      process.env.PATH = oldPath;
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  await test('connect dry-run passes --dry-run to the installer and makes no Slack request', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    const calls = [];
    const slack = fakeSlack();
    const before = fs.readFileSync(path.join(home, 'agent.json'), 'utf8');
    const result = await run(['connect', 'probe', '--channel-name', 'probe', '--installation', dir, '--dry-run'], {
      install: fakeInstaller(calls), slack,
    });
    assert.equal(result.code, 0, result.out + result.err);
    assert.deepEqual(calls[0], ['agent', 'add', home, '--pack', 'ignite', '--json', '--dry-run']);
    assert.equal(slack.calls.length, 0);
    assert.equal(fs.readFileSync(path.join(home, 'agent.json'), 'utf8'), before);
  });

  for (const command of ['connect', 'disconnect']) await test(`${command} refuses an agent folder outside the installation`, async () => {
    const dir = workspace();
    writeConfig(dir);
    const outside = path.join(dir, 'plans', 'agent');
    fs.mkdirSync(outside, { recursive: true });
    fs.writeFileSync(path.join(outside, 'prompt.md'), '---\nname: agent\n---\n');
    fs.writeFileSync(path.join(outside, 'agent.json'), '{}\n');
    const args = command === 'connect'
      ? [command, outside, '--dm', '--installation', dir]
      : [command, outside, '--installation', dir];
    const error = await run(args).catch((caught) => caught);
    assert.match(error.message, /not under/);
    assert.match(error.message, /Nothing changed/);
  });

  await test('connect refuses a missing config and does not create it', async () => {
    const dir = workspace();
    installAgent(dir);
    const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
    const result = await run(['connect', 'probe', '--dm', '--installation', dir]).catch((error) => error);
    assert.match(result.message, /config[/\\]ignite[/\\]config\.json/);
    assert.match(result.message, /core\/ignite\/capabilities\/tools\/ignite\/documentation\/runbook\.md/);
    assert.match(result.message, /Nothing changed\.$/);
    assert.equal(fs.existsSync(file), false);
  });

  await test('connect refuses an agent that is not installed', async () => {
    const dir = workspace();
    writeConfig(dir);
    const result = await run(['connect', 'probe', '--dm', '--installation', dir]).catch((error) => error);
    assert.match(result.message, /not installed/);
    assert.match(result.message, /no folder/);
    assert.match(result.message, /Add it with: rbtv agent add probe --harness HARNESS --model MODEL --effort EFFORT\n/);
    assert.equal(readConfig(dir).dmAgent, undefined);
  });

  await test('connect refuses an agent folder that still holds the old prompt name, with the rename command', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir);
    fs.renameSync(path.join(home, 'prompt.md'), path.join(home, 'agent.md'));
    const result = await run(['connect', 'probe', '--dm', '--installation', dir]).catch((error) => error);
    assert.match(result.message, /cannot be launched: .*prompt\.md is missing\. This folder still has agent\.md/);
    assert.match(result.message, /git mv agent\.md prompt\.md/);
    assert.equal(readConfig(dir).dmAgent, undefined);
  });

  await test('connect refuses a bad channel name', async () => {
    const dir = workspace();
    writeConfig(dir);
    installAgent(dir);
    const slack = fakeSlack();
    const before = fs.readFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), 'utf8');
    const result = await run(['connect', 'probe', '--channel-name', 'Bad Name', '--installation', dir], { slack }).catch((error) => error);
    assert.match(result.message, /channel name/);
    assert.equal(slack.calls.length, 0);
    assert.equal(fs.readFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), 'utf8'), before);
  });

  await test('connect and disconnect find the installation from the current folder', async () => {
    const dir = fs.realpathSync(workspace());
    writeConfig(dir);
    installAgent(dir);
    fs.mkdirSync(path.join(dir, 'plans'));
    const here = process.cwd();
    process.chdir(path.join(dir, 'plans'));
    try {
      const connected = await run(['connect', 'probe', '--dm'], { slack: fakeSlack() });
      assert.equal(connected.code, 0, connected.out + connected.err);
      assert.equal(readConfig(dir).dmAgent, 'probe');
      const removed = await run(['disconnect', 'probe'], { slack: fakeSlack() });
      assert.equal(removed.code, 0, removed.out + removed.err);
      assert.equal(readConfig(dir).dmAgent, undefined);
    } finally {
      process.chdir(here);
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  await test('connect refuses with no installation above the current folder', async () => {
    const outside = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-no-install-')));
    const here = process.cwd();
    process.chdir(outside);
    try {
      const result = await run(['connect', 'probe', '--dm']).catch((error) => error);
      assert.match(result.message, /no installation found/);
      assert.match(result.message, /--installation PATH/);
      assert.match(result.message, /Nothing changed\.$/);
    } finally {
      process.chdir(here);
      fs.rmSync(outside, { recursive: true, force: true });
    }
  });

  await test('connect and disconnect help print only their own page', async () => {
    for (const command of ['connect', 'disconnect']) {
      const out = [];
      const code = await main([command, '-h'], { stdout: (text) => out.push(text) });
      const text = out.join('');
      const other = command === 'connect' ? 'disconnect' : 'connect';
      assert.equal(code, 0);
      assert.equal(text.split('\n')[0], `ignite — ${command} help`);
      assert.doesNotMatch(text, new RegExp(`ignite — ${other} help`));
    }
  });

  await test('connect and disconnect count every file the agent has, once, and say already off when the pack was off', async () => {
    const dir = workspace();
    writeConfig(dir);
    installAgent(dir);
    const install = fakeInstaller();
    const connected = await run(['connect', 'probe', '--dm', '--installation', dir], { install, slack: fakeSlack() });
    assert.equal(connected.code, 0, connected.out + connected.err);
    assert.match(connected.out, /files: 3 -> 11\n/);
    const again = await run(['connect', 'probe', '--dm', '--installation', dir], { install, slack: fakeSlack() });
    assert.match(again.out, /files: 11\n/);
    const removed = await run(['disconnect', 'probe', '--installation', dir], { install, slack: fakeSlack() });
    assert.match(removed.out, /pack: ignite off\n/);
    assert.match(removed.out, /files: 11 -> 3\n/);
    const off = await run(['disconnect', 'probe', '--installation', dir], { install, slack: fakeSlack() });
    assert.match(off.out, /pack: ignite already off\n/);
    assert.match(off.out, /files: 3\n/);
    fs.rmSync(dir, { recursive: true, force: true });
  });

  await test('connecting a non-Albert agent keeps its pack selection, rule set, schedule and channel binding, and adds no Albert rule', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir, 'probe');
    const calls = [];
    const connected = await run(['connect', 'probe', '--channel-name', 'probe', '--installation', dir], { install: fakeInstaller(calls), slack: fakeSlack() });
    assert.equal(connected.code, 0, connected.err);
    assert.deepEqual(calls[0].slice(0, 5), ['agent', 'add', home, '--pack', 'ignite']);
    assert.equal(calls[0].includes('core/ignite#albert-memory-operations'), false);
    assert.match(connected.out, /pack: ignite/);
    assert.match(connected.out, /channel: CNEW probe/);
    assert.match(connected.out, /route: CNEW -> probe/);
    assert.equal(connected.out.includes('albert schedule:'), false);
    const record = JSON.parse(fs.readFileSync(path.join(home, 'agent.json'), 'utf8'));
    assert.equal(record.files.includes('core/ignite#albert-memory-operations'), false);
    assert.equal(record.packs.includes('ignite'), true);
    fs.rmSync(dir, { recursive: true, force: true });
  });

  await test('connecting Albert adds the normal pack plus the rule only', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir, 'albert');
    fs.mkdirSync(path.join(dir, '.rbtv', 'runtime', 'ignite'), { recursive: true });
    fs.writeFileSync(path.join(dir, '.rbtv', 'runtime', 'ignite', 'albert-fence.json'), '{}\n');
    const calls = [];
    const connected = await run(['connect', 'albert', '--channel-name', 'albert', '--installation', dir], { install: fakeInstaller(calls), slack: fakeSlack() });
    assert.equal(connected.code, 0, connected.err + connected.out);
    assert.equal(calls[0].includes('core/ignite#albert-memory-operations'), true);
    assert.equal(calls[0].includes('--pack'), true);
    const record = JSON.parse(fs.readFileSync(path.join(home, 'agent.json'), 'utf8'));
    assert.equal(record.files.includes('core/ignite#albert-memory-operations'), true);
    assert.equal(record.packs.includes('ignite'), true);
    const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    try {
      const ids = store.listSchedules().map((row) => row.id).sort();
      assert.deepEqual(ids, ['albert-friday', 'albert-nightly', 'albert-watchdog']);
      const friday = store.getSchedule('albert-friday');
      assert.equal(friday.cadence, 'cron:45 8 * * 5');
      assert.equal(friday.timezone, 'America/Sao_Paulo');
      assert.equal(friday.check_tool, 'runtime/ignite/checks/albert-evidence.js'.replace('albert-evidence.js', 'albert-friday.js'));
      assert.equal(store.getSchedule('albert-nightly').check_tool, 'runtime/ignite/checks/albert-evidence.js');
    } finally { store.close(); }
    fs.rmSync(dir, { recursive: true, force: true });
  });

  await test('an unconnected Albert has no schedule, channel or connection', async () => {
    const dir = workspace();
    writeConfig(dir);
    const home = installAgent(dir, 'albert');
    assert.equal(readConfig(dir).routes && Object.keys(readConfig(dir).routes).length, 0);
    assert.equal(readConfig(dir).dmAgent, undefined);
    assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
    assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'checks')), false);
    fs.rmSync(dir, { recursive: true, force: true });
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
