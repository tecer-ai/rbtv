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
// ⚠ GRANTS ARE NOT TOUCHED. Launch goes through the supervisor's wrapped spawn door
//    (`launchThroughDoor`, `onSeatBusy: 'queue'`) — never this file's own enqueue [§5].
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
const { requirePythonCmd } = require('../runtime/python-cmd');
const {
  readySeats, readCsv, jobIdFor, uncastSeats, seatBootPrompt, readTaskforce, seatCast,
} = require('./seeding');
// ── THE ONE OWED-WORK COMPUTER AND THE ONE ENQUEUE [spec-supervisor §5, T4-R7, C-15] ──────────
// `deriveOwed` is the SURVIVOR of the two owed-work computers. It lives at the supervisor home
// because the owed set is supervisor-owned, and this file now ASKS it rather than being it.
// `launchThroughDoor` is the single `heartStore.enqueue` on the owed path — the watcher no longer
// has one of its own.
const { deriveOwed } = require('./owed');
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
const { exhaust } = require('./exhaustion');
const { loadRecoveryConfig } = require('./recovery-config');

const COORD_PY = path.join(__dirname, '..', 'team-kit', 'coord.py');
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
    'its own. No runtime ruling instrument exists for them any more: `rule-disposition` (the',
    'verb that used to record a ruling or a HOLD on a row) was deleted [T2-R12, T1-R9] — owner',
    'authorization is now an answer to a live ask, not a standing CLI ruling, and that door is',
    'not wired here yet. This wake will keep repeating on these rows until it is.',
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

// One same-reason retry, and the exhaustion exit when it reaches N. Returns what the pass records:
// `attempts`, whether this retry EXHAUSTED the counter, and whether the driver must not fire at
// all because a previous pass already exhausted it (`disarmed`).
function countRetry({
  store, workspaceRoot, goal, seat, reason, refusalText, config, say, at, countersFile,
}) {
  if (!config) return { counted: false, why: 'recovery-config-error' };
  const driver = driverFor(reason);
  const counted = counters.countAttempt({
    driver, goal, seat, reasonClass: reason, n: config.attempt_counter_n, at,
  }, { countersFile });
  if (!counted.exhausted) return { counted: true, driver, attempts: counted.attempts };
  // THE EXIT. One stamp, one signature-grouped ask RECORD, and not one byte to Slack — the record
  // is impl-slack's to post. A store that cannot stamp (a probe's fake, a dry pass) leaves the
  // count standing and the caller reports it, rather than the pass throwing.
  if (!store || typeof store.stampSystem !== 'function') {
    return {
      counted: true, driver, attempts: counted.attempts, exhausted: true, exit: 'no-ending-store',
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
    say('warn', 'reconcile: attempt counter exhausted — lane stamped disarmed incomplete, ask recorded', {
      goal, seat, reason, attempts: counted.attempts, ask: out.ask.ask_id, grouped: out.ask.grouped,
    });
  }
  return {
    counted: true, driver, attempts: counted.attempts, exhausted: true, ask: out.ask.ask_id,
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

  // Honour `rbtv goal pause`. ONE reader: lane-watch.laneIsPaused (DEC-1 twin of
  // goal_cli.lane_is_paused). Lazy-require — lane-watch requires this module at
  // top level; a cycle at load would leave the reader undefined.
  const { laneIsPaused } = require('./lane-watch');
  if (goalFolder && laneIsPaused(goalFolder, heartStore)) {
    if (!dryRun && heartStore) setPassAt(heartStore, goal, at);
    if (say) say('info', 'reconcile: skipped — goal is paused', { goal });
    return { skipped: 'paused', goal };
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
      signature: `nonterm:${nonterm.map((x) => `${x.seat}=${x.ending}`).sort().join(',')}`,
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

  // Resolved ONCE per pass: every counter in this pass reads the same N.
  const recoveryConfig = recoveryNumbers({
    recovery, workspaceRoot, say, goal,
  });
  if (!recoveryConfig) {
    actions.push({ kind: 'detect', why: 'recovery-config-error', detail: 'attempt counters not applied' });
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
    } else if (counterDisarmed({
      goal, seat: t.seat, reason: t.reason, config: recoveryConfig, countersFile,
    })) {
      // THE BRAKE — the attempt counter's own state, not a byte comparison. This lane already
      // reached N for this reason class, so it is stamped `disarmed` and waits for a named re-arm
      // event. The counter does NOT advance further: there is nothing left to count.
      seenTarget.add(t.seat);
      action = { kind: 'skip-disarmed', seat: t.seat, reason: t.reason };
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
    if (action.kind !== 'skip-disarmed'
      && action.kind !== 'skip-provider-backoff'
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
        say,
      });
      action.attempts = retry.attempts;
      if (retry.exhausted) action.exhausted = true;
      if (retry.ask) action.ask = retry.ask;
      if (!retry.counted) action.counterSkipped = retry.why;
    }
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
        const retry = countRetry({
          store: endingStore,
          workspaceRoot,
          goal,
          seat: recSeat,
          reason: 'room',
          refusalText: `room: ${rec.out || rec.status}`,
          config: recoveryConfig,
          countersFile,
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
