#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { main, HELP } = require('./cli.js');
const { nextCron, FIXED_TZ } = require('./schedule.js');
const { EMPTY_BOARD, parseBoard } = require('./board.js');

const failures = [];

function test(name, fn) {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  }
}

function tempHome() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-cli-'));
}

function writeConfig(workspace, slug, routes) {
  const configDir = path.join(workspace, '.rbtv', 'config', 'ignite');
  fs.mkdirSync(configDir, { recursive: true });
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
    dmAgent: 'master',
    routes,
  };
  fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(body));
  const home = path.join(workspace, '.rbtv', 'agents', slug);
  fs.mkdirSync(home, { recursive: true });
  return home;
}

function run(argv, extra = {}) {
  const out = [];
  const err = [];
  const code = main(argv, {
    stdout: (text) => out.push(text),
    stderr: (text) => err.push(text),
    ...extra,
  });
  return { code, out: out.join(''), err: err.join('') };
}

function acceptCast(setting) {
  if (setting.model === 'missing' || setting.effort === 'nope') {
    throw new Error(`unknown model for ${setting.harness}: ${setting.model}`);
  }
  return { harness: setting.harness, model: setting.model, effort: setting.effort, voice: setting.voice ?? null };
}

function holdWork(store, key, qid, scope) {
  store.enqueue({ id: qid, conversationKey: key, availableAt: 1_000 });
  let claim = store.claimNext(1_000);
  const workId = claim.work_id;
  for (let i = 0; i < 3; i++) {
    const now = 1_000 + i * 60_000;
    const result = store.failRun(claim.runId, 'boom', { scope, now });
    if (!result.held) claim = store.claimNext(result.retryAt);
  }
  return workId;
}

test('settings validation accept', () => {
  const home = tempHome();
  const env = { IGNITE_AGENT_HOME: home };
  const result = run([
    'settings', 'set', '--harness', 'claude', '--model', 'm', '--effort', 'high', '--voice', 'v1',
  ], { env, validateLaunch: acceptCast });
  assert.equal(result.code, 0);
  assert.match(result.out, /applies from the next turn in every conversation/);
  const file = JSON.parse(fs.readFileSync(path.join(home, 'launch.json'), 'utf8'));
  assert.deepEqual(file, { harness: 'claude', model: 'm', effort: 'high', voice: 'v1' });
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    const row = store.getLaunchSetting();
    assert.equal(row.harness, 'claude');
    assert.equal(row.model, 'm');
    assert.equal(row.effort, 'high');
    assert.equal(row.voice, 'v1');
  } finally {
    store.close();
  }
});

test('settings validation reject', () => {
  const home = tempHome();
  const env = { IGNITE_AGENT_HOME: home };
  assert.throws(() => run([
    'settings', 'set', '--harness', 'claude', '--model', 'missing', '--effort', 'high',
  ], { env, validateLaunch: acceptCast }), /unknown model/);
  assert.equal(fs.existsSync(path.join(home, 'launch.json')), false);
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    assert.equal(store.getLaunchSetting(), null);
  } finally {
    store.close();
  }
});

test('cron + tz next-occurrence across a DST change', () => {
  const springFrom = Date.parse('2026-03-08T01:00:00-05:00');
  const missing = nextCron('30 2 * * *', 'America/New_York', springFrom);
  assert.equal(missing, Date.parse('2026-03-09T02:30:00-04:00'));
  const afterJump = nextCron('0 3 * * *', 'America/New_York', springFrom);
  assert.equal(afterJump, Date.parse('2026-03-08T03:00:00-04:00'));
  const beforeFold = Date.parse('2026-11-01T01:00:00-04:00');
  assert.equal(nextCron('30 1 * * *', 'America/New_York', beforeFold), Date.parse('2026-11-01T01:30:00-04:00'));
  const betweenFold = Date.parse('2026-11-01T01:30:00-04:00');
  assert.equal(nextCron('30 1 * * *', 'America/New_York', betweenFold), Date.parse('2026-11-01T01:30:00-05:00'));

  const home = tempHome();
  const store = new Store(path.join(home, 'state.sqlite'));
  store.upsertConversation({ key: 'T1:C1:1.1', agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.close();
  const added = run([
    'schedule', 'add', '--cron', '30 2 * * *', '--tz', 'America/New_York', '--note', 'board',
    '--conversation', 'T1:C1:1.1',
  ], {
    env: { IGNITE_AGENT_HOME: home },
    now: () => springFrom,
  });
  assert.equal(added.code, 0);
  const check = new Store(path.join(home, 'state.sqlite'));
  try {
    const row = check.listSchedules()[0];
    assert.equal(row.timezone, 'America/New_York');
    assert.equal(row.next_at, missing);
  } finally {
    check.close();
  }
  assert.throws(() => run([
    'schedule', 'add', '--cron', '0 * * * *', '--note', 'no zone', '--conversation', 'T1:C1:1.1',
  ], { env: { IGNITE_AGENT_HOME: home } }), /cron requires --tz/);
  assert.throws(() => run([
    'schedule', 'add', '--note', 'empty', '--conversation', 'T1:C1:1.1',
  ], { env: { IGNITE_AGENT_HOME: home } }), /cadence/);
});

test('--every without tz documented as fixed-interval', () => {
  assert.match(HELP, /fixed-interval/);
  const home = tempHome();
  const store = new Store(path.join(home, 'state.sqlite'));
  store.upsertConversation({ key: 'T1:C1:1.1', agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.close();
  const from = Date.parse('2026-03-08T01:30:00-05:00');
  const added = run([
    'schedule', 'add', '--every', '90m', '--note', 'interval', '--conversation', 'T1:C1:1.1',
  ], { env: { IGNITE_AGENT_HOME: home }, now: () => from });
  assert.equal(added.code, 0);
  const check = new Store(path.join(home, 'state.sqlite'));
  try {
    const row = check.listSchedules()[0];
    assert.equal(row.timezone, FIXED_TZ);
    assert.equal(row.cadence, 'every:90m');
    assert.equal(row.next_at, from + 90 * 60_000);
  } finally {
    check.close();
  }
  assert.throws(() => run([
    'schedule', 'add', '--every', '90m', '--tz', 'America/New_York', '--note', 'no',
    '--conversation', 'T1:C1:1.1',
  ], { env: { IGNITE_AGENT_HOME: home } }), /fixed-interval/);
});

test('due-dedupe', () => {
  const home = tempHome();
  const store = new Store(path.join(home, 'state.sqlite'));
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  const heldId = holdWork(store, key, 'q-held', 'work');
  assert.equal(store.getWork(heldId).state, 'held');
  store.upsertSchedule({
    id: 'due-open', conversationKey: key, cadence: 'every:1h', timezone: FIXED_TZ,
    nextAt: 1_000, note: 'open', report: 'when-useful',
  });
  store.upsertSchedule({
    id: 'due-held', conversationKey: key, workId: heldId, cadence: 'every:1h', timezone: FIXED_TZ,
    nextAt: 1_000, note: 'held', report: 'when-useful',
  });
  const stopKey = 'T1:C9:9.9';
  store.upsertConversation({ key: stopKey, agent: 'a', workspace: 'T1', channel: 'C9', rootTs: '9.9' });
  store.enqueue({ id: 'q-stop', conversationKey: stopKey, availableAt: 1_000 });
  const stoppedClaim = store.claimNext(1_000);
  const stoppedId = stoppedClaim.work_id;
  store.stopWork(stoppedId);
  store.upsertSchedule({
    id: 'due-stopped', conversationKey: stopKey, workId: stoppedId, cadence: 'every:1h', timezone: FIXED_TZ,
    nextAt: 1_000, note: 'stopped', report: 'when-useful',
  });
  store.close();
  const first = run(['schedules-due', '--now', '2026-01-01T00:00:00Z', '--json'], {
    env: { IGNITE_AGENT_HOME: home },
  });
  assert.equal(first.code, 0);
  const body = JSON.parse(first.out);
  const open = body.results.find((row) => row.id === 'due-open');
  const held = body.results.find((row) => row.id === 'due-held');
  const stopped = body.results.find((row) => row.id === 'due-stopped');
  assert.equal(open.inserted, true);
  assert.equal(held.inserted, false);
  assert.equal(held.reason, 'held');
  assert.equal(stopped.inserted, false);
  assert.equal(stopped.reason, 'stopped');
  const mid = new Store(path.join(home, 'state.sqlite'));
  try {
    const pending = mid.db.prepare(`SELECT id FROM queue WHERE kind='schedule' AND state='pending'`).all();
    assert.equal(pending.length, 1);
    assert.equal(mid.getWork(heldId).state, 'held');
    assert.equal(mid.getWork(stoppedId).state, 'stopped');
    assert.equal(mid.agentHold(), null);
    assert.equal(mid.getSchedule('due-held').next_at, 1_000);
  } finally {
    mid.close();
  }
  const second = run(['schedules-due', '--now', '2026-01-01T00:00:00Z', '--json'], {
    env: { IGNITE_AGENT_HOME: home },
  });
  const again = JSON.parse(second.out);
  assert.equal(again.results.some((row) => row.id === 'due-open'), false);
  assert.equal(again.results.find((row) => row.id === 'due-held').reason, 'held');
  assert.equal(again.results.find((row) => row.id === 'due-stopped').reason, 'stopped');
  const end = new Store(path.join(home, 'state.sqlite'));
  try {
    const pending = end.db.prepare(`SELECT id FROM queue WHERE kind='schedule' AND state='pending'`).all();
    assert.equal(pending.length, 1);
    assert.equal(end.getWork(heldId).state, 'held');
  } finally {
    end.close();
  }
});

test('each recurring due starts fresh even after delivery rekeys the wake', () => {
  const home = tempHome();
  const store = new Store(path.join(home, 'state.sqlite'));
  const key = 'T1:C1:1.1';
  const env = { IGNITE_AGENT_HOME: home };
  try {
    store.upsertConversation({ key, agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
    store.setSession(key, 'claude', 'old-session');
    store.recordMessage(key, { id: 'old', role: 'owner', text: 'old history' });
    store.upsertSchedule({
      id: 'check', conversationKey: key, cadence: 'every:1h', timezone: FIXED_TZ,
      nextAt: 1_000, note: 'details stay on the board', report: 'always',
    });
    const keys = new Set([key]);
    for (const hour of ['00', '01']) {
      const due = run(['schedules-due', '--now', `2026-01-01T${hour}:00:00Z`, '--json'], { env });
      assert.equal(JSON.parse(due.out).results[0].inserted, true);
      const claim = store.claimNext();
      assert.equal(keys.has(claim.conversation_key), false);
      keys.add(claim.conversation_key);
      assert.deepEqual(claim.payload, { scheduleId: 'check' });
      assert.equal(store.getConversation(claim.conversation_key).root_ts, null);
      assert.equal(store.getSession(claim.conversation_key, 'claude'), null);
      assert.deepEqual(store.listHistory(claim.conversation_key), []);
      store.finishRun(claim.runId, claim.nonce, {
        invocationNonce: claim.nonce, output: '{}', disposition: 'completed',
        harness: 'claude', sessionId: `session-${hour}`, outbox: [{ text: 'result' }],
      });
      const row = store.pendingOutbox()[0];
      store.markDelivered(row.id, { channel: 'C1', ts: `9.${hour}` });
      assert.equal(store.getSchedule('check').conversation_key, key);
    }
    assert.equal(store.getSession(key, 'claude'), 'old-session');
  } finally {
    store.close();
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test('retry clears only the named hold', () => {
  const home = tempHome();
  const store = new Store(path.join(home, 'state.sqlite'));
  const key = 'T1:C1:1.1';
  const other = 'T1:C2:2.2';
  const third = 'T1:C3:3.3';
  for (const [id, channel, root] of [[key, 'C1', '1.1'], [other, 'C2', '2.2'], [third, 'C3', '3.3']]) {
    store.upsertConversation({ key: id, agent: 'a', workspace: 'T1', channel, rootTs: root });
  }
  const first = holdWork(store, key, 'q1', 'work');
  const second = holdWork(store, other, 'q2', 'work');
  holdWork(store, third, 'q3', 'agent');
  assert.ok(store.agentHold());
  assert.equal(store.getWork(first).state, 'held');
  assert.equal(store.getWork(second).state, 'held');
  store.close();
  const result = run(['work', 'retry', first], { env: { IGNITE_AGENT_HOME: home } });
  assert.equal(result.code, 0);
  const check = new Store(path.join(home, 'state.sqlite'));
  try {
    assert.equal(check.getWork(first).state, 'open');
    assert.equal(check.getWork(second).state, 'held');
    assert.ok(check.agentHold());
  } finally {
    check.close();
  }
});

test('post association', () => {
  const workspace = tempHome();
  const home = writeConfig(workspace, 'sample', { C9: 'sample' });
  const dmHome = writeConfig(workspace, 'master', { C9: 'sample' });
  const routed = run(['post', '--text', 'board result', '--file', path.join(workspace, 'bot.json')], {
    env: { IGNITE_AGENT_HOME: home },
  });
  assert.equal(routed.code, 0);
  assert.match(routed.out, /activated/);
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    const pending = store.pendingOutbox();
    assert.equal(pending.length, 1);
    assert.equal(pending[0].as_root, true);
    assert.equal(pending[0].payload.text, 'board result');
    assert.equal(pending[0].payload.files.length, 1);
    const conv = store.getConversation(pending[0].conversation_key);
    assert.equal(conv.activated, true);
    assert.equal(conv.agent, 'sample');
    assert.equal(conv.channel, 'C9');
  } finally {
    store.close();
  }
  const dm = run(['post', '--text', 'dm note', '--audio'], { env: { IGNITE_AGENT_HOME: dmHome } });
  assert.equal(dm.code, 0);
  const dmStore = new Store(path.join(dmHome, 'state.sqlite'));
  try {
    const pending = dmStore.pendingOutbox();
    assert.equal(pending.length, 1);
    assert.equal(pending[0].as_root, true);
    assert.equal(pending[0].payload.audio, true);
    assert.equal(pending[0].payload.imUser, 'UOWNER');
    const conv = dmStore.getConversation(pending[0].conversation_key);
    assert.equal(conv.activated, true);
    assert.equal(conv.channel, 'UOWNER');
    assert.equal(conv.agent, 'master');
  } finally {
    dmStore.close();
  }
});

test('post --thread selects stored channel and DM history without opening a new conversation', () => {
  const workspace = tempHome();
  try {
    for (const [slug, channel] of [['sample', 'C9'], ['master', 'D1']]) {
      const home = writeConfig(workspace, slug, { C9: 'sample' });
      const store = new Store(path.join(home, 'state.sqlite'));
      const key = `T1:${channel}:1.1`;
      try {
        store.upsertConversation({ key, agent: slug, workspace: 'T1', channel, rootTs: '1.1' });
        store.recordMessage(key, { id: 'before', role: 'owner', text: 'earlier context' });
        store.setSession(key, 'claude', 'keep-session');
        const file = path.join(workspace, 'message text.txt');
        fs.writeFileSync(file, 'Café check complete\r\n', 'utf8');
        for (const thread of [key, '1.1']) {
          const result = run(['post', '--thread', thread, '--text-file', file, '--file', 'report.pdf', '--audio', '--json'], {
            env: { IGNITE_AGENT_HOME: home, IGNITE_CONVERSATION: 'unrelated-wake' },
          });
          assert.equal(result.code, 0);
          assert.equal(result.err, '');
          const body = JSON.parse(result.out);
          assert.equal(body.conversationKey, key);
          assert.equal(body.channel, channel);
          assert.equal(body.activated, true);
          const row = store.pendingOutbox().find((item) => item.id === body.outboxId);
          assert.equal(row.as_root, false);
          assert.equal(row.client_msg_id, body.clientMsgId);
          assert.deepEqual(row.payload, { text: 'Café check complete\r\n', audio: true, files: ['report.pdf'] });
        }
        assert.equal(store.db.prepare('SELECT COUNT(*) AS n FROM conversations').get().n, 1);
        assert.equal(store.getConversation(key).activated, true);
        assert.equal(store.getSession(key, 'claude'), 'keep-session');
        assert.deepEqual(store.listHistory(key).map((row) => row.text), ['earlier context']);
        assert.equal(run(['post', '--thread', key, '--text', 'next'], { env: { IGNITE_AGENT_HOME: home } }).out,
          `${key} activated\n`);
      } finally {
        store.close();
      }
    }
  } finally {
    fs.rmSync(workspace, { recursive: true, force: true });
  }
});

test('post --thread refuses unknown, ambiguous and unbound targets without queueing', () => {
  const workspace = tempHome();
  const home = writeConfig(workspace, 'sample', { C9: 'sample' });
  const store = new Store(path.join(home, 'state.sqlite'));
  const env = { IGNITE_AGENT_HOME: home };
  try {
    for (const channel of ['C9', 'C8']) {
      store.upsertConversation({ key: `T1:${channel}:1.1`, agent: 'sample', workspace: 'T1', channel, rootTs: '1.1' });
    }
    store.upsertConversation({ key: 'pending:other', agent: 'sample', workspace: 'T1', channel: 'C9' });
    store.upsertConversation({ key: 'T1:C9:board', agent: 'sample', workspace: 'T1', channel: 'C9', rootTs: 'board' });
    store.upsertConversation({ key: 'T1:C9:2.2', agent: 'other', workspace: 'T1', channel: 'C9', rootTs: '2.2' });
    for (const thread of ['missing', 'pending:other', 'T1:C9:board', 'T1:C9:2.2']) {
      assert.throws(() => run(['post', '--thread', thread, '--text', 'reply'], { env }), /unknown thread/);
    }
    assert.throws(() => run(['post', '--thread', '1.1', '--text', 'reply'], { env }),
      /ambiguous thread: 1\.1; use a full conversation key: .*T1:C[89]:1\.1/);
    assert.throws(() => run(['post', '--thread'], { env }), /requires a value/);
    assert.throws(() => run(['post', '--thread', 'T1:C9:1.1'], { env }), /post requires --text/);
    assert.throws(() => run(['post', '--thread', '1.1', '--thread', '1.1', '--text', 'reply'], { env }), /duplicate flag --thread/);
    assert.deepEqual(store.pendingOutbox(), []);
    assert.equal(store.getConversation('T1:C9:1.1').activated, false);
  } finally {
    store.close();
    fs.rmSync(workspace, { recursive: true, force: true });
  }
});

test('post help explains thread targeting without requiring a home', () => {
  for (const flag of ['--help', '-h']) {
    for (const args of [[flag, 'post'], ['post', flag], ['post', '--thread', 'T1:C9:1.1', flag]]) {
      const result = run(args, { env: {} });
      assert.equal(result.code, 0);
      assert.match(result.out, /\[--thread <thread>\]/);
      assert.match(result.out, /unique root timestamp/);
      assert.match(result.out, /history after delivery/);
      assert.equal(result.err, '');
    }
  }
});

test('help names the new verbs and not create', () => {
  const result = run(['--help']);
  assert.equal(result.code, 0);
  assert.match(result.out, /install <agent file>/);
  assert.match(result.out, /update <agent>/);
  assert.match(result.out, /connect <agent>/);
  assert.match(result.out, /disconnect <agent>/);
  assert.doesNotMatch(result.out, /ignite-agent create/);
  assert.match(HELP, /fixed-interval/);
});

test('create is not a command', () => {
  assert.throws(() => run(['create']), /unknown command: create/);
});

function boardFixture(fn) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite board cli-'));
  const home = path.join(root, 'sample');
  fs.mkdirSync(home);
  const file = path.join(home, 'board.md');
  const candidate = path.join(root, 'candidate board.md');
  const text = EMPTY_BOARD.replace('## What matters now\n', `## What matters now

### Printer toner reorder
Owner chose toner café.
- Threads: none
- Detail: none
- Flags: none
`);
  fs.writeFileSync(candidate, text, 'utf8');
  const deps = { env: { IGNITE_AGENT_HOME: home }, now: () => Date.parse('2026-10-03T12:00:00Z') };
  try { fn({ root, home, file, candidate, text, deps }); }
  finally { fs.rmSync(root, { recursive: true, force: true }); }
}

test('board write uses the current path, reports unchanged, and opens no database', () => {
  boardFixture(({ home, file, candidate, text, deps }) => {
    const first = run(['board', 'write', '--file', candidate], deps);
    assert.equal(first.code, 0);
    assert.equal(first.out, `written ${file}\n`);
    assert.equal(first.err, '');
    assert.equal(fs.readFileSync(file, 'utf8'), text);
    const repeat = run(['board', 'write', '--file', candidate, '--json'], deps);
    assert.deepEqual(JSON.parse(repeat.out), { path: file, changed: false });
    assert.equal(run(['board', 'write', '--file', candidate], deps).out, `unchanged ${file}\n`);
    assert.equal(fs.existsSync(path.join(home, '_artifacts')), false);
    assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), false);
  });
});

test('board close records outcome, date, agent and optional thread in JSON and text modes', () => {
  boardFixture(({ file, candidate, deps }) => {
    assert.equal(run(['board', 'write', '--file', candidate], deps).code, 0);
    const result = run(['board', 'close', 'Printer toner reorder', 'Order confirmed', '[order](https://example.com/order)', '--json'], deps);
    assert.equal(result.code, 0);
    assert.deepEqual(JSON.parse(result.out), { path: file, changed: true, subject: 'Printer toner reorder' });
    const parsed = parseBoard(fs.readFileSync(file, 'utf8'));
    assert.equal(parsed.subjects.length, 0);
    assert.equal(parsed.closed[0], '- Printer toner reorder — Order confirmed (2026-10-03 · sample/[order](https://example.com/order))');
  });
  boardFixture(({ file, candidate, deps }) => {
    run(['board', 'write', '--file', candidate], deps);
    const result = run(['board', 'close', 'Printer toner reorder', 'Order confirmed'], deps);
    assert.equal(result.code, 0);
    assert.equal(result.out, `closed Printer toner reorder in ${file}\n`);
    assert.equal(result.err, '');
  });
});

test('board failures report the reason and preserve existing bytes', () => {
  boardFixture(({ file, candidate, text, deps }) => {
    run(['board', 'write', '--file', candidate], deps);
    const before = fs.readFileSync(file);
    for (const candidateText of [text.replace('## Watch-outs', '## Notes'),
      text.replace('## Watch-outs', `## Watch-outs\n${Array.from({ length: 7 }, () => '- Use one PDF. (2026-10-01 · sample)').join('\n')}`)]) {
      fs.writeFileSync(candidate, candidateText, 'utf8');
      const result = run(['board', 'write', '--file', candidate], deps);
      assert.equal(result.code, 1);
      assert.equal(result.out, '');
      assert.match(result.err, /board refused/);
      assert.deepEqual(fs.readFileSync(file), before);
    }
    const result = run(['board', 'close', 'Unknown', 'Done', '--json'], deps);
    assert.equal(result.code, 1);
    assert.match(JSON.parse(result.out).error, /subject not found/);
    assert.equal(JSON.parse(result.out).path, file);
    assert.equal(result.err, '');
    assert.deepEqual(fs.readFileSync(file), before);
  });
});

test('board rejects invalid arguments, missing input and missing home', () => {
  boardFixture(({ home, candidate, deps }) => {
    for (const args of [
      ['write'], ['write', candidate], ['write', '--file', candidate, '--file', candidate],
      ['write', '--file', candidate, '--unknown', 'x'], ['close'], ['close', 'Subject'],
      ['close', 'Subject', 'Outcome', 'Thread', 'Extra'], ['close', 'Subject', 'Outcome', '--audio'],
      ['erase'], ['write', '--file', path.join(home, 'missing.md')],
    ]) {
      const result = run(['board', ...args, '--json'], deps);
      assert.equal(result.code, 1, args.join(' '));
      assert.ok(JSON.parse(result.out).error);
      assert.equal(result.err, '');
    }
    const missing = run(['board', 'write', '--file', candidate, '--json'], { env: {} });
    assert.equal(missing.code, 1);
    assert.deepEqual(JSON.parse(missing.out), { path: null, error: '--agent or IGNITE_AGENT_HOME required' });
    assert.equal(fs.existsSync(path.join(home, 'board.md')), false);
    assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), false);
  });
});

test('board help works before and after every command depth without context or writes', () => {
  assert.match(run(['--help']).out, /board write --file/);
  for (const args of [[], ['write'], ['close'], ['close', 'Subject', 'Outcome']]) {
    for (const flag of ['--help', '-h']) {
      for (const argv of [[flag, 'board', ...args], ['board', flag, ...args], ['board', ...args, flag]]) {
        const result = run(argv, { env: {} });
        assert.equal(result.code, 0);
        assert.match(result.out, /board write --file <path>/);
        assert.match(result.out, /board close <subject> <outcome>/);
        assert.match(result.out, /90 non-empty lines/);
        assert.equal(result.err, '');
      }
    }
  }
  assert.match(run(['board'], { env: {} }).out, /checked short-term memory/);
  assert.equal(run(['board', 'unknown', '--help'], { env: {} }).code, 0);
});

test('board option terminator permits a literal help-like subject and outcome', () => {
  boardFixture(({ candidate, text, file, deps }) => {
    fs.writeFileSync(candidate, text.replace('Printer toner reorder', '--help'), 'utf8');
    assert.equal(run(['board', 'write', '--file', candidate], deps).code, 0);
    const result = run(['board', 'close', '--', '--help', '--json'], deps);
    assert.equal(result.code, 0);
    assert.equal(result.out, `closed --help in ${file}\n`);
    assert.equal(parseBoard(fs.readFileSync(file, 'utf8')).closed[0], '- --help — --json (2026-10-03 · sample)');
  });
});

test('board resolves explicit workspace and gives IGNITE_AGENT_HOME precedence', () => {
  boardFixture(({ root, home, candidate, file, deps }) => {
    const workspace = path.join(root, 'workspace');
    const other = writeConfig(workspace, 'other', {});
    const selected = run(['--agent', 'other', '--workspace', workspace, 'board', 'write', '--file', candidate], { env: {} });
    assert.equal(selected.code, 0);
    assert.ok(fs.existsSync(path.join(other, 'board.md')));
    assert.equal(fs.existsSync(file), false);
    const overridden = run(['--agent', 'other', '--workspace', workspace, 'board', 'write', '--file', candidate], deps);
    assert.equal(overridden.code, 0);
    assert.ok(fs.existsSync(file));
    assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), false);
  });
});

test('board executable returns real exit codes and JSON from another directory', () => {
  boardFixture(({ root, home, candidate, file }) => {
    const env = { ...process.env, IGNITE_AGENT_HOME: home, NODE_NO_WARNINGS: '1' };
    const invoke = (args) => spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), ...args], { cwd: root, env, encoding: 'utf8' });
    const written = invoke(['board', 'write', '--file', candidate, '--json']);
    assert.equal(written.status, 0);
    assert.deepEqual(JSON.parse(written.stdout), { path: file, changed: true });
    assert.equal(written.stderr, '');
    const failed = invoke(['board', 'close', 'Missing', 'Done', '--json']);
    assert.equal(failed.status, 1);
    assert.match(JSON.parse(failed.stdout).error, /subject not found/);
    assert.equal(failed.stderr, '');
    const plain = invoke(['board', 'close', 'Missing', 'Done']);
    assert.equal(plain.status, 1);
    assert.equal(plain.stdout, '');
    assert.match(plain.stderr, /subject not found/);
  });
});

if (failures.length) {
  console.log(`${failures.length} failed`);
  process.exit(1);
}
console.log('ok');
