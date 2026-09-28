'use strict';

const fs = require('node:fs');
const { openHeartStore, closeHeartStore } = require('./heart/heart-store');
const store = require('./index');

const OPS = new Set([
  'stampSeatDeclare',
  'stampSystem',
  'replaceSeatEnding',
  'writeGoalWord',
  'insertAsk',
  'postAsk',
  'reapAndRelaunch',
  'supersedeAsk',
  'setAskShape',
  'incrementRecoveryRelaunch',
  'setLeaderAttemptUsed',
  'fireNamedEvent',
  'holdSeat',
  'releaseSeat',
  'getSeatHold',
  'abandonSeat',
  'getSeatAbandonment',
  'getCurrentEnding',
  'getGoalState',
  'getAsk',
  'seatWaitingOnOwner',
  'seatHeld',
  'listSeatHolds',
  'listOpenAsks',
  'listAllOpenAsks',
  'goalWaitingOnOwner',
  'countOpenAsks',
  'isGoalPaused',
  'isGoalRunning',
  'isGoalFinished',
  'killClockPauses',
  'isLaunchable',
  'checkDoneOutputs',
]);

// -- THE WORKSPACE-ROOTED OPS - the ones that take NO `--db` --------------------------------------
//
// Every op in `OPS` above is a method ON a bound store, so the caller names the file with `--db`
// and this CLI binds it. `pauseResume` is not one of those and must not be made to look like one:
// it RESOLVES its own store from `workspaceRoot` (`openEndingStoreFor`), and that absence of a
// caller-supplied handle IS the fix 919be192 landed - the executor used to take the caller's
// `heartStore` and a Slack `pause` wrote the daemon's private lane store while the lane gate read
// the workspace home, so the owner's pause was inert. Handing this op a `--db` would re-open that
// exact defect through a new door. A rooted op therefore never reaches `openHeartStore`.
const ROOTED_OPS = new Set(['pauseResume']);

function parseArgs(argv) {
  const out = { db: null, op: null, payload: null };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    const val = argv[i + 1];
    if (key === '--db') { out.db = val; i += 1; }
    else if (key === '--op') { out.op = val; i += 1; }
    else if (key === '--payload') { out.payload = val; i += 1; }
  }
  return out;
}

function loadPayload(spec) {
  if (!spec || spec === '-') return JSON.parse(fs.readFileSync(0, 'utf8') || '{}');
  if (spec.startsWith('{') || spec.startsWith('[')) return JSON.parse(spec);
  return JSON.parse(fs.readFileSync(spec, 'utf8'));
}

function runOp(api, op, payload) {
  if (op === 'getGoalState' || op === 'countOpenAsks' || op === 'isGoalPaused'
      || op === 'isGoalRunning' || op === 'isGoalFinished') {
    return api[op](payload.goal);
  }
  if (op === 'getAsk') return api[op](payload.ask_id);
  if (op === 'isLaunchable' || op === 'checkDoneOutputs') return store[op](payload);
  return api[op](payload);
}

// The rooted ops' one runner. The executor's own `logger` port is drained into the result as
// `logs`, because the caller here is a CONSOLE VERB whose whole job is to SAY what it did: a
// counter ledger that refused becomes a `warn` inside the executor and would otherwise leave the
// operator reading a silent, empty `actions` list as "there was nothing to re-arm".
//
// ⚠ NOTHING ELSE IS PASSED THROUGH, and the executor's signature is deliberately not widened.
// `probe-pause-resume.js`'s R0d/R4 anchor the exact `function pauseResume({...})` parameter list as
// the red-proof for 919be192 (a caller-supplied store handle wrote the wrong file), so ANY added
// parameter silently kills that mutation. The known cost is one string: a console resume that
// flips the goal word stamps `evidence_pointer` as `owner resume in chat`, naming a door the owner
// did not use. Correcting it means moving that anchor in the same change.
function runRootedOp(op, payload) {
  // LAZY, for `pause-resume.js`'s own stated reason: it pulls `chat/bus-ferry` in at module level,
  // and this CLI is on the kit's hot path (`coord/ending_store.py` spawns it once per checkout
  // stamp). A require nobody on the `--db` path uses is a cost every one of those pays.
  const { pauseResume } = require('./heart/pause-resume');
  const logs = [];
  const out = pauseResume({
    workspaceRoot: payload.workspaceRoot,
    verb: payload.verb,
    goal: payload.goal,
    countersFile: payload.countersFile || undefined,
    logger: (line) => logs.push(line),
  });
  return { ...out, logs };
}

if (require.main === module) {
  const args = parseArgs(process.argv.slice(2));
  const rooted = ROOTED_OPS.has(args.op);
  if (!args.op || (!args.db && !rooted)) {
    process.stderr.write('usage: ending-cli --db PATH --op NAME --payload JSON|PATH|-\n');
    process.stderr.write(`       (rooted ops take no --db: ${[...ROOTED_OPS].join(', ')})\n`);
    process.exit(2);
  }
  if (!OPS.has(args.op) && !rooted) {
    process.stderr.write(`unknown op: ${args.op}\n`);
    process.exit(2);
  }
  if (rooted) {
    try {
      const result = runRootedOp(args.op, loadPayload(args.payload));
      process.stdout.write(`${JSON.stringify(result)}\n`);
    } catch (err) {
      process.stderr.write(`${err && err.message ? err.message : String(err)}\n`);
      process.exitCode = 1;
    } finally {
      store.closeEndingStores();
    }
    return;
  }
  const heart = openHeartStore({ dbPath: args.db });
  try {
    const api = store.bind(heart.db);
    const result = runOp(api, args.op, loadPayload(args.payload));
    process.stdout.write(`${JSON.stringify(result == null ? null : result)}\n`);
  } catch (err) {
    process.stderr.write(`${err && err.message ? err.message : String(err)}\n`);
    process.exit(err && err.code ? 1 : 1);
  } finally {
    heart.close();
    closeHeartStore();
  }
}

module.exports = {
  OPS, ROOTED_OPS, parseArgs, runOp, runRootedOp,
};
