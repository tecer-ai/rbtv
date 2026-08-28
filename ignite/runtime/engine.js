'use strict';

// engine/ — THE LIBRARY ENTRY POINT for ignite's workflow-advancement engine.
//
// ONE implementation of workflow advancement, TWO attachments (registry
// `concepts/rbtv-cli.md` § Run-verb machinery, owner ruling
// decisions.md#d-attached-run-embedded-engine). The daemon (`runtime/index.js`) attaches it to a
// long-lived systemd unit behind a gateway; the `rbtv run` verb attaches it to the calling
// terminal and dies with it. Both boot THE SAME code through THIS function. A second sequential
// runner for the attached lane is precisely what that ruling rejected — it would silently lose
// parallel waves, timers and the stall ladder.
//
// WHAT THE ENGINE IS, exactly: the heart store + the spawn/fire path + the ticker's tick
// algorithm. Nothing else. It boots with NO daemon process, NO gateway and NO HTTP — measurable,
// and measured by probe-engine-library.js beside this file.
//
// WHAT THIS FUNCTION DOES NOT OWN: the LOOP. The daemon runs a `setInterval` forever; the attached
// run ticks until completion or the first worker question and returns. That policy is the
// attachment's, and it is the only thing the two lanes are allowed to differ on. `tick()` — the
// algorithm — is shared, and it is the whole point.
//
// ⚠ WHY THE MODULES ARE STILL REQUIRED FROM `../server/` AND NOT MOVED HERE. Task 7.44's
// `_Sequencing:_` demands the re-home land "as a pure re-home with all probes green". Moving
// `state-store/heart/`, `runtime/ticker/` and `supervisor/spawn/` on disk would rewrite the require path of
// ~40 probes and every existing consumer in one step — the opposite of pure. The entry point is
// what was missing (three ad-hoc requires at the daemon's composition root and no façade at all);
// the files' addresses were not. A physical move is a separate, mechanical change that this seam
// makes safe to do later: after it, `runtime/engine.js` is the only import site that has to know.

const path = require('node:path');
const { openHeartStore } = require('../state-store/heart/heart-store');
const { bind, openEndingStoreFor } = require('../state-store');
const { createSpawnManager } = require('../supervisor/spawn/spawn');
const { createTicker } = require('./ticker/ticker');
const { setResolvedGoalsRoot } = require('../state-store/heart/argv-template');
const { publishToRecord } = require('../supervisor/execution-record');
const { seedGoal } = require('../supervisor/seeding');

// Compose the engine. Every dependency is INJECTED — this function opens exactly one thing (the
// store) and constructs the other two around it.
//
//   dbPath          the heart store file. THE CALLER CHOOSES WHICH STORE KIND (CMP-2 § Two store
//                   kinds): the daemon passes `{state_root}/heart.db`; an attached run passes
//                   `<goal-folder>/heart.db` and NEVER the daemon's. One candidate writer each, by
//                   construction — the `E_SECOND_WRITER` throw inside the store is an in-PROCESS
//                   guard and was never able to see across processes.
//   tools/workflows/tickIntervalMs   the store's catalogue + snooze conversion inputs.
//   spawnConfigPath the launch-spec config. Since 7.787 nothing RESOLVES a name through it — the
//                   fire path resolves each seat's own (harness, model) cast against its
//                   `launch-specs:` block, and its `jobs:` block is name-keyed but seat-unreachable.
//   decorateSpawnManager  an OPTIONAL `(spawnManager, heartStore) => spawnManager` wrapper applied
//                   before the ticker is built. It exists for the daemon's headed fork, which
//                   must sit between the two — an attachment-specific decoration, not engine
//                   behaviour. The store is handed in because the decoration is built DURING
//                   composition, when the caller does not yet hold the return value.
function createEngine({
  dbPath,
  tools = {},
  workflows = {},
  tickIntervalMs,
  spawnConfigPath,
  spawnDataRoot = null,
  userManager = true,
  tickerConfig = {},
  feedPath = null,
  logPath = null,
  logger = null,
  decorateSpawnManager = null,
}) {
  if (!dbPath) {
    throw new Error(
      'createEngine requires dbPath — the engine never guesses which heart store it owns. ' +
      'The daemon passes {state_root}/heart.db; an attached execution passes <goal-folder>/heart.db ' +
      '(CMP-2 § Two store kinds, DEC-7 § placement).'
    );
  }
  if (!spawnConfigPath) {
    throw new Error('createEngine requires spawnConfigPath — the launch-profile config the fire path resolves against');
  }

  const heartStore = openHeartStore({ dbPath, tools, workflows, tickIntervalMs });

  const bareSpawnManager = createSpawnManager({
    heartStore,
    configPath: spawnConfigPath,
    logger,
    userManager,
    dataRoot: spawnDataRoot,
  });
  const spawnManager = decorateSpawnManager
    ? decorateSpawnManager(bareSpawnManager, heartStore)
    : bareSpawnManager;

  // Task 7.562 — hand the store the sanctioned fire-tool workdir. It arrives here rather than
  // through `openHeartStore` because `default_workdir_root` lives in the launch-profile config the
  // spawn manager loads, and the spawn manager is built FROM the store. One assignment beats
  // loading that config twice or reordering the composition root.
  heartStore.config.workdirRoot = spawnManager.config.default_workdir_root || null;
  // 7.787, same seam and the same reason: `supervisor/seeding.js` needs each seat's own cage template
  // (`launch-specs.<harness>.<model>.sandbox.SeatBinds`) to run the pre-enqueue cage-admission test,
  // and it holds only the store. Assigned here rather than loaded a second time.
  heartStore.config.launchSpecs = spawnManager.config.launchSpecs || {};
  // D2 (2026-08-19), same seam a third time: the admission gate must resolve WORKSPACE-grammar
  // declared outputs (`.rbtv/mirror/…`) against the same workspace root the spawn manager
  // resolves rw grants against — threaded, never re-derived inside the engine.
  heartStore.config.workspaceRoot = spawnManager.workspaceRoot || null;

  // ── THE ENDING STORE, HELD BY THE ENGINE [spec-state-store §1.1] ────────────────────────────
  //
  // WHAT WAS BROKEN. `supervisor/reconcile.js:796` reads `engine.endingStore` and NOTHING set it,
  // so every production pass ran with `null` and each of its seven gated branches took the absent
  // arm: the leader's answers were never drained (`:835` — four `leader-instructions/*.json` files
  // pending across four goals on 2026-08-28, zero `LEADER INSTRUCTION was applied` lines ever),
  // the exhaustion exit could not stamp (`countRetry`'s `exit: 'no-ending-store'`, and every
  // disarm record on disk carries `the lane could NOT be stamped (no ending store on the pass)`),
  // and `spendRecoveryRelaunch` was unreachable, so `recovery_relaunch_count` stayed 0 on every
  // row and the `relaunch_budget_*` caps in `recovery.json` counted nothing.
  //
  // WHICH FILE, AND WHY NOT `bindEnding`. The ONE ending store is
  // `<workspace>/.rbtv/runtime/ignite/heart.db`, and `openEndingStoreFor` is the resolver both
  // sides of every ending question already spend. `supervisor/ending-reads.js#bindEnding` is the
  // READER's resolver and FALLS THROUGH to the caller's lane store when the home cannot be opened
  // — the fail-safe direction for "nothing declared", and the wrong file for the WRITER this
  // handle is (`stampSystem`, `insertAsk`, `incrementRecoveryRelaunch`). A writer bound to the
  // lane store reports applied and changes a file no reader reads
  // [memory state-store/20260828-i-pause-wrote-a-store-the-lane-g ATTENTION 2].
  //
  // AN UNOPENABLE HOME IS `null` AND ONE ERROR LINE, NEVER A THROW. Every consumer is already
  // written for absence — `reconcile.js` gates each branch on the store and the counter reports
  // `no-ending-store` rather than inventing a second writer — so the daemon boots and the lanes
  // keep running with the recovery half degraded, which is today's behaviour exactly. A boot that
  // died here would trade a degraded recovery path for no daemon at all.
  //
  // ⚠ IT IS NOT CLOSED BY `close()` BELOW. `state-store/open.js` caches ONE handle per file per
  // PROCESS and `bindEnding` hands out that same handle on every lane pass; closing it from here
  // would take the store out from under every other reader in the daemon.
  let endingStore = null;
  try {
    endingStore = bind(openEndingStoreFor(heartStore.config.workspaceRoot));
  } catch (err) {
    if (logger) {
      logger({
        level: 'error',
        message: 'the engine holds NO ending store — the leader-instruction drain, the disarmed '
          + 'stamp and the recovery relaunch budget are all INERT this boot [spec-state-store 1.1]',
        workspace_root: heartStore.config.workspaceRoot,
        error: err && err.message,
      });
    }
  }

  // Ruling `d-0811-workdir-symlink-boot-resolve` — resolve the goals root ONCE, HERE, from the same
  // boot-read trusted value the line above threads. This is the seam because it is the one place
  // that already holds `default_workdir_root` after the config load and before the first tick can
  // fire, and BOTH attachments (daemon and `rbtv run`) pass through it — a resolve at the daemon's
  // composition root would leave the attached lane on the lexical rule alone.
  setResolvedGoalsRoot(heartStore.config.workdirRoot);

  const ticker = createTicker({
    heartStore,
    spawnManager,
    config: tickerConfig,
    logger,
    feedPath,
    logPath,
  });

  let closed = false;

  return {
    heartStore,
    spawnManager,
    ticker,
    // The ONE ending store [spec-state-store 1.1], or `null` when its home could not be
    // opened. `supervisor/reconcile.js` is its reader and gates every branch on it.
    endingStore,
    dbPath: path.resolve(dbPath),

    // The shared algorithm. Both lanes call THIS; neither reimplements it.
    //
    // ⚠ AND THEY BOTH PUBLISH TO THE GOAL'S EXECUTION RECORD FROM HERE (owner ruling
    // decisions.md#d-s23-single-execution-record-now). The publish sits at the tick — the one thing
    // BOTH lanes call — rather than at each place a turn ends, and that placement is the reason
    // this build needs no hook in the completion path, the crash sweep, the kill path or the spawn
    // door: whatever ended a seat's turn, the next tick sees the terminal row and publishes it.
    // The cost is a bounded lag of one cadence between a completion and the shared record; the
    // alternative was four hooks in the daemon's hottest paths, each able to leave the record
    // behind on a path nobody remembered to touch.
    //
    // NEVER FATAL, and loud. A record write that fails must not take a tick down (the daemon serves
    // every goal from this loop), and the run that could not publish still resumes correctly from
    // its own store — it is the OTHER lane that would be misinformed, and the log line is what says
    // so. The next tick retries; the next boot's adoption pass retries again.
    tick: async (now) => {
      const result = await ticker.tick(now);
      try {
        publishToRecord(heartStore, { logger });
      } catch (err) {
        if (logger) logger({ level: 'warn', message: 'execution record NOT published this tick — the other lane cannot see what finished here', error: err.message });
      }
      return result;
    },
    getTickNumber: () => ticker.getTickNumber(),

    // Publish this store's seat outcomes into every goal folder it has touched. Called at boot by
    // the attached lane (the ADOPTION pass) and available to any caller that wants the record
    // current without waiting a cadence.
    publishRecord: () => publishToRecord(heartStore, { logger }),

    // ── THE DAEMON LANE'S GOAL PICKUP (criterion 2 of the same ruling) ──────────────────────────
    // Seed a goal folder's taskforce into THIS store and enqueue what is due, skipping every seat
    // the goal's execution record says is finished — whichever lane finished it. The attached lane
    // does its own seeding inline (it also carries held seats in the terminal, which this does not);
    // this is the entry a SHARED store uses, and it is what the daemon lane never had.
    // `readLease` is the D9 goal-live check's injection point (probes supply a fixture lease
    // reading; production callers pass nothing and get the real `deriveLease`).
    // ⚠ EVERY ARGUMENT THE CALLER MAY PASS MUST BE NAMED HERE. This is a DESTRUCTURING facade, so
    // a key it does not list is silently DROPPED — `laneSkips` was added to `seedGoal` for the C-9
    // per-lane skip and reached nothing until it was named here [D16, C-9].
    seedGoal: ({
      goalFolder, goal, isHeld = null, readLease = undefined, laneSkips = null,
    }) => {
      publishToRecord(heartStore, { logger });
      return seedGoal({
        heartStore, goalFolder, goal, isHeld, logger, laneSkips, ...(readLease ? { readLease } : {}),
      });
    },

    // Idempotent: an attached run closes on its own exit path AND on a signal, and the second
    // call must not throw over the first.
    close() {
      if (closed) return;
      closed = true;
      heartStore.close();
    },
  };
}

module.exports = { createEngine };
