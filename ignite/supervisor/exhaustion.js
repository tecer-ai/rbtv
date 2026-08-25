'use strict';

// -- THE EXHAUSTION PATH - what happens at N [spec-recovery 5, T1-R8, D-2-ruling] ---------------
//
// A counter reaching N is the OWNER-VISIBLE EXIT the deleted brakes never had. Two acts, and only
// two: the lane is stamped `incomplete:` + `disarmed`, and ONE ask record is written per FAILURE
// SIGNATURE - never one per lane. Ten lanes failing the same way are one ask with ten lanes on it,
// which is the whole of what "signature-grouped" means [D-2-ruling].
//
// NO SLACK, NO OUTBOX, NOT ONE BYTE. This module writes a RECORD and stops. impl-slack reads the
// record and does the posting: the ask row lands with `posted = 0` and `posted_at = NULL`, which
// is the state its post transitions. A recovery path that could post is a recovery path that
// silently becomes the notifier, and then two components own the owner's attention.
//
// THE STORED WORDS ARE NOT INVENTED HERE. The stamp goes through impl-state-store's ending api
// (`stampSystem`), whose `LISTED_INCOMPLETE` table already carries the exact row this exit needs:
// `attempt-counter exhaustion` -> `armed: 0`, `named_event: 'named-external-input'`,
// `who_stamped: 'system'`. That string IS the stored diagnostic and may not be decorated - the
// store matches it exactly to decide the flag, so appending the refusal text to it would make the
// stamp refuse. The refusal text therefore rides where it can be read in full: on the ask record
// the `evidence_pointer` points at. Same fact, one hop, no second vocabulary.
//
// ARMED/DISARMED IS NOT REDEFINED HERE either [baseline contradiction-check]. This file only
// PRODUCES `disarmed`. `resume {goal}` and the other named re-arm events CONSUME it - that is
// `consumeDisarmed` below, which is the mechanical `resume` half of spec-recovery section 4 row 1:
// re-arm the driver, reset THAT counter, spend no relaunch budget, rewrite no brief.

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const counters = require('./attempt-counters');

// The ask record home, beside the ONE ending store [spec-state-store 1.1]. Workspace-relative and
// GENERAL - no instance path is spelled anywhere in this repo.
const ASKS_REL = path.join('.rbtv', 'runtime', 'ignite', 'asks');

// The ladder's options, verbatim [T1-R8, D-2-ruling]. Not configurable: an ask that offered a
// different set would be a different rung of a ruled ladder.
const ASK_OPTIONS = Object.freeze(['retry-with-change', 'drop-lane', 'pause-goal']);

// The stored diagnostic, spelled once. It must match `state-store/vocabulary.js#LISTED_INCOMPLETE`
// byte for byte or the disarmed stamp is refused - see the header.
const EXHAUSTION_DIAGNOSTIC = 'attempt-counter exhaustion';

function asksDir(workspaceRoot) {
  if (!workspaceRoot) throw new Error('asksDir requires workspaceRoot');
  return path.resolve(workspaceRoot, ASKS_REL);
}

// -- THE FAILURE SIGNATURE - the grouping key, and nothing volatile in it -----------------------
//
// (driver, reason class). Two lanes that hit the same refusal on the same driver share an ask; a
// different refusal opens a second one. The counter module's tripwire already refuses a reason
// class carrying a timestamp or a digest, so the grouping key cannot drift for the same reason the
// counter key cannot.
function signatureOf({ driver, reasonClass }) {
  if (!driver || !reasonClass) throw new Error('a failure signature needs a driver and a reason class');
  counters.keyOf({
    driver, subject: 'signature', reasonClass,
  });   // borrow the tripwire: refuses a volatile class before it can group anything
  return `${driver}:${reasonClass}`;
}

// A stable, filesystem-safe id for one signature. Same signature -> same id -> same record, which
// is what makes "one ask per signature" hold across passes, restarts and goals.
function askIdFor(signature) {
  return `recovery-${crypto.createHash('sha256').update(signature).digest('hex').slice(0, 12)}`;
}

function askRecordPath(workspaceRoot, askId) {
  return path.join(asksDir(workspaceRoot), `${askId}.json`);
}

function readAskRecord(workspaceRoot, askId) {
  try {
    return JSON.parse(fs.readFileSync(askRecordPath(workspaceRoot, askId), 'utf8'));
  } catch {
    return null;
  }
}

function writeAskRecord(workspaceRoot, record) {
  const target = askRecordPath(workspaceRoot, record.ask_id);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const tmp = `${target}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(record, null, 2)}\n`, 'utf8');
  fs.renameSync(tmp, target);
  return target;
}

// -- THE ONE SIGNATURE-GROUPED ASK RECORD -------------------------------------------------------
//
// Append-a-lane, never open-a-second-ask. The store row is inserted only the FIRST time a
// signature is seen; every later lane with that signature lands in the existing record's `lanes`
// array. `store.insertAsk` binds one seat (spec-owner-io: a daemon-posted ask binds to the lane's
// seat) - that is the FIRST lane, and the record carries the rest.
function recordGroupedAsk({
  store, workspaceRoot, goal, seat, driver, reasonClass, refusalText, attempts, at,
}) {
  const signature = signatureOf({ driver, reasonClass });
  const askId = askIdFor(signature);
  const stamp = at || new Date().toISOString();
  const lane = {
    goal, seat, driver, reason_class: reasonClass, refusal_text: refusalText || '', attempts: attempts || null, at: stamp,
  };
  const existing = readAskRecord(workspaceRoot, askId);
  const record = existing || {
    ask_id: askId,
    kind: 'signature-grouped',
    label: 'recovery',
    signature,
    options: [...ASK_OPTIONS],
    opened_at: stamp,
    lanes: [],
  };
  const already = record.lanes.some((l) => l.goal === goal && l.seat === seat);
  if (!already) record.lanes.push(lane);
  record.updated_at = stamp;
  const file = writeAskRecord(workspaceRoot, record);
  // The store row is the daemon-owned ask [spec-state-store 3] the kill clock's pause predicate
  // and the `N waiting` count read. `posted: 0` is impl-slack's to change, and this module never
  // does.
  let row = store && typeof store.getAsk === 'function' ? store.getAsk(askId) : null;
  if (!row && store && typeof store.insertAsk === 'function') {
    row = store.insertAsk({
      ask_id: askId, goal, seat, label: 'recovery', evidence_pointer: file,
    });
  }
  return {
    ask_id: askId, signature, file, record, row, grouped: Boolean(existing),
  };
}

// -- THE EXIT ITSELF ----------------------------------------------------------------------------
//
// Called by a driver whose `countAttempt` came back `exhausted`. Stamps, records, and returns both
// - a caller that wants to log the exit has everything without re-reading the store.
function exhaust({
  store, workspaceRoot, goal, seat, driver, reasonClass, refusalText, attempts, at, evidencePointer,
}) {
  const ask = recordGroupedAsk({
    store, workspaceRoot, goal, seat, driver, reasonClass, refusalText, attempts, at,
  });
  const ending = store.stampSystem({
    goal,
    seat,
    ending: 'incomplete',
    // `armed` and `named_event` come from the store's own listed row for this diagnostic - not
    // spelled here, so this file cannot drift from the vocabulary that owns them.
    diagnostic: EXHAUSTION_DIAGNOSTIC,
    evidence_pointer: evidencePointer || ask.file,
    stamped_at: at,
    replace: true,
  });
  return { ending, ask, driver, reasonClass, attempts };
}

// -- CONSUMING THE DISARMED FLAG - spec-recovery section 4, row 1 -------------------------------
//
// The mechanical `resume {goal}` (and any other named re-arm act) on a disarmed-counter lane:
// re-arm the ending, reset THAT counter. It spends no relaunch budget and rewrites no brief -
// there is deliberately no budget call in this function, and that absence is the [C-11] guarantee
// that an ask-resume is free.
function consumeDisarmed({
  store, goal, seat, driver, event = counters.RE_ARM.RESUME,
}, { countersFile } = {}) {
  const current = store.getCurrentEnding({ goal, seat });
  const disarmed = Boolean(current && current.ending === 'incomplete' && Number(current.armed) === 0);
  const armedRow = disarmed
    ? store.fireNamedEvent({ goal, seat, named_event: current.named_event })
    : current;
  const reset = counters.rearm({
    event, goal, seat, driver,
  }, { countersFile });
  return {
    consumed: disarmed, ending: armedRow, reset, event,
  };
}

module.exports = {
  ASKS_REL,
  ASK_OPTIONS,
  EXHAUSTION_DIAGNOSTIC,
  asksDir,
  signatureOf,
  askIdFor,
  askRecordPath,
  readAskRecord,
  recordGroupedAsk,
  exhaust,
  consumeDisarmed,
};
