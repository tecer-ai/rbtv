'use strict';

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { createOutbox, outboxStorePath, KINDS, STATES } = require('../outbox');

const OUT = path.join(__dirname, 'probe-chat-outbox.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence }); };

function tmpStore() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'outbox-'));
  return path.join(dir, 'outbox.json');
}

function makeSend(plan) {
  const calls = [];
  return {
    calls,
    send: async (args) => {
      calls.push(args);
      const next = plan.length ? plan.shift() : { delivered: true, ts: `ts-${calls.length}` };
      if (next.throw) throw new Error(next.throw);
      return next;
    },
  };
}

async function main() {
  const storePath = tmpStore();
  const { send, calls } = makeSend([
    { delivered: false, error: 'channel_not_found' },
    { delivered: false, error: 'channel_not_found' },
  ]);
  const box = createOutbox({ storePath, send });
  const first = await box.post({
    kind: 'notification', channel_id: 'C1', thread_ts: '1.0', goal_id: 'g1', ask_id: null,
    payload: 'hello',
  });
  const rec = box.get(first.outbox_id);
  check('ok:false stays pending-delivery',
    first.delivered === false && rec.state === 'pending-delivery' && rec.last_error === 'channel_not_found' && rec.attempt_count === 1,
    { first, rec });

  const retry = await box.post({
    kind: 'notification', channel_id: 'C1', thread_ts: '1.0', goal_id: 'g1', ask_id: null,
    payload: 'hello',
  });
  const afterRetry = box.query({});
  check('retry does not mint a second record',
    retry.outbox_id === first.outbox_id && afterRetry.length === 1 && afterRetry[0].attempt_count === 2 && afterRetry[0].state === 'pending-delivery',
    { retry, afterRetry });

  const { send: sendOk } = makeSend([{ delivered: true, ts: '9.9' }]);
  const box2 = createOutbox({ storePath, send: sendOk });
  const ack = await box2.post({ outbox_id: first.outbox_id });
  const delivered = box2.get(first.outbox_id);
  check('ack flips delivered with slack_ts and delivered_at',
    ack.delivered === true && delivered.state === 'delivered' && delivered.slack_ts === '9.9' && typeof delivered.delivered_at === 'string' && delivered.delivered_at.length > 0,
    { ack, delivered });

  const { send: boom } = makeSend([{ throw: 'ECONNRESET' }]);
  const netStore = tmpStore();
  const netBox = createOutbox({ storePath: netStore, send: boom });
  const net = await netBox.post({
    kind: 'alarm', channel_id: 'C2', thread_ts: null, payload: 'boom',
  });
  const netRec = netBox.get(net.outbox_id);
  check('network error stays pending-delivery with last_error',
    net.delivered === false && netRec.state === 'pending-delivery' && netRec.last_error === 'ECONNRESET' && netRec.attempt_count === 1,
    { net, netRec });

  const qStore = tmpStore();
  const qBox = createOutbox({
    storePath: qStore,
    send: async () => ({ delivered: true, ts: 'tok' }),
    now: (() => {
      let t = 0;
      return () => `2026-08-24T00:00:0${t += 1}Z`;
    })(),
  });
  await qBox.post({ kind: 'ask', channel_id: 'CA', payload: 'a1', goal_id: 'gA', ask_id: 'ask-1' });
  await qBox.post({ kind: 'digest', channel_id: 'CB', payload: 'd1', goal_id: 'gB' });
  await qBox.post({ kind: 'notification', channel_id: 'CA', payload: 'n1', goal_id: 'gA' });
  const failBox = createOutbox({
    storePath: qStore,
    send: async () => ({ delivered: false, error: 'rate_limited' }),
  });
  await failBox.post({ kind: 'nack', channel_id: 'CC', payload: 'nope', ask_id: 'ask-2' });

  const live = createOutbox({ storePath: qStore, send: async () => ({ delivered: true, ts: 'x' }) });
  const byStatePending = live.query({ state: 'pending-delivery' });
  const byStateDelivered = live.query({ state: 'delivered' });
  const byKind = live.query({ kind: 'ask' });
  const byChannel = live.query({ channel_id: 'CA' });
  const byGoal = live.query({ goal_id: 'gA' });
  const byAsk = live.query({ ask_id: 'ask-1' });
  const newest = live.query({});
  const got = live.get(byKind[0].outbox_id);

  check('query state=pending-delivery',
    byStatePending.length === 1 && byStatePending[0].kind === 'nack',
    { byStatePending });
  check('query state=delivered',
    byStateDelivered.length === 3 && byStateDelivered.every((r) => r.state === 'delivered'),
    { n: byStateDelivered.length });
  check('query kind=ask',
    byKind.length === 1 && byKind[0].payload === 'a1',
    { byKind });
  check('query channel_id',
    byChannel.length === 2 && byChannel.every((r) => r.channel_id === 'CA'),
    { byChannel });
  check('query goal_id',
    byGoal.length === 2 && byGoal.every((r) => r.goal_id === 'gA'),
    { byGoal });
  check('query ask_id',
    byAsk.length === 1 && byAsk[0].ask_id === 'ask-1',
    { byAsk });
  check('query newest-first',
    newest.length === 4
      && newest[0].created_at >= newest[1].created_at
      && newest[1].created_at >= newest[2].created_at
      && newest[2].created_at >= newest[3].created_at,
    { created: newest.map((r) => r.created_at) });
  check('get-by-outbox_id',
    !!got && got.outbox_id === byKind[0].outbox_id && got.kind === 'ask',
    { got });

  const src = fs.readFileSync(path.join(__dirname, '..', 'outbox.js'), 'utf8');
  check('outbox path has no strike increment',
    !/\bstrike\b/.test(src),
    { hit: /\bstrike\b/.test(src) });

  check('kinds and states match §7.1',
    KINDS.join(',') === 'ask,alarm,digest,completion,nack,closing,notification'
      && STATES.join(',') === 'pending-delivery,delivered',
    { KINDS, STATES });

  const p = outboxStorePath('/tmp/ws');
  check('store path uses state-store runtime home',
    p === path.resolve('/tmp/ws', '.rbtv', 'runtime', 'ignite', 'outbox.json'),
    { p });

  check('send received spec payload as Slack text',
    calls[0] && calls[0].channel === 'C1' && calls[0].text === 'hello',
    { calls });

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: { probe: 'probe-chat-outbox', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-chat-outbox EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

main().catch((err) => {
  process.stdout.write(`PROBE probe-chat-outbox EXIT=1 ERROR=${err && err.stack ? err.stack : err}\n`);
  process.exit(1);
});
