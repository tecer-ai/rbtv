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
const substrate = require('./substrate');

// Compose the engine. Every dependency is INJECTED — this function opens exactly one thing (the
// store) and constructs the other two around it.
//
//   dbPath          the heart store file. THE CALLER CHOOSES WHICH STORE KIND (CMP-2 § Two store
//                   kinds): the daemon passes `{state_root}/heart.db`; an attached run passes
//                   `<run-folder>/heart.db` and NEVER the daemon's. One candidate writer each, by
//                   construction — the `E_SECOND_WRITER` throw inside the store is an in-PROCESS
//                   guard and was never able to see across processes.
//   profiles/tools/workflows/tickIntervalMs   the store's catalogue + snooze conversion inputs.
//   spawnConfigPath the launch-profile config the fire path resolves NAMED profiles from.
//   decorateSpawnManager  an OPTIONAL `(spawnManager, heartStore) => spawnManager` wrapper applied
//                   before the ticker is built. It exists for the daemon's headed/pty fork, which
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
      'The daemon passes {state_root}/heart.db; an attached run passes <run-folder>/heart.db ' +
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
    tick: (now) => ticker.tick(now),
    getTickNumber: () => ticker.getTickNumber(),

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
