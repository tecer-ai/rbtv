'use strict';

// ── THE APPROVAL THREAD: ITS FIRST MESSAGE, AND WHAT EACH OUTCOME DOES ────────────────────────
// `spec-owner-io.md` §3 (approval first message) and §4.2 (post-parse dispatch by `kind`).
// Law: `DESIGN-BASELINE.md` v2 §Planning approval rows [T5-R5, T3-R4, T3-R16, T3-R20, T3-R21,
// T3-R22, D12, D-5-ruling, C-16, CF-7].
//
// WHY THIS IS A SEPARATE MODULE FROM `ask-thread.js`. The parser is ONE (§4, `reply-grammar.js`)
// and the release rule is ONE (§2.4, `ask-thread.js`). What differs between an ordinary ask and an
// approval is only what happens AFTER the parse — and that is decided by the ask's `kind`, never
// by the token. `approve` typed in an ordinary thread is an ordinary outcome delivered to the
// seat; the SAME word in a `kind=approval` thread is the D12 trigger that starts execution
// [D-5-ruling, CF-7]. Keeping that fork here, above the release door, is what stops the door from
// growing a second parser and stops a stray `approve` anywhere in Slack from firing a materialize.
//
// ⚑ THE FIRST MESSAGE IS THE SAFETY DEVICE, NOT A FORMATTING PREFERENCE [D-5-ruling]. The GOAL
//   NAME and the IRREVERSIBLE EFFECT are each their own BOLD LEAD LINE, before any other body,
//   because the failure this replaces is an owner approving on a phone without seeing which goal
//   is about to start executing. The bound `commit_id` [T5-R5] is in the body for the same reason:
//   an approval that names no commit approves whatever the tree happens to hold later.
//
// ⚑ EVERY POST-BACK GOES TO **THIS** THREAD. A D12 materialize that refuses (collision,
//   unresolvable ref, envelope refusal) reports back in the approval thread the owner is already
//   reading [C-16] — never a new thread, never the system channel, never a log line only.
//
// ⚑ AFTER `reject-and-pause`, THE THREAD IS A DOOR WITH THREE KEYS [T3-R22]: `retry with:`,
//   `approve`, `close`, IN THIS SAME THREAD. Nothing else leaves that pause — not a letter, not
//   another reject. A recognized-but-not-an-exit token is answered in-thread (silence here would
//   rebuild [F-owner-ux-2]) and changes nothing.

const IRREVERSIBLE_PHRASE = 'a reply of approve starts execution.';

// §3: the tokens this thread will actually parse, published in the body — the owner never has to
// remember the vocabulary, and a token that is not on this line is not accepted by this thread.
const APPROVAL_TOKEN_LINE = 'Reply with: approve · reject-and-close · reject-and-pause · reject-and-retry · retry with: · close';

// [T3-R22] The closed list of later exits from a `reject-and-pause`d approval thread.
const PAUSE_EXITS = Object.freeze(['retry with:', 'approve', 'close']);
const PAUSE_EXIT_SET = new Set(PAUSE_EXITS);

// Authored (NOT a spec-verbatim string — §4.5's two NACKs cover an UNPARSED token; this answers a
// token that parsed and simply is not one of the three keys).
const NOT_AN_EXIT = `this approval is paused. Only ${PAUSE_EXITS.join(', ')} in this thread take it further. Nothing changed.`;

function boldLine(text) {
  return `*${String(text).trim()}*`;
}

// THE §3 APPROVAL FIRST MESSAGE, body only. The `{marker} {suffix} · {seat} · {label}` lead line is
// `ask-thread.js#openingLine`'s and is stamped after Slack mints the id — this composes what goes
// UNDER it, so the two never disagree about who owns which line.
function composeApprovalBody({ goalName, digest, commitId, canvasLink = null }) {
  if (!goalName) throw new Error('composeApprovalBody requires goalName — §3 leads with the GOAL NAME');
  if (!commitId) throw new Error('composeApprovalBody requires commitId — an approval binds to a commit [T5-R5]');
  const canvas = canvasLink ? String(canvasLink) : 'none — artifacts on disk';
  return [
    boldLine(`GOAL: ${goalName}`),
    boldLine(`IRREVERSIBLE: ${IRREVERSIBLE_PHRASE}`),
    '',
    String(digest || '').trim(),
    '',
    `Bound commit: \`${commitId}\``,
    `Canvas (optional, may lag): ${canvas}`,
    '',
    APPROVAL_TOKEN_LINE,
    'Comments after the first word.',
  ].join('\n');
}

// ── POST-PARSE DISPATCH ───────────────────────────────────────────────────────────────────────
//
// Every effect is an INJECTED PORT. The bridge is a separate process (`probe-chat-boundary.js`):
// it may not spawn `planning/path_b.py`, close a goal, or write a lane. It decides WHICH act the
// owner asked for and hands that act to whoever can perform it — and reports what came back into
// the thread the owner is reading.
//
//   materialize({goalId, commitId, askId, comments})   → D12, `planning/path_b.py#run_path_b`
//   closeGoal({goalId, askId, comments, why})          → close the planning goal
//   pauseGoal({goalId, askId, comments})               → pause the planning goal
//   relaunchDraftVerify({goalId, askId, findings, comments}) → draft + verify only [T3-R21]
//
// A port returns `{ok: true, ...}` or `{ok: false, error}`; a throw is treated as `{ok:false}`.
// A missing port is a WIRING GAP and is reported into the thread as a failure, never swallowed:
// an owner who typed `approve` and saw nothing would reasonably type it again.
function createApprovalDispatch({
  materialize = null,
  closeGoal = null,
  pauseGoal = null,
  relaunchDraftVerify = null,
  // Posts a line back into the approval thread. Required — [C-16] is this module's whole
  // reporting path, and a dispatch that cannot answer in-thread must fail at construction.
  postBack,
  logger = null,
} = {}) {
  if (typeof postBack !== 'function') {
    throw new Error('createApprovalDispatch requires postBack — [C-16] reports into the approval thread');
  }
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  async function call(port, name, args) {
    if (typeof port !== 'function') return { ok: false, error: `no ${name} port is wired` };
    try {
      const out = await port(args);
      if (out && out.ok === true) return out;
      return { ok: false, error: (out && (out.error || out.reason)) || `${name} refused`, result: out };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  }

  async function say({ channelId, goalId, askId, text }) {
    return postBack({ channelId, goalId, askId, text });
  }

  // `parsed` is `reply-grammar.js#parseReply`'s success object. `entry` is what the bridge knows
  // about this thread: `{goalId, channelId, askId, kind, commitId, paused}`.
  //
  // Returns `{action, done, paused, ok, ...}`. `done` = this approval thread is finished and the
  // bridge may forget it. `paused` = the thread is (still) in the [T3-R22] pause.
  async function dispatch({ entry, parsed }) {
    const { goalId, channelId, askId } = entry;
    const commitId = entry.commitId || null;
    const outcome = parsed.outcome;
    const comments = parsed.comments || '';
    const wasPaused = entry.paused === true;

    // [T3-R22] the pause gate comes FIRST: inside a paused approval thread, only three tokens are
    // an exit, whatever else the grammar recognizes.
    if (wasPaused && !PAUSE_EXIT_SET.has(outcome)) {
      await say({ channelId, goalId, askId, text: NOT_AN_EXIT });
      log('info', 'token recognized but it is not one of the three exits from a paused approval [T3-R22]', { goalId, askId, outcome });
      return { action: 'not-an-exit', ok: false, done: false, paused: true, outcome };
    }

    switch (outcome) {
      case 'approve': {
        // D12. No agent judgment, no second confirmation token [D-5-ruling, CF-7] — the ONLY
        // guard is that this is a genuine `kind=approval` thread, and the bridge checked that
        // before calling here.
        const out = await call(materialize, 'materialize', { goalId, commitId, askId, comments });
        if (!out.ok) {
          // [C-16] the refusal lands in THIS thread. The thread stays alive and stays paused-free
          // so `retry with:` / `approve` / `close` still work on it.
          await say({ channelId, goalId, askId, text: `materialize did not run: ${out.error}. Nothing was started. ${APPROVAL_TOKEN_LINE}` });
          log('warn', 'D12 materialize REFUSED — posted back to the approval thread [C-16]', { goalId, askId, error: out.error });
          return { action: 'materialize-failed', ok: false, done: false, paused: false, outcome, error: out.error };
        }
        log('info', 'D12 materialize fired from an approval thread [D12]', { goalId, askId, commitId });
        return { action: 'materialize', ok: true, done: true, paused: false, outcome, result: out };
      }
      case 'reject-and-close':
      case 'close': {
        const out = await call(closeGoal, 'closeGoal', { goalId, askId, comments, why: outcome });
        if (!out.ok) {
          await say({ channelId, goalId, askId, text: `could not close this planning goal: ${out.error}. Nothing changed.` });
          return { action: 'close-failed', ok: false, done: false, paused: wasPaused, outcome, error: out.error };
        }
        log('info', 'approval thread closed the planning goal', { goalId, askId, outcome });
        return { action: 'close', ok: true, done: true, paused: false, outcome, result: out };
      }
      case 'reject-and-pause': {
        const out = await call(pauseGoal, 'pauseGoal', { goalId, askId, comments });
        if (!out.ok) {
          await say({ channelId, goalId, askId, text: `could not pause this planning goal: ${out.error}. Nothing changed.` });
          return { action: 'pause-failed', ok: false, done: false, paused: wasPaused, outcome, error: out.error };
        }
        // The thread does NOT end. It becomes the [T3-R22] door — and the three keys are printed
        // now, because the owner will come back to this thread hours later.
        await say({ channelId, goalId, askId, text: `planning goal paused. From here, in this thread: ${PAUSE_EXITS.join(', ')}.` });
        log('info', 'approval REJECTED-AND-PAUSED — this thread is now the only exit [T3-R22]', { goalId, askId });
        return { action: 'reject-and-pause', ok: true, done: false, paused: true, outcome, result: out };
      }
      case 'reject-and-retry':
      case 'retry with:': {
        // [T3-R21] draft + verify ONLY, and the comments ARE the findings list. Unlimited
        // owner-driven retries: nothing here counts a strike or spends a budget.
        const findings = Array.isArray(parsed.findings) ? parsed.findings : (comments ? comments.split('\n').map((l) => l.trim()).filter(Boolean) : []);
        const out = await call(relaunchDraftVerify, 'relaunchDraftVerify', { goalId, askId, findings, comments });
        if (!out.ok) {
          await say({ channelId, goalId, askId, text: `could not relaunch draft + verify: ${out.error}. Nothing changed.` });
          return { action: 'retry-failed', ok: false, done: false, paused: wasPaused, outcome, error: out.error, findings };
        }
        log('info', 'approval rejected with findings — draft + verify relaunched [T3-R21]', { goalId, askId, findings: findings.length, wasPaused });
        // A retry is a NAMED EXIT from the pause [T3-R22]: the thread leaves the pause and waits
        // for the next approval message on the same thread.
        return { action: 'retry', ok: true, done: false, paused: false, outcome, findings, result: out };
      }
      default:
        // A lettered outcome (or anything else the grammar recognizes) is NOT an approval outcome
        // (§4.2): it belongs to the seat, exactly as in an ordinary thread.
        log('info', 'recognized token is not an approval outcome — delivered to the seat, not dispatched here [§4.2]', { goalId, askId, outcome });
        return { action: 'to-seat', ok: true, done: false, paused: wasPaused, outcome };
    }
  }

  return { dispatch, PAUSE_EXITS };
}

module.exports = {
  createApprovalDispatch,
  composeApprovalBody,
  IRREVERSIBLE_PHRASE,
  APPROVAL_TOKEN_LINE,
  PAUSE_EXITS,
  NOT_AN_EXIT,
};
