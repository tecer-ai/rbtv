'use strict';

// engine/attached-execution.js — THE SECOND ATTACHMENT.
//
// The daemon attaches the engine to a systemd unit behind a gateway. This attaches THE SAME
// ENGINE to the calling terminal, dying with it (registry `concepts/rbtv-cli.md` § Run-verb
// machinery, owner ruling decisions.md#d-attached-run-embedded-engine). What lives here is
// ATTACHMENT, never advancement: the boot, the loop policy, the exit condition and the seeding of
// this run's seats. Every advance/dispatch/enforce decision is `ticker.tick()`'s — the daemon's
// own. A sequential runner is what that ruling rejected, and there is none here: parallel waves,
// timers and the stall ladder arrive because the ticker arrives.
//
// THE FOUR THINGS THE ATTACHMENT OWNS, and why each is here rather than in the engine:
//
//  1. THE STORE IT OPENS. `<goal-folder>/heart.db` — the PER-GOAL store, CMP-2 § Two store kinds,
//     placed by DEC-7 § placement "by the folder it belongs to", beside `sessions.csv` and
//     `state.json`. It NEVER opens the daemon's `{state_root}/heart.db`, and that is asserted
//     below rather than merely intended. (7.607 E3: the run folder it used to be placed by does
//     not exist — the package IS the goal folder, design-lock item 8.)
//  2. THE LOOP POLICY. The daemon loops forever on a timer. This ticks until the run COMPLETES or
//     until ANY worker asks a question, then RETURNS — the registry's own sentence.
//  3. RESUME. Re-running the verb reopens the same store and continues. Nothing is replayed:
//     seeding is create-only and a seat that already has an execution row is never re-enqueued.
//     Since #d-s23-single-execution-record-now that create-only rule reaches ACROSS LANES: the
//     goal's own `executions.csv` (engine/execution-record.js) is the completion authority both
//     lanes publish to and read before seeding, so a seat finished by the daemon is not re-run
//     here — and the v1 refusal that used to stand in for that record is retired with this build.
//     There is NO WATCHER for this lane and that is RULED, not missing
//     (decisions.md#d-attached-lane-no-watcher): recovery IS the owner re-running this command.
//  4. THE SUBSTRATE SEAM. Asserted FIRST, before any POSIX construct is reachable — see
//     ./substrate.js for what it refuses and why a refusal rather than a fallback.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { createEngine } = require('./index');
const substrate = require('./substrate');
const { loadConfig } = require('../server/spawn/config');
// The lane-independent SEEDING machinery — moved out of this file, unchanged in behaviour, because
// none of it was ever a property of the terminal a run is attached to (see seeding.js's header).
const {
  readCsv, jobIdFor, seedTaskforce, executionsByJob, seatIsFinished, seatHasRun,
  seatState, SEAT_STATES, enqueueEligible, recordView, readySeats,
  // WHICH SEATS ARE NOT CAST. Shared with the daemon lane's watch pass so both doors refuse the
  // same goals (`#d-abolish-profile-names` sub-ruling 3).
  uncastSeats,
} = require('./seeding');
// THE RELAUNCH GRANT'S ONE HOME — `<goal-folder>/relaunch-grants`, the same file the daemon lane
// reads inside the shared seeding functions. This lane used to keep the grant in a process-local
// `Set` built from argv, which is why the other lane could never be given one at all.
const { readGrants, grantRelaunch, spendGrant } = require('./relaunch-grants');
// THE GOAL'S EXECUTION RECORD — the one place any lane's reader asks "did this seat finish"
// (owner ruling decisions.md#d-s23-single-execution-record-now).
// `processOutcome` is the store-status → PROCESS-word map both close sites share, so this lane and
// the daemon's per-tick publish write the same word for the same ending (W2). The hold that used to
// be decided here is gone: an unanswered owner-ask is coord's `HELD` verdict now, computed once,
// universally, on the surface that knows what every seat declared.
const { openExecution, closeExecution, laneOf, processOutcome } = require('./execution-record');

// The goal folder's shape is the goals tree's (CMP-4), not ours to redefine. GOAL-DIRECT since
// 7.607 (design-lock items 7-8 — the `runs/run-{n}` segment is extinguished, not optional):
//   <workspace>/.rbtv/goals/<goal-name>/
const GOAL_FOLDER_RE = /[/\\]\.rbtv[/\\]goals[/\\][^/\\]+[/\\]?$/;

const STORE_FILENAME = 'heart.db';
const TASKFORCE = 'taskforce.csv';
// The goal's LAUNCH TRACE — one row per launched session, schema owned by `coord.py SESSIONS_COLS`
// (task 7.37). Written AND closed here by the foreground carrier (S-20); the cross-lane guard that
// used to read it is retired (see below). It is lifecycle accounting — the OUTCOME lives in the
// goal's execution record, `executions.csv`.
const SESSIONS_CSV = 'sessions.csv';

// A turn that is still the engine's business. `stalled` is LIVE on purpose: it means "the owner
// should look", never "the work is over" (the store's own note on TERMINAL_TURN_STATUSES), so a
// stalled seat must not let the run report itself complete.
const LIVE_TURN_STATUSES = ['launching', 'running', 'stalled'];
// The store's own TERMINAL_TURN_STATUSES, spelled here for the same reason the list above is: a
// carrier that guesses which statuses are final can overwrite a real outcome.
const TERMINAL_TURN_STATUSES = ['done', 'blocked', 'failed', 'killed'];

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function resolveGoalFolder(input) {
  const goalFolder = path.resolve(input);
  if (!fs.existsSync(goalFolder) || !fs.statSync(goalFolder).isDirectory()) {
    throw new Error(`not a directory: ${goalFolder}`);
  }
  if (!GOAL_FOLDER_RE.test(goalFolder)) {
    throw new Error(
      `${goalFolder} is not a goal folder. The attached engine's store is placed BY THE GOAL FOLDER ` +
      `IT BELONGS TO (DEC-7 § placement), so the path must be ` +
      `<workspace>/.rbtv/goals/<goal-name>/. Refusing rather than creating a heart ` +
      `store somewhere no one will look for it.`
    );
  }
  return goalFolder;
}

// CRITERION 4, ASSERTED RATHER THAN INTENDED. The owner ruling says the embedded engine "never
// opens the daemon's {state_root}/heart.db". A comment cannot enforce that, so the daemon's own
// configured data root is resolved and compared. Fail-closed: if the config cannot be read at all
// we still know the goal-folder path, and that path is the only one we ever pass to the engine —
// but where the daemon's root IS knowable, an equal path is a hard refusal.
function assertNotTheDaemonStore(storePath, spawnConfig) {
  const daemonDataRoot = process.env.RBTV_IGNITE_DATA_ROOT
    || (spawnConfig && spawnConfig.spawn && spawnConfig.spawn.data_root)
    || null;
  if (!daemonDataRoot) return;
  const daemonStore = path.resolve(daemonDataRoot, STORE_FILENAME);
  if (path.resolve(storePath) === daemonStore) {
    throw new Error(
      `REFUSING TO RUN: the resolved per-goal store ${storePath} IS the daemon's store. ` +
      `An attached execution keeps its own heart store in its goal folder and never opens ` +
      `{state_root}/heart.db (owner ruling decisions.md#d-attached-run-store-and-seats; ` +
      `CMP-2 § Two store kinds). Two writers on one store is meant to be impossible here by ` +
      `construction, not guarded — the in-process E_SECOND_WRITER guard cannot see the daemon.`
    );
  }
}

// THIS MACHINE's state root, read from the install's endpoint record — the file § State layout
// names as the ONE home of that fact (`.rbtv/modules/ignite/server.json`, machine-keyed because it
// travels via git to every machine). Null on any miss (no record, no entry for this hostname):
// absence here is a config state, not an error, and the caller falls through to the committed value.
function machineStateRoot(goalFolder) {
  const parts = goalFolder.split(path.sep);
  const idx = parts.lastIndexOf('.rbtv');
  if (idx === -1) return null;
  const wsRoot = parts.slice(0, idx).join(path.sep) || path.sep;
  try {
    const record = JSON.parse(fs.readFileSync(path.join(wsRoot, '.rbtv', 'modules', 'ignite', 'server.json'), 'utf8'));
    const entry = record.machines && record.machines[os.hostname()];
    return (entry && entry.state_root) || null;
  } catch {
    return null;
  }
}

// ── THE PER-TICK STATUS BLOCK (owner request 2026-08-12) ─────────────────────────────────────────
//
// The attached run owns a real terminal, and "tick N start / tick N end" was all it said while a
// seat ran for minutes — the operator could not tell running from queued from held without a second
// terminal and `--status`. This block is DERIVED per pass from the same post-tick reads the exit
// decision uses (the pre-tick view is stale by exactly the thing that just happened — same hazard
// evaluateExit's re-read comment documents), so it can never disagree with the verdict printed
// after it. It prints on STATE change, with a paced re-print while something runs so the elapsed
// column stays honest — never every tick, which would bury the engine's own lines.
function elapsedSince(iso) {
  if (!iso) return '?';
  const s = Math.max(0, Math.floor((Date.now() - Date.parse(iso)) / 1000));
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  return h ? `${h}h${String(m % 60).padStart(2, '0')}m` : m ? `${m}m${String(s % 60).padStart(2, '0')}s` : `${s}s`;
}

function renderStatusBlock(heartStore, rows, isHeld, view, ready) {
  const castOf = (r) => [r.harness, r.model, r.effort].filter(Boolean).join('/') || '(uncast)';
  const running = new Map();
  for (const status of ['launching', 'running']) {
    for (const ex of heartStore.listExecutionsByStatus(status)) {
      const m = /^seat-(.+)$/.exec(ex.job_id || '');
      if (m) running.set(m[1], ex.started_at || ex.fired_at || null);
    }
  }
  const finished = rows.filter((r) => view.finished.has(r.seat)).map((r) => r.seat);
  const finishedSet = new Set(finished);
  const pending = rows.filter((r) => !finishedSet.has(r.seat) && !running.has(r.seat));
  const heldCount = pending.filter((r) => isHeld && isHeld(r.seat)).length;

  const lines = [];
  const keyParts = [];
  lines.push(`── ${running.size} running · ${pending.length} queued/waiting · ${heldCount} interactive held for you · ${finished.length}/${rows.length} done ──`);
  if (running.size) {
    lines.push('Running');
    for (const r of rows) {
      if (!running.has(r.seat)) continue;
      lines.push(`  ${r.seat}  ${castOf(r)}  up ${elapsedSince(running.get(r.seat))}`);
      keyParts.push(`run:${r.seat}`);
    }
  }
  if (pending.length) {
    lines.push('Queue');
    const pendingSet = new Set(pending.map((r) => r.seat));
    const afterList = (r) => (r.after || '').split(',').map((s) => s.trim()).filter(Boolean);
    // Display nesting only: a seat hangs under its FIRST still-pending predecessor; the full
    // `after` list is printed on the row, so a multi-predecessor edge loses nothing.
    const children = new Map();
    const roots = [];
    for (const r of pending) {
      const parent = afterList(r).find((a) => pendingSet.has(a)) || null;
      if (parent) {
        if (!children.has(parent)) children.set(parent, []);
        children.get(parent).push(r);
      } else roots.push(r);
    }
    const printRow = (r, depth) => {
      const state = ready && ready.has(r.seat) ? 'ready' : 'waiting';
      const mark = isHeld && isHeld(r.seat) ? ' · interactive' : '';
      const after = afterList(r).length ? `  after: ${afterList(r).join(', ')}` : '';
      lines.push(`  ${'   '.repeat(depth)}${depth ? '└─ ' : ''}${r.seat}  ${castOf(r)}  [${state}]${after}${mark}`);
      keyParts.push(`${state}:${r.seat}`);
      for (const c of children.get(r.seat) || []) printRow(c, depth + 1);
    };
    for (const r of roots) printRow(r, 0);
  }
  if (finished.length) lines.push(`Done  ${finished.join(', ')}`);
  keyParts.push(`done:${finished.join(',')}`);
  // `key` deliberately carries NO elapsed times: equality means "same picture", so the caller can
  // re-print on change and merely refresh (paced) while the picture holds.
  return { block: lines.join('\n'), key: keyParts.join('|') };
}

// ── S-18 · THE CROSS-LANE REFUSAL, v1 — RETIRED (owner ruling #d-s23-single-execution-record-now)
//
// This is where `crossLaneEvidence` / `assertNoCrossLaneEvidence` stood: a refusal that read the
// launch trace, joined its `session-id`s against this goal's own store, and DECLINED to run a goal
// carrying execution evidence its store could not account for. Its own pointer comment said it
// retires when the lane-independent record lands, and the record has landed — so it is DELETED
// rather than left as a second, weaker answer to the question `executions.csv` now answers.
//
// WHAT REPLACES IT, and why the replacement is not a refusal at all: the guard refused a goal
// BECAUSE it could not tell which seats the other lane had finished. The record tells it — by seat,
// with the outcome, in the goal folder both lanes already write to — so the crossover is RESUMED
// instead of refused: the finished seats are skipped, the rest run here. The probe arms that
// measured the refusal now measure the resume, in both directions
// (probes/probe-cross-lane-resume.js § D4).
//
// ⚠ THE ONE CASE THE GUARD COVERED THAT THE RECORD DOES NOT, stated rather than quietly dropped: a
// seat run BY HAND in a tmux sitting writes a `sessions.csv` row and NO execution record row, so it
// is invisible to the record and the seat will be re-run. That is the same bound every "the work
// happened somewhere nothing recorded it" case has, and it is now the ONLY one — the guard's other
// case (a real lane) is answered rather than refused. A hand-run seat that must not be re-run is
// closed the way any lane closes one: by an outcome row in the record.

// ── ONE RUNNER PER GOAL, ENFORCED (review finding 1, wave-B review) ───────────────────────────
//
// Everything below assumed a premise nobody enforced: that one attached run owns a goal at a time.
// The store's `E_SECOND_WRITER` guard is an in-PROCESS singleton and a second process opens the
// same sqlite file happily, so two runners on one goal produced a measured harm — runner B read
// runner A's LIVE foreground row, applied the reconciliation's premise ("non-terminal ⇒ its runner
// is gone", true for ONE runner and no more), ended A's row, and told the operator to
// `--relaunch alpha` — starting a second session for a seat a human was working in. A's own
// turn-end then silently rewrote the row B had written. Loud in neither direction.
//
// So the premise is now a PRECONDITION rather than an assumption, and the cheapest thing that
// holds it is a pidfile the runner's own death clears:
//   · CREATED O_EXCL (`flag: 'wx'`) — the atomicity is the filesystem's, not a check-then-write.
//   · REMOVED on the way out, on the normal path and on a signal; and only if it is still OURS
//     (the content is compared), so a runner can never delete a successor's lock.
//   · A STALE LOCK IS DETECTED, NEVER MANUAL. `kill(pid, 0)` plus the pid's START TIME answers
//     "is that runner still there" — the start time is what keeps a RECYCLED pid from bricking a
//     goal forever, which is the one failure mode a lock file must not have. Unreadable start
//     time degrades to the pid alone rather than refusing.
// PRIN-11 holds: nothing here is state the system reads to decide anything. It is a liveness
// interlock that cannot survive the process it names.
const RUN_LOCK = '.attached-run.lock';

// /proc/<pid>/stat fields, read from AFTER the comm field's closing paren — the comm can contain
// spaces and parens, so a plain split() on the whole line is the classic wrong answer. Index 0 of
// what this returns is field 3, so field N is index N-3.
function procStatFields(pid) {
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    return stat.slice(stat.lastIndexOf(')') + 2).split(' ');
  } catch { return null; }   // not Linux, or the process is gone — the caller degrades, not fails
}

// Field 22 — the process start time, in clock ticks since boot.
function processStartTime(pid) {
  const f = procStatFields(pid);
  return (f && f[19]) || null;
}

// Field 7 — the NUMERIC `tty_nr` of the controlling terminal (0 = none). Numeric, not the
// `/dev/pts/N` path, because that is what `coord.py pane_identity` records in this column and the
// seat-identity gate corroborates against: two spellings of one column would read as a mismatch on
// every seat.
function processTtyNr(pid) {
  const f = procStatFields(pid);
  return (f && f[4]) || '';
}

function runnerAlive(pid, startTime) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
  } catch (err) {
    // EPERM means a process with that pid EXISTS and is not ours to signal — alive.
    if (err.code !== 'EPERM') return false;
  }
  const nowStart = processStartTime(pid);
  // Both known and different ⇒ the pid was recycled and the runner that wrote this lock is gone.
  if (startTime && nowStart && startTime !== nowStart) return false;
  return true;
}

function acquireRunLock(goalFolder, { pid = process.pid } = {}) {
  const lockPath = path.join(goalFolder, RUN_LOCK);
  const payload = `${pid} ${processStartTime(pid) || ''}\n`;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      fs.writeFileSync(lockPath, payload, { flag: 'wx' });
      return {
        lockPath,
        release() {
          // Ours or nobody's: a runner that overran its lock must not remove a successor's.
          try { if (fs.readFileSync(lockPath, 'utf8') === payload) fs.unlinkSync(lockPath); } catch { /* already gone */ }
        },
      };
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
      let held = '';
      try { held = fs.readFileSync(lockPath, 'utf8'); } catch { held = ''; }
      const [pidRaw, startRaw] = held.trim().split(/\s+/);
      const holder = Number(pidRaw);
      if (runnerAlive(holder, startRaw)) {
        throw new Error(
          `REFUSING TO RUN: another attached run is live on this goal (pid ${holder}), and two ` +
          `runners on one goal is a measured harm rather than a race worth risking — the second ` +
          `one reads the first's LIVE foreground row as an orphan, ends it, and invites you to ` +
          `relaunch a seat someone is sitting in. Wait for it, or stop it. ` +
          `Lock: ${lockPath}. (A lock whose runner is GONE is cleared automatically — this one's ` +
          `is not: it answered kill(0) and its start time still matches.)`
        );
      }
      // Stale — the runner that wrote it is gone. Clear it and take the lock; ONE retry, so a
      // genuine race with a third process refuses rather than spinning.
      try { fs.unlinkSync(lockPath); } catch { /* another starter won the clear; the retry decides */ }
    }
  }
  throw new Error(
    `REFUSING TO RUN: could not take ${lockPath} — it was created again between clearing a stale ` +
    `lock and taking it, which means another run is starting right now. Try again.`
  );
}

// ── The FOREGROUND CARRIER (console-run design ruling 1) ──────────────────────────────────────
//
// The engine stays the ONLY DAG-advancer. What changes for a seat matching ruling 5's two gates is
// the CARRIAGE, and nothing else: instead of a detached caged child the engine launches that seat's
// harness session as a FOREGROUND child of this process, sharing the runner's terminal, and the
// tick loop BLOCKS until it exits. It is a spawn variant — no hold state, no release, no second
// advancement path.
//
// FOUR things this owns, each with a reason it could not be somewhere else:
//
//  1. THE PREDICATE IS THE CHAT BRIDGE'S, both gates. `seatIsHumanInteractive` + `goalExecutionMode`
//     from `bridges/chat/bus-ferry.js` — the SAME readers the status verb and the message gate use.
//     A second implementation of "does this seat need the owner" is a system that holds a seat the
//     status surface says is free.
//  2. THE COMMAND IS THE PROFILE'S `headed.tui` BLOCK, not a filtered `exec:`. `exec:` is the
//     HEADLESS template (`-p --output-format stream-json`) and stripping flags off it to make an
//     interactive one is exactly the second interpreter of the one config that DEC-1 forbids. A
//     profile that declares no `headed.tui` is REFUSED, naming the seat and the profile: the
//     headed block IS the declaration that this profile can carry a human (D17).
//     ⚠ KNOWN BOUND, disclosed rather than papered over: the shipped claude profiles declare
//     `headed.tui: { argv: ["claude"] }`, which binds the HARNESS but pins no `--model`. So the
//     foreground seat runs the harness's default model, not the profile's. Fixing it is a one-line
//     change per profile in `config/spawn-profiles.yaml` with daemon-headed blast radius, and is
//     filed rather than smuggled in here.
//  3. NO CAGE. Accepted bound (console-run § Cautions): a session sharing the owner's terminal has
//     neither bwrap nor a systemd slice — the same bound d1's hand-run elicitator had. The
//     detached seats of the same run are caged exactly as before.
//  4. THE TURN IS ENDED FROM THE CHILD'S EXIT CODE, which is this lane's EXISTING rule and not a
//     new one: `ticker.js`'s exit sweep already records `exitCode === 0 ? 'done' : 'failed'` for
//     every seat it observes ending. Turn and session are ended in ONE act
//     (`endTurnAndCloseSession`, G-225) so no crash can leave a terminal turn under a live session.
const FOREGROUND_ENQUEUER = 'attached-foreground';

// The two gates, read ONCE per run. Returns a `(seat) => boolean`; when the goal is not in
// `interactive` execution mode NOTHING is held, and the per-seat file is never read at all.
function heldSeatPredicate(goalFolder) {
  const { goalExecutionMode, seatIsHumanInteractive, INTERACTIVE_MODE } =
    require('../bridges/chat/bus-ferry');
  const workspaceRoot = path.resolve(goalFolder, '..', '..', '..');
  if (goalExecutionMode(workspaceRoot, path.basename(goalFolder)) !== INTERACTIVE_MODE) {
    return () => false;
  }
  return (seat) => seatIsHumanInteractive(goalFolder, seat);
}

// The default carriage: a foreground child on THIS terminal. `stdio: 'inherit'` is the whole
// mechanism — the harness gets the runner's real tty, which is why the entry skill hands the user a
// command to TYPE rather than calling it from inside a session (console-run § Cautions).
function spawnForegroundInTerminal(argv, cwd) {
  return spawnSync(argv[0], argv.slice(1), { cwd, stdio: 'inherit' });
}

// ── S-20 · THE FOREGROUND SEAT'S LAUNCH TRACE (owner ruling #d-s20-foreground-seat-writes-session-row)
//
// A terminal-carried seat IS a launched session, so it writes the goal's `sessions.csv` row like any
// other launch. Before this, the row was written only by the daemon spawn path (`spawn.js`, task
// 7.75's at-dispatch record) — which this carriage deliberately does not go through — so a package
// whose seats were ALL carried in the terminal was traceless, and the edge-runner's check-out fast
// path refuses a traceless package wholesale. That case now disappears rather than gaining a carve-out.
//
// SAME SCHEMA, SAME MOMENT, SAME KEY as the daemon's row, deliberately:
//   · written IN THE DISPATCHING ACT, before the child starts — never post-hoc, never inferred.
//   · keyed by the SAME `session_id` this seat's `jobs_log` row carries, which is what task 7.73's
//     join reads. That join is also what makes the row IDENTIFIABLE AS FOREGROUND without a new
//     column: its execution carries `enqueued_by = attached-foreground`.
//   · appended BY COLUMN NAME against the file's own header (`seat-identity/csv.js`), so a reordered
//     or widened trace keeps receiving correct rows.
//
// THE IDENTITY PAIR IS THE RUNNER'S, and that is the coord.py `pane_identity` rule applied here
// rather than a shortcut: the gate matches a registered pid against the CALLER'S ANCESTRY, and every
// process this seat runs is a descendant of `rbtv run`. Recording the child's pid is impossible in
// any case — `spawnSync` yields it only after the child is dead. `tty` is therefore non-empty and
// non-zero exactly when the run has a real terminal, which is the second, human-readable mark of a
// foreground row: the daemon's at-dispatch row always writes it empty.
//
// THE HEADER IS NOT SPELLED HERE, AND NEITHER IS THE ACT THAT ASKS FOR IT (7.628). `coord.py` owns
// this schema (`SESSIONS_COLS`, task 7.37) and is asked for it at run time, only where the append
// has ALREADY refused for want of one — through `spawn.js`'s `appendRowEnsuringHeader`, now IMPORTED
// rather than copied. The copy that stood here duplicated the MECHANISM, never the schema, and only
// because `spawn.js` was another session's dirty file at that build's moment.
function appendForegroundSessionRow({ goalFolder, seat, sessionId, harness, model, workdir, logger = null }) {
  const csvPath = path.join(goalFolder, SESSIONS_CSV);
  const values = {
    'session-id': sessionId,
    seat,
    harness: harness || '',
    // The model that ACTUALLY launched (ruling D19's prevention guarantee), on the same terms as
    // the daemon door's row: OFFERED to `appendRowEnsuringHeader`, which writes by column name and
    // REPORTS an unknown key as `dropped` rather than inventing a column. `coord.py#SESSIONS_COLS`
    // owns this schema, so a deployment whose header lacks `model` is unaffected.
    model: model || '',
    workdir,
    pid: String(process.pid),
    'pid-starttime': processStartTime(process.pid) || '',
    tty: processTtyNr(process.pid),
    started: isoNow(),
  };
  const warn = (message, extra) => {
    if (logger) logger({ level: 'warn', message, seat, sessionsCsv: csvPath, sessionId, ...extra });
  };
  try {
    // The lazy require is the shape this file already uses for every `server/spawn/` reach
    // (`composeArgv`, `generateSessionId` below): the daemon subtree is relocatable, so nothing
    // here holds a LOAD-time dependency on it.
    const { appendRowEnsuringHeader } = require('../server/spawn/spawn');
    const written = appendRowEnsuringHeader(csvPath, values,
      (level, message, extra) => {
        if (logger) logger({ level, message, seat, sessionsCsv: csvPath, sessionId, ...extra });
      });
    if (!written.appended) {
      warn('foreground session row NOT recorded — this seat will be UNATTRIBUTABLE', { reason: written.reason });
      return written;
    }
    if (written.appended && written.dropped.length && logger) {
      logger({ level: 'warn', message: 'session log lacks columns; they were dropped, not invented (task 7.37 owns the schema)', seat, sessionsCsv: csvPath, dropped: written.dropped });
    }
    return written;
  } catch (err) {
    // NEVER fatal, for the daemon door's own reason: the seat is about to own this terminal, and
    // refusing the launch over its trace would be a worse outcome than an unattributable session.
    warn('foreground session row append failed — this seat will be UNATTRIBUTABLE', { error: err.message });
    return { appended: false, reason: err.message, dropped: [] };
  }
}

// ── THE CLOSE HALF OF THAT ROW (review F2) ────────────────────────────────────────────────────
//
// A row is OPENED by the launch and CLOSED by `coord.py session_close` — and a console-lane seat
// can never reach that closer: `checkIdentity` refuses it `E_GOAL_NOT_LIVE` (there is no tmux room
// on this lane). So the opened row stayed open forever, and `goal-state-job`'s `open_session_seats`
// — *"rows whose `ended` cell is EMPTY"* — reported every FINISHED foreground seat as a live-or-
// crashed sitting for the rest of the goal's life. A new false divergence signal, created by the
// row we added; the row needs its closer or it should not exist.
//
// THE CARRIER IS THE ONE HONEST WITNESS. It blocks on the child, so it OBSERVES the termination —
// which is exactly the fact `coord.py` reserves the value `exited` for: *"the kit attesting that a
// harness terminated, a fact a seat cannot witness about itself"* (`RECORD_DISPOSITION_WRITER`:
// `exited` belongs to the `kit`). So:
//   `ended`              stamped, which is what closes the sitting
//   `disposition`        `exited` — NEVER `done`. `done` is the seat reporting its own work
//                        finished, which no exit code can assert; `exited` marks NOT-done for every
//                        reader (edge-runner: `renew`/`revive`/`exited` do not advance the fast
//                        path), so nothing is advanced on an attestation nobody made.
//   `disposition-writer` `kit`, the pair the value was validated against.
// The child's exit CODE is not a column of this schema and is not invented into one: it is already
// on the `jobs_log` row this session id joins to (`done` / `failed`, written a few lines below).
//
// IT ONLY EVER CLOSES **OUR OWN OPEN ROW** — matched by session id, and skipped if `ended` is
// already set. A seat that somehow did reach `coord`'s closer keeps that closer's values (`done`,
// writer `seat`); this never overwrites another writer's outcome, the same posture the execution-row
// guard below takes.
//
// ponytail: read-modify-write of the whole file, UNLOCKED — `coord.py` guards this file with a
// python `coord_lock` that has no JS binding, and the daemon's own append door takes no lock either.
// The window is one `readFileSync`/`writeFileSync` pair while the ticker is frozen (nothing else in
// this run can append), so a concurrent append would have to come from another lane. Upgrade path:
// a JS binding for `coord_lock`, or a coord verb this carrier can call.
const FOREGROUND_DISPOSITION = 'exited';
const FOREGROUND_DISPOSITION_WRITER = 'kit';

function closeForegroundSessionRow({ goalFolder, sessionId, logger = null }) {
  const csvPath = path.join(goalFolder, SESSIONS_CSV);
  try {
    const { splitRow, quoteField } = require('../server/seat-identity/csv');
    const raw = fs.readFileSync(csvPath, 'utf8');
    const lines = raw.split('\n');
    const header = splitRow(lines[0]).map((h) => h.trim());
    const at = (name) => header.indexOf(name);
    if (at('session-id') < 0 || at('ended') < 0) return { closed: false, reason: 'trace has no session-id/ended column' };
    for (let i = 1; i < lines.length; i += 1) {
      if (!lines[i].length) continue;
      const cells = splitRow(lines[i]);
      while (cells.length < header.length) cells.push('');
      if ((cells[at('session-id')] || '').trim() !== sessionId) continue;
      if ((cells[at('ended')] || '').trim()) return { closed: false, reason: 'already closed by another writer' };
      cells[at('ended')] = isoNow();
      if (at('disposition') >= 0) cells[at('disposition')] = FOREGROUND_DISPOSITION;
      if (at('disposition-writer') >= 0) cells[at('disposition-writer')] = FOREGROUND_DISPOSITION_WRITER;
      lines[i] = header.map((_, c) => quoteField(cells[c])).join(',');
      fs.writeFileSync(csvPath, lines.join('\n'), 'utf8');
      return { closed: true, disposition: FOREGROUND_DISPOSITION };
    }
    return { closed: false, reason: 'no open row for this session id' };
  } catch (err) {
    // Same posture as the open half: loud, never fatal. An unclosed row is a false divergence
    // signal, not a reason to fail a seat whose work is already done.
    if (logger) logger({ level: 'warn', message: 'foreground session row NOT closed — goal-state will report this finished seat as an open sitting', sessionsCsv: csvPath, sessionId, error: err.message });
    return { closed: false, reason: err.message };
  }
}

function nextHeldReadySeat(heartStore, rows, isHeld, relaunch, view = null, ready = null) {
  const byJob = executionsByJob(heartStore, relaunch);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  // `notFinished` rides along, or the carrier would pick up a seat the record holds (`blocked` on
  // the owner, or open in another lane) — the ONE predicate must answer the same way at every one
  // of its call sites, which is why it is one predicate. `ready` is COORD's answer, handed in for
  // the same reason (§ D1): the carrier may not promote a seat this lane's store merely has no row
  // for, and with no coord answer in hand it carries nothing.
  const opts = {
    done: view && view.done, foreign: view && view.foreign, notFinished: view && view.notFinished, ready,
  };
  return rows.find((row) => isHeld(row.seat) && seatState(row, byJob, queued, opts) === 'ready') || null;
}

function runForegroundSeat({
  heartStore, seat, goalFolder, tick, now,
  // The whole (harness, model) -> launch-spec table. The seat's own cast selects from it and there
  // is no second candidate: `#d-abolish-profile-names` deleted the caller's name at this door as
  // at the other two. An UNCAST seat refuses with `E_UNCAST_SEAT`, an unmappable one with
  // `E_UNMAPPED_BINDING`. The default `{}` is an EMPTY table, not a bypass — it refuses everything.
  launchSpecs = {},
  spawnForeground = spawnForegroundInTerminal, logger = null,
}) {
  const seatDir = path.join(goalFolder, 'seats', seat);
  // ── THE SEAT'S CAST IS THE ANSWER HERE TOO (task 7.54 · D19 · 7.787) ────────────────────────
  // The THIRD launch door, and it shares the shape exactly: a seat folder, and both records
  // written from whatever this function decides. Resolved BEFORE the headed check below, so the
  // capability gate validates the spec that will actually carry the human — a seat cast as one
  // model must not open a terminal on another.
  const { launchSpecForSeat } = require('../server/spawn/spawn');
  const { key: profileName, spec: profile } = launchSpecForSeat(launchSpecs || {}, seatDir,
    (level, message, extra) => { if (logger) logger({ level, message, seat, ...extra }); });

  if (!profile.headed || !profile.headed.tui) {
    throw new Error(
      `seat ${seat} is held for you (it declares human-interactive: and this goal runs in ` +
      `interactive execution mode), so it must run in YOUR terminal — but launch spec ` +
      `'${profileName}' declares no headed.tui block, which is the declaration that a spec can ` +
      `carry a human (D17). REFUSING rather than composing an interactive command out of the ` +
      `headless \`exec:\` template: a second interpreter of the one launch-spec config is the drift ` +
      `DEC-1 § Shared launch-spec source exists to prevent.`
    );
  }
  const { generateSessionId } = require('../server/spawn/carrier');
  const { composeArgv } = require('../server/spawn/spawn');

  const sessionId = generateSessionId();
  // mode `headed` selects `profile.headed.tui`; the descriptor injection
  // (`--append-system-prompt-file <seatDir>/seat.md`, claude-only and file-conditional) rides along
  // from the ONE composer every launch already uses.
  const { argv } = composeArgv(profile, 'headed', sessionId, seatDir, null, null);

  const exec = heartStore.recordExecutionStart({
    jobId: jobIdFor(seat),
    actionType: 'launch-agent',
    args: JSON.stringify({ workdir: seatDir }),
    // The marker the boot reconciliation below keys on. A row carrying it was a child of A
    // TERMINAL-BOUND RUNNER, which is what makes "this row is non-terminal at boot ⇒ its process is
    // gone" an observation rather than a guess.
    enqueuedBy: FOREGROUND_ENQUEUER,
    sessionMode: 'headed',
    firedTick: tick,
    firedAt: now,
    sessionId,
    profile: profileName,
    workdir: seatDir,
  });
  if (logger) logger({ level: 'info', message: 'foreground seat — your terminal is now this seat\'s session', seat, argv: argv.join(' ') });

  // S-20: the launch trace row, in the dispatching act, before the child owns the terminal.
  const { harnessOf } = require('../server/spawn/harness-config');
  const { bindingOf } = require('../launch-profiles/catalog');
  appendForegroundSessionRow({
    goalFolder, seat, sessionId, harness: harnessOf(profile),
    model: (bindingOf(profile) || {}).model, workdir: seatDir, logger,
  });
  // S-23: and the goal's EXECUTION RECORD, in the same act. Written here rather than left to the
  // per-tick publish for one reason that is specific to this carriage: this call BLOCKS for as long
  // as the human works, so the publish pass does not come round again until the seat is over. The
  // other lane must be able to see, while that is happening, that this seat is taken.
  openExecution({
    goalFolder, seat, sessionId, lane: laneOf(heartStore.dbPath, goalFolder), startedAt: isoNow(),
  });

  const res = spawnForeground(argv, seatDir) || {};
  const exitCode = typeof res.status === 'number' ? res.status : null;
  const ok = exitCode === 0;

  // …and its CLOSE half, from the one witness of the termination. Before the execution row is
  // touched: an unclosed trace row is what makes a finished seat read as an open sitting forever.
  closeForegroundSessionRow({ goalFolder, sessionId, logger });
  // The record's outcome, from the same witness. The TRACE says the process ended (`exited` — a
  // fact about a process, which is all an exit code can attest); the RECORD says what became of the
  // WORK, in the store's own turn vocabulary. That is the `done`-vs-`exited` divergence dissolving:
  // two surfaces, two questions, one answer each (#d-s23-single-execution-record-now).
  const carriedOutcome = processOutcome(ok ? 'done' : 'failed');
  closeExecution({ goalFolder, sessionId, outcome: carriedOutcome, endedAt: isoNow() });
  // ⚠ NO HOLD IS DECIDED HERE ANY MORE (W2). This site used to call `outcomeForSeat`, which read
  // the goal's bus and the ferry's gates to decide whether a carried seat's `done` should publish
  // as `blocked`. That whole derivation is deleted: the outcome is a fact about the process this
  // carriage just watched exit, and whether the WORK is done is the seat's own check-out, which
  // coord reports as a disposition. A held seat surfaces as coord's `HELD` verdict on the next
  // pass's `ready-seats`, which this loop already reads.

  // ⚠ SOMEONE ELSE MAY HAVE ENDED OUR ROW WHILE THE HUMAN WORKED (review finding 1, second half).
  // The run lock makes that unreachable now; this stays because the alternative to noticing is
  // OVERWRITING — `updateExecutionStatus` is an unconditional UPDATE, so a terminal row written by
  // another writer would be silently replaced by ours and the disagreement would leave no trace
  // anywhere. Refuse the write and SAY SO; the row is terminal either way, so the DAG still moves.
  const current = heartStore.getExecution(exec.exec_id);
  if (current && TERMINAL_TURN_STATUSES.includes(current.status)) {
    const message = `foreground seat ${seat}: its execution row was already ended '${current.status}' by `
      + `another writer while the session ran — REFUSING to overwrite it with '${ok ? 'done' : 'failed'}'. `
      + `Two writers on one goal's store is what the run lock exists to prevent; if you see this, one got past it.`;
    if (logger) logger({ level: 'warn', message, seat, execId: exec.exec_id, foreignStatus: current.status });
    return { seat, execId: exec.exec_id, argv, exitCode, signal: res.signal || null, status: current.status, foreignTerminal: current.status };
  }

  heartStore.endTurnAndCloseSession(exec.exec_id, {
    turnStatus: ok ? 'done' : 'failed',
    sessionStatus: ok ? 'closed' : 'crashed',
    endedAt: new Date(),
    exitCode,
    reason: ok ? null : `foreground seat ${seat} ended ${res.signal ? `on ${res.signal}` : `with exit ${exitCode}`}`,
  });
  return { seat, execId: exec.exec_id, argv, exitCode, signal: res.signal || null, status: ok ? 'done' : 'failed' };
}

// ── The crash edge, resolved at BOOT (console-run § Cautions: "B1's hardest edge") ────────────
//
// A foreground seat killed mid-work — Ctrl-C, a SIGKILL on the runner, a closed terminal — leaves
// an execution row that nobody ended, because the process that would have ended it died with the
// child. THIS is the disposition, and it is deliberately NOT a re-enqueue: seeding is create-only,
// and re-firing a seat because its row looks unfinished is the false-relaunch the create-only rule
// exists to prevent.
//
// The row is ended `failed` / session `crashed` — the same pair the ticker writes for any process
// it observed ending badly — and the run then treats that seat as it treats any failed seat: it
// REFUSES to advance past it and names it. Running it again takes an explicit human act, the
// one-shot relaunch grant (`--relaunch <seat>`).
//
// ── W1 (adv, C12) · THE TWO CLOSERS, AND WHY NEITHER SUBSUMES THE OTHER ───────────────────────
//
// W1 gave the daemon lane a session-closer (`coordinate attest-exit --session … --force-dead`,
// called from `spawn.js#closeSeatSessionRow`). That is a SECOND thing that closes `sessions.csv`
// rows, and this lane already had one — `closeForegroundSessionRow` above. Two closers over one
// file is worth stating rather than discovering, so: the risk is NOT double-close (both skip a row
// whose `ended` is already stamped), it is the two writing DIFFERENT values for one ending.
//
//   THEY CANNOT COLLIDE ON A ROW. The daemon closer is reached only from the ticker's enforce
//   sweep and from `kill()`. Enforce starts from a turn that is still in flight; a foreground
//   turn's row is ended and its session closed IN THE SAME CALL the carrier makes the moment its
//   blocking child returns, before any tick can look — and the runner's tick loop cannot even run
//   while that child holds the terminal. Different stores, besides: this lane's is `<goal>/heart.db`.
//
//   THEY CANNOT DISAGREE ON A VALUE, TODAY. The daemon closer's value comes from the seat's own
//   `awaiting-close.json` declaration and falls back to `exited` when nobody declared — and on THIS
//   lane nobody can: a console-lane seat's check-out is refused `E_GOAL_NOT_LIVE` (there is no tmux
//   room), which is the very reason the constant below exists. So both closers write `exited`.
//
// ⚠ TRIPWIRE — the second paragraph is a fact about TODAY, not a law. The day a console-lane seat
// can check out, `FOREGROUND_DISPOSITION` starts overwriting a real declaration with `exited`, and
// THAT is disposition skew manufactured by this file. At that moment this function and its sibling
// must route through the one coord closer instead (the upgrade path `closeForegroundSessionRow`'s
// own ponytail note already names). It is not done pre-emptively: it would trade an in-process
// write for a python subprocess on the lane where the owner watches it run, to fix nothing yet.
//
// ⚠ WHAT IS *NOT* FIXED HERE, AND WHY IT IS LEFT STANDING. This function ends the STORE rows and
// closes NO `sessions.csv` row, so an interrupted foreground seat leaks an open sitting forever —
// F3 on the attached lane. The one-line fix (call `closeForegroundSessionRow` for each row before
// ending it) was WRITTEN AND REVERTED inside W1's build: measured 2026-08-13, it turns
// `probe-foreground-carrier` from PASS to FAIL on three checks (B1e's explicit `--relaunch`, B1f's
// re-open-by-grant view), because stamping `ended`+`exited` on that row changes what coord's
// readiness view says about the seat — a real behaviour change through the relaunch path that W1
// neither scoped nor land-tests. It is a follow-up with its own acceptance, not a rider.
function reconcileForegroundOrphans(heartStore, { logger = null, endedAt = new Date() } = {}) {
  const ended = [];
  for (const status of LIVE_TURN_STATUSES) {
    for (const row of heartStore.listExecutionsByStatus(status)) {
      if (row.enqueued_by !== FOREGROUND_ENQUEUER) continue;
      heartStore.endTurnAndCloseSession(row.exec_id, {
        turnStatus: 'failed',
        sessionStatus: 'crashed',
        endedAt,
        reason: `foreground seat left ${status} by a runner that is gone — a foreground child cannot ` +
                `outlive the terminal it was attached to, so this row is dead by construction`,
      });
      ended.push(row.job_id);
      if (logger) logger({ level: 'warn', message: 'reconciled an interrupted foreground seat', jobId: row.job_id, was: status });
    }
  }
  return ended;
}

// ── The exit condition — the registry's own sentence, made checkable ──────────────────────────
//
// "returns on completion or on ANY worker question". Both halves are read from the store:
//   COMPLETE — every seat has a finished execution, the queue is empty, and no turn is live.
//   QUESTION — an UNANSWERED `ask` exists.
//
// ⚠ THE QUESTION HALF USED TO BE `!seenAskIds.has(...)` OVER A PER-LOOP SET THAT NOTHING EVER
// ADDED TO, so an ask correlated with nothing: the first ask a run ever recorded ended EVERY later
// run at its first tick, forever, including one whose answer had already been written while the run
// was down. The set is deleted rather than populated — `unansweredAsks()` is the correlation the
// status verb already does (greedy thread pairing in msg_id order), and one correlation shared by
// the surface that REPORTS a question and the loop that STOPS on it is the only way the two can
// agree about what is open.
function evaluateExit(heartStore, rows, relaunch = null, view = null, ready = null) {
  const asks = unansweredAsks(heartStore.dump().messages);
  if (asks.length) {
    return { done: true, reason: 'question', asks };
  }

  const live = LIVE_TURN_STATUSES.flatMap((s) => heartStore.listExecutionsByStatus(s));
  if (live.length) return { done: false, live: live.length };
  if (heartStore.listQueue().length) return { done: false, live: 0 };

  const byJob = executionsByJob(heartStore, relaunch);
  // FINISHED IS THE RECORD'S ANSWER, then this store's own — the same union `seatState` takes, so
  // "is this run complete" cannot disagree with "is this seat done" (a goal whose remaining seats
  // were finished in the OTHER lane is complete, and says so instead of reporting them unfinished).
  const done = view && view.done;
  const foreign = view && view.foreign;
  // THE RECORD'S LAST WORD, honoured by the SAME union `seatState` takes (ruling
  // #d-block-and-queue-mechanical-hold): a seat whose last row is `blocked` or still open is not
  // finished here either, whatever this store's own turn says. Both lanes, one rule — an exit
  // condition that disagreed with the eligibility predicate would call a run complete while the
  // wave is held.
  const notFinished = view && view.notFinished;
  const isFinished = (seat) => !(notFinished && notFinished.has(seat))
    && ((done && done.has(seat)) || seatIsFinished(byJob.get(jobIdFor(seat))));
  const unfinished = rows.filter((r) => !isFinished(r.seat));
  if (unfinished.length === 0) return { done: true, reason: 'complete' };

  // Nothing live, nothing queued, and seats still unfinished. Either a dependency chain is
  // BLOCKED (a seat whose `after` failed) or every remaining seat is waiting on one that will
  // never finish. Say so and stop, rather than spin: an attached run that cannot advance must
  // return to its caller, which is a terminal with a person at it.
  // A seat the RECORD holds for another lane cannot be advanced from here either — and it must be
  // counted with the stuck ones rather than left to the `{done:false}` fall-through, which would
  // spin this loop every 10s forever waiting on a lane whose progress does not arrive through us.
  const stuck = unfinished.filter((r) => {
    if (foreign && foreign.has(r.seat)) return true;
    // A seat BLOCKED ON THE OWNER cannot advance from here either, and it must be counted with the
    // stuck ones rather than falling through to the `seat-failed` arm below — it did not fail, it
    // is waiting, and `blocked` is the reason word this function already has for exactly that.
    if (view && view.blocked && view.blocked.has(r.seat)) return true;
    // A seat that RAN and did not finish is NOT stuck — it is FAILED, and the arm below is what
    // says so. Kept explicit because coord does not offer such a seat either, so without this line
    // every failed seat would report as `blocked` and the two reason words would collapse into one.
    if (seatHasRun(byJob.get(jobIdFor(r.seat)))) return false;
    // THE SAME ANSWER THE ELIGIBILITY PREDICATE USES, from the same place: coord's (§ D1). A seat
    // coord does not offer as READY cannot be advanced from here — its `after` is unmet, its guard
    // has not discharged, or its own last session ended UNDECLARED. No `after` grammar is read in
    // JavaScript, so this loop and the enqueue pass can no longer disagree about what a cell means.
    //
    // ⚠ NO COORD ANSWER (a refusal, a SKEW, no python) MAKES EVERY UNFINISHED SEAT STUCK, and the
    // run ENDS `blocked` naming them rather than spinning every 10s on a computation that is
    // refusing. That is the same direction the refusal takes in the seeding pass: never proceed off
    // an answer nobody has.
    return !(ready && ready.has(r.seat));
  });
  // WHICH OF THEM A GRANT COULD ACTUALLY RELEASE, computed here because this is where the holds are
  // already in hand. It is exactly the set `recordView`'s grant loop deletes from — a seat held by
  // the record (somebody else's row, an open row, `blocked` on the owner) — and deliberately NOT
  // every unfinished seat: a seat whose `after` is unmet is not offered by coord either way, so
  // naming it in the remedy would send an operator to spend a grant that changes nothing.
  const grantable = (rs) => rs.filter((r) => (foreign && foreign.has(r.seat))
    || (notFinished && notFinished.has(r.seat))).map((r) => r.seat);
  if (stuck.length === unfinished.length) {
    return {
      done: true, reason: 'blocked', unfinished: unfinished.map((r) => r.seat),
      grantable: grantable(unfinished),
    };
  }

  // A seat that HAS RUN and did not finish — a failed detached child, or a foreground seat the
  // reconciliation above ended. Nothing is live, nothing is queued and its dependency is satisfied,
  // so no future tick can change its state: the loop would otherwise spin here every 10s forever,
  // which is what it did. Returning is not a retry decision — the seat runs again only on an
  // explicit `--relaunch`, never because the loop came back around.
  const failed = unfinished.filter((r) => seatHasRun(byJob.get(jobIdFor(r.seat))));
  if (failed.length) {
    // Every one of these IS grantable: it has an execution row in THIS store and nothing else, so
    // hiding that row is precisely what a grant does (`executionsByJob`).
    return { done: true, reason: 'seat-failed', unfinished: failed.map((r) => r.seat), grantable: failed.map((r) => r.seat) };
  }
  return { done: false, live: 0 };
}

// ── The status verb — orientation, READ-ONLY, and it works daemon-down ────────────────────────
//
// The console-run design's ruling 2: resume orientation is DERIVED, never stored. No new state
// file, no breadcrumb, no session-maintained doc — everything below is computed from
// `taskforce.csv`, the goal's own `heart.db` (when one exists), the seat descriptors, and the
// `execution-mode` file.
//
// THREE things it must not do, each a real hazard rather than a style note:
//   1. It must not CREATE `heart.db`. Opening the store creates and migrates it, so a status call
//      before the first run would leave a store behind — and "has this goal ever run?" would be
//      unanswerable from disk forever after. The file is opened only if it already exists.
//   2. It must not write ANYTHING else. A read-only verb that dirties the goal folder cannot be
//      run while a review or a run is measuring that folder.
//   3. It must not enqueue. It shares the predicate with the enqueue pass; it does not share the
//      pass.
//
// HELD-FOR-USER is ruling 5's two-gate predicate, not a third spelling of it: the seat declares
// `human-interactive:` in its descriptor AND the goal's execution mode is `interactive`. Both
// readers are the chat bridge's own (`bridges/chat/bus-ferry.js`) so the status surface and the
// gate that actually parks a message can never drift apart.
// Which `ask` rows are still WAITING. Asks and answers correlate by `thread` — the chat bridge
// writes the reply to a pending ask as an `answer` on the chain's own thread
// (bridges/chat/forward-path.js) — and nothing marks the ask row itself. Without this every
// answered question printed under UNANSWERED QUESTIONS forever, which trains the reader to
// ignore the section that exists to be read.
//
// GREEDY PAIRING IN msg_id ORDER, not "an answer exists on this thread": a thread can carry two
// asks and one answer, and the cheap test would call BOTH answered. It errs toward hiding an
// unanswered question, which is the one direction this surface must never err in. `messages` is
// already ordered by msg_id (heart-store dump), and msg_id is the autoincrement, so the nth
// answer on a thread pairs with the nth ask before it.
function unansweredAsks(messages) {
  const pending = new Map();   // thread -> [ask rows, oldest first]
  const out = [];
  for (const m of messages) {
    if (m.type === 'ask') {
      const list = pending.get(m.thread) || [];
      list.push(m);
      pending.set(m.thread, list);
    } else if (m.type === 'answer') {
      const list = pending.get(m.thread);
      if (list && list.length) list.shift();   // answers the OLDEST open ask on this thread
    }
  }
  for (const list of pending.values()) {
    for (const a of list) out.push({ msgId: a.msg_id, sender: a.sender, thread: a.thread, corpus: a.corpus });
  }
  return out.sort((x, y) => x.msgId - y.msgId);
}

function statusAttached({ goalFolder: goalFolderInput, openStore = null }) {
  const goalFolder = resolveGoalFolder(goalFolderInput);
  const tfPath = path.join(goalFolder, TASKFORCE);
  if (!fs.existsSync(tfPath)) {
    throw new Error(
      `${tfPath}: no taskforce — this goal folder has no seats yet. Materialize the workflow ` +
      `into it first; there is nothing to report on.`
    );
  }
  const rows = readCsv(tfPath).filter((r) => r.seat);

  const storePath = path.join(goalFolder, STORE_FILENAME);
  const everRun = fs.existsSync(storePath);
  let byJob = new Map();
  let queued = new Set();
  let asks = [];
  // THE COMPLETION AUTHORITY, and it is read with or without a store: `--status` answers "what is
  // done" from the goal's execution record, so it reports a seat the DAEMON finished (or is running
  // right now) on a goal this lane has never opened a store for — `everRun` false, seats already
  // `done`/`live`. With no store, nothing in the record is ours, which is exactly what is true.
  // THE READINESS ANSWER IS COORD'S HERE TOO (§ D1), and asking it is safe on this surface:
  // `ready-seats` launches nothing, writes nothing and messages nobody, which is exactly the bound
  // this verb holds itself to. A refusal (no python, a SKEW) degrades every unfired seat to
  // `waiting` rather than inventing a frontier — the same direction every other consumer takes.
  // ⚠ READ BEFORE THE VIEW SINCE W2: `recordView` sources done-ness and the `HELD` hold from these
  // rows, so a view built before them would report every seat unfinished.
  const { ready, rows: statusReadyRows } = readySeats(goalFolder);
  let view = recordView(null, goalFolder, { readyRows: statusReadyRows });
  if (everRun) {
    const open = openStore || ((p) => require('../server/heart/heart-store').openHeartStore({ dbPath: p }));
    const store = open(storePath);
    try {
      byJob = executionsByJob(store);
      queued = new Set(store.listQueue().map((q) => q.job_id));
      asks = unansweredAsks(store.dump().messages);
      view = recordView(store, goalFolder, { readyRows: statusReadyRows });
    } finally {
      store.close();
    }
  }

  const { goalExecutionMode, seatIsHumanInteractive, INTERACTIVE_MODE } =
    require('../bridges/chat/bus-ferry');
  // `<workspace>/.rbtv/goals/<goal>` — the reader takes the workspace root and the goal NAME.
  const workspaceRoot = path.resolve(goalFolder, '..', '..', '..');
  const executionMode = goalExecutionMode(workspaceRoot, path.basename(goalFolder));

  const seats = rows.map((row) => {
    const state = seatState(row, byJob, queued, { done: view.done, foreign: view.foreign, notFinished: view.notFinished, ready });
    const humanInteractive = seatIsHumanInteractive(goalFolder, row.seat);
    // BLOCKED ON THE OWNER, reported the way `interrupted` is and for the same reason: the seat's
    // STATE is `live` (not dispatchable, not finished — the pair every reader of SEAT_STATES
    // already understands), and WHY it is not moving is a fact beside the state, never a sixth
    // state word. This is the mechanical hold (#d-block-and-queue-mechanical-hold) made visible.
    const blockedOnOwner = view.blocked.has(row.seat);
    // The OTHER reason a seat's state is `live` with nothing of ours running: the record's last row
    // for it is somebody else's OPEN one (a lane still working, or one that crashed mid-seat).
    // Reported for review F2's reason — `recordView` computed that sentence and no surface read it,
    // so the operator saw `live` and could not tell which kind of live it was.
    const heldByOtherLane = view.foreign.has(row.seat) ? view.foreign.get(row.seat) : null;
    // INTERRUPTED, and it is not a sixth seat state. A foreground row still `launching` belongs to
    // a runner that is gone (a foreground child cannot outlive its terminal), so `live` — true by
    // the shared predicate — reads to an operator as "something is working on it" when nothing is.
    // Reported ALONGSIDE the state rather than instead of it: the predicate stays the engine's one
    // copy, and the next run's reconciliation is what actually resolves the row.
    const interrupted = (byJob.get(jobIdFor(row.seat)) || []).some(
      (r) => r.enqueued_by === FOREGROUND_ENQUEUER && LIVE_TURN_STATUSES.includes(r.status)
    );
    return {
      seat: row.seat,
      after: (row.after || '').trim() || null,
      state,
      interrupted,
      blockedOnOwner,
      heldByOtherLane,
      humanInteractive,
      // Ruling 5's TWO gates, both of them, evaluated here so no caller re-derives one of them.
      heldForUser: state === 'ready' && humanInteractive && executionMode === INTERACTIVE_MODE,
    };
  });

  return {
    goalFolder,
    storePath: everRun ? storePath : null,
    everRun,
    executionMode,
    seats,
    done: seats.filter((s) => s.state === 'done').map((s) => s.seat),
    ready: seats.filter((s) => s.state === 'ready').map((s) => s.seat),
    live: seats.filter((s) => s.state === 'live' || s.state === 'queued').map((s) => s.seat),
    waiting: seats.filter((s) => s.state === 'waiting').map((s) => s.seat),
    heldForUser: seats.filter((s) => s.heldForUser).map((s) => s.seat),
    interrupted: seats.filter((s) => s.interrupted).map((s) => s.seat),
    blockedOnOwner: seats.filter((s) => s.blockedOnOwner).map((s) => s.seat),
    heldByOtherLane: seats.filter((s) => s.heldByOtherLane).map((s) => s.seat),
    // NEXT is what the engine would advance on now — the ready set. Named separately because
    // "what do I do next" is the question the verb exists to answer.
    next: seats.filter((s) => s.state === 'ready').map((s) => s.seat),
    asks,
  };
}

// ── The attached run ──────────────────────────────────────────────────────────────────────────
async function executeAttached({
  goalFolder: goalFolderInput,
  spawnConfigPath,
  tickIntervalMs = null,
  maxTicks = null,
  logger = null,
  now = () => new Date(),
  sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
  // The one-shot relaunch grants this invocation carries (`--relaunch <seat>`), and the carriage
  // for a held seat. `spawnForeground` is injectable because a probe cannot own a real tty — the
  // REAL path stays the default, and a probe substitutes a scripted child.
  relaunch = [],
  spawnForeground = spawnForegroundInTerminal,
}) {
  // THE SEAM, FIRST — before any POSIX construct is reachable. A non-POSIX host is refused with a
  // typed error naming all four degraded sites and the row that owns their bodies (task 7.84),
  // never carried silently down the POSIX path.
  const host = substrate.assertSubstrateSupported();

  const goalFolder = resolveGoalFolder(goalFolderInput);
  const storePath = path.join(goalFolder, STORE_FILENAME);

  const spawnConfig = loadConfig(spawnConfigPath);
  assertNotTheDaemonStore(storePath, spawnConfig);

  // ── THE SESSION-ARTIFACT ROOT THIS LANE SPAWNS AGAINST (logs/, exits/) ────────────────────────
  //
  // The committed config's `spawn.data_root` is the SEED value — system-centric
  // (/var/lib/rbtv-ignite), overridable by RBTV_IGNITE_DATA_ROOT, which the daemon's unit sets and
  // folds into a materialized effective config before its engine boots. This lane boots from the
  // committed file in a user shell where that env var is normally ABSENT, so without a resolution
  // of its own it spawns headless seats against a root a user cannot mkdir — the spawn dies at
  // `ensureLogPath` with EACCES before `launching` is ever recorded (measured 2026-08-12:
  // forge-prompt-channel-master forg-builder, two same-second `crash sweep: exit=null` deaths).
  // Resolution order: the operator env override, then THIS MACHINE's recorded state root from the
  // install's endpoint record (`.rbtv/modules/ignite/server.json` — the one home of that fact),
  // then the config value as committed. Null falls through to the config untouched.
  const spawnDataRoot = process.env.RBTV_IGNITE_DATA_ROOT
    || machineStateRoot(goalFolder)
    || null;

  // ── EVERY SEAT MUST BE CAST BEFORE THIS LANE RUNS (`#d-abolish-profile-names` sub-ruling 3) ──
  //
  // `rbtv run --profile <name>` is GONE. It was the caller-named FALLBACK for a seat that declares
  // no cast; the abolition deletes the fallback, so what stood here as "the flag is required when
  // some seat would read it" becomes "an uncast seat refuses, and it refuses HERE rather than
  // hours later at spawn". `uncastSeats` is the same predicate the daemon's lane watch asks, so
  // the two lanes cannot disagree about which goals may run.
  //
  // ⚠ AN UNMATERIALIZED GOAL IS NOT A CASE HERE: `uncastSeats` reads the taskforce through
  // `readTaskforce`, which raises the same refusal `enqueueEligible` would raise four lines later
  // ("no taskforce — a run executes the run's seats").
  {
    const uncast = uncastSeats(goalFolder);
    if (uncast.length) {
      throw new Error(
        `REFUSING TO RUN: ${uncast.length} seat(s) of this goal declare no harness+model cast in `
        + `their seat.md — ${uncast.join(', ')}. Bindings are the one source of truth for what a `
        + `seat runs (\`#d-abolish-profile-names\`), and there is no fallback left to launch an `
        + `uncast seat on. Cast them with \`rbtv-bindings set <workflow.csv> <seat> <harness> `
        + `<model> [effort]\` and re-materialize, then run again.`
      );
    }
  }

  // THE LOCK, BEFORE THE STORE IS OPENED. Refusing after opening it would already have created and
  // migrated a store behind a live runner's back.
  const runLock = acquireRunLock(goalFolder);

  const engine = createEngine({
    dbPath: storePath,
    tools: spawnConfig.tools || {},
    workflows: spawnConfig.workflows || {},
    tickIntervalMs: tickIntervalMs || undefined,
    spawnConfigPath,
    spawnDataRoot,
    tickerConfig: tickIntervalMs ? { tick_interval_ms: tickIntervalMs } : {},
    feedPath: path.join(goalFolder, 'feed.jsonl'),
    logPath: path.join(goalFolder, 'ticker.log'),
    logger,
  });

  // The run dies with the terminal, by design — "resumable, not survivable" is the ruling's own
  // accepted price. The store is closed on the way out so the next run reopens it cleanly.
  let closedBySignal = false;
  const onSignal = () => {
    closedBySignal = true;
    try { engine.close(); } catch { /* the run is ending; a close error must not mask the signal */ }
    runLock.release();
    process.exit(130);
  };
  process.on('SIGINT', onSignal);
  process.on('SIGTERM', onSignal);

  try {
    // ⚠ THERE IS NO SEPARATE "ADOPTION" CALL HERE, AND ITS ABSENCE IS DELIBERATE (review F2). One
    // stood here — a publish before seeding, so a goal that ran before this record existed carried
    // its finished seats in. It was deleted because it is NOT INDEPENDENTLY OBSERVABLE: every path
    // through this loop ticks, `engine.tick` publishes, and within THIS lane the store's own rows
    // already govern seeding. A call whose removal no arm can detect is a claim, not a behaviour.
    // What the run guarantees instead, and what the probe measures: after any run, the goal's
    // record carries this store's outcomes — one tick later than a boot publish would have, which
    // costs nothing because the only reader that could care is the other lane.
    const rows = seedTaskforce(engine.heartStore, goalFolder, { logger });
    const resumedAtTick = engine.getTickNumber();
    const intervalMs = tickIntervalMs || 10000;
    const isHeld = heldSeatPredicate(goalFolder);
    // The grants this run may spend. A caller-supplied seat list (`relaunch`) is MINTED INTO THE
    // FILE rather than kept in this process: one home means the seat a console run granted is the
    // seat the daemon lane would also honour, and a grant that could not be spent this run survives
    // the terminal closing. The seeding pass sources the same file for itself, so this set is only
    // what THIS loop needs for its own carriage and exit decisions.
    for (const seat of relaunch) grantRelaunch(goalFolder, seat);
    const grants = readGrants(goalFolder);
    // BEFORE the first pass: a foreground row left non-terminal belongs to a runner that is gone.
    const reconciled = reconcileForegroundOrphans(engine.heartStore, { logger });
    const foreground = [];

    let ticks = 0;
    let lastStatusKey = null;
    let lastStatusTick = 0;
    for (;;) {
      // THE FOREGROUND CARRIER, ahead of the enqueue pass and BLOCKING: while this seat's session
      // owns the terminal nothing else in this run advances, which is the design's own sentence.
      // The terminal is SERIAL, but serial is not PACED (7.619): carrying one seat per pass cost
      // (N-1) full tick intervals of blank terminal between N seats ready in the same wave — 10s of
      // dead screen at the default cadence. The carriage now DRAINS the wave. The enqueue pass, the
      // tick and the exit decision below still run exactly once per pass, so nothing else moves.
      //
      // Re-read each pass: our own tick publishes to it, and the other lane may be writing to it
      // while we run. One small file read per pass, against a decision that must not be stale.
      // COORD'S FRONTIER, ONCE PER PASS (§ D1). Every decision below — what the terminal carries,
      // what is enqueued, and whether the run can advance at all — reads this ONE answer, so the
      // three cannot disagree about which seats are ready. A refusal leaves it null, which reads
      // as "no seat is ready" everywhere: the store may decline, never promote.
      // ⚠ IT IS READ BEFORE THE VIEW SINCE W2, and the order is now load-bearing rather than
      // incidental: `recordView` takes these rows as the source of done-ness and of the `HELD`
      // hold, so a view built before them would answer "nothing is done" for the whole pass.
      const { ready, rows: readyRows, reason: readyRefusal } = readySeats(goalFolder);
      let view = recordView(engine.heartStore, goalFolder, { relaunch: grants, readyRows });
      if (!ready && logger) {
        logger({
          level: 'warn',
          message: 'readiness NOT computed this pass — `coordinate ready-seats` refused, so nothing is carried or '
            + 'enqueued and the run cannot advance. A partial pass off a refused computation is worse than none.',
          goalFolder,
          evidence: readyRefusal,
        });
      }
      // The one hazard the drain creates: a seat `nextHeldReadySeat` somehow returns twice was
      // merely re-fired an interval later before, and would be a HOT LOOP now. Carried once per
      // pass — a pathological repeat falls back to the old pacing instead of spinning the terminal.
      const carriedThisPass = new Set();
      for (;;) {
        const held = nextHeldReadySeat(engine.heartStore, rows, isHeld, grants, view, ready);
        if (!held || carriedThisPass.has(held.seat)) break;
        carriedThisPass.add(held.seat);
        // The grant is SPENT at the launch, never re-read — in memory AND on disk, in one act.
        // The second half is what stops a re-run of `rbtv run` (or the daemon's next pass) finding
        // the same grant still standing and carrying the seat a second time.
        if (grants.delete(held.seat)) spendGrant(goalFolder, held.seat);
        foreground.push(runForegroundSeat({
          heartStore: engine.heartStore,
          seat: held.seat,
          goalFolder,
          launchSpecs: spawnConfig.launchSpecs,   // the seat's own cast selects from it (D19 · 7.787)
          tick: engine.getTickNumber(),
          now: now(),
          spawnForeground,
          logger,
        }));
        // ⚠ RE-READ, because the carriage above BLOCKED for the whole of that seat's session and
        // then wrote its outcome to the record. The view built before it is stale by construction,
        // and the enqueue pass below would decide this seat's dependents against a picture from
        // before it ran — measured: a carried `block-and-queue` seat published `blocked`, the stale
        // view still had no row for it, and the store's own `done` turn let its dependent start
        // anyway. One extra small read, on carriage passes only. It is ALSO what makes the next
        // turn of this loop correct: the seat this one just unblocked is visible to it.
        view = recordView(engine.heartStore, goalFolder, { relaunch: grants, readyRows });
      }

      enqueueEligible(engine.heartStore, rows, {
        goalFolder, logger, isHeld, relaunch: grants, view, ready, readyRows,
      });
      await engine.tick(now());
      ticks += 1;

      // ⚠ RE-READ AFTER THE TICK, and this replaces the "same view, one read per pass" economy that
      // stood here. The tick PUBLISHES to the record, so the pass's own view is stale by exactly the
      // thing that just happened — and since the record's last word can now REMOVE done-ness
      // (#d-block-and-queue-mechanical-hold), a stale view no longer merely lags: it says a seat is
      // unfinished that this store finished a moment ago, and the exit condition ENDS THE RUN on
      // that. Measured: probe-foreground-carrier B1a/B1e/B1g returned `seat-failed` on a run that had
      // completed. The dispatch decision keeps the pre-tick view (its own read, its own moment); the
      // exit decision must see what the tick published.
      // ⚠ AND THE FRONTIER IS RE-READ HERE FOR THE SAME REASON THE RECORD IS. A seat that finished
      // INSIDE this tick may have CHECKED OUT inside it, and the pass's own frontier was read
      // before that happened — so the pre-tick answer would call the seat it just unblocked
      // unreachable and END THE RUN `blocked` one pass early. One extra `ready-seats` per pass
      // (~0.4 s) against a decision that terminates the run.
      // ⚠ ONE post-tick `ready-seats`, and the VIEW is built FROM IT (W2) rather than beside it.
      // The frontier and the record's view now share one source for done-ness, so the exit decision
      // and the status block cannot disagree about a seat that checked out inside this tick.
      const post = readySeats(goalFolder);
      const postView = recordView(engine.heartStore, goalFolder, { relaunch: grants, readyRows: post.rows });
      const postReady = post.ready;
      // The status block, from the SAME post-tick reads the exit decision is about to use.
      const status = renderStatusBlock(engine.heartStore, rows, isHeld, postView, postReady);
      const refreshDue = status.block.includes('Running') && (ticks - lastStatusTick) * intervalMs >= 60000;
      if (status.key !== lastStatusKey || refreshDue) {
        lastStatusKey = status.key;
        lastStatusTick = ticks;
        // STDERR, not stdout: under `--json` stdout carries ONLY the machine-readable result, and
        // this write is not gated by the caller's json flag. The CLI already routes every other
        // operator line (the `logger`) to stderr, so a terminal shows this exactly as before.
        process.stderr.write(`${status.block}\n`);
      }
      const verdict = evaluateExit(engine.heartStore, rows, grants, postView, postReady);
      if (verdict.done) {
        return {
          host,
          outcome: verdict.reason,
          goalFolder,
          storePath,
          resumedAtTick,
          tick: engine.getTickNumber(),
          ticks,
          seats: rows.map((r) => r.seat),
          asks: verdict.asks || [],
          unfinished: verdict.unfinished || [],
          // The seats a relaunch grant could actually release — what the CLI's remedy hint prints,
          // so the hint is not a guess made from the outcome word (it used to be exactly that, and
          // was therefore unreachable on the `blocked` verdict a cross-lane failed seat produces).
          grantable: verdict.grantable || [],
          foreground,
          reconciled,
        };
      }

      // A bound the CALLER sets, for probes and for a person who wants one pass. Absent, the run
      // is genuinely attached: it ticks until it finishes or someone asks something.
      if (maxTicks !== null && ticks >= maxTicks) {
        return {
          host, outcome: 'max-ticks', goalFolder, storePath, resumedAtTick,
          tick: engine.getTickNumber(), ticks, seats: rows.map((r) => r.seat), asks: [], unfinished: [],
          grantable: [], foreground, reconciled,
        };
      }
      await sleep(intervalMs);
    }
  } finally {
    process.off('SIGINT', onSignal);
    process.off('SIGTERM', onSignal);
    if (!closedBySignal) engine.close();
    runLock.release();
  }
}

module.exports = {
  executeAttached,
  statusAttached,
  unansweredAsks,
  seatState,
  SEAT_STATES,
  // Exported for the probe, which must be able to exercise each decision on its own rather than
  // only through a whole run — and for a caller that wants the refusals without the loop.
  resolveGoalFolder,
  assertNotTheDaemonStore,
  seedTaskforce,
  enqueueEligible,
  evaluateExit,
  executionsByJob,
  heldSeatPredicate,
  nextHeldReadySeat,
  runForegroundSeat,
  reconcileForegroundOrphans,
  spawnForegroundInTerminal,
  acquireRunLock,
  runnerAlive,
  appendForegroundSessionRow,
  closeForegroundSessionRow,
  FOREGROUND_ENQUEUER,
  RUN_LOCK,
  SESSIONS_CSV,
  jobIdFor,
  GOAL_FOLDER_RE,
  STORE_FILENAME,
};
