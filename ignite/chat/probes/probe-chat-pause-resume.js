'use strict';

// probe-chat-pause-resume — the mechanical door (`spec-owner-io.md` §4.2/§4.4/§4.5) and the
// resume-semantics table (`spec-recovery.md` §4 [C-14]).
//
// NO SLACK AND NO DAEMON. The Slack post is an injected sink. The ENDING STORE, however, is the
// REAL one (`state-store/open.js` on a throwaway workspace): every row of the resume-semantics
// table is asserted against the state the real writers actually leave behind, because the failure
// this replaces is a resume that CLAIMED to lift a lane and left it disarmed. A probe reaching a
// sibling tree is the test harness's privilege, never the bridge runtime's — `probe-chat-boundary`
// is what holds that line.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { createPauseResume } = require('../pause-resume');
const { NACK_MECHANICAL } = require('../reply-grammar');
const { openEndingStoreFor, closeEndingStores } = require('../../state-store/open');
const store = require('../../state-store');
const counters = require('../../supervisor/attempt-counters');
const exhaustion = require('../../supervisor/exhaustion');

const OUT = path.join(__dirname, 'probe-chat-pause-resume.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const CHANNEL = 'C-GOAL-1';
const SYSTEM = 'C-SYSTEM';
const GOAL = 'demo-goal';
const OTHER = 'other-goal';
const EV = 'probe://pause-resume';

function fresh({ withCounterPort = true, withStore = true } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pause-resume-'));
  const db = openEndingStoreFor(root);
  const api = store.bind(db);
  const listSeats = (goal) => db.prepare('SELECT seat FROM seat_endings WHERE goal = ? ORDER BY seat').all(goal).map((r) => r.seat);
  const posts = [];
  // The counter ledger lives in the throwaway workspace, NEVER at the module default — the default
  // is the daemon's own live ledger and a probe that wrote it would re-arm the real instance.
  const countersFile = path.join(root, 'attempt-counters.json');
  // `store` is deliberately NOT handed to the port: the ending half of row 1 belongs to
  // `applyResume`'s own seat loop, and a port that fired it too would make the two halves race to
  // report the same act.
  const rearmCounters = withCounterPort
    ? (goal) => exhaustion.rearmScope({ goal, event: counters.RE_ARM.RESUME }, { countersFile }).cleared
    : null;
  const door = createPauseResume({
    store: withStore ? api : null,
    listSeats,
    rearmCounters,
    post: async (p) => { posts.push(p); return { delivered: true }; },
    logger: null,
  });
  return { root, db, api, door, posts, listSeats, countersFile };
}

// A driver that has already reached N on this lane — the state `reconcile.js#counterDisarmed`
// reads to take `skip-disarmed`. Written through `countAttempt` (never a hand-built JSON row) so
// the fixture is the shape the real driver leaves.
function exhaustCounter(countersFile, seat, reasonClass, n = 3) {
  for (let i = 0; i < n; i += 1) {
    counters.countAttempt({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: GOAL, seat, reasonClass, n,
    }, { countersFile });
  }
  return counters.peekCounter({
    driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: GOAL, seat, reasonClass,
  }, { countersFile });
}

// A lane halted the way the spec's row describes it. `stampSystem` is the ONLY writer that can
// leave a disarmed `incomplete:` — using it (rather than a raw INSERT) is what makes the fixture a
// real halted lane and not a shape that looks like one.
function halt(api, seat, diagnostic) {
  return api.stampSystem({
    goal: GOAL, seat, ending: 'incomplete', armed: 0, diagnostic,
    evidence_pointer: EV,
  });
}

(async () => {
  // ── A. TARGET RESOLUTION AND THE VERBATIM §4.5 MECHANICAL NACK ──────────────────────────────
  {
    const { door, posts, api } = fresh();
    api.writeGoalWord({ goal: GOAL, stored: 'running', who_stamped: 'owner', evidence_pointer: EV });

    // A1. System channel, no slug. There is no channel goal to fall back on, so the verb cannot
    // be targeted at all.
    const a1 = await door.handle({ text: 'pause', channelId: SYSTEM, channelGoal: null, liveGoals: [GOAL, OTHER] });
    check('A1: no slug in the system channel → the VERBATIM §4.5 mechanical NACK, nothing applied',
      a1.mechanical === true && a1.nacked === true && a1.nack === NACK_MECHANICAL
      && a1.applied === false && posts.length === 1 && posts[0].text === NACK_MECHANICAL
      && api.getGoalState(GOAL).stored === 'running',
      { nack: posts[0] && posts[0].text, goal: api.getGoalState(GOAL).stored });

    // A2. A slug matching ZERO live goals.
    const a2 = await door.handle({ text: 'pause no-such-goal', channelId: SYSTEM, channelGoal: null, liveGoals: [GOAL, OTHER] });
    check('A2: a slug matching ZERO live goals → the verbatim NACK, nothing applied',
      a2.nacked === true && a2.nack === NACK_MECHANICAL && a2.applied === false
      && api.getGoalState(GOAL).stored === 'running',
      { outcome: a2 });

    // A3. A slug matching SEVERAL live goals (§4.2: zero OR several is the same ambiguity).
    const a3 = await door.handle({ text: 'resume dup', channelId: SYSTEM, channelGoal: null, liveGoals: ['dup', 'DUP'] });
    check('A3: a slug matching TWO live goals → the verbatim NACK, nothing applied',
      a3.nacked === true && a3.nack === NACK_MECHANICAL && a3.applied === false,
      { outcome: a3 });

    // A4. The bare verb in a GOAL channel is unambiguous — it targets that channel's goal.
    const a4 = await door.handle({ text: 'pause', channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL, OTHER] });
    check('A4: a BARE verb in a goal channel targets THAT goal — no slug needed [§4.2]',
      a4.mechanical === true && a4.ok === true && a4.goal === GOAL
      && api.getGoalState(GOAL).stored === 'paused' && api.getGoalState(OTHER) == null,
      { goal: a4.goal, state: api.getGoalState(GOAL).stored, sibling: api.getGoalState(OTHER) });

    // A5. A first token that is not pause/resume is NOT this door's message — it must fall
    // through to the master doors [T5-R14], not collect a mechanical NACK.
    const before = posts.length;
    const a5 = await door.handle({ text: 'what is the status?', channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    check('A5: a non-mechanical first token is NOT handled here and gets NO NACK — it falls through to the master door [T5-R14]',
      a5.mechanical === false && posts.length === before, { result: a5 });
  }

  // ── B. THE RESUME-SEMANTICS TABLE, ONE FIXTURE PER ROW [C-14] ────────────────────────────────

  // ROW 4 — paused goal.
  {
    const { door, api } = fresh();
    api.writeGoalWord({ goal: GOAL, stored: 'paused', who_stamped: 'owner', evidence_pointer: EV });
    const out = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    check('B-row4: a PAUSED GOAL flips paused→running so armed eligible lanes may launch',
      out.ok === true && api.getGoalState(GOAL).stored === 'running'
      && out.actions.some((a) => a.row === 'goal' && a.change === 'paused→running'),
      { state: api.getGoalState(GOAL).stored, actions: out.actions });
  }

  // ROW 1 — disarmed `incomplete:` from attempt-counter exhaustion.
  {
    const { door, api } = fresh();
    halt(api, 'worker', 'attempt-counter exhaustion');
    api.incrementRecoveryRelaunch({ goal: GOAL, seat: 'worker' });
    const before = api.getCurrentEnding({ goal: GOAL, seat: 'worker' });
    const out = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    const after = api.getCurrentEnding({ goal: GOAL, seat: 'worker' });
    check('B-row1: a COUNTER-EXHAUSTED lane is RE-ARMED (armed 0→1, named_event consumed) and the relaunch BUDGET is NOT spent',
      out.ok === true && Number(before.armed) === 0 && Number(after.armed) === 1 && after.named_event == null
      && after.recovery_relaunch_count === before.recovery_relaunch_count
      && out.actions.some((a) => a.row === 'counter-exhaustion' && a.seat === 'worker'),
      { before: { armed: before.armed, ev: before.named_event, budget: before.recovery_relaunch_count },
        after: { armed: after.armed, ev: after.named_event, budget: after.recovery_relaunch_count } });
  }

  // ROW 2 — `incomplete: blocked-on-human`.
  {
    const { door, api, posts } = fresh();
    halt(api, 'asker', 'blocked-on-human');
    // `insertAsk` always lands `posted = 0`; `postAsk` is what marks it told-to-the-owner, and
    // §2.1's wait predicate reads that flag — an unposted ask holds nothing.
    api.insertAsk({ ask_id: '1724508123.123456', goal: GOAL, seat: 'asker', label: 'work-content', evidence_pointer: EV });
    api.postAsk({ ask_id: '1724508123.123456', posted_at: '2026-08-24T10:00:00Z' });
    const out = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    const after = api.getCurrentEnding({ goal: GOAL, seat: 'asker' });
    const ask = api.getAsk('1724508123.123456');
    const said = posts.map((p) => p.text).join('\n');
    check('B-row2: a BLOCKED-ON-HUMAN lane is REFUSED and pointed at its open ask thread — still disarmed, ask still OPEN, never reaped',
      Number(after.armed) === 0 && ask.state === 'open'
      && out.refusals.some((r) => r.row === 'blocked-on-human' && r.asks.includes('1724508123.123456'))
      && said.includes('1724508123.123456'),
      { armed: after.armed, ask: ask.state, refusals: out.refusals, said });
  }

  // ROW 3 — gate-cap stop (two failed D13s).
  {
    const { door, api, posts } = fresh();
    halt(api, 'gate', 'gate-re-plan cap');
    const out = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    const after = api.getCurrentEnding({ goal: GOAL, seat: 'gate' });
    check('B-row3: a GATE-CAP lane is REFUSED and pointed at the gate decision-ask — no third re-plan, cap not flipped, still disarmed',
      Number(after.armed) === 0 && after.named_event === 'ask-answered'
      && out.refusals.some((r) => r.row === 'gate-cap' && r.seat === 'gate')
      && posts.some((p) => /re-plan cap/.test(p.text)),
      { armed: after.armed, named_event: after.named_event, refusals: out.refusals });
  }

  // "A goal may carry more than one kind at once. Apply every matching row." (spec-recovery §4)
  {
    const { door, api } = fresh();
    api.writeGoalWord({ goal: GOAL, stored: 'paused', who_stamped: 'owner', evidence_pointer: EV });
    halt(api, 'counter', 'attempt-counter exhaustion');
    halt(api, 'human', 'blocked-on-human');
    const out = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    const counter = api.getCurrentEnding({ goal: GOAL, seat: 'counter' });
    const human = api.getCurrentEnding({ goal: GOAL, seat: 'human' });
    check('B-multi: a goal carrying THREE halted kinds applies EVERY matching row independently — goal running, counter lane re-armed, blocked-on-human lane still disarmed',
      api.getGoalState(GOAL).stored === 'running' && Number(counter.armed) === 1 && Number(human.armed) === 0
      && out.actions.length === 2 && out.refusals.length === 1,
      { goal: api.getGoalState(GOAL).stored, counter: counter.armed, human: human.armed, actions: out.actions, refusals: out.refusals });
  }

  // ── C. PAUSE IS THE INVERSE OF THE PAUSED-GOAL ROW **ONLY** ─────────────────────────────────
  {
    const { door, api } = fresh();
    api.writeGoalWord({ goal: GOAL, stored: 'running', who_stamped: 'owner', evidence_pointer: EV });
    api.stampSystem({ goal: GOAL, seat: 'live', ending: 'incomplete', armed: 1, diagnostic: 'context full', evidence_pointer: EV });
    api.insertAsk({ ask_id: '999.111', goal: GOAL, seat: 'live', label: 'work-content', evidence_pointer: EV });
    api.postAsk({ ask_id: '999.111', posted_at: '2026-08-24T11:00:00Z' });
    const out = await door.handle({ text: `pause ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    const lane = api.getCurrentEnding({ goal: GOAL, seat: 'live' });
    const ask = api.getAsk('999.111');
    check('C1: `pause {goal}` flips running→paused and NOTHING else — it does not disarm a lane and does not open an ask',
      out.ok === true && api.getGoalState(GOAL).stored === 'paused'
      && Number(lane.armed) === 1 && ask.state === 'open',
      { state: api.getGoalState(GOAL).stored, laneArmed: lane.armed, ask: ask.state });

    // §4.2: neither verb releases an ask. Resume must leave it exactly as pause did.
    const out2 = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    const ask2 = api.getAsk('999.111');
    check('C2: neither verb flips an ask off `open` [§4.2] — pause/resume is not an answer and never releases one',
      out2.ok === true && ask2.state === 'open' && ask2.authorized_reply_at == null,
      { ask: ask2.state, repliedAt: ask2.authorized_reply_at });
  }

  // ── D. ROW 1'S OTHER HALF: THE ATTEMPT COUNTER ──────────────────────────────────────────────
  //
  // The failure being replaced is a resume that reports `disarmed→armed` and leaves the lane
  // SKIPPED: `fireNamedEvent` re-arms the ending row, but `reconcile.js#counterDisarmed` reads the
  // counter ledger, and nothing was clearing it. Seven lanes on the live instance were in that
  // state (2026-08-27) with no way out of it.
  {
    const { door, api, posts, countersFile } = fresh();
    const before = exhaustCounter(countersFile, 'leader', 'nonterm');
    exhaustCounter(countersFile, 'leader', 'unread');
    exhaustCounter(countersFile, 'plan-drafter', 'nonterm');
    // A different goal's row, to prove the resume is LANE-SCOPED and not a wide clear.
    counters.countAttempt({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: OTHER, seat: 'leader', reasonClass: 'nonterm', n: 3,
    }, { countersFile });
    halt(api, 'leader', 'attempt-counter exhaustion');
    halt(api, 'plan-drafter', 'attempt-counter exhaustion');

    check('D1: the fixture is a real disarmed counter — three same-reason passes reached N=3',
      before && before.attempts === 3, { attempts: before && before.attempts });

    const out = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL, OTHER] });
    const gone = (seat, cls) => counters.peekCounter({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: GOAL, seat, reasonClass: cls,
    }, { countersFile }) === null;

    check('D2: resume CONSUMES the disarmed counter — every row of every lane of that goal is cleared',
      gone('leader', 'nonterm') && gone('leader', 'unread') && gone('plan-drafter', 'nonterm'),
      { leaderNonterm: gone('leader', 'nonterm'), leaderUnread: gone('leader', 'unread'), drafter: gone('plan-drafter', 'nonterm') });

    const other = counters.peekCounter({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: OTHER, seat: 'leader', reasonClass: 'nonterm',
    }, { countersFile });
    check('D3: and it is LANE-SCOPED — another goal\'s counter is untouched (only code-deploy/config-change are wide)',
      other !== null && other.attempts === 1, { other: other && other.attempts });

    const lane = api.getCurrentEnding({ goal: GOAL, seat: 'leader' });
    check('D4: the ENDING half still fires — both acts of row 1 happen, not one instead of the other',
      Number(lane.armed) === 1 && out.actions.some((a) => a.row === 'counter-exhaustion'),
      { armed: lane.armed, rows: out.actions.map((a) => a.row) });

    const counterActions = out.actions.filter((a) => a.row === 'counter');
    check('D5: each cleared row is REPORTED with the count it was cleared from — a silent undo of a silent disarm is no better',
      counterActions.length === 3 && counterActions.every((a) => a.attempts >= 1 && a.reason_class)
        && /attempt counter re-armed \(nonterm, was 3\)/.test(posts[posts.length - 1].text),
      { actions: counterActions.map((a) => `${a.seat}/${a.reason_class}=${a.attempts}`), text: posts[posts.length - 1].text });
  }

  // ── D-RED. THE MUTATION: the door as it stood before this wiring ────────────────────────────
  //
  // No port = the pre-fix shape. The ending row flips and the counter STANDS AT N, which is the
  // exact state the live instance was in: `resume` answers `disarmed→armed` and the reconcile loop
  // skips the lane forever. If this arm ever goes green, the fix has been undone.
  {
    const { door, api, countersFile } = fresh({ withCounterPort: false });
    exhaustCounter(countersFile, 'leader', 'nonterm');
    halt(api, 'leader', 'attempt-counter exhaustion');
    await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    const row = counters.peekCounter({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: GOAL, seat: 'leader', reasonClass: 'nonterm',
    }, { countersFile });
    const lane = api.getCurrentEnding({ goal: GOAL, seat: 'leader' });
    check('D6 [RED-MUTATION]: with no counter port the lane is armed on paper and still disarmed to the reconcile loop',
      row !== null && row.attempts === 3 && Number(lane.armed) === 1,
      { attempts: row && row.attempts, armed: lane.armed });
  }

  // ── D-NO-STORE. The deployed shape: no ending-store port is wired in this process ────────────
  {
    const { door, posts, countersFile } = fresh({ withStore: false });
    exhaustCounter(countersFile, 'leader', 'nonterm');
    const out = await door.handle({ text: `resume ${GOAL}`, channelId: CHANNEL, channelGoal: GOAL, liveGoals: [GOAL] });
    const row = counters.peekCounter({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: GOAL, seat: 'leader', reasonClass: 'nonterm',
    }, { countersFile });
    check('D7: with no store the counter half STILL runs — it is the half the reconcile loop reads — and the missing half is said out loud',
      out.applied === true && row === null && /no ending-store port is wired/.test(posts[posts.length - 1].text),
      { applied: out.applied, row, text: posts[posts.length - 1].text });
  }

  closeEndingStores();
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
})().catch((err) => {
  process.stdout.write(`PROBE probe-chat-pause-resume EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});
