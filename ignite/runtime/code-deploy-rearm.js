'use strict';

// -- `code-deploy`, THE FIRST OF THE FOUR NAMED RE-ARM EVENTS TO GET A PRODUCER -----------------
//
// WHAT WAS BROKEN. `spec-recovery` §5 closes the re-arm list at four events — code deploy, config
// change, owner/leader act, mechanical `resume` — and says a counter "resets ONLY on a named
// re-arm event". Every one of the four was unwired: `counters.rearm` had one caller
// (`exhaustion.js#consumeDisarmed`) and that caller had none. So a driver that reached N was
// disarmed FOREVER — `reconcile.js#counterDisarmed` skipped its lane on every pass, through every
// restart, through every deploy of the very code whose refusals had been counted. Seven lanes on
// this instance were in that state on 2026-08-27, one of them a live goal's leader.
//
// WHAT THIS IS. The boot pass that fires `code-deploy`: if the code THIS process loaded is not the
// code the last boot recorded, the world changed under every counter, so every counter is cleared
// and each cleared row is journalled. It is deliberately not a new ledger — the previous digest is
// already on disk in the boot marker `code-fingerprint.js` has written since G-188 stage 3, and
// the recording of the new digest is that same marker's existing write.
//
// ⚠ A RESTART IS NOT A DEPLOY. The same bytes hash to the same digest, so an ordinary restart
// compares equal and re-arms NOTHING. That is the difference this pass exists to hold: a re-arm on
// every restart would turn the attempt counter back into the unbounded retry it replaced, because
// the owner's own fix for a stuck daemon is to restart it.
//
// ⚠ AN UNKNOWN FINGERPRINT RE-ARMS NOTHING EITHER. `captureLoadedCode` returns null on any failure
// (its fail-soft boot bar), and null is UNKNOWN, not "changed" — firing a wide re-arm off a failed
// scan would clear every counter on a boot that learned nothing.
//
// ⚠ THE DIGEST COMPARED IS THE WIDE ONE — the whole `ignite/` require closure, recorded on the
// boot marker as `deploy`. The marker's other digest (`code`) covers only the runtime component,
// because that is the scope its own reader re-hashes; building the deploy decision on it would
// leave `code-deploy` silent for every commit that touches `supervisor/` and nothing else, which
// is most of them.
//
// ⚠ NO RECORDED DIGEST FIRES IT. A first boot with no marker cannot prove the code is unchanged,
// and by definition something was deployed to get here, so the event fires and says `first_boot`.
//
// ⚠ IT NO LONGER CLEARS EVERYTHING, AND THE EXCEPTION IS THIS FILE'S OWN PREMISE. The event fires
// because THE CODE CHANGED (⚠ above), so the rows it may clear are the ones whose failure the code
// could have caused. A `reconcile-respawn` / `nonterm` row counts leader wakes over another seat's
// `failed` ENDING — a row written before this daemon booted, which new bytes do not touch — so it
// SURVIVES the deploy with its attempts intact (`attempt-counters.js#DEPLOY_IMMUNE`, owner ruling
// 2026-08-28 decision 4(c)). Wiping it re-bought three paid leader sittings per deploy for a
// failure the deploy had not changed. Everything else still goes.
//
// ⚠ FAIL-SOFT, LIKE EVERYTHING ELSE ON THE BOOT PATH. It never throws: `index.js` exits hard on an
// unhandled boot error, and a daemon that refuses to start because a counter file was unreadable
// is a worse failure than a counter that stays disarmed one more boot.

const { readCodeMarker } = require('./code-fingerprint');
const { RE_ARM, listCounters } = require('../supervisor/attempt-counters');
const { rearmScope } = require('../supervisor/exhaustion');

/**
 * Fire `code-deploy` when this boot's code differs from the last boot's.
 *
 * MUST be called BEFORE `writeCodeMarker`, which is what records the new digest — reading the
 * marker after the write would compare this boot against itself and never fire.
 *
 * @param {object}   args
 * @param {string}   args.workspaceRoot   where the boot marker lives
 * @param {object|null} args.fingerprint  this boot's WIDE `captureLoadedCode` result — the whole
 *                                        `ignite/` closure, not the runtime component's slice
 *                                        (null = UNKNOWN). Compared against the marker's `deploy`
 *                                        summary, which is where the last boot recorded the same.
 * @param {function} [args.log]           `(level, message, fields)` — the daemon's journal
 * @param {object}   [opts]
 * @param {string}   [opts.countersFile]  overridden by a probe, exactly as `reconcile.js` does
 * @returns {{fired: boolean, why: string, previous: string|null, digest: string|null,
 *            cleared: Array, kept: Array}} `kept` = the rows the cause filter left standing
 */
function rearmOnCodeDeploy({ workspaceRoot, fingerprint, log = () => {} }, { countersFile } = {}) {
  const digest = (fingerprint && fingerprint.digest) || null;
  const previousMarker = workspaceRoot ? readCodeMarker(workspaceRoot) : null;
  const previous = (previousMarker && previousMarker.deploy && previousMarker.deploy.digest) || null;

  if (!digest) {
    log('warn', 'code fingerprint UNKNOWN at boot — no code-deploy re-arm decision was made', { previous_digest: previous });
    return {
      fired: false, why: 'unknown-fingerprint', previous, digest, cleared: [], kept: [],
    };
  }
  if (digest === previous) {
    return {
      fired: false, why: 'unchanged', previous, digest, cleared: [], kept: [],
    };
  }

  const why = previous ? 'code-changed' : 'first-boot';
  let cleared = [];
  let kept = [];
  try {
    // No `store`: nothing in the deployed tree sets `engine.endingStore`, so the ending half has no
    // writer to reach and the counter half is the whole of what a re-arm can do here today. When a
    // store does arrive, it is one argument — see `exhaustion.js#rearmScope`.
    ({ cleared } = rearmScope({ event: RE_ARM.CODE_DEPLOY }, { countersFile }));
    // WHAT SURVIVED. The event's scope is every row, so after a wide sweep whatever is still in
    // the ledger is a row the cause filter KEPT. Read through `listCounters` — the module's one
    // parser of that file — rather than re-deriving it here from a second copy of the rule.
    kept = listCounters({}, { countersFile });
  } catch (err) {
    log('warn', 'code-deploy re-arm failed — the attempt counters stand as they were', { error: err.message, why });
    return {
      fired: false, why: 'rearm-failed', previous, digest, cleared: [], kept: [], error: err.message,
    };
  }

  // ONE LINE PER CLEARED ROW, at `info`, carrying the count it was cleared FROM. A disarm that was
  // silent for days is what this whole chain is repairing; its undo must not be silent either.
  for (const row of cleared) {
    log('info', `re-armed by code-deploy: ${row.subject} ${row.reason_class} (was N=${row.attempts})`, {
      subject: row.subject, reason_class: row.reason_class, driver: row.driver, attempts: row.attempts, goal: row.goal, seat: row.seat,
    });
  }
  // AND ONE LINE PER ROW THE DEPLOY DID NOT CLEAR, for the same reason: a lane that stays disarmed
  // through a deploy is a lane whose next wake is NOT coming, and that must be as audible as the
  // ones that were re-armed.
  for (const row of kept) {
    log('info', `NOT re-armed by code-deploy (the failure it counts is a seat's ending, which new code does not change): ${row.subject} ${row.reason_class} (N=${row.attempts})`, {
      subject: row.subject, reason_class: row.reason_class, driver: row.driver, attempts: row.attempts, goal: row.goal, seat: row.seat,
    });
  }
  log('info', 'code-deploy re-arm fired', {
    why,
    previous_digest: previous,
    digest,
    cleared: cleared.length,
    kept: kept.length,
    first_boot: why === 'first-boot',
  });
  return {
    fired: true, why, previous, digest, cleared, kept,
  };
}

module.exports = { rearmOnCodeDeploy };
