'use strict';

// The waking service's side of live status (live-status.js names the states): it reads each agent's
// stored live status and shows it in Slack through the Slack connector's live status, which holds
// the emoji and their order rules. The service is the one place that sees every agent, so it holds
// the reaction budget they share.
//
// API
// createTicker({ stores, slack, now?, log?, pace?, callMs? }) → { step(), stop() }
//   stores() → [{ slug, store }], the agents' open stores. slack() → the Slack client, or null while
//   there is none; a client without addReaction and removeReaction shows nothing. Each reaction call
//   is given { signal } as its fourth argument: it is aborted after callMs (CALL_MS by default) and by
//   stop(); a call cut off this way leaves its name unsure in the row's record.
//   pace = { load() → { pausedUntil, adds }, save({ pausedUntil, adds }) }: where the shared budget
//   (the time of each add in the last minute) and the pause after HTTP 429 are kept, so that a
//   restarted service honours them. In memory when absent.
//   step() → Promise, never rejects. One pass:
//   - It reads the messages whose state changed since the last pass. A message read for the first
//     time, every message at service start, starts from the reactions its row records as shown (the
//     connector's record, saved before and after each call): its calls then finish whatever a
//     stopped service left, the reactions of earlier states included.
//   - A message waiting for workers whose work no longer waits (stopped, held, ended) stops waiting
//     (live-status.js waitEnded).
//   - A message ticks while its turn runs (its run is the store's active run), and while its agent
//     state is waiting, which also ticks between turns and after a restart. Ticking stops when the
//     turn ends or fails. A tick moves the agent emoji to its next frame.
//   - Reaction adds share ADDS_PER_MINUTE across all agents, counted when each add is sent; an add
//     the budget allowed but not yet sent is held apart until it is sent or given up. A frame lasts
//     FRAME_MS for one ticking message (WAITING_FRAME_MS for waiting), stretched by the factor that
//     keeps every ticking message's adds inside that budget: one message alone ticks every 1.33 s.
//   - After Slack's HTTP 429 no reaction call is made until its Retry-After has passed; after an
//     HTTP 5xx, for the connector's short pause.
//   - A pass still running when step() is called again makes the new call return at once.
//   stop() → Promise: no pass and no reaction call starts after it, the call in flight is aborted,
//   and the promise settles when the pass in flight has ended.
//   Reaction errors are logged by the Slack connector's live status; a store or Slack failure is
//   logged as { event: 'status-failed' } and never reaches a turn or a delivery.

const live = require('./live-status.js');
const { liveStatus } = require('../../../../../connectors/slack/capabilities/tools/slack/lib/live-status.js');

const ADDS_PER_MINUTE = 45;
const FRAME_MS = 1_200;
const WAITING_FRAME_MS = 10_000;
const MINUTE = 60_000;
// The longest a reaction call may take: shorter than the 5 s a stopping service waits for its pass.
const CALL_MS = 4_000;

function memoryPace() {
  let kept = null;
  return { load: () => kept, save(state) { kept = state; } };
}

function shownOf(row) {
  if (!row.shown) return null;
  try { return JSON.parse(row.shown); } catch { return null; }
}

function createTicker({ stores, slack, now = Date.now, log, pace = memoryPace(), callMs = CALL_MS } = {}) {
  let show = null;
  const lastRev = new Map();
  const activeRun = new Map();
  // The store that holds each message's row, where its shown reactions are recorded.
  const homes = new Map();
  // Messages with an agent state: the ones that may tick.
  const agents = new Map();
  // Messages whose reactions do not yet show their state, in the order their change arrived.
  const unsettled = new Map();
  const kept = loadPace();
  // The time each add was sent in the last minute; reserved: adds allowed and not yet sent.
  const adds = kept.adds;
  let reserved = 0;
  let pausedUntil = kept.pausedUntil;
  let running = null;
  let halted = false;
  // The reaction call in flight, aborted by stop().
  let inFlight = null;

  function note(fields) {
    if (typeof log !== 'function') return;
    try { log(fields); } catch { /* keep the service */ }
  }

  function loadPace() {
    try {
      const state = pace.load() || {};
      return {
        pausedUntil: Number.isFinite(state.pausedUntil) ? state.pausedUntil : 0,
        adds: Array.isArray(state.adds) ? state.adds.filter(Number.isFinite) : [],
      };
    } catch (error) {
      note({ event: 'status-failed', message: error.message });
      return { pausedUntil: 0, adds: [] };
    }
  }

  function savePace() {
    try { pace.save({ pausedUntil, adds: [...adds] }); } catch (error) { note({ event: 'status-failed', message: error.message }); }
  }

  function display() {
    if (show) return show;
    const client = typeof slack === 'function' ? slack() : null;
    if (!client || typeof client.addReaction !== 'function' || typeof client.removeReaction !== 'function') return null;
    show = liveStatus({
      addReaction: (channel, ts, name) => react(client, 'addReaction', channel, ts, name),
      removeReaction: (channel, ts, name) => react(client, 'removeReaction', channel, ts, name),
      now,
      log,
      record(message, shown) {
        const store = homes.get(`${message.channel}:${message.ts}`);
        if (!store) throw new Error(`no store holds the live status of ${message.channel} ${message.ts}`);
        store.setLiveShown(message.channel, message.ts, shown);
      },
    });
    return show;
  }

  // One reaction call. None starts after stop(); the one in flight is aborted by stop() or after
  // callMs. An add is charged to the budget as it is sent.
  async function react(client, method, channel, ts, name) {
    if (halted) throw new Error('live status stopped: call not made');
    if (method === 'addReaction') {
      reserved = Math.max(0, reserved - 1);
      adds.push(now());
      savePace();
    }
    const call = new AbortController();
    const timer = setTimeout(() => call.abort(new Error(`no answer from Slack in ${callMs} ms`)), callMs);
    inFlight = call;
    try {
      return await client[method](channel, ts, name, { signal: call.signal });
    } finally {
      clearTimeout(timer);
      inFlight = null;
    }
  }

  // Reserves an add: the connector asks before the remove paired with it, and sends it after.
  function mayAdd() {
    const at = now();
    while (adds.length && adds[0] <= at - MINUTE) adds.shift();
    if (adds.length + reserved >= ADDS_PER_MINUTE) return false;
    reserved += 1;
    return true;
  }

  function read() {
    for (const { slug, store } of stores()) {
      try {
        activeRun.set(store, store.getActiveRun()?.id || null);
        for (const one of agents.values()) {
          if (one.store === store && one.agent === 'waiting') live.waitEnded(store, one.message, log);
        }
        let rev = lastRev.get(store) || 0;
        for (const row of store.liveStatuses({ sinceRev: rev })) {
          rev = Math.max(rev, row.rev);
          const key = `${row.channel}:${row.ts}`;
          const message = { channel: row.channel, ts: row.ts };
          const state = { system: row.system, agent: row.agent, task: row.task };
          if (homes.has(key)) show.set(message, state);
          else show.restore(message, state, shownOf(row));
          homes.set(key, store);
          if (!show.settled(message)) unsettled.set(key, message);
          if (row.agent && !row.task) {
            agents.set(key, { message, store, agent: row.agent, runId: row.run_id, nextTickAt: null });
          } else {
            agents.delete(key);
          }
        }
        lastRev.set(store, rev);
      } catch (error) {
        note({ event: 'status-failed', slug, message: error.message });
      }
    }
  }

  const ticking = (one) => one.agent === 'waiting' || (one.runId != null && one.runId === activeRun.get(one.store));
  const frameMs = (one) => (one.agent === 'waiting' ? WAITING_FRAME_MS : FRAME_MS);

  function tick() {
    const due = [...agents.entries()].filter(([, one]) => ticking(one));
    const demand = due.reduce((sum, [, one]) => sum + MINUTE / frameMs(one), 0);
    const stretch = Math.max(1, demand / ADDS_PER_MINUTE);
    const at = now();
    for (const [key, one] of due) {
      one.interval = frameMs(one) * stretch;
      if (one.nextTickAt == null) {
        one.nextTickAt = at + one.interval;
      } else if (at >= one.nextTickAt && show.settled(one.message)) {
        show.tick(one.message);
        unsettled.set(key, one.message);
        // The next tick is counted from when this frame shows: an add that waits on the budget
        // never brings the next frame closer.
        one.nextTickAt = Infinity;
      }
    }
  }

  async function settle() {
    for (const [key, message] of [...unsettled]) {
      if (halted) return;
      const result = await show.apply(message, { mayAdd });
      // An add reserved and not sent is given up when apply returns.
      reserved = 0;
      if (result.retryAfterMs != null) {
        pausedUntil = now() + result.retryAfterMs;
        savePace();
        note({ event: 'reactions-paused', ms: result.retryAfterMs });
        return;
      }
      if (!result.settled) continue;
      unsettled.delete(key);
      const one = agents.get(key);
      if (one?.nextTickAt === Infinity) one.nextTickAt = now() + one.interval;
    }
  }

  async function pass() {
    try {
      if (!display()) return;
      read();
      if (now() < pausedUntil) return;
      tick();
      await settle();
    } catch (error) {
      note({ event: 'status-failed', message: error.message });
    }
  }

  function step() {
    if (halted || running) return Promise.resolve();
    running = pass().finally(() => { running = null; });
    return running;
  }

  function stop() {
    halted = true;
    inFlight?.abort(new Error('the service stopped'));
    return running || Promise.resolve();
  }

  return { step, stop };
}

module.exports = { createTicker, ADDS_PER_MINUTE, FRAME_MS, WAITING_FRAME_MS, CALL_MS };
