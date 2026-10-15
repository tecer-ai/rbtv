'use strict';

// Live status: what Ignite shows the owner on each owner message while its work runs, in three
// layers. Ignite owns the states and names no emoji: a communication connector shows them in its
// medium (Slack: connectors/slack/capabilities/tools/slack/lib/live-status.js). This file writes the
// state into the agent's store; status-ticker.js, in the waking service, reads it and shows it.
//
// API
// SYSTEM   queued | running | fallback | retrying | failed — set by Ignite
// AGENT    working | gathering | thinking | making | orchestrating | waiting — working by Ignite at
//          each turn start, waiting by Ignite when a turn ends waiting_workers
// DECLARED gathering | thinking | making | orchestrating — the agent states `ignite status` takes
// TASK     done | caveats | question | stopped — from the turn result, shown at delivery
// At most two layers show: the system, plus the agent during the work or the task after it.
// taskOf(disposition, caveats) → the task state a turn result gives, or null for continue and
//   waiting_workers.
// messageOf(store, run, log?) → { conversationKey, channel, ts } of the owner message a turn shows
//   on: an owner turn's own message; a continue or wake turn's latest owner message of its work.
//   null for a scheduled wake.
// The service-side writes below never throw: a failed write is logged as { event: 'status-failed' }.
//   received(store, message, log)               system queued
//   started(store, message, runId, log)         system running, agent working, no task; any other
//                                               message of the conversation loses its agent state
//   fellBack(store, message, log)               system fallback
//   ended(store, message, disposition, task, replies, log)
//                                               waiting_workers → agent waiting; continue → agent
//                                               working; with no replies, the task at once
//   failed(store, message, held, log)           system retrying, or failed once held; no agent
//   delivered(store, mark, log)                 every reply carrying mark { channel, ts, task? } is
//                                               delivered: the task replaces the agent
//   deliveryFailed(store, mark, log)            system failed; no agent
//   waitEnded(store, message, log)              a waiting message whose work no longer waits for
//                                               workers (stopped, held, ended): no agent
//   A task a turn ends with (ended, delivered) also shows on every message of the same work whose
//   agent state a later turn cleared, which until then shows its system state alone.
//   Callers run ended and failed in the transaction that ends the run, and delivered and
//   deliveryFailed in the one that records the delivery, so a stop never loses the state.
// The two writes `ignite status` makes throw a refusal (exitCode 1) instead:
//   declare(store, conversationKey, state) → the row, or null when the running turn answers no
//     owner message.
//   markTask(store, conversationKey, ts, task) → the row of an earlier owner message of the
//     running turn's conversation whose last turn has finished.

const SYSTEM = Object.freeze(['queued', 'running', 'fallback', 'retrying', 'failed']);
const AGENT = Object.freeze(['working', 'gathering', 'thinking', 'making', 'orchestrating', 'waiting']);
const DECLARED = Object.freeze(['gathering', 'thinking', 'making', 'orchestrating']);
const TASK = Object.freeze(['done', 'caveats', 'question', 'stopped']);

function taskOf(disposition, caveats) {
  if (disposition === 'completed') return caveats ? 'caveats' : 'done';
  if (disposition === 'waiting_owner') return 'question';
  if (disposition === 'stopped') return 'stopped';
  return null;
}

function guard(log, fn) {
  try {
    return fn();
  } catch (error) {
    if (typeof log === 'function') {
      try { log({ event: 'status-failed', message: error.message }); } catch { /* keep the caller */ }
    }
    return null;
  }
}

function messageOf(store, run, log) {
  if (!run) return null;
  return guard(log, () => {
    const conv = store.getConversation(run.conversation_key);
    if (!conv) return null;
    let ts = null;
    if (run.kind === 'owner') ts = run.payload?.ts || null;
    else if ((run.kind === 'continue' || run.kind === 'wake') && run.work_id) ts = store.ownerTs(run.work_id);
    return ts ? { conversationKey: run.conversation_key, channel: conv.channel, ts } : null;
  });
}

function write(store, message, fields, log) {
  if (!message?.channel || !message?.ts) return null;
  return guard(log, () => store.setLiveStatus({ ...message, ...fields }));
}

function received(store, message, log) {
  return write(store, message, { system: 'queued' }, log);
}

function started(store, message, runId, log) {
  if (!message) return null;
  return guard(log, () => store.transaction(() => {
    for (const row of store.liveStatuses({ conversationKey: message.conversationKey })) {
      if (row.agent && !(row.channel === message.channel && row.ts === message.ts)) {
        store.setLiveStatus({ channel: row.channel, ts: row.ts, agent: null });
      }
    }
    return store.setLiveStatus({ ...message, system: 'running', agent: 'working', task: null, runId });
  }));
}

function fellBack(store, message, log) {
  return write(store, message, { system: 'fallback' }, log);
}

// The task on the message, and on each message of the same work whose agent state a later turn
// cleared: its turn ran (system running or fallback) and it shows neither an agent nor a task.
function showTask(store, message, task) {
  return store.transaction(() => {
    const row = store.getLiveStatus(message.channel, message.ts);
    const shown = store.setLiveStatus({ channel: message.channel, ts: message.ts, task, agent: null });
    const workId = row?.run_id ? store.getRun(row.run_id)?.work_id : null;
    for (const other of workId ? store.liveStatusesOfWork(workId) : []) {
      const cleared = !other.agent && !other.task && (other.system === 'running' || other.system === 'fallback');
      if (cleared && !(other.channel === message.channel && other.ts === message.ts)) {
        store.setLiveStatus({ channel: other.channel, ts: other.ts, task });
      }
    }
    return shown;
  });
}

function ended(store, message, disposition, task, replies, log) {
  if (!message?.channel || !message?.ts) return null;
  if (disposition === 'waiting_workers') return write(store, message, { agent: 'waiting' }, log);
  if (disposition === 'continue') return write(store, message, { agent: 'working' }, log);
  if (task && !replies) return guard(log, () => showTask(store, message, task));
  return null;
}

function failed(store, message, held, log) {
  return write(store, message, { system: held ? 'failed' : 'retrying', agent: null }, log);
}

function delivered(store, mark, log) {
  if (!mark?.task || !mark.channel || !mark.ts) return null;
  return guard(log, () => showTask(store, { channel: mark.channel, ts: mark.ts }, mark.task));
}

function deliveryFailed(store, mark, log) {
  return write(store, { channel: mark?.channel, ts: mark?.ts }, { system: 'failed', agent: null }, log);
}

function waitEnded(store, message, log) {
  // The row, when it waits for a work that no longer waits for workers.
  const ended = () => {
    const row = store.getLiveStatus(message.channel, message.ts);
    if (row?.agent !== 'waiting') return null;
    const workId = row.run_id ? store.getRun(row.run_id)?.work_id : null;
    return workId && store.getWork(workId)?.state === 'waiting_workers' ? null : row;
  };
  return guard(log, () => {
    if (!ended()) return null;
    return store.transaction(() => {
      const row = ended();
      return row ? store.setLiveStatus({ channel: row.channel, ts: row.ts, agent: null }) : null;
    });
  });
}

function refuse(message) {
  const error = new Error(`${message}\nNothing changed.\nignite status -h`);
  error.exitCode = 1;
  return error;
}

function declare(store, conversationKey, state) {
  if (!DECLARED.includes(state)) throw refuse(`unknown state: ${state}\nchoose from ${DECLARED.join(', ')}`);
  return store.transaction(() => {
    const run = store.getActiveRun();
    if (!run) throw refuse('no turn of this agent is running; ignite status runs inside a turn');
    if (run.conversation_key !== conversationKey) {
      throw refuse(`the running turn belongs to ${run.conversation_key}, not ${conversationKey}`);
    }
    const row = store.liveStatusOfRun(run.id);
    if (!row) return null;
    return store.setLiveStatus({ channel: row.channel, ts: row.ts, agent: state });
  });
}

function markTask(store, conversationKey, ts, task) {
  if (!TASK.includes(task)) throw refuse(`unknown task state: ${task}\nchoose from ${TASK.join(', ')}`);
  return store.transaction(() => {
    const run = store.getActiveRun();
    if (!run) throw refuse('no turn of this agent is running; ignite status runs inside a turn');
    if (run.conversation_key !== conversationKey) {
      throw refuse(`the running turn belongs to ${run.conversation_key}, not ${conversationKey}`);
    }
    const row = store.liveStatuses({ conversationKey }).find((one) => one.ts === ts);
    if (!row) throw refuse(`no owner message ${ts} in conversation ${conversationKey}`);
    if (row.run_id === run.id) {
      throw refuse('this turn\'s own message takes its task state from RESULT_FILE: disposition and caveats');
    }
    if (!row.run_id || store.getRun(row.run_id)?.state !== 'finished') {
      throw refuse(`owner message ${ts} has no finished turn yet; only an earlier message whose turn has finished takes a task state`);
    }
    return store.setLiveStatus({ channel: row.channel, ts: row.ts, task, agent: null });
  });
}

module.exports = {
  SYSTEM, AGENT, DECLARED, TASK,
  taskOf, messageOf, received, started, fellBack, ended, failed, delivered, deliveryFailed, waitEnded,
  declare, markTask,
};
