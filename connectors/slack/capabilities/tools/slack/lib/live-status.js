'use strict';

// Live status in Slack: the reactions that show an owner message's Ignite state. Ignite names the
// states (core/ignite/capabilities/tools/ignite/live-status.js) and knows no emoji; this file holds
// the Slack emoji for each state and the order rules. Pure logic: it makes no network call and keeps
// no timer. The caller passes the two reaction functions and the clock, and decides when to apply.
//
// API
// EMOJI — the Slack name of each state: one per system and task state, a list of frames per agent
//   state. ADD_GAP_MS — the least time between two adds on one message.
// liveStatus({ addReaction(channel, ts, name), removeReaction(channel, ts, name), now?, log? })
//   → one object that keeps, in memory, what every message it was given shows:
//   set(message, state)    the state to show; message = { channel, ts }, state = { system, agent,
//                          task }, each an Ignite state name or null. A task wins over an agent: the
//                          two are never shown together. A new agent state starts at its first frame.
//   assume(message, state) what the message already shows, as last recorded (after a restart): the
//                          system and task emoji as stated, the agent at an unknown frame. No call.
//   tick(message)          moves the agent state to its next frame.
//   settled(message)       true when the reactions show the state set.
//   apply(message, { mayAdd? }) → Promise<{ settled, waitUntil?, retryAfterMs? }>, never rejects.
//       Makes the calls that bring the reactions to the state set, as far as the rules allow now:
//       - the system emoji stays on the left: a new one replaces the old, then the emoji on its
//         right is removed and added again so it ends on the right;
//       - an agent frame or a task emoji is replaced remove first, then add;
//       - nothing wanted on the right (a failed turn): the agent frame or task emoji is removed;
//       - two adds on one message are ADD_GAP_MS apart: an add due sooner waits, and waitUntil
//         says when it may go;
//       - mayAdd() is asked before each add and may refuse (the caller's shared budget): the add
//         and the remove paired with it wait for a later apply;
//       - Slack's HTTP 429 stops the calls: retryAfterMs is its Retry-After (RETRY_AFTER_MS when
//         absent), and the refused call is made again on a later apply.
//       already_reacted and no_reaction pass silently. Any other error is logged as
//       { event: 'reaction-failed' } and the reaction is taken as changed, so a broken call is never
//       repeated forever.
// The reaction functions report HTTP 429 as an error with status 429 and retryAfter in seconds, or
// a message ending in "HTTP 429" or "ratelimited".

const EMOJI = Object.freeze({
  system: Object.freeze({
    queued: 'hourglass_flowing_sand',
    running: 'large_green_circle',
    fallback: 'repeat',
    retrying: 'recycle',
    failed: 'x',
  }),
  agent: Object.freeze({
    working: Object.freeze(['clock12', 'clock130', 'clock3', 'clock430', 'clock6', 'clock730', 'clock9', 'clock1030']),
    gathering: Object.freeze(['mag', 'mag_right']),
    thinking: Object.freeze(['brain', 'thought_balloon']),
    making: Object.freeze(['hammer', 'hammer_and_wrench']),
    orchestrating: Object.freeze(['busts_in_silhouette', 'bust_in_silhouette']),
    waiting: Object.freeze(['zzz', 'sleeping']),
  }),
  task: Object.freeze({
    done: 'white_check_mark',
    caveats: 'warning',
    question: 'question',
    stopped: 'black_square_for_stop',
  }),
});

const ADD_GAP_MS = 1_000;
// Slack's Retry-After measured on reactions.add, used when a 429 carries none.
const RETRY_AFTER_MS = 30_000;
const EXPECTED = /already_reacted$|no_reaction$/;
const SYSTEM_NAMES = new Set(Object.values(EMOJI.system));
const RIGHT_NAMES = new Set([...Object.values(EMOJI.agent).flat(), ...Object.values(EMOJI.task)]);

function rateLimit(error) {
  const text = String(error?.message || '');
  if (error?.status !== 429 && !/HTTP 429$|ratelimited$/.test(text)) return null;
  const seconds = Number(error?.retryAfter);
  return Number.isFinite(seconds) && seconds > 0 ? seconds * 1000 : RETRY_AFTER_MS;
}

function liveStatus({ addReaction, removeReaction, now = Date.now, log } = {}) {
  if (typeof addReaction !== 'function' || typeof removeReaction !== 'function') {
    throw new Error('liveStatus requires addReaction and removeReaction');
  }
  const messages = new Map();

  function entry(message) {
    const key = `${message.channel}:${message.ts}`;
    let one = messages.get(key);
    if (!one) {
      one = {
        channel: message.channel,
        ts: message.ts,
        want: { system: null, agent: null, task: null },
        frame: 0,
        // The names on the message, in Slack's order: an add goes to the right end.
        order: [],
        // Names that may be on the message, after a restart: removed before the next add on the right.
        unsure: new Set(),
        lastAddAt: -Infinity,
      };
      messages.set(key, one);
    }
    return one;
  }

  function wanted(one) {
    const { system, agent, task } = one.want;
    const sys = (system && EMOJI.system[system]) || null;
    let right = null;
    if (task) right = EMOJI.task[task] || null;
    else if (agent && EMOJI.agent[agent]) right = EMOJI.agent[agent][one.frame % EMOJI.agent[agent].length];
    return { sys, right };
  }

  const rightSide = (one) => [...one.order.filter((name) => RIGHT_NAMES.has(name)), ...one.unsure];
  const shownSystem = (one) => one.order.find((name) => SYSTEM_NAMES.has(name)) || null;

  function inPlace(one, sys, right) {
    if (one.unsure.size) return false;
    const names = one.order.filter((name) => RIGHT_NAMES.has(name));
    if (names.length !== 1 || names[0] !== right) return false;
    return !sys || one.order.indexOf(right) > one.order.indexOf(sys);
  }

  function isSettled(one) {
    const { sys, right } = wanted(one);
    if (shownSystem(one) !== sys) return false;
    return right ? inPlace(one, sys, right) : rightSide(one).length === 0;
  }

  async function call(fn, one, name, step) {
    try {
      await fn(one.channel, one.ts, name);
    } catch (error) {
      const retryAfterMs = rateLimit(error);
      if (retryAfterMs != null) throw Object.assign(new Error('rate limited'), { retryAfterMs });
      if (EXPECTED.test(String(error?.message || ''))) return;
      if (typeof log !== 'function') return;
      try {
        log({ event: 'reaction-failed', step, name, channel: one.channel, ts: one.ts, message: error?.message });
      } catch { /* a reaction never breaks its caller */ }
    }
  }

  async function add(one, name) {
    one.lastAddAt = now();
    await call(addReaction, one, name, 'add');
    one.order = [...one.order.filter((shown) => shown !== name), name];
  }

  async function remove(one, names) {
    for (const name of names) {
      await call(removeReaction, one, name, 'remove');
      one.order = one.order.filter((shown) => shown !== name);
      one.unsure.delete(name);
    }
  }

  // null when an add may go now; otherwise why it waits.
  function gate(one, mayAdd) {
    const at = one.lastAddAt + ADD_GAP_MS;
    if (now() < at) return { settled: false, waitUntil: at };
    if (!mayAdd()) return { settled: false };
    return null;
  }

  async function apply(message, { mayAdd = () => true } = {}) {
    const one = entry(message);
    try {
      for (;;) {
        const { sys, right } = wanted(one);
        if (!right && rightSide(one).length) await remove(one, rightSide(one));
        const old = shownSystem(one);
        if (old !== sys) {
          if (sys) {
            const wait = gate(one, mayAdd);
            if (wait) return wait;
          }
          await remove(one, one.order.filter((name) => SYSTEM_NAMES.has(name)));
          if (sys) await add(one, sys);
          continue;
        }
        if (right && !inPlace(one, sys, right)) {
          const wait = gate(one, mayAdd);
          if (wait) return wait;
          await remove(one, rightSide(one));
          await add(one, right);
          continue;
        }
        return { settled: true };
      }
    } catch (error) {
      if (error.retryAfterMs != null) return { settled: false, retryAfterMs: error.retryAfterMs };
      return { settled: false };
    }
  }

  return {
    set(message, state) {
      const one = entry(message);
      const next = {
        system: state?.system ?? null,
        agent: state?.task ? null : (state?.agent ?? null),
        task: state?.task ?? null,
      };
      if (next.agent !== one.want.agent) one.frame = 0;
      one.want = next;
    },
    assume(message, state) {
      this.set(message, state);
      const one = entry(message);
      const { sys } = wanted(one);
      one.order = [sys, one.want.task ? EMOJI.task[one.want.task] : null].filter(Boolean);
      one.unsure = new Set(one.want.agent ? EMOJI.agent[one.want.agent] || [] : []);
    },
    tick(message) {
      const one = entry(message);
      if (one.want.agent) one.frame += 1;
    },
    settled(message) {
      return isSettled(entry(message));
    },
    apply,
  };
}

module.exports = { liveStatus, EMOJI, ADD_GAP_MS, RETRY_AFTER_MS };
