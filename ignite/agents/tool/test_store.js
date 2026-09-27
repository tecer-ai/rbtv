#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Store, conversationKey, DISPOSITIONS, RETRY_DELAYS_MS, MAX_ATTEMPTS } = require('./store.js');

const failures = [];

function test(name, fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-store-'));
  const db = path.join(dir, 'state.sqlite');
  let store = new Store(db);
  const open = () => new Store(db);
  try {
    fn(store, { dir, db, open, reopen() { store.close(); store = open(); return store; } });
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  } finally {
    try { store.close(); } catch { /* already closed */ }
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function conv(store, key = 'T1:C1:1.1', extra = {}) {
  return store.upsertConversation({
    key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1', ...extra,
  });
}

function ownerMessage(id, text = 'hello') {
  return { id, role: 'owner', text, team: 'T1', channel: 'C1', ts: id };
}

function launch(store) {
  return store.setLaunchSetting({ harness: 'claude', model: 'm', effort: 'high' });
}

function finish(store, claim, disposition, extra = {}) {
  return store.finishRun(claim.runId, claim.nonce, {
    invocationNonce: claim.nonce,
    output: JSON.stringify({ disposition }),
    disposition,
    summary: 's',
    nextStep: disposition === 'continue' ? 'next' : null,
    ...extra,
  });
}

test('2a owner input reopens completed work; wake does not', (store) => {
  conv(store);
  const first = store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', payload: { n: 1 }, availableAt: 1_000 });
  assert.equal(first.inserted, true);
  const claim = store.claimNext(1_000);
  finish(store, claim, 'completed');
  assert.equal(store.getWork(first.workId).state, 'completed');
  const wake = store.wake({ workId: first.workId });
  assert.equal(wake.inserted, false);
  assert.equal(store.getWork(first.workId).state, 'completed');
  const again = store.enqueue({ id: 'q2', conversationKey: 'T1:C1:1.1', payload: { n: 2 } });
  assert.equal(again.reason, 'reopened');
  assert.notEqual(again.workId, first.workId);
  assert.equal(store.getWork(first.workId).state, 'completed');
  assert.equal(store.getWork(again.workId).state, 'open');
  assert.equal(store.getWork(again.workId).predecessor_id, first.workId);
  const stopped = store.enqueue({ id: 'q3', conversationKey: 'T1:C1:1.1', workId: again.workId, availableAt: 2_000 });
  assert.equal(stopped.workId, again.workId);
  store.claimNext(2_000);
  const active = store.getActiveRun();
  finish(store, { runId: active.id, nonce: active.nonce }, 'stopped');
  const wakeStopped = store.wake({ workId: again.workId });
  assert.equal(wakeStopped.inserted, false);
  const reopened = store.acceptOwnerInput({
    key: 'T1:C1:1.1', agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1',
    message: ownerMessage('9.9', 'new request'),
  });
  assert.equal(reopened.duplicate, false);
  assert.equal(reopened.reason, 'reopened');
  assert.equal(store.getWork(again.workId).state, 'stopped');
});

test('2b liveRun returns pid and pidStart', (store) => {
  conv(store);
  launch(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  assert.equal(store.liveRun(), null);
  assert.equal(store.getActiveRun().id, claim.runId);
  store.attachProcess(claim.runId, { pid: 4242, pidStart: 'start-9' });
  const live = store.liveRun();
  assert.equal(live.pid, 4242);
  assert.equal(live.pidStart, 'start-9');
  assert.equal(store.claimNext(2_000), null);
  assert.throws(() => store.attachProcess(claim.runId, { pid: 1, pidStart: 'other' }));
});

test('2c clearHold is explicit and wakes do not unhold', (store) => {
  conv(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  let claim = store.claimNext(1_000);
  store.failRun(claim.runId, 'boom', { now: 1_000 });
  claim = store.claimNext(1_000 + RETRY_DELAYS_MS[0]);
  store.failRun(claim.runId, 'boom', { now: 1_000 + RETRY_DELAYS_MS[0] });
  claim = store.claimNext(1_000 + RETRY_DELAYS_MS[0] + RETRY_DELAYS_MS[1]);
  const held = store.failRun(claim.runId, 'boom', { scope: 'work', now: 9_000 });
  assert.equal(held.held, true);
  assert.equal(held.scope, 'work');
  const workId = store.getActiveRun() ? null : store.listWork()[0].id;
  assert.equal(store.getWork(workId).state, 'held');
  assert.equal(store.wake({ workId }).inserted, false);
  assert.equal(store.getWork(workId).state, 'held');
  assert.equal(store.enqueueScheduleWake({ id: 'sw1', conversationKey: 'T1:C1:1.1', workId }).inserted, false);
  assert.equal(store.getWork(workId).state, 'held');
  assert.equal(store.claimNext(10_000), null);
  assert.equal(store.clearHold({ workId: workId }), true);
  assert.equal(store.getWork(workId).state, 'open');
  assert.ok(store.claimNext());
});

test('2d one pending scheduled wake per agent', (store) => {
  conv(store);
  store.upsertConversation({ key: 'T1:C2:2.2', agent: 'master', workspace: 'T1', channel: 'C2', rootTs: '2.2' });
  const first = store.enqueueScheduleWake({ id: 'sw1', conversationKey: 'T1:C1:1.1', scheduleId: 's1' });
  assert.equal(first.inserted, true);
  const second = store.enqueueScheduleWake({ id: 'sw2', conversationKey: 'T1:C2:2.2', scheduleId: 's2' });
  assert.equal(second.inserted, false);
  assert.equal(second.reason, 'duplicate');
  store.setLaunchSetting({ harness: 'claude', model: 'm', effort: 'low' });
  const claim = store.claimNext();
  assert.equal(claim.kind, 'schedule');
  const third = store.enqueueScheduleWake({ id: 'sw3', conversationKey: 'T1:C1:1.1' });
  assert.equal(third.inserted, true);
  store.finishRun(claim.runId, claim.nonce, {
    invocationNonce: claim.nonce, output: '{}', disposition: 'completed', summary: 'board',
  });
});

test('2e owner input claimed before continuation', (store) => {
  conv(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  finish(store, claim, 'continue');
  store.enqueue({ id: 'q-owner', conversationKey: 'T1:C1:1.1', payload: { fresh: true }, availableAt: 1_000 });
  const next = store.claimNext();
  assert.equal(next.kind, 'owner');
  assert.equal(next.id, 'q-owner');
  assert.equal(next.priority, 0);
});

test('2f outbox client_msg_id retry state and delivered ts', (store) => {
  conv(store);
  assert.equal(store.enqueueOutbox({
    id: 'ob1', conversationKey: 'T1:C1:1.1', payload: { text: 'hi' }, clientMsgId: 'ob1',
  }), true);
  assert.equal(store.enqueueOutbox({
    id: 'ob1', conversationKey: 'T1:C1:1.1', payload: { text: 'hi' },
  }), false);
  let pending = store.pendingOutbox(1_000);
  assert.equal(pending.length, 1);
  assert.equal(pending[0].client_msg_id, 'ob1');
  const failed = store.markDeliveryFailed('ob1', 'timeout', { retryAt: 5_000 });
  assert.equal(failed.state, 'pending');
  assert.equal(failed.attempts, 1);
  assert.equal(failed.last_error, 'timeout');
  assert.equal(failed.ts, null);
  assert.equal(store.pendingOutbox(4_999).length, 0);
  assert.equal(store.pendingOutbox(5_000)[0].client_msg_id, 'ob1');
  const delivered = store.markDelivered('ob1', { channel: 'C1', ts: '3.3' });
  assert.equal(delivered.ts, '3.3');
  assert.equal(delivered.clientMsgId, 'ob1');
  assert.deepEqual(store.markDelivered('ob1', { channel: 'OTHER', ts: '9.9' }), {
    channel: 'C1', ts: '3.3', clientMsgId: 'ob1',
  });
  assert.equal(store.pendingOutbox(9_000).length, 0);
});

test('2g conversation maps to agent and activation flag', (store) => {
  const row = conv(store, 'T1:C1:1.1', { activated: false });
  assert.equal(row.agent, 'master');
  assert.equal(row.activated, false);
  assert.equal(store.conversationByThread({ workspace: 'T1', channel: 'C1', rootTs: '1.1' }).key, 'T1:C1:1.1');
  assert.equal(store.activateConversation('T1:C1:1.1').activated, true);
  const saved = store.acceptOwnerInput({
    key: 'T1:C1:1.1', agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true,
    message: ownerMessage('4.4', 'mention'),
  });
  assert.equal(saved.conversation.activated, true);
  assert.equal(saved.conversation.agent, 'master');
  const again = store.acceptOwnerInput({
    key: 'T1:C1:1.1', agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1',
    message: ownerMessage('4.4', 'mention'),
  });
  assert.equal(again.duplicate, true);
  assert.equal(store.listHistory('T1:C1:1.1').length, 1);
  assert.equal(store.listHistory('T1:C1:1.1')[0].ts, '4.4');
  assert.throws(() => store.upsertConversation({
    key: 'T1:C1:1.1', agent: 'other', workspace: 'T1', channel: 'C1',
  }));
  assert.equal(conversationKey('T1', 'C1', '1.1'), 'T1:C1:1.1');
});

test('2h session id is per harness', (store) => {
  conv(store);
  store.setSession('T1:C1:1.1', 'claude', 'ses-claude');
  store.setSession('T1:C1:1.1', 'codex', 'ses-codex');
  assert.equal(store.getSession('T1:C1:1.1', 'claude'), 'ses-claude');
  assert.equal(store.getSession('T1:C1:1.1', 'codex'), 'ses-codex');
  store.setSession('T1:C1:1.1', 'codex', 'ses-codex-2');
  assert.equal(store.getSession('T1:C1:1.1', 'claude'), 'ses-claude');
  assert.equal(store.getSession('T1:C1:1.1', 'codex'), 'ses-codex-2');
  assert.equal(store.getSession('T1:C1:1.1', 'opencode'), null);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  finish(store, claim, 'completed', { harness: 'claude', sessionId: 'ses-after-turn' });
  assert.equal(store.getSession('T1:C1:1.1', 'claude'), 'ses-after-turn');
  assert.equal(store.getSession('T1:C1:1.1', 'codex'), 'ses-codex-2');
});

test('2i launch setting timestamp and run snapshot', (store) => {
  conv(store);
  const first = launch(store);
  assert.equal(typeof first.changedAt, 'number');
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  store.attachProcess(claim.runId, { pid: 7, pidStart: 'p' });
  const second = store.setLaunchSetting({ harness: 'codex', model: 'other', effort: 'max', voice: 'v' });
  assert.ok(second.changedAt > first.changedAt);
  assert.equal(store.agentHold(), null);
  const live = store.liveRun();
  assert.equal(live.launch_snapshot.harness, 'claude');
  assert.equal(live.launch_snapshot.model, 'm');
  assert.equal(store.getLaunchSetting().harness, 'codex');
  assert.equal(store.getLaunchSetting().voice, 'v');
});

test('retry delays are 5s then 30s then work hold', (store) => {
  assert.deepEqual(RETRY_DELAYS_MS, [5_000, 30_000]);
  assert.equal(MAX_ATTEMPTS, 3);
  assert.deepEqual(DISPOSITIONS, ['completed', 'continue', 'waiting_owner', 'waiting_workers', 'stopped']);
  conv(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 10_000 });
  const t0 = 10_000;
  let claim = store.claimNext(t0);
  let failed = store.failRun(claim.runId, 'e1', { now: t0 });
  assert.equal(failed.held, false);
  assert.equal(failed.retryAt, t0 + 5_000);
  assert.equal(store.claimNext(t0 + 4_999), null);
  claim = store.claimNext(t0 + 5_000);
  failed = store.failRun(claim.runId, 'e2', { now: t0 + 5_000 });
  assert.equal(failed.retryAt, t0 + 5_000 + 30_000);
  claim = store.claimNext(t0 + 35_000);
  failed = store.failRun(claim.runId, 'e3', { scope: 'work', now: t0 + 35_000 });
  assert.equal(failed.held, true);
  assert.equal(failed.attempts, 3);
  const notice = store.pendingOutbox()[0];
  assert.equal(notice.client_msg_id, `hold:${claim.id}`);
  assert.match(notice.payload.text, /three technical attempts/);
  assert.match(notice.payload.text, /work retry/);
});

test('agent hold blocks every claim until clearHold', (store) => {
  conv(store);
  store.upsertConversation({ key: 'T1:C9:9.9', agent: 'master', workspace: 'T1', channel: 'C9', rootTs: '9.9' });
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  for (let i = 0; i < 2; i += 1) {
    const current = i === 0 ? claim : store.claimNext(1_000 + RETRY_DELAYS_MS[0]);
    store.failRun(current.runId, 'launch', { scope: 'agent', now: 1_000 + (i === 0 ? 0 : RETRY_DELAYS_MS[0]) });
  }
  const third = store.claimNext(1_000 + 35_000);
  const held = store.failRun(third.runId, 'launch', { scope: 'agent', now: 50_000 });
  assert.equal(held.scope, 'agent');
  store.enqueue({ id: 'q-other', conversationKey: 'T1:C9:9.9', availableAt: 60_000 });
  assert.equal(store.claimNext(60_000), null);
  assert.ok(store.agentHold());
  assert.equal(store.enqueueScheduleWake({ id: 'sw', conversationKey: 'T1:C1:1.1' }).reason, 'agent_hold');
  assert.equal(store.clearHold(), true);
  assert.equal(store.agentHold(), null);
  assert.ok(store.claimNext());
});

test('waiting_owner does not auto-continue; owner answer does', (store) => {
  conv(store);
  store.upsertConversation({ key: 'T1:C2:2.2', agent: 'master', workspace: 'T1', channel: 'C2', rootTs: '2.2' });
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  finish(store, claim, 'waiting_owner');
  assert.equal(store.claimNext(2_000), null);
  store.enqueue({ id: 'other', conversationKey: 'T1:C2:2.2', availableAt: 3_000 });
  const other = store.claimNext(3_000);
  assert.equal(other.id, 'other');
  finish(store, other, 'completed');
  store.enqueue({ id: 'answer', conversationKey: 'T1:C1:1.1', availableAt: 4_000 });
  const answer = store.claimNext(4_000);
  assert.equal(answer.id, 'answer');
  assert.equal(answer.kind, 'owner');
});

test('waiting_workers wakes once and a schedule wake does not rearm it', (store) => {
  conv(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  const work = finish(store, claim, 'waiting_workers', { workers: [{ ref: 'w', kind: 'task' }] });
  assert.equal(store.claimNext(2_000), null);
  const wake = store.wake({ conversationKey: 'T1:C1:1.1', note: 'done' });
  assert.equal(wake.inserted, true);
  assert.equal(store.wake({ workId: work.id }).reason, 'duplicate');
  assert.equal(store.enqueueScheduleWake({
    id: 'sw', conversationKey: 'T1:C1:1.1', workId: work.id,
  }).reason, 'refused');
  assert.equal(store.getWork(work.id).state, 'waiting_workers');
  const next = store.claimNext();
  assert.equal(next.kind, 'wake');
});

test('stopWork cancels continuation and leaves schedules', (store) => {
  conv(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  const work = finish(store, claim, 'continue');
  store.upsertSchedule({
    id: 'sched', conversationKey: 'T1:C1:1.1', cadence: 'every 1h', timezone: 'UTC', nextAt: 5, note: 'board',
  });
  const stopped = store.stopWork(work.id);
  assert.equal(stopped.state, 'stopped');
  assert.equal(store.claimNext(9_000), null);
  assert.equal(store.getSchedule('sched').cadence, 'every 1h');
  assert.equal(store.wake({ workId: work.id }).inserted, false);
});

test('stop during a run survives finishRun continue', (store) => {
  conv(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  const workId = claim.work_id;
  store.stopWork(workId);
  const work = finish(store, claim, 'continue');
  assert.equal(work.state, 'stopped');
  assert.equal(store.claimNext(2_000), null);
});

test('nonce freshness, invalid disposition, continue requires next step', (store) => {
  conv(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  const claim = store.claimNext(1_000);
  assert.throws(() => store.finishRun(claim.runId, claim.nonce, {
    invocationNonce: 'nope', output: '{}', disposition: 'completed',
  }), /stale/);
  assert.throws(() => store.finishRun(claim.runId, claim.nonce, {
    invocationNonce: claim.nonce, output: '{}', disposition: 'wait_input',
  }), /invalid disposition/);
  assert.throws(() => store.finishRun(claim.runId, claim.nonce, {
    invocationNonce: claim.nonce, output: '{}', disposition: 'continue', nextStep: '  ',
  }), /next step/);
  finish(store, claim, 'completed');
  assert.throws(() => finish(store, claim, 'completed'), /not active/);
});

test('single active run and message idempotency', (store) => {
  conv(store);
  store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', message: ownerMessage('1.1', 'a'), availableAt: 1_000 });
  assert.equal(store.claimNext(1_000).id, 'q1');
  assert.equal(store.claimNext(1_000), null);
  assert.equal(store.recordMessage('T1:C1:1.1', ownerMessage('1.1', 'a')), false);
  assert.equal(store.listHistory('T1:C1:1.1').length, 1);
  assert.throws(() => store.recordMessage('missing', ownerMessage('2.2')));
});

test('history order, files roundtrip, orphan rejected', (store) => {
  conv(store);
  store.recordMessage('T1:C1:1.1', { ...ownerMessage('1.0', 'older'), files: ['a'], metadata: { k: 1 }, createdAt: 1 });
  store.recordMessage('T1:C1:1.1', { ...ownerMessage('2.0', 'newer'), createdAt: 2 });
  const rows = store.listHistory('T1:C1:1.1');
  assert.deepEqual(rows.map((row) => row.text), ['older', 'newer']);
  assert.deepEqual(rows[0].files, ['a']);
  assert.deepEqual(rows[0].metadata, { k: 1 });
  assert.throws(() => store.db.prepare('INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    .run('x', 'nope', 'owner', '', '[]', '{}', null, null, null, 1));
});

test('schedules crud and due query', (store) => {
  conv(store);
  store.upsertSchedule({
    id: 's1', conversationKey: 'T1:C1:1.1', cadence: '0 9 * * *', timezone: 'America/Sao_Paulo',
    nextAt: 100, note: 'look', report: 'when-useful',
  });
  store.upsertSchedule({
    id: 's2', conversationKey: 'T1:C1:1.1', cadence: 'once', timezone: 'UTC', nextAt: 300, enabled: false,
  });
  assert.equal(store.dueSchedules(50).length, 0);
  assert.equal(store.dueSchedules(100).length, 1);
  assert.equal(store.dueSchedules(100)[0].note, 'look');
  store.upsertSchedule({
    id: 's1', conversationKey: 'T1:C1:1.1', cadence: '0 10 * * *', timezone: 'America/Sao_Paulo', nextAt: 50,
  });
  assert.equal(store.getSchedule('s1').cadence, '0 10 * * *');
  assert.equal(store.deleteSchedule('s2'), true);
  assert.equal(store.listSchedules().length, 1);
});

test('proactive post binds activated thread on delivery', (store) => {
  const begun = store.beginProactive({
    id: 'p1', agent: 'master', workspace: 'T1', channel: 'C1', payload: { text: 'board' },
  });
  assert.equal(begun.activated, true);
  assert.equal(store.getConversation(begun.conversationKey).activated, true);
  const delivered = store.markDelivered(begun.outboxId, { channel: 'C1', ts: '8.8' });
  assert.equal(delivered.conversationKey, 'T1:C1:8.8');
  const bound = store.conversationByThread({ workspace: 'T1', channel: 'C1', rootTs: '8.8' });
  assert.equal(bound.activated, true);
  assert.equal(bound.agent, 'master');
  assert.equal(store.getConversation(begun.conversationKey), null);
});

test('transaction rollback and persistence', (store, ctx) => {
  conv(store);
  assert.throws(() => store.transaction(() => {
    store.enqueue({ id: 'q-roll', conversationKey: 'T1:C1:1.1' });
    throw new Error('nope');
  }));
  assert.equal(store.listWork().length, 0);
  store.enqueue({ id: 'q-keep', conversationKey: 'T1:C1:1.1' });
  const reopened = ctx.reopen();
  assert.equal(reopened.getConversation('T1:C1:1.1').agent, 'master');
  assert.equal(reopened.listWork().length, 1);
});

test('held owner input is retained and not an unhold', (store) => {
  conv(store);
  const first = store.enqueue({ id: 'q1', conversationKey: 'T1:C1:1.1', availableAt: 1_000 });
  let claim = store.claimNext(1_000);
  store.failRun(claim.runId, 'e', { now: 1_000 });
  claim = store.claimNext(6_000);
  store.failRun(claim.runId, 'e', { now: 6_000 });
  claim = store.claimNext(36_000);
  store.failRun(claim.runId, 'e', { scope: 'work', now: 36_000 });
  const kept = store.enqueue({ id: 'steer', conversationKey: 'T1:C1:1.1', payload: { steer: true }, availableAt: 40_000 });
  assert.equal(kept.workId, first.workId);
  assert.equal(store.getWork(first.workId).state, 'held');
  assert.equal(store.claimNext(40_000), null);
  store.clearHold({ workId: first.workId });
  const next = store.claimNext(40_000);
  assert.equal(next.kind, 'owner');
});

if (failures.length) {
  console.log(`FAIL ${failures.length}`);
  process.exit(1);
}
console.log('PASS store');
