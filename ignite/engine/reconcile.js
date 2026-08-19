'use strict';

// engine/reconcile.js — THE GOAL WATCHER (D1 / D15). One derivation of owed work from the
// ledgers, one pass per goal, cadence-gated to 300 s. Acts first, escalates second.
//
// SHAPE A: called from engine/lane-watch.js. Coverage is structural — every goal the watch
// pass sees, no per-goal registration. Owner escalation stays inside the daemon process
// (a fire-tool job cannot reach the Slack credential; ticker.js#runToolLikeExec / toolExecEnv).
//
// ⚠ READYNESS IS coord.py's. This module never re-derives DAG math. It calls
// seeding.readySeats (the one subprocess) and reads the ledgers.
// ⚠ DEAD SEATS ARE NEVER OWED (D22). ready-seats carries `dead` beside BLOCKED.
// ⚠ GRANTS ARE NOT TOUCHED. Launch is heartStore.enqueue({ onSeatBusy: 'queue' }).
//    delete-grants has nothing to remove here.
// Class (c) `outputs-unverified` is routed as class (a): verified-done records it as
// `incomplete`, which is already non-terminal. One mechanism.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync, spawnSync } = require('node:child_process');
const { requirePythonCmd } = require('../lib/python-cmd');
const {
  readySeats, readCsv, jobIdFor, uncastSeats, seatBootPrompt, readTaskforce,
} = require('./seeding');

const COORD_PY = path.join(__dirname, '..', 'team-kit', 'coord.py');
const RECOVER_ROOM = path.join(__dirname, '..', 'jobs', 'recover-room.py');

const CADENCE_MS = 5 * 60 * 1000;
const STRIKE_LIMIT = 3;
const OWNER_AFTER_STUCK = 3;

const RECORD_DISPOSITIONS = Object.freeze(['done', 'renew', 'revive', 'exited', 'incomplete']);
const TERMINAL_DISPOSITIONS = Object.freeze(['done']);
const NON_TERMINAL_DISPOSITIONS = Object.freeze(
  RECORD_DISPOSITIONS.filter((d) => !TERMINAL_DISPOSITIONS.includes(d)),
);
const EXTRA_NON_TERMINAL = Object.freeze(['renew-interrupted', 'unverified']);
const STAFF_CHAIRS = Object.freeze(['leader', 'consultant', 'goal-master']);

const MSG_HEADER = /^## (?<num>\d+) \| from: (?<sender>\S+)(?: \| from-pkg: (?<from_pkg>\S+))? \| to: (?<to>\S+) \| type: (?<type>\S+)(?: \| supersedes: (?<supersedes>\d+))?(?: \| re: (?<re>\d+))?(?: \| exec: (?<exec_id>\S+))?(?: \| milestone: (?<milestone>\S+))?(?: \| chat-thread: (?<chat_thread>\S+))?(?: \| deliver: (?<deliver>post|wake))?(?: \| why: (?<why>[^|]*?))? \| (?<ts>.+)$/;

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function normTs(s) {
  if (!s) return '';
  return String(s).replace('T', ' ').replace(/Z$/, '').replace(/\.\d+$/, '').trim();
}

function tsAfter(a, b) {
  const na = normTs(a);
  const nb = normTs(b);
  if (!na || !nb) return false;
  return na > nb;
}

function sessionsPath(goalFolder) {
  const root = path.join(goalFolder, 'sessions.csv');
  if (fs.existsSync(root)) return root;
  const coord = path.join(goalFolder, 'coordination', 'sessions.csv');
  return fs.existsSync(coord) ? coord : root;
}

function messagesPath(goalFolder) {
  const coord = path.join(goalFolder, 'coordination', 'messages.md');
  if (fs.existsSync(coord)) return coord;
  return path.join(goalFolder, 'messages.md');
}

function loadSessions(goalFolder) {
  const p = sessionsPath(goalFolder);
  if (!fs.existsSync(p)) return [];
  try { return readCsv(p); } catch { return []; }
}

function loadMessages(goalFolder) {
  const p = messagesPath(goalFolder);
  if (!fs.existsSync(p)) return [];
  let text;
  try { text = fs.readFileSync(p, 'utf8'); } catch { return []; }
  const blocks = [];
  for (const line of text.split('\n')) {
    const m = line.match(MSG_HEADER);
    if (!m) continue;
    blocks.push({
      num: Number(m.groups.num),
      sender: m.groups.sender,
      to: m.groups.to,
      type: m.groups.type,
      ts: (m.groups.ts || '').trim(),
    });
  }
  return blocks;
}

function isNonTerminal(disp) {
  const d = String(disp || '').trim();
  if (!d) return false;
  return NON_TERMINAL_DISPOSITIONS.includes(d) || EXTRA_NON_TERMINAL.includes(d);
}

function pidAlive(pid) {
  const n = Number(pid);
  if (!Number.isInteger(n) || n <= 1) return false;
  try { return fs.existsSync(`/proc/${n}`); } catch { return false; }
}

function lastBySeat(rows) {
  const last = new Map();
  for (const r of rows) {
    const seat = (r.seat || '').trim();
    if (!seat) continue;
    const prev = last.get(seat);
    if (!prev || tsAfter(r.started, prev.started) || (!prev.started && r.started)) last.set(seat, r);
  }
  return last;
}

function laterSitting(rows, seat, afterEnded) {
  if (!afterEnded) return false;
  return rows.some((r) => (r.seat || '').trim() === seat && tsAfter(r.started, afterEnded));
}

function liveSeatsFromLedgers(rows) {
  const live = new Set();
  for (const r of rows) {
    const seat = (r.seat || '').trim();
    if (!seat) continue;
    if ((r.ended || '').trim()) continue;
    if (pidAlive(r.pid)) live.add(seat);
  }
  return live;
}

function checkinOf(lastRow) {
  const raw = lastRow && lastRow.checkin;
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

function leaderSeat(goalFolder) {
  try {
    const rows = readTaskforce(goalFolder);
    const seats = rows.map((r) => (r.seat || '').trim()).filter(Boolean);
    if (seats.includes('leader')) return 'leader';
    return seats[0] || 'leader';
  } catch {
    return 'leader';
  }
}

function queuedSeats(heartStore, goal) {
  const out = new Set();
  if (!heartStore || typeof heartStore.listQueue !== 'function') return out;
  for (const q of heartStore.listQueue()) {
    const id = String(q.job_id || '');
    const prefix = `seat-${goal}-`;
    if (id.startsWith(prefix)) out.add(id.slice(prefix.length));
    else if (id.startsWith('seat-') && !goal) out.add(id.slice(5));
  }
  return out;
}

function roomState(goal) {
  const session = String(goal);
  const has = spawnSync('tmux', ['has-session', '-t', `=${session}`], { encoding: 'utf8' });
  if (has.status !== 0) return { exists: false, empty: true };
  const panes = spawnSync('tmux', ['list-panes', '-s', '-t', `=${session}`, '-F', '#{pane_id}'], { encoding: 'utf8' });
  const list = (panes.stdout || '').split('\n').map((l) => l.trim()).filter(Boolean);
  return { exists: true, empty: list.length === 0 };
}

function deriveOwed(goalFolder, {
  readyAnswer = null,
  live = null,
  queued = null,
} = {}) {
  const sessions = loadSessions(goalFolder);
  const messages = loadMessages(goalFolder);
  const last = lastBySeat(sessions);
  const liveSet = live || liveSeatsFromLedgers(sessions);
  const queuedSet = queued || new Set();

  const dead = new Set();
  let readyRefused = null;
  let readyCount = 0;
  const pending = [];
  if (readyAnswer) {
    if (readyAnswer.reason && readyAnswer.ready === null) {
      readyRefused = readyAnswer.reason;
    } else {
      for (const r of readyAnswer.rows || []) {
        if (!r || !r.seat) continue;
        if (r.dead === true) { dead.add(r.seat); continue; }
        if (r.verdict === 'READY') readyCount += 1;
        else if (r.verdict && r.verdict !== 'DONE') pending.push(r.seat);
      }
    }
  }

  const classA = [];
  for (const [seat, row] of last) {
    if (dead.has(seat)) continue;
    const disp = (row.disposition || '').trim();
    if (!isNonTerminal(disp)) continue;
    const ended = (row.ended || '').trim();
    if (!ended) continue;
    if (laterSitting(sessions, seat, ended)) continue;
    const reason = String(row['incomplete-reason'] || row.reason || '');
    const outputsUnverified = disp === 'incomplete' && /outputs-unverified/.test(reason);
    classA.push({
      seat, disposition: disp, ended, outputsUnverified,
      reason: outputsUnverified ? 'outputs-unverified' : 'nonterm',
    });
  }

  const classB = [];
  for (const chair of STAFF_CHAIRS) {
    if (dead.has(chair)) continue;
    if (liveSet.has(chair) || queuedSet.has(chair)) continue;
    const cursor = checkinOf(last.get(chair));
    const unread = messages.filter((m) => m.to === chair && m.num > cursor && m.sender !== chair);
    if (!unread.length) continue;
    classB.push({
      seat: chair,
      unreadCount: unread.length,
      lastNum: unread[unread.length - 1].num,
      reason: 'unread',
    });
  }

  const moving = liveSet.size > 0 || queuedSet.size > 0;
  const classE = (!readyRefused && readyCount === 0 && pending.length && !moving)
    ? { pending: pending.slice().sort(), ready: 0 }
    : null;

  return {
    readyRefused,
    deadSeats: [...dead],
    classA,
    classB,
    classC: classA.filter((x) => x.outputsUnverified),
    classE,
    live: [...liveSet],
    queued: [...queuedSet],
    owed: classA.length > 0 || classB.length > 0,
  };
}

function getAttempt(store, goal, seat, reason) {
  if (store && typeof store.getReconcileAttempt === 'function') {
    return store.getReconcileAttempt(goal, seat, reason);
  }
  return null;
}

function putAttempt(store, rec) {
  if (store && typeof store.upsertReconcileAttempt === 'function') {
    store.upsertReconcileAttempt(rec);
  }
}

function clearAttempt(store, goal, seat, reason) {
  if (store && typeof store.clearReconcileAttempt === 'function') {
    store.clearReconcileAttempt(goal, seat, reason);
  }
}

function lastPassAt(store, goal) {
  if (store && typeof store.getReconcilePass === 'function') {
    const row = store.getReconcilePass(goal);
    return row && row.last_at ? row.last_at : null;
  }
  return null;
}

function setPassAt(store, goal, at) {
  if (store && typeof store.setReconcilePass === 'function') {
    store.setReconcilePass(goal, at);
  }
}

function sendStuck({ goalFolder, body, sendFn }) {
  if (typeof sendFn === 'function') return sendFn({ goalFolder, body });
  const out = execFileSync(requirePythonCmd(), [
    COORD_PY, '--package', goalFolder, '--as', 'ignite-daemon',
    'send', 'auto', body, '--type', 'stuck', '--inline',
  ], { encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'pipe'] });
  return { ok: true, out };
}

function recoverRoom({ goal, goalFolder, seat, recoverFn }) {
  if (typeof recoverFn === 'function') return recoverFn({ goal, goalFolder, seat });
  const r = spawnSync(requirePythonCmd(), [
    RECOVER_ROOM,
    '--session', goal,
    '--package', goalFolder,
    '--seat', seat,
    '--coord', COORD_PY,
  ], { encoding: 'utf8', timeout: 120000 });
  return { ok: r.status === 0, status: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

function launchSitting({
  heartStore, goal, goalFolder, seat, promptFn, say,
}) {
  const seatDir = path.join(goalFolder, 'seats', seat);
  if (!fs.existsSync(seatDir)) {
    return { ok: false, error: 'no-seat-folder', seat };
  }
  let uncast = [];
  try { uncast = uncastSeats(goalFolder); } catch { uncast = []; }
  if (uncast.includes(seat)) {
    return { ok: false, error: 'E_UNCAST_SEAT', seat };
  }
  const jobId = jobIdFor(seat, goal);
  if (heartStore && typeof heartStore.getJob === 'function' && !heartStore.getJob(jobId)) {
    heartStore.registerJob({
      jobId,
      actionType: 'launch-agent',
      function: `reconcile sitting ${seat}`,
      argsSchema: JSON.stringify({ required: {}, optional: { workdir: 'string', prompt: 'string' } }),
      description: `watcher launch of ${seat} on ${goal}`,
      createdAt: isoNow(),
      updatedAt: isoNow(),
    });
  }
  let prompt = null;
  if (typeof promptFn === 'function') {
    prompt = promptFn(goalFolder, seat);
  } else {
    const boot = seatBootPrompt(goalFolder, seat);
    prompt = boot.prompt;
    if (prompt === null) return { ok: false, error: boot.reason || 'no-boot-prompt', seat };
  }
  if (!prompt) return { ok: false, error: 'no-boot-prompt', seat };
  const enq = heartStore.enqueue({
    jobId,
    args: JSON.stringify({ workdir: seatDir, prompt }),
    sessionMode: 'headless',
    triggerKind: 'scheduled',
    runAt: isoNow(),
    enqueuedBy: 'goal-watcher',
    onSeatBusy: 'queue',
  });
  if (enq && enq.deduped) {
    if (say) say('warn', 'reconcile: enqueue returned deduped — sitting was NOT queued', {
      goal, seat, because: enq.because, queue_id: enq.queue_id, exec_id: enq.exec_id,
    });
    return { ok: false, error: 'deduped', enq, seat };
  }
  return { ok: true, enq, seat, jobId };
}

function strike({
  store, goal, seat, reason, signature, goalFolder, say, sendFn, engine, pickup, now,
}) {
  const prev = getAttempt(store, goal, seat, reason) || {
    attempts: 0, stuck_emitted: 0, signature: '',
  };
  const same = prev.signature === signature;
  const attempts = (same ? Number(prev.attempts) || 0 : 0) + 1;
  const stuckWas = same && Number(prev.stuck_emitted) ? 1 : 0;
  let stuckEmitted = stuckWas;
  let sent = null;
  if (attempts >= STRIKE_LIMIT && !stuckWas) {
    const body = `stuck: ${reason} on \`${seat}\` after ${attempts} mechanical attempts. signature=${signature}`;
    try {
      sent = sendStuck({ goalFolder, body, sendFn });
      stuckEmitted = 1;
      if (say) say('warn', 'reconcile: emitted stuck to the leader', { goal, seat, reason, attempts });
    } catch (err) {
      if (say) say('warn', 'reconcile: stuck send failed', { goal, seat, error: err && err.message });
    }
  }
  putAttempt(store, {
    goal, seat, reason, attempts, stuckEmitted, signature, updatedAt: isoNow(),
  });
  const pastOwner = stuckEmitted && attempts >= STRIKE_LIMIT + OWNER_AFTER_STUCK;
  const leaderIsSubject = seat === 'leader' || seat === 'goal-master';
  if ((leaderIsSubject && stuckEmitted) || pastOwner) {
    if (engine && say) {
      const { alarmOnStall } = require('./lane-watch');
      alarmOnStall({
        goal, goalFolder, engine, say,
        pickup: pickup || {
          frozen: {
            kind: 'reconcile-stuck',
            seats: [seat],
            detail: `${reason} still standing after ${attempts} attempts`,
          },
        },
      });
    }
  }
  return { attempts, stuckEmitted, sent, signature };
}

function reconcileGoal({
  goal, goalFolder, engine, say = () => {}, pickup = null,
  now = Date.now(), force = false, dryRun = false,
  cadenceMs = CADENCE_MS,
  readyAnswer: readyInjected = undefined,
  promptFn = undefined,
  sendFn = undefined,
  recoverFn = undefined,
  live = undefined,
}) {
  const heartStore = engine && engine.heartStore;
  const at = typeof now === 'number' ? new Date(now).toISOString().replace(/\.\d{3}Z$/, 'Z') : isoNow();
  if (!force && heartStore) {
    const prev = lastPassAt(heartStore, goal);
    if (prev) {
      const prevMs = Date.parse(prev);
      if (Number.isFinite(prevMs) && (now - prevMs) < cadenceMs) {
        return { skipped: 'cadence', goal, lastAt: prev };
      }
    }
  }

  // Honour `rbtv goal pause`. ONE reader: lane-watch.laneIsPaused (DEC-1 twin of
  // goal_cli.lane_is_paused). Lazy-require — lane-watch requires this module at
  // top level; a cycle at load would leave the reader undefined.
  const { laneIsPaused } = require('./lane-watch');
  if (goalFolder && laneIsPaused(goalFolder)) {
    if (!dryRun && heartStore) setPassAt(heartStore, goal, at);
    if (say) say('info', 'reconcile: skipped — goal is paused', { goal });
    return { skipped: 'paused', goal };
  }

  let readyAnswer = readyInjected;
  if (readyAnswer === undefined) {
    readyAnswer = readySeats(goalFolder);
  }

  const queued = queuedSeats(heartStore, goal);
  const derived = deriveOwed(goalFolder, { readyAnswer, live, queued });
  const leader = leaderSeat(goalFolder);

  const actions = [];
  if (!dryRun && heartStore) setPassAt(heartStore, goal, at);

  if (say) {
    say('info', 'reconcile: pass', {
      goal,
      classA: derived.classA.map((x) => x.seat),
      classB: derived.classB.map((x) => x.seat),
      classC: derived.classC.map((x) => x.seat),
      classE: derived.classE ? derived.classE.pending : null,
      readyRefused: derived.readyRefused,
      deadExcluded: derived.deadSeats.length,
      leader,
      dryRun: Boolean(dryRun),
    });
  }

  if (dryRun) {
    return { goal, derived, actions, leader, dryRun: true };
  }

  if (derived.readyRefused) {
    actions.push({ kind: 'detect', why: 'ready-seats-refused', detail: derived.readyRefused });
  }
  if (derived.classE) {
    actions.push({ kind: 'detect', why: 'frozen-frontier', seats: derived.classE.pending });
  }

  const launchTargets = [];
  if (derived.classA.length) {
    launchTargets.push({
      seat: leader,
      reason: 'nonterm',
      signature: `nonterm:${derived.classA.map((x) => x.seat).sort().join(',')}`,
      source: 'a',
    });
  }
  for (const item of derived.classB) {
    launchTargets.push({
      seat: item.seat,
      reason: 'unread',
      signature: `unread:${item.seat}:${item.lastNum}`,
      source: 'b',
    });
  }

  const liveSet = new Set(derived.live);
  const seenTarget = new Set();
  for (const t of launchTargets) {
    if (seenTarget.has(t.seat)) continue;
    seenTarget.add(t.seat);
    if (liveSet.has(t.seat) || queued.has(t.seat)) {
      clearAttempt(heartStore, goal, t.seat, t.reason);
      actions.push({ kind: 'skip-live-or-queued', seat: t.seat, reason: t.reason });
      continue;
    }
    const launched = launchSitting({
      heartStore, goal, goalFolder, seat: t.seat, promptFn, say,
    });
    if (launched.ok) {
      clearAttempt(heartStore, goal, t.seat, t.reason);
      actions.push({ kind: 'enqueue', seat: t.seat, reason: t.reason, enq: launched.enq, jobId: launched.jobId });
    } else {
      const struck = strike({
        store: heartStore, goal, seat: t.seat, reason: t.reason,
        signature: t.signature, goalFolder, say, sendFn, engine, pickup, now,
      });
      actions.push({
        kind: 'launch-refused', seat: t.seat, reason: t.reason,
        error: launched.error, attempts: struck.attempts, stuckEmitted: struck.stuckEmitted,
      });
    }
  }

  if (derived.owed) {
    const room = roomState(goal);
    if (!room.exists || room.empty) {
      const recSeat = leader;
      const rec = recoverRoom({ goal, goalFolder, seat: recSeat, recoverFn });
      if (rec.ok) {
        clearAttempt(heartStore, goal, recSeat, 'room');
        actions.push({ kind: 'room-rebuilt', seat: recSeat });
      } else {
        const struck = strike({
          store: heartStore, goal, seat: recSeat, reason: 'room',
          signature: `room:${room.exists ? 'empty' : 'dead'}`,
          goalFolder, say, sendFn, engine, pickup, now,
        });
        actions.push({
          kind: 'room-refused', error: rec.out || rec.status,
          attempts: struck.attempts, stuckEmitted: struck.stuckEmitted,
        });
      }
    }
  }

  if (!derived.owed) {
    clearAttempt(heartStore, goal, leader, 'nonterm');
    clearAttempt(heartStore, goal, leader, 'room');
    for (const chair of STAFF_CHAIRS) clearAttempt(heartStore, goal, chair, 'unread');
  }

  return { goal, derived, actions, leader };
}

function maybeReconcile(args) {
  try {
    return reconcileGoal(args);
  } catch (err) {
    if (args.say) {
      args.say('warn', 'reconcile: pass threw — the tick continues', {
        goal: args.goal, error: err && err.message,
      });
    }
    return { error: err && err.message, goal: args.goal };
  }
}

module.exports = {
  CADENCE_MS,
  STRIKE_LIMIT,
  RECORD_DISPOSITIONS,
  NON_TERMINAL_DISPOSITIONS,
  STAFF_CHAIRS,
  deriveOwed,
  reconcileGoal,
  maybeReconcile,
  launchSitting,
  loadSessions,
  loadMessages,
  isNonTerminal,
};
