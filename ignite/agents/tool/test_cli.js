#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Store } = require('./store.js');
const { main, HELP } = require('./cli.js');
const { nextCron, FIXED_TZ } = require('./schedule.js');

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
  const dir = path.join(workspace, '.rbtv', 'agents');
  fs.mkdirSync(dir, { recursive: true });
  const body = {
    workspace,
    slack: {
      team: 'T1',
      botUserId: 'UBOT',
      ownerUserId: 'UOWNER',
      botTokenFile: path.join(workspace, 'bot.json'),
      appTokenSource: 'SLACK_APP_TOKEN',
      ownerTokenFile: path.join(workspace, 'owner.json'),
      stoolsWorkspace: 'ignite',
    },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' },
    defaultLaunch: { harness: 'claude', model: 'm', effort: 'high' },
    dmAgent: 'master',
    routes,
  };
  fs.writeFileSync(path.join(dir, 'ignite.json'), JSON.stringify(body));
  const home = path.join(dir, slug);
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

if (failures.length) {
  console.log(`${failures.length} failed`);
  process.exit(1);
}
console.log('ok');
