'use strict';

// ── THE RECOVERY THREAD: WHAT EACH OF THE THREE RULED OPTIONS DOES ───────────────────────────────
// `spec-recovery.md` §5 (the ladder), `d-ask14-recovery-thread-shape` (one thread per stuck goal —
// the thread IS the reply's address, so `ask-thread.js#release`'s exact-thread match already tells
// two lanes apart; nothing here re-derives that).
//
// WHY THIS IS A SEPARATE MODULE FROM `ask-thread.js`, exactly `approval-thread.js`'s reason: the
// parser is ONE (`reply-grammar.js`, kind-gated to the recovery ladder) and the release rule is ONE
// (`ask-thread.js#release`). What differs is only what happens AFTER the parse, decided by the ask's
// `kind`, never by the token — kept here so the release door never grows a third parser.
//
// ⚑ EVERY EFFECT IS AN INJECTED PORT, `approval-thread.js`'s own reason: the bridge is a separate
//   process (`probes/probe-chat-boundary.js`) and may not re-arm a counter, drop a lane or pause a
//   goal itself. A MISSING port is a WIRING GAP, reported into the thread as a failure — never
//   swallowed, because an owner who typed `drop-lane` and saw nothing would reasonably type it
//   again, exactly the silence this whole seat exists to end.
//
// ⚑ `retryWithChange` AND `dropLane` ARE NOT WIRED BY ANY CALLER TODAY (`digest-recovery-thread`'s
//   own report). `retry-with-change` needs a LANE-scoped re-arm+relaunch gateway act (today's
//   `pause-resume` resume is GOAL-scoped, `rearmScope`); `drop-lane` needs a "permanently abandon
//   this lane" concept the counters/reconcile system does not have anywhere yet. Building either is
//   its own design surface, not a parameter on an existing door — this module still dispatches to
//   them so the shape is complete, and reports the missing-port failure honestly until they exist.
//   `pauseGoal` IS wired (`chat-bridge.js`): `pause-goal` reuses the EXISTING `pause-resume` intent
//   directly, goal-scoped, exactly what that outcome asks for.

function call(port, name, args) {
  if (typeof port !== 'function') return Promise.resolve({ ok: false, error: `no ${name} port is wired` });
  return Promise.resolve(port(args)).then(
    (out) => ((out && out.ok === true) ? out : { ok: false, error: (out && (out.error || out.reason)) || `${name} refused`, result: out }),
    (err) => ({ ok: false, error: err.message }),
  );
}

function createRecoveryDispatch({
  retryWithChange = null,
  dropLane = null,
  pauseGoal = null,
  // Posts a line back into the recovery thread — the ONE reporting path an owner watching that
  // thread has, exactly [C-16]'s reason in `approval-thread.js`.
  postBack,
  logger = null,
} = {}) {
  if (typeof postBack !== 'function') {
    throw new Error('createRecoveryDispatch requires postBack — the outcome is reported into the recovery thread, same as an approval');
  }
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  async function say({ channelId, goalId, askId, text }) {
    return postBack({ channelId, goalId, askId, text });
  }

  // `parsed` is `reply-grammar.js#parseReply`'s success object (`family: 'recovery'`). `entry` is
  // what the bridge knows about this thread: `{goalId, channelId, askId, seat}`.
  async function dispatch({ entry, parsed }) {
    const {
      goalId, channelId, askId, seat,
    } = entry;
    const outcome = parsed.outcome;
    const comments = parsed.comments || '';

    switch (outcome) {
      case 'retry-with-change': {
        const out = await call(retryWithChange, 'retryWithChange', {
          goalId, seat, askId, comments,
        });
        if (!out.ok) {
          await say({ channelId, goalId, askId, text: `retry-with-change did not run: ${out.error}. The ask is settled; the lane was NOT re-armed.` });
          log('warn', 'recovery retry-with-change REFUSED', { goalId, seat, askId, error: out.error });
          return {
            action: 'retry-with-change-failed', ok: false, outcome, error: out.error,
          };
        }
        log('info', 'recovery retry-with-change fired', { goalId, seat, askId });
        return {
          action: 'retry-with-change', ok: true, outcome, result: out,
        };
      }
      case 'drop-lane': {
        const out = await call(dropLane, 'dropLane', { goalId, seat, askId, comments });
        if (!out.ok) {
          await say({ channelId, goalId, askId, text: `drop-lane did not run: ${out.error}. The ask is settled; the lane was NOT dropped.` });
          log('warn', 'recovery drop-lane REFUSED', { goalId, seat, askId, error: out.error });
          return { action: 'drop-lane-failed', ok: false, outcome, error: out.error };
        }
        log('info', 'recovery drop-lane fired', { goalId, seat, askId });
        return {
          action: 'drop-lane', ok: true, outcome, result: out,
        };
      }
      case 'pause-goal': {
        const out = await call(pauseGoal, 'pauseGoal', { goalId, askId, comments });
        if (!out.ok) {
          await say({ channelId, goalId, askId, text: `pause-goal did not run: ${out.error}. The ask is settled; the goal was NOT paused.` });
          log('warn', 'recovery pause-goal REFUSED', { goalId, seat, askId, error: out.error });
          return { action: 'pause-goal-failed', ok: false, outcome, error: out.error };
        }
        await say({ channelId, goalId, askId, text: `${goalId} paused.` });
        log('info', 'recovery pause-goal fired', { goalId, seat, askId });
        return {
          action: 'pause-goal', ok: true, outcome, result: out,
        };
      }
      default:
        // The grammar is closed to exactly these three tokens when `kind: 'recovery'`
        // (`reply-grammar.js`) — this arm exists so a caller passing a wider parse in error fails
        // loudly here rather than as a silent no-op.
        return {
          action: 'unrecognized', ok: false, outcome, error: `not a recovery outcome: ${outcome}`,
        };
    }
  }

  return { dispatch };
}

module.exports = { createRecoveryDispatch };
