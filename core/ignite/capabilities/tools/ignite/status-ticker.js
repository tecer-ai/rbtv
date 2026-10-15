'use strict';

// The waking service's side of live status (live-status.js names the states): it reads each agent's
// stored live status and shows it in Slack through the Slack connector's live status, which holds
// the emoji and their order rules. The service is the one place that sees every agent, so it holds
// the reaction budget they share.
//
// API
// createTicker({ stores, slack, now?, log? }) → { baseline(), step() }
//   stores() → [{ slug, store }], the agents' open stores. slack() → the Slack client, or null while
//   there is none; a client without addReaction and removeReaction shows nothing.
//   baseline() → takes every message stored now as already shown, as the service that stopped left
//   it, and makes no call. The service calls it once at start, before any event or turn can change a
//   state; a message's agent frame is then unknown, so its first pass removes every frame of its
//   agent state before adding one.
//   step() → Promise, never rejects. One pass:
//   - It reads the messages whose state changed since the last pass, or since the baseline; a store
//     the baseline did not see is read whole, every state as new.
//   - A message ticks while its turn runs (its run is the store's active run), and while its agent
//     state is waiting, which also ticks between turns and after a restart. Ticking stops when the
//     turn ends or fails. A tick moves the agent emoji to its next frame.
//   - Reaction adds share ADDS_PER_MINUTE across all agents. A frame lasts FRAME_MS for one ticking
//     message (WAITING_FRAME_MS for waiting), stretched by the factor that keeps every ticking
//     message's adds inside that budget.
//   - After Slack's HTTP 429 no reaction call is made until its Retry-After has passed.
//   - A pass still running when step() is called again makes the new call return at once.
//   Reaction errors are logged by the Slack connector's live status; a store or Slack failure is
//   logged as { event: 'status-failed' } and never reaches a turn or a delivery.

const { liveStatus } = require('../../../../../connectors/slack/capabilities/tools/slack/lib/live-status.js');

const ADDS_PER_MINUTE = 45;
const FRAME_MS = 1_200;
const WAITING_FRAME_MS = 10_000;
const MINUTE = 60_000;

function createTicker({ stores, slack, now = Date.now, log } = {}) {
  let show = null;
  const lastRev = new Map();
  const activeRun = new Map();
  // Messages with an agent state: the ones that may tick.
  const agents = new Map();
  // Messages whose reactions do not yet show their state, in the order their change arrived.
  const unsettled = new Map();
  const adds = [];
  let pausedUntil = 0;
  let busy = false;

  function note(fields) {
    if (typeof log !== 'function') return;
    try { log(fields); } catch { /* keep the service */ }
  }

  function display() {
    if (show) return show;
    const client = typeof slack === 'function' ? slack() : null;
    if (!client || typeof client.addReaction !== 'function' || typeof client.removeReaction !== 'function') return null;
    show = liveStatus({
      addReaction: (channel, ts, name) => client.addReaction(channel, ts, name),
      removeReaction: (channel, ts, name) => client.removeReaction(channel, ts, name),
      now,
      log,
    });
    return show;
  }

  function mayAdd() {
    const at = now();
    while (adds.length && adds[0] <= at - MINUTE) adds.shift();
    if (adds.length >= ADDS_PER_MINUTE) return false;
    adds.push(at);
    return true;
  }

  function read(assume) {
    for (const { slug, store } of stores()) {
      try {
        activeRun.set(store, store.getActiveRun()?.id || null);
        let rev = lastRev.get(store) || 0;
        for (const row of store.liveStatuses({ sinceRev: rev })) {
          rev = Math.max(rev, row.rev);
          const key = `${row.channel}:${row.ts}`;
          const message = { channel: row.channel, ts: row.ts };
          const state = { system: row.system, agent: row.agent, task: row.task };
          if (assume) show.assume(message, state);
          else show.set(message, state);
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
    const live = [...agents.entries()].filter(([, one]) => ticking(one));
    const demand = live.reduce((sum, [, one]) => sum + MINUTE / frameMs(one), 0);
    const stretch = Math.max(1, demand / ADDS_PER_MINUTE);
    const at = now();
    for (const [key, one] of live) {
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
      const result = await show.apply(message, { mayAdd });
      if (result.retryAfterMs != null) {
        pausedUntil = now() + result.retryAfterMs;
        note({ event: 'reactions-paused', ms: result.retryAfterMs });
        return;
      }
      if (!result.settled) continue;
      unsettled.delete(key);
      const one = agents.get(key);
      if (one?.nextTickAt === Infinity) one.nextTickAt = now() + one.interval;
    }
  }

  async function step() {
    if (busy) return;
    busy = true;
    try {
      if (!display()) return;
      read(false);
      if (now() < pausedUntil) return;
      tick();
      await settle();
    } catch (error) {
      note({ event: 'status-failed', message: error.message });
    } finally {
      busy = false;
    }
  }

  function baseline() {
    if (display()) read(true);
  }

  return { baseline, step };
}

module.exports = { createTicker, ADDS_PER_MINUTE, FRAME_MS, WAITING_FRAME_MS };
