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
// ── THE CONTRACT THIS MODULE IS BUILT TO (owner direction 2026-08-28 ~02:00Z, restated VERBATIM
//    from the `fix-pause-bridge` seat; the daemon half is built against the same words) ─────────
//
//   Intent `pause-resume`, payload `{ verb: 'pause'|'resume', goal }`, sent by the bridge token
//   through the forwarder you already hold (`chat/gateway-forwarder.js:50 call(intent, payload,
//   opts)` / `forward`). Result `{ verb, goal, applied, actions, refusals:[{row,text,seat?}] }` —
//   today's `applyPause`/`applyResume` return shape (`chat/pause-resume.js:113-206`), so
//   `summarize()` (`:208-222`) renders it unchanged. Errors: `NOT_FOUND` = the slug names no live
//   goal → post the verbatim §4.5 mechanical NACK (`reply-grammar.js:5 NACK_MECHANICAL`,
//   byte-identical to spec-owner-io §4.5, diff-verified by the wave); any other refusal or
//   transport failure → post an honest one-line refusal naming the reason (`pause <goal> was NOT
//   applied — <error>`), never silence.
//
// ⚑ THIS MODULE IS GRAMMAR + SENDER + POSTER, AND NOTHING ELSE. It holds no store handle, opens
//   no database, and applies nothing itself: `applyPause`/`applyResume` and the resume-semantics
//   table LIVE IN THE DAEMON now, behind the `pause-resume` intent. That is not a refactor — it is
//   the only shape that works. The bridge is a separate process (`probes/probe-chat-boundary.js`
//   forbids this subtree a store handle, a child process and a sibling require), so the door that
//   used to take an INJECTED store applied nothing in production and said nothing about it. The
//   fix is the `start-execution` precedent exactly (`chat/start-execution.js:41-46`): the sender is
//   built from the forwarder the bridge already holds, ALWAYS, and the capability stays daemon-
//   side. An injectable applier port is the wrong seam — it is where a stub `{applied:true}` gets
//   written to make a test pass, and the door then tells the owner a goal is paused when it runs.
//
// ⚑ NO SECOND COPY OF THE RESUME-SEMANTICS TABLE MAY EXIST IN `chat/`. If a lane's refusal prose
//   or a diagnostic name reappears here, two processes are deciding one fact and they will drift.
//
// ⚑ THERE IS NO THIRD PAUSE GRAMMAR. The owner-reply `pause` token is parsed by
//   `reply-grammar.js` (§4). The verb's EFFECT is the daemon's; this file only names it.
//
// ⚑ THE DOOR ADMITS ONLY AN AUTHORIZED SENDER, AND THAT IS LOAD-BEARING NOW. `chat-bridge.js`
//   runs this door BEFORE the forward path's per-principal admission gate
//   (`forward-path.js#onChatMessage` → `allowlist.check`), because a mechanical verb never
//   forwards. That was inert while the door applied nothing; with the intent LIVE it would let any
//   member of the Slack workspace who can DM the bot pause a goal, stamped `who_stamped: 'owner'`.
//   So the door asks the SAME predicate object the ask door authorizes with (`config.allowlist`,
//   `chat-bridge.js` → `ask-thread.js#authorizedSenders`) — never a second list — and an
//   unauthorized sender's `pause X` returns `{mechanical: false}`, falls through to the ordinary
//   path, and is refused at the existing gate. It gets NO answer from this door on purpose: this
//   door must not tell an unadmitted principal which goals exist.
//
// ⚑ PAUSE/RESUME NEVER RELEASES AN ASK [§4.2]. Neither verb writes `open_asks`. An owner who
//   pauses a goal that is waiting on a question is still owed that question's answer, and the ask
//   must still read `open` to every digest, status line and kill clock afterwards.

const { parseReply, NACK_MECHANICAL } = require('./reply-grammar');

const INTENT = 'pause-resume';

// The one error code with a SPECIFIED answer: the slug named no live goal, which is the §4.2
// ambiguity §4.5 answers with its verbatim NACK. Every other code is rendered honestly instead.
const NOT_FOUND = 'NOT_FOUND';

// The honest one-line refusal. It names the verb, the goal and the REASON, because the failure
// this replaces is silence — an owner who typed `pause` and got nothing back cannot tell a paused
// goal from a broken bridge.
function refusalLine(verb, goal, reason) {
  return `${verb} ${goal} was NOT applied — ${reason}`;
}

function createPauseResume({
  // The bridge's ONE outbound path to the daemon (`gateway-forwarder.js`). REQUIRED, and refused
  // at construction: a door built without it could only ever answer as if it had acted, and this
  // module exists because that is precisely what it used to do.
  forwarder,
  // `isAuthorizedSender(chatUserId) -> boolean`. REQUIRED. See the admission note above: the
  // bridge passes the predicate of the list it already holds, never a copy of the list.
  isAuthorizedSender,
  // Posts a line back where the verb arrived: in-thread when it came in a thread, otherwise as a
  // reply to the command message. Required — a mechanical verb that answers nothing is the
  // silence [F-owner-ux-2] forbids.
  post,
  logger = null,
} = {}) {
  if (!forwarder || typeof forwarder.forward !== 'function') {
    throw new Error('createPauseResume requires the gateway forwarder — the verb crosses the daemon boundary as the `pause-resume` intent');
  }
  if (typeof isAuthorizedSender !== 'function') {
    throw new Error('createPauseResume requires isAuthorizedSender — this door runs BEFORE the forward path\'s admission gate');
  }
  if (typeof post !== 'function') throw new Error('createPauseResume requires post — a mechanical verb must answer where it arrived');
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  // The daemon's answer, rendered. UNCHANGED from the shape `applyPause`/`applyResume` returned
  // when they lived here — that is why the contract fixes the result shape rather than inventing
  // a wire format: the renderer is the part the owner reads and it was already right.
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
  // `text` is the owner's raw message. `senderId` is the chat principal who typed it. `channelGoal`
  // is the goal this channel belongs to (null in the system channel and in a DM, which is exactly
  // why the slug is required there). `liveGoals` is an OPTIONAL roster for the grammar — null in
  // production now, because the live-goal roster is the daemon's fact and the daemon is the one
  // resolving the slug; the approval-thread release path still passes what it has.
  //
  // Returns `{mechanical:false}` when the first token is not `pause`/`resume`, AND when the sender
  // is not authorized — the caller then continues to whatever door it would otherwise have used,
  // unchanged [T5-R14].
  async function handle({ text, channelId, threadTs = null, channelGoal = null, liveGoals = null, senderId = null }) {
    const parsed = parseReply(text, { channelGoal, liveGoals });

    // Is this message ours at all? A parse failure is only OURS when the first token really was
    // `pause`/`resume`; anything else is not this door's message and must not be answered with
    // this door's NACK.
    const ours = parsed.ok ? parsed.family === 'mechanical' : parsed.nackKind === 'mechanical';
    if (!ours) return { mechanical: false };

    // ADMISSION, BEFORE ANY POST AND BEFORE ANY CALL. Checked here rather than at the parse arms
    // below so that an unauthorized principal cannot even learn from the NACK that this door
    // exists — and so that the fall-through carries the message to the one gate that owns the
    // refusal (`forward-path.js#onChatMessage`), which also records the pairing request.
    if (!isAuthorizedSender(senderId)) {
      log('warn', 'mechanical verb from an UNAUTHORIZED sender — not handled here; falls through to the ordinary admission gate', { senderId, channelGoal });
      return { mechanical: false, refused: 'unauthorized-sender' };
    }

    if (!parsed.ok) {
      await post({ channelId, threadTs, goalId: channelGoal, text: NACK_MECHANICAL });
      log('info', 'mechanical verb could not be targeted — verbatim §4.5 NACK posted, NOTHING changed', { channelGoal });
      return { mechanical: true, ok: false, nacked: true, nack: NACK_MECHANICAL, applied: false };
    }

    const goal = parsed.goal;
    const verb = parsed.outcome;

    // Every exit below this line POSTS. There is no arm that returns in silence — that branch is
    // the defect this module was rewritten to delete.
    const nacked = async () => {
      await post({ channelId, threadTs, goalId: channelGoal, text: NACK_MECHANICAL });
      log('info', 'the daemon knows no such live goal — verbatim §4.5 NACK posted, NOTHING changed', { verb, goal });
      return { mechanical: true, ok: false, nacked: true, nack: NACK_MECHANICAL, applied: false, verb, goal };
    };
    const refused = async (reason) => {
      await post({ channelId, threadTs, goalId: goal, text: refusalLine(verb, goal, reason) });
      log('warn', `mechanical ${verb} was NOT applied`, { verb, goal, reason });
      return { mechanical: true, ok: false, applied: false, verb, goal, error: reason, actions: [], refusals: [] };
    };

    let res;
    try {
      res = await forwarder.forward(INTENT, { verb, goal });
    } catch (err) {
      // The forwarder resolves transport failures rather than throwing, so a throw here is a
      // programming or wiring fault — still answered, never swallowed.
      return refused(`the ${INTENT} call threw: ${err.message}`);
    }

    if (!res.ok) {
      const code = (res.error && res.error.code) || 'unknown';
      // NOT_FOUND is the §4.2 ambiguity, and §4.5 fixes its wording. Every OTHER code — an
      // UNKNOWN_INTENT from a daemon that has not been deployed with the executor yet, an
      // authorization refusal, a transport timeout — is rendered as itself. Collapsing them into
      // the NACK would tell the owner their goal does not exist when the daemon is simply old.
      if (code === NOT_FOUND) return nacked();
      const message = (res.error && res.error.message) || code;
      return refused(`${code}: ${message}`);
    }

    const out = res.result;
    // A malformed result is a refusal, not a rendered "nothing to change." — `summarize` reads
    // `actions`/`refusals` and would answer an EMPTY success for a daemon that returned nothing,
    // which is the same lie in a new place.
    if (!out || !Array.isArray(out.actions) || !Array.isArray(out.refusals)) {
      return refused(`the daemon answered ${INTENT} with no actions/refusals result`);
    }

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

  return { handle };
}

module.exports = {
  createPauseResume,
  NACK_MECHANICAL,
  INTENT,
  refusalLine,
};
