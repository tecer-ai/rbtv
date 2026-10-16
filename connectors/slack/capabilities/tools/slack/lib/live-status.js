'use strict';

// Live status in Slack: the reactions that show a message's Ignite state. Ignite names the
// states (core/ignite/capabilities/tools/ignite/live-status.js) and knows no emoji; this file holds
// the Slack emoji for each state, the order rules and the legend that explains them. Pure logic: it
// makes no network call and keeps no timer. The caller passes the two reaction functions, the clock
// and where to record what each message shows, and decides when to apply.
//
// API
// EMOJI — the Slack name of each state: one per system and task state, a list of frames per agent
//   state. ADD_GAP_MS — the least time between two adds on one message.
// legendView(meaning) → the modal (views.open's view) that explains every reaction. meaning is
//   Ignite's MEANING: { system, agent, task }, each layer's states in order with one sentence each.
//   Per layer: a divider, its name and place, then one row per state of meaning as a two-column
//   table (section fields, LEGEND_ROWS rows per section): its emoji from EMOJI, an agent state's
//   frames in order, with the state name in bold, beside its sentence.
// liveStatus({ addReaction(channel, ts, name), removeReaction(channel, ts, name), now?, log?, record? })
//   → one object that keeps, in memory, what every message it was given shows:
//   set(message, state)    the state to show; message = { channel, ts }, state = { system, agent,
//                          task }, each an Ignite state name or null. A task wins over an agent: the
//                          two are never shown together. A new agent state starts at its first frame.
//   restore(message, state, shown)
//                          a message not in memory (after a restart): the state to show and what it
//                          shows, as record() last gave it. null is an unknown display: the message may
//                          hold any name this file shows, so every one is removed before the state is
//                          shown. The agent continues from the frame shown. No call.
//   tick(message)          moves the agent state to its next frame.
//   settled(message)       true when the reactions show the state set.
//   apply(message, { mayAdd? }) → Promise<{ settled, waitUntil?, retryAfterMs? }>, never rejects.
//       Makes the calls that bring the reactions to the state set, one at a time:
//       - the system emoji is on the left at every moment: when it changes, the emoji on its right
//         is removed first, the system replaced, and the right one added again ADD_GAP_MS later;
//         when it goes with none to replace it, an agent frame or task not wanted goes first, then
//         the system, and a task wanted stays where it is;
//       - an agent frame or a task emoji is replaced remove first, then add;
//       - nothing is added on a side while another name of that side may still be on the message:
//         a name is gone only once Slack acknowledged its removal;
//       - two adds on one message are ADD_GAP_MS apart: an add due sooner waits, and waitUntil
//         says when it may go;
//       - mayAdd() is asked before each add and may refuse (the caller's shared budget): the add
//         and the remove paired with it wait for a later apply;
//       - Slack's HTTP 429 stops the calls: retryAfterMs is its Retry-After (RETRY_AFTER_MS when
//         absent), and the refused call is made again on a later apply. An HTTP 5xx stops them for
//         SERVER_PAUSE_MS.
//       already_reacted and no_reaction pass silently; message_not_found ends the message's calls.
//       Any other error, an HTTP 5xx included, is logged as { event: 'reaction-failed' } and leaves
//       its name uncertain: the name is removed before anything is added beside it. A failed call,
//       or an error of this file's own (a record that cannot be saved, logged as
//       { event: 'status-failed' }), makes the message wait BACKOFF_MS before its next call,
//       doubling with each failure in a row up to BACKOFF_MAX_MS: waitUntil says until when.
//   record(message, shown) — the caller's, called before each call and after its answer, with
//     shown = { order, unsure, lastAddAt, gone }: order the names Slack acknowledged, in its order;
//     unsure the names a call may or may not have changed; lastAddAt the last add's time. Kept by
//     the caller and given back to restore(), it lets the next service finish what a stopped one
//     began. A record that throws stops the call before it is made.
// The reaction functions report an HTTP error with status (and, on 429, retryAfter in seconds), or a
// message ending in "HTTP <status>", "ratelimited" or the Slack error code.

const EMOJI = Object.freeze({
  system: Object.freeze({
    queued: 'hourglass_flowing_sand',
    running: 'large_green_circle',
    fallback: 'repeat',
    retrying: 'recycle',
    failed: 'x',
  }),
  agent: Object.freeze({
    working: Object.freeze(['clock12', 'clock2', 'clock4', 'clock6', 'clock8', 'clock10']),
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
const SERVER_PAUSE_MS = 5_000;
const BACKOFF_MS = 1_000;
const BACKOFF_MAX_MS = 300_000;
const EXPECTED = /already_reacted$|no_reaction$/;
const GONE = /message_not_found$/;
const SYSTEM_NAMES = new Set(Object.values(EMOJI.system));
// Every name this file can show: what a message whose display is unknown may hold.
const ALL_NAMES = Object.freeze([...SYSTEM_NAMES, ...Object.values(EMOJI.agent).flat(), ...Object.values(EMOJI.task)]);
const isSystem = (name) => SYSTEM_NAMES.has(name);

function rateLimit(error) {
  const text = String(error?.message || '');
  if (error?.status !== 429 && !/HTTP 429$|ratelimited$/.test(text)) return null;
  const seconds = Number(error?.retryAfter);
  return Number.isFinite(seconds) && seconds > 0 ? seconds * 1000 : RETRY_AFTER_MS;
}

function serverError(error) {
  const status = Number(error?.status);
  return (status >= 500 && status <= 599) || /HTTP 5\d\d$/.test(String(error?.message || ''));
}

function liveStatus({ addReaction, removeReaction, now = Date.now, log, record } = {}) {
  if (typeof addReaction !== 'function' || typeof removeReaction !== 'function') {
    throw new Error('liveStatus requires addReaction and removeReaction');
  }
  const messages = new Map();

  function note(fields) {
    if (typeof log !== 'function') return;
    try { log(fields); } catch { /* a reaction never breaks its caller */ }
  }

  function entry(message) {
    const key = `${message.channel}:${message.ts}`;
    let one = messages.get(key);
    if (!one) {
      one = {
        channel: message.channel,
        ts: message.ts,
        want: { system: null, agent: null, task: null },
        frame: 0,
        // The names Slack acknowledged on the message, in its order: an add goes to the right end.
        order: [],
        // The names a call may or may not have changed: removed before anything is added beside them.
        unsure: new Set(),
        lastAddAt: -Infinity,
        gone: false,
        // An add the shared budget and the gap allowed, kept while the removes before it are made.
        ticket: false,
        failures: 0,
        retryAt: -Infinity,
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

  // The next call toward the state set: { remove, replaced } (replaced: an add on that side follows),
  // { add }, or null when the reactions show the state.
  function next(one) {
    const { sys, right } = wanted(one);
    const unsure = [...one.unsure];
    const systems = one.order.filter(isSystem);
    const rights = one.order.filter((name) => !isSystem(name));
    const sysInPlace = !unsure.some(isSystem) && (sys ? systems.length === 1 && systems[0] === sys : !systems.length);
    if (!sysInPlace && !sys) {
      // Nothing comes to the left: the right side keeps a task it still shows.
      return { remove: rights.find((name) => name !== right) || unsure.find(isSystem) || systems[0], replaced: false };
    }
    if (!sysInPlace) {
      // The right side goes first, so the new system emoji lands on the left.
      const first = unsure.find((name) => !isSystem(name)) || rights[0]
        || unsure.find(isSystem) || systems.find((name) => name !== sys);
      if (first) return { remove: first, replaced: Boolean(sys) };
      return { add: sys };
    }
    const misplaced = (name) => name !== right || (sys && one.order.indexOf(name) < one.order.indexOf(sys));
    const first = unsure[0] || rights.find(misplaced);
    if (first) return { remove: first, replaced: Boolean(right) };
    if (right && !rights.includes(right)) return { add: right };
    return null;
  }

  function shownOf(one) {
    return {
      order: [...one.order],
      unsure: [...one.unsure],
      lastAddAt: Number.isFinite(one.lastAddAt) ? one.lastAddAt : null,
      gone: one.gone,
    };
  }

  function save(one) {
    if (typeof record === 'function') record({ channel: one.channel, ts: one.ts }, shownOf(one));
  }

  // What Slack did with one call: { done }, { gone }, { pauseMs } (429: nothing changed), or
  // { unknown } (the call may have changed the message), with pauseMs on an HTTP 5xx.
  async function call(fn, one, name, step) {
    try {
      await fn(one.channel, one.ts, name);
      return { done: true };
    } catch (error) {
      const text = String(error?.message || '');
      if (EXPECTED.test(text)) return { done: true };
      if (GONE.test(text)) return { gone: true };
      const retryAfterMs = rateLimit(error);
      if (retryAfterMs != null) return { pauseMs: retryAfterMs };
      note({ event: 'reaction-failed', step, name, channel: one.channel, ts: one.ts, message: error?.message });
      return serverError(error) ? { unknown: true, pauseMs: SERVER_PAUSE_MS } : { unknown: true };
    }
  }

  async function add(one, name) {
    const before = one.lastAddAt;
    one.unsure.add(name);
    one.lastAddAt = now();
    one.ticket = false;
    save(one);
    const answer = await call(addReaction, one, name, 'add');
    if (answer.done) {
      one.unsure.delete(name);
      one.order = [...one.order.filter((shown) => shown !== name), name];
    } else if (answer.pauseMs != null && !answer.unknown) {
      one.unsure.delete(name);
      one.lastAddAt = before;
    }
    if (!answer.gone) save(one);
    return answer;
  }

  async function remove(one, name) {
    const at = one.order.indexOf(name);
    one.order = one.order.filter((shown) => shown !== name);
    one.unsure.add(name);
    save(one);
    const answer = await call(removeReaction, one, name, 'remove');
    if (answer.done) {
      one.unsure.delete(name);
    } else if (answer.pauseMs != null && !answer.unknown && at >= 0) {
      one.unsure.delete(name);
      one.order.splice(at, 0, name);
    }
    if (!answer.gone) save(one);
    return answer;
  }

  function backOff(one) {
    one.failures += 1;
    one.ticket = false;
    one.retryAt = now() + Math.min(BACKOFF_MAX_MS, BACKOFF_MS * 2 ** (one.failures - 1));
    return { settled: false, waitUntil: one.retryAt };
  }

  // null when an add may go now; otherwise why it waits. An add allowed once stays allowed until made.
  function gate(one, mayAdd) {
    if (one.ticket) return null;
    const at = one.lastAddAt + ADD_GAP_MS;
    if (now() < at) return { settled: false, waitUntil: at };
    if (!mayAdd()) return { settled: false };
    one.ticket = true;
    return null;
  }

  async function apply(message, { mayAdd = () => true } = {}) {
    const one = entry(message);
    if (one.gone) return { settled: true };
    if (now() < one.retryAt) return { settled: false, waitUntil: one.retryAt };
    try {
      for (;;) {
        const step = next(one);
        if (!step) {
          one.failures = 0;
          one.ticket = false;
          return { settled: true };
        }
        if (step.add || step.replaced) {
          const wait = gate(one, mayAdd);
          if (wait) return wait;
        }
        const answer = step.add ? await add(one, step.add) : await remove(one, step.remove);
        if (answer.gone) {
          one.gone = true;
          one.order = [];
          one.unsure.clear();
          save(one);
          return { settled: true };
        }
        if (answer.pauseMs != null) {
          if (answer.unknown) backOff(one);
          one.ticket = false;
          return { settled: false, retryAfterMs: answer.pauseMs };
        }
        if (answer.unknown) return backOff(one);
        one.failures = 0;
      }
    } catch (error) {
      note({ event: 'status-failed', channel: one.channel, ts: one.ts, message: error?.message });
      return backOff(one);
    }
  }

  function set(message, state) {
    const one = entry(message);
    const want = {
      system: state?.system ?? null,
      agent: state?.task ? null : (state?.agent ?? null),
      task: state?.task ?? null,
    };
    if (want.agent !== one.want.agent) one.frame = 0;
    one.want = want;
    return one;
  }

  return {
    set(message, state) {
      set(message, state);
    },
    restore(message, state, shown) {
      const one = set(message, state);
      const names = (list) => (Array.isArray(list) ? list.filter((name) => typeof name === 'string') : []);
      one.order = names(shown?.order);
      one.unsure = new Set(shown == null ? ALL_NAMES : names(shown.unsure));
      one.lastAddAt = Number.isFinite(shown?.lastAddAt) ? shown.lastAddAt : -Infinity;
      one.gone = shown?.gone === true;
      const frames = (one.want.agent && EMOJI.agent[one.want.agent]) || [];
      one.frame = Math.max(0, frames.findIndex((name) => one.order.includes(name)));
    },
    tick(message) {
      const one = entry(message);
      if (one.want.agent) one.frame += 1;
    },
    settled(message) {
      const one = entry(message);
      return one.gone || next(one) === null;
    },
    apply,
  };
}

// Each layer's name and place in the legend; the reactions show the system on the left.
const LEGEND_GROUPS = Object.freeze([
  ['system', '*System* · left · stays still'],
  ['agent', '*Agent* · right · moves while it works'],
  ['task', '*Task* · right · once it replies'],
]);
// A section holds at most 10 fields: five rows of two.
const LEGEND_ROWS = 5;

function legendView(meaning) {
  const mrkdwn = (text) => ({ type: 'mrkdwn', text });
  const blocks = [
    { type: 'header', text: { type: 'plain_text', text: 'What the reactions mean' } },
    { type: 'context', elements: [mrkdwn('The latest message of a thread carries up to two reactions. The left one is the system and stays still. '
      + 'The right one is the agent while it works, then the task once it replies. Earlier messages keep their final task.')] },
  ];
  for (const [layer, heading] of LEGEND_GROUPS) {
    blocks.push({ type: 'divider' }, { type: 'section', text: mrkdwn(heading) });
    const rows = Object.entries(meaning?.[layer] || {}).map(([state, sentence]) => {
      // An animated state shows its first two frames only: enough to read as motion (owner, 2026-10-16).
      const emoji = [EMOJI[layer][state] || []].flat().slice(0, 2).map((name) => `:${name}:`).join('');
      const name = state.charAt(0).toUpperCase() + state.slice(1);
      return [mrkdwn([emoji, `*${name}*`].filter(Boolean).join(' ')), mrkdwn(sentence)];
    });
    for (let at = 0; at < rows.length; at += LEGEND_ROWS) {
      blocks.push({ type: 'section', fields: rows.slice(at, at + LEGEND_ROWS).flat() });
    }
  }
  return {
    type: 'modal',
    title: { type: 'plain_text', text: 'Live status' },
    close: { type: 'plain_text', text: 'Close' },
    blocks,
  };
}

module.exports = { liveStatus, legendView, EMOJI, ADD_GAP_MS, RETRY_AFTER_MS, SERVER_PAUSE_MS, BACKOFF_MS, BACKOFF_MAX_MS };
