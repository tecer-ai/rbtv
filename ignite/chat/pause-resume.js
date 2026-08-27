'use strict';

// ── THE MECHANICAL DOOR: `pause {goal}` / `resume {goal}` ─────────────────────────────────────
// Grammar + target resolution + NACK: `spec-owner-io.md` §4.2 / §4.4 / §4.5.
// What `resume` DOES to each halted kind: `spec-recovery.md` §4, the resume-semantics table
// [C-14]. Law: `DESIGN-BASELINE.md` v2 §Owner interface [T5-R14, C-14].
//
// WHY A DOOR AND NOT A MASTER PROMPT [§4.4, C-14]. Pausing a goal used to require a conversation
// with that goal's master — an agent turn, a model call, and a judgment, to perform two words that
// admit no judgment at all. A first token of `pause` or `resume` is handled by the daemon/bot and
// BYPASSES the goal master; every other owner-initiated message still goes to the master doors
// [T5-R14]. That is the entire reason this module exists.
//
// ⚑ THIS MODULE HOLDS NO STORE HANDLE AND OPENS NO DATABASE. The bridge is a separate process
//   (`probes/probe-chat-boundary.js`). The ending-store API arrives INJECTED — the object
//   `state-store/index.js#bind(db)` returns — so the reader is the one the redesign already owns
//   and the recovery semantics are CALLED, never re-implemented here.
//
// ⚑ ROW 1 OF THE RESUME TABLE IS TWO ACTS, NOT ONE. `fireNamedEvent` re-arms the ENDING row; the
//   table's "resets that counter" is the DRIVER's attempt counter (spec-recovery §5), which lives
//   in the supervisor's ledger and which `reconcile.js#counterDisarmed` reads on every pass. A
//   resume that fires only the first act reports `disarmed→armed` and leaves the lane skipped
//   forever. The second act arrives through the `rearmCounters` port below for the same
//   process-boundary reason the store does.
//
// ⚑ THERE IS NO THIRD PAUSE GRAMMAR. The owner-reply `pause` token is parsed by
//   `reply-grammar.js` (§4) and applied to the ending store's goal word (`goal_states.stored`,
//   spec-state-store §3). It is NOT `lane-watch.laneIsPaused` — that reads the legacy
//   `execution-lane` file's first token. Two readers exist during the migration; a third would be
//   one more place for the two to disagree.
//
// ⚑ PAUSE/RESUME NEVER RELEASES AN ASK [§4.2]. Neither verb writes `open_asks`. An owner who
//   pauses a goal that is waiting on a question is still owed that question's answer, and the ask
//   must still read `open` to every digest, status line and kill clock afterwards.

const { parseReply, NACK_MECHANICAL } = require('./reply-grammar');

// The diagnostics the resume-semantics table has a row for (spec-state-store's
// `LISTED_INCOMPLETE` keys — quoted, not imported: this module may not reach a sibling tree).
const D_BLOCKED_ON_HUMAN = 'blocked-on-human';
const D_GATE_CAP = 'gate-re-plan cap';
const D_COUNTER_EXHAUSTION = 'attempt-counter exhaustion';
const NAMED_EXTERNAL_INPUT = 'named-external-input';

// Authored refusal prose (NOT spec-verbatim — §4.5's two NACKs answer an UNPARSED verb; these two
// answer a verb that parsed and named a live goal whose halt `resume` deliberately does not lift).
function blockedOnHumanRefusal(seat, askIds) {
  const where = askIds.length ? ` Answer it in its thread: ${askIds.join(', ')}.` : '';
  return `resume does not lift ${seat}: it is halted waiting on an open ask, and only an authorized reply in that thread releases it.${where}`;
}

function gateCapRefusal(seat) {
  return `resume does not lift ${seat}: it stopped at the re-plan cap. Answer the gate decision-ask — resume does not open a third re-plan.`;
}

function createPauseResume({
  // The bound ending-store API (`state-store/index.js#bind(db)`). Duck-typed on purpose: this
  // module names the four calls it makes and nothing else, so it can be driven by the real store
  // or by whatever process ends up holding the handle.
  store = null,
  // `listSeats(goal) -> [seatName]`. The ending store has no "every lane of this goal" reader
  // today, and inventing one here would be a second source of that fact — so the enumerator is
  // the embedder's, and a missing one means resume applies the GOAL row only.
  listSeats = null,
  // `rearmCounters(goal) -> [{subject, seat, driver, reason_class, attempts}]` — the OTHER half of
  // resume-semantics row 1. The table says resume "re-arms that driver; resets that counter", and
  // the counter is NOT the ending row: it is the supervisor's attempt-counter ledger, which
  // `reconcile.js#counterDisarmed` reads on every pass and which `fireNamedEvent` does not touch.
  // A lane re-armed on the ending row alone is still skipped by the reconcile loop — that gap is
  // why seven lanes on this instance were permanently disarmed (2026-08-27).
  //
  // ⚑ INJECTED FOR THE SAME REASON `store` IS, and this is a WALL, not a preference. The ledger is
  //   DAEMON state and this is a separate process: `probes/probe-chat-boundary.js` forbids this
  //   subtree a store handle, a child process and a sibling require, and the build memory records
  //   what happens to a migration that reaches through it anyway (entry
  //   `20260824-i-open-asks-has-no-boundary-lega`, reverted whole). The daemon-side implementation
  //   is `supervisor/exhaustion.js#rearmScope`; wiring it into THIS process needs a gateway intent,
  //   which is an owner-ruled act. With no port the counter half simply does not happen and the
  //   door says so, exactly as it already does for the unwired store.
  rearmCounters = null,
  // Posts a line back where the verb arrived: in-thread when it came in a thread, otherwise as a
  // reply to the command message. Required — a mechanical verb that answers nothing is the
  // silence [F-owner-ux-2] forbids.
  post,
  // Every ending-store write carries one (`evidence_pointer` is NOT NULL and non-empty).
  evidencePointer = (verb, goal) => `owner ${verb} in chat · goal ${goal}`,
  logger = null,
} = {}) {
  if (typeof post !== 'function') throw new Error('createPauseResume requires post — a mechanical verb must answer where it arrived');
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  function seatsOf(goal) {
    if (typeof listSeats !== 'function') return [];
    try { return (listSeats(goal) || []).map(String); } catch (err) {
      log('warn', 'could not enumerate the goal\'s lanes — resume applies the goal row only', { goal, error: err.message });
      return [];
    }
  }

  // The counter half's one call site. A port that throws must not cost the owner the rest of the
  // table — the failure becomes a refusal the door posts, never an exception that eats the verb.
  function rearmCounterRows(goal) {
    if (typeof rearmCounters !== 'function') return { cleared: [], error: null };
    try {
      const out = rearmCounters(goal);
      return { cleared: Array.isArray(out) ? out : [], error: null };
    } catch (err) {
      log('warn', 'the attempt-counter re-arm port refused — resume\'s counter half did not happen', { goal, error: err.message });
      return { cleared: [], error: err.message };
    }
  }

  // `pause {goal}` is the inverse of the paused-goal row ONLY (spec-recovery §4): flip
  // `running` → `paused`. It does not disarm a lane and it does not open an ask.
  function applyPause(goal) {
    if (!store) return { applied: false, reason: 'no-store', actions: [], refusals: [] };
    const before = store.getGoalState(goal);
    if (before && before.stored === 'paused') {
      return { applied: true, actions: [{ row: 'goal', change: 'already-paused', goal }], refusals: [] };
    }
    if (before && before.stored === 'finished') {
      return { applied: false, reason: 'finished', actions: [], refusals: [{ row: 'goal', text: `${goal} is finished — there is nothing to pause.` }] };
    }
    store.writeGoalWord({ goal, stored: 'paused', who_stamped: 'owner', evidence_pointer: evidencePointer('pause', goal) });
    return { applied: true, actions: [{ row: 'goal', change: 'running→paused', goal }], refusals: [] };
  }

  // `resume {goal}` — the resume-semantics table [C-14], EVERY MATCHING ROW. A goal may carry
  // more than one halted kind at once, and each row is independent: the goal flipping to
  // `running` does not re-arm a counter-exhausted lane, and a lane refusing to be lifted does not
  // stop the goal word from flipping.
  function applyResume(goal) {
    const actions = [];
    const refusals = [];

    // ROW 1, THE COUNTER HALF. It runs FIRST and it runs whether or not a store is wired, because
    // it is the half the reconcile loop reads: a lane whose counter still stands at N is skipped
    // on every pass no matter what the ending row says.
    const counter = rearmCounterRows(goal);
    for (const row of counter.cleared) {
      actions.push({
        row: 'counter',
        seat: row.seat || row.subject,
        driver: row.driver,
        reason_class: row.reason_class,
        attempts: row.attempts,
        change: 'counter reset',
      });
    }
    if (counter.error) refusals.push({ row: 'counter', text: `${goal}: the attempt counters were NOT re-armed — ${counter.error}` });

    if (!store) {
      // The goal word and every lane ending need the store this process does not hold. Say which
      // half happened rather than answering as if the whole row did.
      refusals.push({ row: 'no-store', text: `${goal}: no ending-store port is wired in this process — the goal word and the lane endings were not touched.` });
      return {
        applied: counter.cleared.length > 0,
        ...(counter.cleared.length ? {} : { reason: 'no-store' }),
        actions,
        refusals,
      };
    }

    // ROW 4 — paused goal: flip `paused` → `running`. Armed eligible lanes may then launch; a
    // disarmed one stays disarmed until its own row (or another named re-arm) consumes the flag.
    const goalState = store.getGoalState(goal);
    if (goalState && goalState.stored === 'paused') {
      store.writeGoalWord({ goal, stored: 'running', who_stamped: 'owner', evidence_pointer: evidencePointer('resume', goal) });
      actions.push({ row: 'goal', change: 'paused→running', goal });
    } else if (goalState && goalState.stored === 'finished') {
      refusals.push({ row: 'goal', text: `${goal} is finished — resume does not reopen a finished goal.` });
    }

    for (const seat of seatsOf(goal)) {
      let current = null;
      try { current = store.getCurrentEnding({ goal, seat }); } catch { current = null; }
      if (!current || current.ending !== 'incomplete' || Number(current.armed) !== 0) continue;
      const diagnostic = String(current.diagnostic || '');

      // ROW 2 — `incomplete: blocked-on-human`: NACK pointing at the open ask thread. Resume is
      // NOT a substitute for an authorized reply and does not reap the ask.
      if (diagnostic === D_BLOCKED_ON_HUMAN) {
        let askIds = [];
        try { askIds = (store.listOpenAsks({ goal, seat }) || []).map((a) => String(a.ask_id)); } catch { askIds = []; }
        refusals.push({ row: 'blocked-on-human', seat, text: blockedOnHumanRefusal(seat, askIds), asks: askIds });
        continue;
      }

      // ROW 3 — gate-cap stop (two failed D13s): NACK pointing at the gate decision-ask. Resume
      // does not open a third re-plan and does not flip the cap.
      if (diagnostic === D_GATE_CAP) {
        refusals.push({ row: 'gate-cap', seat, text: gateCapRefusal(seat) });
        continue;
      }

      // ROW 1 — disarmed `incomplete:` from attempt-counter exhaustion: re-arm that driver via the
      // NAMED RE-ARM EVENT the store already models (spec-recovery §5's closed list names
      // "mechanical `resume {goal}` on a disarmed-counter lane"). `fireNamedEvent` is the one
      // writer of that flag — the counter is CONSUMED here, and the relaunch budget
      // (`recovery_relaunch_count`) is deliberately left where it stands.
      if (diagnostic === D_COUNTER_EXHAUSTION || current.named_event === NAMED_EXTERNAL_INPUT) {
        try {
          store.fireNamedEvent({ goal, seat, named_event: NAMED_EXTERNAL_INPUT });
          actions.push({ row: 'counter-exhaustion', seat, change: 'disarmed→armed', named_event: NAMED_EXTERNAL_INPUT });
        } catch (err) {
          refusals.push({ row: 'counter-exhaustion', seat, text: `could not re-arm ${seat}: ${err.message}` });
        }
        continue;
      }
      // Any other disarmed diagnostic has NO row in the table — it is left exactly as it is, and
      // said so, rather than lifted by a rule nobody wrote.
      refusals.push({ row: 'no-row', seat, text: `resume has no rule for ${seat} (${diagnostic || 'disarmed'}) — left untouched.` });
    }
    return { applied: true, actions, refusals };
  }

  function summarize(verb, goal, out) {
    const lines = [];
    if (out.actions.length === 0 && out.refusals.length === 0) {
      lines.push(`${verb} ${goal}: nothing to change.`);
    }
    for (const a of out.actions) {
      if (a.row === 'goal' && a.change === 'already-paused') lines.push(`${goal} was already paused.`);
      else if (a.row === 'goal') lines.push(`${goal}: ${a.change}.`);
      else if (a.row === 'counter') lines.push(`${a.seat}: attempt counter re-armed (${a.reason_class}, was ${a.attempts}).`);
      else lines.push(`${a.seat}: re-armed (${a.change}).`);
    }
    for (const r of out.refusals) lines.push(r.text);
    return lines.join('\n');
  }

  // ── THE DOOR ────────────────────────────────────────────────────────────────────────────────
  //
  // `text` is the owner's raw message. `channelGoal` is the goal this channel belongs to (null in
  // the system channel and in a DM, which is exactly why the slug is required there). `liveGoals`
  // is the live-goal name list the slug must resolve against — a slug that matches ZERO or SEVERAL
  // is the ambiguity §4.5 answers with its verbatim mechanical NACK.
  //
  // Returns `{mechanical:false}` when the first token is not `pause`/`resume` — the caller then
  // continues to whatever door it would otherwise have used, unchanged [T5-R14].
  async function handle({ text, channelId, threadTs = null, channelGoal = null, liveGoals = null }) {
    const parsed = parseReply(text, { channelGoal, liveGoals });

    // A parse failure is only OURS when the first token really was `pause`/`resume`; anything else
    // is not this door's message and must not be answered with this door's NACK.
    if (!parsed.ok) {
      if (parsed.nackKind !== 'mechanical') return { mechanical: false };
      await post({ channelId, threadTs, goalId: channelGoal, text: NACK_MECHANICAL });
      log('info', 'mechanical verb could not be targeted — verbatim §4.5 NACK posted, NOTHING changed', { channelGoal });
      return { mechanical: true, ok: false, nacked: true, nack: NACK_MECHANICAL, applied: false };
    }
    if (parsed.family !== 'mechanical') return { mechanical: false };

    const goal = parsed.goal;
    const verb = parsed.outcome;
    // `pause` writes the goal word and nothing else, so with no store it has no applier at all.
    // `resume` has TWO appliers — the ending store and the counter ledger — and either one wired
    // is a verb worth running: the counter half is the half the reconcile loop reads.
    const hasApplier = store || (verb === 'resume' && typeof rearmCounters === 'function');
    if (!hasApplier) {
      // No applier is wired in this process yet. Say so rather than answer as if it worked — a
      // silent success is how an owner learns to trust a door that does nothing.
      log('warn', 'mechanical verb parsed and targeted, but NO applier port is wired in this process — nothing applied', { verb, goal });
      return { mechanical: true, ok: false, applied: false, reason: 'no-store', verb, goal, comments: parsed.comments };
    }

    const out = verb === 'pause' ? applyPause(goal) : applyResume(goal);
    await post({ channelId, threadTs, goalId: goal, text: summarize(verb, goal, out) });
    log('info', `mechanical ${verb} applied`, {
      goal, actions: out.actions.map((a) => a.row), refusals: out.refusals.map((r) => r.row),
    });
    return {
      mechanical: true,
      ok: out.applied === true,
      applied: out.applied === true,
      verb,
      goal,
      // [C-14] an approval-thread `resume {goal}` WITH comments is resume-with-instructions; the
      // instructions ride out to the caller rather than being interpreted here.
      comments: parsed.comments,
      instructions: parsed.comments ? parsed.comments : null,
      actions: out.actions,
      refusals: out.refusals,
    };
  }

  return { handle, applyPause, applyResume };
}

module.exports = {
  createPauseResume,
  NACK_MECHANICAL,
  D_BLOCKED_ON_HUMAN,
  D_GATE_CAP,
  D_COUNTER_EXHAUSTION,
  NAMED_EXTERNAL_INPUT,
  blockedOnHumanRefusal,
  gateCapRefusal,
};
