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
// ⚠ SUMMONED SEATS ARE NEVER OWED (D24). See `summonedSeats` below.
// ⚠ GRANTS ARE NOT TOUCHED. Launch is heartStore.enqueue({ onSeatBusy: 'queue' }).
//    delete-grants has nothing to remove here.
// ⚠ CLASS A SPLITS BY WORD (D33a). `incomplete` is SEAT-written and means one thing — the seat
//   said unfinished — so the watcher relaunches THAT seat by name. `unverified` (checkout's D5
//   refusal, D32), `exited` and an empty cell are nobody's to close but the leader's: ONE leader
//   wake per pass, carrying a payload that NAMES the rows and the act that closes them. The old
//   class (c) parsed a per-row reason column `sessions.csv` never had, so it never fired — deleted.
// ⚠ THE STRIKE COUNTER MEASURES NO PROGRESS, NEVER LAUNCH SUCCESS (D34). A pass whose owed
//   signature is unchanged is one attempt, however well the launch went; the count clears only
//   when that signature changes or the (seat, reason) drops out of the owed set.

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
const STRIKE_LIMIT = 2; // D34 (was 3), and counted on NO PROGRESS — see `strike` below.
const OWNER_AFTER_STUCK = 3;

const RECORD_DISPOSITIONS = Object.freeze(
  ['done', 'renew', 'revive', 'exited', 'incomplete', 'unverified'],
);
const TERMINAL_DISPOSITIONS = Object.freeze(['done']);
const NON_TERMINAL_DISPOSITIONS = Object.freeze(
  RECORD_DISPOSITIONS.filter((d) => !TERMINAL_DISPOSITIONS.includes(d)),
);
// `renew-interrupted` is never a literal `disposition` cell coord.py writes — it is this
// module's OWN synthetic label for a renew marker whose successor session never showed up. It
// stays in its own list, separate from RECORD_DISPOSITIONS (coord.py's real recorded enum).
const EXTRA_NON_TERMINAL = Object.freeze(['renew-interrupted']);
const STAFF_CHAIRS = Object.freeze(['leader', 'consultant', 'goal-master']);

// D24 · A SUMMONED SEAT IS NEVER OWED. It is spawned ONLY when the owner summons it (a
// goal-channel message or an `@rbtv` bot tag) — mail is NOT a wake term for it. Without this
// guard reconcile derived class (b) from the chair's unread mail and relaunched meet's
// `goal-master` on every cadence (jobs_log exec 30020/30026/30036/30042/30049/30056,
// 2026-08-20), and the phantom sitting then registered as a live holder for the owner's post.
//
// ⚠ THE LIST IS COORD'S, READ OFF COORD. Hardcoding `goal-master` here would mint the second
// list this program exists to remove. `ready-seats --json` cannot answer it: coord's D24
// `IDLE` branch sits BELOW the disposition branch, so a chair that has checked out reads
// `verdict: DONE` and carries no summoned term at all (measured on meet, 2026-08-20) — which
// is precisely the state reconcile mis-derives.
// ⚠ DEGRADATION IS TOWARD THE OLD BEHAVIOUR, NEVER A SILENT HOLE: an older coord with no such
// tuple, or a read that fails, yields the EMPTY set — every seat stays owed exactly as before
// this guard, and the miss is logged. Cached for the process: coord.py cannot change under a
// running daemon without a deploy, and a deploy restarts it.
const SUMMONED_PY = [
  'import importlib.util, json, sys',
  'spec = importlib.util.spec_from_file_location("coord_summoned", sys.argv[1])',
  'm = importlib.util.module_from_spec(spec)',
  'spec.loader.exec_module(m)',
  'print(json.dumps(list(getattr(m, "SUMMONED_SEATS", []))))',
].join('\n');

let SUMMONED_CACHE = null;

function summonedSeats(say) {
  if (SUMMONED_CACHE) return SUMMONED_CACHE;
  let names = [];
  try {
    const r = spawnSync(requirePythonCmd(), ['-c', SUMMONED_PY, COORD_PY], {
      encoding: 'utf8', timeout: 30000,
    });
    if (r.status === 0) {
      const parsed = JSON.parse(r.stdout);
      if (Array.isArray(parsed)) names = parsed.map(String).filter(Boolean);
    }
  } catch {
    names = [];
  }
  if (!names.length && say) {
    say('warn', 'reconcile: coord names no SUMMONED_SEATS — the D24 exclusion is OFF', {});
  }
  SUMMONED_CACHE = new Set(names);
  return SUMMONED_CACHE;
}

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

// ⚠ NO SUPERSEDED-BY-A-LATER-SITTING CHECK, AND NEVER AGAIN (F-1). `lastBySeat` already
// returns the row with the MAXIMUM `started`, so by construction no later sitting of that seat
// can exist — the old `laterSitting(sessions, seat, row.ended)` guard could only ever match the
// row against ITSELF. And it did: coord writes `started` at second precision
// (`2026-08-20T05:38:40Z`) and `ended` at minute precision (`2026-08-20 05:38`), so the string
// compare in `tsAfter` read a row's own `started` as AFTER its own `ended` whenever the sitting
// fit inside one minute. Three meet rows (plan-3-plan-check-{consistency,edges,resources},
// sat 2026-08-20 05:38-05:40) were invisible to the watcher, and a stools seat that gave up in
// under 60 s dropped out of class (a) and swept its own strike counter.
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

// D35 · A CHAIR'S UNREAD MAIL IS WHAT WAS RECORDED AFTER ITS LAST CHECK-IN. `checkin` is a
// TIMESTAMP column (coord `SESSIONS_COLS`); the old `Number()` here made it NaN → cursor 0 →
// every message the chair ever received read "unread" forever (238 on meet, 72 on stools), and
// class (b) fired on every pass. Fallback `started`; a chair with NO row at all — or a row
// carrying neither stamp — is owed ALL its mail, which is the pre-D35 behaviour, not a hole.
function checkinOf(lastRow) {
  if (!lastRow) return '';
  const ci = String(lastRow.checkin || '').trim();
  return ci || String(lastRow.started || '').trim();
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
  summoned = null,
} = {}) {
  const sessions = loadSessions(goalFolder);
  const messages = loadMessages(goalFolder);
  const last = lastBySeat(sessions);
  const liveSet = live || liveSeatsFromLedgers(sessions);
  const queuedSet = queued || new Set();
  const summonedSet = summoned || new Set();

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
    if (summonedSet.has(seat)) continue;
    const disp = (row.disposition || '').trim();
    if (!isNonTerminal(disp)) continue;
    const ended = (row.ended || '').trim();
    if (!ended) continue;
    // D42 · A RULED HOLD IS SKIPPED, AND IT IS THE ONLY THING THE HOLD CHANGES.
    // `meet/issues.md#G-leader-0820-1748`, filed by the live leader: a row the leader had
    // INVESTIGATED and deliberately held was byte-identical to an unattended owed one, because
    // the disposition cell must keep its value for `ready-seats` to keep blocking the successors
    // — and this scan reads only that cell. So the leader was re-woken every cadence, forever,
    // with identical output (17:37/17:43/17:48, measured).
    //
    // ⚠ THE SKIP IS THE WATCHER'S ALONE. `ready-seats` still reports the row's real class, the
    // row still blocks its successors and it is still rulable at any time. Nothing here advances
    // an edge and nothing reads this cell as authorization: it is an ANCHOR STRING written by
    // `coord.py rule-disposition --hold` and released by the next real ruling on the same row.
    // Not a grant, not a latch, no expiry, nothing to spend (D12 intact).
    if ((row['hold-anchor'] || '').trim()) continue;
    // D33(a) · the word IS the split. `incomplete` → that seat, by name. Everything else
    // non-terminal → the leader, who is the only actor with a verb for it.
    classA.push({
      seat, disposition: disp, ended,
      reason: disp === 'incomplete' ? 'incomplete' : 'nonterm',
    });
  }
  classA.sort((x, y) => (x.seat < y.seat ? -1 : x.seat > y.seat ? 1 : 0));

  const classB = [];
  for (const chair of STAFF_CHAIRS) {
    if (dead.has(chair)) continue;
    if (summonedSet.has(chair)) continue;
    if (liveSet.has(chair) || queuedSet.has(chair)) continue;
    const since = checkinOf(last.get(chair));
    const unread = messages.filter((m) => m.to === chair && m.sender !== chair
      && (!since || tsAfter(m.ts, since)));
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
    summonedSeats: [...summonedSet],
    classA,
    classB,
    classE,
    seats: [...last.keys()],
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

// D33(a) · THE LEADER IS NEVER WOKEN BLIND. Until now class (a) produced ONE target — the
// leader, launched on its plain boot prompt, with nothing naming what it had been woken FOR
// (144/144 passes on both live goals). The boot prompt stays FIRST and UNCHANGED — if it cannot
// be built the launch fails exactly as it did before, and nothing is invented in its place —
// and this block is APPENDED after it.
function nontermPayload(rows) {
  return [
    '',
    '',
    '---',
    '',
    `## The watcher woke you for ${rows.length} owed session-log row(s)`,
    '',
    ...rows.map((r) => `- \`${r.seat}\` — last row \`${r.disposition || '(empty)'}\`, ended ${r.ended}`),
    '',
    'Each of those rows ended with an ending nothing can advance on, and no seat can close',
    'its own. You are the only actor with a verb for them (D33b):',
    '',
    '    rule-disposition <seat> done --anchor <p-*/d-* or message ref> --go',
    '    rule-disposition <seat> "" --anchor <p-*/d-* or message ref> --go   # CLEAR the row',
    '',
    'A `done` ruling\'s anchor must quote the on-disk evidence. Rule them or this wake repeats.',
    '',
    'If a row must simply WAIT — you investigated it and ruled that it stays as it is — HOLD it',
    'and this wake stops repeating on it (D42). The cell keeps its value, the row keeps blocking',
    'its successors, and the next real ruling releases the hold in the same act:',
    '',
    '    rule-disposition <seat> --hold --anchor <p-*/d-* or message ref> --go',
    '',
    'A CRASHED SEAT IS RE-RUN IN ONE ACT (D42). A row reading `exited` is the KIT saying the',
    'harness TERMINATED and the work is UNKNOWN — never that it finished. Do NOT clear it first:',
    'the CLEAR destroys the `exited` word, which is the only record of how that session ended.',
    'This opens an ORDINARY WORKING SESSION and leaves the row standing to be superseded:',
    '',
    '    launch --only <seat> --rerun <p-*/d-* or message ref>',
    '',
    'CLEARING IS NOT A RELAUNCH — they are TWO acts (D39), and it is the CLEARED row\'s path, not',
    'the crashed one\'s. A cleared row reads UNDECLARED, the daemon maps that to not-waitable, and',
    'NEVER re-seeds it. To bring a cleared seat back you must then issue the second command',
    'yourself — a session that DECLARES the ending:',
    '',
    '    launch --only <seat> --declare-only <p-*/d-* or message ref>',
    '',
    'Clear without that second command and the seat simply sits there.',
    '',
  ].join('\n');
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

// D44 (owner ruling, 2026-08-20) — `stuck` IS A BRAKE, NOT ONLY A REPORT.
//
// ⚠ THIS CHANGES A SPEC BY OWNER RULING, and that is recorded here rather than glossed: the
// report-only behaviour was BUILT AS SPECIFIED — `seats/resolve-watcher/seat.md:39` says in so
// many words "A successful launch records the attempt; it does not clear it", and `strike` below
// was written to record and escalate, never to gate. D44 supersedes that line. The gap it closes
// is between D34/D40's prose ("bounded", "then typed `stuck` to the leader") and a low-level spec
// that never gated the launch on `attempts`: measured on the live goal, `audio-component-smith`
// was launched 17 times in 2h12m, one full `claude-opus-5` boot per ~5 min, on a row whose only
// blocker was an unanswered owner escalation. Once `stuck` has been emitted the row is the
// LEADER's, and the leader can relaunch it.
//
// KEYED ON THE SIGNATURE, which is what keeps D34/D40 intact: a CHANGED owed-set signature is
// PROGRESS, so this predicate goes false, `strike` resets the counter to 1, and launching
// re-arms in the same pass. Only a stuck-and-unchanged row is braked.
function stuckStands(store, goal, seat, reason, signature) {
  const prev = getAttempt(store, goal, seat, reason);
  return !!(prev && prev.signature === signature && Number(prev.stuck_emitted));
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
  const derived = deriveOwed(goalFolder, {
    readyAnswer, live, queued, summoned: summonedSeats(say),
  });
  const leader = leaderSeat(goalFolder);

  const actions = [];
  if (!dryRun && heartStore) setPassAt(heartStore, goal, at);

  if (say) {
    say('info', 'reconcile: pass', {
      goal,
      classA: derived.classA.map((x) => x.seat),
      classB: derived.classB.map((x) => x.seat),
      classE: derived.classE ? derived.classE.pending : null,
      readyRefused: derived.readyRefused,
      deadExcluded: derived.deadSeats.length,
      summonedExcluded: derived.summonedSeats,
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
  // D33(a) · `incomplete` is the seat's own word for "unfinished" — relaunch THAT seat, by name.
  for (const item of derived.classA.filter((x) => x.reason === 'incomplete')) {
    launchTargets.push({
      seat: item.seat,
      reason: 'incomplete',
      // D40 · NO `:${item.ended}`. `ended` advances on every re-checkout, so an identical
      // give-up read as new work and the attempt counter reset to 1 — D34's bound never fired.
      signature: `incomplete:${item.seat}`,
      source: 'a',
    });
  }
  // The rest is the leader's judgment, in ONE wake that NAMES the rows. The signature is the
  // owed CONTENT, so a ruling that removes or changes a row IS progress (D34).
  const nonterm = derived.classA.filter((x) => x.reason !== 'incomplete');
  if (nonterm.length) {
    launchTargets.push({
      seat: leader,
      reason: 'nonterm',
      signature: `nonterm:${nonterm.map((x) => `${x.seat}=${x.disposition}`).sort().join(',')}`,
      source: 'a',
      promptFn: (gf, seat) => {
        const head = promptFn ? promptFn(gf, seat) : seatBootPrompt(gf, seat).prompt;
        return (head === null || head === undefined) ? null : head + nontermPayload(nonterm);
      },
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
  // Every (seat, reason) this pass still owes. Anything absent from it is progress, and the
  // end-of-pass sweep clears it (D34).
  const owedKeys = new Set();
  for (const t of launchTargets) {
    owedKeys.add(`${t.seat}\u0000${t.reason}`);
    let action;
    if (seenTarget.has(t.seat)) {
      // One launch per seat per pass; the OTHER reason still counts its own attempt.
      action = { kind: 'skip-already-targeted', seat: t.seat, reason: t.reason };
    } else if (liveSet.has(t.seat) || queued.has(t.seat)) {
      seenTarget.add(t.seat);
      action = { kind: 'skip-live-or-queued', seat: t.seat, reason: t.reason };
    } else if (stuckStands(heartStore, goal, t.seat, t.reason, t.signature)) {
      // D44 · the BRAKE. `stuck` already went to the leader for this exact (seat, reason,
      // signature) — the mechanical relaunch stops here and the row is the leader's. `strike`
      // still runs below, so the counter keeps advancing and the owner-alarm leg
      // (STRIKE_LIMIT + OWNER_AFTER_STUCK) is untouched; what stops is the SPEND.
      seenTarget.add(t.seat);
      action = { kind: 'skip-stuck', seat: t.seat, reason: t.reason };
    } else {
      seenTarget.add(t.seat);
      const launched = launchSitting({
        heartStore, goal, goalFolder, seat: t.seat, promptFn: t.promptFn || promptFn, say,
      });
      action = launched.ok
        ? { kind: 'enqueue', seat: t.seat, reason: t.reason, enq: launched.enq, jobId: launched.jobId }
        : { kind: 'launch-refused', seat: t.seat, reason: t.reason, error: launched.error };
    }
    // D34 · THE ATTEMPT IS THE PASS, NOT THE LAUNCH. `clearAttempt` used to fire right here on
    // `launched.ok`, so a wake that enqueued cleanly reset the counter every pass and the loop
    // was unbounded (`reconcile_attempts` empty after hundreds of passes on both live goals).
    // `strike` resets to 1 by itself when the signature differs — that IS the progress test.
    const struck = strike({
      store: heartStore, goal, seat: t.seat, reason: t.reason,
      signature: t.signature, goalFolder, say, sendFn, engine, pickup, now,
    });
    action.attempts = struck.attempts;
    action.stuckEmitted = struck.stuckEmitted;
    actions.push(action);
  }

  if (derived.owed) {
    const room = roomState(goal);
    if (!room.exists || room.empty) {
      const recSeat = leader;
      const rec = recoverRoom({ goal, goalFolder, seat: recSeat, recoverFn });
      if (rec.ok) {
        actions.push({ kind: 'room-rebuilt', seat: recSeat });
      } else {
        owedKeys.add(`${recSeat}\u0000room`);
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

  // D34 · the counter clears when the owed set changes or empties, and nowhere else. Sweeping
  // by (every seat this goal has ever seated) × (this module's four reasons) needs no new store
  // method and no new column; a DELETE of an absent row costs nothing. When nothing is owed
  // there are no keys, so every row goes — which is the old `!derived.owed` block, generalised.
  const sweepSeats = new Set([...derived.seats, ...STAFF_CHAIRS, leader]);
  for (const seat of sweepSeats) {
    for (const reason of ['incomplete', 'nonterm', 'unread', 'room']) {
      if (owedKeys.has(`${seat}\u0000${reason}`)) continue;
      clearAttempt(heartStore, goal, seat, reason);
    }
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
  summonedSeats,
  reconcileGoal,
  maybeReconcile,
  launchSitting,
  loadSessions,
  loadMessages,
  isNonTerminal,
};
