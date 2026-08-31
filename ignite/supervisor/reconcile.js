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
// ⚠ SUMMONED SEATS ARE NEVER OWED AND ARE NEVER SEEDED (D24). The one reader of coord's list is
// `seeding.js#summonedSeats`, imported below.
// ⚠ GRANTS ARE NOT TOUCHED. Launch goes through the supervisor's wrapped spawn door
//    (`launchThroughDoor`, `onSeatBusy: 'queue'`) — never this file's own enqueue [§5].
//    delete-grants has nothing to remove here.
// ⚠ CLASS A SPLITS BY WORD (D33a). `incomplete` is SEAT-written and means one thing — the seat
//   said unfinished — so the watcher relaunches THAT seat by name. `unverified` (checkout's D5
//   refusal, D32), `exited` and an empty cell are nobody's to close but the leader's: ONE leader
//   wake per pass, carrying a payload that NAMES the rows and the act that closes them. The old
//   class (c) parsed a per-row reason column `sessions.csv` never had, so it never fired — deleted.
// ⚠ THE ATTEMPT COUNTER MEASURES A RETRY, NEVER LAUNCH SUCCESS. A pass is one attempt however
//   well the launch went, and the count CLEARS ONLY ON A NAMED RE-ARM EVENT [spec-recovery §5] -
//   never on a launch outcome, never on evidence drift. (The line that used to stand here promised
//   a clear "when the signature changes"; that reset is the deleted brake and is gone.) A pass
//   whose owed ITEMS are all new does not ADD to the count either - it is a first attempt at
//   different work - and that is a decline to increment, never a reset. See `announceDisarm` and
//   the owed-item marker in `attempt-counters.js`.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync, spawnSync } = require('node:child_process');
const { requirePythonCmd } = require('../runtime/python-cmd');
const {
  readySeats, summonedSeats, readCsv, jobIdFor, uncastSeats, seatBootPrompt, readTaskforce, seatCast,
} = require('./seeding');
// ── THE ONE OWED-WORK COMPUTER AND THE ONE ENQUEUE [spec-supervisor §5, T4-R7, C-15] ──────────
// `deriveOwed` is the SURVIVOR of the two owed-work computers. It lives at the supervisor home
// because the owed set is supervisor-owned, and this file now ASKS it rather than being it.
// `launchThroughDoor` is the single `heartStore.enqueue` on the owed path — the watcher no longer
// has one of its own.
const { deriveOwed } = require('./owed');
const { finishEvent } = require('./owed-from-endings');
const { launchThroughDoor } = require('./launch-door');
const { DOORS } = require('./doors');
// ── THE PROVIDER-CLASSIFICATION HOOKUP [spec-recovery §3, T1-R13, C-10] ───────────────────────
// The ONLY thing this file knows about provider faults is which api to ask. What an error text
// MEANS is `supervisor/provider-classify.js` (two owner-editable lists), and what each meaning
// DOES to the lane is `supervisor/provider-lanes.js`. Deliberately kept out of the counter
// internals above: a recognition-list edit must never have to reach inside the counting.
const providerLanes = require('./provider-lanes');
// ── THE ATTEMPT COUNTER REPLACES THE BYTE-EQUALITY BRAKE [spec-recovery §5, T4-R3, C-2] ───────
// `strike`/`stuckStands` and their shared bound (`heart-store.js`'s `ADMISSION_BRAKE_LIMIT`) are
// DELETED. Both compared an owed-content signature byte for byte, and both reset on a volatile
// field, so neither bound ever fired. What counts a retry now is the driver-agnostic counter at
// the supervisor home; what N is comes from the recovery config file, never from a literal here.
const counters = require('./attempt-counters');
const { exhaust, recordGroupedAsk } = require('./exhaustion');
const relaunchBudget = require('./relaunch-budget');
const checkpoint = require('./checkpoint');
const { loadRecoveryConfig } = require('./recovery-config');

const COORD_PY = path.join(__dirname, '..', 'coord', 'coord.py');
const RECOVER_ROOM = path.join(__dirname, '..', 'runtime', 'jobs', 'recover-room.py');

const CADENCE_MS = 5 * 60 * 1000;
// D70 (2026-08-22) — the ONE system sender that ever writes to a goal's messages.md
// (`supervisor/seeding.js`'s surface-refusal; the watcher's own `sendStuck` is deleted with the brake
// it escalated for). System-written mail must never count
// as progress for the mail-cursor signal (class B) — see `deriveOwed`'s classB loop.
const SYSTEM_MAIL_SENDER = 'ignite-daemon';

const STAFF_CHAIRS = Object.freeze(['leader', 'goal-master']);

// D24 · A SUMMONED SEAT IS NEVER OWED. It is spawned ONLY when the owner summons it (a
// goal-channel message or an `@rbtv` bot tag) — mail is NOT a wake term for it. Without this
// guard reconcile derived class (b) from the chair's unread mail and relaunched meet's
// `goal-master` on every cadence (jobs_log exec 30020/30026/30036/30042/30049/30056,
// 2026-08-20), and the phantom sitting then registered as a live holder for the owner's post.
//
// ⚠ THE READER MOVED TO `seeding.js` (2026-08-27) AND IS IMPORTED, NEVER RE-IMPLEMENTED. The
// same coord tuple now also excludes a summoned chair from the SEEDING frontier, and two readers
// of one list is the state D24's own note forbids. Everything the reader guarantees — coord is
// the source, a failed read degrades to the EMPTY set and logs, cached for the process — is
// stated at its definition there.

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

// ── THE LEADER CHAIR IS A TASKFORCE ROW, OR THERE IS NO LEADER [B16] ──────────────────────────
//
// WHAT WAS HERE, and it is the defect: `if (seats.includes('leader')) return 'leader'; return
// seats[0] || 'leader';`. A goal whose taskforce carries no `leader` row got its FIRST row back
// instead, and every consumer in this file then treated an ordinary worker as the chair — the
// watcher printed `"leader":"distill-ignite-memory"` on `goal-memory-management` on every pass
// (the worker itself), woke it for judgment calls that are not its to make, and named it as the
// seat the room is rebuilt under. The `catch` arm was worse: an UNREADABLE taskforce produced the
// literal name `leader`, i.e. a chair asserted from a file nobody could read.
//
// THE CONTRACT the fallback broke: `taskforce.csv` IS the register of who holds which chair
// (`seeding.js#readTaskforce` validates it at load, and `materialize-seats.py`'s staffing pass is
// the only writer of a `leader` row). A goal with no such row has no leader — that is a STAFFING
// state, and substituting a seat for it is the daemon inventing an answer the register does not
// hold. So this fails CLOSED: no row, no leader, and the reason travels with the answer so the
// caller can name it in the journal instead of silently promoting somebody.
//
// The BACKFILL that repairs it already exists and is not this file's — `materialize-seats.py`
// mints the missing chairs on the next materialize that touches the goal.
const LEADER_CHAIR = 'leader';

// { seat: 'leader' } when the chair is genuinely staffed; { seat: null, why, detail } otherwise.
// Never a substitute.
function leaderSeat(goalFolder) {
  try {
    const rows = readTaskforce(goalFolder);
    const seats = rows.map((r) => (r.seat || '').trim()).filter(Boolean);
    if (seats.includes(LEADER_CHAIR)) return { seat: LEADER_CHAIR };
    return {
      seat: null,
      why: 'no-leader-row',
      detail: `this goal's taskforce.csv carries no \`${LEADER_CHAIR}\` row (rows: ${seats.join(', ') || 'none'})`,
    };
  } catch (err) {
    return {
      seat: null,
      why: 'taskforce-unreadable',
      detail: (err && err.message) || String(err),
    };
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

// The watcher's half of the ONE owed computer: class A (a seat whose last ending is non-terminal)
// and class B (a chair with unread mail). It hands in the ledger readers and reads no other half —
// the graph half [T1-R3] is the same function's class R, asked for by the seeding cadence. Two
// callers of one computer is the design; two computers is the defect [spec-supervisor §5].
function owedFromLedgers(goalFolder, opts = {}) {
  return deriveOwed(goalFolder, {
    ...opts,
    ledger: {
      loadSessions,
      loadMessages,
      lastBySeat,
      liveSeatsFromLedgers,
      checkinOf,
      tsAfter,
      STAFF_CHAIRS,
      SYSTEM_MAIL_SENDER,
    },
  });
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
    ...rows.map((r) => `- \`${r.seat}\` — last ending \`${r.ending || '(none)'}\`, ended ${r.ended}`),
    '',
    'Each of those rows ended with an ending nothing can advance on, and no seat can close',
    'its own. Rule it: `supervise accept <seat> --anchor <ref> --go` where the work in fact',
    'concluded, `supervise instruct <seat> <kind> --go` where it did not, or',
    '`supervise hold <seat> --until <new-ending|ask-answered:<ask-id>|release> --anchor <ref> --go`',
    'where the row genuinely cannot be ruled yet and you are waiting on a NAMED change. All three',
    'are honoured by this pass; a HOLD stops the wake and stops the attempt counter until the',
    'change you named happens, and `supervise release <seat> --go` ends it early. (`rule-disposition`,',
    'the verb that used to record a ruling or a HOLD on a `sessions.csv` cell, was deleted',
    '[T2-R12, T1-R9]; none of these is its return — they write the ENDING STORE.) This wake will',
    'keep repeating on these rows until one of the three is used. A verdict posted only as a',
    'message is NOT one of them: this pass reads rows, never mail.',
    '',
    'A CRASHED SEAT IS RE-RUN IN ONE ACT (D42). A `failed` ending with reason_class crash is the',
    'system saying the harness TERMINATED and the work is UNKNOWN — never that it finished.',
    'Do NOT invent a kit close. This opens an ORDINARY WORKING SESSION:',
    '',
    '    launch --only <seat> --rerun <p-*/d-* or message ref>',
    '',
    'CLEARING IS NOT A RELAUNCH — they are TWO acts (D39). Absence of a current ending is not a',
    'stored word. To bring a seat back you must issue a session that DECLARES the ending:',
    '',
    '    launch --only <seat> --declare-only <p-*/d-* or message ref>',
    '',
    'Clear without that second command and the seat simply sits there.',
    '',
  ].join('\n');
}

function launchSitting({
  heartStore, goal, goalFolder, seat, promptFn, say, reason, signature,
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
  // ── THE ONE ENQUEUE ON THE OWED PATH [spec-supervisor §5, T4-R7] ────────────────────────────
  // `deriveOwed` must not `heartStore.enqueue` on its own, and neither may its caller: BOTH owed
  // computers used to enqueue independently, which is the second launch path the unification
  // removes. This goes through the wrapped spawn door, which is the only remaining one.
  //
  // `enqueuedBy` is read off the supervisor's door list rather than spelled here: that string is
  // what turns back into the door name at the pid moment (`doors.js#doorForLauncher`), so a second
  // spelling of it is a reconcile launch that silently registers UNSUPERVISED.
  //
  // D52/D66 — `reason` and `progressSignature` are the watcher's already-derived values, threaded
  // as first-class request fields (never as an unregistered `args` key — `validateArgs` refuses
  // those). They are what the admission brake inside `enqueue()` counts on.
  const launched = launchThroughDoor({
    heartStore,
    seat,
    goal,
    jobId,
    args: JSON.stringify({ workdir: seatDir, prompt }),
    runAt: isoNow(),
    enqueuedBy: DOORS.reconcile.launcher,
    onSeatBusy: 'queue',
    reason,
    progressSignature: signature,
  });
  const enq = launched.enq;
  if (launched.refused) {
    // The door's refusal, surfaced exactly as it was when this function read the enqueue result
    // itself. The admission brake that used to add a second refusal here is deleted
    // [spec-recovery §5] — the bound is the attempt counter below, applied by this driver.
    if (say) {
      say('warn', 'reconcile: enqueue returned deduped — sitting was NOT queued', {
        goal, seat, evidence: launched.evidence,
      });
    }
    return { ok: false, error: launched.kind || 'deduped', enq, seat };
  }
  return { ok: true, enq, seat, jobId };
}

// ── THE ATTEMPT COUNTER, AT THE WATCHER [spec-recovery §5, T4-R3, C-2, D-2-ruling] ────────────
//
// WHAT WAS HERE. `strike()` counted a retry only while the owed-set SIGNATURE stayed byte-
// identical, and `stuckStands()` braked only a stuck-and-unchanged row. The signature carried
// volatile content, so a drifting field read as PROGRESS, reset the count to 1, and the bound
// D34/D44 promised never fired — the relaunch loop had no exit an owner could see. Both are
// deleted [C-4 kill map], together with the second lock the same bytes drove at the enqueue door.
//
// WHAT COUNTS NOW. The retry's REASON CLASS — `incomplete`, `nonterm`, `unread`, `room` — and
// nothing else. Same class on the next pass is the same retry, whatever moved in the ledgers. The
// counter is reset by exactly four named events (`supervisor/attempt-counters.js#RE_ARM_EVENTS`)
// and by no evidence at all, which is the whole correction.
//
// ⚠ THE COUNTER INTERNALS ARE SELF-CONTAINED IN THESE THREE FUNCTIONS. The provider-classification
// hookup lands elsewhere in this file on purpose: a classification edit must never have to reach
// inside the counting.

// Class A `incomplete` is its own spec-§5 driver row (the recovery relaunch of a named seat); the
// leader wake, the unread wake and the room rebuild are the cadence wake / sitting re-spawn row.
function driverFor(reason) {
  return reason === 'incomplete'
    ? counters.DRIVERS.RECONCILE_CLASS_A
    : counters.DRIVERS.RECONCILE_RESPAWN;
}

// N is the config file's, resolved once per pass. A pass that cannot read the file APPLIES NO
// RECOVERY CLOCK and says so [spec-recovery §2.1] — it does not fall back to a number in code,
// because a silent fallback is an instance running on knobs nobody can see or tweak.
function recoveryNumbers({ recovery, workspaceRoot, say, goal }) {
  if (recovery) return recovery;
  try {
    return loadRecoveryConfig({ workspace: workspaceRoot });
  } catch (err) {
    if (say) {
      say('warn', 'reconcile: recovery config unreadable — attempt counters are NOT applied this pass', {
        goal, error: err && err.message,
      });
    }
    return null;
  }
}

// ── A DISARM IS NEVER SILENT ──────────────────────────────────────────────────────────────────
//
// WHAT WAS BROKEN. `skip-disarmed` is the strongest thing this pass can do to a lane — it stops
// every mechanical relaunch until a named external event — and it said NOTHING: no journal line,
// no ask, no owner surface. On `scratch-tool-reach-note` the leader's `nonterm` lane disarmed at
// 17:11Z 2026-08-27 and the next four hours of passes printed only `reconcile: pass`, while the
// plan reviewer's ending mail sat unread. A stop nobody can see is indistinguishable from a system
// with nothing to do.
//
// ONCE PER (SUBJECT, DISARM), and the marker is the counter row's own `disarm_announced_at` — so a
// 5-minute cadence does not become a 5-minute alarm, a restart does not re-announce, and `rearm`
// deleting the row is what makes the NEXT disarm audible again. No new channel is invented: the
// journal `warn` is this file's existing voice and the ask record is `exhaustion.js`'s existing
// owner surface (`{workspace}/.rbtv/runtime/ignite/asks/<id>.json` + the `open_asks` row), the same
// one the exhaustion exit writes.
function announceDisarm({
  goal, seat, reason, driver, workspaceRoot, store, config, say, at, countersFile,
  attempts = null, stamped = false,
}) {
  const row = counters.peekCounter(
    { driver, goal, seat, reasonClass: reason }, { countersFile },
  );
  if (!row || row.disarm_announced_at) return null;
  const refusalText = `${reason} reached the attempt bound on this lane; `
    + `${stamped ? 'the lane is stamped disarmed' : 'the lane could NOT be stamped (no ending store on the pass)'}`;
  let ask = null;
  let askError = null;
  if (workspaceRoot) {
    try {
      ask = recordGroupedAsk({
        store, workspaceRoot, goal, seat, driver, reasonClass: reason, refusalText,
        attempts: attempts || row.attempts, at,
      });
    } catch (err) {
      askError = (err && err.message) || String(err);
    }
  }
  if (say) {
    say('warn', 'reconcile: this lane is DISARMED — every mechanical relaunch for this reason '
      + 'class is STOPPED until a named re-arm event. Nothing re-arms on its own.', {
      goal,
      seat,
      reason,
      driver,
      attempts: row.attempts,
      n: config && config.attempt_counter_n,
      first_at: row.first_at,
      last_at: row.last_at,
      owed_items: row.owed_items || null,
      stamped_disarmed: stamped,
      ask: ask ? ask.ask_id : null,
      ask_record: ask ? ask.file : null,
      ask_error: askError,
      re_arm_events: counters.RE_ARM_EVENTS,
    });
  }
  counters.markDisarmAnnounced({
    driver, goal, seat, reasonClass: reason, at,
  }, { countersFile });
  return { announced: true, ask: ask ? ask.ask_id : null, askError };
}

// One same-reason retry, and the exhaustion exit when it reaches N. Returns what the pass records:
// `attempts`, whether this retry EXHAUSTED the counter, and whether the driver must not fire at
// all because a previous pass already exhausted it (`disarmed`).
function countRetry({
  store, workspaceRoot, goal, seat, reason, refusalText, config, say, at, countersFile, items,
}) {
  if (!config) return { counted: false, why: 'recovery-config-error' };
  const driver = driverFor(reason);
  const counted = counters.countAttempt({
    driver, goal, seat, reasonClass: reason, n: config.attempt_counter_n, at, items,
  }, { countersFile });
  if (!counted.exhausted) {
    return {
      counted: true, driver, attempts: counted.attempts, advanced: counted.advanced,
    };
  }
  // THE EXIT. One stamp, one signature-grouped ask RECORD, and not one byte to Slack — the record
  // is impl-slack's to post. A store that cannot stamp (a probe's fake, a dry pass) leaves the
  // count standing and the caller reports it, rather than the pass throwing.
  if (!store || typeof store.stampSystem !== 'function') {
    // ⚠ THIS PASS HOLDS NO ENDING STORE, so the owner-visible EXIT cannot be taken: no `disarmed`
    // stamp. It used to return here in total silence, and that silence is the second half of the
    // 2026-08-27 stall — five live counter rows at or past N, zero exhaustion lines in the journal,
    // and no `asks/` directory at all, because nothing in the deployed tree sets `engine.endingStore`
    // [memory engine/20260825-c-attempt-counter-replaces-both ATTENTION 4]. The lane still stops on
    // the next pass, so the stop is ANNOUNCED here even though it cannot be stamped.
    const said = announceDisarm({
      goal, seat, reason, driver, workspaceRoot, store, config, say, at, countersFile,
      attempts: counted.attempts, stamped: false,
    });
    return {
      counted: true,
      driver,
      attempts: counted.attempts,
      advanced: counted.advanced,
      exhausted: true,
      exit: 'no-ending-store',
      ...(said && said.ask ? { ask: said.ask } : {}),
    };
  }
  const out = exhaust({
    store,
    workspaceRoot,
    goal,
    seat,
    driver,
    reasonClass: reason,
    refusalText: refusalText || `${reason} retried ${counted.attempts} times with the same refusal class`,
    attempts: counted.attempts,
    at,
  });
  if (say) {
    say('warn', 'reconcile: attempt counter exhausted — lane stamped disarmed incomplete, ask '
      + 'recorded. Nothing re-arms on its own; a named re-arm event is required.', {
      goal,
      seat,
      reason,
      attempts: counted.attempts,
      ask: out.ask.ask_id,
      grouped: out.ask.grouped,
      re_arm_events: counters.RE_ARM_EVENTS,
    });
  }
  // This IS the disarm announcement for this (subject, disarm), so the `skip-disarmed` branch on
  // the following passes stays quiet rather than repeating it every cadence.
  counters.markDisarmAnnounced({
    driver, goal, seat, reasonClass: reason, at,
  }, { countersFile });
  return {
    counted: true,
    driver,
    attempts: counted.attempts,
    advanced: counted.advanced,
    exhausted: true,
    ask: out.ask.ask_id,
  };
}

// THE BRAKE, and it is the counter's own state rather than a byte comparison: a lane whose counter
// already reached N is DISARMED and the mechanical relaunch stops. It re-arms on a named event —
// `resume {goal}`, a deploy, a config change, an owner/leader act — and on nothing else.
function counterDisarmed({
  goal, seat, reason, config, countersFile,
}) {
  if (!config) return false;
  const row = counters.peekCounter(
    { driver: driverFor(reason), goal, seat, reasonClass: reason }, { countersFile },
  );
  return Boolean(row && Number(row.attempts) >= config.attempt_counter_n);
}

// ── THE HOOKUP ITSELF, and it is deliberately THIN ────────────────────────────────────────────
//
// Everything it decides is decided elsewhere. It reads the two facts this file already has a
// reader for — what the seat's DESCRIPTOR declares (`seatCast`, the surface the launch actually
// obeys) and what its BINDING says (`readTaskforce`, the surface `rbtv-bindings set` writes) —
// hands them to the ruling's own predicate, and passes the answer on.
//
// ⚠ NOTHING COUNTER-INTERNAL IS TOUCHED HERE. The counter's three functions above are
// self-contained; this returns a decision and the caller spends (or does not spend) the strike.
function classifyRefusal({
  goal, goalFolder, seat, errorText, config, lanesFile, tableFile, at, say,
}) {
  let declaredModel = '';
  let declaredHarness = '';
  let boundModel = '';
  try {
    const cast = seatCast(goalFolder, seat);
    declaredModel = cast.model || '';
    declaredHarness = cast.harness || '';
  } catch { /* an unreadable descriptor is "no pin expressed", never a pin */ }
  try {
    const row = readTaskforce(goalFolder).find((r) => r.seat === seat);
    boundModel = (row && row.model) || '';
  } catch { /* an unreadable taskforce is the same */ }

  const override = providerLanes.seatModelOverride({ declaredModel, boundModel });
  try {
    const decision = providerLanes.onLaunchFailure({
      goal,
      seat,
      errorText,
      harness: declaredHarness || null,
      model: declaredModel || null,
      override,
      config,
      at,
      lanesFile,
      tableFile,
    });
    if (say) {
      say(decision.strike ? 'warn' : 'info',
        decision.strike
          ? 'reconcile: CONFIGURATION provider fault — ordinary failed + strike, no reroute [spec-recovery §3]'
          : 'reconcile: TRANSIENT provider fault — no strike [spec-recovery §3]', {
          goal,
          seat,
          provider_class: decision.classification,
          matched: decision.evidence && decision.evidence.matched,
          override,
          reroute: decision.reroute ? decision.reroute.to : null,
          provider_backoff_until: decision.backoff_until,
        });
    }
    return decision;
  } catch (err) {
    // A missing recognition list or an unreadable routing table is a CONFIGURATION-ERROR, and the
    // safe direction is the ordinary strike path — never a silent no-strike dead end.
    if (say) {
      say('warn', 'reconcile: provider classification UNAVAILABLE — the ordinary strike path stands', {
        goal, seat, error: err && err.message,
      });
    }
    return null;
  }
}

// ── B11 · THE RETRY-BUDGET HANDOFF, ASSEMBLED FROM WHAT THIS PASS ALREADY READS ───────────────
//
// `relaunch-budget.js#assembleHandoff` REFUSES a payload with a hole [T4-R6] — the leader spends
// its one bounded attempt on whatever it is handed, and that attempt does not come back. So every
// field is read from a real source here, and a field that cannot be read is a REFUSAL to hand off,
// never a blank.
//
// ⚠ THE PROGRESS NOTE IS ONE FILE PER SEAT, not one per sitting: `checkpoint.js` writes
// `progress-note.md` into the seat folder and the next sitting overwrites it. So only the LATEST
// sitting's note can exist on disk, and the earlier one is reported as absent WITH THAT REASON
// rather than as a seat that wrote nothing — the two are different facts and the leader is
// judging on them.
function handoffFieldsFor({ goalFolder, goal, seat }) {
  const seatDir = path.join(goalFolder, 'seats', seat);
  let brief;
  try {
    brief = fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8');
  } catch (err) {
    return { ok: false, why: 'no-seat-brief', detail: err.message };
  }

  // The seat's last two ENDED rows, newest first — the two sittings the budget was spent on.
  const rows = loadSessions(goalFolder)
    .filter((r) => (r.seat || '').trim() === seat && (r.ended || '').trim())
    .sort((a, b) => (tsAfter(a.ended, b.ended) ? -1 : 1))
    .slice(0, 2);

  let latestNote = null;
  try { latestNote = checkpoint.readProgressNote(seatDir); } catch { latestNote = null; }

  const progressNotes = rows.map((r, i) => (i === 0
    ? {
      sitting: r['session-id'] || r.started || 'latest',
      seat_dir: seatDir,
      note: latestNote,
      ...(latestNote ? {} : { missing: true, why: 'this sitting wrote no progress note' }),
    }
    : {
      sitting: r['session-id'] || r.started || `sitting-${i + 1}`,
      note: null,
      missing: true,
      why: 'the progress note is ONE file per seat and the later sitting overwrote it',
    }));
  // BOTH notes are required. Fewer than two ended rows means the budget cannot have been spent on
  // two sittings, so the caller has a state this handoff was not designed for — say so.
  if (progressNotes.length < 2) {
    return { ok: false, why: 'fewer-than-two-sittings', detail: `${progressNotes.length} ended row(s)` };
  }

  const killReasons = rows.map((r) => {
    const disp = (r.disposition || '').trim() || '(none)';
    const writer = (r['disposition-writer'] || '').trim() || 'unknown';
    return `${r['session-id'] || r.started}: ${disp} (written by ${writer})`;
  });
  const transcriptPointers = rows.map((r) => {
    const native = (r['native-session-id'] || '').trim();
    return `${r.harness || 'harness?'}:${native || '(no native session id)'} @ ${r.workdir || seatDir}`;
  });
  return {
    ok: true, brief, progressNotes, killReasons, transcriptPointers,
  };
}

// The whole B11 exit, in one place: the budget is exhausted, so the lane STOPS and the leader is
// asked. Returns the action the pass records — it launches nothing itself, because the wake rides
// the leader launch target the caller assembles from `handoff.payloadText`.
function leaderHandoffFor({
  store, workspaceRoot, goalFolder, goal, seat, config, at,
}) {
  const fields = handoffFieldsFor({ goalFolder, goal, seat });
  if (!fields.ok) return { ok: false, why: fields.why, detail: fields.detail };
  let handoff;
  try {
    handoff = relaunchBudget.leaderHandoff({
      store,
      goal,
      seat,
      brief: fields.brief,
      progressNotes: fields.progressNotes,
      killReasons: fields.killReasons,
      transcriptPointers: fields.transcriptPointers,
    }, config);
  } catch (err) {
    // The commonest arm by far: the one bounded attempt is ALREADY spent, which is exactly what
    // `leader_attempt_used` is for. Not an error — the next rung is the owner ask.
    return { ok: false, why: 'handoff-refused', detail: err.message };
  }
  const answerPath = relaunchBudget.leaderInstructionPath(workspaceRoot, goal, seat);
  return {
    ok: true,
    payload: handoff.payload,
    ending: handoff.ending,
    answerPath,
    payloadText: relaunchBudget.handoffPayloadText(handoff.payload, answerPath),
  };
}

function reconcileGoal({
  goal, goalFolder, engine, say = () => {}, pickup = null,
  now = Date.now(), force = false, dryRun = false,
  cadenceMs = CADENCE_MS,
  // The recovery knobs, and the workspace they are read from. Injected by a probe or a selftest;
  // resolved off the store's own workspace root in the daemon [spec-recovery §2.1].
  workspaceRoot: workspaceRootArg = undefined,
  recovery = undefined,
  // The counter ledger's file. Overridden by a probe or a selftest exactly as `registryFile` is,
  // so a fixture pass never writes into the daemon's own counters.
  countersFile = undefined,
  // The provider-lane ledger and the shared routing table. Overridden by a probe or a selftest
  // exactly as `countersFile` is, so a fixture pass never writes into the daemon's own lanes nor
  // reroutes off the owner's real table.
  lanesFile = undefined,
  tableFile = undefined,
  readyAnswer: readyInjected = undefined,
  promptFn = undefined,
  recoverFn = undefined,
  live = undefined,
}) {
  const heartStore = engine && engine.heartStore;
  const workspaceRoot = workspaceRootArg
    || (heartStore && heartStore.config && heartStore.config.workspaceRoot) || null;
  // The ending store is the ONE store the exhaustion exit stamps through [spec-state-store §1.1].
  // `engine.endingStore` when the daemon holds one; absent in a dry pass, and the counter reports
  // that rather than inventing a second writer.
  const endingStore = (engine && engine.endingStore) || null;
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

  // Honour `rbtv goal pause`. ONE reader: lane-watch.laneIsPaused (the goal-state
  // row; leftover `paused ` prefix is consumed there). Lazy-require — lane-watch
  // requires this module at top level; a cycle at load would leave the reader undefined.
  const { laneIsPaused } = require('./lane-watch');
  if (goalFolder && laneIsPaused(goalFolder, heartStore)) {
    if (!dryRun && heartStore) setPassAt(heartStore, goal, at);
    if (say) say('info', 'reconcile: skipped — goal is paused', { goal });
    return { skipped: 'paused', goal };
  }

  // Honour the finish EVENT (append-only FINISH_MARKER completion), never the store word.
  // Same shape as pause: watchers terminate here so a dead room is not rebuilt and no chair launches.
  if (goalFolder && finishEvent(goalFolder)) {
    if (!dryRun && heartStore) setPassAt(heartStore, goal, at);
    if (say) say('info', 'reconcile: skipped — goal is finished', { goal });
    return { skipped: 'finished', goal };
  }

  const actions = [];

  // Resolved ONCE per pass: every counter AND the relaunch budget in this pass read the same
  // numbers. Hoisted above the launch targets because the B11 drain below runs before them.
  const recoveryConfig = recoveryNumbers({
    recovery, workspaceRoot, say, goal,
  });
  if (!recoveryConfig) {
    actions.push({ kind: 'detect', why: 'recovery-config-error', detail: 'attempt counters not applied' });
  }

  // ── B11 · THE LEADER'S ANSWER, DRAINED BEFORE ANYTHING IS DECIDED ────────────────────────────
  //
  // A leader that was asked for one of the four instructions writes its judgment as a file; this
  // is the ONE place it is applied, and it runs FIRST so a `rewrite-brief` re-arm is visible to
  // this same pass's launch decisions rather than a cadence later. `executeLeaderInstruction` does
  // the applying — nothing here re-decides anything the leader decided.
  if (!dryRun && endingStore && workspaceRoot) {
    let applied = [];
    try {
      applied = relaunchBudget.drainLeaderInstructions({
        store: endingStore, workspaceRoot, goal, at,
      });
    } catch (err) {
      say('warn', 'reconcile: draining the leader instruction inbox threw — the pass continues', {
        goal, error: err && err.message,
      });
    }
    for (const r of applied) {
      say(r.applied ? 'info' : 'warn',
        r.applied
          ? 'reconcile: a LEADER INSTRUCTION was applied — the leader decided, the daemon executed [D6, CF-3]'
          : 'reconcile: a leader instruction was REFUSED — the file is moved aside with its reason beside it',
        {
          goal, seat: r.seat, instruction: r.kind || null, error: r.error || null, file: r.file || null,
        });
      actions.push({
        kind: r.applied ? 'leader-instruction-applied' : 'leader-instruction-refused',
        seat: r.seat,
        instruction: r.kind || null,
        error: r.error || null,
      });
    }
  }

  let readyAnswer = readyInjected;
  if (readyAnswer === undefined) {
    readyAnswer = readySeats(goalFolder, { heartStore, goal });
  }

  const queued = queuedSeats(heartStore, goal);
  const derived = owedFromLedgers(goalFolder, {
    readyAnswer, live, queued, summoned: summonedSeats(say),
    heartStore, goal,
  });
  // B16 — the chair, or NOTHING. `leader` is `null` on a goal with no staffed leader row, and
  // every consumer below refuses rather than substituting.
  const leaderChair = leaderSeat(goalFolder);
  const leader = leaderChair.seat;

  if (!dryRun && heartStore) setPassAt(heartStore, goal, at);

  if (say) {
    say('info', 'reconcile: pass', {
      goal,
      classA: derived.classA.map((x) => x.seat),
      classB: derived.classB.map((x) => x.seat),
      classE: derived.classE ? derived.classE.pending : null,
      readyRefused: derived.readyRefused,
      deadExcluded: derived.deadSeats.length,
      summonedExcluded: readyAnswer.summonedExcluded || derived.summonedSeats,
      // THE HELD ROWS ARE NAMED, NOT COUNTED. A hold is a leader RULING and the pass that honours
      // it must say whose ruling and what releases it — a silent exclusion is how nine paid
      // sittings looked identical to nine no-ops in the journal.
      heldExcluded: (derived.heldSeats || []).map((h) => `${h.seat}:until ${h.until}${h.ask_id ? `:${h.ask_id}` : ''}`),
      leader,
      dryRun: Boolean(dryRun),
    });
  }

  // ── THE LOUD, NAMED REFUSAL [B16] ────────────────────────────────────────────────────────────
  // Fired on EVERY pass, deliberately: this is a staffing state that only a `materialize` can
  // clear, and the alternative the daemon used to take was to promote a worker into the chair in
  // silence. A pass that says nothing here is the defect, not the noise.
  if (!leader) {
    say('warn', 'reconcile: this goal has NO LEADER CHAIR — no seat is treated as leader on this '
      + 'pass. Rows needing the leader\'s judgment are NOT handed to a substitute, and the room is '
      + 'NOT rebuilt under one. The `leader` chair is minted by the staffing backfill: re-run '
      + '`rbtv goal materialize <goal>` on this goal.', {
      goal, why: leaderChair.why, detail: leaderChair.detail,
    });
    actions.push({ kind: 'detect', why: leaderChair.why, detail: leaderChair.detail });
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
      // The owed item IS this seat, and it is invariant for the life of the lane — so the
      // owed-item marker can never make this driver skip a count (D40's signature is invariant for
      // the same reason). A relaunch of the same named seat is a retry by definition.
      owedItems: [item.seat],
      source: 'a',
    });
  }
  // The rest is the leader's judgment, in ONE wake that NAMES the rows. The signature is the
  // owed CONTENT, so a ruling that removes or changes a row IS progress (D34).
  const nonterm = derived.classA.filter((x) => x.reason !== 'incomplete');
  if (nonterm.length && !leader) {
    // B16 — these rows need a JUDGMENT, and judgment is the leader chair's. With no chair there is
    // nobody to wake: the rows stand and are named, which is what the silent `seats[0]` promotion
    // used to hide behind an ordinary-looking wake of the wrong seat.
    say('warn', 'reconcile: owed row(s) need the leader\'s judgment and this goal has NO LEADER '
      + 'CHAIR — nothing is woken for them, and NO substitute seat is used. They stand until the '
      + '`leader` row is staffed.', {
      goal, why: leaderChair.why, seats: nonterm.map((x) => x.seat),
    });
    actions.push({
      kind: 'no-leader-chair',
      reason: 'nonterm',
      why: leaderChair.why,
      seats: nonterm.map((x) => x.seat),
    });
  } else if (nonterm.length) {
    launchTargets.push({
      seat: leader,
      reason: 'nonterm',
      signature: `nonterm:${nonterm.map((x) => `${x.seat}=${x.ending}`).sort().join(',')}`,
      // THE OWED ITEMS ARE THE SEATS WHOSE ROWS NEED JUDGMENT. Overlap with what the counter last
      // counted = the leader still owes judgment on work it was already woken for = a retry, and
      // the bound keeps closing (owed `{a}` then `{a,b}` still reaches N — the [C-4] inversion).
      // NO overlap = every row it was woken for was resolved and these are different rows = a
      // FIRST attempt at new work, which is the 2026-08-27 per-hop planning chain exactly.
      owedItems: nonterm.map((x) => x.seat),
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
      // `lastNum` is the chair's highest pending message number — the `last_unread_max_id` progress
      // marker. Unchanged = the SAME pending mail woke this chair again = a retry. Moved = mail
      // that did not exist when the counter last advanced = new work, and a new staff mail is
      // never a retry.
      owedItems: [`#${item.lastNum}`],
      source: 'b',
    });
  }

  const liveSet = new Set(derived.live);
  const seenTarget = new Set();
  for (const t of launchTargets) {
    let action;
    if (seenTarget.has(t.seat)) {
      // One launch per seat per pass; the OTHER reason still counts its own attempt.
      action = { kind: 'skip-already-targeted', seat: t.seat, reason: t.reason };
    } else if (liveSet.has(t.seat) || queued.has(t.seat)) {
      seenTarget.add(t.seat);
      action = { kind: 'skip-live-or-queued', seat: t.seat, reason: t.reason };
    } else if (providerLanes.laneFacts(
      { goal, seat: t.seat }, { lanesFile, now: new Date(now) },
    ).provider_backoff_waiting) {
      // ── THE PROVIDER BACKOFF, AS A PER-LANE BRAKE [spec-recovery §3, C-5, C-9] ─────────────
      // THIS LANE is waiting out a provider window; its siblings on the same goal are untouched,
      // which is the whole C-9 correction. No counter advances: a transient provider outage is
      // not something the seat did, so nothing it did may be counted against it.
      seenTarget.add(t.seat);
      action = {
        kind: 'skip-provider-backoff',
        seat: t.seat,
        reason: t.reason,
        until: providerLanes.laneFacts({ goal, seat: t.seat }, { lanesFile }).provider_backoff_until,
      };
    } else if (t.reason === 'incomplete'
      && recoveryConfig && endingStore && workspaceRoot
      && relaunchBudget.budgetState(
        { store: endingStore, goal, seat: t.seat }, recoveryConfig,
      ).exhausted) {
      // ── B11 · THE RECOVERY RELAUNCH BUDGET IS EXHAUSTED — THE LEADER IS ASKED ──────────────
      //
      // ⚠ THE BUDGET IS ASKED **BEFORE** THE ATTEMPT COUNTER AND THIS BRANCH RETURNS, which is
      // `relaunch-budget.js`'s own stated contract: the two bounds are INDEPENDENT, whichever
      // trips first takes its exit, and the other must not also fire in the same act. So no
      // `countRetry` runs on this seat this pass (the `kind` below is excluded from the counting
      // block, exactly as the disarm and backoff skips are).
      //
      // Class A `incomplete` is the recovery cause `armed-incomplete` [T1-R6] — the relaunch of a
      // lane the seat itself declared unfinished. `nonterm` and `unread` are not recovery
      // relaunches and never reach here.
      seenTarget.add(t.seat);
      const handoff = leaderHandoffFor({
        store: endingStore, workspaceRoot, goalFolder, goal, seat: t.seat,
        config: recoveryConfig, at,
      });
      if (!handoff.ok) {
        say('warn', 'reconcile: the relaunch budget is EXHAUSTED and the leader could NOT be asked '
          + '— the lane stays stopped and the next rung is the owner ask', {
          goal, seat: t.seat, why: handoff.why, detail: handoff.detail,
        });
        action = {
          kind: 'budget-exhausted-no-handoff', seat: t.seat, reason: t.reason, why: handoff.why,
        };
      } else if (!leader) {
        // B16 composes with B11: there is a judgment to hand over and no chair to hand it to.
        say('warn', 'reconcile: the relaunch budget is EXHAUSTED and this goal has NO LEADER CHAIR '
          + '— the handoff payload is written but nobody is woken for it', {
          goal, seat: t.seat, answer_path: handoff.answerPath,
        });
        action = {
          kind: 'budget-exhausted-no-handoff', seat: t.seat, reason: t.reason, why: 'no-leader-chair',
        };
      } else {
        say('warn', 'reconcile: the recovery relaunch budget is EXHAUSTED — the lane STOPS and the '
          + 'leader gets its ONE bounded attempt [D6, T1-R8]', {
          goal,
          seat: t.seat,
          tripped: handoff.payload.budget.tripped,
          failures: `${handoff.payload.budget.failures}/${handoff.payload.budget.capFailures}`,
          total: `${handoff.payload.budget.total}/${handoff.payload.budget.capTotal}`,
          instructions: handoff.payload.instruction_kinds,
          answer_path: handoff.answerPath,
        });
        // The ask rides the door that already puts a question in front of the leader: the D33(a)
        // leader wake, boot prompt first and the block appended after it.
        const woken = launchSitting({
          heartStore,
          goal,
          goalFolder,
          seat: leader,
          promptFn: (gf, sname) => {
            const head = promptFn ? promptFn(gf, sname) : seatBootPrompt(gf, sname).prompt;
            return (head === null || head === undefined) ? null : head + handoff.payloadText;
          },
          say,
          reason: 'leader-handoff',
          signature: `leader-handoff:${t.seat}`,
        });
        action = {
          kind: woken.ok ? 'leader-handoff' : 'leader-handoff-not-woken',
          seat: t.seat,
          reason: t.reason,
          leader,
          answerPath: handoff.answerPath,
          ...(woken.ok ? { enq: woken.enq, jobId: woken.jobId } : { error: woken.error }),
        };
      }
    } else if (counterDisarmed({
      goal, seat: t.seat, reason: t.reason, config: recoveryConfig, countersFile,
    })) {
      // THE BRAKE — the attempt counter's own state, not a byte comparison. This lane already
      // reached N for this reason class, so it is stamped `disarmed` and waits for a named re-arm
      // event. The counter does NOT advance further: there is nothing left to count.
      //
      // AND IT IS AUDIBLE. `announceDisarm` journals the stop ONCE per (subject, disarm) with the
      // counter row and the re-arm list, and raises it on the ask surface. This branch used to be
      // completely silent — see the header on `announceDisarm`.
      seenTarget.add(t.seat);
      const said = announceDisarm({
        goal,
        seat: t.seat,
        reason: t.reason,
        driver: driverFor(t.reason),
        workspaceRoot,
        store: endingStore,
        config: recoveryConfig,
        say,
        at,
        countersFile,
        stamped: Boolean(endingStore),
      });
      action = {
        kind: 'skip-disarmed',
        seat: t.seat,
        reason: t.reason,
        ...(said ? { announced: true, ask: said.ask } : {}),
      };
    } else {
      seenTarget.add(t.seat);
      const launched = launchSitting({
        heartStore, goal, goalFolder, seat: t.seat, promptFn: t.promptFn || promptFn, say,
        reason: t.reason, signature: t.signature,
      });
      if (launched.ok) {
        // The attempt is over: the pass through the alternates and the backoff ladder both clear.
        // The seat's recorded reroutes are NOT cleared — they are what it actually ran.
        providerLanes.onLaunchSucceeded({ goal, seat: t.seat }, { lanesFile });
        action = {
          kind: 'enqueue', seat: t.seat, reason: t.reason, enq: launched.enq, jobId: launched.jobId,
        };
        // ── B11 · THE SPEND, AT THE MOMENT THE RELAUNCH ACTUALLY HAPPENED ───────────────────
        // Never on intent: `relaunch-budget.js` says a budget that decrements on consideration
        // stops lanes that were never relaunched. Class A `incomplete` only — an `unread` wake or
        // a leader wake is not a recovery relaunch and the module REFUSES a non-recovery cause by
        // name, so a future caller cannot route one through this door by accident [C-11].
        if (t.reason === 'incomplete' && endingStore) {
          try {
            relaunchBudget.spendRecoveryRelaunch({
              store: endingStore, goal, seat: t.seat, cause: 'armed-incomplete',
            });
          } catch (err) {
            say('warn', 'reconcile: the recovery relaunch was made but the budget could not be '
              + 'spent — the bound is weaker than it reads until this is fixed', {
              goal, seat: t.seat, error: err && err.message,
            });
            action.budgetSpendFailed = err && err.message;
          }
        }
      } else {
        action = {
          kind: 'launch-refused', seat: t.seat, reason: t.reason, error: launched.error,
        };
        // ── THE SPLIT [spec-recovery §3] ──────────────────────────────────────────────────────
        // Before this existed, EVERY refusal fed the counter identically: a transient quota
        // outage struck the seat toward a dead end for something no seat did (ST-10), and a
        // plan-declared bad slug got the same treatment with no reroute and no surfacing
        // (ST-19). The two now take opposite paths, and the caller of this file learns which.
        const decision = classifyRefusal({
          goal, goalFolder, seat: t.seat, errorText: launched.error,
          config: recoveryConfig, lanesFile, tableFile, at: new Date(now), say,
        });
        if (decision) {
          action.provider_class = decision.classification;
          if (decision.reroute) action.reroute = decision.reroute;
          if (decision.backoff_until) action.provider_backoff_until = decision.backoff_until;
          // TRANSIENT NEVER STRIKES. The flag is read by the counting block below.
          action.noStrike = decision.strike === false;
        }
      }
    }
    // THE ATTEMPT IS THE PASS, NOT THE LAUNCH — that part of D34 survives intact. What changed is
    // the RESET: no launch outcome and no signature drift clears this count, only a named re-arm
    // event does [spec-recovery §5].
    // ⚠ THE BUDGET EXIT IS EXCLUDED HERE, and that exclusion is the [spec-recovery 2] rule that
    // the two bounds are independent: whichever trips first takes its exit and the other does not
    // also fire in the same act. A `leader-handoff` pass that ALSO struck the counter would spend
    // both bounds on one event and land the owner ask one pass early.
    if (action.kind !== 'skip-disarmed'
      && action.kind !== 'skip-provider-backoff'
      && action.kind !== 'leader-handoff'
      && action.kind !== 'leader-handoff-not-woken'
      && action.kind !== 'budget-exhausted-no-handoff'
      && !action.noStrike) {
      const retry = countRetry({
        store: endingStore,
        workspaceRoot,
        goal,
        seat: t.seat,
        reason: t.reason,
        refusalText: action.error ? `${t.reason}: ${action.error}` : null,
        config: recoveryConfig,
        countersFile,
        items: t.owedItems,
        at,
        say,
      });
      action.attempts = retry.attempts;
      // FALSE = this pass was NEW WORK, not a retry: the count stands where it was (it is never
      // reset — only `RE_ARM_EVENTS` does that). Recorded so the pass's own record says which.
      if (retry.counted) action.attemptAdvanced = Boolean(retry.advanced);
      if (retry.exhausted) action.exhausted = true;
      if (retry.ask) action.ask = retry.ask;
      if (!retry.counted) action.counterSkipped = retry.why;
    }
    actions.push(action);
  }

  if (derived.owed && !leader) {
    // B16 — the room is rebuilt UNDER A SEAT (`recover-room.py --seat`), and the seat it used was
    // the leader. With no chair there is no seat to rebuild under, and picking one is the
    // substitution this fix removes.
    const room = roomState(goal);
    if (!room.exists || room.empty) {
      say('warn', 'reconcile: this goal\'s room is dead or empty and there is NO LEADER CHAIR to '
        + 'rebuild it under — the room is NOT rebuilt. Staff the `leader` row and the next pass '
        + 'rebuilds it.', { goal, why: leaderChair.why });
      actions.push({ kind: 'room-refused', error: 'no-leader-chair', why: leaderChair.why });
    }
  } else if (derived.owed) {
    const room = roomState(goal);
    if (!room.exists || room.empty) {
      const recSeat = leader;
      const rec = recoverRoom({ goal, goalFolder, seat: recSeat, recoverFn });
      if (rec.ok) {
        actions.push({ kind: 'room-rebuilt', seat: recSeat });
      } else {
        const retry = countRetry({
          store: endingStore,
          workspaceRoot,
          goal,
          seat: recSeat,
          reason: 'room',
          refusalText: `room: ${rec.out || rec.status}`,
          config: recoveryConfig,
          countersFile,
          // No owed-item marker: the subject IS the room and a failed rebuild retried is a retry
          // of the same work, every time. The marker would be a constant, so it is not spelled.
          at,
          say,
        });
        actions.push({
          kind: 'room-refused', error: rec.out || rec.status,
          attempts: retry.attempts, exhausted: Boolean(retry.exhausted), ask: retry.ask,
        });
      }
    }
  }

  // THE END-OF-PASS SWEEP IS DELETED. It cleared a counter whenever the owed set changed — which
  // is exactly the evidence-driven reset spec-recovery §5 forbids, and the reason a drifting
  // ledger kept the old bound from ever firing. A counter now clears ONLY on a named re-arm event,
  // through `supervisor/attempt-counters.js#rearm`, and nowhere in this pass.

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
  STAFF_CHAIRS,
  owedFromLedgers,
  summonedSeats,
  reconcileGoal,
  maybeReconcile,
  launchSitting,
  loadSessions,
  loadMessages,
  lastBySeat,
  liveSeatsFromLedgers,
  checkinOf,
  tsAfter,
};
