#!/usr/bin/env node
'use strict';

// Suite for live status: the Slack connector's display (lib/live-status.js), Ignite's states
// (live-status.js), the service's ticker (status-ticker.js) and `ignite status`. Time is a fake
// clock; Slack is a stand-in that keeps each message's reactions in Slack's order.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Store } = require('./store.js');
const live = require('./live-status.js');
const { createTicker } = require('./status-ticker.js');
const { main } = require('./cli.js');
const { ignitePaths } = require('./config.js');
const { liveStatus } = require('../../../../../connectors/slack/capabilities/tools/slack/lib/live-status.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

function clock(start = 1_000_000) {
  let t = start;
  return { now: () => t, advance(ms) { t += ms; } };
}

const FRAMES = new Set(['clock12', 'clock130', 'clock3', 'clock430', 'clock6', 'clock730', 'clock9', 'clock1030',
  'mag', 'mag_right', 'brain', 'thought_balloon', 'hammer', 'hammer_and_wrench', 'busts_in_silhouette',
  'bust_in_silhouette', 'zzz', 'sleeping']);
const TASKS = new Set(['white_check_mark', 'warning', 'question', 'black_square_for_stop']);
const SYSTEMS = new Set(['hourglass_flowing_sand', 'large_green_circle', 'repeat', 'recycle', 'x']);

// A faithful Slack: adding a reaction twice and removing an absent one are errors, an add goes to
// the right end. After every call it checks that a message never holds two system emoji, two agent
// frames, or an agent frame together with a task emoji.
function fakeSlack(t, carried = null) {
  const slack = {
    on: carried ? carried.on : new Map(),
    calls: [],
    adds: [],
    violations: [],
    fail: null,
    of(channel, ts) { return [...(slack.on.get(`${channel}:${ts}`) || [])]; },
    check(key) {
      const names = slack.on.get(key) || [];
      const frames = names.filter((n) => FRAMES.has(n)).length;
      const tasks = names.filter((n) => TASKS.has(n)).length;
      const systems = names.filter((n) => SYSTEMS.has(n)).length;
      if (frames > 1 || tasks > 1 || systems > 1 || (frames && tasks)) slack.violations.push(`${key}: ${names.join(' ')}`);
    },
    async addReaction(channel, ts, name) {
      const key = `${channel}:${ts}`;
      slack.calls.push(`add ${name}`);
      if (slack.fail) { const error = slack.fail('add', name); if (error) throw error; }
      const names = slack.on.get(key) || [];
      slack.on.set(key, names);
      if (names.includes(name)) throw new Error('Slack reactions.add: already_reacted');
      names.push(name);
      slack.adds.push({ key, name, at: t.now() });
      slack.check(key);
    },
    async removeReaction(channel, ts, name) {
      const key = `${channel}:${ts}`;
      slack.calls.push(`remove ${name}`);
      if (slack.fail) { const error = slack.fail('remove', name); if (error) throw error; }
      const names = slack.on.get(key) || [];
      if (!names.includes(name)) throw new Error('Slack reactions.remove: no_reaction');
      names.splice(names.indexOf(name), 1);
      slack.check(key);
    },
  };
  return slack;
}

function display(t, slack, log) {
  return liveStatus({
    addReaction: (c, ts, n) => slack.addReaction(c, ts, n),
    removeReaction: (c, ts, n) => slack.removeReaction(c, ts, n),
    now: t.now,
    log,
  });
}

// The least time between two adds on one message.
function smallestGap(slack) {
  let least = Infinity;
  const last = new Map();
  for (const { key, at } of slack.adds) {
    if (last.has(key)) least = Math.min(least, at - last.get(key));
    last.set(key, at);
  }
  return least;
}

// An agent store holding one owner message, accepted but not yet claimed.
function agentStore(channel = 'C1', ts = '1.1') {
  const store = new Store(':memory:');
  const key = `T1:${channel}:${ts}`;
  store.acceptOwnerInput({
    key, agent: 'a', workspace: 'T1', channel, rootTs: ts, activated: true,
    message: { id: ts, role: 'owner', text: 'hi', team: 'T1', channel, ts },
    payload: { text: 'hi', ts, threadTs: ts },
  });
  const message = { conversationKey: key, channel, ts };
  live.received(store, message);
  return { store, message, key };
}

// Claims the queued input and starts its turn, as turn-loop does.
function startTurn(box, now = Date.now()) {
  const claim = box.store.claimNext(now);
  live.started(box.store, live.messageOf(box.store, claim), claim.runId);
  return claim;
}

function endTurn(box, claim, disposition, { replies = 0 } = {}) {
  const work = box.store.finishRun(claim.runId, claim.nonce, {
    invocationNonce: claim.nonce, output: '{}', disposition, summary: 's',
    nextStep: disposition === 'continue' ? 'next' : null,
  });
  live.ended(box.store, box.message, disposition, live.taskOf(disposition, false), replies);
  return work;
}

async function run(ticker, t, ms, every = 100) {
  for (let spent = 0; spent < ms; spent += every) {
    t.advance(every);
    await ticker.step();
  }
}

function tickerFor(boxes, t, slack, logs = []) {
  return createTicker({
    stores: () => boxes.map((box, i) => ({ slug: `a${i}`, store: box.store })),
    slack: () => slack,
    now: t.now,
    log: (f) => logs.push(f),
  });
}

// ---- The Slack connector's display ----

test('each state change makes its calls in order, remove before add', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const show = display(t, slack);
  const m = { channel: 'C1', ts: '1.1' };
  show.set(m, { system: 'queued' });
  assert.deepEqual(await show.apply(m), { settled: true });
  t.advance(1000);
  show.set(m, { system: 'running', agent: 'working' });
  const waiting = await show.apply(m);
  assert.deepEqual(waiting, { settled: false, waitUntil: t.now() + 1000 });
  t.advance(1000);
  assert.deepEqual(await show.apply(m), { settled: true });
  t.advance(1200);
  show.tick(m);
  await show.apply(m);
  t.advance(1200);
  show.set(m, { system: 'running', agent: 'thinking' });
  await show.apply(m);
  t.advance(1200);
  show.tick(m);
  await show.apply(m);
  t.advance(1200);
  show.set(m, { system: 'running', agent: null, task: 'done' });
  await show.apply(m);
  assert.deepEqual(slack.calls, [
    'add hourglass_flowing_sand',
    'remove hourglass_flowing_sand', 'add large_green_circle',
    'add clock12',
    'remove clock12', 'add clock130',
    'remove clock130', 'add brain',
    'remove brain', 'add thought_balloon',
    'remove thought_balloon', 'add white_check_mark',
  ]);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'white_check_mark']);
  assert.deepEqual(slack.violations, []);
  assert.ok(smallestGap(slack) >= 1000);
});

test('every agent state has its frames and every task state its emoji', async () => {
  const frames = {
    working: ['clock12', 'clock130', 'clock3', 'clock430', 'clock6', 'clock730', 'clock9', 'clock1030'],
    gathering: ['mag', 'mag_right'],
    thinking: ['brain', 'thought_balloon'],
    making: ['hammer', 'hammer_and_wrench'],
    orchestrating: ['busts_in_silhouette', 'bust_in_silhouette'],
    waiting: ['zzz', 'sleeping'],
  };
  for (const [agent, names] of Object.entries(frames)) {
    const t = clock();
    const slack = fakeSlack(t);
    const show = display(t, slack);
    const m = { channel: 'C1', ts: '1.1' };
    show.set(m, { system: 'running', agent });
    const seen = [];
    for (let i = 0; i <= names.length; i++) {
      t.advance(1200);
      if (i) show.tick(m);
      await show.apply(m);
      if (!i) {
        t.advance(1000);
        await show.apply(m);
      }
      seen.push(slack.of('C1', '1.1')[1]);
    }
    assert.deepEqual(seen, [...names, names[0]], agent);
  }
  const tasks = { done: 'white_check_mark', caveats: 'warning', question: 'question', stopped: 'black_square_for_stop' };
  const systems = { queued: 'hourglass_flowing_sand', running: 'large_green_circle', fallback: 'repeat', retrying: 'recycle', failed: 'x' };
  for (const [task, name] of Object.entries(tasks)) {
    for (const [system, sys] of Object.entries(systems)) {
      const t = clock();
      const slack = fakeSlack(t);
      const show = display(t, slack);
      const m = { channel: 'C1', ts: '1.1' };
      show.set(m, { system, task });
      await show.apply(m);
      t.advance(1000);
      await show.apply(m);
      assert.deepEqual(slack.of('C1', '1.1'), [sys, name]);
    }
  }
});

test('a system change mid-turn and after delivery keeps the system on the left', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const show = display(t, slack);
  const m = { channel: 'C1', ts: '1.1' };
  show.set(m, { system: 'running', agent: 'working' });
  await show.apply(m);
  t.advance(1000);
  await show.apply(m);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'clock12']);
  // Mid-turn: the turn falls back to another model.
  t.advance(5000);
  show.set(m, { system: 'fallback', agent: 'working' });
  const first = await show.apply(m);
  assert.equal(first.settled, false);
  assert.deepEqual(slack.of('C1', '1.1'), ['clock12', 'repeat']);
  t.advance(1000);
  assert.equal((await show.apply(m)).settled, true);
  assert.deepEqual(slack.of('C1', '1.1'), ['repeat', 'clock12']);
  // After delivery: the task shows, then the system changes.
  t.advance(1200);
  show.set(m, { system: 'fallback', task: 'done' });
  await show.apply(m);
  t.advance(5000);
  show.set(m, { system: 'failed', task: 'done' });
  await show.apply(m);
  assert.deepEqual(slack.of('C1', '1.1'), ['white_check_mark', 'x']);
  t.advance(1000);
  await show.apply(m);
  assert.deepEqual(slack.of('C1', '1.1'), ['x', 'white_check_mark']);
  assert.deepEqual(slack.calls.slice(-6), [
    'remove clock12', 'add white_check_mark',
    'remove repeat', 'add x',
    'remove white_check_mark', 'add white_check_mark',
  ]);
  assert.deepEqual(slack.violations, []);
  assert.ok(smallestGap(slack) >= 1000);
});

test('a refused add waits with the remove paired to it; a failed turn removes the agent frame', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const show = display(t, slack);
  const m = { channel: 'C1', ts: '1.1' };
  show.set(m, { system: 'running', agent: 'working' });
  await show.apply(m);
  t.advance(1000);
  await show.apply(m);
  t.advance(1200);
  show.tick(m);
  const before = slack.calls.length;
  assert.deepEqual(await show.apply(m, { mayAdd: () => false }), { settled: false });
  assert.equal(slack.calls.length, before);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'clock12']);
  show.set(m, { system: 'retrying', agent: null });
  await show.apply(m);
  assert.deepEqual(slack.of('C1', '1.1'), ['recycle']);
  assert.deepEqual(slack.calls.slice(before), ['remove clock12', 'remove large_green_circle', 'add recycle']);
});

test('after a restart the agent frame is unknown: every frame of its state is removed, then one added', async () => {
  const t = clock();
  const before = fakeSlack(t);
  before.on.set('C1:1.1', ['large_green_circle', 'sleeping']);
  const slack = fakeSlack(t, before);
  const logs = [];
  const show = display(t, slack, (f) => logs.push(f));
  const m = { channel: 'C1', ts: '1.1' };
  show.assume(m, { system: 'running', agent: 'waiting' });
  assert.equal(show.settled(m), false);
  assert.equal(slack.calls.length, 0);
  await show.apply(m);
  assert.deepEqual(slack.calls, ['remove zzz', 'remove sleeping', 'add zzz']);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'zzz']);
  assert.deepEqual(logs, []);
  // A settled message assumed after a restart makes no call.
  const done = { channel: 'C1', ts: '2.2' };
  show.assume(done, { system: 'running', task: 'done' });
  assert.equal(show.settled(done), true);
});

test('reaction errors: expected codes pass silently, others are logged, 429 stops with Retry-After', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const logs = [];
  const show = display(t, slack, (f) => logs.push(f));
  const m = { channel: 'C1', ts: '1.1' };
  slack.fail = (op) => (op === 'add' ? new Error('Slack reactions.add: invalid_name') : null);
  show.set(m, { system: 'queued' });
  assert.deepEqual(await show.apply(m), { settled: true });
  assert.deepEqual(logs.map((f) => [f.event, f.step, f.name]), [['reaction-failed', 'add', 'hourglass_flowing_sand']]);
  slack.fail = () => Object.assign(new Error('Slack reactions.add: HTTP 429'), { status: 429, retryAfter: 12 });
  t.advance(1000);
  show.set(m, { system: 'running' });
  assert.deepEqual(await show.apply(m), { settled: false, retryAfterMs: 12_000 });
  slack.fail = () => new Error('Slack reactions.remove: ratelimited');
  assert.deepEqual(await show.apply(m), { settled: false, retryAfterMs: 30_000 });
  slack.fail = null;
  t.advance(1000);
  assert.deepEqual(await show.apply(m), { settled: true });
  assert.equal(logs.length, 1);
});

// ---- The service's ticker over Ignite's stored states ----

test('ticker: queued, then working by default at turn start, then frames every 1.33 s for one message', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  const ticker = tickerFor([box], t, slack);
  await run(ticker, t, 500);
  assert.deepEqual(slack.of('C1', '1.1'), ['hourglass_flowing_sand']);
  startTurn(box);
  // The green circle waits 1 s after the hourglass, the first frame 1 s after the green circle.
  await run(ticker, t, 2500);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'clock12']);
  assert.deepEqual(slack.calls, ['add hourglass_flowing_sand', 'remove hourglass_flowing_sand', 'add large_green_circle', 'add clock12']);
  slack.adds.length = 0;
  await run(ticker, t, 60_000);
  // One message alone wants 50 frames a minute at 1.2 s; the budget of 45 stretches it to 1.33 s.
  assert.ok(slack.adds.length <= 45 && slack.adds.length >= 43, String(slack.adds.length));
  assert.ok(smallestGap(slack) >= 1300, String(smallestGap(slack)));
  assert.deepEqual(slack.violations, []);
});

test('ticker: the shared budget slows the ticks of several running messages', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const boxes = [agentStore('C1'), agentStore('C2'), agentStore('C3')];
  const ticker = tickerFor(boxes, t, slack);
  for (const box of boxes) startTurn(box);
  await run(ticker, t, 5000);
  slack.adds.length = 0;
  await run(ticker, t, 120_000);
  // Every minute window holds at most 45 adds across the three.
  for (let i = 0; i < slack.adds.length; i++) {
    const windowAdds = slack.adds.filter((a) => a.at > slack.adds[i].at - 60_000 && a.at <= slack.adds[i].at);
    assert.ok(windowAdds.length <= 45, String(windowAdds.length));
  }
  const perMessage = ['C1:1.1', 'C2:1.1', 'C3:1.1'].map((key) => slack.adds.filter((a) => a.key === key).length);
  for (const n of perMessage) assert.ok(n >= 28 && n <= 31, String(perMessage));
  // Each frame lasts three times as long as it does alone: 3 × 1.33 s.
  assert.ok(smallestGap(slack) >= 3900, String(smallestGap(slack)));
});

test('ticker: a burst of state changes waits for the shared budget of 45 adds a minute', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const boxes = Array.from({ length: 50 }, (_, i) => agentStore(`C${i}`));
  const ticker = tickerFor(boxes, t, slack);
  await run(ticker, t, 59_000);
  assert.equal(slack.adds.length, 45);
  await run(ticker, t, 3_000);
  assert.equal(slack.adds.length, 50);
  assert.ok(slack.adds.every((a) => a.name === 'hourglass_flowing_sand'));
});

test('ticker: HTTP 429 stops every reaction call until Retry-After has passed', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const logs = [];
  const box = agentStore();
  const ticker = tickerFor([box], t, slack, logs);
  startTurn(box);
  await run(ticker, t, 3000);
  let limited = null;
  slack.fail = (op) => {
    if (op !== 'add' || limited) return null;
    limited = t.now();
    return Object.assign(new Error('Slack reactions.add: HTTP 429'), { status: 429, retryAfter: 30 });
  };
  await run(ticker, t, 5000);
  assert.ok(limited);
  const calls = slack.calls.length;
  await run(ticker, t, 29_000 - (t.now() - limited));
  assert.equal(slack.calls.length, calls);
  await run(ticker, t, 3000);
  assert.ok(slack.calls.length > calls);
  assert.deepEqual(logs.filter((f) => f.event === 'reactions-paused'), [{ event: 'reactions-paused', ms: 30_000 }]);
});

test('ticker: ticking stops when the turn ends and when it fails', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  const ticker = tickerFor([box], t, slack);
  const claim = startTurn(box);
  await run(ticker, t, 5000);
  assert.ok(slack.adds.length >= 4);
  // The turn ends with replies still to deliver: the frame stays, still.
  endTurn(box, claim, 'completed', { replies: 1 });
  await run(ticker, t, 200);
  const frozen = slack.calls.length;
  const shown = slack.of('C1', '1.1');
  await run(ticker, t, 10_000);
  assert.equal(slack.calls.length, frozen);
  assert.deepEqual(slack.of('C1', '1.1'), shown);
  // Delivery: the frame gives way to the task.
  live.delivered(box.store, { channel: 'C1', ts: '1.1', task: 'done' });
  await run(ticker, t, 1500);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'white_check_mark']);

  // A second message whose turn fails: the frame goes and nothing ticks.
  const other = agentStore('C2');
  const ticker2 = tickerFor([other], t, slack);
  const failing = startTurn(other);
  await run(ticker2, t, 5000);
  const failure = other.store.failRun(failing.runId, 'boom', { now: t.now() });
  live.failed(other.store, other.message, failure.held);
  await run(ticker2, t, 1500);
  assert.deepEqual(slack.of('C2', '1.1'), ['recycle']);
  const after = slack.calls.length;
  await run(ticker2, t, 10_000);
  assert.equal(slack.calls.length, after);
  assert.deepEqual(slack.violations, []);
});

test('ticker: waiting_workers shows waiting, no task, ticking slowly until the wake turn; it survives a restart', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  const ticker = tickerFor([box], t, slack);
  const claim = startTurn(box);
  await run(ticker, t, 3000);
  endTurn(box, claim, 'waiting_workers', { replies: 1 });
  live.delivered(box.store, { channel: 'C1', ts: '1.1' });
  await run(ticker, t, 1500);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'zzz']);
  slack.adds.length = 0;
  await run(ticker, t, 31_000);
  assert.deepEqual(slack.adds.map((a) => a.name), ['sleeping', 'zzz', 'sleeping']);
  assert.ok(smallestGap(slack) >= 10_000);

  // The service restarts: a new ticker with no memory of what was shown resumes the slow tick.
  const restarted = fakeSlack(t, slack);
  const again = tickerFor([box], t, restarted);
  again.baseline();
  assert.deepEqual(restarted.calls, []);
  await run(again, t, 500);
  assert.deepEqual(restarted.calls, ['remove zzz', 'remove sleeping', 'add zzz']);
  assert.deepEqual(restarted.of('C1', '1.1'), ['large_green_circle', 'zzz']);
  restarted.adds.length = 0;
  await run(again, t, 21_000);
  assert.deepEqual(restarted.adds.map((a) => a.name), ['sleeping', 'zzz']);

  // The worker's wake starts the next turn: working again.
  assert.equal(box.store.wake({ conversationKey: box.key, note: 'done' }).inserted, true);
  const wake = box.store.claimNext(Date.now() + 1000);
  assert.equal(wake.kind, 'wake');
  live.started(box.store, live.messageOf(box.store, wake), wake.runId);
  await run(again, t, 600);
  assert.deepEqual(restarted.of('C1', '1.1'), ['large_green_circle', 'clock12']);
  assert.deepEqual(slack.violations, []);
  assert.deepEqual(restarted.violations, []);
});

test('ticker: continue keeps working, still, until the next turn runs', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  const ticker = tickerFor([box], t, slack);
  const claim = startTurn(box);
  await run(ticker, t, 3000);
  box.store.setLiveStatus({ channel: 'C1', ts: '1.1', agent: 'making' });
  await run(ticker, t, 1500);
  endTurn(box, claim, 'continue');
  assert.deepEqual(box.store.getLiveStatus('C1', '1.1').agent, 'working');
  await run(ticker, t, 1500);
  const between = slack.calls.length;
  assert.equal(slack.of('C1', '1.1')[1].startsWith('clock'), true);
  await run(ticker, t, 5000);
  assert.equal(slack.calls.length, between);
  const next = box.store.claimNext(Date.now() + 1000);
  assert.equal(next.kind, 'continue');
  live.started(box.store, live.messageOf(box.store, next), next.runId);
  await run(ticker, t, 5000);
  assert.ok(slack.calls.length > between);
  assert.equal(slack.of('C1', '1.1')[0], 'large_green_circle');
});

test('ticker: reaction errors are logged and never throw', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const logs = [];
  const box = agentStore();
  const ticker = tickerFor([box], t, slack, logs);
  slack.fail = () => new Error('network down');
  startTurn(box);
  await run(ticker, t, 3000);
  assert.ok(logs.some((f) => f.event === 'reaction-failed' && f.message === 'network down'));
  const broken = createTicker({ stores: () => { throw new Error('no stores'); }, slack: () => slack, now: t.now, log: (f) => logs.push(f) });
  await broken.step();
  assert.ok(logs.some((f) => f.event === 'status-failed' && f.message === 'no stores'));
  const none = createTicker({ stores: () => [{ slug: 'a', store: box.store }], slack: () => ({ addReaction() {} }), now: t.now });
  await none.step();
});

// ---- ignite status ----

function turnHome() {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-status-'));
  const store = new Store(ignitePaths(home).database);
  const box = { store, key: 'T1:C1:1.1' };
  for (const ts of ['1.1', '2.2']) {
    store.acceptOwnerInput({
      key: box.key, agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true,
      message: { id: ts, role: 'owner', text: 'hi', team: 'T1', channel: 'C1', ts },
      payload: { text: 'hi', ts, threadTs: '1.1' },
    });
  }
  const first = store.claimNext(Date.now());
  live.started(store, live.messageOf(store, first), first.runId);
  endTurn({ store, message: { conversationKey: box.key, channel: 'C1', ts: '1.1' } }, first, 'waiting_owner', { replies: 1 });
  live.delivered(store, { channel: 'C1', ts: '1.1', task: 'question' });
  const second = store.claimNext(Date.now() + 1000);
  live.started(store, live.messageOf(store, second), second.runId);
  return { home, store, ...box };
}

function status(argv, env) {
  const out = [];
  try {
    const code = main(['status', ...argv], { env, stdout: (text) => out.push(text) });
    return { code, out: out.join(''), err: '' };
  } catch (error) {
    return { code: error.exitCode || 1, out: out.join(''), err: error.message };
  }
}

test('ignite status: refuses an unknown state, outside a turn and a missing --message, changing nothing', async () => {
  const box = turnHome();
  try {
    const env = { RBTV_AGENT_HOME: box.home, IGNITE_CONVERSATION: box.key };
    const before = box.store.liveStatuses().map((row) => row.rev).join();
    const bad = status(['working'], env);
    assert.equal(bad.code, 1);
    assert.match(bad.err, /^unknown state: working\nchoose from gathering, thinking, making, orchestrating\n/);
    assert.match(status(['waiting'], env).err, /unknown state: waiting/);
    assert.match(status([], env).err, /status requires a state: gathering, thinking, making, orchestrating/);
    assert.match(status(['thinking', 'making'], env).err, /unexpected word 'making'/);
    assert.match(status(['--task', 'finished', '--message', '1.1'], env).err, /unknown task state: finished\nchoose from done, caveats, question, stopped/);
    assert.match(status(['--task', 'done'], env).err, /--task requires --message/);
    assert.match(status(['--message', '1.1'], env).err, /--message requires --task/);
    assert.match(status(['thinking'], { RBTV_AGENT_HOME: box.home }).err, /runs inside a turn: IGNITE_CONVERSATION is not set/);
    assert.match(status(['thinking'], { ...env, IGNITE_CONVERSATION: 'T1:C9:9.9' }).err, /the running turn belongs to T1:C1:1.1/);
    assert.match(status(['--task', 'done', '--message', '2.2'], env).err, /this turn's own message takes its task state from RESULT_FILE/);
    assert.match(status(['--task', 'done', '--message', '7.7'], env).err, /no owner message 7.7 in conversation T1:C1:1.1/);
    assert.equal(box.store.liveStatuses().map((row) => row.rev).join(), before);
    assert.match(status(['-h'], env).out, /^ignite status — show the owner what this turn is doing/);
    // The words are refused before the agent home is opened: a missing home is never reached.
    const missing = path.join(box.home, 'no-such-agent');
    assert.match(status(['bogus'], { RBTV_AGENT_HOME: missing, IGNITE_CONVERSATION: box.key }).err, /^unknown state: bogus\n/);
    assert.equal(fs.existsSync(missing), false);
  } finally {
    box.store.close();
    fs.rmSync(box.home, { recursive: true, force: true });
  }
});

test('ignite status: declares the running turn\'s state and sets an earlier message\'s task', async () => {
  const box = turnHome();
  try {
    const env = { RBTV_AGENT_HOME: box.home, IGNITE_CONVERSATION: box.key };
    for (const state of ['gathering', 'thinking', 'making', 'orchestrating']) {
      const done = status([state], env);
      assert.equal(done.code, 0, done.err);
      assert.equal(done.out, `${state} shown on 2.2\n`);
      assert.equal(box.store.getLiveStatus('C1', '2.2').agent, state);
    }
    const json = status(['thinking', '--json'], env);
    assert.deepEqual(JSON.parse(json.out), { state: 'thinking', message: '2.2' });
    assert.deepEqual({ ...box.store.getLiveStatus('C1', '1.1') }.task, 'question');
    const marked = status(['--task', 'done', '--message', '1.1'], env);
    assert.equal(marked.code, 0, marked.err);
    assert.equal(marked.out, 'task done shown on 1.1\n');
    const row = box.store.getLiveStatus('C1', '1.1');
    assert.deepEqual([row.system, row.agent, row.task], ['running', null, 'done']);
    // A turn that answers no owner message has nowhere to show the state.
    const run = box.store.getActiveRun();
    box.store.db.prepare('UPDATE live_status SET run_id=NULL WHERE run_id=?').run(run.id);
    const nowhere = status(['making'], env);
    assert.equal(nowhere.code, 0);
    assert.equal(nowhere.out, 'nothing shown: this turn answers no owner message\n');
  } finally {
    box.store.close();
    fs.rmSync(box.home, { recursive: true, force: true });
  }
});

test('taskOf: the task state each disposition gives', () => {
  assert.equal(live.taskOf('completed', false), 'done');
  assert.equal(live.taskOf('completed', true), 'caveats');
  assert.equal(live.taskOf('waiting_owner', false), 'question');
  assert.equal(live.taskOf('stopped', false), 'stopped');
  assert.equal(live.taskOf('continue', false), null);
  assert.equal(live.taskOf('waiting_workers', false), null);
});

(async () => {
  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      await fn();
      process.stdout.write(`PASS ${name}\n`);
    } catch (error) {
      failed += 1;
      process.stdout.write(`FAIL ${name}: ${error.stack || error.message}\n`);
    }
  }
  process.stdout.write(`live-status: ${tests.length - failed} passed, ${failed} failed\n`);
  process.exit(failed ? 1 : 0);
})();
