'use strict';

// engine/ — THE LIBRARY ENTRY POINT for ignite's workflow-advancement engine.
//
// ONE implementation of workflow advancement, TWO attachments (registry
// `concepts/rbtv-cli.md` § Run-verb machinery, owner ruling
// decisions.md#d-attached-run-embedded-engine). The daemon (`server/index.js`) attaches it to a
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
// `server/heart/`, `server/ticker/` and `server/spawn/` on disk would rewrite the require path of
// ~40 probes and every existing consumer in one step — the opposite of pure. The entry point is
// what was missing (three ad-hoc requires at the daemon's composition root and no façade at all);
// the files' addresses were not. A physical move is a separate, mechanical change that this seam
// makes safe to do later: after it, `engine/index.js` is the only import site that has to know.

const path = require('node:path');
const { openHeartStore } = require('../server/heart/heart-store');
const { createSpawnManager } = require('../server/spawn/spawn');
const { createTicker } = require('../server/ticker/ticker');
const { setResolvedGoalsRoot } = require('../server/heart/argv-template');
const substrate = require('./substrate');
const { publishToRecord } = require('./execution-record');
const { seedGoal } = require('./seeding');

// Compose the engine. Every dependency is INJECTED — this function opens exactly one thing (the
// store) and constructs the other two around it.
//
//   dbPath          the heart store file. THE CALLER CHOOSES WHICH STORE KIND (CMP-2 § Two store
//                   kinds): the daemon passes `{state_root}/heart.db`; an attached run passes
//                   `<goal-folder>/heart.db` and NEVER the daemon's. One candidate writer each, by
//                   construction — the `E_SECOND_WRITER` throw inside the store is an in-PROCESS
//                   guard and was never able to see across processes.
//   profiles/tools/workflows/tickIntervalMs   the store's catalogue + snooze conversion inputs.
//   spawnConfigPath the launch-profile config the fire path resolves NAMED profiles from.
//   decorateSpawnManager  an OPTIONAL `(spawnManager, heartStore) => spawnManager` wrapper applied
//                   before the ticker is built. It exists for the daemon's headed fork, which
//                   must sit between the two — an attachment-specific decoration, not engine
//                   behaviour. The store is handed in because the decoration is built DURING
//                   composition, when the caller does not yet hold the return value.
function createEngine({
  dbPath,
  profiles = {},
  tools = {},
  workflows = {},
  tickIntervalMs,
  spawnConfigPath,
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

  const heartStore = openHeartStore({ dbPath, profiles, tools, workflows, tickIntervalMs });

  const bareSpawnManager = createSpawnManager({
    heartStore,
    configPath: spawnConfigPath,
    logger,
    userManager,
  });
  const spawnManager = decorateSpawnManager
    ? decorateSpawnManager(bareSpawnManager, heartStore)
    : bareSpawnManager;

  // Task 7.562 — hand the store the sanctioned fire-tool workdir. It arrives here rather than
  // through `openHeartStore` because `default_workdir_root` lives in the launch-profile config the
  // spawn manager loads, and the spawn manager is built FROM the store. One assignment beats
  // loading that config twice or reordering the composition root.
  heartStore.config.workdirRoot = spawnManager.config.default_workdir_root || null;

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
    seedGoal: ({ goalFolder, goal, profile, isHeld = null }) => {
      publishToRecord(heartStore, { logger });
      return seedGoal({ heartStore, goalFolder, goal, profile, isHeld, logger });
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

module.exports = { createEngine, substrate };
