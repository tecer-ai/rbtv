'use strict';

// probe-pause-resume — THE FIFTEENTH INTENT (owner direction 2026-08-28, ~02:00Z + item (2) at
// 02:12Z, `role-action-program/decisions.md`): the owner's mechanical `pause {goal}` /
// `resume {goal}`, crossing the daemon boundary and reaching the ending store, the goal's lane
// endings and the attempt-counter ledger.
//
// WHAT THIS PROBE IS FOR. `chat/probes/probe-chat-pause-resume.js` proves the BRIDGE's door parses,
// targets and renders — but every applier it drives there is an injected fake, because the bridge
// process may hold none of them. This probe measures the OTHER half: what the DAEMON does when a
// caller asks it to pause or resume. The load-bearing legs are C/D — a slug outside the live-goal
// roster must be `NOT_FOUND` rather than an empty success, because an `ok:true` carrying no actions
// reads to the owner as "your goal was paused" — and G, the second-writer hold: a resume that meets
// a live console lane marker must NOT claim the goal is running, because `laneIsPaused` will keep
// skipping it.
//
// In-process parse + dispatch + authz over a REAL (scratch) ending store, a REAL (scratch) goals
// tree with `goals.csv` + goal folders + `taskforce.csv`, and a REAL (scratch) attempt-counter
// ledger. Nothing here spawns, and no live state directory is opened: the ledger path is injected
// and the store is a fresh file under a temp root.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-pause-resume.out');
fs.writeFileSync(outPath, '');

const { createInternalApi, ENVELOPE_VERSION } = require('../dispatch');
const { parseRequest } = require('../../gateway/parse');
const { createAuthzPolicy } = require('../authz');
const { pauseResume } = require('../../../state-store/heart/pause-resume');
const { openEndingStore, bind } = require('../../../state-store');
const { laneIsPaused } = require('../../../supervisor/lane-watch');
const counters = require('../../../supervisor/attempt-counters');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const GOAL = 'probe-pause-goal';
const PARKED = 'probe-parked-goal';
const SYSTEM_PKG = '_channel-master';
const BOGUS = 'no-such-goal-here';
const LEADER = 'leader';
const HELD = 'plan-verifier';
const N = 3;

function seedGoal(root, goal, { lane = 'daemon', seats = [] } = {}) {
  const dir = path.join(root, '.rbtv', 'goals', goal);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'execution-lane'), `${lane}\n`);
  if (seats.length) {
    const rows = seats.map((s) => `tf,${s},,bash,probe-pause-resume,high,35,`);
    fs.writeFileSync(path.join(dir, 'taskforce.csv'),
      `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${rows.join('\n')}\n`);
  }
  return dir;
}

function writeRegister(root, names) {
  const goalsRoot = path.join(root, '.rbtv', 'goals');
  fs.mkdirSync(goalsRoot, { recursive: true });
  fs.writeFileSync(path.join(goalsRoot, 'goals.csv'),
    `name,creation date,due date,type,goal-kind,status\n${names.map((n) => `${n},2026-08-28,,one-shot,interactive,briefed`).join('\n')}\n`);
}

// A lane disarmed exactly the way the supervisor disarms one: the ENDING row carries
// `incomplete: attempt-counter exhaustion` with `armed = 0`, and the LEDGER carries the counter row
// at N. Resume's row 1 is TWO acts and only both together unstick the lane, so the fixture has to
// carry both halves or the arm cannot tell them apart.
function disarmLane(store, { goal, seat, diagnostic, countersFile, driver = 'reconcile-respawn', reasonClass = 'unread' }) {
  store.stampSystem({
    goal, seat, ending: 'incomplete', armed: 0, diagnostic, replace: true,
    evidence_pointer: `probe:${goal}/${seat}`,
  });
  if (countersFile) {
    for (let i = 0; i < N; i += 1) {
      counters.countAttempt({
        driver, goal, seat, reasonClass, n: N, at: '2026-08-28T02:00:00Z',
      }, { countersFile });
    }
  }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('evidence-class: FIXTURE in-process parse+dispatch+authz over a SCRATCH ending store, a SCRATCH goals tree and a SCRATCH attempt-counter ledger (no live state dir, no spawn)');

  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pause-resume-probe-'));
  const countersFile = path.join(root, 'attempt-counters.json');
  const goalDir = seedGoal(root, GOAL, { lane: 'daemon', seats: [LEADER, HELD] });
  const parkedDir = seedGoal(root, PARKED, { lane: 'paused daemon', seats: [LEADER] });
  seedGoal(root, SYSTEM_PKG, { lane: 'console' });
  writeRegister(root, [SYSTEM_PKG, GOAL, PARKED]);

  const db = openEndingStore(path.join(root, '.rbtv', 'runtime', 'ignite', 'heart.db'));
  const store = bind(db);

  const secret = crypto.randomBytes(32).toString('hex');
  const logs = [];
  const api = createInternalApi({
    heartStore: { db }, spawnManager: {}, secret, workspaceRoot: root,
    logger: (row) => logs.push(row),
  });

  const BRIDGE = { id: 'probe-bridge', kind: 'bridge' };
  const AGENT = { id: 'probe-agent', kind: 'agent' };
  const OWNER = { id: 'probe-owner', kind: 'owner' };
  const MASTER = { id: 'probe-agent', kind: 'agent', seat: 'goal-master' };

  async function call(sender, payload) {
    let parsed;
    try {
      parsed = parseRequest({ intent: 'pause-resume', payload });
    } catch (err) {
      return { body: { ok: false, error: { code: err.code, message: err.message } }, gatewayRefused: true };
    }
    const res = await api.dispatch({
      v: ENVELOPE_VERSION, id: crypto.randomUUID(), ts: new Date().toISOString(),
      auth: secret, sender, intent: 'pause-resume', payload: parsed,
    });
    return { body: res, gatewayRefused: false };
  }

  // ── (a) PAUSE — the goal word flips ─────────────────────────────────────────────────────────
  let r = await call(BRIDGE, { verb: 'pause', goal: GOAL });
  check('a1: pause is ok:true and applied',
    r.body.ok === true && r.body.result.applied === true, JSON.stringify(r.body.result || r.body.error));
  check('a2: pause reports the action `running→paused` on the goal row',
    !!(r.body.result && r.body.result.actions.some((x) => x.row === 'goal' && x.change === 'running→paused')),
    JSON.stringify(r.body.result && r.body.result.actions));
  check('a3: the goal-state row now reads `paused` in the REAL store',
    (store.getGoalState(GOAL) || {}).stored === 'paused', JSON.stringify(store.getGoalState(GOAL)));
  check('a4: the result carries the verb and the goal (the shape the bridge renders unchanged)',
    r.body.result.verb === 'pause' && r.body.result.goal === GOAL && Array.isArray(r.body.result.refusals));

  // ── (b) RESUME — all four rows of the resume-semantics table, on ONE goal ────────────────────
  //
  // The goal is paused (from (a)); `leader` is counter-exhausted with a ledger row at N; and
  // `plan-verifier` is blocked-on-human with an open ask. Each row is independent, so one pass must
  // do all three things and refuse only the one it has no rule to lift.
  disarmLane(store, { goal: GOAL, seat: LEADER, diagnostic: 'attempt-counter exhaustion', countersFile });
  disarmLane(store, { goal: GOAL, seat: HELD, diagnostic: 'blocked-on-human' });
  store.insertAsk({ ask_id: 'C0-THREAD-1', goal: GOAL, seat: HELD, label: 'work-content', evidence_pointer: '/tmp/ask.txt' });
  store.postAsk({ ask_id: 'C0-THREAD-1', posted_at: '2026-08-28 02:00' });

  check('b0: fixture — the ledger carries the disarmed counter row before resume',
    counters.listCounters({ goal: GOAL }, { countersFile }).length === 1,
    JSON.stringify(counters.listCounters({ goal: GOAL }, { countersFile })));

  // The handler takes no ledger override (production writes the daemon's own), so the wire arm
  // below proves the CROSSING and this direct call proves the LEDGER half against a scratch file.
  const direct = pauseResume({ db }, {
    workspaceRoot: root, verb: 'resume', goal: GOAL, countersFile,
  });
  check('b1: resume flips the goal row `paused→running`',
    direct.actions.some((x) => x.row === 'goal' && x.change === 'paused→running')
      && (store.getGoalState(GOAL) || {}).stored === 'running',
    JSON.stringify(store.getGoalState(GOAL)));
  // ⚑ ROW 1 IS ONE ACT, NOT TWO REPORTS. With a real store handed to `rearmScope`, `consumeDisarmed`
  // fires `fireNamedEvent` and `counters.rearm` together per subject — that is the module's design
  // (`20260827-c-the-four-named-re-arm-events-g`) and the reason it takes a store at all. So the
  // ENDING half is proven on the ROW, not on a second action line: a `counter` action plus an armed
  // ending is the whole of row 1. The seat loop's own `counter-exhaustion` branch still owns the
  // lane that has a disarmed ending and NO ledger row — proven at b2b.
  check('b2: resume re-arms the counter-exhausted lane — the ENDING row is armed again after the pass',
    Number((store.getCurrentEnding({ goal: GOAL, seat: LEADER }) || {}).armed) === 1,
    JSON.stringify(store.getCurrentEnding({ goal: GOAL, seat: LEADER })));
  check('b3: resume CLEARS the attempt-counter ledger row — the half the reconcile loop reads (rearmScope reported it)',
    direct.actions.some((x) => x.row === 'counter' && x.seat === LEADER)
      && counters.listCounters({ goal: GOAL }, { countersFile }).length === 0,
    JSON.stringify(counters.listCounters({ goal: GOAL }, { countersFile })));
  check('b4: the blocked-on-human lane is REFUSED and the refusal names its ask id',
    direct.refusals.some((x) => x.row === 'blocked-on-human' && x.seat === HELD && /C0-THREAD-1/.test(x.text)),
    JSON.stringify(direct.refusals));
  check('b5: resume never releases the ask [§4.2] — it still reads open after the verb',
    (store.listOpenAsks({ goal: GOAL, seat: HELD }) || []).length === 1,
    JSON.stringify(store.listOpenAsks({ goal: GOAL, seat: HELD })));
  check('b6: applied is true — the unparked goal really is running',
    direct.applied === true && direct.found === true, JSON.stringify({ applied: direct.applied, reason: direct.reason }));

  // b2b — the OTHER half of row 1: a lane disarmed on the ending with NO ledger row (nothing for
  // `rearmScope` to sweep) is re-armed by the executor's own seat loop, which is the branch the
  // bridge's table has always owned.
  {
    seedGoal(root, GOAL, { lane: 'daemon', seats: [LEADER, HELD] });
    store.writeGoalWord({ goal: GOAL, stored: 'paused', who_stamped: 'owner', evidence_pointer: 'probe:b2b' });
    disarmLane(store, { goal: GOAL, seat: LEADER, diagnostic: 'attempt-counter exhaustion' });
    const ledgerEmpty = counters.listCounters({ goal: GOAL }, { countersFile }).length === 0;
    const second = pauseResume({ db }, { workspaceRoot: root, verb: 'resume', goal: GOAL, countersFile });
    check('b2b: with an EMPTY ledger, the seat loop\'s own row-1 branch re-arms the lane (`disarmed→armed`)',
      ledgerEmpty
        && second.actions.some((x) => x.row === 'counter-exhaustion' && x.seat === LEADER && x.change === 'disarmed→armed')
        && Number((store.getCurrentEnding({ goal: GOAL, seat: LEADER }) || {}).armed) === 1,
      JSON.stringify(second.actions));
  }

  // The same verb across the REAL wire, to prove the handler is what the caller reaches.
  r = await call(BRIDGE, { verb: 'resume', goal: GOAL });
  check('b7: wire — resume crosses parse -> dispatch -> authz -> executor and returns the door\'s shape',
    r.body.ok === true && r.body.result.verb === 'resume' && Array.isArray(r.body.result.actions),
    JSON.stringify(r.body.result || r.body.error));

  // ── (c) A BOGUS SLUG IS `NOT_FOUND`, NEVER AN EMPTY SUCCESS ─────────────────────────────────
  r = await call(BRIDGE, { verb: 'pause', goal: BOGUS });
  check('c1: a slug outside the live-goal roster is NOT_FOUND and the message names it',
    r.body.ok === false && r.body.error.code === 'NOT_FOUND' && r.body.error.message.includes(BOGUS),
    r.body.error && r.body.error.message);

  // ── (d) A SYSTEM PACKAGE IS NOT A GOAL THE OWNER PAUSES ─────────────────────────────────────
  //
  // MEASURED, NOT ASSUMED — and the measurement corrected the claim. `_channel-master` is refused
  // THREE times and the OUTERMOST refusal fires first: `BUS_NAME_RE` requires an alphanumeric first
  // character, so the leading `_` never reaches the core (d1); `isSafeName` refuses it again inside
  // the executor before the roster is consulted at all. The roster's own `_` exclusion is therefore
  // NOT the operative guard on this path — it is what keeps the LIST itself honest for every reader
  // of it (d2 asserts exactly that, and nothing more). A probe asserting `NOT_FOUND` here would
  // have reported a code path that never ran as covered.
  r = await call(BRIDGE, { verb: 'pause', goal: SYSTEM_PKG });
  check('d1: `_channel-master` never crosses the door — the leading `_` fails BUS_NAME_RE at the gateway',
    r.gatewayRefused === true, JSON.stringify(r.body.error));
  const roster = require('../../../state-store/heart/pause-resume').liveGoals(root);
  const asIfAdmitted = pauseResume({ db }, { workspaceRoot: root, verb: 'pause', goal: SYSTEM_PKG, countersFile });
  check('d2: the ROSTER excludes `_channel-master` (lane-watch:464\'s exclusion) though its folder AND its register row both exist, and the executor refuses it at the name check that fires first',
    !roster.includes(SYSTEM_PKG) && asIfAdmitted.found === false,
    JSON.stringify({ roster, asIfAdmitted }));
  check('d3: control — the roster is not simply empty: it names the two real goals, in register order',
    JSON.stringify(roster) === JSON.stringify([GOAL, PARKED]), JSON.stringify(roster));

  // ── (e) AUTHORIZATION IS BRIDGE-ONLY ────────────────────────────────────────────────────────
  const policy = createAuthzPolicy();
  check('e1: authz — the chat bridge is allowed', policy.canPauseResume({ sender: BRIDGE }).allowed === true);
  check('e2: authz — an agent token is REFUSED (a hold an agent can release is not a hold)',
    policy.canPauseResume({ sender: AGENT }).allowed === false, policy.canPauseResume({ sender: AGENT }).reason);
  check('e3: authz — a proven goal-master is REFUSED', policy.canPauseResume({ sender: MASTER }).allowed === false);
  check('e4: authz — even the owner token is REFUSED: the console route is `rbtv goal pause`',
    policy.canPauseResume({ sender: OWNER }).allowed === false);
  r = await call(AGENT, { verb: 'pause', goal: GOAL });
  check('e5: wire — a non-bridge sender is UNAUTHORIZED_SENDER and NOTHING is written',
    r.body.ok === false && r.body.error.code === 'UNAUTHORIZED_SENDER'
      && (store.getGoalState(GOAL) || {}).stored === 'running',
    `${r.body.error && r.body.error.code} / row=${JSON.stringify(store.getGoalState(GOAL))}`);

  // ── (f) SHAPE IS REFUSED, NEVER IGNORED ─────────────────────────────────────────────────────
  r = await call(BRIDGE, { verb: 'pause', goal: GOAL, comments: 'and tell the team' });
  check('f1: an unknown payload key is REFUSED AT THE GATEWAY — never a silently ignored key',
    r.gatewayRefused === true && /comments/.test(r.body.error.message), r.body.error && r.body.error.message);
  r = await call(BRIDGE, { verb: 'halt', goal: GOAL });
  check('f2: a verb outside the closed two-member enum is refused at the gateway',
    r.gatewayRefused === true && /verb/.test(r.body.error.message), r.body.error && r.body.error.message);
  r = await call(BRIDGE, { verb: 'pause', goal: '../../etc' });
  check('f3: a goal carrying path separators is refused at the gateway',
    r.gatewayRefused === true, r.body.error && r.body.error.message);
  // The CORE re-validates independently of the gateway (DEC-3): the same refusals, asked of dispatch
  // with the gateway skipped, must still fire.
  const raw = await api.dispatch({
    v: ENVELOPE_VERSION, id: crypto.randomUUID(), ts: new Date().toISOString(),
    auth: secret, sender: BRIDGE, intent: 'pause-resume', payload: { verb: 'pause', goal: GOAL, comments: 'x' },
  });
  check('f4: the CORE refuses the unknown key too — the gateway copy is not the only check (DEC-3)',
    raw.ok === false && raw.error.code === 'VALIDATION_FAILED', JSON.stringify(raw.error));

  // ── (g) THE SECOND PAUSE WRITER: a live console marker HOLDS, and resume says so ─────────────
  //
  // `PARKED` carries `paused daemon` on disk (what `rbtv goal pause` writes) and, after the resume
  // below, a goal-state row reading `running`. Before this change the row would have decided and
  // the goal would have silently un-parked.
  store.writeGoalWord({ goal: PARKED, stored: 'paused', who_stamped: 'owner', evidence_pointer: 'probe:parked' });
  r = await call(BRIDGE, { verb: 'resume', goal: PARKED });
  check('g1: resume on a console-parked goal is ok:true but applied:false — the goal is NOT claimed to be running',
    r.body.ok === true && r.body.result.applied === false && r.body.result.reason === 'lane-file-paused',
    JSON.stringify(r.body.result));
  check('g2: the refusal NAMES the console lane marker and the command that lifts it',
    r.body.result.refusals.some((x) => x.row === 'lane-file' && /console lane marker/.test(x.text) && new RegExp(`rbtv goal resume ${PARKED}`).test(x.text)),
    JSON.stringify(r.body.result.refusals));
  check('g3: the acts that DID happen are still reported — the goal row really flipped',
    r.body.result.actions.some((x) => x.row === 'goal' && x.change === 'paused→running')
      && (store.getGoalState(PARKED) || {}).stored === 'running',
    JSON.stringify(store.getGoalState(PARKED)));
  check('g4: `laneIsPaused` is TRUE with the lane file `paused daemon` and the store row `running` — either surface holds',
    laneIsPaused(parkedDir, { db }) === true);
  check('g5: control — the same gate is FALSE when both surfaces say running (it is an OR, not a constant)',
    laneIsPaused(goalDir, { db }) === false,
    `row=${JSON.stringify(store.getGoalState(GOAL))} lane=${fs.readFileSync(path.join(goalDir, 'execution-lane'), 'utf8').trim()}`);
  check('g6: control — `laneIsPaused` is TRUE from the STORE ROW alone (lane file `daemon`)',
    (() => {
      store.writeGoalWord({ goal: GOAL, stored: 'paused', who_stamped: 'owner', evidence_pointer: 'probe:row-only' });
      const v = laneIsPaused(goalDir, { db });
      store.writeGoalWord({ goal: GOAL, stored: 'running', who_stamped: 'owner', evidence_pointer: 'probe:row-only' });
      return v === true;
    })());

  // ── RED ARMS: each guard removed on a COPY, and the arm it protects must go red ──────────────
  const mutDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pause-resume-mut-'));

  // R1 — the authz predicate. Without it, an agent token pauses a goal.
  {
    const src = fs.readFileSync(path.join(__dirname, '..', 'authz.js'), 'utf8');
    const ANCHOR = "const allowed = !!sender && sender.kind === 'bridge';\n    const seenAs = !sender ? 'no attested sender at all'\n      : (typeof sender.kind === 'string' && sender.kind\n        ? `a ${sender.kind} token`\n        : 'a sender carrying no attested kind');\n    return {\n      allowed,\n      principals: allowed ? ['bridge'] : [],\n      // S-3's rule, applied: state the predicate ACTUALLY ENFORCED and the kind SEEN.\n      reason: allowed\n        ? 'authorized as: the chat bridge'\n        : `pause-resume requires the chat BRIDGE token; you are ${seenAs}`,";
    check('R0: red-proof anchor — the pause-resume predicate is present verbatim in authz.js', src.includes(ANCHOR));
    const beside = path.join(__dirname, '..', `authz.pause-resume-mutant-${process.pid}.js`);
    try {
      fs.writeFileSync(beside, src.replace(ANCHOR, ANCHOR.replace("sender.kind === 'bridge'", 'true')));
      const mut = require(beside);
      const mutPolicy = mut.createAuthzPolicy();
      check('R1: red-proof — with the bridge predicate dropped, an AGENT token is authorized to pause (COPY, discarded)',
        mutPolicy.canPauseResume({ sender: AGENT }).allowed === true);
    } finally {
      try { fs.rmSync(beside, { force: true }); } catch {}
    }
  }

  // R2 — the roster check. Without it, a bogus slug is accepted and writes a goal-state row.
  {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'state-store', 'heart', 'pause-resume.js'), 'utf8');
    const ANCHOR = "if (!liveGoals(workspaceRoot).includes(String(goal))) {";
    check('R0b: red-proof anchor — the roster check is present in the executor', src.includes(ANCHOR));
    const beside = path.join(__dirname, '..', '..', '..', 'state-store', 'heart', `pause-resume.mutant-${process.pid}.js`);
    try {
      fs.writeFileSync(beside, src.replace(ANCHOR, 'if (false) {'));
      const mut = require(beside);
      const mutOut = mut.pauseResume({ db }, { workspaceRoot: root, verb: 'pause', goal: BOGUS, countersFile });
      check('R2: red-proof — with the roster check dropped, a BOGUS slug passes and is applied (COPY, discarded)',
        mutOut.found === true && mutOut.applied === true,
        JSON.stringify({ found: mutOut.found, applied: mutOut.applied }));
    } finally {
      try { fs.rmSync(beside, { force: true }); } catch {}
    }
  }

  // R3 — the laneIsPaused fall-through. Reverted to the old `return` and the console-parked goal
  // reads as NOT paused, which is the silent un-park this change exists to prevent.
  {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'supervisor', 'lane-watch.js'), 'utf8');
    const ANCHOR = "if (row && row.stored === 'paused') return true;";
    check('R0c: red-proof anchor — the OR fall-through is present in laneIsPaused', src.includes(ANCHOR));
    const beside = path.join(__dirname, '..', '..', '..', 'supervisor', `lane-watch.mutant-${process.pid}.js`);
    try {
      fs.writeFileSync(beside, src.replace(ANCHOR, "if (row && row.stored) return row.stored === 'paused';"));
      const mut = require(beside);
      check('R3: red-proof — with the pre-change `return` restored, the console-parked goal reads NOT paused while its row says running (COPY, discarded)',
        mut.laneIsPaused(parkedDir, { db }) === false);
    } finally {
      try { fs.rmSync(beside, { force: true }); } catch {}
    }
  }

  try { db.close(); } catch {}
  try { fs.rmSync(root, { recursive: true, force: true }); } catch {}
  try { fs.rmSync(mutDir, { recursive: true, force: true }); } catch {}

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`RESULT: ${failed.length ? 'FAIL' : 'PASS'} — ${checks.length - failed.length}/${checks.length} checks`);
  out(`WALL_MS ${Date.now() - start}`);
  out(`EXIT ${failed.length ? 1 : 0}`);
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(failed.length ? 1 : 0);
}

main().catch((err) => {
  out(`PROBE FAULT: ${err && err.stack ? err.stack : err}`);
  out('EXIT 1');
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(1);
});
