'use strict';

// -- THE FROZEN INVARIANT'S TICK DRIVER [T1-R15, C-5, spec-owner-io §9] -------------------------
//
// `observation/frozen.js` was built, proven and left UNCALLED: nothing supplied it observations,
// nothing supplied it `frozen_window_min`, and its own header says so ("wiring itself is not done
// here — nothing calls either module yet"). This file is that caller, and it is ONLY that. It
// decides nothing about what frozen means: the conjunction, the two [C-5] exclusions, the hold
// clock and the hourly repeat all stay in the module it calls.
//
// ⚠ THE FACTS ARE HANDED IN BY THE PASS THAT ALREADY COMPUTES THEM. `engine/lane-watch.js` runs
// once a cadence over every daemon-assigned goal and already knows, for each: what the goal-state
// row says, whether it is paused, what this pass enqueued, whether an ask is open, and what the
// provider lanes say. Re-deriving any of that here would make this a second scheduler — the exact
// thing `frozen.js` refuses to be, one level up.
//
// ⚠ `frozen_window_min` COMES FROM THE RECOVERY CONFIG AND FROM NOWHERE ELSE [spec-recovery §2.1].
// A pass that cannot read that file arms NOTHING and says so, exactly as `ticker.js`'s deferred
// counter does — it never falls back to a number in code.
//
// ⚠ THE DAEMON RESOLVES NO SLACK CREDENTIAL, and that is not an oversight here either
// (`r-cutover-gated`; `queued-start-notify.js` states the same rule). The alarm is composed, the
// registry row is written, and the post is minted `pending-delivery` in the durable outbox [C-17].
// The owner learns of it through the 2-hourly system digest, which reads the SAME registry
// (`bridges/chat/system-digest.js` § Open conditions) from the process that does hold a token.
// That is the designed path, not a degradation: §9.2 gives one emission per condition and hands
// re-surfacing to the digest.
//
// ⚠ A DAEMON RESTART SUPPRESSES THIS PASS FOR THE CONFIGURED WINDOW (task #113 criterion 2). The
// whole pass, not the individual alarm: after a restart every goal's latency looks wrong for the
// same reason, so filtering one alarm at a time would be arithmetic over a fact that applies to all
// of them. See `restart-window.js` for what counts as a restart and why the fact is read off the
// watchdog's ledger rather than the daemon's own memory.

const { createAlarmEmitter, alarmRegistryPath } = require('../observation/emitter');
const { createFrozenInvariant } = require('../observation/frozen');
const { createOutbox, outboxStorePath } = require('../bridges/chat/outbox');
const { loadRecoveryConfig } = require('../supervisor/recovery-config');
const { restartSuppression } = require('./restart-window');
const path = require('node:path');

// Beside the alarm registry, exactly where `frozen.js` documents the hold clock lives — persisted,
// so a restart mid-freeze does not restart the window.
const HOLDS_REL = ['.rbtv', 'runtime', 'ignite', 'frozen-holds.json'];

// The daemon's outbox `send`. It is unwired ON PURPOSE (see the header): a post minted here is a
// durable record with the reason on it, never a lost alarm and never a silent success.
function daemonSend() {
  return async () => ({
    delivered: false,
    error: 'the daemon holds no Slack credential (r-cutover-gated) — the alarm is a durable pending-delivery record, re-surfaced by the 2-hourly system digest',
  });
}

// One pass. `facts` is what `runLaneWatch` collected this cadence: one entry per daemon-assigned
// goal it reached, carrying the eight goal facts and nothing else. The channel is added here
// because a goal's own Slack channel id is not knowable daemon-side (the bridge holds that map, in
// its own process), so a goal alarm posts in the system channel [T5-R1] — stated, not guessed.
async function runFrozenPass({
  facts = [],
  workspaceRoot = null,
  systemChannelId = null,
  suppressWindowMin = null,
  ledgerFile = null,
  alarmStorePath = null,
  outboxStore = null,
  holdsFile = null,
  registryFile = undefined,
  now = null,
  logger = null,
} = {}) {
  const say = (level, message, extra = {}) => { if (logger) logger({ level, message, ...extra }); };
  if (!facts.length) return { armed: false, reason: 'no-goals', checked: 0, results: [] };
  if (!workspaceRoot) {
    say('warn', 'frozen invariant NOT armed — no workspace root, so neither the recovery config nor the alarm registry can be located');
    return { armed: false, reason: 'no-workspace-root', checked: 0, results: [] };
  }
  if (!systemChannelId) {
    say('warn', 'frozen invariant NOT armed — no system channel is configured (RBTV_SYSTEM_CHANNEL_ID). A frozen goal would be observed with nowhere to say so.');
    return { armed: false, reason: 'no-system-channel', checked: 0, results: [] };
  }

  let config;
  try {
    config = loadRecoveryConfig({ workspace: workspaceRoot });
  } catch (err) {
    // spec-recovery §2.1: missing/unreadable/invalid is a configuration-error and the daemon
    // REFUSES to apply recovery clocks. There is no in-code window to fall back to.
    say('warn', 'frozen invariant NOT armed — the recovery config could not be read, and this module has no fallback window [spec-recovery §2.1]',
      { error: err.message });
    return { armed: false, reason: 'recovery-config-error', checked: 0, results: [] };
  }

  const clock = now || (() => Date.now());
  const suppression = restartSuppression({
    workspaceRoot, ledgerFile, windowMin: suppressWindowMin, now: clock,
  });
  if (suppression.suppressed) {
    say('info', 'frozen invariant SUPPRESSED this pass — a watchdog-detected daemon restart is inside the suppression window; latency after a restart is the restart, not a stall [task #113]',
      { ...suppression, goals: facts.length });
    return {
      armed: true, suppressed: true, reason: suppression.reason, suppression, checked: 0, results: [],
    };
  }

  const box = createOutbox({
    storePath: outboxStore || outboxStorePath(workspaceRoot),
    send: daemonSend(),
  });
  const emitter = createAlarmEmitter({
    storePath: alarmStorePath || alarmRegistryPath(workspaceRoot),
    post: box.post,
    systemChannelId,
  });
  const invariant = createFrozenInvariant({
    emitter,
    frozenWindowMin: config.frozen_window_min,
    registryFile,
    holdsPath: holdsFile || path.resolve(workspaceRoot, ...HOLDS_REL),
    now: clock,
  });

  const observations = facts.map((f) => ({ ...f, channel_id: f.channel_id || systemChannelId }));
  const results = [];
  for (const observation of observations) {
    try {
      results.push(await invariant.checkOne(observation));
    } catch (err) {
      // A malformed observation is the OBSERVING code's bug and `frozen.js` throws to say which
      // field is missing. One bad goal must not take the pass — or the daemon's tick — down.
      say('warn', 'frozen invariant: an observation was REFUSED — the pass continues without it',
        { goal: observation && observation.goal_id, error: err.message });
      results.push({ goal_id: observation && observation.goal_id, refused: err.message });
    }
  }

  const emitted = results.filter((r) => r && r.emitted).map((r) => r.goal_id);
  if (emitted.length) {
    say('warn', 'frozen invariant: alarm(s) emitted — a running goal with no live seat, no eligible launch, no open ask and no pause, held past the configured window',
      { goals: emitted, window_min: config.frozen_window_min, suppression: suppression.reason });
  }
  return {
    armed: true,
    suppressed: false,
    window_min: config.frozen_window_min,
    suppression,
    checked: results.length,
    emitted,
    results,
  };
}

module.exports = { runFrozenPass, HOLDS_REL };
