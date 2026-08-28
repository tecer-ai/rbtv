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

// -- THE READ SIDE OF THOSE RECORDS, FOR THE OWNER SURFACE THAT RENDERS THEM -------------------
//
// WHAT WAS BROKEN. This module's whole point is that the exit at N is OWNER-VISIBLE — spec-recovery
// section 5 deleted the byte-equality brake because "it had no owner-visible exit" and replaced it
// with "open ONE signature-grouped ask". The ask was opened, as a file, and NOTHING carried it to
// the owner: `runtime/internal-api/dispatch.js`'s `inspect asks` — the port spec-owner-io section 5's
// 2-hourly system digest reads — answered from the `open_asks` TABLE alone, and this record lives
// on disk. Two lanes disarmed on 2026-08-28 (`goal-memory-management` 04:09Z,
// `scratch-death-recovery-1-exec` 05:27Z) and the owner was told nothing on either.
//
// READ-ONLY, BY CONSTRUCTION. It lists a directory and parses what is there. It opens no store,
// writes no file and mints no record — the ask surface stays this module's write side alone.
//
// OPEN MEANS THE RECORD IS STILL IN `asks/`. There is no reaper for these files today (the
// `open_asks` row has one; the record does not), so a listed ask stays listed until an owner act
// removes it. That is stated rather than papered over: the digest posts on CHANGE, so a standing
// record is rendered once and then rides the baseline.
//
// THE ONE-LINER IS THE RECORD'S OWN WORDS. The first lane's `refusal_text`, first line, truncated —
// never a sentence assembled here from the goal and seat names, which would put words on the
// owner's phone that nobody wrote [memory gateway/20260825-c-inspect-asks-the-read-half-of
// ATTENTION 3]. The extra-lane count is appended because it is a FACT OF THE RECORD, and hiding it
// would render a ten-lane ask as one lane's problem — the grouping this file exists for.
function oneLinerOfRecord(record) {
  const lanes = Array.isArray(record.lanes) ? record.lanes : [];
  const text = String((lanes[0] && lanes[0].refusal_text) || '').split(/\r?\n/).find((l) => l.trim());
  if (!text) return null;
  const head = text.trim().slice(0, 120);
  return lanes.length > 1 ? `${head} (+${lanes.length - 1} more lane${lanes.length > 2 ? 's' : ''})` : head;
}

// The row shape is `state-store/heart/ask-record.js#listOpenAsks`'s, key for key, so the digest and
// the CLI render one waiting set and neither needs to know which record a row came out of.
// `goal`/`seat` are the FIRST lane's — the same lane `recordGroupedAsk` binds the store row to.
function listOpenGroupedAsks(workspaceRoot) {
  if (!workspaceRoot) return [];
  let entries;
  try {
    entries = fs.readdirSync(asksDir(workspaceRoot), { withFileTypes: true });
  } catch {
    return [];              // no directory is the ordinary state: no lane has ever reached N
  }
  const rows = [];
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith('.json')) continue;
    const file = path.join(asksDir(workspaceRoot), entry.name);
    let record;
    try {
      record = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch {
      continue;             // an unreadable record costs its row, never the listing
    }
    if (!record || !record.ask_id) continue;
    const first = (Array.isArray(record.lanes) && record.lanes[0]) || {};
    rows.push({
      id: record.ask_id,
      goal: first.goal || null,
      seat: first.seat || null,
      label: record.label || 'recovery',
      one_liner: oneLinerOfRecord(record),
      opened_at: record.opened_at || null,
      evidence_pointer: file,
    });
  }
  return rows;
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
// THE STORE IS OPTIONAL, and that is not laxity - it is the deployed truth. Nothing sets
// `engine.endingStore` and `chat/index.js#main()` wires no port, so on this instance a disarmed
// lane exists ONLY as a counter row and the ending half has no writer to reach. A `store` that
// must be present would make the counter half - the half `reconcile.js#counterDisarmed` actually
// reads - unreachable for exactly as long as the ending store stays unwired. With no store the
// ending half is simply not performed, and `consumed` says so.
//
// `subject` rides through for the drivers whose subject is not a `(goal, seat)` lane (a job, an
// alarm identity). `counters.rearm` prefers it over goal+seat, which is what makes a scope sweep
// able to re-arm a row it did not have to name.
function consumeDisarmed({
  store = null, goal, seat, subject, driver, event = counters.RE_ARM.RESUME,
}, { countersFile } = {}) {
  const current = (store && seat) ? store.getCurrentEnding({ goal, seat }) : null;
  const disarmed = Boolean(current && current.ending === 'incomplete' && Number(current.armed) === 0);
  const armedRow = disarmed
    ? store.fireNamedEvent({ goal, seat, named_event: current.named_event })
    : current;
  const reset = counters.rearm({
    event, goal, seat, subject, driver,
  }, { countersFile });
  return {
    consumed: disarmed, ending: armedRow, reset, event,
  };
}

// -- THE SCOPE SWEEP - a named re-arm event over every row it owns ------------------------------
//
// WHAT WAS BROKEN. `consumeDisarmed` above is the mechanical half of spec-recovery section 4 row 1
// and it had ZERO callers; no boot or deploy path fired `code-deploy` either. So the closed re-arm
// list had no PRODUCER at all: a counter that reached N stayed at N forever and its lane was
// skipped on every pass, permanently (seven lanes on this instance, 2026-08-27). The counter
// module was never the gap - the two acts that were supposed to call it were.
//
// WHAT THIS IS. One entry point for "this named event happened, re-arm what it owns", returning
// the rows it cleared so the caller can SAY what it did. The scope is the event's own, exactly as
// `counters.rearm` defines it: `code-deploy` / `config-change` change the world for every driver
// and clear everything; `resume` / `owner-leader-act` are about a lane and clear that lane. Pass
// `goal` for the lane-scoped events; leave it null for the wide ones.
//
// IT DOES NOT DECIDE WHETHER A ROW WAS DISARMED. A wide event clears every row by design (the
// module's own scope rule), and a lane-scoped one clears the lane the owner just named. Filtering
// to `attempts >= N` here would need a second copy of the N and would leave a row at N-1 counting
// through a deploy that changed the very code it was counting refusals from.
function rearmScope({ store = null, goal = null, event }, { countersFile } = {}) {
  const before = counters.listCounters({ goal }, { countersFile });
  if (!before.length) return { event, goal, cleared: [], consumed: [] };
  const consumed = [];
  const seen = new Set();
  for (const row of before) {
    if (seen.has(row.subject)) continue;   // one re-arm per subject; a subject's rows go together
    seen.add(row.subject);
    const out = consumeDisarmed({
      store, goal: row.goal, seat: row.seat, subject: row.subject, event,
    }, { countersFile });
    if (out.consumed) consumed.push({ goal: row.goal, seat: row.seat, subject: row.subject });
  }
  // Reported from what is ACTUALLY gone, never from what was asked for: a wide event clears rows
  // this sweep never named, and a caller journalling its own intent instead of the outcome is how
  // a log grows to disagree with the ledger it describes.
  const after = new Set(counters.listCounters({ goal }, { countersFile }).map((r) => r.key));
  return {
    event, goal, cleared: before.filter((r) => !after.has(r.key)), consumed,
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
  listOpenGroupedAsks,
  recordGroupedAsk,
  exhaust,
  consumeDisarmed,
  rearmScope,
};
