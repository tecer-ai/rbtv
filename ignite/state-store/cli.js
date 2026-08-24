'use strict';

const fs = require('node:fs');
const { openHeartStore, closeHeartStore } = require('../server/heart/heart-store');
const store = require('./index');

const OPS = new Set([
  'stampSeatDeclare',
  'stampSystem',
  'replaceSeatEnding',
  'writeGoalWord',
  'insertAsk',
  'postAsk',
  'reapAndRelaunch',
  'incrementRecoveryRelaunch',
  'setLeaderAttemptUsed',
  'fireNamedEvent',
  'getCurrentEnding',
  'getGoalState',
  'getAsk',
  'seatWaitingOnOwner',
  'goalWaitingOnOwner',
  'countOpenAsks',
  'isGoalPaused',
  'isGoalRunning',
  'isGoalFinished',
  'killClockPauses',
  'isLaunchable',
  'checkDoneOutputs',
]);

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

if (require.main === module) {
  const args = parseArgs(process.argv.slice(2));
  if (!args.db || !args.op) {
    process.stderr.write('usage: ending-cli --db PATH --op NAME --payload JSON|PATH|-\n');
    process.exit(2);
  }
  if (!OPS.has(args.op)) {
    process.stderr.write(`unknown op: ${args.op}\n`);
    process.exit(2);
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

module.exports = { OPS, parseArgs, runOp };
