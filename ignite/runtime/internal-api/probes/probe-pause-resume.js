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
// reads to the owner as "your goal was paused" — and G, one pause record: a leftover console
// `paused ` prefix does not hold a resume, because the store row is the only truth.
//
// In-process parse + dispatch + authz over a REAL (scratch) ending store, a REAL (scratch) goals
// tree with `goals.csv` + goal folders + `taskforce.csv`, and a REAL (scratch) attempt-counter
// ledger. Nothing here spawns, and no live state directory is opened: the ledger path is injected
// and the store is a fresh file under a temp root.
//
// SECTION (h) ADDS A SECOND WORKSPACE IN WHICH THE TWO STORES ARE DIFFERENT FILES. Sections (a)-(g)
// hand the dispatcher a `heartStore` whose `db` IS the workspace ending store, so they cannot tell
// a writer bound to the CALLER'S store from one bound to the HOME — which is how they read 38/38
// green while the live Slack `pause` wrote the daemon's private `{data_root}/heart.db` and the lane
// gate, reading `<workspace>/.rbtv/runtime/ignite/heart.db`, never saw it. (h) pulls them apart and
// names the file every arm read.

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
const {
  openEndingStore, openEndingStoreFor, endingStorePath, bind,
} = require('../../../state-store');
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
const LANE_GOAL = 'probe-lane-scope-goal';
const LANE_A = 'lane-a';
const LANE_B = 'lane-b';

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
  out('evidence-class: FIXTURE in-process parse+dispatch+authz over SCRATCH ending stores, SCRATCH goals trees and a SCRATCH attempt-counter ledger (no live state dir, no live store, no spawn). Section (h) runs a SECOND workspace whose ending home is a pre-existing file COPIED into place and whose daemon-side lane store is a DIFFERENT file.');

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

  async function call(sender, payload, useApi = api) {
    let parsed;
    try {
      parsed = parseRequest({ intent: 'pause-resume', payload });
    } catch (err) {
      return { body: { ok: false, error: { code: err.code, message: err.message } }, gatewayRefused: true };
    }
    const res = await useApi.dispatch({
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

  // ── (a2) `chat_user` — OWNER RE-RULING D-4(a): reported by the bridge, named in the evidence
  // text, NEVER an authorization input, and `who_stamped` stays the closed `owner`/`system` enum ──
  store.writeGoalWord({ goal: GOAL, stored: 'running', who_stamped: 'system', evidence_pointer: 'probe:a2-reset' });
  r = await call(BRIDGE, { verb: 'pause', goal: GOAL, chat_user: 'U0123ABC' });
  check('a2a: pause WITH chat_user is still ok:true/applied, and who_stamped stays the closed `owner` enum',
    r.body.ok === true && r.body.result.applied === true && (store.getGoalState(GOAL) || {}).who_stamped === 'owner',
    JSON.stringify(store.getGoalState(GOAL)));
  check('a2b: the evidence pointer NAMES the Slack user reported by the bridge',
    /by U0123ABC \(reported by bridge\)/.test((store.getGoalState(GOAL) || {}).evidence_pointer || ''),
    (store.getGoalState(GOAL) || {}).evidence_pointer);
  store.writeGoalWord({ goal: GOAL, stored: 'running', who_stamped: 'system', evidence_pointer: 'probe:a2-reset2' });
  r = await call(BRIDGE, { verb: 'pause', goal: GOAL });
  check('a2c: pause WITHOUT chat_user keeps the pre-existing evidence wording, byte-for-byte',
    r.body.ok === true
      && (store.getGoalState(GOAL) || {}).evidence_pointer === `owner pause in chat · goal ${GOAL}`,
    (store.getGoalState(GOAL) || {}).evidence_pointer);

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
  const direct = pauseResume({
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
    const second = pauseResume({ workspaceRoot: root, verb: 'resume', goal: GOAL, countersFile });
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
  const asIfAdmitted = pauseResume({ workspaceRoot: root, verb: 'pause', goal: SYSTEM_PKG, countersFile });
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
  r = await call(BRIDGE, { verb: 'pause', goal: GOAL, chat_user: 'not-a-slack-id' });
  check('f5: a malformed chat_user is refused AT THE GATEWAY, naming the field — absence is fine, garbage is not',
    r.gatewayRefused === true && /chat_user/.test(r.body.error.message), r.body.error && r.body.error.message);
  const raw2 = await api.dispatch({
    v: ENVELOPE_VERSION, id: crypto.randomUUID(), ts: new Date().toISOString(),
    auth: secret, sender: BRIDGE, intent: 'pause-resume', payload: { verb: 'pause', goal: GOAL, chat_user: 'not-a-slack-id' },
  });
  check('f6: the CORE refuses the same malformed chat_user independently of the gateway (DEC-3)',
    raw2.ok === false && raw2.error.code === 'VALIDATION_FAILED' && /chat_user/.test(raw2.error.message), JSON.stringify(raw2.error));

  // ── (g) ONE PAUSE RECORD: a leftover console prefix does NOT hold a resume ──────────────────
  //
  // `PARKED` still carries a leftover `paused daemon` on disk. Resume writes the row `running`
  // and reports applied:true — the file is not a pause surface. `laneIsPaused` then treats the
  // leftover as stale (running row wins) and strips it.
  store.writeGoalWord({ goal: PARKED, stored: 'paused', who_stamped: 'owner', evidence_pointer: 'probe:parked' });
  r = await call(BRIDGE, { verb: 'resume', goal: PARKED });
  check('g1: resume on a leftover-prefix goal is applied:true — the store row is the only truth',
    r.body.ok === true && r.body.result.applied === true,
    JSON.stringify(r.body.result));
  check('g2: resume does not emit a lane-file refusal',
    !(r.body.result.refusals || []).some((x) => x.row === 'lane-file'),
    JSON.stringify(r.body.result.refusals));
  check('g3: the goal row really flipped to running',
    r.body.result.actions.some((x) => x.row === 'goal' && x.change === 'paused→running')
      && (store.getGoalState(PARKED) || {}).stored === 'running',
    JSON.stringify(store.getGoalState(PARKED)));
  check('g4: `laneIsPaused` is FALSE with leftover prefix + running row — the store won, prefix stripped',
    laneIsPaused(parkedDir, { db }) === false
      && fs.readFileSync(path.join(parkedDir, 'execution-lane'), 'utf8') === 'daemon\n');
  check('g5: control — the same gate is FALSE when the row is running and the file is clean',
    laneIsPaused(goalDir, { db }) === false,
    `row=${JSON.stringify(store.getGoalState(GOAL))} lane=${fs.readFileSync(path.join(goalDir, 'execution-lane'), 'utf8').trim()}`);
  check('g6: control — `laneIsPaused` is TRUE from the STORE ROW alone (lane file `daemon`)',
    (() => {
      store.writeGoalWord({ goal: GOAL, stored: 'paused', who_stamped: 'owner', evidence_pointer: 'probe:row-only' });
      const v = laneIsPaused(goalDir, { db });
      store.writeGoalWord({ goal: GOAL, stored: 'running', who_stamped: 'owner', evidence_pointer: 'probe:row-only' });
      return v === true;
    })());
  check('g7: leftover prefix with NO row still reads paused (never silently un-pause) and is ported',
    (() => {
      const orphanDir = seedGoal(root, 'probe-orphan-legacy', { lane: 'paused daemon' });
      writeRegister(root, [SYSTEM_PKG, GOAL, PARKED, 'probe-orphan-legacy']);
      const v = laneIsPaused(orphanDir, { db });
      const stored = (store.getGoalState('probe-orphan-legacy') || {}).stored;
      const file = fs.readFileSync(path.join(orphanDir, 'execution-lane'), 'utf8');
      return v === true && stored === 'paused' && file === 'daemon\n';
    })());

  // ── (h) THE ENDING HOME, AND A GOAL WITH NO TASKFORCE ───────────────────────────────────────
  //
  // WHY A SECOND WORKSPACE. Everything above hands the dispatcher `heartStore: { db }` where `db`
  // IS the workspace ending store, so a writer that bound the CALLER'S store and a writer that
  // bound the HOME were indistinguishable — 38/38 green while, in production, the Slack `pause`
  // wrote `{data_root}/heart.db` and the lane gate read `<workspace>/.rbtv/runtime/ignite/heart.db`
  // and never saw it (2026-08-28 03:37Z, goal `channel-master-diag-test`). This fixture pulls the
  // two files APART: the daemon's own `heartStore` is a store of its own under `lane-state/`, the
  // home is the workspace path, and every arm below names which file it read.
  //
  // THE HOME IS A PRE-EXISTING FILE, COPIED IN. A donor store is opened, given the two goals'
  // rows, WAL-checkpointed so the bytes are really in the `.db`, and copied to `endingStorePath()`
  // — so the arms measure a writer opening a store that was already there with rows in it, not one
  // it created blank. The donor is built here rather than copied from an instance path: a probe
  // that reads a live store would be an instance path in the tree AND a live read this seat is
  // walled off from.
  //
  // `probe-seatless-goal` HAS NO `taskforce.csv`, which is the shape of the live fixture the
  // failure was found on: `seeding.js#readTaskforce` THROWS on a missing file (`:525-530`), so this
  // is the goal whose resume used to die inside its own logger.
  const hRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'pause-resume-home-'));
  const HGOAL = 'probe-seatless-goal';
  const HSEATED = 'probe-seated-goal';
  const hGoalDir = seedGoal(hRoot, HGOAL, { lane: 'daemon' });
  seedGoal(hRoot, HSEATED, { lane: 'daemon', seats: [LEADER] });
  writeRegister(hRoot, [HGOAL, HSEATED]);

  const donorPath = path.join(hRoot, 'donor-heart.db');
  {
    const donorDb = openEndingStore(donorPath);
    const donor = bind(donorDb);
    donor.writeGoalWord({ goal: HGOAL, stored: 'running', who_stamped: 'system', evidence_pointer: 'probe:donor' });
    donor.writeGoalWord({ goal: HSEATED, stored: 'paused', who_stamped: 'owner', evidence_pointer: 'probe:donor' });
    donorDb.exec('PRAGMA wal_checkpoint(TRUNCATE);');
  }
  fs.mkdirSync(path.dirname(endingStorePath(hRoot)), { recursive: true });
  fs.copyFileSync(donorPath, endingStorePath(hRoot));

  // The DAEMON'S OWN store — what `{data_root}/heart.db` is to the running unit, and the handle the
  // executor used to write.
  const laneDb = openEndingStore(path.join(hRoot, 'lane-state', 'heart.db'));
  const lane = bind(laneDb);
  const home = bind(openEndingStoreFor(hRoot));
  const hLogs = [];
  const hApi = createInternalApi({
    heartStore: { db: laneDb }, spawnManager: {}, secret, workspaceRoot: hRoot,
    logger: (row) => hLogs.push(row),
  });

  check('h1: fixture — the HOME carries the donor rows and the daemon\'s own store carries NOTHING for either goal (the two files really are apart)',
    (home.getGoalState(HGOAL) || {}).stored === 'running'
      && (home.getGoalState(HSEATED) || {}).stored === 'paused'
      && !lane.getGoalState(HGOAL) && !lane.getGoalState(HSEATED),
    JSON.stringify({ home: home.getGoalState(HGOAL), lane: lane.getGoalState(HGOAL) }));

  r = await call(BRIDGE, { verb: 'pause', goal: HGOAL }, hApi);
  check('h2: pause writes the goal word into the WORKSPACE ending store — the file the lane gate reads',
    r.body.ok === true && r.body.result.applied === true
      && (home.getGoalState(HGOAL) || {}).stored === 'paused',
    JSON.stringify({ result: r.body.result || r.body.error, home: home.getGoalState(HGOAL) }));
  check('h3: pause writes NOTHING into the daemon\'s separately-bound lane store — the split that made the live pause inert',
    !lane.getGoalState(HGOAL), JSON.stringify(lane.getGoalState(HGOAL)));
  check('h4: `laneIsPaused` — THE READER ITSELF, holding the daemon\'s lane store — now answers TRUE for the paused goal',
    laneIsPaused(hGoalDir, { db: laneDb }) === true,
    `lane-file=${fs.readFileSync(path.join(hGoalDir, 'execution-lane'), 'utf8').trim()} home-row=${JSON.stringify(home.getGoalState(HGOAL))}`);

  // (c) — the seatless resume. `applied:true`, the warn, the row, and NO throw.
  r = await call(BRIDGE, { verb: 'resume', goal: HGOAL }, hApi);
  check('h5: resume on a goal with NO taskforce.csv does not fault — it is ok:true and applied',
    r.body.ok === true && r.body.result.applied === true,
    JSON.stringify(r.body.result || r.body.error));
  check('h6: the store really reads `running` afterwards — the answer and the file agree',
    (home.getGoalState(HGOAL) || {}).stored === 'running', JSON.stringify(home.getGoalState(HGOAL)));
  check('h7: the unreadable lane roster is REPORTED as a warn naming the goal, not thrown',
    hLogs.some((row) => row.level === 'warn' && /could not enumerate/.test(String(row.message)) && row.goal === HGOAL),
    JSON.stringify(hLogs.filter((row) => row.level === 'warn')));

  // (d) — the seated goal still gets its table. A disarmed `incomplete` lane in the HOME is lifted.
  disarmLane(home, { goal: HSEATED, seat: LEADER, diagnostic: 'attempt-counter exhaustion' });
  r = await call(BRIDGE, { verb: 'resume', goal: HSEATED }, hApi);
  check('h8: control — resume on a goal WITH a taskforce still lifts its disarmed `incomplete` lane, out of the HOME',
    r.body.ok === true
      && r.body.result.actions.some((x) => x.row === 'counter-exhaustion' && x.seat === LEADER && x.change === 'disarmed→armed')
      && Number((home.getCurrentEnding({ goal: HSEATED, seat: LEADER }) || {}).armed) === 1,
    JSON.stringify({ actions: r.body.result && r.body.result.actions, ending: home.getCurrentEnding({ goal: HSEATED, seat: LEADER }) }));

  // (e) — the refusal is journalled daemon-side. Before this change only the applied branch wrote a
  // line, so a mistyped slug left the daemon journal empty and only the bridge's NACK survived.
  const beforeRefusal = hLogs.length;
  r = await call(BRIDGE, { verb: 'pause', goal: BOGUS }, hApi);
  check('h9: a `no-such-goal` refusal is NOT_FOUND *and* leaves a daemon journal line naming the verb and the slug',
    r.body.ok === false && r.body.error.code === 'NOT_FOUND'
      && hLogs.slice(beforeRefusal).some((row) => row.level === 'info' && /REFUSED/.test(String(row.message))
        && row.goal === BOGUS && row.verb === 'pause' && row.reason === 'no-such-goal'),
    JSON.stringify(hLogs.slice(beforeRefusal)));

  // ── (i) LANE-SCOPED RESUME — `d-recovery-retry-scope` (owner ruling 2026-08-31): a resume aimed
  // at ONE seat re-arms ONLY that lane. Two seats, disarmed the IDENTICAL way (both
  // counter-exhaustion, both at N), so only the SCOPE — never the diagnosis — can tell i2 apart
  // from i3: a false pass here means the fix reads as scoped when it is actually still sweeping the
  // whole goal, exactly the pre-fix defect (proven RED separately, see the report).
  seedGoal(root, LANE_GOAL, { lane: 'daemon', seats: [LANE_A, LANE_B] });
  writeRegister(root, [SYSTEM_PKG, GOAL, PARKED, LANE_GOAL]);
  disarmLane(store, {
    goal: LANE_GOAL, seat: LANE_A, diagnostic: 'attempt-counter exhaustion', countersFile,
  });
  disarmLane(store, {
    goal: LANE_GOAL, seat: LANE_B, diagnostic: 'attempt-counter exhaustion', countersFile,
  });
  check('i0: fixture — both lanes disarmed and both counters at N, before the lane-scoped resume',
    Number((store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_A }) || {}).armed) === 0
      && Number((store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_B }) || {}).armed) === 0
      && counters.listCounters({ goal: LANE_GOAL }, { countersFile }).length === 2,
    JSON.stringify(counters.listCounters({ goal: LANE_GOAL }, { countersFile })));

  const laneOut = pauseResume({
    workspaceRoot: root, verb: 'resume', goal: LANE_GOAL, seat: LANE_A, countersFile,
  });
  check('i1: the act accepts a (goal, seat) pair and reports the targeted seat back',
    laneOut.found === true && laneOut.applied === true && laneOut.seat === LANE_A,
    JSON.stringify(laneOut));
  check('i2: lane-a — the TARGETED lane — is re-armed: ending armed again and its counter row cleared',
    Number((store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_A }) || {}).armed) === 1
      && counters.listCounters({ goal: LANE_GOAL }, { countersFile }).every((rr) => rr.seat !== LANE_A),
    JSON.stringify({
      ending: store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_A }),
      counters: counters.listCounters({ goal: LANE_GOAL }, { countersFile }),
    }));
  check('i3: lane-b — the UNTARGETED lane — is UNCHANGED: still disarmed, its counter row still at N',
    Number((store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_B }) || {}).armed) === 0
      && (store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_B }) || {}).diagnostic === 'attempt-counter exhaustion'
      && counters.listCounters({ goal: LANE_GOAL }, { countersFile }).some((rr) => rr.seat === LANE_B && rr.attempts === N),
    JSON.stringify({
      ending: store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_B }),
      counters: counters.listCounters({ goal: LANE_GOAL }, { countersFile }),
    }));
  check('i4: the lane-scoped act touches ONLY the lane — no `row: goal` action (the goal word is not this act\'s to flip)',
    !laneOut.actions.some((x) => x.row === 'goal'), JSON.stringify(laneOut.actions));

  // (i5) `pause` REFUSES a `seat` — it has no per-lane effect, and an unusable field is a refusal,
  // never quiet dead input (the fifteenth intent's own `comments`-refusal precedent).
  r = await call(BRIDGE, { verb: 'pause', goal: LANE_GOAL, seat: LANE_A });
  check('i5: `pause` with a `seat` is refused at the gateway, naming the field',
    r.gatewayRefused === true && r.body.error.code === 'SHAPE_INVALID' && /verb=resume/.test(r.body.error.message),
    JSON.stringify(r.body.error));

  // (i6)-(i7) — wire: the same scoping crosses parse -> dispatch -> authz -> executor. Re-disarm
  // lane-a (i1-i4 already consumed it) so the wire call has a real lane to lift.
  disarmLane(store, {
    goal: LANE_GOAL, seat: LANE_A, diagnostic: 'attempt-counter exhaustion', countersFile,
  });
  r = await call(BRIDGE, { verb: 'resume', goal: LANE_GOAL, seat: LANE_A });
  check('i6: wire — the lane-scoped resume crosses parse -> dispatch -> authz and echoes `seat` in the result',
    r.body.ok === true && r.body.result.applied === true && r.body.result.seat === LANE_A,
    JSON.stringify(r.body.result || r.body.error));
  check('i7: wire — lane-b is STILL untouched after the wire-crossing call too',
    Number((store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_B }) || {}).armed) === 0,
    JSON.stringify(store.getCurrentEnding({ goal: LANE_GOAL, seat: LANE_B })));

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
      const mutOut = mut.pauseResume({ workspaceRoot: root, verb: 'pause', goal: BOGUS, countersFile });
      check('R2: red-proof — with the roster check dropped, a BOGUS slug passes and is applied (COPY, discarded)',
        mutOut.found === true && mutOut.applied === true,
        JSON.stringify({ found: mutOut.found, applied: mutOut.applied }));
    } finally {
      try { fs.rmSync(beside, { force: true }); } catch {}
    }
  }

  // R3 — leftover prefix with no row. Drop the port and a file-only pause reads NOT paused.
  {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'supervisor', 'lane-watch.js'), 'utf8');
    const ANCHOR = 'if (!legacy) return false;';
    check('R0c: red-proof anchor — leftover-prefix consumption is present in laneIsPaused', src.includes(ANCHOR));
    const beside = path.join(__dirname, '..', '..', '..', 'supervisor', `lane-watch.mutant-${process.pid}.js`);
    try {
      fs.writeFileSync(beside, src.replace(ANCHOR, 'if (true) return false;'));
      delete require.cache[require.resolve(beside)];
      const mut = require(beside);
      const orphanDir = seedGoal(root, 'probe-orphan-red', { lane: 'paused daemon' });
      check('R3: red-proof — with leftover consumption deleted, a prefix-only pause reads NOT paused (COPY, discarded)',
        mut.laneIsPaused(orphanDir, { db }) === false);
    } finally {
      try { fs.rmSync(beside, { force: true }); } catch {}
    }
  }

  // R4 — the ENDING HOME. With `bind(heartStore.db)` and its parameter restored, the pause lands in
  // the daemon's own store, the workspace home never hears about it, and the lane gate — the whole
  // reason the owner typed the word — answers NOT paused. This is the live 2026-08-28 defect, run
  // on a copy.
  {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'state-store', 'heart', 'pause-resume.js'), 'utf8');
    // Anchor widened alongside `d-recovery-retry-scope`'s `seat` parameter (same move the
    // `chat_user` field made at c1e3a864): the red-proof re-checks the ending-home defect, not a
    // frozen signature — the anchor tracks the real one so a stale copy can't silently stop firing.
    const SIG = 'function pauseResume({\n  workspaceRoot, verb, goal, seat = undefined, countersFile = undefined, chatUser = undefined, logger = null,\n}) {';
    const BIND = '  const store = bind(openEndingStoreFor(workspaceRoot));';
    check('R0d: red-proof anchors — the home resolver and its no-store-parameter signature are present in the executor',
      src.includes(SIG) && src.includes(BIND));
    const beside = path.join(__dirname, '..', '..', '..', 'state-store', 'heart', `pause-resume.home-mutant-${process.pid}.js`);
    try {
      fs.writeFileSync(beside, src
        .replace(SIG, 'function pauseResume(heartStore, {\n  workspaceRoot, verb, goal, seat = undefined, countersFile = undefined, chatUser = undefined, logger = null,\n}) {')
        .replace(BIND, '  const store = bind(heartStore.db);'));
      const mut = require(beside);
      const mutOut = mut.pauseResume({ db: laneDb }, { workspaceRoot: hRoot, verb: 'pause', goal: HGOAL, countersFile });
      check('R4: red-proof — with `bind(heartStore.db)` restored, pause reports applied while the HOME never changes and the daemon\'s own store takes the write (COPY, discarded)',
        mutOut.applied === true
          && (lane.getGoalState(HGOAL) || {}).stored === 'paused'
          && (home.getGoalState(HGOAL) || {}).stored === 'running',
        JSON.stringify({ home: home.getGoalState(HGOAL), lane: lane.getGoalState(HGOAL) }));
      check('R4b: red-proof — and so `laneIsPaused` answers FALSE: the owner\'s pause is INERT to the lane gate (COPY, discarded)',
        laneIsPaused(hGoalDir, { db: laneDb }) === false);
    } finally {
      try { fs.rmSync(beside, { force: true }); } catch {}
    }
  }

  // R5 — the hoisted lane enumeration. With the logger closure restored to the loop head, a goal
  // with no `taskforce.csv` throws out of `seatsOf`'s own catch on the loop variable it has not
  // bound yet — AFTER row 4 has already flipped the goal to `running`. The owner is told the resume
  // was NOT applied and the store says it was.
  {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'state-store', 'heart', 'pause-resume.js'), 'utf8');
    // Anchor widened alongside `d-recovery-retry-scope`'s `targetSeat`-aware enumeration — same
    // reasoning as the SIG anchor above: the red-proof tracks the real hoisted line, whatever it
    // computes `seats` from, not a frozen RHS.
    const HOIST = '  const seats = targetSeat !== undefined ? [targetSeat] : seatsOf(goalDir, log);';
    const LOOP = '  for (const seat of seats) {';
    check('R0e: red-proof anchors — the enumeration is hoisted above the writes and the loop reads it',
      src.includes(HOIST) && src.includes(LOOP) && src.indexOf(HOIST) < src.indexOf(LOOP));
    const beside = path.join(__dirname, '..', '..', '..', 'state-store', 'heart', `pause-resume.loop-mutant-${process.pid}.js`);
    try {
      fs.writeFileSync(beside, src
        .replace(HOIST, '')
        .replace(LOOP, '  for (const seat of seatsOf(goalDir, (level, message, fields) => log(level, message, { seat, ...fields }))) {'));
      const mut = require(beside);
      home.writeGoalWord({ goal: HGOAL, stored: 'paused', who_stamped: 'owner', evidence_pointer: 'probe:R5' });
      let thrown = null;
      try {
        mut.pauseResume({ workspaceRoot: hRoot, verb: 'resume', goal: HGOAL, countersFile });
      } catch (err) { thrown = err; }
      check('R5: red-proof — with the closure restored, resume on the taskforce-less goal throws `Cannot access \'seat\' before initialization` (COPY, discarded)',
        !!thrown && thrown instanceof ReferenceError && /seat/.test(String(thrown.message)),
        thrown && thrown.message);
      check('R5b: red-proof — and the throw is HALF-APPLIED: the goal row already read `running` when the fault fired (COPY, discarded)',
        (home.getGoalState(HGOAL) || {}).stored === 'running', JSON.stringify(home.getGoalState(HGOAL)));
    } finally {
      try { fs.rmSync(beside, { force: true }); } catch {}
    }
  }

  try { db.close(); } catch {}
  try { fs.rmSync(root, { recursive: true, force: true }); } catch {}
  try { fs.rmSync(hRoot, { recursive: true, force: true }); } catch {}
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
