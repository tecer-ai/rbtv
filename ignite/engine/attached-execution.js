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
//     There is NO WATCHER for this lane and that is RULED, not missing
//     (decisions.md#d-attached-lane-no-watcher): recovery IS the owner re-running this command.
//  4. THE SUBSTRATE SEAM. Asserted FIRST, before any POSIX construct is reachable — see
//     ./substrate.js for what it refuses and why a refusal rather than a fallback.

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { createEngine } = require('./index');
const substrate = require('./substrate');
const { loadConfig } = require('../server/spawn/config');

// The goal folder's shape is the goals tree's (CMP-4), not ours to redefine. GOAL-DIRECT since
// 7.607 (design-lock items 7-8 — the `runs/run-{n}` segment is extinguished, not optional):
//   <workspace>/.rbtv/goals/<goal-name>/
const GOAL_FOLDER_RE = /[/\\]\.rbtv[/\\]goals[/\\][^/\\]+[/\\]?$/;

const STORE_FILENAME = 'heart.db';
const TASKFORCE = 'taskforce.csv';

// Every turn status the store knows (heart-store TURN_STATUSES). Enumerated so "is this seat
// finished" is answered from the store's OWN partition of jobs_log rather than from a guess about
// which statuses exist — a list that drifts from the store's is a silent mis-answer.
const ALL_TURN_STATUSES = ['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed'];
// A turn that is still the engine's business. `stalled` is LIVE on purpose: it means "the owner
// should look", never "the work is over" (the store's own note on TERMINAL_TURN_STATUSES), so a
// stalled seat must not let the run report itself complete.
const LIVE_TURN_STATUSES = ['launching', 'running', 'stalled'];

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

// Minimal CSV read — the taskforce file is written by `rbtv goal` with plain comma-joined fields
// and no embedded commas or quotes. Reading it with a general CSV parser would be a dependency
// bought for a shape this repo already writes by hand (goal_cli.py write_csv).
function readCsv(file) {
  const text = fs.readFileSync(file, 'utf8');
  const lines = text.split('\n').filter((l) => l.trim().length);
  if (!lines.length) return [];
  const cols = lines[0].split(',').map((c) => c.trim());
  return lines.slice(1).map((line) => {
    const cells = line.split(',');
    const row = {};
    cols.forEach((c, i) => { row[c] = (cells[i] === undefined ? '' : cells[i]).trim(); });
    return row;
  });
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

// ── Seeding: the taskforce IS the workflow ────────────────────────────────────────────────────
//
// `taskforce.csv` already carries one row per seat with an `after` column naming the seat it
// follows. That column IS the wave structure — nothing new is invented here, and no second
// scheduler is written: seeding only decides WHICH seats are eligible now, and the ticker decides
// what actually launches and how many run at once (`max_live_agent_sessions` — the parallel wave).
//
// The PROFILE is not derived from the row's `harness`/`model`. Mapping an elected (model, variant)
// onto exactly one profile NAME is task 7.54's catalog, and inventing a second mapping here is the
// drift that DEC-1's shared-profile-source ruling exists to prevent. So the profile is passed by
// NAME by the caller, resolved from the ONE shared config — which keeps all four properties the
// widened sole-spawn gate kept: a pinned NAMED profile from the one shared config, picked by name,
// caller free text never reaching argv, and the pure-mechanism boundary intact.
function jobIdFor(seat) {
  return `seat-${seat}`;
}

function seedTaskforce(heartStore, goalFolder, { profile, logger }) {
  const tfPath = path.join(goalFolder, TASKFORCE);
  if (!fs.existsSync(tfPath)) {
    throw new Error(
      `${tfPath}: no taskforce — an attached run executes the run's seats, and the taskforce is ` +
      `where they are declared (CMP-4 goals tree). Nothing to run.`
    );
  }
  const rows = readCsv(tfPath).filter((r) => r.seat);
  if (!rows.length) throw new Error(`${tfPath}: no seat rows`);

  // CREATE-ONLY, and that is what makes a re-run a RESUME rather than a replay. registerJob is
  // create-only in the store (it throws E_JOB_EXISTS); a second boot finds every job already
  // registered and registers nothing.
  for (const row of rows) {
    const jobId = jobIdFor(row.seat);
    if (heartStore.getJob(jobId)) continue;
    heartStore.registerJob({
      jobId,
      actionType: 'launch-agent',
      function: `attached-execution seat ${row.seat}`,
      // `required`/`optional` are OBJECTS of name -> type, not arrays — the store parses them
      // that way (parseArgsSchema) and REFUSES an array. Registration is strict on purpose: a
      // schema a future enqueue could never satisfy is what campaign issue S-2(a) was.
      argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { workdir: 'string', prompt: 'string' } }),
      description: `seat ${row.seat} of ${row.taskforce_id || row['taskforce-id'] || 'this run'}`,
      createdAt: isoNow(),
      updatedAt: isoNow(),
    });
    if (logger) logger({ level: 'info', message: 'registered seat job', jobId, seat: row.seat });
  }
  return rows;
}

// The execution picture, read ONCE per pass from the store's own partition of jobs_log.
//
// `relaunch` is the ONE-SHOT RELAUNCH GRANT (console-run B1): a seat named in it is presented to
// the predicate WITHOUT its execution history, so a seat whose last attempt died reads `ready`
// again. The grant hides the rows from THIS VIEW only — nothing in the store is rewritten, so the
// failed attempt stays on the record it was written to. A FINISHED seat is never hidden: a grant
// must not be able to re-run completed work, and that is enforced here rather than trusted to the
// caller who typed the seat name.
function executionsByJob(heartStore, relaunch = null) {
  const byJob = new Map();
  for (const status of ALL_TURN_STATUSES) {
    for (const row of heartStore.listExecutionsByStatus(status)) {
      const list = byJob.get(row.job_id) || [];
      list.push(row);
      byJob.set(row.job_id, list);
    }
  }
  if (relaunch) {
    for (const seat of relaunch) {
      const jobId = jobIdFor(seat);
      if (!seatIsFinished(byJob.get(jobId))) byJob.delete(jobId);
    }
  }
  return byJob;
}

function seatIsFinished(rows) {
  return Boolean(rows) && rows.some((r) => r.status === 'done');
}

function seatHasRun(rows) {
  return Boolean(rows) && rows.length > 0;
}

// THE ELIGIBILITY PREDICATE, in ONE place. Both the enqueue pass and the read-only status verb
// answer "what is this seat's state right now" from here — a second copy of the wave math is a
// status surface that can disagree with the engine it reports on, which is worse than no surface.
//
//   done     a finished execution exists
//   live     an execution exists that has not finished (running / stalled / failed / …)
//   queued   a pending queue row exists
//   ready    never fired, and its `after` is done — the next thing the engine enqueues
//   waiting  never fired, and its `after` is not done
const SEAT_STATES = ['done', 'live', 'queued', 'ready', 'waiting'];

function seatState(row, byJob, queued) {
  const jobId = jobIdFor(row.seat);
  const mine = byJob.get(jobId);
  if (seatIsFinished(mine)) return 'done';
  if (seatHasRun(mine)) return 'live';
  if (queued.has(jobId)) return 'queued';
  const after = (row.after || '').trim();
  if (after && !seatIsFinished(byJob.get(jobIdFor(after)))) return 'waiting';
  return 'ready';
}

// Enqueue every seat whose `after` dependency has finished and which has never been fired. Returns
// the seats enqueued this pass.
//
// `isHeld` is the ONE place the engine can DETACH a human-interactive seat, and it is where it is
// stopped (console-run ruling 1: such a seat is dispatched through the foreground carrier or not at
// all). Skipping it here rather than filtering the rows earlier keeps the wave math on the WHOLE
// taskforce — a held seat still blocks its dependents exactly as it would if it had been queued.
function enqueueEligible(heartStore, rows, { profile, goalFolder, logger, isHeld = null, relaunch = null }) {
  const byJob = executionsByJob(heartStore, relaunch);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  const enqueued = [];

  for (const row of rows) {
    const jobId = jobIdFor(row.seat);
    if (seatState(row, byJob, queued) !== 'ready') continue;
    if (isHeld && isHeld(row.seat)) continue;
    if (relaunch) relaunch.delete(row.seat);

    const after = (row.after || '').trim();
    const seatDir = path.join(goalFolder, 'seats', row.seat);
    heartStore.enqueue({
      jobId,
      args: JSON.stringify({ profile, workdir: seatDir }),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt: isoNow(),
      enqueuedBy: 'attached-execution',
    });
    enqueued.push(row.seat);
    if (logger) logger({ level: 'info', message: 'enqueued seat', seat: row.seat, after: after || null });
  }
  return enqueued;
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

function nextHeldReadySeat(heartStore, rows, isHeld, relaunch) {
  const byJob = executionsByJob(heartStore, relaunch);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  return rows.find((row) => isHeld(row.seat) && seatState(row, byJob, queued) === 'ready') || null;
}

function runForegroundSeat({
  heartStore, seat, goalFolder, profileName, profile, tick, now,
  spawnForeground = spawnForegroundInTerminal, logger = null,
}) {
  if (!profile.headed || !profile.headed.tui) {
    throw new Error(
      `seat ${seat} is held for you (it declares human-interactive: and this goal runs in ` +
      `interactive execution mode), so it must run in YOUR terminal — but profile ` +
      `'${profileName}' declares no headed.tui block, which is the declaration that a profile can ` +
      `carry a human (D17). REFUSING rather than composing an interactive command out of the ` +
      `headless \`exec:\` template: a second interpreter of the one profile config is the drift ` +
      `DEC-1 § Shared profile source exists to prevent.`
    );
  }
  const { generateSessionId } = require('../server/spawn/carrier');
  const { composeArgv } = require('../server/spawn/spawn');

  const seatDir = path.join(goalFolder, 'seats', seat);
  const sessionId = generateSessionId();
  // mode `headed` selects `profile.headed.tui`; the descriptor injection
  // (`--append-system-prompt-file <seatDir>/seat.md`, claude-only and file-conditional) rides along
  // from the ONE composer every launch already uses.
  const { argv } = composeArgv(profile, 'headed', sessionId, seatDir, null, null);

  const exec = heartStore.recordExecutionStart({
    jobId: jobIdFor(seat),
    actionType: 'launch-agent',
    args: JSON.stringify({ profile: profileName, workdir: seatDir }),
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

  const res = spawnForeground(argv, seatDir) || {};
  const exitCode = typeof res.status === 'number' ? res.status : null;
  const ok = exitCode === 0;
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
function evaluateExit(heartStore, rows, relaunch = null) {
  const asks = unansweredAsks(heartStore.dump().messages);
  if (asks.length) {
    return { done: true, reason: 'question', asks };
  }

  const live = LIVE_TURN_STATUSES.flatMap((s) => heartStore.listExecutionsByStatus(s));
  if (live.length) return { done: false, live: live.length };
  if (heartStore.listQueue().length) return { done: false, live: 0 };

  const byJob = executionsByJob(heartStore, relaunch);
  const unfinished = rows.filter((r) => !seatIsFinished(byJob.get(jobIdFor(r.seat))));
  if (unfinished.length === 0) return { done: true, reason: 'complete' };

  // Nothing live, nothing queued, and seats still unfinished. Either a dependency chain is
  // BLOCKED (a seat whose `after` failed) or every remaining seat is waiting on one that will
  // never finish. Say so and stop, rather than spin: an attached run that cannot advance must
  // return to its caller, which is a terminal with a person at it.
  const stuck = unfinished.filter((r) => {
    const after = (r.after || '').trim();
    return after && !seatIsFinished(byJob.get(jobIdFor(after)));
  });
  if (stuck.length === unfinished.length) {
    return { done: true, reason: 'blocked', unfinished: unfinished.map((r) => r.seat) };
  }

  // A seat that HAS RUN and did not finish — a failed detached child, or a foreground seat the
  // reconciliation above ended. Nothing is live, nothing is queued and its dependency is satisfied,
  // so no future tick can change its state: the loop would otherwise spin here every 10s forever,
  // which is what it did. Returning is not a retry decision — the seat runs again only on an
  // explicit `--relaunch`, never because the loop came back around.
  const failed = unfinished.filter((r) => seatHasRun(byJob.get(jobIdFor(r.seat))));
  if (failed.length) {
    return { done: true, reason: 'seat-failed', unfinished: failed.map((r) => r.seat) };
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
  if (everRun) {
    const open = openStore || ((p) => require('../server/heart/heart-store').openHeartStore({ dbPath: p }));
    const store = open(storePath);
    try {
      byJob = executionsByJob(store);
      queued = new Set(store.listQueue().map((q) => q.job_id));
      asks = unansweredAsks(store.dump().messages);
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
    const state = seatState(row, byJob, queued);
    const humanInteractive = seatIsHumanInteractive(goalFolder, row.seat);
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
    // NEXT is what the engine would advance on now — the ready set. Named separately because
    // "what do I do next" is the question the verb exists to answer.
    next: seats.filter((s) => s.state === 'ready').map((s) => s.seat),
    asks,
  };
}

// ── The attached run ──────────────────────────────────────────────────────────────────────────
async function executeAttached({
  goalFolder: goalFolderInput,
  profile,
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

  if (!profile) {
    throw new Error(
      'an attached run needs a NAMED launch profile from the one shared config. The (harness, ' +
      'model) -> profile-name catalog is core-build task 7.54, and a second mapping invented here ' +
      'is exactly the drift DEC-1 § Shared profile source forbids.'
    );
  }

  const spawnConfig = loadConfig(spawnConfigPath);
  assertNotTheDaemonStore(storePath, spawnConfig);
  if (!spawnConfig.profiles[profile]) {
    throw new Error(
      `unknown launch profile '${profile}' — known: ${Object.keys(spawnConfig.profiles).join(', ')}. ` +
      `Profiles are PINNED and NAMED in the one shared config; this lane never composes one.`
    );
  }

  const engine = createEngine({
    dbPath: storePath,
    profiles: spawnConfig.profiles || {},
    tools: spawnConfig.tools || {},
    workflows: spawnConfig.workflows || {},
    tickIntervalMs: tickIntervalMs || undefined,
    spawnConfigPath,
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
    process.exit(130);
  };
  process.on('SIGINT', onSignal);
  process.on('SIGTERM', onSignal);

  try {
    const rows = seedTaskforce(engine.heartStore, goalFolder, { profile, logger });
    const resumedAtTick = engine.getTickNumber();
    const intervalMs = tickIntervalMs || 10000;
    const isHeld = heldSeatPredicate(goalFolder);
    const grants = new Set(relaunch);
    // BEFORE the first pass: a foreground row left non-terminal belongs to a runner that is gone.
    const reconciled = reconcileForegroundOrphans(engine.heartStore, { logger });
    const foreground = [];

    let ticks = 0;
    for (;;) {
      // THE FOREGROUND CARRIER, ahead of the enqueue pass and BLOCKING: while this seat's session
      // owns the terminal nothing else in this run advances, which is the design's own sentence.
      // One per pass — the terminal is serial, and the next pass picks up the next held seat.
      const held = nextHeldReadySeat(engine.heartStore, rows, isHeld, grants);
      if (held) {
        grants.delete(held.seat);            // the grant is SPENT at the launch, never re-read
        foreground.push(runForegroundSeat({
          heartStore: engine.heartStore,
          seat: held.seat,
          goalFolder,
          profileName: profile,
          profile: spawnConfig.profiles[profile],
          tick: engine.getTickNumber(),
          now: now(),
          spawnForeground,
          logger,
        }));
      }

      enqueueEligible(engine.heartStore, rows, { profile, goalFolder, logger, isHeld, relaunch: grants });
      await engine.tick(now());
      ticks += 1;

      const verdict = evaluateExit(engine.heartStore, rows, grants);
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
          foreground, reconciled,
        };
      }
      await sleep(intervalMs);
    }
  } finally {
    process.off('SIGINT', onSignal);
    process.off('SIGTERM', onSignal);
    if (!closedBySignal) engine.close();
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
  FOREGROUND_ENQUEUER,
  jobIdFor,
  GOAL_FOLDER_RE,
  STORE_FILENAME,
};
