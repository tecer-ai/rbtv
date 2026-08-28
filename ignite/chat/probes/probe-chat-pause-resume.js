'use strict';

// probe-chat-pause-resume — the mechanical door (`spec-owner-io.md` §4.2/§4.4/§4.5) as it is NOW:
// grammar + sender check + `pause-resume` gateway call + the answer it posts.
//
// NO SLACK, NO DAEMON, NO STORE. Both edges are fakes and that is the RIGHT harness now: this
// module no longer applies anything. It sends the `pause-resume` intent and renders what comes
// back, so what is provable here is exactly (1) which intent and payload cross the boundary,
// (2) that EVERY outcome — success, NACK, refusal, transport failure — produces an answer where
// the verb arrived, and (3) that an unauthorized sender gets neither a call nor a post. The
// resume-semantics table itself is asserted against the REAL ending store on the daemon side,
// where it now lives; asserting it here against a fake would prove nothing about the live goal.
//
// ⚠ THE ARM THIS PROBE EXISTS FOR IS (D). The failure being replaced is SILENCE: the door used to
// return before any post when it had no applier, so an owner who typed `pause X` in Slack got
// nothing at all — not an answer, not a refusal. Every failure arm below asserts `posts.length`,
// never just the returned object.

const path = require('node:path');
const fs = require('node:fs');
const { createPauseResume, INTENT, refusalLine } = require('../pause-resume');
const { NACK_MECHANICAL } = require('../reply-grammar');

// ⚑ TRANSCRIBED FROM `spec-owner-io.md` §4.5's second verbatim block, BY HAND AND ON PURPOSE.
// This constant is the probe's independent copy of the spec text; the check below is a BYTE
// comparison against the constant the code posts. A probe that imported the same constant it is
// testing would pass on any wording at all, including a typo introduced in the same edit.
const SPEC_4_5_MECHANICAL_NACK = "couldn't parse pause/resume. Use `pause {goal}` or `resume {goal}` with one live goal slug. In a goal channel, bare pause/resume targets that goal. Reply again.";

const OUT = path.join(__dirname, 'probe-chat-pause-resume.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const CHANNEL = 'C-GOAL-1';
const SYSTEM = 'C-SYSTEM';
const GOAL = 'demo-goal';
const OTHER = 'other-goal';
const OWNER = 'U-OWNER';        // on `config.allowlist`
const STRANGER = 'U-STRANGER';  // any member of the Slack workspace who can DM the bot

// The fake forwarder: it RECORDS the crossing and answers a script. `answer` may be a function of
// the payload, so one door can answer differently per verb.
function fake({ answer = null, throws = null, admitted = [OWNER] } = {}) {
  const calls = [];
  const posts = [];
  const forwarder = {
    forward: async (intent, payload, opts) => {
      calls.push({ intent, payload, opts });
      if (throws) throw new Error(throws);
      return typeof answer === 'function' ? answer(payload) : answer;
    },
  };
  const door = createPauseResume({
    forwarder,
    isAuthorizedSender: (id) => admitted.includes(String(id)),
    post: async (p) => { posts.push(p); return { delivered: true }; },
    logger: null,
  });
  return { door, calls, posts };
}

const ok = (result) => ({ ok: true, result, error: null, status: 200 });
const err = (code, message) => ({ ok: false, result: null, error: { code, message }, status: 400 });

(async () => {
  // ── CONSTRUCTION: the two seams that must not exist ─────────────────────────────────────────
  {
    let noForwarder = null;
    try {
      createPauseResume({ isAuthorizedSender: () => true, post: async () => {} });
    } catch (e) { noForwarder = e.message; }
    let noSender = null;
    try {
      createPauseResume({ forwarder: { forward: async () => ok({}) }, post: async () => {} });
    } catch (e) { noSender = e.message; }
    check('X1: the door REFUSES to exist without the forwarder — an applier that can be stubbed is how a door answers as if it acted (`start-execution.js` precedent)',
      typeof noForwarder === 'string' && /forwarder/.test(noForwarder), { error: noForwarder });
    check('X2: and without the sender predicate — this door runs BEFORE the forward path\'s admission gate, so a missing check is an open lever',
      typeof noSender === 'string' && /isAuthorizedSender/.test(noSender), { error: noSender });
  }

  // ── (a) THE HAPPY CROSSING: one intent, one payload, one line ────────────────────────────────
  {
    const { door, calls, posts } = fake({
      answer: (p) => ok({ verb: p.verb, goal: p.goal, applied: true, actions: [{ row: 'goal', change: 'running→paused', goal: p.goal }], refusals: [] }),
    });
    const out = await door.handle({ text: `pause ${GOAL}`, channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: OWNER });
    check('a1: an authorized `pause {goal}` crosses the daemon boundary EXACTLY ONCE, as intent `pause-resume` with payload {verb,goal} and nothing else',
      calls.length === 1 && calls[0].intent === INTENT
      && JSON.stringify(calls[0].payload) === JSON.stringify({ verb: 'pause', goal: GOAL }),
      { calls: calls.map((c) => ({ intent: c.intent, payload: c.payload })) });
    check('a2: and the owner gets ONE line back where the verb arrived, rendering the daemon\'s own action',
      posts.length === 1 && posts[0] && posts[0].text === `${GOAL}: running→paused.`
      && posts[0].channelId === CHANNEL && posts[0].goalId === GOAL
      && out.mechanical === true && out.ok === true && out.applied === true,
      { posts: posts.map((p) => p.text), out: { ok: out.ok, applied: out.applied } });
  }

  // ── (b) A RESUME ANSWER CARRYING BOTH HALVES: every line is posted ───────────────────────────
  //
  // The daemon applies EVERY matching row of the resume-semantics table and a goal may carry more
  // than one halted kind at once. A renderer that drops the refusals reports a resume that lifted
  // lanes it did not lift — which is the same lie the silence told, told louder.
  {
    const result = {
      verb: 'resume', goal: GOAL, applied: true,
      actions: [
        { row: 'goal', change: 'paused→running', goal: GOAL },
        { row: 'counter', seat: 'leader', reason_class: 'nonterm', attempts: 3, change: 'counter reset' },
        { row: 'counter-exhaustion', seat: 'leader', change: 'disarmed→armed' },
      ],
      refusals: [
        { row: 'blocked-on-human', seat: 'asker', text: 'resume does not lift asker: it is halted waiting on an open ask, and only an authorized reply in that thread releases it. Answer it in its thread: 1724508123.123456.' },
        { row: 'gate-cap', seat: 'gate', text: 'resume does not lift gate: it stopped at the re-plan cap. Answer the gate decision-ask — resume does not open a third re-plan.' },
      ],
    };
    const { door, calls, posts } = fake({ answer: ok(result) });
    const out = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: OWNER });
    const said = posts.length === 1 ? posts[0].text.split('\n') : [];
    check('b1: `resume` crosses with verb=resume and the SAME one-call shape',
      calls.length === 1 && calls[0].payload.verb === 'resume' && calls[0].payload.goal === GOAL,
      { payload: calls[0] && calls[0].payload });
    check('b2: EVERY action and EVERY refusal the daemon returned is a line in the one posted answer — three actions + two refusals = five lines, refusals verbatim',
      posts.length === 1 && said.length === 5
      && said[0] === `${GOAL}: paused→running.`
      && said[1] === 'leader: attempt counter re-armed (nonterm, was 3).'
      && said[2] === 'leader: re-armed (disarmed→armed).'
      && said[3] === result.refusals[0].text && said[4] === result.refusals[1].text,
      { lines: said });
    check('b3: and the caller gets the daemon\'s result unchanged — `actions`/`refusals` ride out for the approval-thread path',
      (out.actions || []).length === 3 && (out.refusals || []).length === 2 && out.ok === true,
      { actions: (out.actions || []).length, refusals: (out.refusals || []).length });
  }

  // ── (c) NOT_FOUND → THE VERBATIM §4.5 MECHANICAL NACK ────────────────────────────────────────
  {
    const { door, calls, posts } = fake({ answer: err('NOT_FOUND', 'no live goal named no-such-goal') });
    const out = await door.handle({ text: 'pause no-such-goal', channelId: SYSTEM, threadTs: null, channelGoal: null, senderId: OWNER });
    check('c1: the daemon answering NOT_FOUND is the §4.2 ambiguity — the door posts the §4.5 NACK and reports nothing applied',
      calls.length === 1 && posts.length === 1 && out.nacked === true && out.applied === false,
      { posts: posts.map((p) => p.text), out });
    check('c2: and that NACK is BYTE-IDENTICAL to spec-owner-io §4.5\'s second verbatim block, transcribed independently in this probe',
      posts.length === 1 && posts[0].text === SPEC_4_5_MECHANICAL_NACK && NACK_MECHANICAL === SPEC_4_5_MECHANICAL_NACK
      && posts[0].text.length === SPEC_4_5_MECHANICAL_NACK.length,
      { posted: posts[0] && posts[0].text, spec: SPEC_4_5_MECHANICAL_NACK });
  }

  // ── (d) THE SILENCE ARM: every other failure is ANSWERED, never dropped ──────────────────────
  //
  // ⚠ EACH OF THESE ASSERTS `posts.length === 1`. Before this rewrite the door returned
  // `{reason:'no-store'}` BEFORE any post and the owner got nothing at all. If any arm here ever
  // reads `posts.length === 0`, the silence is back.
  {
    // d1. THE DEPLOY ORDER MADE VISIBLE. A bridge carrying this fix in front of a daemon that has
    // not been deployed with the executor answers UNKNOWN_INTENT (`gateway/errors.js`,
    // `gateway/parse.js` — the intent set is closed). The owner must read THAT, not "no such goal".
    const { door, posts } = fake({ answer: err('UNKNOWN_INTENT', 'unknown intent: pause-resume') });
    const out = await door.handle({ text: `pause ${GOAL}`, channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: OWNER });
    check('d1: a daemon that does not know `pause-resume` yet → ONE honest refusal line naming UNKNOWN_INTENT, never silence and never the §4.5 NACK',
      posts.length === 1 && posts[0]
      && posts[0].text === refusalLine('pause', GOAL, 'UNKNOWN_INTENT: unknown intent: pause-resume')
      && posts[0] && posts[0].text !== NACK_MECHANICAL
      && out.applied === false && out.ok === false && out.mechanical === true,
      { posted: posts[0] && posts[0].text, posts: posts.length });
  }
  {
    // d2. The daemon refused the bridge's authority.
    const { door, posts } = fake({ answer: err('UNAUTHORIZED_SENDER', 'this token may not pause a goal') });
    await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, threadTs: 'T1', channelGoal: GOAL, senderId: OWNER });
    check('d2: a daemon-side authorization refusal → ONE honest refusal line carrying the code and the reason',
      posts.length === 1 && posts[0]
      && posts[0].text === refusalLine('resume', GOAL, 'UNAUTHORIZED_SENDER: this token may not pause a goal')
      && posts[0].threadTs === 'T1',
      { posted: posts[0] && posts[0].text, posts: posts.length });
  }
  {
    // d3. Transport: the forwarder resolves these rather than throwing (gateway-forwarder.js).
    const { door, posts } = fake({ answer: err('TRANSPORT', 'gateway at 127.0.0.1:8787 did not respond within 10000ms') });
    await door.handle({ text: `pause ${GOAL}`, channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: OWNER });
    check('d3: the daemon being DOWN → ONE honest refusal line, so a paused-looking goal is never mistaken for a paused goal',
      posts.length === 1 && posts[0] && /TRANSPORT/.test(posts[0].text) && /was NOT applied/.test(posts[0].text),
      { posted: posts[0] && posts[0].text, posts: posts.length });
  }
  {
    // d4. A THROW is a wiring fault, and it is still answered.
    const { door, posts } = fake({ throws: 'socket exploded' });
    const out = await door.handle({ text: `pause ${GOAL}`, channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: OWNER });
    check('d4: the call THROWING is answered too — an exception must not eat the verb',
      posts.length === 1 && posts[0] && /socket exploded/.test(posts[0].text) && out.applied === false,
      { posted: posts[0] && posts[0].text, posts: posts.length });
  }
  {
    // d5. `{ok:true}` with no result is the LIE THIS ARM EXISTS TO STOP: `summarize` would read
    // empty arrays and answer "nothing to change." for a daemon that in fact did nothing at all.
    const { door, posts } = fake({ answer: ok(null) });
    const out = await door.handle({ text: `pause ${GOAL}`, channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: OWNER });
    check('d5: an `ok` with no actions/refusals result is a REFUSAL, not a rendered "nothing to change."',
      posts.length === 1 && posts[0] && /was NOT applied/.test(posts[0].text) && !/nothing to change/.test(posts[0].text)
      && out.applied === false,
      { posted: posts[0] && posts[0].text });
  }

  // ── (e) THE ADMISSION GATE: an unauthorized sender gets NO call and NO post ──────────────────
  //
  // This door runs BEFORE `forward-path.js#onChatMessage`'s `allowlist.check`, and a mechanical
  // verb never forwards — so with the intent live this predicate is the only thing between any
  // Slack workspace member who can DM the bot and a goal paused in the owner's name.
  {
    const { door, calls, posts } = fake({ answer: ok({ verb: 'pause', goal: GOAL, applied: true, actions: [], refusals: [] }) });
    const out = await door.handle({ text: `pause ${GOAL}`, channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: STRANGER });
    check('e1: an UNAUTHORIZED sender\'s `pause {goal}` is NOT this door\'s message — no gateway call, no post, and it falls through to the ordinary admission gate',
      out.mechanical === false && calls.length === 0 && posts.length === 0,
      { out, calls: calls.length, posts: posts.length });
    const out2 = await door.handle({ text: 'pause', channelId: SYSTEM, threadTs: null, channelGoal: null, senderId: STRANGER });
    check('e2: and an unauthorized MALFORMED verb gets no NACK either — this door must not tell an unadmitted principal that it exists',
      out2.mechanical === false && posts.length === 0, { out: out2, posts: posts.length });
    const out3 = await door.handle({ text: `pause ${GOAL}`, channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: null });
    check('e3: a message with NO sender id is unauthorized — absent identity is never admitted',
      out3.mechanical === false && calls.length === 0 && posts.length === 0, { out: out3 });
  }

  // ── (f) THE GRAMMAR, A1–A5, KEPT ─────────────────────────────────────────────────────────────
  {
    const { door, calls, posts } = fake({
      answer: (p) => ok({ verb: p.verb, goal: p.goal, applied: true, actions: [{ row: 'goal', change: 'running→paused', goal: p.goal }], refusals: [] }),
    });

    // A1. System channel, no slug: no channel goal to fall back on, so the verb cannot be targeted.
    const a1 = await door.handle({ text: 'pause', channelId: SYSTEM, threadTs: null, channelGoal: null, senderId: OWNER });
    check('A1: no slug in the system channel/DM → the VERBATIM §4.5 mechanical NACK, and NO call crosses the boundary',
      a1.mechanical === true && a1.nacked === true && a1.nack === NACK_MECHANICAL && a1.applied === false
      && posts.length === 1 && posts[0] && posts[0].text === SPEC_4_5_MECHANICAL_NACK && calls.length === 0,
      { nack: posts[0] && posts[0].text, calls: calls.length });

    // A2. A slug matching ZERO of the goals the caller supplied.
    const a2 = await door.handle({ text: 'pause no-such-goal', channelId: SYSTEM, threadTs: null, channelGoal: null, liveGoals: [GOAL, OTHER], senderId: OWNER });
    check('A2: with a roster supplied, a slug matching ZERO live goals NACKs at the grammar — still no call',
      a2.nacked === true && a2.applied === false && calls.length === 0, { out: a2, calls: calls.length });

    // A3. A slug matching SEVERAL (§4.2: zero OR several is the same ambiguity).
    const a3 = await door.handle({ text: 'resume dup', channelId: SYSTEM, threadTs: null, channelGoal: null, liveGoals: ['dup', 'DUP'], senderId: OWNER });
    check('A3: a slug matching TWO live goals is the same ambiguity → the verbatim NACK, no call',
      a3.nacked === true && a3.applied === false && calls.length === 0, { out: a3 });

    // A4. The bare verb in a GOAL channel is unambiguous — it targets that channel's goal.
    const a4 = await door.handle({ text: 'pause', channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: OWNER });
    check('A4: a BARE verb in a goal channel targets THAT goal — no slug needed [§4.2] — and that goal is what crosses',
      a4.mechanical === true && a4.ok === true && a4.goal === GOAL
      && calls.length === 1 && calls[0].payload.goal === GOAL,
      { goal: a4.goal, payload: calls[0] && calls[0].payload });

    // A5. A non-mechanical first token falls through to the master doors [T5-R14].
    const beforePosts = posts.length;
    const a5 = await door.handle({ text: 'what is the status?', channelId: CHANNEL, threadTs: null, channelGoal: GOAL, senderId: OWNER });
    check('A5: a non-mechanical first token is NOT handled here and gets NO NACK — it falls through to the master door [T5-R14]',
      a5.mechanical === false && posts.length === beforePosts && calls.length === 1, { result: a5 });

    // [C-14] resume-with-instructions: the comments ride out to the caller, uninterpreted.
    const a6 = await door.handle({ text: `resume ${GOAL} but skip the audio step`, channelId: CHANNEL, threadTs: 'T2', channelGoal: GOAL, senderId: OWNER });
    check('A6: [C-14] an approval-thread `resume {goal}` WITH comments carries them out as instructions, uninterpreted here',
      a6.instructions === 'but skip the audio step' && a6.comments === 'but skip the audio step',
      { instructions: a6.instructions });
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: { probe: 'probe-chat-pause-resume', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-chat-pause-resume EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err2) => {
  process.stdout.write(`PROBE probe-chat-pause-resume EXIT=1 THREW ${err2.stack}\n`);
  process.exit(1);
});
