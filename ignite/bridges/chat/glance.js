'use strict';

// -- THE GLANCE WIRING: WHAT MAKES §5 AND §6 REACHABLE IN PRODUCTION ---------------------------
//
// `system-digest.js` and `status-line.js` were built, proven and left UNREACHED: `index.js#main()`
// wired no slot driver, no ask/condition readers and no Slack status port, so both surfaces were
// BUILT AND PROVEN in the same sense the approval and pause/resume doors were. This module is that
// wiring and NOTHING ELSE. It invents no rendering, no schedule and no trigger: every decision
// still lives in the two modules it composes.
//
// ⚠ IT IS A SEPARATE FILE FROM `index.js` SO IT CAN BE PROBED WITHOUT STARTING A BRIDGE. `main()`
// resolves credentials and opens a Socket-Mode connection; a wiring probe must be able to drive the
// slot clock, the readers and the status port with fakes, and it cannot do that through a process
// entry point. `index.js` calls this, and that call IS the wiring.
//
// ⚠ THE PORTS ARE HANDED IN, NEVER OPENED HERE. The bridge is a SEPARATE PROCESS from the daemon
// and `probes/probe-chat-boundary.js` forbids a store handle, a child process and a sibling reach
// into `server/`, `gateway/` or `cli/`. So:
//   · open asks come back over the gateway (`ask-store.js#listOpenAsks` -> `inspect asks`);
//   · open conditions come from `observation/emitter.js`'s OWN published read interface, read off
//     the registry file the daemon writes — never from a stand-in registry here, which would be a
//     second source of alarm truth [T4-R10];
//   · the status text goes through the transport's `setStatusText`, the only surface §6 has.
//
// ⚠ THE DIGEST READS ASKS ONLY ON A SLOT. `checkSlot` asks `isSlot` FIRST and returns without a
// single gateway call on the other 599 checks of a 10-hour stretch. A version that read on every
// check would put ~2,880 reads a day on the daemon to answer a question ten instants a day.
//
// ⚠ AN UNREADABLE ASK LIST SKIPS THE SLOT — it never renders as "none open". `listOpenAsks`
// answers `null` on a refusal and `[]` when nothing is waiting, and those are different facts: a
// gateway outage rendered as `[]` would post "• none open", MOVE THE BASELINE on Slack's ack, and
// then re-post everything when the daemon came back. The digest's own port cannot make this
// distinction (`(await readOpenAsks()) || []`), which is exactly why the check is made HERE,
// before the digest is asked anything.

const path = require('node:path');

const { createSystemDigest, isSlot } = require('./system-digest');
const { createStatusLine } = require('./status-line');
// The alarm registry's published READ interface, and the reason this is not a local reimplementation
// of it: the registry's shape is a CONTRACT between `observation/emitter.js` and
// `system-digest.js`, and a second reader here would be a second definition of what an open
// condition is. The emitter is CONSUMED, never extended — nothing in `observation/` changes to
// admit this caller.
const { createAlarmEmitter, alarmRegistryPath } = require('../../observation/emitter');

// The digest's changed-only baseline, persisted so a bridge restart between two slots does not
// re-post an unchanged digest (`system-digest.js` ATTENTION 3). Runtime state, so it lives under the
// workspace's `.rbtv/`, never in the repo (`ignite/` rule 3).
const DIGEST_STATE_REL = ['.rbtv', 'runtime', 'ignite', 'system-digest.json'];

// The slot clock is checked TWICE a minute, not once. A slot is the instant `minute === 0` at
// America/Sao_Paulo, so a driver ticking exactly every 60 s has to keep phase for the life of the
// process to keep hitting it; one skipped beat under load silences a whole slot. At 30 s a lost
// beat still leaves a check inside the minute. A second check in the SAME minute costs nothing: the
// snapshot is unchanged against the baseline the first one delivered, and if it was NOT delivered
// the outbox recognises the identical pending record and retries it rather than minting a second.
const SLOT_CHECK_MS = 30 * 1000;

function digestStatePath(workspaceRoot) {
  return path.resolve(workspaceRoot, ...DIGEST_STATE_REL);
}

// The bridge NEVER emits an alarm — it renders the ones the daemon already emitted. Handing the
// emitter a `post` that throws is what makes that true by construction rather than by discipline:
// this instance is only ever asked `readOpenConditions()`, and any future line that tries to emit
// through it dies at the call site with a sentence naming the rule instead of quietly minting a
// second composer of owner alarms.
function refusingPost() {
  return async () => {
    throw new Error('the chat bridge never EMITS alarms — it reads open conditions [T4-R10]; alarms are composed only in observation/emitter.js');
  };
}

// `readOpenConditions` for the digest, over the daemon-written registry file.
//
// ⚠ `reload()` BEFORE EVERY READ, and that is not a defensive habit. `createAlarmEmitter` loads the
// rows ONCE at construction; the WRITER is the daemon, in another process, so a bridge that read
// its constructor-time snapshot would render the alarm set as it stood when the bridge last
// started — indistinguishable from "nothing is wrong" after any daemon activity.
function createConditionReader({ workspaceRoot, storePath = null, logger = null }) {
  const file = storePath || (workspaceRoot ? alarmRegistryPath(workspaceRoot) : null);
  if (!file) {
    if (logger) {
      logger({
        level: 'warn',
        message: 'system digest: NO alarm registry path (no workspace root) — the digest will render "• none open" for conditions whether or not any alarm is standing',
      });
    }
    return () => [];
  }
  const reader = createAlarmEmitter({ storePath: file, post: refusingPost() });
  return () => {
    reader.reload();
    return reader.readOpenConditions();
  };
}

// `deps` are the already-constructed parts of a running bridge:
//   outbox        — the bridge's ONE outbox (`chat-bridge.js`), so a digest that Slack never acked
//                   leaves the same `pending-delivery` record every other post leaves [C-17].
//   askRecord     — the bridge's ONE ask sender (`ask-store.js`), so the read and the two writes
//                   travel the same intent through the same forwarder.
//   setStatusText — the transport's §6 port (`slack-socket-mode.js#setStatusText`).
function createGlance({
  outbox,
  askRecord,
  setStatusText = null,
  systemChannelId = null,
  workspaceRoot = null,
  conditionsStorePath = null,
  digestState = null,
  // The beat, injectable for exactly one reason: a probe cannot wait 30 s to see the driver fire,
  // and a driver nobody can watch fire is a driver nobody has proven runs. Production never passes
  // it — `index.js` takes the constant.
  checkEveryMs = SLOT_CHECK_MS,
  now = () => new Date(),
  logger = null,
} = {}) {
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  // Both refusals are LOUD and neither is fatal to the bridge. A bridge that refused to start
  // because the owner's glance surface is unconfigured would trade every message it carries for a
  // convenience — and the digest's own constructor throws on a missing channel, which would be a
  // crash at boot rather than a sentence an operator can act on.
  if (!systemChannelId) {
    log('warn', 'system digest NOT wired — no system channel is configured (set RBTV_SYSTEM_CHANNEL_ID, or `system_channel_id` in the bridge config). The owner gets NO 2-hourly digest.');
    return null;
  }
  if (!outbox || typeof outbox.post !== 'function') throw new Error('createGlance requires the bridge outbox');
  if (!askRecord || typeof askRecord.listOpenAsks !== 'function') throw new Error('createGlance requires the ask record reader');

  const readOpenConditions = createConditionReader({
    workspaceRoot, storePath: conditionsStorePath, logger,
  });

  const statePath = digestState
    || (workspaceRoot ? digestStatePath(workspaceRoot) : null);
  if (!statePath) {
    log('warn', 'system digest baseline is NOT persisted — no workspace root configured. A bridge restart between two slots will re-post the last digest (`system-digest.js` ATTENTION 3).');
  }

  // The asks the CURRENT check read. The digest's port is synchronous-by-contract from its own
  // point of view; the read that can fail happens in `checkSlot` below, where a failure can still
  // mean "skip this slot" instead of "nothing is open".
  let slotAsks = [];

  const digest = createSystemDigest({
    post: outbox.post,
    systemChannelId,
    readOpenAsks: () => slotAsks,
    readOpenConditions,
    statePath,
    now,
    logger,
  });

  // ⚠ `readBlockedCount` IS DELIBERATELY LEFT AT ITS DEFAULT. §6 sums lanes stamped
  // `incomplete: blocked-on-human` with goals in stored state `paused`, and NO read door for
  // either exists from this process yet. The default answers `0`, and the line then reads
  // `N waiting · oldest Xh · 0 blocked`. Wiring a guess here would be worse than the zero: the
  // owner cannot tell an invented number from a measured one.
  const statusLine = createStatusLine({
    readOpenAsks: async () => {
      const rows = await askRecord.listOpenAsks();
      return rows || [];
    },
    setStatusText: typeof setStatusText === 'function' ? setStatusText : null,
    now,
    logger,
  });

  // ONE slot check. Returns what it decided, exactly as `digest.check` does, so "was not a slot",
  // "could not read" and "posted nothing because nothing changed" stay three distinct answers.
  let checking = false;

  async function checkSlot(when = null) {
    const at = when || now();
    if (!isSlot(at)) return { ran: false, reason: 'not-a-slot', posted: false };
    const asks = await askRecord.listOpenAsks();
    if (asks === null) {
      log('warn', 'system digest slot SKIPPED — the open-ask read failed, and an unreadable set is not an empty one. The next slot retries; the baseline has not moved.');
      return { ran: false, reason: 'asks-unreadable', posted: false };
    }
    slotAsks = asks;
    return digest.check(at);
  }

  let timer = null;

  function start() {
    if (timer) return { started: false, reason: 'already-running' };
    timer = setInterval(() => {
      // One pass at a time. The gateway read inside a slot check can outlive a 30 s beat, and two
      // overlapping checks would read the same slot twice against a baseline neither had moved yet.
      if (checking) return;
      checking = true;
      checkSlot().finally(() => { checking = false; }).catch((err) => log('warn', 'system digest slot check THREW — the slot is skipped, the baseline has not moved', { error: err.message }));
    }, checkEveryMs);
    if (timer.unref) timer.unref();
    log('info', 'system digest slot driver started — ten America/Sao_Paulo slots, changed-only', { systemChannelId, statePath });
    return { started: true, intervalMs: checkEveryMs };
  }

  function stop() {
    if (!timer) return { stopped: false };
    clearInterval(timer);
    timer = null;
    return { stopped: true };
  }

  return {
    digest, statusLine, checkSlot, start, stop,
    onTrigger: (t) => statusLine.onTrigger(t),
    readOpenConditions,
  };
}

module.exports = { createGlance, createConditionReader, SLOT_CHECK_MS, DIGEST_STATE_REL };
