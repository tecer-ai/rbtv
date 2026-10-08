#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { main, OPTIONS } = require('./cli.js');
const { PAGES } = require('./help.js');
const { getState } = require('./dreamer.js');
const { nextCron, FIXED_TZ } = require('./schedule.js');
const { EMPTY_BOARD, parseBoard, boardPath } = require('./board.js');
const { acquireMemoryLock, writeRoot } = require('./memory-write.js');

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
  fs.mkdirSync(path.dirname(boardPath(home)));
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  store.upsertConversation({ key: 'T1:C1:1.1', agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.close();
  const added = run([
    'schedule', 'add', '--cron', '30 2 * * *', '--tz', 'America/New_York', '--note', 'board',
    '--conversation', 'T1:C1:1.1',
  ], {
    env: { RBTV_AGENT_HOME: home },
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
  ], { env: { RBTV_AGENT_HOME: home } }), /cron requires --tz/);
  assert.throws(() => run([
    'schedule', 'add', '--note', 'empty', '--conversation', 'T1:C1:1.1',
  ], { env: { RBTV_AGENT_HOME: home } }), /cadence/);
});

test('--every without tz documented as fixed-interval', () => {
  assert.match(run(['schedule', 'add', '-h']).out, /fixed-interval/);
  const home = tempHome();
  fs.mkdirSync(path.dirname(boardPath(home)));
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  store.upsertConversation({ key: 'T1:C1:1.1', agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.close();
  const from = Date.parse('2026-03-08T01:30:00-05:00');
  const added = run([
    'schedule', 'add', '--every', '90m', '--note', 'interval', '--conversation', 'T1:C1:1.1',
  ], { env: { RBTV_AGENT_HOME: home }, now: () => from });
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
  ], { env: { RBTV_AGENT_HOME: home } }), /fixed-interval/);
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
    env: { RBTV_AGENT_HOME: home },
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
    env: { RBTV_AGENT_HOME: home },
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
  const env = { RBTV_AGENT_HOME: home };
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
  const result = run(['work', 'retry', first], { env: { RBTV_AGENT_HOME: home } });
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
    env: { RBTV_AGENT_HOME: home },
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
  const dm = run(['post', '--text', 'dm note', '--audio'], { env: { RBTV_AGENT_HOME: dmHome } });
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
            env: { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: 'unrelated-wake' },
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
        assert.equal(run(['post', '--thread', key, '--text', 'next'], { env: { RBTV_AGENT_HOME: home } }).out,
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
  const env = { RBTV_AGENT_HOME: home };
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

test('help names connect and disconnect but not retired verbs', () => {
  const result = run(['--help']);
  assert.equal(result.code, 0);
  assert.match(result.out, /^ {2}connect {8}Turn the ignite pack on/m);
  assert.match(result.out, /^ {2}disconnect {5}Remove the Slack route/m);
  assert.doesNotMatch(result.out, /^ *ignite (connect|disconnect|turn|deploy) [A-Z-]/m);
  assert.doesNotMatch(result.out, /\binstall\b|\bupdate\b|\bsettings\b/);
  assert.doesNotMatch(result.out, /ignite create/);
  assert.match(run(['schedule', 'add', '-h']).out, /fixed-interval/);
});

test('root and group help print no usage form of a child; each verb prints its own', () => {
  const groups = {
    schedule: ['add', 'list', 'change', 'cancel'],
    work: ['status', 'retry', 'resume', 'stop'],
    board: ['write', 'close'],
    dreamer: ['run', 'enable', 'disable'],
  };
  for (const [group, verbs] of Object.entries(groups)) {
    const page = run([group, '-h'], { env: {} });
    assert.equal(page.code, 0);
    assert.doesNotMatch(page.out, /usage:/);
    assert.doesNotMatch(page.out, new RegExp(`^ *(ignite )?${group} (${verbs.join('|')}) [-<\\[(A-Z]`, 'm'));
    for (const verb of verbs) {
      assert.match(page.out, new RegExp(`^ {2}${verb} +\\S`, 'm'));
      for (const argv of [[group, verb, '-h'], ['-h', group, verb], [group, '--help', verb]]) {
        const leaf = run(argv, { env: {} });
        assert.equal(leaf.code, 0);
        assert.equal(leaf.err, '');
        assert.match(leaf.out, new RegExp(`^ignite ${group} ${verb} — `));
        assert.match(leaf.out, new RegExp(`^usage: ignite ${group} ${verb}\\b`, 'm'));
      }
    }
  }
});

test('schedule list and work status pages describe what the commands print', () => {
  const home = tempHome();
  try {
    fs.mkdirSync(path.dirname(boardPath(home)));
    fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
    const store = new Store(path.join(home, 'state.sqlite'));
    store.upsertConversation({ key: 'T1:C1:1.1', agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
    store.close();
    const env = { RBTV_AGENT_HOME: home };
    const now = () => Date.parse('2026-10-03T12:00:00Z');
    run(['schedule', 'add', '--every', '1h', '--note', 'n', '--conversation', 'T1:C1:1.1'], { env, now });
    const list = run(['schedule', 'list'], { env });
    assert.match(list.out, /^\S+ every:1h fixed next=1791032400000 enabled=true n\n$/);
    const page = run(['schedule', 'list', '-h'], { env: {} }).out;
    assert.match(page, /next=<next fire in epoch milliseconds>\nenabled=<true\|false> <note>/);
    const status = run(['work', 'status', '-h'], { env: {} }).out;
    assert.match(status, /open, continue,\s+held, stopped, completed, waiting_owner or waiting_workers/);
    assert.match(status, /agentHold is the hold record\s+\{reason, at\} or null/);
  } finally { fs.rmSync(home, { recursive: true, force: true }); }
});

function filesUnder(dir) {
  return fs.readdirSync(dir, { recursive: true }).map(String).sort()
    .filter((name) => fs.statSync(path.join(dir, name)).isFile())
    .map((name) => [name, fs.readFileSync(path.join(dir, name)).toString('base64')]);
}

const OPTION_KEY = 'T1:C1:1.1';

// Each group runs its refusals twice from the real executable: against a home with a database,
// then against a home with none. Every file under the installation must stay byte-identical.
function optionRefusals(group, cases) {
  test(`${group} refuses an option the verb does not have and writes nothing`, () => {
    const workspace = tempHome();
    try {
      const home = writeConfig(workspace, 'sample', { C1: 'sample' });
      fs.mkdirSync(path.dirname(boardPath(home)));
      fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
      const candidate = path.join(workspace, 'candidate.md');
      fs.writeFileSync(candidate, EMPTY_BOARD, 'utf8');
      const db = path.join(home, 'state.sqlite');
      const store = new Store(db);
      store.upsertConversation({ key: OPTION_KEY, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
      store.upsertSchedule({ id: 'existing', conversationKey: OPTION_KEY, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: 1000, note: 'Original' });
      store.close();
      const env = { ...process.env, RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: OPTION_KEY, NODE_NO_WARNINGS: '1' };
      const invoke = (args) => spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), ...args], { cwd: workspace, env, encoding: 'utf8' });
      for (const withDatabase of [true, false]) {
        if (!withDatabase) fs.rmSync(db);
        const before = filesUnder(workspace);
        for (const [verb, option, args] of cases) {
          const label = `${args.join(' ')} (${withDatabase ? 'database' : 'no database'})`;
          const message = `'${option}' is not a ${verb} option\nNothing changed.\nignite ${verb} -h`;
          const result = invoke(args.map((arg) => (arg === 'CANDIDATE' ? candidate : arg)));
          assert.equal(result.status, 1, label);
          assert.equal(result.stdout, '', label);
          assert.equal(result.stderr, `${message}\n`, label);
          assert.deepEqual(filesUnder(workspace), before, label);
        }
      }
    } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
  });
}

optionRefusals('schedule', [
  ['schedule add', '--bogus', ['schedule', 'add', '--every', '1h', '--note', 'n', '--bogus', '1']],
  ['schedule add', '--enabled', ['schedule', 'add', '--every', '1h', '--note', 'n', '--enabled', 'false']],
  ['schedule add', '--audio', ['schedule', 'add', '--every', '1h', '--note', 'n', '--audio']],
  ['schedule add', '--note=n', ['schedule', 'add', '--every', '1h', '--note=n']],
  ['schedule list', '--bogus', ['schedule', 'list', '--bogus', '1']],
  ['schedule change', '--subject', ['schedule', 'change', 'existing', '--subject', 'x']],
  ['schedule change', '--conversation', ['schedule', 'change', 'existing', '--note', 'Changed', '--conversation', 'x']],
  ['schedule cancel', '--bogus', ['schedule', 'cancel', 'existing', '--bogus', '1']],
]);
optionRefusals('schedules-due', [
  ['schedules-due', '--bogus', ['schedules-due', '--now', '2026-10-01T13:00:00Z', '--bogus', '1']],
]);
optionRefusals('work', [
  ['work status', '--bogus', ['work', 'status', '--bogus', '1']],
  ['work retry', '--conversation', ['work', 'retry', '--conversation', OPTION_KEY]],
  ['work resume', '--bogus', ['work', 'resume', '--bogus', '1']],
  ['work stop', '--bogus', ['work', 'stop', 'existing', '--bogus', '1']],
]);
optionRefusals('wake', [
  ['wake', '--bogus', ['wake', '--conversation', OPTION_KEY, '--note', 'n', '--bogus', '1']],
]);
optionRefusals('post', [
  ['post', '--bogus', ['post', '--text', 'hi', '--bogus', '1']],
  ['post', '--note', ['post', '--text', 'hi', '--note', 'n']],
]);
optionRefusals('board', [
  ['board write', '--bogus', ['board', 'write', '--file', 'CANDIDATE', '--bogus', '1']],
  ['board close', '--file', ['board', 'close', 'Subject', 'Outcome', '--file', 'CANDIDATE']],
  ['board close', '--audio', ['board', 'close', 'Subject', 'Outcome', '--audio']],
]);
optionRefusals('remember', [
  ['remember', '--bogus', ['remember', 'fact', '--bogus', '1']],
]);

test('each verb takes exactly the options its help page names', () => {
  for (const [verb, options] of Object.entries(OPTIONS)) {
    if (verb === 'remember') {
      assert.deepEqual(options, []);
      continue;
    }
    const usage = PAGES[verb].match(/^usage: [^]*?\n\n/m)[0];
    const named = new Set([...usage.matchAll(/--([a-z-]+)/g)].map((match) => match[1]));
    named.delete('json');
    assert.deepEqual([...named].sort(), [...options].sort(), verb);
  }
});

test('schedule change refuses each empty note schedule add refuses', () => {
  const home = tempHome();
  fs.mkdirSync(path.dirname(boardPath(home)));
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  const deps = { env: { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: OPTION_KEY } };
  try {
    store.upsertConversation({ key: OPTION_KEY, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
    store.upsertSchedule({ id: 'existing', conversationKey: OPTION_KEY, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: 1000, note: 'Original' });
    const board = fs.readFileSync(boardPath(home), 'utf8');
    for (const note of ['', '  ', '\n\t']) {
      for (const args of [['add', '--every', '1h'], ['change', 'existing']]) {
        assert.throws(() => run(['schedule', ...args, '--note', note], deps),
          (error) => error.message === '--note requires non-empty text' && error.exitCode === 1, `${args[0]} ${JSON.stringify(note)}`);
      }
    }
    assert.throws(() => run(['schedule', 'add', '--every', '1h'], deps), /^Error: --note is required$/);
    assert.deepEqual(store.listSchedules().map((row) => row.note), ['Original']);
    assert.equal(fs.readFileSync(boardPath(home), 'utf8'), board);
    assert.equal(run(['schedule', 'change', 'existing', '--report', 'always'], deps).code, 0);
    assert.equal(store.getSchedule('existing').note, 'Original');
  } finally { store.close(); fs.rmSync(home, { recursive: true, force: true }); }
});

test('retired verbs are unknown', () => {
  for (const verb of ['install', 'update', 'settings']) {
    assert.throws(() => run([verb]), new RegExp(`unknown command: ${verb}`));
  }
});

test('create is not a command', () => {
  assert.throws(() => run(['create']), /unknown command: create/);
});

function boardFixture(fn) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite board cli-'));
  const home = path.join(root, 'sample');
  fs.mkdirSync(home);
  const file = boardPath(home);
  const candidate = path.join(root, 'candidate board.md');
  const text = EMPTY_BOARD.replace('## What matters now\n', `## What matters now

### Printer toner reorder
Owner chose toner café.
- Threads: none
- Detail: none
- Flags: none
`);
  fs.writeFileSync(candidate, text, 'utf8');
  const deps = { env: { RBTV_AGENT_HOME: home }, now: () => Date.parse('2026-10-03T12:00:00Z') };
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
    assert.equal(fs.existsSync(path.join(home, 'board.md')), false);
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
    assert.deepEqual(JSON.parse(missing.out), { path: null, error: '--agent or RBTV_AGENT_HOME required' });
    assert.equal(fs.existsSync(path.join(home, 'board.md')), false);
    assert.equal(fs.existsSync(boardPath(home)), false);
    assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), false);
  });
});

test('board help works before and after every command depth without context or writes', () => {
  assert.match(run(['board', '--help']).out, /^ {2}write +Replace the board/m);
  for (const [args, usage, text] of [
    [[], null, /checked short-term memory/],
    [['write'], /^usage: ignite board write --file <path>/m, /90 non-empty lines/],
    [['close'], /^usage: ignite board close <subject> <outcome> \[thread\]/m, /Recently closed/],
    [['close', 'Subject', 'Outcome'], /^usage: ignite board close <subject> <outcome> \[thread\]/m, /Recently closed/],
  ]) {
    for (const flag of ['--help', '-h']) {
      for (const argv of [[flag, 'board', ...args], ['board', flag, ...args], ['board', ...args, flag]]) {
        const result = run(argv, { env: {} });
        assert.equal(result.code, 0);
        if (usage) assert.match(result.out, usage);
        else assert.doesNotMatch(result.out, /usage:/);
        assert.match(result.out, text);
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

test('board resolves explicit workspace and gives RBTV_AGENT_HOME precedence', () => {
  boardFixture(({ root, home, candidate, file, deps }) => {
    const workspace = path.join(root, 'workspace');
    const other = writeConfig(workspace, 'other', {});
    const selected = run(['--agent', 'other', '--installation', workspace, 'board', 'write', '--file', candidate], { env: {} });
    assert.equal(selected.code, 0);
    assert.ok(fs.existsSync(boardPath(other)));
    assert.equal(fs.existsSync(file), false);
    const overridden = run(['--agent', 'other', '--installation', workspace, 'board', 'write', '--file', candidate], deps);
    assert.equal(overridden.code, 0);
    assert.ok(fs.existsSync(file));
    assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), false);
  });
});

test('board executable returns real exit codes and JSON from another directory', () => {
  boardFixture(({ root, home, candidate, file }) => {
    const env = { ...process.env, RBTV_AGENT_HOME: home, NODE_NO_WARNINGS: '1' };
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

test('board commands migrate a legacy board and leave the old bytes untouched', () => {
  boardFixture(({ home, file, candidate, text, deps }) => {
    const legacy = path.join(home, 'board.md');
    fs.writeFileSync(legacy, text, 'utf8');
    assert.equal(run(['board', 'write', '--file', candidate], deps).code, 0);
    assert.equal(fs.readFileSync(file, 'utf8'), text);
    assert.equal(run(['board', 'close', 'Printer toner reorder', 'Done'], deps).code, 0);
    assert.equal(parseBoard(fs.readFileSync(file, 'utf8')).subjects.length, 0);
    assert.equal(fs.readFileSync(legacy, 'utf8'), text);
  });
});

test('schedule subjects and generated timers survive changes and dues; cancellation removes the row', () => {
  const home = tempHome();
  fs.mkdirSync(path.dirname(boardPath(home)));
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  const key = 'T1:C1:1.1';
  const now = Date.parse('2026-10-01T12:00:00Z');
  const deps = { env: { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: key }, now: () => now };
  const timers = () => parseBoard(fs.readFileSync(boardPath(home), 'utf8')).timers;
  try {
    store.upsertConversation({ key, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
    const added = run(['schedule', 'add', '--every', '1h', '--note', 'Read café notes', '--subject', 'Café review', '--json'], deps);
    const id = JSON.parse(added.out).schedule.id;
    assert.equal(store.getSchedule(id).subject, 'Café review');
    assert.equal(timers()[2], `| 2026-10-01 13:00 UTC | ${id} | Read café notes | Café review |`);
    run(['schedule', 'change', id, '--note', 'Read latest notes'], deps);
    assert.match(timers()[2], /Read latest notes \| Café review/);
    run(['schedules-due', '--now', '2026-10-01T13:00:00Z'], deps);
    assert.equal(store.getSchedule(id).subject, 'Café review');
    assert.match(timers()[2], /2026-10-01 14:00 UTC/);
    run(['schedule', 'change', id, '--enabled', 'false'], deps);
    assert.equal(timers().length, 3, 'the pending wake still needs its note');
    const claim = store.claimNext();
    store.finishRun(claim.runId, claim.nonce, { invocationNonce: claim.nonce, output: '{}', disposition: 'completed' });
    run(['schedules-due', '--now', '2026-10-01T13:00:00Z'], deps);
    assert.equal(timers().length, 2);
    run(['schedule', 'change', id, '--enabled', 'true'], deps);
    assert.match(timers()[2], /Café review/);
    run(['schedule', 'cancel', id], deps);
    assert.equal(store.getSchedule(id), null);
    assert.equal(timers().length, 2);
    const unlinked = run(['schedule', 'add', '--at', '2026-10-01T10:00:00-03:00', '--note', 'Once', '--json'], deps);
    const row = JSON.parse(unlinked.out).schedule;
    assert.equal(row.subject, null);
    assert.equal(timers()[2], `| 2026-10-01 13:00 UTC | ${row.id} | Once | none |`);
    for (const subject of ['', '  ', 'one\ntwo']) {
      assert.throws(() => run(['schedule', 'add', '--every', '1h', '--note', 'x', '--subject', subject], deps), /--subject/);
    }
    assert.equal(store.listSchedules().length, 1);
    assert.match(run(['schedule', 'add', '--help']).out, /--subject <title>/);
  } finally { store.close(); fs.rmSync(home, { recursive: true, force: true }); }
});

test('a schedules-due tick refreshes idle flags even with no due schedules', () => {
  boardFixture(({ home, file, candidate, text, deps }) => {
    const rootTs = `${Date.parse('2026-09-25T12:00:00Z') / 1000}.000000`;
    fs.writeFileSync(candidate, text.replace('Threads: none', `Threads: [review](https://example.slack.com/archives/C1/p${rootTs.replace('.', '')})`), 'utf8');
    run(['board', 'write', '--file', candidate], deps);
    const result = run(['schedules-due', '--now', '2026-10-03T12:00:00Z', '--json'], deps);
    assert.deepEqual(JSON.parse(result.out).results, []);
    assert.equal(parseBoard(fs.readFileSync(file, 'utf8')).subjects[0].flags, 'idle since 2026-09-25');
  });
});

test('remember appends UTF-8 once with thread provenance and leaves learned rules untouched', () => {
  const workspace = tempHome();
  try {
    const home = writeConfig(workspace, 'sample', { C9: 'sample' });
    fs.mkdirSync(path.join(home, 'memory'));
    const learned = path.join(home, 'memory', 'learned.md');
    fs.writeFileSync(learned, '# Learned rules — sample\n', 'utf8');
    const env = { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: 'T1:C9:123.456' };
    const result = run(['remember', 'Café\r\nin the afternoon', '--json'], { env, now: () => Date.parse('2026-10-01T12:00:00Z') });
    const file = path.join(workspace, '.rbtv', 'memory', 'inbox.md');
    assert.equal(result.code, 0);
    assert.equal(result.err, '');
    assert.deepEqual(JSON.parse(result.out), { path: file, appended: true, lines: 1, warning: null });
    assert.equal(fs.readFileSync(file, 'utf8'), '- Café in the afternoon (2026-10-01 · sample/[thread](https://app.slack.com/archives/C9/p123456))\n');
    assert.equal(fs.readFileSync(learned, 'utf8'), '# Learned rules — sample\n');
    assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), false);
    assert.equal(run(['remember', 'Several', 'words'], { env }).out, `remembered in ${file}\n`);
    assert.equal(run(['remember', '--', '--help'], { env }).code, 0);
    assert.match(fs.readFileSync(file, 'utf8'), /- --help /);
  } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
});

test('remember rejects empty normalized text before setup or writes', () => {
  const workspace = tempHome();
  try {
    const home = writeConfig(workspace, 'sample', { C9: 'sample' });
    const memory = path.join(workspace, '.rbtv', 'memory');
    const file = path.join(memory, 'inbox.md');
    const before = '# Inbox\r\n- Keep this (2026-10-01 · sample)\r\n';
    for (const existing of [false, true]) {
      if (existing) {
        fs.mkdirSync(memory);
        fs.writeFileSync(file, before, 'utf8');
      }
      for (const text of [[''], [' \t '], ['\r\n\n\r'], ['\u2028\u2029'], ['', '\r\n', ' \t']]) {
        for (const env of [{}, { RBTV_AGENT_HOME: home }]) {
          const plain = run(['remember', ...text], { env });
          assert.equal(plain.code, 1);
          assert.equal(plain.out, '');
          assert.equal(plain.err, 'remember requires non-empty text\n');
          const json = run(['remember', ...text, '--json'], { env });
          assert.equal(json.code, 1);
          assert.equal(json.err, '');
          assert.deepEqual(JSON.parse(json.out), { path: null, error: 'remember requires non-empty text' });
        }
      }
      if (existing) assert.equal(fs.readFileSync(file, 'utf8'), before);
      else assert.equal(fs.existsSync(memory), false);
      assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), false);
    }
  } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
});

test('remember accepts a real note surrounded by blank arguments and line breaks', () => {
  const workspace = tempHome();
  try {
    const home = writeConfig(workspace, 'sample', { C9: 'sample' });
    const result = run(['remember', '', '\r\nCafé\u2028after lunch\u2029', '\t', '--json'], {
      env: { RBTV_AGENT_HOME: home }, now: () => Date.parse('2026-10-01T12:00:00Z'),
    });
    assert.equal(result.code, 0);
    assert.equal(result.err, '');
    const file = path.join(workspace, '.rbtv', 'memory', 'inbox.md');
    assert.deepEqual(JSON.parse(result.out), { path: file, appended: true, lines: 1, warning: null });
    assert.equal(fs.readFileSync(file, 'utf8'), '- Café after lunch (2026-10-01 · sample)\n');
  } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
});

test('remember never refuses broken or overfull inboxes and queues owner alerts inside or outside a turn', () => {
  const workspace = tempHome();
  try {
    for (const [slug, key] of [['sample', 'T1:C9:1.1'], ['master', null]]) {
      const home = writeConfig(workspace, slug, { C9: 'sample' });
      const store = new Store(path.join(home, 'state.sqlite'));
      try {
        if (key) store.upsertConversation({ key, agent: slug, workspace: 'T1', channel: 'C9', rootTs: '1.1' });
        const file = path.join(workspace, '.rbtv', 'memory', 'inbox.md');
        fs.mkdirSync(path.dirname(file), { recursive: true });
        const before = '# Inbox\r\n\r\n' + '- unfiled broken line\r\n'.repeat(19);
        fs.writeFileSync(file, before, 'utf8');
        const twentieth = run(['remember', 'Twentieth', '--json'], { env: { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: key } });
        assert.equal(JSON.parse(twentieth.out).lines, 20);
        assert.equal(JSON.parse(twentieth.out).warning, null);
        assert.deepEqual(store.pendingOutbox(), []);
        const result = run(['remember', 'x'.repeat(5000), '--json'], { env: { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: key } });
        assert.equal(result.code, 0);
        assert.equal(JSON.parse(result.out).lines, 21);
        assert.match(JSON.parse(result.out).warning, /over 20/);
        assert.ok(fs.readFileSync(file, 'utf8').startsWith(before));
        const [alert] = store.pendingOutbox();
        assert.match(alert.payload.text, /21 bullet lines/);
        if (key) assert.equal(alert.conversation_key, key);
        else assert.equal(alert.payload.imUser, 'UOWNER');
      } finally { store.close(); }
    }
  } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
});

test('remember succeeds after append even if the owner alert cannot be queued', () => {
  const workspace = tempHome();
  try {
    const home = path.join(workspace, '.rbtv', 'agents', 'sample');
    fs.mkdirSync(home, { recursive: true });
    const file = path.join(workspace, '.rbtv', 'memory', 'inbox.md');
    fs.mkdirSync(path.dirname(file));
    fs.writeFileSync(file, '- broken\n'.repeat(20), 'utf8');
    const result = run(['remember', 'Still save this', '--json'], { env: { RBTV_AGENT_HOME: home } });
    assert.equal(result.code, 0);
    assert.match(JSON.parse(result.out).warning, /Owner alert could not be queued/);
    assert.match(fs.readFileSync(file, 'utf8'), /Still save this/);
  } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
});

test('remember help at every position needs no home; failures are structured and leave no append', () => {
  assert.match(run(['remember', '--help']).out, /remember <text>/);
  for (const args of [['--help', 'remember'], ['remember', '--help'], ['remember', 'fact', '-h']]) {
    const result = run(args, { env: {} });
    assert.equal(result.code, 0);
    assert.match(result.out, /one append/);
    assert.match(result.out, /20 bullet lines/);
    assert.match(result.out, /Headings and blanks do not count/);
    assert.equal(result.err, '');
  }
  for (const args of [['remember'], ['remember', 'fact'], ['remember', '--unknown', 'value']]) {
    const result = run([...args, '--json'], { env: {} });
    assert.equal(result.code, 1);
    assert.ok(JSON.parse(result.out).error);
    assert.equal(result.err, '');
  }
});

test('remember executable resolves installation outside cwd and reports real write failures', () => {
  const workspace = tempHome();
  try {
    const home = writeConfig(workspace, 'sample', {});
    const env = { ...process.env, RBTV_AGENT_HOME: home, NODE_NO_WARNINGS: '1' };
    const invoke = (args) => spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), ...args], { cwd: os.tmpdir(), env, encoding: 'utf8' });
    const first = invoke(['remember', 'From elsewhere', '--json']);
    assert.equal(first.status, 0);
    const file = JSON.parse(first.stdout).path;
    assert.equal(file, path.join(workspace, '.rbtv', 'memory', 'inbox.md'));
    assert.equal(first.stderr, '');
    fs.unlinkSync(file);
    fs.mkdirSync(file);
    const failed = invoke(['remember', 'Cannot append', '--json']);
    assert.equal(failed.status, 1);
    assert.ok(JSON.parse(failed.stdout).error);
    assert.equal(failed.stderr, '');
    const plain = invoke(['remember']);
    assert.equal(plain.status, 1);
    assert.equal(plain.stdout, '');
    assert.match(plain.stderr, /requires <text>/);
    fs.rmSync(file, { recursive: true });
    const selected = run(['--agent', 'sample', '--installation', workspace, 'remember', 'Explicit selection'], { env: {} });
    assert.equal(selected.code, 0);
    assert.match(fs.readFileSync(file, 'utf8'), /Explicit selection/);
  } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
});

for (const state of ['deleted', 'invalid']) {
  for (const args of [['add', '--every', '1h', '--note', 'New'], ['change', 'existing', '--note', 'Changed'], ['cancel', 'existing']]) {
    test(`${state} board refuses schedule ${args[0]} with SQLite unchanged`, () => {
      const home = tempHome();
      const db = path.join(home, 'state.sqlite');
      const file = boardPath(home);
      try {
        const store = new Store(db);
        try {
          store.upsertConversation({ key: 'k', agent: 'sample', workspace: 'T1', channel: 'C1' });
          store.upsertSchedule({ id: 'existing', conversationKey: 'k', cadence: 'every:1h', timezone: 'fixed', nextAt: 1000, note: 'Original' });
        } finally { store.close(); }
        fs.mkdirSync(path.dirname(file));
        fs.writeFileSync(file, EMPTY_BOARD, 'utf8');
        fs.writeFileSync(path.join(home, 'board.md'), EMPTY_BOARD, 'utf8');
        if (state === 'deleted') fs.unlinkSync(file);
        else fs.writeFileSync(file, 'invalid board café\r\n', 'utf8');
        const before = fs.readFileSync(db);
        const result = spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), 'schedule', ...args], {
          cwd: os.tmpdir(), encoding: 'utf8',
          env: { ...process.env, RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: 'k', NODE_NO_WARNINGS: '1' },
        });
        assert.equal(result.status, 1, result.stderr);
        assert.equal(result.stdout, '');
        assert.ok(result.stderr.startsWith(`board refused: ${file}: `));
        if (state === 'deleted') assert.equal(result.stderr, `board refused: ${file}: board is missing\n`);
        assert.deepEqual(fs.readFileSync(db), before);
        assert.deepEqual(fs.readdirSync(home).filter((name) => name.startsWith('state.sqlite')), ['state.sqlite']);
        if (state === 'deleted') assert.equal(fs.existsSync(file), false);
        else assert.equal(fs.readFileSync(file, 'utf8'), 'invalid board café\r\n');
      } finally { fs.rmSync(home, { recursive: true, force: true }); }
    });
  }

  test(`${state} board refuses schedule mutations before database creation`, () => {
    const home = tempHome();
    try {
      const file = boardPath(home);
      fs.mkdirSync(path.dirname(file));
      fs.writeFileSync(file, EMPTY_BOARD, 'utf8');
      if (state === 'deleted') fs.unlinkSync(file);
      else fs.writeFileSync(file, 'invalid', 'utf8');
      for (const args of [['add', '--every', '1h', '--note', 'New'], ['change', 'existing', '--note', 'Changed'], ['cancel', 'existing']]) {
        assert.throws(() => run(['schedule', ...args], { env: { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: 'k' } }),
          (error) => error.message.startsWith(`board refused: ${file}: `));
        assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), false);
      }
    } finally { fs.rmSync(home, { recursive: true, force: true }); }
  });
}

for (const json of [false, true]) {
  for (const action of ['add', 'change', 'cancel']) test(`schedule ${action} reports committed with refresh pending in ${json ? 'JSON' : 'text'} mode`, () => {
    boardFixture(({ home, file, candidate, text, deps }) => {
      run(['board', 'write', '--file', candidate], deps);
      const store = new Store(path.join(home, 'state.sqlite'));
      const method = action === 'cancel' ? 'deleteSchedule' : 'upsertSchedule';
      const original = Store.prototype[method];
      let release;
      try {
        store.upsertConversation({ key: 'k', agent: 'sample', workspace: 'T1', channel: 'C1' });
        if (action !== 'add') store.upsertSchedule({ id: 'existing', conversationKey: 'k', cadence: 'every:1h', timezone: 'fixed', nextAt: 1000, note: 'Original' });
        // This runs after preflight and SQLite commit, before the board refresh.
        Store.prototype[method] = function (...args) {
          const result = original.apply(this, args);
          if (json) release = acquireMemoryLock(writeRoot(file));
          else fs.writeFileSync(file, 'changed to invalid after preflight', 'utf8');
          return result;
        };
        const args = action === 'add' ? ['add', '--every', '1h', '--note', 'Changed']
          : action === 'change' ? ['change', 'existing', '--note', 'Changed'] : ['cancel', 'existing'];
        const result = run(['schedule', ...args, ...(json ? ['--json'] : [])], {
          ...deps, env: { ...deps.env, IGNITE_CONVERSATION: 'k' },
        });
        assert.equal(result.code, 0);
        assert.equal(result.err, '');
        const rows = store.listSchedules();
        assert.equal(rows.length, action === 'cancel' ? 0 : 1);
        const id = action === 'cancel' ? 'existing' : rows[0].id;
        if (action !== 'cancel') assert.equal(rows[0].note, 'Changed');
        const warning = `${id} committed; board refresh pending`;
        if (json) {
          const body = JSON.parse(result.out);
          assert.equal(body.warning, warning);
          assert.equal(action === 'cancel' ? body.cancelled : body.schedule.id, id);
          assert.equal(body.error, undefined);
          assert.equal(fs.readFileSync(file, 'utf8'), text);
        } else assert.ok(result.out.includes(warning));
        if (release) { release(); release = null; }
        Store.prototype[method] = original;
        if (!json) fs.writeFileSync(file, text, 'utf8');
        // The next board write/close refreshes from committed schedules without a retry.
        const refreshed = run(action === 'change'
          ? ['board', 'close', 'Printer toner reorder', 'Done']
          : ['board', 'write', '--file', candidate], deps);
        assert.equal(refreshed.code, 0, refreshed.err);
        const timers = parseBoard(fs.readFileSync(file, 'utf8')).timers;
        assert.equal(timers.length, action === 'cancel' ? 2 : 3);
        if (action !== 'cancel') assert.ok(timers[2].includes(`| ${id} | Changed |`));
      } finally {
        Store.prototype[method] = original;
        if (release) release();
        store.close();
      }
    });
  });
}

test('schedule executable exits zero after commit when a competing holder blocks board refresh', () => {
  const workspace = tempHome();
  const home = path.join(workspace, '.rbtv', 'agents', 'sample');
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  const release = acquireMemoryLock(workspace);
  try {
    store.upsertConversation({ key: 'k', agent: 'sample', workspace: 'T1', channel: 'C1' });
    const result = spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), 'schedule', 'add', '--every', '1h', '--note', 'Check', '--json'], {
      cwd: workspace, encoding: 'utf8', env: { ...process.env, RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: 'k' }, timeout: 10_000,
    });
    assert.equal(result.status, 0, result.stderr);
    assert.doesNotMatch(result.stderr, /lock busy/);
    const [row] = store.listSchedules();
    assert.equal(store.listSchedules().length, 1);
    const body = JSON.parse(result.stdout);
    assert.equal(body.schedule.id, row.id);
    assert.equal(body.warning, `${row.id} committed; board refresh pending`);
  } finally { release(); store.close(); fs.rmSync(workspace, { recursive: true, force: true }); }
});

test('board commands ignore an invalid legacy board after canonical deletion', () => {
  const home = tempHome();
  try {
    fs.writeFileSync(path.join(home, 'board.md'), 'invalid legacy board', 'utf8');
    const candidate = path.join(home, 'candidate.md');
    fs.writeFileSync(candidate, EMPTY_BOARD, 'utf8');
    const result = run(['board', 'write', '--file', candidate], { env: { RBTV_AGENT_HOME: home } });
    assert.equal(result.code, 0, result.err);
    assert.equal(fs.readFileSync(boardPath(home), 'utf8'), EMPTY_BOARD);
    assert.equal(fs.readFileSync(path.join(home, 'board.md'), 'utf8'), 'invalid legacy board');
  } finally { fs.rmSync(home, { recursive: true, force: true }); }
});

async function runAsync(argv, extra = {}) {
  const out = [];
  const err = [];
  const code = await main(argv, {
    stdout: (text) => out.push(text),
    stderr: (text) => err.push(text),
    ...extra,
  });
  return { code, out: out.join(''), err: err.join('') };
}

const DREAMER_TEST_MODEL = Object.freeze({ harness: 'claude', model: 'example-model', effort: 2 });
const OWNER_WORDING = 'Enable and disable affect automatic Dreamer operation for the entire installation, not only the calling agent. ' +
  'Agents must use these commands only when explicitly requested by the owner. ' +
  'Do not disable Dreamer as a workaround for an individual agent\'s problem.';

// model null leaves dreamer.model out of the file.
// updateConfig writes by rename, so any write gives the file a new inode.
function configIdentity(file) {
  const { ino, mtimeMs } = fs.statSync(file);
  return { ino, mtimeMs };
}

function dreamerInstall(enabled = false, model = DREAMER_TEST_MODEL) {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-dreamer-cli-')));
  const home = writeConfig(dir, 'master', {});
  const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
  const config = JSON.parse(fs.readFileSync(file, 'utf8'));
  config.dreamer = model ? { enabled, model } : { enabled };
  fs.writeFileSync(file, JSON.stringify(config));
  fs.mkdirSync(path.join(dir, '.rbtv', 'memory'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'inbox.md'), '# Inbox — waiting to be filed\n', 'utf8');
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  store.close();
  return { dir, home };
}

function addOwner(home) {
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    store.upsertConversation({ key: 'T1:D1:1.000000', agent: 'master', workspace: 'T1', channel: 'D1', rootTs: '1.000000' });
    store.recordMessage('T1:D1:1.000000', {
      id: 'owner-1', role: 'owner', text: 'Please remember this.', metadata: { source: 'slack' },
    });
  } finally { store.close(); }
}

async function testAsync(name, fn) {
  try {
    await fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  }
}

async function finishCli() {
  await testAsync('dreamer help needs no home, carries the owner wording at every verb and rejects a missing or unknown verb', async () => {
    const help = await runAsync(['dreamer', '--help']);
    assert.equal(help.code, 0);
    for (const argv of [['dreamer', '-h'], ['dreamer', 'status', '-h'], ['-h', 'dreamer']]) {
      const page = await runAsync(argv);
      assert.equal(page.code, 0);
      assert.equal(page.out, help.out);
    }
    assert.doesNotMatch(help.out, /usage:/);
    assert.doesNotMatch(help.out, /dreamer status/);
    const pages = {};
    for (const verb of ['run', 'enable', 'disable']) {
      assert.match(help.out, new RegExp(`^ {2}${verb} +\\S`, 'm'));
      for (const argv of [['dreamer', verb, '-h'], ['dreamer', verb, '--help'], ['-h', 'dreamer', verb], ['dreamer', verb, '--installation', '/x', '-h']]) {
        const page = await runAsync(argv);
        assert.equal(page.code, 0);
        pages[verb] = pages[verb] || page.out;
        assert.equal(page.out, pages[verb]);
      }
      assert.match(pages[verb], new RegExp(`^usage: ignite dreamer ${verb} \\[--installation PATH\\]`, 'm'));
    }
    assert.ok(help.out.replace(/\s+/g, ' ').includes(OWNER_WORDING));
    assert.match(pages.enable, /^usage: ignite dreamer enable \[--installation PATH\] \[--json\]/m);
    assert.match(pages.disable, /^usage: ignite dreamer disable \[--installation PATH\] \[--json\]/m);
    assert.match(pages.disable, /A consolidation already in\s+progress is not cancelled/);
    assert.match(pages.enable, /records codex gpt-6\.1-sol effort 3/);
    const top = run(['-h']).out;
    assert.match(top, /dreamer +Run one memory consolidation, or enable or disable the\n +nightly consolidation for the whole installation\./);
    assert.match(pages.run, /dreamer.enabled is false/);
    assert.match(pages.run, /snapshot reads and publication/);
    assert.match(pages.run, /Releases it before every model call/);
    assert.match(pages.run, /digestQueued/);
    assert.match(pages.run, /noticeQueued/);
    for (const argv of [['dreamer'], ['dreamer', 'status'], ['dreamer', 'enable', 'master'], ['dreamer', 'run', 'now']]) {
      await assert.rejects(() => runAsync(argv), /dreamer requires exactly one of run, enable, disable\nNothing changed\.\nignite dreamer -h/);
    }
    for (const argv of [['dreamer', 'enable', '--bogus'], ['dreamer', 'disable', '--bogus'], ['dreamer', 'run', '--bogus'], ['dreamer', '--bogus', 'enable']]) {
      await assert.rejects(() => runAsync(argv), /^Error: '--bogus' is not a dreamer option\nNothing changed\.\nignite dreamer -h$/);
    }
  });

  await testAsync('dreamer enable records the model, preserves every other setting and repeats without writing', async () => {
    const { dir } = dreamerInstall(false, null);
    const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
    const before = JSON.parse(fs.readFileSync(file, 'utf8'));
    before.routes = { C1: 'master', C2: 'other-agent' };
    fs.writeFileSync(file, JSON.stringify(before));
    try {
      const first = await runAsync(['dreamer', 'enable', '--installation', dir]);
      assert.equal(first.code, 0); assert.equal(first.err, '');
      const after = JSON.parse(fs.readFileSync(file, 'utf8'));
      assert.deepEqual(after.dreamer, { enabled: true, model: { harness: 'codex', model: 'gpt-6.1-sol', effort: 3 } });
      assert.deepEqual({ ...after, dreamer: null }, { ...before, dreamer: null });
      assert.match(first.out, /^Dreamer enabled for the entire installation .*, not only the calling agent\.\n/);
      assert.match(first.out, /Model: codex gpt-6\.1-sol effort 3 \(recorded now in dreamer\.model\)\./);
      assert.ok(first.out.includes(`To use another model, edit dreamer.model in ${file}.`));
      const written = configIdentity(file);
      const again = await runAsync(['dreamer', 'enable', '--installation', dir]);
      assert.equal(again.code, 0);
      assert.match(again.out, /^Dreamer was already enabled for the entire installation .*\. Nothing changed\.\n/);
      assert.match(again.out, /Model: codex gpt-6\.1-sol effort 3 \(from dreamer\.model\)\./);
      assert.deepEqual(configIdentity(file), written);
      const json = JSON.parse((await runAsync(['dreamer', 'enable', '--installation', dir, '--json'])).out);
      assert.deepEqual(json, { installation: dir, config: file, enabled: true, changed: false,
        model: { harness: 'codex', model: 'gpt-6.1-sol', effort: 3 }, modelRecorded: false });
      assert.deepEqual(configIdentity(file), written);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });

  await testAsync('dreamer enable keeps a model already in the file', async () => {
    const { dir } = dreamerInstall(false);
    const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
    try {
      const result = JSON.parse((await runAsync(['--json', 'dreamer', 'enable', '--installation', dir])).out);
      assert.deepEqual(result, { installation: dir, config: file, enabled: true, changed: true, model: { ...DREAMER_TEST_MODEL }, modelRecorded: false });
      assert.deepEqual(JSON.parse(fs.readFileSync(file, 'utf8')).dreamer, { enabled: true, model: { ...DREAMER_TEST_MODEL } });
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });

  await testAsync('dreamer disable keeps the model and every other setting, says a run in progress continues, and repeats without writing', async () => {
    const { dir } = dreamerInstall(true);
    const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
    const before = JSON.parse(fs.readFileSync(file, 'utf8'));
    try {
      const first = await runAsync(['dreamer', 'disable', '--installation', dir]);
      assert.equal(first.code, 0); assert.equal(first.err, '');
      assert.deepEqual(JSON.parse(fs.readFileSync(file, 'utf8')), { ...before, dreamer: { enabled: false, model: { ...DREAMER_TEST_MODEL } } });
      assert.match(first.out, /^Dreamer disabled for the entire installation .*, not only the calling agent\.\n/);
      assert.match(first.out, /A consolidation already in progress is not cancelled\./);
      assert.match(first.out, /Model: claude example-model effort 2 \(from dreamer\.model, kept\)\./);
      const written = configIdentity(file);
      const again = await runAsync(['dreamer', 'disable', '--installation', dir]);
      assert.equal(again.code, 0);
      assert.match(again.out, /^Dreamer was already disabled for the entire installation .*\. Nothing changed\.\n/);
      assert.deepEqual(configIdentity(file), written);
      const json = JSON.parse((await runAsync(['dreamer', 'disable', '--installation', dir, '--json'])).out);
      assert.deepEqual(json, { installation: dir, config: file, enabled: false, changed: false, model: { ...DREAMER_TEST_MODEL }, modelRecorded: false });
      assert.deepEqual(configIdentity(file), written);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });

  await testAsync('dreamer enable and disable refuse an invalid configuration and write nothing', async () => {
    for (const text of ['{}\n', 'not json\n', JSON.stringify({ dreamer: { enabled: 'yes' } })]) for (const verb of ['enable', 'disable']) {
      const { dir } = dreamerInstall(false);
      const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
      fs.writeFileSync(file, text, 'utf8');
      try {
        await assert.rejects(() => runAsync(['dreamer', verb, '--installation', dir]), /\nNothing changed\.\nignite dreamer -h$/);
        assert.equal(fs.readFileSync(file, 'utf8'), text);
      } finally { fs.rmSync(dir, { recursive: true, force: true }); }
    }
    const { dir } = dreamerInstall(true, null);
    const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
    const text = fs.readFileSync(file, 'utf8');
    try {
      for (const verb of ['enable', 'disable']) {
        await assert.rejects(() => runAsync(['dreamer', verb, '--installation', dir]), /dreamer\.model required when dreamer\.enabled is true: add "model": \{"harness":"codex"/);
        assert.equal(fs.readFileSync(file, 'utf8'), text);
      }
      const missing = path.join(dir, 'missing installation');
      const result = spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), 'dreamer', 'enable', '--json', '--installation', missing], {
        encoding: 'utf8', env: { ...process.env, RBTV_AGENT_HOME: '', NODE_NO_WARNINGS: '1' },
      });
      assert.equal(result.status, 1); assert.equal(result.stdout, '');
      assert.match(result.stderr, /^cannot load Ignite config: .*\nNothing changed\.\nignite dreamer -h\n$/);
      assert.equal(fs.existsSync(missing), false);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });

  await testAsync('dreamer run without dreamer.model is refused before any run, naming the key', async () => {
    const daemon = require('./daemon.js');
    const original = daemon.runInstalledDreamer;
    daemon.runInstalledDreamer = async () => { throw new Error('must not run'); };
    const disabled = dreamerInstall(false, null);
    const enabled = dreamerInstall(true, null);
    try {
      const off = JSON.parse((await runAsync(['--installation', disabled.dir, 'dreamer', 'run'])).out);
      assert.equal(off.ok, false); assert.equal(off.enabled, false); assert.equal(off.note, null);
      assert.match(off.error, /^dreamer\.model required to run a consolidation: add "model": \{"harness":"codex","model":"gpt-6\.1-sol","effort":3\} under "dreamer"/);
      const on = await runAsync(['--installation', enabled.dir, 'dreamer', 'run']);
      assert.equal(on.code, 1); assert.equal(JSON.parse(on.out).enabled, null);
      assert.match(JSON.parse(on.out).error, /dreamer\.model required when dreamer\.enabled is true/);
    } finally {
      daemon.runInstalledDreamer = original;
      fs.rmSync(disabled.dir, { recursive: true, force: true });
      fs.rmSync(enabled.dir, { recursive: true, force: true });
    }
  });

  await testAsync('dreamer run uses the shared nightly function and says when dreamer is disabled', async () => {
    const daemon = require('./daemon.js');
    const original = daemon.runInstalledDreamer;
    let calls = 0;
    daemon.runInstalledDreamer = async (opts) => {
      calls += 1;
      assert.equal(opts.config.dmAgent, 'master');
      assert.equal(opts.slack, undefined);
      return { ok: true, busy: false, quiet: true, changed: false, alert: null, digestQueued: false, noticeQueued: false, delivered: false, conflictsSaved: false, error: null };
    };
    const disabled = dreamerInstall(false);
    const enabled = dreamerInstall(true);
    try {
      const off = await runAsync(['--installation', disabled.dir, 'dreamer', 'run']);
      assert.equal(calls, 1);
      assert.equal(off.code, 0, off.err);
      assert.equal(off.out.split('\n').length, 2);
      const offBody = JSON.parse(off.out);
      assert.equal(offBody.enabled, false);
      assert.match(offBody.note, /dreamer.enabled is false; ran because this command was called/);
      const on = await runAsync(['--installation', enabled.dir, 'dreamer', 'run']);
      assert.equal(calls, 2);
      assert.equal(JSON.parse(on.out).note, null);
      assert.equal(JSON.parse(on.out).enabled, true);
      for (const { dir } of [disabled, enabled]) {
        const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
        assert.equal(JSON.parse(fs.readFileSync(file, 'utf8')).dreamer.enabled, dir === enabled.dir);
      }
    } finally {
      daemon.runInstalledDreamer = original;
      fs.rmSync(disabled.dir, { recursive: true, force: true });
      fs.rmSync(enabled.dir, { recursive: true, force: true });
    }
  });

  await testAsync('dreamer run queues the digest and leaves unconfirmed conflicts unsaved', async () => {
    const { dir, home } = dreamerInstall(false);
    addOwner(home);
    try {
      const result = await runAsync(['--installation', dir, 'dreamer', 'run'], {
        now: () => Date.parse('2026-10-01T12:00:00Z'),
        runDreamer: async () => ({
          ok: true, changed: true, alert: null,
          digest: { text: 'Memory consolidation\nFiled the note.', conflicts: ['Clarify the preference.'] },
        }),
      });
      assert.equal(result.code, 0, result.err + result.out);
      assert.equal(result.out.split('\n').length, 2);
      const body = JSON.parse(result.out);
      assert.equal(body.enabled, false);
      assert.match(body.note, /dreamer.enabled is false/);
      assert.equal(body.digestQueued, true);
      assert.equal(body.noticeQueued, false);
      assert.equal(body.delivered, false);
      assert.equal(body.conflictsSaved, false);
      assert.equal(body.busy, false);
      const store = new Store(path.join(home, 'state.sqlite'));
      try {
        const pending = store.pendingOutbox();
        assert.equal(pending.length, 1);
        assert.match(pending[0].payload.text, /^Memory consolidation\nFiled the note\./);
        assert.equal(getState(store).reportedConflicts, undefined);
        assert.equal(store.db.prepare("SELECT value FROM settings WHERE key='dreamer_enabled_at'").get(), undefined);
        assert.equal(store.db.prepare("SELECT value FROM settings WHERE key='dreamer_slot'").get(), undefined);
      } finally { store.close(); }
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });

  await testAsync('dreamer run reports a queued failure notice separately from a digest', async () => {
    const { dir, home } = dreamerInstall(false);
    addOwner(home);
    try {
      const result = await runAsync(['--installation', dir, 'dreamer', 'run'], {
        runDreamer: async () => ({ ok: false, changed: false, digest: null, alert: 'Dreamer failed: model failed: Insufficient credits.' }),
      });
      assert.equal(result.code, 1); assert.equal(result.err, '');
      assert.equal(result.out.split('\n').length, 2);
      const body = JSON.parse(result.out);
      assert.equal(body.digestQueued, false); assert.equal(body.noticeQueued, true);
      assert.equal(body.delivered, false); assert.equal(body.conflictsSaved, false);
      const store = new Store(path.join(home, 'state.sqlite'));
      try { assert.equal(store.pendingOutbox()[0].payload.text, `Memory alert: ${body.alert}`); }
      finally { store.close(); }
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });

  await testAsync('dreamer cap refusal JSON includes the file and proposed size without content', async () => {
    const { dir, home } = dreamerInstall(false);
    addOwner(home);
    const name = '.rbtv/memory/knowledge/facts.md';
    const text = '---\ndescription: when reviewing facts\ntype: facts\naliases: []\n---\n# Facts\n' + 'private-fixture-content'.repeat(200);
    try {
      fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'profile.md'), '# Profile — Sam\n\n## Who\n\n## Working with Sam\n\n## Now\n', 'utf8');
      fs.mkdirSync(path.join(home, 'memory'), { recursive: true });
      fs.writeFileSync(path.join(home, 'memory', 'learned.md'), '# Learned rules — master\n', 'utf8');
      const output = { conflicts: [], operations: [{ op: 'add', path: name, text,
        sources: [1], reason: 'owner', explanation: 'private-fixture-explanation' }] };
      const cast = path.join(dir, 'fake cast.js');
      fs.writeFileSync(cast, `process.stdout.write(${JSON.stringify(JSON.stringify(output))});\n`, 'utf8');
      const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
      const config = JSON.parse(fs.readFileSync(file, 'utf8')); config.tools.cast = cast;
      fs.writeFileSync(file, JSON.stringify(config), 'utf8');
      const result = await runAsync(['--installation', dir, 'dreamer', 'run']);
      assert.equal(result.code, 1); assert.equal(result.err, '');
      assert.equal(result.out.split('\n').length, 2);
      const body = JSON.parse(result.out);
      assert.equal(body.alert, `Dreamer failed: ${name}: knowledge cap exceeded (${[...text].length}/3000 characters).`);
      assert.equal(body.ok, false); assert.equal(body.changed, false);
      assert.equal(body.noticeQueued, true); assert.equal(body.digestQueued, false);
      assert.equal(result.out.includes('private-fixture'), false);
      assert.equal(fs.existsSync(path.join(dir, name)), false);
      const store = new Store(path.join(home, 'state.sqlite'));
      try {
        assert.equal(store.pendingOutbox()[0].payload.text, `Memory alert: ${body.alert}`);
        assert.equal(getState(store).cursor, 0);
      } finally { store.close(); }
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });

  await testAsync('quiet dreamer run reports neither a digest nor a notice queued', async () => {
    const { dir } = dreamerInstall(false);
    try {
      const result = await runAsync(['--installation', dir, 'dreamer', 'run']);
      const body = JSON.parse(result.out);
      assert.equal(result.code, 0); assert.equal(body.quiet, true);
      assert.equal(body.digestQueued, false); assert.equal(body.noticeQueued, false);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });

  await testAsync('dreamer run returns busy when the installation lock is held', async () => {
    const { dir, home } = dreamerInstall(false);
    const previous = Date.parse('2026-10-01T00:00:00Z');
    const store = new Store(path.join(home, 'state.sqlite'));
    store.db.prepare("INSERT INTO settings(key, value, updated_at) VALUES ('dreamer', ?, ?)")
      .run(JSON.stringify({ cursor: 0, lastSuccessAt: previous, commit: null }), previous);
    store.close();
    const release = acquireMemoryLock(dir);
    try {
      const result = await runAsync(['--installation', dir, 'dreamer', 'run'], {
        runDreamer: async () => { throw new Error('must not run'); },
      });
      assert.equal(result.code, 1);
      assert.equal(result.out.split('\n').length, 2);
      const body = JSON.parse(result.out);
      assert.equal(body.busy, true);
      assert.equal(body.digestQueued, false);
      assert.equal(body.noticeQueued, false);
      assert.equal(body.ok, false);
      assert.match(body.error, /lock busy/);
      assert.match(body.note, /dreamer.enabled is false/);
      const after = new Store(path.join(home, 'state.sqlite'));
      try {
        assert.equal(after.pendingOutbox().length, 0);
        assert.equal(getState(after).lastSuccessAt, previous);
      } finally { after.close(); }
    } finally {
      release();
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  for (const missing of ['dmAgent', 'DM store']) for (const notice of ['digest', 'failure']) {
    await testAsync(`dreamer run fails when ${notice} cannot be queued without ${missing}`, async () => {
      const { dir, home } = dreamerInstall(false);
      fs.appendFileSync(path.join(dir, '.rbtv', 'memory', 'inbox.md'), '- Prefers café. (2026-10-01 · master)\n', 'utf8');
      if (missing === 'dmAgent') {
        const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
        const config = JSON.parse(fs.readFileSync(file, 'utf8'));
        delete config.dmAgent;
        fs.writeFileSync(file, JSON.stringify(config), 'utf8');
      } else {
        fs.rmSync(home, { recursive: true, force: true });
      }
      let calls = 0;
      try {
        const result = await runAsync(['--installation', dir, 'dreamer', 'run'], {
          runDreamer: async () => {
            calls++;
            return notice === 'digest'
              ? { ok: true, changed: true, digest: { text: 'Memory consolidation' }, alert: null }
              : { ok: false, changed: false, digest: null, alert: 'Dreamer failed.' };
          },
        });
        assert.equal(calls, 1);
        assert.equal(result.code, 1);
        assert.equal(result.out.split('\n').length, 2);
        assert.equal(result.err, '');
        const body = JSON.parse(result.out);
        assert.equal(body.ok, false);
        assert.equal(body.busy, false);
        assert.equal(body.changed, notice === 'digest');
        assert.equal(body.digestQueued, false);
        assert.equal(body.noticeQueued, false);
        assert.equal(body.delivered, false);
        assert.equal(body.conflictsSaved, false);
        assert.match(body.error, missing === 'dmAgent' ? /requires config\.dmAgent/ : /direct-message agent missing/);
        assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'runtime', 'ignite', 'memory.lock')), false);
      } finally { fs.rmSync(dir, { recursive: true, force: true }); }
    });
  }

  for (const failure of ['workspace', 'config', 'lock']) {
    await testAsync(`dreamer run emits one JSON failure line for invalid ${failure}`, async () => {
      const { dir } = dreamerInstall(false);
      const target = failure === 'workspace' ? path.join(dir, 'missing workspace') : dir;
      if (failure === 'config') {
        fs.writeFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), '{}\r\n', 'utf8');
      } else if (failure === 'lock') {
        fs.writeFileSync(path.join(dir, '.rbtv', 'runtime'), 'not a directory\n', 'utf8');
      }
      try {
        const result = spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), 'dreamer', 'run', '--installation', target], {
          encoding: 'utf8', env: { ...process.env, RBTV_AGENT_HOME: '', NODE_NO_WARNINGS: '1' },
        });
        assert.equal(result.status, 1);
        assert.equal(result.stdout.split('\n').length, 2);
        assert.equal(result.stderr, '');
        const body = JSON.parse(result.stdout);
        assert.equal(body.ok, false);
        assert.equal(body.busy, false);
        assert.equal(body.digestQueued, false);
        assert.equal(body.noticeQueued, false);
        assert.equal(body.enabled, failure === 'lock' ? false : null);
        assert.ok(body.error);
      } finally { fs.rmSync(dir, { recursive: true, force: true }); }
    });
  }

  if (failures.length) {
    console.log(`${failures.length} failed`);
    process.exit(1);
  }
  console.log('ok');
}

finishCli();
