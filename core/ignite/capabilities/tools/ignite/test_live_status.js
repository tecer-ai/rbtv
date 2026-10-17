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
const { createTicker, CALL_MS } = require('./status-ticker.js');
const { deliverPending, RETRY_MS } = require('./outbox.js');
const { main } = require('./cli.js');
const { ignitePaths } = require('./config.js');
const { createLegend } = require('./legend.js');
const { liveStatus, legendView, EMOJI } = require('../../../../../connectors/slack/capabilities/tools/slack/lib/live-status.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

function clock(start = 1_000_000) {
  let t = start;
  return { now: () => t, advance(ms) { t += ms; } };
}

const FRAMES = new Set(['clock12', 'clock2', 'clock4', 'clock6', 'clock8', 'clock10',
  'mag', 'mag_right', 'brain', 'thought_balloon', 'hammer', 'hammer_and_wrench', 'busts_in_silhouette',
  'bust_in_silhouette', 'zzz', 'sleeping', 'microphone', 'memo']);
const TASKS = new Set(['white_check_mark', 'warning', 'question', 'black_square_for_stop']);
const SYSTEMS = new Set(['hourglass_flowing_sand', 'large_green_circle', 'repeat', 'recycle', 'x']);

// A faithful Slack: adding a reaction twice and removing an absent one are errors, an add goes to
// the right end. After every call it checks that a message never holds two system emoji, two agent
// frames, an agent frame together with a task emoji, or a system emoji right of another, and keeps
// the names the message then holds (seen). hang(op, name, key) makes Slack apply a call and never answer,
// as when the service stops mid-call; wait holds every add until it settles. trail keeps each call with
// the message it touches, as channel:ts.
function fakeSlack(t, carried = null) {
  const slack = {
    on: carried ? carried.on : new Map(),
    calls: [],
    trail: [],
    adds: [],
    seen: [],
    violations: [],
    fail: null,
    hang: null,
    wait: null,
    of(channel, ts) { return [...(slack.on.get(`${channel}:${ts}`) || [])]; },
    check(key) {
      const names = slack.on.get(key) || [];
      const frames = names.filter((n) => FRAMES.has(n)).length;
      const tasks = names.filter((n) => TASKS.has(n)).length;
      const systems = names.filter((n) => SYSTEMS.has(n)).length;
      const systemRight = names.findLastIndex((n) => SYSTEMS.has(n)) > names.findIndex((n) => !SYSTEMS.has(n))
        && names.some((n) => !SYSTEMS.has(n));
      if (frames > 1 || tasks > 1 || systems > 1 || (frames && tasks) || systemRight) {
        slack.violations.push(`${key}: ${names.join(' ')}`);
      }
      slack.seen.push([...names]);
    },
    async addReaction(channel, ts, name) {
      const key = `${channel}:${ts}`;
      slack.calls.push(`add ${name}`);
      slack.trail.push(`add ${key} ${name}`);
      if (slack.wait) await slack.wait;
      if (slack.fail) { const error = slack.fail('add', name); if (error) throw error; }
      const names = slack.on.get(key) || [];
      slack.on.set(key, names);
      if (names.includes(name)) throw new Error('Slack reactions.add: already_reacted');
      names.push(name);
      slack.adds.push({ key, name, at: t.now() });
      slack.check(key);
      if (slack.hang?.('add', name, key)) await new Promise(() => {});
    },
    async removeReaction(channel, ts, name) {
      const key = `${channel}:${ts}`;
      slack.calls.push(`remove ${name}`);
      slack.trail.push(`remove ${key} ${name}`);
      if (slack.fail) { const error = slack.fail('remove', name); if (error) throw error; }
      const names = slack.on.get(key) || [];
      if (!names.includes(name)) throw new Error('Slack reactions.remove: no_reaction');
      names.splice(names.indexOf(name), 1);
      slack.check(key);
      if (slack.hang?.('remove', name, key)) await new Promise(() => {});
    },
  };
  return slack;
}

function display(t, slack, log, record) {
  return liveStatus({
    addReaction: (c, ts, n) => slack.addReaction(c, ts, n),
    removeReaction: (c, ts, n) => slack.removeReaction(c, ts, n),
    now: t.now,
    log,
    record,
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

// An agent store holding one owner message, accepted but not yet claimed; in memory unless a
// database file is given.
function agentStore(channel = 'C1', ts = '1.1', database = ':memory:') {
  const store = new Store(database);
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
  live.ended(box.store, live.messageOf(box.store, claim), disposition, live.taskOf(disposition, false), replies);
  return work;
}

// The owner writes ts in box's thread, accepted as ingress accepts it.
function ownerWrites(box, ts) {
  const { channel } = box.message;
  box.store.acceptOwnerInput({
    key: box.key, agent: 'a', workspace: 'T1', channel, rootTs: box.message.ts, activated: true,
    message: { id: ts, role: 'owner', text: 'more', team: 'T1', channel, ts },
    payload: { text: 'more', ts, threadTs: box.message.ts },
  });
  live.received(box.store, { conversationKey: box.key, channel, ts });
}

// A reply of claim's turn delivered at ts into box's thread, as outbox.js reports it: task when it is
// the turn's last reply. With no claim, a post.
function replyDelivered(box, claim, ts, task = null) {
  const answer = claim ? { ts: live.messageOf(box.store, claim).ts, runId: claim.runId, ...(task && { task }) } : null;
  return live.delivered(box.store, { conversationKey: box.key, channel: box.message.channel, messages: [ts] }, answer);
}

// What each message shows, by its ts.
function shows(slack, tss, channel = 'C1') {
  return Object.fromEntries(tss.map((ts) => [ts, slack.of(channel, ts)]));
}

async function run(ticker, t, ms, every = 100) {
  for (let spent = 0; spent < ms; spent += every) {
    t.advance(every);
    await ticker.step();
  }
}

// As run, for a ticker whose pass may never end (a call Slack never answers): each pass gets until
// its calls have no more to do, not until it ends.
async function runCut(ticker, t, ms, every = 100) {
  for (let spent = 0; spent < ms; spent += every) {
    t.advance(every);
    ticker.step();
    await new Promise((resolve) => setImmediate(resolve));
  }
}

function tickerFor(boxes, t, slack, logs = [], pace = undefined) {
  return createTicker({
    stores: () => boxes.map((box, i) => ({ slug: `a${i}`, store: box.store })),
    slack: () => slack,
    now: t.now,
    log: (f) => logs.push(f),
    pace,
  });
}

// The pace a service keeps across a restart, held here in memory.
function keptPace() {
  let kept = null;
  return { load: () => kept, save(state) { kept = JSON.parse(JSON.stringify(state)); } };
}

// The shown reactions a message's row records.
function recorded(box, ts = '1.1', channel = box.message.channel) {
  return JSON.parse(box.store.getLiveStatus(channel, ts).shown);
}

function layers(store, ts, channel = 'C1') {
  const row = store.getLiveStatus(channel, ts);
  return { system: row.system, agent: row.agent, task: row.task };
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
    'remove clock12', 'add clock2',
    'remove clock2', 'add brain',
    'remove brain', 'add thought_balloon',
    'remove thought_balloon', 'add white_check_mark',
  ]);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'white_check_mark']);
  assert.deepEqual(slack.violations, []);
  assert.ok(smallestGap(slack) >= 1000);
});

test('every agent state has its frames and every task state its emoji', async () => {
  const frames = {
    working: ['clock12', 'clock2', 'clock4', 'clock6', 'clock8', 'clock10'],
    gathering: ['mag', 'mag_right'],
    thinking: ['brain', 'thought_balloon'],
    making: ['hammer', 'hammer_and_wrench'],
    orchestrating: ['busts_in_silhouette', 'bust_in_silhouette'],
    waiting: ['zzz', 'sleeping'],
    transcribing: ['microphone', 'memo'],
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

test('a system change keeps the system on the left at every moment, mid-turn and after delivery', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const show = display(t, slack);
  const m = { channel: 'C1', ts: '1.1' };
  show.set(m, { system: 'running', agent: 'working' });
  await show.apply(m);
  t.advance(1000);
  await show.apply(m);
  // Mid-turn: the turn falls back to another model. The frame goes first, then the system is
  // replaced, and the frame comes back one add gap later.
  t.advance(5000);
  show.set(m, { system: 'fallback', agent: 'working' });
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 1000 });
  t.advance(1000);
  assert.deepEqual(await show.apply(m), { settled: true });
  // After delivery: the task shows, then the system changes.
  t.advance(1200);
  show.set(m, { system: 'fallback', task: 'done' });
  await show.apply(m);
  t.advance(5000);
  show.set(m, { system: 'failed', task: 'done' });
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 1000 });
  t.advance(1000);
  assert.deepEqual(await show.apply(m), { settled: true });
  assert.deepEqual(slack.calls, [
    'add large_green_circle', 'add clock12',
    'remove clock12', 'remove large_green_circle', 'add repeat', 'add clock12',
    'remove clock12', 'add white_check_mark',
    'remove white_check_mark', 'remove repeat', 'add x', 'add white_check_mark',
  ]);
  // What the message holds after every call: no system emoji is ever right of another emoji.
  assert.deepEqual(slack.seen, [
    ['large_green_circle'], ['large_green_circle', 'clock12'],
    ['large_green_circle'], [], ['repeat'], ['repeat', 'clock12'],
    ['repeat'], ['repeat', 'white_check_mark'],
    ['repeat'], [], ['x'], ['x', 'white_check_mark'],
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

test('restore: a message starts from the reactions it records and finishes what a stopped service left', async () => {
  const t = clock();
  const before = fakeSlack(t);
  before.on.set('C1:1.1', ['large_green_circle', 'clock4']);
  before.on.set('C1:2.2', ['large_green_circle', 'mag']);
  before.on.set('C1:3.3', ['large_green_circle', 'clock2']);
  before.on.set('C1:4.4', ['large_green_circle', 'sleeping']);
  const slack = fakeSlack(t, before);
  const records = [];
  const show = display(t, slack, undefined, (message, shown) => records.push([message.ts, shown]));
  const at = t.now() - 5000;
  // Done was recorded, but the stopped service never showed it: the old frame goes, the task comes.
  const done = { channel: 'C1', ts: '1.1' };
  show.restore(done, { system: 'running', task: 'done' }, { order: ['large_green_circle', 'clock4'], unsure: [], lastAddAt: at });
  // Waiting was recorded while an earlier state's frame still shows.
  const waiting = { channel: 'C1', ts: '2.2' };
  show.restore(waiting, { system: 'running', agent: 'waiting' }, { order: ['large_green_circle', 'mag'], unsure: [], lastAddAt: at });
  // The service stopped while Slack had not answered an add: that name is removed before the frame.
  const cut = { channel: 'C1', ts: '3.3' };
  show.restore(cut, { system: 'running', agent: 'working' }, { order: ['large_green_circle'], unsure: ['clock2'], lastAddAt: at });
  // A message that shows its state makes no call, and its agent continues from the frame shown.
  const still = { channel: 'C1', ts: '4.4' };
  show.restore(still, { system: 'running', agent: 'waiting' }, { order: ['large_green_circle', 'sleeping'], unsure: [], lastAddAt: at });
  assert.deepEqual([done, waiting, cut, still].map((m) => show.settled(m)), [false, false, false, true]);
  assert.equal(slack.calls.length, 0);
  for (const m of [done, waiting, cut, still]) assert.deepEqual(await show.apply(m), { settled: true });
  assert.deepEqual(slack.calls, [
    'remove clock4', 'add white_check_mark',
    'remove mag', 'add zzz',
    'remove clock2', 'add clock12',
  ]);
  assert.deepEqual(['1.1', '2.2', '3.3', '4.4'].map((ts) => slack.of('C1', ts)), [
    ['large_green_circle', 'white_check_mark'],
    ['large_green_circle', 'zzz'],
    ['large_green_circle', 'clock12'],
    ['large_green_circle', 'sleeping'],
  ]);
  // Each call is recorded before it is made (its name unsure) and after Slack answers.
  assert.deepEqual(records.filter(([ts]) => ts === '1.1').map(([, shown]) => [shown.order, shown.unsure]), [
    [['large_green_circle'], ['clock4']],
    [['large_green_circle'], []],
    [['large_green_circle'], ['white_check_mark']],
    [['large_green_circle', 'white_check_mark'], []],
  ]);
  show.tick(still);
  t.advance(1000);
  await show.apply(still);
  assert.deepEqual(slack.of('C1', '4.4'), ['large_green_circle', 'zzz']);
  assert.deepEqual(slack.violations, []);
});

test('reaction errors: expected codes pass silently, others are logged and retried, 429 stops with Retry-After', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const logs = [];
  const show = display(t, slack, (f) => logs.push(f));
  const m = { channel: 'C1', ts: '1.1' };
  // A refused add is not taken as shown: its name may be on the message, so it is removed before
  // the add is tried again, after a wait.
  slack.fail = (op) => (op === 'add' ? new Error('Slack reactions.add: invalid_name') : null);
  show.set(m, { system: 'queued' });
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 1000 });
  assert.deepEqual(logs.map((f) => [f.event, f.step, f.name]), [['reaction-failed', 'add', 'hourglass_flowing_sand']]);
  slack.fail = null;
  t.advance(1000);
  assert.deepEqual(await show.apply(m), { settled: true });
  assert.deepEqual(slack.calls, ['add hourglass_flowing_sand', 'remove hourglass_flowing_sand', 'add hourglass_flowing_sand']);
  assert.deepEqual(slack.of('C1', '1.1'), ['hourglass_flowing_sand']);
  // HTTP 429 stops with its Retry-After, or 30 s without one; nothing changed, so nothing is unsure.
  slack.fail = () => Object.assign(new Error('Slack reactions.add: HTTP 429'), { status: 429, retryAfter: 12 });
  t.advance(1000);
  show.set(m, { system: 'running' });
  assert.deepEqual(await show.apply(m), { settled: false, retryAfterMs: 12_000 });
  assert.deepEqual(slack.of('C1', '1.1'), ['hourglass_flowing_sand']);
  slack.fail = () => new Error('Slack reactions.remove: ratelimited');
  assert.deepEqual(await show.apply(m), { settled: false, retryAfterMs: 30_000 });
  slack.fail = null;
  t.advance(1000);
  assert.deepEqual(await show.apply(m), { settled: true });
  assert.deepEqual(slack.calls.slice(3), [
    'remove hourglass_flowing_sand', 'remove hourglass_flowing_sand', 'remove hourglass_flowing_sand', 'add large_green_circle',
  ]);
  assert.equal(logs.length, 1);
  // A deleted message ends its calls.
  const gone = { channel: 'C1', ts: '9.9' };
  slack.fail = () => new Error('Slack reactions.add: message_not_found');
  show.set(gone, { system: 'queued' });
  assert.deepEqual(await show.apply(gone), { settled: true });
  assert.deepEqual(await show.apply(gone), { settled: true });
  assert.equal(slack.calls.filter((c) => c === 'add hourglass_flowing_sand').length, 3);
  assert.equal(logs.length, 1);
});

test('a failed remove keeps its name: nothing replaces it until Slack acknowledges the removal', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const logs = [];
  const show = display(t, slack, (f) => logs.push(f));
  const m = { channel: 'C1', ts: '1.1' };
  show.set(m, { system: 'running', agent: 'working' });
  await show.apply(m);
  t.advance(1000);
  await show.apply(m);
  // Delivery while Slack fails the frame's removal: the task waits, the frame stays the only one.
  slack.fail = (op) => (op === 'remove' ? new Error('fetch failed') : null);
  t.advance(1200);
  show.set(m, { system: 'running', task: 'done' });
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 1000 });
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'clock12']);
  const calls = slack.calls.length;
  // No call while it waits; each failure in a row doubles the wait.
  t.advance(500);
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 500 });
  assert.equal(slack.calls.length, calls);
  t.advance(500);
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 2000 });
  slack.fail = null;
  t.advance(2000);
  assert.deepEqual(await show.apply(m), { settled: true });
  assert.deepEqual(slack.calls.slice(calls - 1), ['remove clock12', 'remove clock12', 'remove clock12', 'add white_check_mark']);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'white_check_mark']);
  assert.deepEqual(logs.map((f) => [f.event, f.step, f.name, f.message]), [
    ['reaction-failed', 'remove', 'clock12', 'fetch failed'],
    ['reaction-failed', 'remove', 'clock12', 'fetch failed'],
  ]);
  // A failed tick removal: the next frame waits for it, so two frames never show.
  t.advance(5000);
  show.set(m, { system: 'running', agent: 'working' });
  await show.apply(m);
  t.advance(1200);
  show.tick(m);
  slack.fail = (op) => (op === 'remove' ? new Error('fetch failed') : null);
  assert.equal((await show.apply(m)).settled, false);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'clock12']);
  assert.deepEqual(slack.violations, []);
});

test('an HTTP 5xx pauses the calls briefly and leaves its name unsure', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const show = display(t, slack, () => {});
  const m = { channel: 'C1', ts: '1.1' };
  show.set(m, { system: 'running', agent: 'working' });
  await show.apply(m);
  t.advance(1000);
  await show.apply(m);
  t.advance(1200);
  show.tick(m);
  slack.fail = (op) => (op === 'remove' ? Object.assign(new Error('Slack reactions.remove: HTTP 503'), { status: 503 }) : null);
  assert.deepEqual(await show.apply(m), { settled: false, retryAfterMs: 5_000 });
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'clock12']);
  slack.fail = null;
  t.advance(5000);
  assert.deepEqual(await show.apply(m), { settled: true });
  assert.deepEqual(slack.calls.slice(2), ['remove clock12', 'remove clock12', 'add clock2']);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'clock2']);
});

test('an error inside apply waits before the next try instead of retrying at once', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const logs = [];
  const show = display(t, slack, (f) => logs.push(f), () => { throw new Error('disk full'); });
  const m = { channel: 'C1', ts: '1.1' };
  show.set(m, { system: 'queued' });
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 1000 });
  t.advance(250);
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 750 });
  t.advance(750);
  assert.deepEqual(await show.apply(m), { settled: false, waitUntil: t.now() + 2000 });
  // The record is made before the call: a call that cannot be recorded is never made.
  assert.deepEqual(slack.calls, []);
  assert.deepEqual(logs.map((f) => [f.event, f.message]), [['status-failed', 'disk full'], ['status-failed', 'disk full']]);
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
  // Delivery: the reply takes the live status, its task in place of the frame.
  replyDelivered(box, claim, '9.1', 'done');
  await run(ticker, t, 1500);
  assert.deepEqual(shows(slack, ['1.1', '9.1']), { 1.1: [], 9.1: ['large_green_circle', 'white_check_mark'] });

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
  endTurn(box, claim, 'waiting_workers');
  await run(ticker, t, 1500);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'zzz']);
  slack.adds.length = 0;
  await run(ticker, t, 31_000);
  assert.deepEqual(slack.adds.map((a) => a.name), ['sleeping', 'zzz', 'sleeping']);
  assert.ok(smallestGap(slack) >= 10_000);

  // The service restarts: a new ticker starts from the frame the row records as shown, makes no
  // call for it, and resumes the slow tick from there.
  assert.deepEqual(recorded(box), { order: ['large_green_circle', 'sleeping'], unsure: [], lastAddAt: slack.adds.at(-1).at, gone: false });
  const restarted = fakeSlack(t, slack);
  const again = tickerFor([box], t, restarted);
  await run(again, t, 500);
  assert.deepEqual(restarted.calls, []);
  await run(again, t, 21_000);
  assert.deepEqual(restarted.calls, ['remove sleeping', 'add zzz', 'remove zzz', 'add sleeping']);

  // The worker's wake starts the next turn: working again.
  assert.equal(box.store.wake({ conversationKey: box.key, note: 'done' }).inserted, true);
  const wake = box.store.claimNext(Date.now() + 1000);
  assert.equal(wake.kind, 'wake');
  live.started(box.store, live.messageOf(box.store, wake), wake.runId);
  await run(again, t, 1100);
  assert.deepEqual(restarted.of('C1', '1.1'), ['large_green_circle', 'clock12']);
  assert.deepEqual(slack.violations, []);
  assert.deepEqual(restarted.violations, []);
});

test('ticker: a restart finishes what the stopped service left: a recorded state, a call cut off', async () => {
  const t = clock();
  // Each message shows its first frame, then its service stops.
  const boxes = [agentStore('C1'), agentStore('C2'), agentStore('C3')];
  const slack = fakeSlack(t);
  const first = tickerFor(boxes, t, slack);
  const claims = boxes.map((box) => startTurn(box));
  await runCut(first, t, 2500);
  for (const box of boxes) assert.deepEqual(slack.of(box.message.channel, '1.1'), ['large_green_circle', 'clock12']);
  // C2 declares gathering and shows it. C1 and C3 tick (three share the budget: a frame every 4 s),
  // and C3's next frame reaches Slack, which never answers.
  boxes[1].store.setLiveStatus({ channel: 'C2', ts: '1.1', agent: 'gathering' });
  slack.hang = (op, name, key) => op === 'add' && key === 'C3:1.1';
  await runCut(first, t, 2000);
  assert.deepEqual(['C1', 'C2', 'C3'].map((channel) => slack.of(channel, '1.1')), [
    ['large_green_circle', 'clock2'],
    ['large_green_circle', 'mag'],
    ['large_green_circle', 'clock2'],
  ]);
  assert.deepEqual(recorded(boxes[2]).unsure, ['clock2']);
  // The service is gone. Meanwhile C1's reply is delivered (done), so the live status moves from its
  // owner message to the reply, and C2's turn ends waiting.
  endTurn(boxes[0], claims[0], 'completed', { replies: 1 });
  replyDelivered(boxes[0], claims[0], '9.1', 'done');
  endTurn(boxes[1], claims[1], 'waiting_workers', { replies: 0 });
  const restarted = fakeSlack(t, slack);
  const again = tickerFor(boxes, t, restarted);
  await run(again, t, 1200);
  // C3 added a frame less than a second before the stop: the gap it records holds it back. C1's owner
  // message only loses reactions; its reply is a new message with no gap to wait for.
  assert.deepEqual(restarted.trail, [
    'remove C1:1.1 clock2', 'remove C1:1.1 large_green_circle',
    'add C1:9.1 large_green_circle',
    'remove C2:1.1 mag', 'add C2:1.1 zzz',
    'remove C3:1.1 clock2', 'add C3:1.1 clock12',
    'add C1:9.1 white_check_mark',
  ]);
  assert.deepEqual(['C1', 'C2', 'C3'].map((channel) => restarted.of(channel, '1.1')), [
    [],
    ['large_green_circle', 'zzz'],
    ['large_green_circle', 'clock12'],
  ]);
  assert.deepEqual(restarted.of('C1', '9.1'), ['large_green_circle', 'white_check_mark']);
  assert.deepEqual(restarted.violations, []);
});

test('ticker: the 429 pause and the shared budget survive a restart', async () => {
  const t = clock();
  // The budget: 50 messages queued at once; the first service adds 45 of them, then stops.
  const pace = keptPace();
  const slack = fakeSlack(t);
  const boxes = Array.from({ length: 50 }, (_, i) => agentStore(`C${i}`));
  await run(tickerFor(boxes, t, slack, [], pace), t, 1000);
  assert.equal(slack.adds.length, 45);
  const restarted = fakeSlack(t, slack);
  const again = tickerFor(boxes, t, restarted, [], pace);
  await run(again, t, 57_000);
  assert.deepEqual(restarted.calls, []);
  await run(again, t, 3_000);
  assert.equal(restarted.adds.length, 5);

  // The pause: a 429 with Retry-After 30 s, then a restart 1 s later.
  const paced = keptPace();
  const box = agentStore();
  const limited = fakeSlack(t);
  limited.fail = () => Object.assign(new Error('Slack reactions.add: HTTP 429'), { status: 429, retryAfter: 30 });
  await run(tickerFor([box], t, limited, [], paced), t, 1000);
  assert.deepEqual(limited.calls, ['add hourglass_flowing_sand']);
  const next = fakeSlack(t, limited);
  const later = tickerFor([box], t, next, [], paced);
  await run(later, t, 28_000);
  assert.deepEqual(next.calls, []);
  await run(later, t, 2_000);
  assert.deepEqual(next.calls, ['add hourglass_flowing_sand']);
});

test('ticker: stop() lets the pass in flight finish its call and record it, and starts no other', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  let release;
  slack.wait = new Promise((resolve) => { release = resolve; });
  const ticker = tickerFor([box], t, slack);
  const pass = ticker.step();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(slack.calls, ['add hourglass_flowing_sand']);
  let stopped = false;
  const done = ticker.stop().then(() => { stopped = true; });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(stopped, false);
  release();
  await done;
  await pass;
  assert.deepEqual(recorded(box), { order: ['hourglass_flowing_sand'], unsure: [], lastAddAt: t.now(), gone: false });
  startTurn(box);
  t.advance(2000);
  await ticker.step();
  assert.deepEqual(slack.calls, ['add hourglass_flowing_sand']);
});

test('ticker: a row made before the shown column is an unknown display: every live status name is removed, then its state shows', async () => {
  const t = clock();
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-live-'));
  const file = path.join(dir, 'state.sqlite');
  try {
    new Store(file).close();
    const { DatabaseSync } = require('node:sqlite');
    const old = new DatabaseSync(file);
    old.exec('DROP TABLE live_status');
    old.exec(`CREATE TABLE live_status (channel TEXT NOT NULL, ts TEXT NOT NULL, conversation_key TEXT NOT NULL,
      system TEXT, agent TEXT, task TEXT, run_id TEXT, rev INTEGER NOT NULL, updated_at INTEGER NOT NULL,
      PRIMARY KEY (channel, ts))`);
    old.exec(`INSERT INTO live_status(channel, ts, conversation_key, system, agent, task, run_id, rev, updated_at)
      VALUES ('C1', '1.1', 'T1:C1:1.1', 'running', NULL, 'done', NULL, 1, 1)`);
    old.close();
    const store = new Store(file);
    try {
      assert.equal(store.getLiveStatus('C1', '1.1').shown, null);
      // Every row then was an owner message: the task it shows is the one it keeps.
      assert.deepEqual([store.getLiveStatus('C1', '1.1').kept, store.getLiveStatus('C1', '1.1').kept_for], ['done', '1.1']);
      // The service that made the row showed the green circle and a working frame.
      const slack = fakeSlack(t);
      slack.on.set('C1:1.1', ['large_green_circle', 'clock2']);
      await run(tickerFor([{ store }], t, slack), t, 3000);
      assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'white_check_mark']);
      assert.deepEqual(slack.calls, [
        'remove clock12', 'remove clock2', 'remove clock4', 'remove clock6', 'remove clock8', 'remove clock10',
        'remove mag', 'remove mag_right', 'remove brain', 'remove thought_balloon',
        'remove hammer', 'remove hammer_and_wrench', 'remove busts_in_silhouette', 'remove bust_in_silhouette',
        'remove zzz', 'remove sleeping', 'remove microphone', 'remove memo',
        'remove white_check_mark', 'remove warning', 'remove question',
        'remove black_square_for_stop', 'remove hourglass_flowing_sand', 'remove large_green_circle', 'remove repeat',
        'remove recycle', 'remove x', 'add large_green_circle', 'add white_check_mark',
      ]);
      const shown = JSON.parse(store.getLiveStatus('C1', '1.1').shown);
      assert.deepEqual([shown.order, shown.unsure], [['large_green_circle', 'white_check_mark'], []]);
      assert.deepEqual(slack.violations, []);
      // A row made now records that it shows nothing yet: its message makes no removal.
      const fresh = agentStore('C2');
      assert.equal(fresh.store.getLiveStatus('C2', '1.1').shown, '{}');
    } finally {
      store.close();
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('ticker: a reaction call is aborted after 4 s and by stop(), its name left unsure; no call starts after stop()', async () => {
  assert.equal(CALL_MS, 4000);
  const t = clock();
  const box = agentStore();
  const slack = fakeSlack(t);
  // Slack answers no add. As with fetch, an aborted request rejects with its signal's reason.
  const signals = [];
  slack.addReaction = (channel, ts, name, { signal } = {}) => {
    slack.calls.push(`add ${name}`);
    signals.push(signal);
    return new Promise((resolve, reject) => signal?.addEventListener('abort', () => reject(signal.reason)));
  };
  const logs = [];
  const failures = () => logs.filter((f) => f.event === 'reaction-failed').map((f) => f.message);
  const ticker = createTicker({ stores: () => [{ slug: 'a0', store: box.store }], slack: () => slack, now: t.now,
    log: (f) => logs.push(f), callMs: 20 });
  // The pass ends once the add, unanswered for callMs, is aborted.
  await ticker.step();
  assert.deepEqual(slack.calls, ['add hourglass_flowing_sand']);
  assert.equal(signals[0].aborted, true);
  assert.deepEqual(failures(), ['no answer from Slack in 20 ms']);
  assert.deepEqual(recorded(box).unsure, ['hourglass_flowing_sand']);
  // After the 1 s backoff the unsure name is removed and added again; stop() aborts that add.
  t.advance(1000);
  const pass = ticker.step();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(slack.calls, ['add hourglass_flowing_sand', 'remove hourglass_flowing_sand', 'add hourglass_flowing_sand']);
  await ticker.stop();
  await pass;
  assert.equal(signals[1].aborted, true);
  assert.deepEqual(failures(), ['no answer from Slack in 20 ms', 'the service stopped']);
  assert.deepEqual(recorded(box).unsure, ['hourglass_flowing_sand']);
  t.advance(5000);
  await ticker.step();
  assert.equal(slack.calls.length, 3);

  // A remove Slack answers after stop(): the add paired with it is never sent.
  const other = agentStore('C2');
  const second = fakeSlack(t);
  const shows = tickerFor([other], t, second);
  await run(shows, t, 500);
  startTurn(other);
  let answer;
  let sent = null;
  const answered = new Promise((resolve) => { answer = resolve; });
  const remove = second.removeReaction;
  second.removeReaction = async (channel, ts, name) => { sent = name; await answered; return remove(channel, ts, name); };
  t.advance(1000);
  const cut = shows.step();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(sent, 'hourglass_flowing_sand');
  const stopped = shows.stop();
  answer();
  await stopped;
  await cut;
  assert.deepEqual(second.calls, ['add hourglass_flowing_sand', 'remove hourglass_flowing_sand']);
  assert.deepEqual(second.of('C2', '1.1'), []);
});

test('ticker: an add is counted when it is sent: a slow remove before it never lets 46 adds into 60 s', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const boxes = Array.from({ length: 50 }, (_, i) => agentStore(`C${i}`));
  // C0 shows the hourglass a stopped service added; its turn starts, so the green circle replaces it.
  slack.on.set('C0:1.1', ['hourglass_flowing_sand']);
  boxes[0].store.setLiveShown('C0', '1.1', { order: ['hourglass_flowing_sand'], unsure: [] });
  startTurn(boxes[0]);
  // Slack takes 2 s to answer each of C0's removes.
  const remove = slack.removeReaction;
  slack.removeReaction = async (channel, ts, name) => {
    if (channel === 'C0') t.advance(2000);
    return remove(channel, ts, name);
  };
  await run(tickerFor(boxes, t, slack), t, 120_000);
  assert.deepEqual(slack.calls.slice(0, 3), ['remove hourglass_flowing_sand', 'add large_green_circle', 'add hourglass_flowing_sand']);
  const most = Math.max(...slack.adds.map((a) => slack.adds.filter((b) => b.at > a.at - 60_000 && b.at <= a.at).length));
  assert.equal(most, 45);
  assert.ok(slack.adds.length > 45, String(slack.adds.length));
});

test('ticker: waiting ends when its work no longer waits for workers: stopped or held', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const boxes = [agentStore('C1'), agentStore('C2')];
  const ticker = tickerFor(boxes, t, slack);
  const claims = boxes.map((box) => startTurn(box));
  await run(ticker, t, 3000);
  boxes.forEach((box, i) => endTurn(box, claims[i], 'waiting_workers'));
  await run(ticker, t, 1500);
  assert.deepEqual(['C1', 'C2'].map((channel) => slack.of(channel, '1.1')), [['large_green_circle', 'zzz'], ['large_green_circle', 'zzz']]);
  // The owner stops the first work; the second is held.
  boxes[0].store.stopWork(claims[0].work_id);
  boxes[1].store.db.prepare("UPDATE work SET state='held' WHERE id=?").run(claims[1].work_id);
  await run(ticker, t, 1500);
  for (const [i, channel] of ['C1', 'C2'].entries()) {
    assert.deepEqual(layers(boxes[i].store, '1.1', channel), { system: 'running', agent: null, task: null });
    assert.deepEqual(slack.of(channel, '1.1'), ['large_green_circle']);
  }
  const calls = slack.calls.length;
  await run(ticker, t, 30_000);
  assert.equal(slack.calls.length, calls);
  assert.deepEqual(slack.violations, []);
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

// ---- Ignite's states ----

// ---- The live status follows the thread's latest message ----

// Runs the ticker for ms and returns the calls it made, each with its message.
async function step(ticker, t, slack, ms) {
  slack.trail.length = 0;
  await run(ticker, t, ms);
  return [...slack.trail];
}

test('the live status follows the thread\'s latest message: each move\'s calls in order, the old message keeps only its task', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  const ticker = tickerFor([box], t, slack);
  // The owner writes: the hourglass on the message.
  assert.deepEqual(await step(ticker, t, slack, 500), ['add C1:1.1 hourglass_flowing_sand']);
  // The turn runs there: the green circle replaces the hourglass, the clock follows 1 s later.
  const first = startTurn(box);
  assert.deepEqual(await step(ticker, t, slack, 1900), [
    'remove C1:1.1 hourglass_flowing_sand', 'add C1:1.1 large_green_circle', 'add C1:1.1 clock12',
  ]);
  // It replies and ends waiting for a worker: the green circle and the waiting move to the reply, and
  // the owner message ends with no reaction.
  endTurn(box, first, 'waiting_workers', { replies: 1 });
  replyDelivered(box, first, '1.5');
  assert.deepEqual(await step(ticker, t, slack, 2500), [
    'remove C1:1.1 clock12', 'remove C1:1.1 large_green_circle',
    'add C1:1.5 large_green_circle', 'add C1:1.5 zzz',
  ]);
  // The worker's wake starts the next turn: the clock on that reply.
  assert.equal(box.store.wake({ conversationKey: box.key, note: 'worker done' }).inserted, true);
  const wake = box.store.claimNext(Date.now() + 1000);
  live.started(box.store, live.messageOf(box.store, wake), wake.runId);
  assert.deepEqual(await step(ticker, t, slack, 1000), ['remove C1:1.5 zzz', 'add C1:1.5 clock12']);
  // The final reply, completed: the green circle and done on it; the earlier reply ends with none.
  endTurn(box, wake, 'completed', { replies: 1 });
  replyDelivered(box, wake, '1.7', 'done');
  assert.deepEqual(await step(ticker, t, slack, 2000), [
    'remove C1:1.5 clock12', 'remove C1:1.5 large_green_circle',
    'add C1:1.7 large_green_circle', 'add C1:1.7 white_check_mark',
  ]);
  // The owner writes again: the hourglass on the new message; the final reply keeps only its done.
  ownerWrites(box, '2.2');
  assert.deepEqual(await step(ticker, t, slack, 1500), ['remove C1:1.7 large_green_circle', 'add C1:2.2 hourglass_flowing_sand']);
  assert.deepEqual(shows(slack, ['1.1', '1.5', '1.7', '2.2']),
    { 1.1: [], 1.5: [], 1.7: ['white_check_mark'], 2.2: ['hourglass_flowing_sand'] });
  assert.deepEqual(slack.violations, []);
});

test('a reply that keeps a task and is the latest when the next turn starts: the clock hides the task, which shows again once the status moves on', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  const first = startTurn(box);
  const ticker = tickerFor([box], t, slack);
  assert.deepEqual(await step(ticker, t, slack, 1500), ['add C1:1.1 large_green_circle', 'add C1:1.1 clock12']);
  // The owner writes while the turn runs: the running turn's status moves to the new message.
  ownerWrites(box, '2.2');
  assert.deepEqual(await step(ticker, t, slack, 1500), [
    'remove C1:1.1 clock12', 'remove C1:1.1 large_green_circle',
    'add C1:2.2 large_green_circle', 'add C1:2.2 clock12',
  ]);
  // The turn's reply lands after it, done. 2.2 still waits for its turn: the system is queued.
  endTurn(box, first, 'completed', { replies: 1 });
  replyDelivered(box, first, '2.5', 'done');
  assert.deepEqual(await step(ticker, t, slack, 2000), [
    'remove C1:2.2 clock12', 'remove C1:2.2 large_green_circle',
    'add C1:2.5 hourglass_flowing_sand', 'add C1:2.5 white_check_mark',
  ]);
  // 2.2's turn starts on the latest message, the reply: agent and task never show together, so the
  // clock takes the done's place; the reply keeps its task.
  const second = box.store.claimNext(Date.now() + 1000);
  assert.equal(second.payload.ts, '2.2');
  live.started(box.store, live.messageOf(box.store, second), second.runId);
  assert.deepEqual(await step(ticker, t, slack, 1900), [
    'remove C1:2.5 white_check_mark', 'remove C1:2.5 hourglass_flowing_sand',
    'add C1:2.5 large_green_circle', 'add C1:2.5 clock12',
  ]);
  // Marking the first owner message lands on the reply that keeps its task, unseen until the status moves.
  assert.equal(live.markTask(box.store, box.key, '1.1', 'caveats').ts, '2.5');
  assert.deepEqual(layers(box.store, '2.5'), { system: 'running', agent: 'working', task: null });
  // 2.2's reply: the status moves on, and the earlier reply shows its task again.
  endTurn(box, second, 'completed', { replies: 1 });
  replyDelivered(box, second, '3.5', 'done');
  assert.deepEqual(await step(ticker, t, slack, 2000), [
    'remove C1:2.5 clock12', 'remove C1:2.5 large_green_circle',
    'add C1:3.5 large_green_circle', 'add C1:2.5 warning', 'add C1:3.5 white_check_mark',
  ]);
  assert.deepEqual(shows(slack, ['1.1', '2.2', '2.5', '3.5']),
    { 1.1: [], 2.2: [], 2.5: ['warning'], 3.5: ['large_green_circle', 'white_check_mark'] });
  assert.deepEqual(slack.violations, []);
});

test('a restart after a move made while the service was stopped clears the old message and resumes on the new one', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  const claim = startTurn(box);
  endTurn(box, claim, 'waiting_workers', { replies: 1 });
  const first = tickerFor([box], t, slack);
  await run(first, t, 1500);
  assert.deepEqual(slack.of('C1', '1.1'), ['large_green_circle', 'zzz']);
  await first.stop();
  // Stopped: the reply is delivered and takes the live status in the store only.
  replyDelivered(box, claim, '1.5');
  const restarted = fakeSlack(t, slack);
  const again = tickerFor([box], t, restarted);
  assert.deepEqual(await step(again, t, restarted, 1500), [
    'remove C1:1.1 zzz', 'remove C1:1.1 large_green_circle',
    'add C1:1.5 large_green_circle', 'add C1:1.5 zzz',
  ]);
  assert.deepEqual(recorded(box, '1.1').order, []);
  assert.deepEqual(recorded(box, '1.5').order, ['large_green_circle', 'zzz']);
  // The waiting keeps ticking there, slowly, and the wake turn works there.
  assert.deepEqual(await step(again, t, restarted, 10_000), ['remove C1:1.5 zzz', 'add C1:1.5 sleeping']);
  box.store.wake({ conversationKey: box.key, note: 'worker done' });
  const wake = box.store.claimNext(Date.now() + 1000);
  live.started(box.store, live.messageOf(box.store, wake), wake.runId);
  assert.deepEqual(await step(again, t, restarted, 1000), ['remove C1:1.5 sleeping', 'add C1:1.5 clock12']);
  assert.deepEqual(restarted.violations, []);
});

test('a post into the thread takes the live status, the conversation\'s task included, and keeps that task once the status leaves it', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const database = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-post-')), 'state.sqlite');
  const box = agentStore('C1', '1.1', database);
  const claim = startTurn(box);
  endTurn(box, claim, 'completed', { replies: 1 });
  replyDelivered(box, claim, '1.5', 'done');
  const ticker = tickerFor([box], t, slack);
  assert.deepEqual(await step(ticker, t, slack, 1500), ['add C1:1.5 large_green_circle', 'add C1:1.5 white_check_mark']);
  replyDelivered(box, null, '1.8');
  assert.deepEqual(await step(ticker, t, slack, 1500), [
    'remove C1:1.5 large_green_circle', 'add C1:1.8 large_green_circle', 'add C1:1.8 white_check_mark',
  ]);
  // The owner's next message: the post keeps the done it shows and loses only its system emoji.
  ownerWrites(box, '2.2');
  assert.deepEqual(await step(ticker, t, slack, 1500), ['remove C1:1.8 large_green_circle', 'add C1:2.2 hourglass_flowing_sand']);
  const after = { 1.1: [], 1.5: ['white_check_mark'], 1.8: ['white_check_mark'], 2.2: ['hourglass_flowing_sand'] };
  assert.deepEqual(shows(slack, ['1.1', '1.5', '1.8', '2.2']), after);
  // A restart reopens the store: the post still keeps its done, and nothing is called.
  await ticker.stop();
  box.store.close();
  box.store = new Store(database);
  const row = box.store.getLiveStatus('C1', '1.8');
  assert.deepEqual([row.task, row.kept, row.kept_for], ['done', 'done', '1.1']);
  const restarted = fakeSlack(t, slack);
  assert.deepEqual(await step(tickerFor([box], t, restarted), t, restarted, 1500), []);
  assert.deepEqual(shows(restarted, ['1.1', '1.5', '1.8', '2.2']), after);
  assert.deepEqual([...slack.violations, ...restarted.violations], []);
  box.store.close();
});

test('a post keeps the task it shows across a restart: the move made after reopening the store removes only its system emoji', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const database = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-post-')), 'state.sqlite');
  const box = agentStore('C1', '1.1', database);
  const claim = startTurn(box);
  endTurn(box, claim, 'completed', { replies: 1 });
  replyDelivered(box, claim, '1.5', 'done');
  replyDelivered(box, null, '1.8');
  const ticker = tickerFor([box], t, slack);
  assert.deepEqual(await step(ticker, t, slack, 1500), ['add C1:1.5 white_check_mark', 'add C1:1.8 large_green_circle', 'add C1:1.8 white_check_mark']);
  await ticker.stop();
  box.store.close();
  // Stopped, the store reopened: the owner writes, and the restarted service makes the move.
  box.store = new Store(database);
  ownerWrites(box, '2.2');
  const restarted = fakeSlack(t, slack);
  assert.deepEqual(await step(tickerFor([box], t, restarted), t, restarted, 1500), [
    'remove C1:1.8 large_green_circle', 'add C1:2.2 hourglass_flowing_sand',
  ]);
  assert.deepEqual(shows(restarted, ['1.1', '1.5', '1.8', '2.2']),
    { 1.1: [], 1.5: ['white_check_mark'], 1.8: ['white_check_mark'], 2.2: ['hourglass_flowing_sand'] });
  assert.deepEqual([...slack.violations, ...restarted.violations], []);
  box.store.close();
});

// Ends claim's turn with its replies queued for delivery, as turn-loop does: each reply { id, text }
// carries the mark of the owner message the turn answers, with the task of the result.
function endWithReplies(box, claim, disposition, replies) {
  const message = live.messageOf(box.store, claim);
  const task = live.taskOf(disposition, false);
  const mark = { channel: message.channel, ts: message.ts, runId: claim.runId, ...(task && { task }) };
  box.store.finishRun(claim.runId, claim.nonce, {
    invocationNonce: claim.nonce, output: '{}', disposition, summary: 's',
    outbox: replies.map(({ id, text }) => ({ id, payload: { text, mark } })),
  });
  live.ended(box.store, message, disposition, task, replies.length);
}

test('an earlier turn\'s reply that gives up after a later turn has run changes nothing of that turn: its reply shows running and done', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const box = agentStore();
  const ticker = tickerFor([box], t, slack);
  const posted = [];
  const chat = {
    async postMessage({ channel, text }) {
      posted.push(text);
      if (text === 'reply A') throw new Error('slack down');
      return { channel, ts: '2.5' };
    },
  };
  const deliver = async () => { const results = await deliverPending(box.store, { slack: chat, now: t.now }); t.advance(RETRY_MS); return results; };
  // Turn A completes; its reply fails twice, a transient failure each time.
  const a = startTurn(box);
  endWithReplies(box, a, 'completed', [{ id: 'a-reply', text: 'reply A' }]);
  await deliver();
  await deliver();
  // The owner writes again, and turn B starts and completes with its own reply.
  ownerWrites(box, '2.2');
  const b = box.store.claimNext(Date.now() + 1000);
  assert.equal(b.payload.ts, '2.2');
  live.started(box.store, live.messageOf(box.store, b), b.runId);
  endWithReplies(box, b, 'completed', [{ id: 'b-reply', text: 'reply B' }]);
  assert.deepEqual(await step(ticker, t, slack, 1500), ['add C1:2.2 large_green_circle', 'add C1:2.2 clock12']);
  // One pass: A's reply gives up on its third failure, then B's reply is delivered.
  const results = await deliver();
  assert.deepEqual(results.map((one) => [one.id, one.delivered]), [['a-reply', false], ['b-reply', true]]);
  assert.deepEqual(posted, ['reply A', 'reply A', 'reply A', 'reply B']);
  assert.deepEqual(layers(box.store, '2.5'), { system: 'running', agent: null, task: 'done' });
  assert.deepEqual(await step(ticker, t, slack, 2000), [
    'remove C1:2.2 clock12', 'remove C1:2.2 large_green_circle',
    'add C1:2.5 large_green_circle', 'add C1:2.5 white_check_mark',
  ]);
  assert.deepEqual(shows(slack, ['1.1', '2.2', '2.5']), { 1.1: [], 2.2: [], 2.5: ['large_green_circle', 'white_check_mark'] });
  // A's failure stays in its outbox row and its hold notice.
  const outbox = (id) => box.store.db.prepare('SELECT state, last_error FROM outbox WHERE id=?').get(id);
  assert.deepEqual({ ...outbox('a-reply') }, { state: 'failed', last_error: 'slack down' });
  assert.equal(outbox('hold:delivery:a-reply').state, 'pending');
  assert.deepEqual(slack.violations, []);
});

test('a turn that ends with no reply while a newer owner message waits: its task goes to the message it saw, and the waiting one shows queued', () => {
  const box = agentStore();
  const first = startTurn(box);
  ownerWrites(box, '2.2');
  assert.deepEqual(layers(box.store, '2.2'), { system: 'running', agent: 'working', task: null });
  endTurn(box, first, 'completed');
  assert.deepEqual(layers(box.store, '1.1'), { system: null, agent: null, task: 'done' });
  assert.deepEqual(layers(box.store, '2.2'), { system: 'queued', agent: null, task: null });
  // 2.2's own turn ends with no reply: the task on 2.2, the latest message.
  const second = startTurn(box);
  endTurn(box, second, 'completed');
  assert.deepEqual(layers(box.store, '2.2'), { system: 'running', agent: null, task: 'done' });
  const kept = (ts) => { const row = box.store.getLiveStatus('C1', ts); return [row.kept, row.kept_for]; };
  assert.deepEqual([kept('1.1'), kept('2.2')], [['done', '1.1'], ['done', '2.2']]);
});

test('a system emoji that goes with nothing in its place is removed alone: a task beside it stays where it is', async () => {
  const t = clock();
  const slack = fakeSlack(t);
  const show = display(t, slack);
  const cases = [
    [['large_green_circle', 'white_check_mark'], { task: 'done' }, ['remove large_green_circle'], ['white_check_mark']],
    [['large_green_circle', 'clock4'], {}, ['remove clock4', 'remove large_green_circle'], []],
    [['large_green_circle', 'clock4'], { task: 'done' }, ['remove clock4', 'remove large_green_circle', 'add white_check_mark'], ['white_check_mark']],
  ];
  for (const [i, [before, state, calls, after]] of cases.entries()) {
    const m = { channel: 'C1', ts: `${i}.1` };
    slack.on.set(`C1:${i}.1`, [...before]);
    show.restore(m, state, { order: before, unsure: [], lastAddAt: null });
    slack.calls.length = 0;
    assert.deepEqual(await show.apply(m), { settled: true });
    assert.deepEqual(slack.calls, calls);
    assert.deepEqual(slack.of('C1', `${i}.1`), after);
  }
  assert.deepEqual(slack.violations, []);
});

// ---- ignite status ----

function turnHome() {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-status-'));
  const store = new Store(ignitePaths(home).database);
  const message = { conversationKey: 'T1:C1:1.1', channel: 'C1', ts: '1.1' };
  const box = { store, key: message.conversationKey, message };
  // The first owner message's turn asks a question in its reply 1.5.
  store.acceptOwnerInput({
    key: box.key, agent: 'a', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true,
    message: { id: '1.1', role: 'owner', text: 'hi', team: 'T1', channel: 'C1', ts: '1.1' },
    payload: { text: 'hi', ts: '1.1', threadTs: '1.1' },
  });
  live.received(store, message);
  const first = store.claimNext(Date.now());
  live.started(store, live.messageOf(store, first), first.runId);
  endTurn(box, first, 'waiting_owner', { replies: 1 });
  replyDelivered(box, first, '1.5', 'question');
  // The owner answers in 2.2, whose turn runs; 3.3 arrives while it runs and is the latest message.
  ownerWrites(box, '2.2');
  const second = store.claimNext(Date.now() + 1000);
  live.started(store, live.messageOf(store, second), second.runId);
  ownerWrites(box, '3.3');
  return { home, ...box };
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

test('--message takes the owner message, any message of its reply or a post showing its task, and lands on every message keeping that task', () => {
  const box = agentStore();
  const first = startTurn(box);
  endTurn(box, first, 'completed', { replies: 1 });
  // The reply is a text at 1.5 and a file at 1.6; a post at 1.8 shows its done too.
  live.delivered(box.store, { conversationKey: box.key, channel: 'C1', messages: ['1.5', '1.6'] },
    { ts: '1.1', runId: first.runId, task: 'done' });
  replyDelivered(box, null, '1.8');
  ownerWrites(box, '2.2');
  startTurn(box);
  const none = { system: null, agent: null, task: null };
  for (const [ts, task] of [['1.5', 'caveats'], ['1.8', 'question'], ['1.6', 'stopped'], ['1.1', 'done']]) {
    assert.equal(live.markTask(box.store, box.key, ts, task).ts, '1.8');
    assert.deepEqual(['1.1', '1.5', '1.6', '1.8'].map((one) => layers(box.store, one)),
      [none, none, { ...none, task }, { ...none, task }]);
  }
  assert.deepEqual(layers(box.store, '2.2'), { system: 'running', agent: 'working', task: null });
});

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
    assert.match(status(['--task', 'done', '--message', '7.7'], env).err, /^no message 7.7 in conversation T1:C1:1.1\n/);
    assert.equal(status(['--task', 'done', '--message', '3.3'], env).err,
      'message 3.3 has no finished turn yet; only an earlier message whose turn has finished takes a task state\nNothing changed.\nignite status -h');
    assert.match(status(['--task', 'done', '--message', '1.1'], { ...env, IGNITE_CONVERSATION: 'T1:C9:9.9' }).err,
      /^the running turn belongs to T1:C1:1.1, not T1:C9:9.9\n/);
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

test('ignite status --note keeps one line for the /agent panel, with a state or alone, and refuses what it cannot keep', async () => {
  const box = turnHome();
  try {
    const env = { RBTV_AGENT_HOME: box.home, IGNITE_CONVERSATION: box.key };
    const both = status(['making', '--note', '  Writing the Work tab  '], env);
    assert.equal(both.code, 0, both.err);
    assert.equal(both.out, 'making shown on 3.3\nnote saved\n');
    assert.equal(box.store.getLiveStatus('C1', '3.3').agent, 'making');
    const alone = status(['--note', 'Running the suites', '--json'], env);
    assert.deepEqual(JSON.parse(alone.out), { state: null, message: null, note: true });
    assert.deepEqual(box.store.listNotes(box.key).map((row) => row.text), ['Running the suites', 'Writing the Work tab']);
    const before = box.store.liveStatuses().map((row) => row.rev).join();
    assert.match(status(['--note', 'two\nlines'], env).err, /^--note takes one line\n/);
    assert.match(status(['--note', 'x'.repeat(301)], env).err, /^--note takes at most 300 characters; this one has 301\n/);
    assert.match(status(['--note', 'a', '--task', 'done', '--message', '1.1'], env).err, /^--note goes with a state word or alone, not with --task\n/);
    assert.match(status(['thinking', '--note', 'elsewhere'], { ...env, IGNITE_CONVERSATION: 'T1:C9:9.9' }).err, /the running turn belongs to T1:C1:1.1/);
    assert.equal(box.store.listNotes(box.key).length, 2);
    assert.equal(box.store.listNotes('T1:C9:9.9').length, 0);
    assert.equal(box.store.liveStatuses().map((row) => row.rev).join(), before);
    assert.match(status(['-h'], env).out, /ignite status --note <text>/);
  } finally {
    box.store.close();
    fs.rmSync(box.home, { recursive: true, force: true });
  }
});

test('ignite status: declares the running turn\'s state on the latest message and sets an earlier task by either ts', async () => {
  const box = turnHome();
  try {
    const env = { RBTV_AGENT_HOME: box.home, IGNITE_CONVERSATION: box.key };
    for (const state of ['gathering', 'thinking', 'making', 'orchestrating']) {
      const done = status([state], env);
      assert.equal(done.code, 0, done.err);
      assert.equal(done.out, `${state} shown on 3.3\n`);
      assert.equal(box.store.getLiveStatus('C1', '3.3').agent, state);
    }
    const json = status(['thinking', '--json'], env);
    assert.deepEqual(JSON.parse(json.out), { state: 'thinking', message: '3.3', note: false });
    assert.deepEqual(layers(box.store, '1.5'), { system: null, agent: null, task: 'question' });
    // The owner message's ts finds the reply that keeps its task; the reply's own ts finds it too.
    const marked = status(['--task', 'done', '--message', '1.1'], env);
    assert.equal(marked.code, 0, marked.err);
    assert.equal(marked.out, 'task done shown on 1.5\n');
    assert.deepEqual(layers(box.store, '1.5'), { system: null, agent: null, task: 'done' });
    assert.deepEqual(layers(box.store, '1.1'), { system: null, agent: null, task: null });
    const again = status(['--task', 'caveats', '--message', '1.5', '--json'], env);
    assert.deepEqual(JSON.parse(again.out), { task: 'caveats', message: '1.5' });
    const row = box.store.getLiveStatus('C1', '1.5');
    assert.deepEqual([row.system, row.agent, row.task, row.kept, row.kept_for], [null, null, 'caveats', 'caveats', '1.1']);
    // A turn that answers no owner message has nowhere to show the state.
    const run = box.store.getActiveRun();
    box.store.db.prepare('UPDATE live_status SET run_id=NULL WHERE run_id=?').run(run.id);
    const nowhere = status(['making'], env);
    assert.equal(nowhere.code, 0);
    assert.equal(nowhere.out, 'nothing shown: this turn answers no owner message\n');
    // With no turn running, no message takes a task state.
    box.store.failRun(run.id, 'stopped by the test');
    assert.match(status(['--task', 'done', '--message', '1.1'], env).err, /^no turn of this agent is running/);
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

const mrkdwn = (text) => ({ type: 'mrkdwn', text });

test('legend: the modal, its header, and the heading and rows of each group as a two-column table', () => {
  const view = legendView(live.MEANING);
  assert.deepEqual(view.type, 'modal');
  assert.deepEqual(view.title, { type: 'plain_text', text: 'Live status' });
  assert.deepEqual(view.close, { type: 'plain_text', text: 'Close' });
  assert.equal('submit' in view, false);
  assert.deepEqual(view.blocks.map((b) => (b.fields ? `fields ${b.fields.length}` : b.type)), [
    'header', 'context',
    'divider', 'section', 'fields 10',
    'divider', 'section', 'fields 10', 'fields 4',
    'divider', 'section', 'fields 8',
  ]);
  assert.deepEqual(view.blocks[0], { type: 'header', text: { type: 'plain_text', text: 'What the reactions mean' } });
  assert.deepEqual(view.blocks[1], { type: 'context', elements: [mrkdwn('The latest message of a thread carries up to two reactions. '
    + 'The left one is the system and stays still. The right one is the agent while it works, then the task once it replies. '
    + 'Earlier messages keep their final task.')] });
  assert.deepEqual(view.blocks[3], { type: 'section', text: mrkdwn('*System* · left · stays still') });
  assert.deepEqual(view.blocks[4].fields.slice(0, 2), [mrkdwn(':hourglass_flowing_sand: *Queued*'), mrkdwn('Received; waiting for a turn to start.')]);
  assert.deepEqual(view.blocks[6], { type: 'section', text: mrkdwn('*Agent* · right · moves while it works') });
  assert.deepEqual(view.blocks[7].fields.slice(0, 4), [
    mrkdwn(':clock12::clock2: *Working*'), mrkdwn('At work; it has not named the kind of work.'),
    mrkdwn(':mag::mag_right: *Gathering*'), mrkdwn('Reading, searching and collecting what the work needs.'),
  ]);
  // System-owned states share the right-hand animation, including before the model starts.
  assert.deepEqual(view.blocks[8], { type: 'section', fields: [
    mrkdwn(':zzz::sleeping: *Waiting*'), mrkdwn('Waiting for its workers to finish.'),
    mrkdwn(':microphone::memo: *Transcribing*'), mrkdwn('The system is transcribing incoming audio before the model starts.'),
  ] });
  assert.deepEqual(view.blocks[10], { type: 'section', text: mrkdwn('*Task* · right · once it replies') });
  assert.deepEqual(view.blocks[11].fields.slice(2, 4), [mrkdwn(':warning: *Caveats*'), mrkdwn('Done, with problems worth a follow-up.')]);
});

test('legend: every state of the Ignite contract appears once, in order, with its emoji and meaning, and nothing else', () => {
  // The Slack mapping names exactly the contract's states, no more and no fewer.
  assert.deepEqual(Object.keys(EMOJI.system), live.SYSTEM);
  assert.deepEqual(Object.keys(EMOJI.agent), live.AGENT);
  assert.deepEqual(Object.keys(EMOJI.task), live.TASK);
  assert.deepEqual([live.SYSTEM.length, live.AGENT.length, live.TASK.length], [5, 7, 4]);
  const view = legendView(live.MEANING);
  const shown = { system: [], agent: [], task: [] };
  let layer = null;
  for (const block of view.blocks) {
    if (block.type === 'section' && block.text) layer = block.text.text.match(/^\*(\w+)\*/)[1].toLowerCase();
    if (!block.fields) continue;
    for (let at = 0; at < block.fields.length; at += 2) {
      const [, emoji, state] = block.fields[at].text.match(/^((?::[a-z0-9_]+:)*) \*(\w+)\*$/);
      shown[layer].push({ state, emoji, meaning: block.fields[at + 1].text });
    }
  }
  for (const [name, states] of [['system', live.SYSTEM], ['agent', live.AGENT], ['task', live.TASK]]) {
    assert.deepEqual(shown[name].map((row) => row.state.toLowerCase()), [...states], name);
    for (const row of shown[name]) {
      // An animated state shows its first two frames only (owner, 2026-10-16).
      const key = row.state.toLowerCase();
      assert.equal(row.emoji, [EMOJI[name][key]].flat().slice(0, 2).map((n) => `:${n}:`).join(''), `${name} ${key}`);
      assert.equal(row.state, key.charAt(0).toUpperCase() + key.slice(1));
      assert.equal(row.meaning, live.MEANING[name][key]);
      // A meaning is a plain sentence: no emoji and no Slack markup.
      assert.match(row.meaning, /^[A-Z][^:*_\p{Extended_Pictographic}]*\.$/u, `${name} ${row.state}`);
    }
  }
});

function legendSlack(fail = null) {
  const slack = {
    calls: [],
    async openView(triggerId, view) {
      slack.calls.push({ triggerId, view });
      if (fail) throw fail;
      return { viewId: 'V1' };
    },
  };
  return slack;
}

test('legend: /legend from any user opens the legend with its trigger id; other commands and interactions are ignored', async () => {
  const slack = legendSlack();
  const logs = [];
  const legend = createLegend({ slack: () => slack, log: (fields) => logs.push(fields) });
  assert.equal(await legend.handle('slash_commands', { command: '/payments', user_id: 'UOWNER', team_id: 'T1', trigger_id: 'trig-1' }), undefined);
  await legend.handle('interactive', { type: 'block_actions', user: { id: 'UOTHER' }, trigger_id: 'trig-2', actions: [{ action_id: 'payments_settings' }] });
  await legend.handle('slash_commands', {});
  assert.deepEqual(slack.calls, []);
  await legend.handle('slash_commands', { command: '/legend', user_id: 'UNOTOWNER', team_id: 'T1', trigger_id: 'trig-7' });
  assert.deepEqual(slack.calls, [{ triggerId: 'trig-7', view: legendView(live.MEANING) }]);
  assert.deepEqual(logs, []);
});

test('legend: a failed views.open is logged and the handler resolves', async () => {
  const logs = [];
  const slack = legendSlack(new Error('views.open failed: expired_trigger_id'));
  const legend = createLegend({ slack: () => slack, log: (fields) => logs.push(fields) });
  assert.equal(await legend.handle('slash_commands', { command: '/legend', user_id: 'UNOTOWNER', trigger_id: 'trig-7' }), undefined);
  assert.equal(slack.calls.length, 1);
  assert.deepEqual(logs, [{ event: 'legend', action: 'open-failed', message: 'views.open failed: expired_trigger_id' }]);
  // No Slack client, and a log that throws: still nothing escapes.
  const bare = createLegend({ slack: () => null, log: () => { throw new Error('log down'); } });
  assert.equal(await bare.handle('slash_commands', { command: '/legend', trigger_id: 'trig-8' }), undefined);
});

// A test left waiting on a promise that never settles would end the process before the summary.
let finished = false;
process.on('exit', () => {
  if (finished) return;
  process.stdout.write('FAIL the suite ended before its last test finished\n');
  process.exitCode = 1;
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
  finished = true;
  process.exit(failed ? 1 : 0);
})();
