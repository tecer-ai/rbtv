'use strict';

// probe-start-execution — THE FOURTEENTH INTENT (owner ruling 2026-08-24, option (b),
// `redesign-implementation/decisions.md`): the approval thread's `approve`, crossing the daemon
// boundary and reaching the supervised Path-B birth.
//
// WHAT THIS PROBE IS FOR. `probe-chat-approval` proves the BRIDGE fires D12 exactly once and only
// from a `kind=approval` thread — but that fork is a fact of the bridge's own in-process map, so it
// is not evidence to the daemon. This probe measures the OTHER half: what the daemon does when a
// caller asks it to start an execution goal. The load-bearing leg is R1 — a caller naming a thread
// that carries no approval record must be REFUSED, and the birth must never be attempted. Without
// it, anything holding a bridge token could name any string and start an execution goal.
//
// In-process parse + dispatch + authz over a real (scratch) ending store; the Path-B birth itself
// is injected, so nothing here scaffolds a goal, spawns python, or touches a git tree.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-start-execution.out');
fs.writeFileSync(outPath, '');

const { createInternalApi, ENVELOPE_VERSION } = require('../dispatch');
const { parseRequest } = require('../../gateway/parse');
const { createAuthzPolicy } = require('../authz');
const { startExecution, APPROVE_PACKAGE } = require('../../../state-store/heart/start-execution');
const { openEndingStore } = require('../../../state-store');
const { bind } = require('../../../state-store');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const GOAL = 'plan-goal';
const OTHER_GOAL = 'other-plan-goal';
const SEAT = 'verify-seat';
const THREAD = '1724508123.123456';
const LOOSE_THREAD = '1724508999.999999';
const COMMIT = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678';
const OTHER_COMMIT = '9999999999999999999999999999999999999999';

function seedGoal(root, goal) {
  const dir = path.join(root, '.rbtv', 'goals', goal);
  fs.mkdirSync(path.join(dir, 'coordination', 'asks'), { recursive: true });
  return dir;
}

function writePackage(goalDir, fields) {
  const file = path.join(goalDir, APPROVE_PACKAGE);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify({ execution_goal: 'born-exec-goal', lane: 'default', bound_commit: COMMIT, ...fields }, null, 2));
  return file;
}

// An ask, opened and then RELEASED the way the §2.4 door releases one: `reapAndRelaunch` is what
// stamps `authorized_reply_at`, and reaching it is the whole proof that an authorized owner reply
// landed in this exact thread.
function openAndRelease(api, { askId, goal, seat, release }) {
  api.insertAsk({ ask_id: askId, goal, seat, label: 'work-content', evidence_pointer: `/tmp/${askId}.txt` });
  api.postAsk({ ask_id: askId, posted_at: '2026-08-24 10:00' });
  if (release) api.reapAndRelaunch({ ask_id: askId, authorized_reply_at: '2026-08-24 10:05' });
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('evidence-class: FIXTURE in-process parse+dispatch+authz over a scratch ending store; the Path-B birth is INJECTED (never spawned)');

  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'start-execution-probe-'));
  const goalDir = seedGoal(root, GOAL);
  seedGoal(root, OTHER_GOAL);
  writePackage(goalDir, {});

  const db = openEndingStore(path.join(root, '.rbtv', 'runtime', 'ignite', 'heart.db'));
  const store = bind(db);
  openAndRelease(store, { askId: THREAD, goal: GOAL, seat: SEAT, release: true });
  openAndRelease(store, { askId: LOOSE_THREAD, goal: GOAL, seat: SEAT, release: false });
  openAndRelease(store, { askId: '1724508777.777777', goal: OTHER_GOAL, seat: SEAT, release: true });

  const secret = crypto.randomBytes(32).toString('hex');
  const logs = [];
  const api = createInternalApi({
    heartStore: { db },
    spawnManager: {},
    secret,
    workspaceRoot: root,
    logger: (row) => logs.push(row),
  });

  const BRIDGE = { id: 'probe-bridge', kind: 'bridge' };
  const AGENT = { id: 'probe-agent', kind: 'agent' };
  const OWNER = { id: 'probe-owner', kind: 'owner' };
  const MASTER = { id: 'probe-agent', kind: 'agent', seat: 'goal-master' };

  async function call(sender, payload) {
    let parsed;
    try {
      parsed = parseRequest({ intent: 'start-execution', payload });
    } catch (err) {
      return { body: { ok: false, error: { code: err.code, message: err.message } }, gatewayRefused: true };
    }
    const res = await api.dispatch({
      v: ENVELOPE_VERSION,
      id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      auth: secret,
      sender,
      intent: 'start-execution',
      payload: parsed,
    });
    return { body: res, gatewayRefused: false };
  }

  // ── A. AUTHORIZATION IS BRIDGE-ONLY ─────────────────────────────────────────────────────────
  const policy = createAuthzPolicy();
  check('A1: authz — the chat bridge is allowed', policy.canStartExecution({ sender: BRIDGE }).allowed === true);
  check('A2: authz — an agent token is REFUSED (a seat approving its own plan is the failure the door exists to prevent)',
    policy.canStartExecution({ sender: AGENT }).allowed === false, policy.canStartExecution({ sender: AGENT }).reason);
  check('A3: authz — a proven goal-master is REFUSED', policy.canStartExecution({ sender: MASTER }).allowed === false);
  check('A4: authz — even the owner token is REFUSED: he approves in Slack, and the bridge carries it',
    policy.canStartExecution({ sender: OWNER }).allowed === false);

  let r = await call(AGENT, { goal: GOAL, thread: THREAD, commit: COMMIT });
  check('A5: wire — an agent token is UNAUTHORIZED_SENDER, and no birth is attempted',
    r.body.error && r.body.error.code === 'UNAUTHORIZED_SENDER',
    r.body.error && r.body.error.message);

  // ── B. SHAPE IS REFUSED, NEVER IGNORED ──────────────────────────────────────────────────────
  r = await call(BRIDGE, { goal: GOAL, thread: THREAD, commit: COMMIT, comments: 'ship it' });
  check('B1: an unknown payload key (`comments`) is REFUSED AT THE GATEWAY — never a silently ignored key',
    r.gatewayRefused === true && /comments/.test(r.body.error.message), r.body.error && r.body.error.message);

  r = await call(BRIDGE, { goal: GOAL, thread: THREAD, commit: 'main' });
  check('B2: a REF NAME as the bound commit is refused [T5-R5] — a moving binding is not the tree the owner read',
    r.gatewayRefused === true && /commit/.test(r.body.error.message), r.body.error && r.body.error.message);

  r = await call(BRIDGE, { goal: '../../etc', thread: THREAD, commit: COMMIT });
  check('B3: a goal name carrying path separators is refused — it becomes a PATH SEGMENT under .rbtv/goals/',
    r.gatewayRefused === true, r.body.error && r.body.error.message);

  r = await call(BRIDGE, { goal: GOAL, thread: THREAD });
  check('B4: a missing commit is refused — an approval that names no commit approves whatever the tree holds later',
    r.gatewayRefused === true, r.body.error && r.body.error.message);

  // ── R. THE APPROVAL-THREAD BINDING (the leg this probe exists for) ──────────────────────────
  r = await call(BRIDGE, { goal: GOAL, thread: LOOSE_THREAD.replace('999999', '000000'), commit: COMMIT });
  check('R1: a caller naming a thread THIS DAEMON NEVER RECORDED is refused `no-approval-record` — a bridge token alone cannot start an execution goal',
    r.body.ok === true && r.body.result.started === false && r.body.result.reason === 'no-approval-record',
    JSON.stringify(r.body.result));

  r = await call(BRIDGE, { goal: GOAL, thread: LOOSE_THREAD, commit: COMMIT });
  check('R2: an ask that was OPENED but never RELEASED by an authorized owner reply is refused `ask-not-released` — nobody approved in it',
    r.body.ok === true && r.body.result.started === false && r.body.result.reason === 'ask-not-released',
    JSON.stringify(r.body.result));

  r = await call(BRIDGE, { goal: OTHER_GOAL, thread: THREAD, commit: COMMIT });
  check('R3: an approval thread bound to ANOTHER goal cannot start this one — refused `ask-not-bound-here`',
    r.body.ok === true && r.body.result.started === false && r.body.result.reason === 'ask-not-bound-here',
    JSON.stringify(r.body.result));

  r = await call(BRIDGE, { goal: GOAL, thread: THREAD, commit: OTHER_COMMIT });
  check('R4: a commit that is NOT the one the plan is bound to is refused `commit-not-bound` [T5-R5]',
    r.body.ok === true && r.body.result.started === false && r.body.result.reason === 'commit-not-bound',
    JSON.stringify(r.body.result));

  const noPkgDir = seedGoal(root, 'no-package-goal');
  openAndRelease(store, { askId: '1724508555.555555', goal: 'no-package-goal', seat: SEAT, release: true });
  r = await call(BRIDGE, { goal: 'no-package-goal', thread: '1724508555.555555', commit: COMMIT });
  check('R5: a planning goal carrying no approve-package is refused `no-approve-package` — a birth with a guessed package is a birth of something nobody read',
    r.body.ok === true && r.body.result.started === false && r.body.result.reason === 'no-approve-package',
    `${noPkgDir}: ${JSON.stringify(r.body.result)}`);

  // ── S. THE SUPERVISED BIRTH, AND ITS FAILURE RECORD ─────────────────────────────────────────
  const seen = [];
  let ok = { ok: true };
  const run = (pkg) => { seen.push(pkg); return ok; };

  let direct = startExecution({ workspaceRoot: root, goal: GOAL, thread: THREAD, commit: COMMIT, runPathB: run });
  check('S1: a genuine approval thread + a matching bound commit RUNS the supervised Path-B birth exactly once',
    direct.started === true && seen.length === 1 && direct.execution_goal === 'born-exec-goal', JSON.stringify(direct));
  check('S2: the daemon STAMPS the package fields it owns — the planning goal that receives the D12 failure record, the goals root, and the approval thread as origin_id',
    seen[0].planning_goal === goalDir
    && seen[0].goals_root === path.join(root, '.rbtv', 'goals')
    && seen[0].origin_id === THREAD
    && seen[0].bound_commit === COMMIT,
    JSON.stringify({ planning_goal: seen[0].planning_goal, origin_id: seen[0].origin_id }));

  ok = { ok: false, record: { class: 'lock-collision', code: 'materialize-locked', reason: 'another pass holds the lock', subject: 'born-exec-goal' } };
  direct = startExecution({ workspaceRoot: root, goal: GOAL, thread: THREAD, commit: COMMIT, runPathB: run });
  check('S3: a supervised-materialize FAILURE comes back as data carrying the wrapper\'s six-field record — it is what the approval thread shows the owner [C-16]',
    direct.started === false && direct.reason === 'materialize-failed'
    && direct.record && direct.record.code === 'materialize-locked', JSON.stringify(direct));

  // A package copied here from another goal names a planning goal that is not this one.
  writePackage(goalDir, { planning_goal: '/somewhere/else' });
  direct = startExecution({ workspaceRoot: root, goal: GOAL, thread: THREAD, commit: COMMIT, runPathB: run });
  check('S4: a package naming a DIFFERENT planning goal is refused rather than silently overwritten — a stale copy must not read as this goal\'s plan',
    direct.started === false && direct.reason === 'package-not-bound-here', JSON.stringify(direct));
  writePackage(goalDir, {});

  // ── SPLIT. `refuseReason`'s `getAsk` MUST resolve the ENDING store from `workspaceRoot`, never
  // from a caller's `heartStore` ─────────────────────────────────────────────────────────────────
  //
  // Every call above hands `startExecution` no store at all — it takes none — but the WRITER that
  // opened the approval ask (`ask-record.js#openAsk`, via `record-owner-ask`) and the daemon's own
  // `heartStore` are, in production, TWO DIFFERENT FILES (the daemon's private lane store vs the
  // workspace's ending store). This section proves the approval check still finds the ask when the
  // process holds a private store that is neither the one the ask was opened into nor pre-seeded —
  // an empty file at a path that is never `endingStorePath(root3)`.
  const root3 = fs.mkdtempSync(path.join(os.tmpdir(), 'start-execution-split-probe-'));
  const goalDir3 = seedGoal(root3, GOAL);
  writePackage(goalDir3, {});
  const askRecord = require('../../../state-store/heart/ask-record');
  const { openEndingStoreFor } = require('../../../state-store');
  const THREAD_SPLIT = '1724509500.500500';
  const opened = askRecord.openAsk({
    workspaceRoot: root3, goal: GOAL, seat: SEAT, thread: THREAD_SPLIT, corpus: 'split-probe approval ask',
  });
  const reapedSplit = askRecord.reapAsk({ workspaceRoot: root3, goal: GOAL, seat: SEAT, thread: THREAD_SPLIT });
  check('SPLIT-1: SETUP — the approval ask was opened and released through the FIXED writer',
    opened.recorded && reapedSplit.recorded, JSON.stringify({ opened, reapedSplit }));

  const privateDb3 = openEndingStore(path.join(root3, 'private-lane-store', 'heart.db')); // NEVER the ending store
  check('SPLIT-2: the private store this process ALSO holds carries no such ask — the two files are genuinely apart',
    !bind(privateDb3).getAsk(THREAD_SPLIT) && Boolean(bind(openEndingStoreFor(root3)).getAsk(THREAD_SPLIT)));
  const seenSplit = [];
  const directSplit = startExecution({
    workspaceRoot: root3, goal: GOAL, thread: THREAD_SPLIT, commit: COMMIT,
    runPathB: (pkg) => { seenSplit.push(pkg); return { ok: true }; },
  });
  check('SPLIT-3: `startExecution` finds the approval and BIRTHS — its `getAsk` resolved the ending store, not the private one it never touched',
    directSplit.started === true && seenSplit.length === 1, JSON.stringify(directSplit));

  // RED CONTROL — a mutant restoring the pre-fix shape: `refuseReason`/`startExecution` take a
  // caller `heartStore` and check `bind(heartStore.db).getAsk(...)` instead of resolving
  // `openEndingStoreFor(workspaceRoot)`. Handed THIS process's private store (which never saw the
  // ask), it must refuse an approval that genuinely exists — the live defect, reproduced offline.
  const seSrcPath = path.join(__dirname, '..', '..', '..', 'state-store', 'heart', 'start-execution.js');
  const seSrc = fs.readFileSync(seSrcPath, 'utf8');
  const seOpenNeedle = 'function refuseReason({ workspaceRoot, goal, thread, commit }) {';
  const seGetNeedle = '    row = bind(openEndingStoreFor(workspaceRoot)).getAsk(String(thread));';
  const seStartNeedle = 'function startExecution({ workspaceRoot, goal, thread, commit, runPathB = null }) {\n  const refusal = refuseReason({ workspaceRoot, goal, thread, commit });';
  check('SPLIT-M1: red-proof — all three mutation needles are found in the fixed source',
    seSrc.includes(seOpenNeedle) && seSrc.includes(seGetNeedle) && seSrc.includes(seStartNeedle));
  if (seSrc.includes(seOpenNeedle) && seSrc.includes(seGetNeedle) && seSrc.includes(seStartNeedle)) {
    const seMutBeside = path.join(path.dirname(seSrcPath), 'start-execution.SPLIT-MUTANT.js');
    const seMutated = seSrc
      .replace(seOpenNeedle, 'function refuseReason(heartStore, { workspaceRoot, goal, thread, commit }) {')
      .replace(seGetNeedle, '    row = bind(heartStore.db).getAsk(String(thread));')
      .replace(seStartNeedle, 'function startExecution(heartStore, { workspaceRoot, goal, thread, commit, runPathB = null }) {\n  const refusal = refuseReason(heartStore, { workspaceRoot, goal, thread, commit });');
    fs.writeFileSync(seMutBeside, seMutated);
    try {
      const seMut = require(seMutBeside);
      const mutSplitOut = seMut.startExecution({ db: privateDb3 }, {
        workspaceRoot: root3, goal: GOAL, thread: THREAD_SPLIT, commit: COMMIT,
        runPathB: () => ({ ok: true }),
      });
      check('SPLIT-M2 RED — with the caller-store binding restored, a GENUINE approval is refused `no-approval-record` because the private store never saw it (the live defect, reproduced)',
        mutSplitOut.started === false && mutSplitOut.reason === 'no-approval-record',
        JSON.stringify(mutSplitOut));
    } finally {
      try { fs.rmSync(seMutBeside, { force: true }); } catch {}
    }
  }

  try { privateDb3.close(); } catch {}
  try { fs.rmSync(root3, { recursive: true, force: true }); } catch {}

  // ── M. RED-ARM BY MUTATION: delete the binding check, watch R1 turn into a birth ─────────────
  const mutDir = fs.mkdtempSync(path.join(os.tmpdir(), 'start-execution-mut-'));
  const srcPath = path.join(__dirname, '..', '..', '..', 'state-store', 'heart', 'start-execution.js');
  const src = fs.readFileSync(srcPath, 'utf8');
  const needle = "  if (!row) return { reason: 'no-approval-record', detail: `no ask on thread ${thread} — this is not an approval thread` };";
  check('M1: red-proof — the mutation needle (the no-approval-record refusal) is found in the executor', src.includes(needle));
  if (src.includes(needle)) {
    // The mutant is written BESIDE the original so its relative requires still resolve.
    const mutBeside = path.join(path.dirname(srcPath), 'start-execution.MUTANT.js');
    fs.writeFileSync(mutBeside, src.replace(needle, '  if (!row) return null;', 1));
    try {
      const mut = require(mutBeside);
      const mutSeen = [];
      const mutOut = mut.startExecution({
        workspaceRoot: root, goal: GOAL, thread: '1724500000.000000', commit: COMMIT,
        runPathB: (pkg) => { mutSeen.push(pkg); return { ok: true }; },
      });
      check('M2: red-proof — with the binding check mutated away, a thread carrying NO approval record BIRTHS an execution goal (COPY, discarded)',
        mutOut.started === true && mutSeen.length === 1,
        `started=${mutOut.started} births=${mutSeen.length}`);
    } finally {
      try { fs.rmSync(mutBeside, { force: true }); } catch {}
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
