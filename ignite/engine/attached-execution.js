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
function executionsByJob(heartStore) {
  const byJob = new Map();
  for (const status of ALL_TURN_STATUSES) {
    for (const row of heartStore.listExecutionsByStatus(status)) {
      const list = byJob.get(row.job_id) || [];
      list.push(row);
      byJob.set(row.job_id, list);
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
function enqueueEligible(heartStore, rows, { profile, goalFolder, logger }) {
  const byJob = executionsByJob(heartStore);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  const enqueued = [];

  for (const row of rows) {
    const jobId = jobIdFor(row.seat);
    if (seatState(row, byJob, queued) !== 'ready') continue;

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

// ── The exit condition — the registry's own sentence, made checkable ──────────────────────────
//
// "returns on completion or on ANY worker question". Both halves are read from the store:
//   COMPLETE — every seat has a finished execution, the queue is empty, and no turn is live.
//   QUESTION — a message of type `ask` exists that this loop has not already reported.
function evaluateExit(heartStore, rows, seenAskIds) {
  const asks = heartStore.dump().messages.filter((m) => m.type === 'ask' && !seenAskIds.has(m.msg_id));
  if (asks.length) {
    return { done: true, reason: 'question', asks };
  }

  const live = LIVE_TURN_STATUSES.flatMap((s) => heartStore.listExecutionsByStatus(s));
  if (live.length) return { done: false, live: live.length };
  if (heartStore.listQueue().length) return { done: false, live: 0 };

  const byJob = executionsByJob(heartStore);
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
      asks = store.dump().messages
        .filter((m) => m.type === 'ask')
        .map((a) => ({ msgId: a.msg_id, sender: a.sender, corpus: a.corpus }));
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
    return {
      seat: row.seat,
      after: (row.after || '').trim() || null,
      state,
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
    const seenAskIds = new Set();
    const intervalMs = tickIntervalMs || 10000;

    let ticks = 0;
    for (;;) {
      enqueueEligible(engine.heartStore, rows, { profile, goalFolder, logger });
      await engine.tick(now());
      ticks += 1;

      const verdict = evaluateExit(engine.heartStore, rows, seenAskIds);
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
          asks: (verdict.asks || []).map((a) => ({ msgId: a.msg_id, sender: a.sender, thread: a.thread, corpus: a.corpus })),
          unfinished: verdict.unfinished || [],
        };
      }

      // A bound the CALLER sets, for probes and for a person who wants one pass. Absent, the run
      // is genuinely attached: it ticks until it finishes or someone asks something.
      if (maxTicks !== null && ticks >= maxTicks) {
        return {
          host, outcome: 'max-ticks', goalFolder, storePath, resumedAtTick,
          tick: engine.getTickNumber(), ticks, seats: rows.map((r) => r.seat), asks: [], unfinished: [],
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
  seatState,
  SEAT_STATES,
  // Exported for the probe, which must be able to exercise each decision on its own rather than
  // only through a whole run — and for a caller that wants the refusals without the loop.
  resolveGoalFolder,
  assertNotTheDaemonStore,
  seedTaskforce,
  enqueueEligible,
  evaluateExit,
  jobIdFor,
  GOAL_FOLDER_RE,
  STORE_FILENAME,
};
