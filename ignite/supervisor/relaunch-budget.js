'use strict';

// -- THE RECOVERY RELAUNCH BUDGET AND THE LEADER HANDOFF [T1-R6, C-11, T4-R6, CF-3, D6] ---------
//
// WHAT THE BUDGET COUNTS, and the sentence is short because every extra thing counted is a lane
// that stops early: RECOVERY relaunches only - a kill, a crash, or the relaunch of an ARMED
// `incomplete` lane. Two caps, whichever trips first: `relaunch_budget_failures` (seeded 2) and
// `relaunch_budget_total` (seeded 5), both read from the recovery config file, never literals.
//
// EACH `failed` COUNTS AGAINST BOTH CAPS. It is a failure AND it is a relaunch, so it advances
// `failure_strike_count` and `recovery_relaunch_count`. Nothing double-counts: the ending store
// advances the strike when the `failed` row is stamped, and `spendRecoveryRelaunch` advances the
// total when the relaunch is actually made.
//
// AN ASK-RESUME NEVER SPENDS IT [C-11]. That is not a branch in this file - it is the ABSENCE of
// one: the resume path (`exhaustion.js#consumeDisarmed`, and the store's own `reapAndRelaunch`)
// never calls anything here. `spendRecoveryRelaunch` additionally REFUSES a non-recovery cause, so
// a future caller cannot route an ask-resume through it by accident.
//
// BUDGET AND ATTEMPT-COUNTER ARE INDEPENDENT [spec-recovery 2]. Whichever trips first takes its
// exit and the other does not also fire in the same act. This file therefore has no knowledge of
// the counter at all, and the caller that holds both asks the budget FIRST and returns.
//
// THE EXIT: ONE BOUNDED D6 LEADER ATTEMPT. The lane stops, the leader gets exactly one attempt,
// and it is spent only on PRODUCING AN ENDING - never on merely resuming a seat off an answered
// ask. `leader_attempt_used` on the ending row is the bound, and `leaderHandoff` sets it in the
// same act that assembles the payload, so a second handoff cannot be assembled at all.
//
// LEADER DECIDES, DAEMON EXECUTES [CF-3, T2-R5, D7]. The leader REPORTS one of four instructions;
// `executeLeaderInstruction` is the daemon act that applies it. The leader never executes the
// seat's work, and this file enforces that literally: an instruction carrying seat work is
// refused, because the only thing a leader may hand back is a judgment.

const fs = require('node:fs');
const path = require('node:path');
const checkpoint = require('./checkpoint');
const exhaustion = require('./exhaustion');

// The three causes that spend the budget [T1-R6]. `ask-resume` is not one, and is refused by name
// rather than by falling through, so the refusal message names the ruling.
const RECOVERY_CAUSES = Object.freeze(['kill', 'crash', 'armed-incomplete']);
const FREE_CAUSES = Object.freeze(['ask-resume']);

// The four things a leader may report [D6, T4-R6]. Closed: a fifth would be a remedy verb nobody
// ruled [T2-R5].
const INSTRUCTIONS = Object.freeze({
  REWRITE_BRIEF: 'rewrite-brief',
  REASSIGN: 'reassign',
  BLOCKED_PENDING_PLAN_GAP: 'blocked-pending-plan-gap',
  ESCALATE: 'escalate',
});
const INSTRUCTION_LIST = Object.freeze(Object.values(INSTRUCTIONS));

class RelaunchBudgetError extends Error {
  constructor(message) {
    super(message);
    this.name = 'RelaunchBudgetError';
    this.code = 'E_RELAUNCH_BUDGET';
  }
}

// -- THE READ - both caps off the ending row's own store-visible counters -----------------------
//
// No second ledger. `failure_strike_count` and `recovery_relaunch_count` are fields spec-state-
// store already pins on every current ending row, so the budget is answered from the same row the
// scheduler reads and cannot disagree with it.
function budgetState({ store, goal, seat }, config) {
  const capFailures = config && config.relaunch_budget_failures;
  const capTotal = config && config.relaunch_budget_total;
  if (!Number.isInteger(capFailures) || !Number.isInteger(capTotal)) {
    throw new RelaunchBudgetError(
      'both relaunch budget caps must come from the recovery config file [spec-recovery 2.1] - no in-code default',
    );
  }
  const row = store.getCurrentEnding({ goal, seat });
  const failures = row ? Number(row.failure_strike_count) : 0;
  const total = row ? Number(row.recovery_relaunch_count) : 0;
  // Whichever trips FIRST. Failures is checked first only so the reported `tripped` names the
  // tighter cap when both are at their bound - the exit is the same either way.
  let tripped = null;
  if (failures >= capFailures) tripped = 'failures';
  else if (total >= capTotal) tripped = 'total';
  return {
    goal, seat, failures, total, capFailures, capTotal, exhausted: Boolean(tripped), tripped,
  };
}

// -- THE SPEND ----------------------------------------------------------------------------------
//
// Called at the moment a recovery relaunch ACTUALLY HAPPENS, never when one is merely considered:
// a budget that decrements on intent stops lanes that never got relaunched.
function spendRecoveryRelaunch({
  store, goal, seat, cause,
}) {
  if (FREE_CAUSES.includes(cause)) {
    throw new RelaunchBudgetError(
      `${cause} never spends the recovery relaunch budget [C-11] - do not route it through this door`,
    );
  }
  if (!RECOVERY_CAUSES.includes(cause)) {
    throw new RelaunchBudgetError(`unknown relaunch cause: ${cause} (recovery causes: ${RECOVERY_CAUSES.join(', ')})`);
  }
  return store.incrementRecoveryRelaunch({ goal, seat });
}

// -- THE HANDOFF PAYLOAD - every field [T4-R6] --------------------------------------------------
//
// The seat's brief, BOTH sittings' progress notes, the kill reasons, and pointers to the
// transcripts. All four are required and the assembly REFUSES a missing one: a leader handed a
// payload with a hole spends its one bounded attempt guessing, and that attempt does not come
// back. A note is read off disk through the checkpoint contract (`progress-note.md` in the seat
// folder) so the leader reads the same three fields the seat wrote.
function readNote(seatDir) {
  if (!seatDir) return null;
  try {
    // `readProgressNote` returns the note's TEXT (the three fields as the seat wrote them), or
    // null when that sitting never wrote one - which is itself a fact the leader needs.
    const note = checkpoint.readProgressNote(seatDir);
    return note ? { seat_dir: seatDir, note } : { seat_dir: seatDir, note: null, missing: true };
  } catch {
    return { seat_dir: seatDir, missing: true };
  }
}

function assembleHandoff({
  store, goal, seat, brief, sittingDirs = [], progressNotes = null, killReasons = [], transcriptPointers = [],
}, config) {
  if (!brief) throw new RelaunchBudgetError('the leader handoff requires the seat brief [T4-R6]');
  const notes = progressNotes || sittingDirs.map(readNote);
  if (!Array.isArray(notes) || notes.length < 2) {
    throw new RelaunchBudgetError('the leader handoff requires BOTH sittings\' progress notes [T4-R6]');
  }
  if (!Array.isArray(killReasons) || killReasons.length === 0) {
    throw new RelaunchBudgetError('the leader handoff requires the kill reasons [T4-R6]');
  }
  if (!Array.isArray(transcriptPointers) || transcriptPointers.length === 0) {
    throw new RelaunchBudgetError('the leader handoff requires the transcript pointers [T4-R6]');
  }
  return {
    goal,
    seat,
    seat_brief: brief,
    progress_notes: notes,
    kill_reasons: [...killReasons],
    transcript_pointers: [...transcriptPointers],
    budget: budgetState({ store, goal, seat }, config),
    attempt: 'one-bounded-d6',
    // Spelled ON the payload so the leader reads its own closed option set rather than inventing a
    // fifth verb [T2-R5].
    instruction_kinds: [...INSTRUCTION_LIST],
    may_execute_seat_work: false,
  };
}

// The whole exit, in one call: the lane stops, the one D6 attempt is marked used, and the payload
// comes back for the caller to hand over. `setLeaderAttemptUsed` is what BOUNDS the rung - a
// second call finds `leader_attempt_used` already 1 and is refused here.
function leaderHandoff(fields, config) {
  const { store, goal, seat } = fields;
  const row = store.getCurrentEnding({ goal, seat });
  if (row && Number(row.leader_attempt_used) === 1) {
    throw new RelaunchBudgetError(
      `the one bounded D6 leader attempt is already spent on ${goal}/${seat} [T1-R8] - the next rung is the owner ask`,
    );
  }
  const payload = assembleHandoff(fields, config);
  const ending = store.setLeaderAttemptUsed({ goal, seat });
  return { payload, ending };
}

// -- THE DAEMON'S EXECUTE-A-LEADER-INSTRUCTION ACT ----------------------------------------------
//
// Four kinds, each a mechanical act with no judgment left in it. The judgment already happened -
// the leader made it - and this function's whole job is to be the only place it is performed.
function executeLeaderInstruction({
  store, workspaceRoot, goal, seat, instruction, at,
}) {
  const kind = instruction && instruction.kind;
  if (!INSTRUCTION_LIST.includes(kind)) {
    throw new RelaunchBudgetError(`unknown leader instruction: ${kind} (closed list: ${INSTRUCTION_LIST.join(', ')})`);
  }
  // THE WALL [CF-3, T2-R5]. A leader reports; it never does the seat's work. A payload carrying
  // work product - a patch, a file body, an output - is a leader that executed, and the daemon
  // refuses to launder it into an act.
  if (instruction.work_product || instruction.patch || instruction.outputs) {
    throw new RelaunchBudgetError(
      'a leader instruction may carry a judgment, never the seat\'s work [CF-3, T2-R5] - refused',
    );
  }
  const stamp = at || new Date().toISOString();

  if (kind === INSTRUCTIONS.REWRITE_BRIEF) {
    // The brief is rewritten on disk and the lane is re-armed for the ONE authorized relaunch.
    // The write is the daemon's; the words are the leader's.
    if (!instruction.brief || !instruction.brief_path) {
      throw new RelaunchBudgetError('rewrite-brief needs the new brief and the path it lands at');
    }
    fs.mkdirSync(path.dirname(path.resolve(instruction.brief_path)), { recursive: true });
    fs.writeFileSync(path.resolve(instruction.brief_path), instruction.brief, 'utf8');
    const ending = store.stampSystem({
      goal,
      seat,
      ending: 'incomplete',
      armed: 1,
      diagnostic: 'leader rewrote the brief',
      evidence_pointer: path.resolve(instruction.brief_path),
      stamped_at: stamp,
      replace: true,
    });
    return {
      kind, executed: true, brief_path: path.resolve(instruction.brief_path), ending,
    };
  }

  if (kind === INSTRUCTIONS.REASSIGN) {
    // A different seat design takes the work. The old lane's ending is the leader's judgment
    // recorded against it; the new lane is launched by the ordinary door, not from here.
    if (!instruction.to_seat) throw new RelaunchBudgetError('reassign needs the seat design it reassigns to');
    const ending = store.stampSystem({
      goal,
      seat,
      ending: 'incomplete',
      armed: 1,
      diagnostic: `leader reassigned to ${instruction.to_seat}`,
      evidence_pointer: instruction.evidence_pointer || `reassign:${goal}/${seat}->${instruction.to_seat}`,
      stamped_at: stamp,
      replace: true,
    });
    return {
      kind, executed: true, to_seat: instruction.to_seat, ending,
    };
  }

  if (kind === INSTRUCTIONS.BLOCKED_PENDING_PLAN_GAP) {
    // The gap is in the PLAN, not the seat. The daemon records the D13 scoped re-plan request; the
    // re-plan pipeline itself is spec-planning-door's, and this act deliberately stops at the
    // request so a recovery path never mints a plan.
    const target = path.resolve(workspaceRoot, exhaustion.ASKS_REL, '..', 'replan-requests');
    fs.mkdirSync(target, { recursive: true });
    const file = path.join(target, `${goal}--${seat}.json`);
    fs.writeFileSync(file, `${JSON.stringify({
      goal, seat, kind: 'd13-scoped-replan', milestone: instruction.milestone || null,
      gap: instruction.gap || '', requested_at: stamp,
    }, null, 2)}\n`, 'utf8');
    const ending = store.stampSystem({
      goal,
      seat,
      ending: 'incomplete',
      armed: 0,
      diagnostic: 'materialize-failed',   // the store's listed disarmed row for a plan-side halt
      evidence_pointer: file,
      stamped_at: stamp,
      replace: true,
    });
    return {
      kind, executed: true, replan_request: file, ending,
    };
  }

  // ESCALATE - a formed decision-ask to the owner, recorded and NOT posted. Same record shape and
  // the same grouping rule as the attempt-counter exit, so the owner sees one ask per signature
  // whichever rung produced it.
  const ask = exhaustion.recordGroupedAsk({
    store,
    workspaceRoot,
    goal,
    seat,
    driver: instruction.driver || 'reconcile-class-a-relaunch',
    reasonClass: instruction.reason_class || 'leader-escalation',
    refusalText: instruction.report || '',
    at: stamp,
  });
  return { kind, executed: true, ask };
}

module.exports = {
  RECOVERY_CAUSES,
  FREE_CAUSES,
  INSTRUCTIONS,
  INSTRUCTION_LIST,
  RelaunchBudgetError,
  budgetState,
  spendRecoveryRelaunch,
  assembleHandoff,
  leaderHandoff,
  executeLeaderInstruction,
};
