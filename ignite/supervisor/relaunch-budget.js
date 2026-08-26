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
//
// -- HOW THE ASK GOES OUT AND HOW THE ANSWER COMES BACK [B11] -----------------------------------
//
// UNTIL 2026-08-26 NEITHER HALF EXISTED. `leaderHandoff` and `executeLeaderInstruction` were
// exported and had NO production caller anywhere in the repo - a grep returned the definitions,
// the export block and the selftest, and nothing else. So the exit described above was never
// taken: no handoff was ever assembled, the leader was never asked, and the four instructions
// were a closed list nobody could report from.
//
// THE ASK rides the door the daemon ALREADY uses to put a question in front of the leader: the
// watcher's leader wake (`reconcile.js`, D33(a)), which appends a block to the leader's own boot
// prompt. `handoffPayloadText` below is that block. Nothing new transports it.
//
// THE ANSWER is a JSON file the leader writes and this module drains - `leader-instructions/
// <goal>--<seat>.json`, beside the ask records, in the same shape and for the same reason
// `blocked-pending-plan-gap` already writes `replan-requests/`. It is a FILE and not a CLI verb
// because there is no ruling instrument left to carry it: `rule-disposition` was deleted [T2-R12,
// T1-R9] and nothing replaced it. `drainLeaderInstructions` reads each pending file, applies it
// through `executeLeaderInstruction` - the ONE place an instruction is ever performed - and moves
// the file out of the pending directory so a repeating pass cannot apply the same judgment twice.

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

// -- THE ASK: THE BLOCK THE LEADER READS [B11] --------------------------------------------------
//
// Every field of the payload, in prose, plus the ONE thing the payload cannot carry - where to
// write the answer and in what shape. Kept here beside `executeLeaderInstruction` so the wording
// of the ask and the closed list it is answered from can never drift apart: both read
// `INSTRUCTION_LIST`.
function handoffPayloadText(payload, answerPath) {
  const notes = (payload.progress_notes || []).map((n, i) => {
    const where = n.sitting ? `sitting \`${n.sitting}\`` : `sitting ${i + 1}`;
    return n.note
      ? `- ${where} — progress note:\n\n\`\`\`\n${String(n.note).trim()}\n\`\`\``
      : `- ${where} — NO progress note on disk${n.why ? ` (${n.why})` : ''}`;
  });
  return [
    '',
    '',
    '---',
    '',
    `## The relaunch budget for \`${payload.seat}\` is EXHAUSTED — one bounded decision is yours`,
    '',
    `The recovery relaunch budget on \`${payload.goal}/${payload.seat}\` has run out `
      + `(${payload.budget.failures}/${payload.budget.capFailures} failures, `
      + `${payload.budget.total}/${payload.budget.capTotal} relaunches; the \`${payload.budget.tripped}\` `
      + 'cap tripped first). The lane has STOPPED. The daemon will not relaunch that seat again on '
      + 'its own, and this ask is not repeated: you get ONE attempt, it is already marked used, and '
      + 'the next rung after it is an ask to the owner.',
    '',
    'YOU REPORT A JUDGMENT; THE DAEMON EXECUTES IT. Do not do the seat\'s work, do not write its '
    + 'outputs, do not patch anything on its behalf — an instruction carrying work product is '
    + 'REFUSED by the daemon rather than laundered into an act.',
    '',
    '### The seat\'s brief',
    '',
    '```',
    String(payload.seat_brief).trim(),
    '```',
    '',
    '### What the sittings left behind',
    '',
    ...notes,
    '',
    `Kill reasons: ${payload.kill_reasons.join(' · ')}`,
    `Transcripts: ${payload.transcript_pointers.join(' · ')}`,
    '',
    '### Report ONE of these four, and nothing else',
    '',
    `    ${INSTRUCTIONS.REWRITE_BRIEF}            the brief was wrong — you supply the new one, the daemon writes it and re-arms the lane ONCE`,
    `    ${INSTRUCTIONS.REASSIGN}                 a different seat design takes the work`,
    `    ${INSTRUCTIONS.BLOCKED_PENDING_PLAN_GAP} the gap is in the PLAN, not the seat — the daemon records a scoped re-plan request`,
    `    ${INSTRUCTIONS.ESCALATE}                 nobody here can decide this — the daemon records a decision-ask for the owner`,
    '',
    '### How to report it',
    '',
    'Write this file (create the directory if it is absent). The daemon drains it on its next',
    'reconcile pass over this goal, applies it, and moves the file aside:',
    '',
    `    ${answerPath}`,
    '',
    '```json',
    JSON.stringify({
      kind: INSTRUCTIONS.REWRITE_BRIEF,
      brief: '<the new brief text — rewrite-brief only>',
      brief_path: '<absolute path the brief lands at — rewrite-brief only>',
      to_seat: '<the seat design that takes over — reassign only>',
      milestone: '<milestone id — blocked-pending-plan-gap only>',
      gap: '<what the plan is missing — blocked-pending-plan-gap only>',
      report: '<the decision-ask text — escalate only>',
    }, null, 2),
    '```',
    '',
    'Keep only the keys your chosen `kind` uses. A key carrying the seat\'s WORK',
    '(`work_product`, `patch`, `outputs`) is refused.',
    '',
  ].join('\n');
}

// -- THE ANSWER: WHERE THE LEADER WRITES IT, AND THE DRAIN THAT APPLIES IT [B11] ----------------
//
// Beside the ask records [spec-state-store 1.1], workspace-relative and GENERAL - no instance path
// is spelled anywhere in this repo.
const LEADER_INSTRUCTIONS_REL = path.join('.rbtv', 'runtime', 'ignite', 'leader-instructions');

function leaderInstructionsDir(workspaceRoot) {
  if (!workspaceRoot) throw new RelaunchBudgetError('leaderInstructionsDir requires workspaceRoot');
  return path.resolve(workspaceRoot, LEADER_INSTRUCTIONS_REL);
}

// One file per (goal, seat): the ask is bounded to one attempt per lane, so a second pending file
// for the same lane cannot be a second judgment - it is the same one, rewritten.
function leaderInstructionPath(workspaceRoot, goal, seat) {
  return path.join(leaderInstructionsDir(workspaceRoot), `${goal}--${seat}.json`);
}

// THE DRAIN. Applies every pending instruction for ONE goal and gets the file OUT of the pending
// directory in the same act - `done/` on success, `refused/` with the refusal text beside it
// otherwise. A file that stayed would be re-applied on every cadence, which for `rewrite-brief` is
// a lane re-armed forever and for `escalate` is an ask re-opened forever.
function drainLeaderInstructions({
  store, workspaceRoot, goal, at, seats = null,
}) {
  const dir = leaderInstructionsDir(workspaceRoot);
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];              // no directory is the ordinary state: no leader has answered anything
  }
  const out = [];
  const prefix = `${goal}--`;
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith('.json')) continue;
    if (!entry.name.startsWith(prefix)) continue;
    const seat = entry.name.slice(prefix.length, -'.json'.length);
    if (seats && !seats.includes(seat)) continue;
    const src = path.join(dir, entry.name);
    let instruction;
    try {
      instruction = JSON.parse(fs.readFileSync(src, 'utf8'));
    } catch (err) {
      out.push(settleInstruction(dir, src, 'refused', {
        goal, seat, applied: false, error: `unreadable JSON: ${err.message}`,
      }));
      continue;
    }
    try {
      const result = executeLeaderInstruction({
        store, workspaceRoot, goal, seat, instruction, at,
      });
      out.push(settleInstruction(dir, src, 'done', {
        goal, seat, applied: true, kind: result.kind, result,
      }));
    } catch (err) {
      out.push(settleInstruction(dir, src, 'refused', {
        goal, seat, applied: false, error: err.message,
      }));
    }
  }
  return out;
}

// The file leaves the pending directory whichever way it went, and the outcome is written beside
// it - a refused instruction the leader can never see is a judgment silently dropped.
function settleInstruction(dir, src, outcome, record) {
  const target = path.join(dir, outcome);
  fs.mkdirSync(target, { recursive: true });
  const base = path.basename(src, '.json');
  const moved = path.join(target, `${base}.json`);
  try {
    fs.renameSync(src, moved);
    fs.writeFileSync(path.join(target, `${base}.outcome.json`),
      `${JSON.stringify({ ...record, outcome }, null, 2)}\n`, 'utf8');
  } catch (err) {
    return { ...record, outcome, settle_error: err.message };
  }
  return { ...record, outcome, file: moved };
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
  handoffPayloadText,
  LEADER_INSTRUCTIONS_REL,
  leaderInstructionsDir,
  leaderInstructionPath,
  drainLeaderInstructions,
};
