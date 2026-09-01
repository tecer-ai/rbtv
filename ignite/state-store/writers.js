'use strict';

const {
  EndingStoreError,
  E_WRITE_ONCE,
  E_KILLED_VOCABULARY,
  E_WRITER_REFUSED,
  E_BAD_ENDING,
  E_MISSING_EVIDENCE,
  E_ASK_NOT_FOUND,
  E_NO_CURRENT_ENDING,
} = require('./errors');
const {
  ENDINGS,
  GOAL_WORDS,
  REASON_CLASSES,
  NAMED_EVENTS,
  ASK_LABELS,
  HOLD_UNTIL,
  LISTED_INCOMPLETE,
  isKilledWord,
} = require('./vocabulary');

function nowIso() {
  return new Date().toISOString();
}

function tx(db, fn) {
  db.exec('BEGIN IMMEDIATE');
  try {
    const result = fn();
    db.exec('COMMIT');
    return result;
  } catch (err) {
    try { db.exec('ROLLBACK'); } catch { /* already gone */ }
    throw err;
  }
}

function refuseKilled(fields) {
  for (const value of Object.values(fields)) {
    if (isKilledWord(value)) {
      throw new EndingStoreError(
        E_KILLED_VOCABULARY,
        `killed vocabulary refused: ${value}`,
        { value: String(value) },
      );
    }
  }
}

function requireEvidence(pointer) {
  if (pointer == null || String(pointer) === '') {
    throw new EndingStoreError(E_MISSING_EVIDENCE, 'evidence_pointer is required');
  }
}

function getCurrentEnding(db, { goal, seat }) {
  return db.prepare(
    'SELECT * FROM seat_endings WHERE goal = ? AND seat = ?',
  ).get(goal, seat) || null;
}

function getGoalState(db, goal) {
  return db.prepare('SELECT * FROM goal_states WHERE goal = ?').get(goal) || null;
}

function getAsk(db, askId) {
  return db.prepare('SELECT * FROM open_asks WHERE ask_id = ?').get(askId) || null;
}

function archiveCurrent(db, row, supersededAt) {
  db.prepare(
    `INSERT INTO seat_endings_log (
      goal, seat, ending, armed, reason_class, who_stamped, evidence_pointer,
      diagnostic, named_event, stamped_at, recovery_relaunch_count,
      failure_strike_count, leader_attempt_used, superseded_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
  ).run(
    row.goal, row.seat, row.ending, row.armed, row.reason_class, row.who_stamped,
    row.evidence_pointer, row.diagnostic, row.named_event, row.stamped_at,
    row.recovery_relaunch_count, row.failure_strike_count, row.leader_attempt_used,
    supersededAt,
  );
  db.prepare('DELETE FROM seat_endings WHERE goal = ? AND seat = ?').run(row.goal, row.seat);
}

function nextCounters(prev, fields) {
  const recovery = prev ? prev.recovery_relaunch_count : 0;
  let strikes = prev ? prev.failure_strike_count : 0;
  const leader = prev ? prev.leader_attempt_used : 0;
  if (fields.ending === 'failed' && fields.reason_class !== 'provider-error') {
    strikes += 1;
  }
  return {
    recovery_relaunch_count: fields.recovery_relaunch_count != null
      ? fields.recovery_relaunch_count : recovery,
    failure_strike_count: fields.failure_strike_count != null
      ? fields.failure_strike_count : strikes,
    leader_attempt_used: fields.leader_attempt_used != null
      ? fields.leader_attempt_used : leader,
  };
}

function insertEnding(db, row) {
  db.prepare(
    `INSERT INTO seat_endings (
      goal, seat, ending, armed, reason_class, who_stamped, evidence_pointer,
      diagnostic, named_event, stamped_at, recovery_relaunch_count,
      failure_strike_count, leader_attempt_used
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`,
  ).run(
    row.goal, row.seat, row.ending, row.armed, row.reason_class, row.who_stamped,
    row.evidence_pointer, row.diagnostic, row.named_event, row.stamped_at,
    row.recovery_relaunch_count, row.failure_strike_count, row.leader_attempt_used,
  );
  return getCurrentEnding(db, row);
}

function normalizeArmed(value) {
  if (value == null) return null;
  if (value === true || value === 1 || value === '1') return 1;
  if (value === false || value === 0 || value === '0') return 0;
  throw new EndingStoreError(E_BAD_ENDING, `armed must be 0, 1, or null: ${value}`);
}

function applyListedDiagnostic(fields) {
  const listed = LISTED_INCOMPLETE[fields.diagnostic];
  if (!listed) return fields;
  return {
    ...fields,
    armed: fields.armed != null ? fields.armed : listed.armed,
    named_event: fields.named_event !== undefined ? fields.named_event : listed.named_event,
  };
}

function validateSeatDeclare(fields) {
  refuseKilled({
    ending: fields.ending,
    reason_class: fields.reason_class,
    named_event: fields.named_event,
  });
  if (!ENDINGS.includes(fields.ending)) {
    throw new EndingStoreError(E_BAD_ENDING, `unknown ending: ${fields.ending}`);
  }
  if (fields.ending === 'failed') {
    throw new EndingStoreError(E_WRITER_REFUSED, 'seat may not stamp failed');
  }
  if (fields.ending === 'incomplete') {
    const armed = normalizeArmed(fields.armed);
    if (armed !== 1) {
      throw new EndingStoreError(E_WRITER_REFUSED, 'seat may not stamp incomplete disarmed');
    }
    if (fields.named_event != null) {
      throw new EndingStoreError(E_WRITER_REFUSED, 'seat incomplete armed forbids named_event');
    }
  }
  if (fields.ending === 'done' && fields.reason_class != null) {
    throw new EndingStoreError(E_WRITER_REFUSED, 'done forbids reason_class');
  }
}

function validateSystemStamp(fields) {
  refuseKilled({
    ending: fields.ending,
    reason_class: fields.reason_class,
    named_event: fields.named_event,
  });
  if (!ENDINGS.includes(fields.ending)) {
    throw new EndingStoreError(E_BAD_ENDING, `unknown ending: ${fields.ending}`);
  }
  if (fields.ending === 'done') {
    throw new EndingStoreError(E_WRITER_REFUSED, 'system may not stamp seat-voice done');
  }
  if (fields.ending === 'failed') {
    if (!REASON_CLASSES.includes(fields.reason_class)) {
      throw new EndingStoreError(E_BAD_ENDING, `unknown reason_class: ${fields.reason_class}`);
    }
    if (fields.reason_class === 'crash') requireEvidence(fields.evidence_pointer);
  }
  if (fields.ending === 'incomplete') {
    const armed = normalizeArmed(fields.armed);
    if (armed === 0) {
      const listed = LISTED_INCOMPLETE[fields.diagnostic];
      if (!listed || listed.armed !== 0) {
        throw new EndingStoreError(
          E_WRITER_REFUSED,
          'system incomplete disarmed requires a listed diagnostic',
        );
      }
      if (fields.named_event && !NAMED_EVENTS.includes(fields.named_event)) {
        throw new EndingStoreError(E_BAD_ENDING, `unknown named_event: ${fields.named_event}`);
      }
    }
  }
}

function buildEndingRow(fields, prev, who) {
  requireEvidence(fields.evidence_pointer);
  const stampedAt = fields.stamped_at || nowIso();
  const counters = nextCounters(prev, fields);
  let armed = normalizeArmed(fields.armed);
  let namedEvent = fields.named_event === undefined ? null : fields.named_event;
  let reasonClass = fields.reason_class == null ? null : fields.reason_class;
  if (fields.ending === 'done' || fields.ending === 'failed') {
    armed = null;
    namedEvent = null;
  }
  if (fields.ending !== 'failed') reasonClass = null;
  if (fields.ending === 'incomplete' && armed === 1) namedEvent = null;
  return {
    goal: fields.goal,
    seat: fields.seat,
    ending: fields.ending,
    armed,
    reason_class: reasonClass,
    who_stamped: who,
    evidence_pointer: String(fields.evidence_pointer),
    diagnostic: fields.diagnostic == null ? '' : String(fields.diagnostic),
    named_event: namedEvent,
    stamped_at: stampedAt,
    ...counters,
  };
}

function writeEnding(db, fields, { who, replace }) {
  if (!fields.goal || !fields.seat) {
    throw new EndingStoreError(E_BAD_ENDING, 'goal and seat are required');
  }
  const current = getCurrentEnding(db, fields);
  if (current && !replace) {
    throw new EndingStoreError(
      E_WRITE_ONCE,
      `current ending already exists for ${fields.goal}/${fields.seat}`,
      { goal: fields.goal, seat: fields.seat, ending: current.ending },
    );
  }
  const row = buildEndingRow(fields, current, who);
  return tx(db, () => {
    if (current) archiveCurrent(db, current, row.stamped_at);
    return insertEnding(db, row);
  });
}

const { checkDoneOutputs } = require('./outputs-check');

function stampSeatDeclare(db, fields) {
  const next = applyListedDiagnostic({ ...fields, who_stamped: 'seat' });
  if (next.ending === 'incomplete' && next.armed == null) next.armed = 1;
  validateSeatDeclare(next);
  if (next.ending === 'done') {
    const check = checkDoneOutputs(next.declared_outputs || []);
    if (!check.ok) {
      return stampSystem(db, {
        goal: next.goal,
        seat: next.seat,
        ending: 'failed',
        reason_class: 'outputs-missing',
        evidence_pointer: check.missing,
        diagnostic: 'outputs-missing',
        replace: next.replace,
      });
    }
    next.armed = null;
    next.named_event = null;
    next.reason_class = null;
  }
  return writeEnding(db, next, { who: 'seat', replace: Boolean(next.replace) });
}

function stampSystem(db, fields) {
  const next = applyListedDiagnostic({ ...fields, who_stamped: 'system' });
  if (next.ending === 'incomplete' && next.armed == null && next.diagnostic) {
    const listed = LISTED_INCOMPLETE[next.diagnostic];
    if (listed) next.armed = listed.armed;
  }
  validateSystemStamp(next);
  return writeEnding(db, next, { who: 'system', replace: Boolean(next.replace) });
}

function replaceSeatEnding(db, fields) {
  return fields.who_stamped === 'seat'
    ? stampSeatDeclare(db, { ...fields, replace: true })
    : stampSystem(db, { ...fields, replace: true });
}

function writeGoalWord(db, fields) {
  refuseKilled({ stored: fields.stored });
  if (!fields.goal) throw new EndingStoreError(E_BAD_ENDING, 'goal is required');
  if (!GOAL_WORDS.includes(fields.stored)) {
    throw new EndingStoreError(E_BAD_ENDING, `unknown goal word: ${fields.stored}`);
  }
  requireEvidence(fields.evidence_pointer);
  if (fields.stored === 'paused' && fields.who_stamped !== 'owner') {
    throw new EndingStoreError(E_WRITER_REFUSED, 'paused is owner-hand');
  }
  if (fields.stored === 'finished' && fields.who_stamped !== 'system') {
    throw new EndingStoreError(E_WRITER_REFUSED, 'finished is system-stamped');
  }
  if (fields.stored === 'closed' && fields.who_stamped !== 'owner') {
    throw new EndingStoreError(E_WRITER_REFUSED, 'closed is owner-hand');
  }
  if (fields.who_stamped !== 'owner' && fields.who_stamped !== 'system') {
    throw new EndingStoreError(E_BAD_ENDING, `unknown who_stamped: ${fields.who_stamped}`);
  }
  const stampedAt = fields.stamped_at || nowIso();
  db.prepare(
    `INSERT INTO goal_states (goal, stored, who_stamped, evidence_pointer, stamped_at)
     VALUES (?,?,?,?,?)
     ON CONFLICT(goal) DO UPDATE SET
       stored = excluded.stored,
       who_stamped = excluded.who_stamped,
       evidence_pointer = excluded.evidence_pointer,
       stamped_at = excluded.stamped_at`,
  ).run(fields.goal, fields.stored, fields.who_stamped, String(fields.evidence_pointer), stampedAt);
  return getGoalState(db, fields.goal);
}

function insertAsk(db, fields) {
  refuseKilled({ label: fields.label, state: fields.state });
  if (!fields.ask_id) throw new EndingStoreError(E_BAD_ENDING, 'ask_id is required');
  if (!ASK_LABELS.includes(fields.label)) {
    throw new EndingStoreError(E_BAD_ENDING, `unknown ask label: ${fields.label}`);
  }
  requireEvidence(fields.evidence_pointer);
  db.prepare(
    `INSERT INTO open_asks (
      ask_id, goal, seat, label, state, posted, posted_at, authorized_reply_at, evidence_pointer
    ) VALUES (?,?,?,?, 'open', 0, NULL, NULL, ?)`,
  ).run(fields.ask_id, fields.goal, fields.seat, fields.label, String(fields.evidence_pointer));
  return getAsk(db, fields.ask_id);
}

function postAsk(db, { ask_id, posted_at }) {
  const row = getAsk(db, ask_id);
  if (!row) throw new EndingStoreError(E_ASK_NOT_FOUND, `no ask ${ask_id}`);
  const at = posted_at || nowIso();
  db.prepare('UPDATE open_asks SET posted = 1, posted_at = ? WHERE ask_id = ?').run(at, ask_id);
  return getAsk(db, ask_id);
}

function armAskAnswered(db, { goal, seat }) {
  const current = getCurrentEnding(db, { goal, seat });
  if (!current) return null;
  if (current.ending === 'incomplete' && Number(current.armed) === 0
      && current.named_event === 'ask-answered') {
    db.prepare(
      'UPDATE seat_endings SET armed = 1, named_event = NULL WHERE goal = ? AND seat = ?',
    ).run(goal, seat);
    return getCurrentEnding(db, { goal, seat });
  }
  return current;
}

function reapAndRelaunch(db, { ask_id, authorized_reply_at }) {
  return tx(db, () => {
    const row = getAsk(db, ask_id);
    if (!row) throw new EndingStoreError(E_ASK_NOT_FOUND, `no ask ${ask_id}`);
    if (row.state === 'closed') {
      return {
        ask: row,
        idempotent: true,
        relaunch: { goal: row.goal, seat: row.seat, ask_id: row.ask_id },
      };
    }
    const replied = authorized_reply_at || nowIso();
    db.prepare(
      "UPDATE open_asks SET state = 'answered', authorized_reply_at = ? WHERE ask_id = ?",
    ).run(replied, ask_id);
    db.prepare("UPDATE open_asks SET state = 'closed' WHERE ask_id = ?").run(ask_id);
    const armed = armAskAnswered(db, row);
    const closed = getAsk(db, ask_id);
    return {
      ask: closed,
      idempotent: false,
      ending: armed,
      relaunch: { goal: row.goal, seat: row.seat, ask_id: row.ask_id },
    };
  });
}

function incrementRecoveryRelaunch(db, { goal, seat }) {
  const current = getCurrentEnding(db, { goal, seat });
  if (!current) {
    throw new EndingStoreError(E_NO_CURRENT_ENDING, `no current ending for ${goal}/${seat}`);
  }
  db.prepare(
    'UPDATE seat_endings SET recovery_relaunch_count = recovery_relaunch_count + 1 WHERE goal = ? AND seat = ?',
  ).run(goal, seat);
  return getCurrentEnding(db, { goal, seat });
}

function setLeaderAttemptUsed(db, { goal, seat }) {
  const current = getCurrentEnding(db, { goal, seat });
  if (!current) {
    throw new EndingStoreError(E_NO_CURRENT_ENDING, `no current ending for ${goal}/${seat}`);
  }
  db.prepare(
    'UPDATE seat_endings SET leader_attempt_used = 1 WHERE goal = ? AND seat = ?',
  ).run(goal, seat);
  return getCurrentEnding(db, { goal, seat });
}

function fireNamedEvent(db, { goal, seat, named_event }) {
  if (!NAMED_EVENTS.includes(named_event)) {
    throw new EndingStoreError(E_BAD_ENDING, `unknown named_event: ${named_event}`);
  }
  const current = getCurrentEnding(db, { goal, seat });
  if (!current) {
    throw new EndingStoreError(E_NO_CURRENT_ENDING, `no current ending for ${goal}/${seat}`);
  }
  if (current.ending !== 'incomplete' || Number(current.armed) !== 0
      || current.named_event !== named_event) {
    throw new EndingStoreError(
      E_WRITER_REFUSED,
      `named event ${named_event} does not match current ending`,
    );
  }
  db.prepare(
    'UPDATE seat_endings SET armed = 1, named_event = NULL WHERE goal = ? AND seat = ?',
  ).run(goal, seat);
  return getCurrentEnding(db, { goal, seat });
}

// ── THE LEADER'S HOLD — the write half ─────────────────────────────────────────────────────────
//
// `getSeatHold` is the RAW row; whether that row still HOLDS anything is `predicates.js#seatHeld`,
// which is the one predicate every reader asks. Two functions and not one because a release
// condition is evaluated against OTHER rows (the ending's `stamped_at`, the ask's `state`), and a
// getter that silently applied it would leave `supervise release` unable to see what it is
// releasing.
function getSeatHold(db, { goal, seat }) {
  return db.prepare(
    'SELECT * FROM seat_holds WHERE goal = ? AND seat = ?',
  ).get(goal, seat) || null;
}

// One hold per (goal, seat) — the PRIMARY KEY says so, and that is the idempotence: a leader that
// posts the SAME hold twice (two sittings that read the same mail and reach the same verdict) gets
// its first row back untouched, `held_at` included, rather than a hold whose clock silently
// restarted. A hold that differs in any recorded field is a NEW ruling and replaces the old one.
//
// ⚠ `--anchor` IS RECORDED, NEVER VERIFIED — the same discipline `accept` carries: no tool can
// check that an anchor names a real investigation, and a hold citing nothing is a stall nobody can
// audit. ⚠ THE `new-ending` WITNESS IS CAPTURED HERE, not at read time: the hold is live while the
// ending still carries the stamp it carried when the leader ruled on it.
function holdSeat(db, {
  goal, seat, until, ask_id = null, anchor, held_by, held_at,
}) {
  refuseKilled({
    goal, seat, until, ask_id, anchor, held_by,
  });
  if (!goal || !seat) throw new EndingStoreError(E_WRITER_REFUSED, 'a hold needs a goal and a seat');
  if (!HOLD_UNTIL.includes(until)) {
    throw new EndingStoreError(E_BAD_ENDING, `unknown hold release condition: ${until} (closed list: ${HOLD_UNTIL.join(', ')})`);
  }
  if (until === 'ask-answered' && !ask_id) {
    throw new EndingStoreError(E_WRITER_REFUSED, '`--until ask-answered` names the ask that releases it: ask-answered:<ask-id>');
  }
  requireEvidence(anchor);
  if (!held_by) throw new EndingStoreError(E_WRITER_REFUSED, 'a hold records WHO ruled it');
  return tx(db, () => {
    const prior = getSeatHold(db, { goal, seat });
    const askId = until === 'ask-answered' ? String(ask_id) : null;
    if (prior && prior.until === until && (prior.ask_id || null) === askId
        && prior.anchor === String(anchor) && prior.held_by === String(held_by)) {
      return { hold: prior, idempotent: true };
    }
    const current = getCurrentEnding(db, { goal, seat });
    db.prepare(
      `INSERT INTO seat_holds (goal, seat, until, ask_id, anchor, held_by, held_at, ending_stamped_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(goal, seat) DO UPDATE SET
         until = excluded.until, ask_id = excluded.ask_id, anchor = excluded.anchor,
         held_by = excluded.held_by, held_at = excluded.held_at,
         ending_stamped_at = excluded.ending_stamped_at`,
    ).run(goal, seat, until, askId, String(anchor), String(held_by),
      held_at || nowIso(), current ? String(current.stamped_at) : '');
    return { hold: getSeatHold(db, { goal, seat }), idempotent: false };
  });
}

// The explicit release. Releasing a seat that is not held is NOT an error: the hold may have been
// released by its own named change one pass earlier, and a leader that then types `release` has
// asked for exactly the state it already has.
function releaseSeat(db, { goal, seat }) {
  return tx(db, () => {
    const prior = getSeatHold(db, { goal, seat });
    if (!prior) return { released: null, idempotent: true };
    db.prepare('DELETE FROM seat_holds WHERE goal = ? AND seat = ?').run(goal, seat);
    return { released: prior, idempotent: false };
  });
}

// ── ABANDONMENT — the write half of a lane's second terminal outcome ─────────────────────────────
//
// `getSeatAbandonment` is the RAW row; there is no separate predicate (unlike `seatHeld`) because
// there is no release condition to evaluate against other rows — the row's mere presence IS the
// answer, permanently. `tables.sql`'s own header states why this is a sibling table and not a
// widened `seat_endings.ending`.
function getSeatAbandonment(db, { goal, seat }) {
  return db.prepare(
    'SELECT * FROM seat_abandonments WHERE goal = ? AND seat = ?',
  ).get(goal, seat) || null;
}

// ONE row per (goal, seat) — the PRIMARY KEY says so, and it is never replaced or deleted: dropping
// a lane has no undo path (`d-recovery-drop-is-one-lane-permanent`). A second call on an already
// -abandoned seat returns the FIRST row unchanged, idempotent on a retried write (the drop is a
// two-step act — stop live work, then mark abandoned — that must not half-complete), never a second
// ruling that could read as "abandoned again, for a different reason".
//
// ⚠ `anchor` IS RECORDED, NEVER VERIFIED — the same discipline `holdSeat` carries: an abandonment
// citing nothing is a lane nobody can later explain was dropped on purpose.
function abandonSeat(db, {
  goal, seat, anchor, abandoned_by, abandoned_at, ask_id = null,
}) {
  refuseKilled({
    goal, seat, anchor, abandoned_by,
  });
  if (!goal || !seat) throw new EndingStoreError(E_WRITER_REFUSED, 'an abandonment needs a goal and a seat');
  requireEvidence(anchor);
  if (!abandoned_by) throw new EndingStoreError(E_WRITER_REFUSED, 'an abandonment records WHO dropped the lane');
  return tx(db, () => {
    const prior = getSeatAbandonment(db, { goal, seat });
    if (prior) return { abandonment: prior, idempotent: true };
    db.prepare(
      `INSERT INTO seat_abandonments (goal, seat, anchor, abandoned_by, abandoned_at, ask_id)
       VALUES (?, ?, ?, ?, ?, ?)`,
    ).run(goal, seat, String(anchor), String(abandoned_by), abandoned_at || nowIso(), ask_id);
    return { abandonment: getSeatAbandonment(db, { goal, seat }), idempotent: false };
  });
}

module.exports = {
  getCurrentEnding,
  getGoalState,
  getAsk,
  stampSeatDeclare,
  stampSystem,
  replaceSeatEnding,
  writeGoalWord,
  insertAsk,
  postAsk,
  reapAndRelaunch,
  incrementRecoveryRelaunch,
  setLeaderAttemptUsed,
  fireNamedEvent,
  getSeatHold,
  holdSeat,
  releaseSeat,
  getSeatAbandonment,
  abandonSeat,
};
