#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { main, VERBS } = require('./cli.js');
const { PAGES } = require('./help.js');
const { nextCron, FIXED_TZ } = require('./schedule.js');
const { EMPTY_BOARD, parseBoard, boardPath, boardRevision } = require('./board.js');
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  store.upsertConversation({ key: 'T1:C1:1.1', agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.close();
  const from = Date.parse('2026-03-08T01:30:00-05:00');
  const added = run([
    'schedule', 'add', '--every', '90m', '--note', 'interval', '--conversation', 'T1:C1:1.1',
  ], { env: { RBTV_AGENT_HOME: home }, now: () => from });
  assert.equal(added.code, 0);
  const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const mid = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const end = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const check = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  // The DM agent's channel is the owner's direct conversation, a contact: a new thread there goes through
  // the message port command (connector architecture, phase 2); --thread into a held conversation stays.
  assert.throws(() => run(['post', '--text', 'dm note', '--audio'], { env: { RBTV_AGENT_HOME: dmHome } }),
    /post refused: this agent's channel is the owner's direct conversation, a contact; use message send --to UOWNER --via slack TEXT\. Nothing changed\.$/);
  const dmStore = new Store(path.join(dmHome, 'runtime', 'ignite', 'state.sqlite'));
  try {
    assert.equal(dmStore.pendingOutbox().length, 0);
  } finally {
    dmStore.close();
  }
});

test('post --thread selects stored channel and DM history without opening a new conversation', () => {
  const workspace = tempHome();
  try {
    for (const [slug, channel] of [['sample', 'C9'], ['master', 'D1']]) {
      const home = writeConfig(workspace, slug, { C9: 'sample' });
      const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
    const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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

// Runs each refusal twice from the real executable: against a home with a database, then against
// a home with none. Every file under the installation must stay byte-identical. A case is
// [message, args, env]: message and env may be functions of the installation folder, CANDIDATE in
// args is a valid board candidate file, WORKSPACE the installation folder, and env overrides the
// environment. No case may create the agent folder "ghost".
function refusals(name, cases) {
  test(name, () => {
    const workspace = tempHome();
    try {
      const home = writeConfig(workspace, 'sample', { C1: 'sample' });
      fs.mkdirSync(path.dirname(boardPath(home)));
      fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
      const candidate = path.join(workspace, 'candidate.md');
      fs.writeFileSync(candidate, EMPTY_BOARD, 'utf8');
      const db = path.join(home, 'runtime', 'ignite', 'state.sqlite');
      const store = new Store(db);
      store.upsertConversation({ key: OPTION_KEY, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
      store.upsertSchedule({ id: 'existing', conversationKey: OPTION_KEY, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: 1000, note: 'Original' });
      store.close();
      const env = { ...process.env, RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: OPTION_KEY, NODE_NO_WARNINGS: '1' };
      const invoke = (args, extra) => spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), ...args], { cwd: workspace, env: { ...env, ...(typeof extra === 'function' ? extra(workspace) : extra) }, encoding: 'utf8' });
      for (const withDatabase of [true, false]) {
        if (!withDatabase) fs.rmSync(db);
        const before = filesUnder(workspace);
        for (const [message, args, extra] of cases) {
          const label = `${args.map((arg) => JSON.stringify(arg)).join(' ')} (${withDatabase ? 'database' : 'no database'})`;
          const result = invoke(args.map((arg) => ({ CANDIDATE: candidate, WORKSPACE: workspace }[arg] ?? arg)), extra);
          assert.equal(result.stderr, `${typeof message === 'function' ? message(workspace) : message}\n`, label);
          assert.equal(result.status, 1, label);
          assert.equal(result.stdout, '', label);
          assert.deepEqual(filesUnder(workspace), before, label);
          assert.equal(fs.existsSync(ghostHome(workspace)), false, label);
        }
      }
    } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
  });
}

function ghostHome(workspace) {
  return path.join(workspace, '.rbtv', 'agents', 'ghost');
}

function optionRefusals(group, cases) {
  refusals(`${group} refuses an option the verb does not have and writes nothing`,
    cases.map(([verb, option, args]) => [`'${option}' is not a ${verb} option\nNothing changed.\nignite ${verb} -h`, args]));
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
  for (const [verb, { options }] of Object.entries(VERBS)) {
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

test('each verb takes exactly the positional words its help page names', () => {
  for (const [verb, { words }] of Object.entries(VERBS)) {
    if (verb === 'remember') {
      assert.equal(words, Infinity);
      continue;
    }
    const usage = PAGES[verb].match(/^usage: [^]*?\n\n/m)[0];
    assert.equal(words, [...usage.matchAll(/(?<!--[a-z-]+) \[?<[a-z]+>| \[thread\]/g)].length, verb);
  }
});

const emptyValue = (option, help) => `${option} requires a value that is not empty or only spaces\nNothing changed.\n${help}`;

refusals('an option given an empty value is refused and writes nothing', [
  [emptyValue('--tz', 'ignite schedule add -h'), ['schedule', 'add', '--every', '1h', '--note', 'n', '--tz', '']],
  [emptyValue('--tz', 'ignite schedule change -h'), ['schedule', 'change', 'existing', '--tz', '']],
  [emptyValue('--conversation', 'ignite schedule add -h'), ['schedule', 'add', '--every', '1h', '--note', 'n', '--conversation', '']],
  [emptyValue('--note', 'ignite wake -h'), ['wake', '--conversation', OPTION_KEY, '--note', '  ']],
  [emptyValue('--work', 'ignite wake -h'), ['wake', '--conversation', OPTION_KEY, '--note', 'n', '--work', '']],
  [emptyValue('--conversation', 'ignite work status -h'), ['work', 'status', '--conversation', '']],
  [emptyValue('--text', 'ignite post -h'), ['post', '--file', 'CANDIDATE', '--text', '']],
  [emptyValue('--text-file', 'ignite post -h'), ['post', '--text', 'hi', '--text-file', '']],
  [emptyValue('--file', 'ignite post -h'), ['post', '--text', 'hi', '--file', '']],
  [emptyValue('--agent', 'ignite -h'), ['schedule', 'list', '--agent', '']],
  [emptyValue('--installation', 'ignite -h'), ['schedule', 'list', '--installation', '  ']],
  ...Object.entries(VERBS).flatMap(([verb, { options }]) => options.filter((option) => option !== 'audio')
    .flatMap((option) => ['', '  ', '\t'].map((value) => [emptyValue(`--${option}`, `ignite ${verb} -h`), [...verb.split(' '), `--${option}`, value]]))),
]);

refusals('a positional word beyond those a verb takes is refused and writes nothing', [
  ["unexpected word 'extra': schedule cancel takes at most 1 positional word\nNothing changed.\nignite schedule cancel -h", ['schedule', 'cancel', 'existing', 'extra']],
  ["unexpected word 'extra': schedule list takes no positional words\nNothing changed.\nignite schedule list -h", ['schedule', 'list', 'extra']],
  ["unexpected word 'extra': work stop takes at most 1 positional word\nNothing changed.\nignite work stop -h", ['work', 'stop', 'existing', 'extra']],
  ["unexpected word 'extra': board close takes at most 3 positional words\nNothing changed.\nignite board close -h", ['board', 'close', 'Subject', 'Outcome', '[t](https://example.com/t)', 'extra']],
  ["unexpected word 'extra': board write takes no positional words\nNothing changed.\nignite board write -h", ['board', 'write', '--file', 'CANDIDATE', 'extra']],
  ["unexpected word '-x': schedule list takes no positional words\nNothing changed.\nignite schedule list -h", ['schedule', 'list', '--', '-x']],
  ...Object.entries(VERBS).filter(([, { words }]) => Number.isFinite(words)).map(([verb, { words }]) => [
    `unexpected word 'extra': ${verb} takes ${words ? `at most ${words} positional word${words > 1 ? 's' : ''}` : 'no positional words'}\nNothing changed.\nignite ${verb} -h`,
    [...verb.split(' '), ...Array(words).fill('word'), 'extra'],
  ]),
]);

const GHOST_COMMANDS = [
  ['schedule', 'list'],
  ['schedule', 'add', '--every', '1h', '--note', 'n', '--conversation', OPTION_KEY],
  ['schedule', 'change', 'existing', '--note', 'Changed'],
  ['schedule', 'cancel', 'existing'],
  ['schedules-due', '--now', '2026-10-01T13:00:00Z'],
  ['work', 'status'],
  ['work', 'retry'],
  ['work', 'resume', 'existing'],
  ['work', 'stop', 'existing'],
  ['wake', '--conversation', OPTION_KEY, '--note', 'n'],
  ['post', '--text', 'hi'],
  ['board', 'write', '--file', 'CANDIDATE'],
  ['board', 'close', 'Subject', 'Outcome'],
  ['remember', 'fact'],
];
const noAgentFolder = (workspace) => `agent folder not found: ${ghostHome(workspace)}\nNothing changed.\nignite -h`;

refusals('a verb pointed at an agent folder that does not exist refuses and creates nothing', [
  ...GHOST_COMMANDS.map((args) => [noAgentFolder, [...args, '--agent', 'ghost', '--installation', 'WORKSPACE'], { RBTV_AGENT_HOME: '' }]),
  ...GHOST_COMMANDS.map((args) => [noAgentFolder, args, (workspace) => ({ RBTV_AGENT_HOME: ghostHome(workspace) })]),
]);

test('an existing agent folder with no database gets one from a read', () => {
  for (const args of [['schedule', 'list'], ['work', 'status']]) {
    const workspace = tempHome();
    try {
      const home = writeConfig(workspace, 'sample', { C1: 'sample' });
      const result = run([...args, '--agent', 'sample', '--installation', workspace], { env: {} });
      assert.equal(result.code, 0, args.join(' '));
      assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), true, args.join(' '));
    } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
  }
});

test('schedule change refuses each empty note schedule add refuses', () => {
  const home = tempHome();
  fs.mkdirSync(path.dirname(boardPath(home)));
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  const deps = { env: { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: OPTION_KEY } };
  try {
    store.upsertConversation({ key: OPTION_KEY, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
    store.upsertSchedule({ id: 'existing', conversationKey: OPTION_KEY, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: 1000, note: 'Original' });
    const board = fs.readFileSync(boardPath(home), 'utf8');
    for (const note of ['', '  ', '\n\t']) {
      for (const args of [['add', '--every', '1h'], ['change', 'existing']]) {
        assert.throws(() => run(['schedule', ...args, '--note', note], deps),
          (error) => error.message === emptyValue('--note', `ignite schedule ${args[0]} -h`) && error.exitCode === 1, `${args[0]} ${JSON.stringify(note)}`);
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

test('dreamer is an unknown command', () => {
  assert.throws(() => run(['dreamer', 'run']), (error) => {
    assert.match(error.message, /unknown command: dreamer\nchoose from connect, disconnect, manage, turn,\nschedule, schedules-due, work, wake, post, status, payment, board, remember, runtime, deploy\nNothing changed\.\nignite -h/);
    return true;
  });
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
    assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
  });
});

test('board write refuses a stale revision and writes nothing', () => {
  boardFixture(({ file, candidate, text, deps }) => {
    assert.equal(run(['board', 'write', '--file', candidate], deps).code, 0);
    const revision = boardRevision(fs.readFileSync(file, 'utf8'));
    const next = text.replace('Owner chose toner café.', 'Owner chose paper.');
    fs.writeFileSync(candidate, next, 'utf8');
    const stale = run(['board', 'write', '--file', candidate, '--revision', 'stale-revision'], deps);
    assert.equal(stale.code, 1);
    assert.match(stale.err, /stale revision/);
    assert.equal(fs.readFileSync(file, 'utf8'), text);
    const fresh = run(['board', 'write', '--file', candidate, '--revision', revision], deps);
    assert.equal(fresh.code, 0, fresh.err);
    assert.match(fs.readFileSync(file, 'utf8'), /Owner chose paper/);
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
    assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
  });
});

test('board help works before and after every command depth without context or writes', () => {
  assert.match(run(['board', '--help']).out, /^ {2}write +Replace the board/m);
  for (const [args, usage, text] of [
    [[], null, /checked short-term memory/],
    [['write'], /^usage: ignite board write --file <path>/m, /6,000 Unicode code points/],
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
    assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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

test('schedule check tool: add, change and list carry it; a refused value changes nothing; a timer without one is as before', () => {
  const home = tempHome();
  fs.mkdirSync(path.dirname(boardPath(home)));
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  const key = 'T1:C1:board';
  const deps = { env: { RBTV_AGENT_HOME: home, IGNITE_CONVERSATION: key }, now: () => Date.parse('2026-10-03T12:00:00Z') };
  const add = (...extra) => JSON.parse(run(['schedule', 'add', '--every', '5m', '--note', 'n', ...extra, '--json'], deps).out).schedule;
  try {
    store.upsertConversation({ key, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: 'board' });
    const mail = add('--check', 'tools\\mail-check.js', '--subject', 'Inbox');
    assert.equal(mail.check_tool, 'tools/mail-check.js');
    const plain = add();
    assert.equal(plain.check_tool, null);
    assert.equal(add('--check', 'meeting-check').check_tool, 'meeting-check');

    const lines = run(['schedule', 'list'], deps).out.split('\n');
    assert.ok(lines.includes(`${mail.id} every:5m fixed next=${mail.next_at} enabled=true check=tools/mail-check.js n`));
    assert.ok(lines.includes(`${plain.id} every:5m fixed next=${plain.next_at} enabled=true n`));
    const listed = JSON.parse(run(['schedule', 'list', '--json'], deps).out).schedules;
    assert.deepEqual(listed.map((row) => row.check_tool).sort(), ['meeting-check', 'tools/mail-check.js', null].sort());

    const noted = JSON.parse(run(['schedule', 'change', mail.id, '--note', 'new note', '--every', '10m', '--json'], deps).out).schedule;
    assert.deepEqual([noted.check_tool, noted.subject, noted.note], ['tools/mail-check.js', 'Inbox', 'new note']);
    run(['schedule', 'change', mail.id, '--check', './mail.py'], deps);
    assert.equal(store.getSchedule(mail.id).check_tool, './mail.py');
    run(['schedule', 'change', plain.id, '--report', 'always'], deps);
    assert.equal(store.getSchedule(plain.id).check_tool, null);
    run(['schedule', 'change', plain.id, '--check', 'tools/late.js'], deps);
    assert.equal(store.getSchedule(plain.id).check_tool, 'tools/late.js');

    const before = store.listSchedules();
    const boardBefore = fs.readFileSync(boardPath(home), 'utf8');
    for (const bad of ['/usr/bin/x', 'C:\\x.exe', '../x', 'tools/', '', '  ']) {
      assert.throws(() => run(['schedule', 'add', '--every', '5m', '--note', 'n', '--check', bad], deps), /--check/, `add ${bad}`);
      assert.throws(() => run(['schedule', 'change', mail.id, '--note', 'lost', '--check', bad], deps), /--check/, `change ${bad}`);
    }
    assert.deepEqual(store.listSchedules(), before);
    assert.equal(fs.readFileSync(boardPath(home), 'utf8'), boardBefore);

    for (const page of ['schedule add', 'schedule change']) {
      assert.match(PAGES[page], /\[--check <path or command>\]/);
      assert.match(PAGES[page], /relative to the agent\s+home/);
      assert.ok(VERBS[page].options.includes('check'));
    }
    assert.match(PAGES['schedule list'], /check=<path or command>/);
    assert.match(PAGES['schedule list'], /check_tool/);
  } finally { store.close(); fs.rmSync(home, { recursive: true, force: true }); }
});

test('schedules-due wakes every timer due together, records one occurrence once, and leaves refused and check timers due', () => {
  const home = tempHome();
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
  const key = 'T1:C1:board';
  const env = { RBTV_AGENT_HOME: home };
  const due = (at) => JSON.parse(run(['schedules-due', '--now', at, '--json'], { env }).out).results;
  const wakes = () => store.db.prepare("SELECT id FROM queue WHERE kind='schedule' AND state='pending' ORDER BY id").all().map((row) => row.id);
  try {
    store.upsertConversation({ key, agent: 'a', workspace: 'T1', channel: 'C1', rootTs: 'board' });
    for (const id of ['briefing', 'reminder']) {
      store.upsertSchedule({ id, conversationKey: key, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: 1_000, note: id });
    }
    store.upsertSchedule({
      id: 'mail', conversationKey: key, cadence: 'every:5m', timezone: FIXED_TZ, nextAt: 1_000, note: 'mail', checkTool: 'tools/mail-check.js',
    });
    const at = Date.parse('2026-01-01T00:00:00Z');
    const first = due('2026-01-01T00:00:00Z');
    assert.deepEqual(first, [
      { id: 'briefing', inserted: true, reason: 'queued', nextAt: at + 3_600_000 },
      { id: 'mail', inserted: false, reason: 'check', nextAt: 1_000 },
      { id: 'reminder', inserted: true, reason: 'queued', nextAt: at + 3_600_000 },
    ]);
    assert.deepEqual(wakes(), ['schedule:briefing:1000', 'schedule:reminder:1000']);
    assert.equal(store.getSchedule('mail').next_at, 1_000);
    assert.equal(store.getSchedule('mail').check_tool, 'tools/mail-check.js');

    // The same occurrence due again, as after a crash before the advance: no second wake, and the timer moves on.
    store.db.prepare("UPDATE schedules SET next_at=1000 WHERE id='briefing'").run();
    const again = due('2026-01-01T00:00:00Z').find((row) => row.id === 'briefing');
    assert.deepEqual(again, { id: 'briefing', inserted: false, reason: 'duplicate', nextAt: at + 3_600_000 });
    assert.deepEqual(wakes(), ['schedule:briefing:1000', 'schedule:reminder:1000']);
    assert.equal(store.getSchedule('briefing').next_at, at + 3_600_000);

    // A wake the queue refuses leaves its timer where it was.
    const waiting = store.enqueue({ id: 'owner', conversationKey: key, availableAt: 1 });
    store.db.prepare("UPDATE work SET state='waiting_owner' WHERE id=?").run(waiting.workId);
    store.upsertSchedule({ id: 'gated', conversationKey: key, workId: waiting.workId, cadence: 'every:1h', timezone: FIXED_TZ, nextAt: 2_000, note: 'gated' });
    assert.deepEqual(due('2026-01-01T00:00:00Z').find((row) => row.id === 'gated'),
      { id: 'gated', inserted: false, reason: 'refused', nextAt: 2_000 });
    assert.equal(store.getSchedule('gated').next_at, 2_000);
    assert.deepEqual(wakes(), ['schedule:briefing:1000', 'schedule:reminder:1000']);
    assert.match(PAGES['schedules-due'], /One wake per timer and occurrence/);
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
    assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
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
      assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
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
      const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
      const db = path.join(home, 'runtime', 'ignite', 'state.sqlite');
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
        assert.deepEqual(fs.readdirSync(path.dirname(db)).filter((name) => name.startsWith('state.sqlite')), ['state.sqlite']);
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
        assert.equal(fs.existsSync(path.join(home, 'runtime', 'ignite', 'state.sqlite')), false);
      }
    } finally { fs.rmSync(home, { recursive: true, force: true }); }
  });
}

for (const json of [false, true]) {
  for (const action of ['add', 'change', 'cancel']) test(`schedule ${action} reports committed with refresh pending in ${json ? 'JSON' : 'text'} mode`, () => {
    boardFixture(({ home, file, candidate, text, deps }) => {
      run(['board', 'write', '--file', candidate], deps);
      const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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
  const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
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

function albertCli(dir, args, extraEnv = {}) {
  return spawnSync(process.execPath, [path.join(__dirname, 'cli.js'), 'albert', ...args, '--installation', dir], {
    encoding: 'utf8',
    env: { ...process.env, RBTV_AGENT_HOME: '', NODE_NO_WARNINGS: '1', ...extraEnv },
  });
}

test('cli.js albert fence prints fenced', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  try {
    const result = albertCli(dir, ['fence']);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'fenced\n');
    assert.equal(result.stderr, '');
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'runtime', 'ignite', 'albert-fence.json')), true);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cli.js albert drain without a fence prints the refusal on stderr', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  writeConfig(dir, 'master', {});
  try {
    const result = albertCli(dir, ['drain']);
    assert.equal(result.status, 1);
    assert.equal(result.stdout, '');
    assert.equal(result.stderr, 'drain requires the legacy fence\n');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cli.js albert drain prints drained', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  try {
    assert.equal(albertCli(dir, ['fence']).status, 0);
    const result = albertCli(dir, ['drain']);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'drained\n');
    assert.equal(result.stderr, '');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cli.js albert migrate dry-run prints dry-run writes: none', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  writeConfig(dir, 'master', {});
  try {
    const result = albertCli(dir, ['migrate', '--dry-run']);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'missing master\nliveness none\nconflicts 0\ndry-run writes: none\n');
    assert.equal(result.stderr, '');
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'albert', 'runtime', 'albert', 'ignite-cursors.json')), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cli.js albert migrate prints migrated', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  writeConfig(dir, 'master', {});
  try {
    const result = albertCli(dir, ['migrate']);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'missing master\nliveness none\nconflicts 0\nmigrated\n');
    assert.equal(result.stderr, '');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cli.js albert verify prints nightly, watchdog and report dry-run', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  const home = writeConfig(dir, 'master', {});
  const stub = path.join(dir, 'albert-stub.js');
  fs.writeFileSync(stub, [
    "const op = process.argv[2];",
    "if (op === 'check' || op === 'watchdog') process.stdout.write('{\"new\":false}\\n');",
    "else if (op === 'report') process.stdout.write('{\"identity\":\"fixture-report\"}\\n');",
    "else { process.stderr.write('stub\\n'); process.exit(1); }",
    '',
  ].join('\n'));
  fs.mkdirSync(path.join(dir, '.rbtv', 'agents', 'albert'), { recursive: true });
  new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite')).close();
  try {
    const result = albertCli(dir, ['verify'], { ALBERT_TOOL: stub, ALBERT_OCCASION: '2026-10-16' });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'nightly {"new":false}\nwatchdog {"new":false}\nreport dry-run fixture-report\n');
    assert.equal(result.stderr, '');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cli.js albert recover prints recovered legacy', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  try {
    assert.equal(albertCli(dir, ['fence']).status, 0);
    const result = albertCli(dir, ['recover']);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'recovered legacy\n');
    assert.equal(result.stderr, '');
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'runtime', 'ignite', 'albert-fence.json')), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cli.js albert cleanup prints cleaned', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  writeConfig(dir, 'master', {});
  const file = path.join(dir, '.rbtv', 'config', 'ignite', 'config.json');
  const config = JSON.parse(fs.readFileSync(file, 'utf8'));
  config.dreamer = { enabled: false };
  fs.writeFileSync(file, JSON.stringify(config));
  try {
    const result = albertCli(dir, ['cleanup']);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'cleaned\n');
    assert.equal(result.stderr, '');
    assert.equal(JSON.parse(fs.readFileSync(file, 'utf8')).dreamer, undefined);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cli.js albert probe prints dreamer keys absent', () => {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-cli-')));
  writeConfig(dir, 'master', {});
  try {
    const result = albertCli(dir, ['probe']);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'dreamer keys absent\n');
    assert.equal(result.stderr, '');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

if (failures.length) {
  console.log(`${failures.length} failed`);
  process.exit(1);
}
console.log('ok');
