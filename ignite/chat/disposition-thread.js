'use strict';

// ── THE DISPOSITION THREAD: WHAT EACH OF THE TWO RULED OPTIONS DOES ───────────────────────────────
// `d-recovery-last-lane-asks` + `d-recovery-waiting-goal-freeze` (owner ruling, 2026-08-31): when a
// goal's last owed lane is dropped, the owner is asked once — close this goal, or keep it open?
// `ask-thread.js#release`'s exact-thread match already tells two goals' asks apart; nothing here
// re-derives that. What differs from `recovery-thread.js` is only the vocabulary (`close`/`keep`,
// not the three-rung recovery ladder) and what each outcome does after the parse — kept in its own
// module for `recovery-thread.js`'s own reason: the parser is ONE (`reply-grammar.js`, kind-gated)
// and the release rule is ONE (`ask-thread.js#release`); only the post-parse effect differs.
//
// ⚑ EVERY EFFECT IS AN INJECTED PORT, `recovery-thread.js`'s own reason: the bridge is a separate
//   process (`probes/probe-chat-boundary.js`) and may not write `goal_states` itself.
//
// ⚑ `keep` NEEDS NO PORT. The ask's own release (`ask-thread.js#release`, called before this
//   dispatch ever runs) already reaped the ask — that IS the entire meaning of "keep": nothing more
//   is owed and nothing launches on its own, so the owner-visible half is already done the moment
//   the reply parsed. This dispatch only posts the confirmation.
//
// ⚑ `close` HAS NO daemon-side act TODAY, and NOT because nobody wired it — `state-store/
//   vocabulary.js#GOAL_WORDS` is a closed three-word enum (`running`/`paused`/`finished`), and
//   `finished` is the ONLY terminal word, always read as ordinary success (`isGoalFinished`,
//   every downstream reader of goal state). Stamping it here would make a goal the owner explicitly
//   gave up on read as done — the exact outcome `d-recovery-last-lane-asks` forbids ("a goal given
//   up on must never read as done"). A fourth terminal word (or equivalent) is a state-store
//   vocabulary decision with its own blast radius across every reader of goal state; it is not this
//   seat's to invent. `closeGoal` is therefore left UNWIRED (`null`, the same shape `dropLane`/
//   `retryWithChange` carried before their own seats built them) and this door reports that
//   honestly into the thread — never a silent success, per this ruling's own words: "under no shape
//   does a timeout, a default, or silence close the goal."

function call(port, name, args) {
  if (typeof port !== 'function') return Promise.resolve({ ok: false, error: `no ${name} port is wired` });
  return Promise.resolve(port(args)).then(
    (out) => ((out && out.ok === true) ? out : { ok: false, error: (out && (out.error || out.reason)) || `${name} refused`, result: out }),
    (err) => ({ ok: false, error: err.message }),
  );
}

function createDispositionDispatch({
  closeGoal = null,
  // Posts a line back into the disposition thread — the ONE reporting path an owner watching that
  // thread has, exactly [C-16]'s reason in `approval-thread.js` / `recovery-thread.js`.
  postBack,
  logger = null,
} = {}) {
  if (typeof postBack !== 'function') {
    throw new Error('createDispositionDispatch requires postBack — the outcome is reported into the disposition thread, same as a recovery outcome');
  }
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  async function say({ channelId, goalId, askId, text }) {
    return postBack({ channelId, goalId, askId, text });
  }

  // `parsed` is `reply-grammar.js#parseReply`'s success object (`family: 'disposition'`). `entry` is
  // what the bridge knows about this thread: `{goalId, channelId, askId}`.
  async function dispatch({ entry, parsed }) {
    const { goalId, channelId, askId } = entry;
    const outcome = parsed.outcome;

    switch (outcome) {
      case 'keep':
        await say({ channelId, goalId, askId, text: `${goalId} kept open. Nothing more is owed and nothing launches on its own.` });
        log('info', 'disposition keep settled', { goalId, askId });
        return { action: 'keep', ok: true, outcome };
      case 'close': {
        const out = await call(closeGoal, 'closeGoal', { goalId, askId });
        if (!out.ok) {
          await say({ channelId, goalId, askId, text: `close did not run: ${out.error}. The ask is settled; the goal was NOT closed.` });
          log('warn', 'disposition close REFUSED', { goalId, askId, error: out.error });
          return { action: 'close-failed', ok: false, outcome, error: out.error };
        }
        await say({ channelId, goalId, askId, text: `${goalId} closed — given up on, not a success.` });
        log('info', 'disposition close fired', { goalId, askId });
        return { action: 'close', ok: true, outcome, result: out };
      }
      default:
        // The grammar is closed to exactly these two tokens when `kind: 'goal-disposition'`
        // (`reply-grammar.js`) — this arm exists so a caller passing a wider parse in error fails
        // loudly here rather than as a silent no-op.
        return {
          action: 'unrecognized', ok: false, outcome, error: `not a disposition outcome: ${outcome}`,
        };
    }
  }

  return { dispatch };
}

module.exports = { createDispositionDispatch };
