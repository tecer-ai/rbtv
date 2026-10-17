'use strict';

// Live status: what Ignite shows the owner on the latest message of each conversation's thread while
// its work runs, in three layers. Ignite owns the states and names no emoji: a communication connector
// shows them in its medium (Slack: connectors/slack/capabilities/tools/slack/lib/live-status.js). This
// file writes the state into the agent's store; status-ticker.js, in the waking service, reads it and
// shows it.
//
// API
// SYSTEM   queued | running | fallback | retrying | failed — set by Ignite
// AGENT    working | gathering | thinking | making | orchestrating | waiting | transcribing — working
//          by Ignite at model start, waiting at waiting_workers, transcribing during audio preprocessing
// DECLARED gathering | thinking | making | orchestrating — the agent states `ignite status` takes
// TASK     done | caveats | question | stopped — from the turn result, shown at delivery
// MEANING  { system, agent, task }: each layer's states in the order above, each with one plain
//          sentence of what it tells the owner; SYSTEM, AGENT and TASK are its keys. A connector's
//          legend shows the sentence beside the state's sign in its medium.
// At most two layers show: the system, plus the agent during the work or the task after it.
// Where they show: the store keeps one row per message of a conversation Ignite knows about, each
// owner message it accepts and each Slack message of a reply or post it delivers into the thread (its
// text, each file). The newest of them (highest Slack ts) is the conversation's live row and shows its
// layers. Every write first makes the newest row the live row: the layers move there, and the message
// that held them keeps only its task. A message keeps every task it shows, the conversation's task a
// post shows included, with the owner message that task answers; a new owner message keeps none. While
// a later turn's agent state shows on a message that keeps a task, the task is hidden; it shows again
// once the live status moves on.
// taskOf(disposition, caveats) → the task state a turn result gives, or null for continue and
//   waiting_workers.
// messageOf(store, run, log?) → { conversationKey, channel, ts } of the owner message a turn answers:
//   an owner turn's own message; a continue or wake turn's latest owner message of its work. null for
//   a scheduled wake, which shows nothing.
// The service-side writes below never throw: a failed write is logged as { event: 'status-failed' }.
// message is the owner message a turn answers (messageOf); each write acts on its conversation.
//   received(store, message, log)               the new owner message is known; system queued, and no
//                                               task on it, unless a turn of the conversation runs
//   started(store, message, runId, log)         system running, agent working, no task
//   transcribing(store, message, runId, log)    agent transcribing during incoming audio processing;
//                                               system unchanged, or queued for a new row; no task
//   fellBack(store, message, log)               system fallback
//   ended(store, message, disposition, task, replies, log)
//                                               waiting_workers → agent waiting; continue → agent
//                                               working; with no replies, the task at once, kept by
//                                               the newest message that is not an owner message
//                                               still waiting for its turn
//   failed(store, message, held, log)           system retrying, or failed once held; no agent
//   delivered(store, reply, answer, log)        reply { conversationKey, channel, messages }, delivered
//                                               into a thread that shows a live status: messages, the
//                                               Slack ts of each of its messages, are known, and the
//                                               newest stands for the reply. answer is the mark of the
//                                               turn it belongs to, { ts, runId?, task? }, with task
//                                               once every reply of that turn is delivered: the reply
//                                               keeps that task, which replaces the turn's agent state;
//                                               null for a post
//   deliveryFailed(store, mark, log)            mark { conversationKey, runId? }: while the live row
//                                               belongs to that turn (any turn for a mark without a
//                                               runId), system failed and no agent. Nothing moves
//   waitEnded(store, message, log)              a waiting message whose work no longer waits for
//                                               workers (stopped, held, ended): no agent
//   When no turn of the conversation runs and an owner message of it waits for a turn, a turn's
//   running or fallback gives way to queued.
//   Callers run ended and failed in the transaction that ends the run, and delivered and
//   deliveryFailed in the one that records the delivery, so a stop never loses the state.
// The two writes `ignite status` makes throw a refusal (exitCode 1) instead:
//   declare(store, conversationKey, state) → the row, or null when the running turn answers no
//     owner message.
//   markTask(store, conversationKey, ts, task) → the newest row that now keeps the task of ts: ts is
//     an owner message of the conversation whose turn has finished, or a message that keeps its task
//     or belongs to a reply of that turn. Every message keeping that task takes the new one (the owner
//     message itself when none does). The running turn's own owner message is refused.

const MEANING = Object.freeze({
  system: Object.freeze({
    queued: 'Received; waiting for a turn to start.',
    running: "A turn is running on the agent's own model.",
    fallback: 'A turn is running on a fallback model.',
    retrying: 'The turn failed and will be tried again.',
    failed: 'The work failed and will not be retried.',
  }),
  agent: Object.freeze({
    working: 'At work; it has not named the kind of work.',
    gathering: 'Reading, searching and collecting what the work needs.',
    thinking: 'Analysing, comparing, deciding or planning.',
    making: 'Writing, building or editing files.',
    orchestrating: 'Launching and coordinating workers.',
    waiting: 'Waiting for its workers to finish.',
    transcribing: 'The system is transcribing incoming audio before the model starts.',
  }),
  task: Object.freeze({
    done: 'The work is done.',
    caveats: 'Done, with problems worth a follow-up.',
    question: 'The agent asked a question and waits for the answer.',
    stopped: 'The work stopped before it was done.',
  }),
});
const SYSTEM = Object.freeze(Object.keys(MEANING.system));
const AGENT = Object.freeze(Object.keys(MEANING.agent));
const DECLARED = Object.freeze(['gathering', 'thinking', 'making', 'orchestrating']);
const TASK = Object.freeze(Object.keys(MEANING.task));

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

// Slack ts order: whole seconds, then the fraction as six digits.
function newer(a, b) {
  const [as, af = ''] = String(a).split('.');
  const [bs, bf = ''] = String(b).split('.');
  if (Number(as) !== Number(bs)) return Number(as) > Number(bs);
  return af.padEnd(6, '0') > bf.padEnd(6, '0');
}

const newest = (rows) => rows.reduce((one, row) => (newer(row.ts, one.ts) ? row : one));

const COLUMN = { system: 'system', agent: 'agent', task: 'task', runId: 'run_id', kept: 'kept', keptFor: 'kept_for' };

// Writes the fields that differ from the row; the row as it is when none does.
function change(store, row, fields) {
  const diff = Object.entries(fields).filter(([name, value]) => value !== undefined && (row[COLUMN[name]] ?? null) !== value);
  if (!diff.length) return row;
  return store.setLiveStatus({ channel: row.channel, ts: row.ts, ...Object.fromEntries(diff) });
}

// A message of the conversation Ignite knows about from now on, showing nothing yet; keptFor, the owner
// message it answers.
function know(store, message, keptFor) {
  if (store.getLiveStatus(message.channel, message.ts)) return;
  store.setLiveStatus({ conversationKey: message.conversationKey, channel: message.channel, ts: message.ts, keptFor });
}

// The conversation's live row, its newest message, or null when it has none. The layers and their run
// move there from the row that held them; every other message is left with the task it keeps. A task
// the new live row shows is one it keeps, with the owner message that task answers. Older rows are
// written first, so the ticker clears the old message before it shows the new one.
function follow(store, key) {
  const rows = store.liveStatuses({ conversationKey: key });
  if (!rows.length) return null;
  const latest = newest(rows);
  const from = latest.system || latest.agent ? latest : rows.filter((row) => row.system || row.agent).at(-1);
  for (const row of rows) {
    if (row !== latest) change(store, row, { system: null, agent: null, task: row.kept ?? null, runId: null });
  }
  if (!from || from === latest) return latest;
  return change(store, latest, {
    system: from.system, agent: from.agent, task: from.task, runId: from.run_id,
    ...(from.task && { kept: from.task, keptFor: from.kept_for }),
  });
}

// Writes fields, or fields(row), on the conversation's live row.
function onLive(store, key, fields) {
  const row = follow(store, key);
  if (!row) return null;
  return change(store, row, typeof fields === 'function' ? fields(row) : fields);
}

const runs = (store, key) => store.getActiveRun()?.conversation_key === key;

// A turn's running or fallback, once no turn of the conversation runs and an owner message of it
// waits for one: queued.
function idle(store, key, system) {
  if (system !== 'running' && system !== 'fallback') return system;
  if (runs(store, key)) return system;
  return store.pendingOwnerTs(key).length ? 'queued' : system;
}

function received(store, message, log) {
  const key = message?.conversationKey;
  if (!key || !message.channel || !message.ts) return null;
  return guard(log, () => store.transaction(() => {
    know(store, message);
    return onLive(store, key, (row) => {
      if (runs(store, key)) return {};
      // A new request: its message shows and keeps no task of the work before it.
      return { system: 'queued', ...(row.ts === message.ts && { task: null, kept: null, keptFor: null }) };
    });
  }));
}

function transcribing(store, message, runId, log) {
  const key = message?.conversationKey;
  if (!key || !message.channel || !message.ts) return null;
  return guard(log, () => store.transaction(() => {
    know(store, message);
    return onLive(store, key, (row) => ({ system: row.system || 'queued', agent: 'transcribing', task: null, runId }));
  }));
}

function started(store, message, runId, log) {
  const key = message?.conversationKey;
  if (!key || !message.channel || !message.ts) return null;
  return guard(log, () => store.transaction(() => {
    know(store, message);
    return onLive(store, key, { system: 'running', agent: 'working', task: null, runId });
  }));
}

function fellBack(store, message, log) {
  const key = message?.conversationKey;
  if (!key) return null;
  return guard(log, () => store.transaction(() => onLive(store, key, { system: 'fallback' })));
}

// The task of a turn with no reply to carry it, kept by the newest message that is not an owner
// message still waiting for its turn (a request the turn never saw). The live row ends the turn's agent.
function showTask(store, key, task, answers) {
  const live = follow(store, key);
  if (!live) return null;
  const waiting = new Set(store.pendingOwnerTs(key));
  const seen = store.liveStatuses({ conversationKey: key }).filter((row) => !waiting.has(row.ts));
  const carrier = seen.length ? newest(seen) : live;
  const keeps = { task, kept: task, keptFor: answers };
  if (carrier.ts !== live.ts) change(store, carrier, keeps);
  return change(store, store.getLiveStatus(live.channel, live.ts), {
    agent: null,
    system: idle(store, key, live.system),
    ...(carrier.ts === live.ts && keeps),
  });
}

function ended(store, message, disposition, task, replies, log) {
  const key = message?.conversationKey;
  if (!key) return null;
  if (disposition === 'waiting_workers' || disposition === 'continue') {
    const agent = disposition === 'waiting_workers' ? 'waiting' : 'working';
    return guard(log, () => store.transaction(() => onLive(store, key, (row) => ({ agent, system: idle(store, key, row.system) }))));
  }
  if (task && !replies) return guard(log, () => store.transaction(() => showTask(store, key, task, message.ts)));
  return null;
}

function failed(store, message, held, log) {
  const key = message?.conversationKey;
  if (!key || !message.channel || !message.ts) return null;
  return guard(log, () => store.transaction(() => {
    // A turn that fails before it starts (a voice note it cannot hear) still shows its failure.
    know(store, message);
    return onLive(store, key, { system: held ? 'failed' : 'retrying', agent: null });
  }));
}

function delivered(store, reply, answer, log) {
  const key = reply?.conversationKey;
  const messages = (reply?.messages || []).filter(Boolean);
  if (!key || !reply.channel || !messages.length) return null;
  return guard(log, () => store.transaction(() => {
    // A thread that shows no live status (a scheduled wake's, a proactive post's) gets none.
    if (!store.liveStatuses({ conversationKey: key }).length) return null;
    const ts = messages.reduce((one, other) => (newer(other, one) ? other : one));
    // Each message of a reply leads `ignite status --message` to the owner message the reply answers.
    for (const one of messages) know(store, { conversationKey: key, channel: reply.channel, ts: one }, answer?.ts);
    const live = follow(store, key);
    const task = answer?.task || null;
    // The live layers belong to the reply's turn: its task replaces its agent state.
    const ours = !answer?.runId || live.run_id === answer.runId;
    const keeps = task ? { kept: task, keptFor: answer.ts } : {};
    if (task && ts !== live.ts) change(store, store.getLiveStatus(reply.channel, ts), { task, ...keeps });
    return change(store, live, {
      system: idle(store, key, live.system),
      ...(task && ours && { agent: null }),
      ...(task && ts === live.ts && { ...keeps, ...(ours && { task }) }),
    });
  }));
}

function deliveryFailed(store, mark, log) {
  const key = mark?.conversationKey;
  if (!key) return null;
  // A reply of an earlier turn that gives up leaves a later turn's state as it is.
  return guard(log, () => store.transaction(() => onLive(store, key, (row) => (
    !mark.runId || row.run_id === mark.runId ? { system: 'failed', agent: null } : {}
  ))));
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

// The running turn of this agent, which must belong to the conversation.
function activeRun(store, conversationKey) {
  const run = store.getActiveRun();
  if (!run) throw refuse('no turn of this agent is running; ignite status runs inside a turn');
  if (run.conversation_key !== conversationKey) {
    throw refuse(`the running turn belongs to ${run.conversation_key}, not ${conversationKey}`);
  }
  return run;
}

function declare(store, conversationKey, state) {
  if (!DECLARED.includes(state)) throw refuse(`unknown state: ${state}\nchoose from ${DECLARED.join(', ')}`);
  return store.transaction(() => {
    const run = activeRun(store, conversationKey);
    const row = follow(store, conversationKey);
    if (!row || row.run_id !== run.id) return null;
    return change(store, row, { agent: state });
  });
}

function markTask(store, conversationKey, ts, task) {
  if (!TASK.includes(task)) throw refuse(`unknown task state: ${task}\nchoose from ${TASK.join(', ')}`);
  return store.transaction(() => {
    const run = activeRun(store, conversationKey);
    const live = follow(store, conversationKey);
    const rows = store.liveStatuses({ conversationKey });
    const own = rows.find((one) => one.ts === ts);
    // The owner message whose task ts names, and every message keeping that task.
    const owner = own?.kept_for || ts;
    const keepers = rows.filter((one) => one.kept && one.kept_for === owner);
    if (!own && !keepers.length) throw refuse(`no message ${ts} in conversation ${conversationKey}`);
    const answering = messageOf(store, run)?.ts;
    if (answering && (ts === answering || owner === answering)) {
      throw refuse('this turn\'s own message takes its task state from RESULT_FILE: disposition and caveats');
    }
    if (!keepers.length && !store.ownerTurnFinished(conversationKey, owner)) {
      throw refuse(`message ${ts} has no finished turn yet; only an earlier message whose turn has finished takes a task state`);
    }
    // On the live row while an agent state shows, the task waits for the live status to move on.
    const marked = (keepers.length ? keepers : [own]).map((row) => {
      const hidden = row.ts === live?.ts && live.agent;
      return change(store, row, { kept: task, keptFor: owner, ...(!hidden && { task }) });
    });
    return newest(marked);
  });
}

module.exports = {
  SYSTEM, AGENT, DECLARED, TASK, MEANING,
  taskOf, messageOf, received, transcribing, started, fellBack, ended, failed, delivered, deliveryFailed, waitEnded,
  declare, markTask,
};
