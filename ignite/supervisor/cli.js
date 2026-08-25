'use strict';

// -- THE KIT DOOR - one JSON surface over the registry, for the callers that are not node --------
//
// The reap and check-in halves of this module are reached from team-kit's python (`checkout.py`,
// `attest.py`), and the ending store already settled the shape a python caller talks through:
// `--op NAME --payload JSON|PATH|-`, one JSON document on stdout. This is the same door for the
// same reason - a second spelling of "which seats are supervised" is how two answers to one
// question get born, and this module exists precisely to have ONE answer [T4-R8].
//
// `--registry PATH` is optional; without it the module's own default file is used.
//
// `--db PATH` is required by exactly the two ops that need an ENDING, and by no other: `stampDeath`
// (which writes one) and `awaitingReap` (which asks whether one exists). The store is opened HERE
// and injected, so `death-stamp.js` keeps no ending-store handle - the same posture `awaitingReap`
// takes with `hasEnding`. A python caller therefore reaches the death stamp through ONE door with
// ONE spelling, instead of stamping the store itself and hoping the two agree.

const fs = require('node:fs');
const registry = require('./registry');
const { readopt } = require('./readopt');
const { stampDeath, confirmAndReap } = require('./death-stamp');
const { seedRecoveryConfig, loadRecoveryConfig } = require('./recovery-config');
const { recordSignal } = require('./progress');

const OPS = new Set([
  'loadRegistry',
  'recordSpawn',
  'recordCheckIn',
  'dropRow',
  'isRowAlive',
  'readopt',
  'stampDeath',
  'confirmAndReap',
  'awaitingReap',
  // The recovery half, for the python callers that are not node: the installer / first-bootstrap
  // seeding step, the read api sibling recovery work consumes, and the progress collector a
  // team-kit writer fires. Same door, same spelling, for the same reason as the rows above.
  'seedRecoveryConfig',
  'loadRecoveryConfig',
  'recordSignal',
  'lastProgressAt',
]);

// The ops that cannot answer without the ending store.
const STORE_OPS = new Set(['stampDeath', 'confirmAndReap', 'awaitingReap']);

function parseArgs(argv) {
  const out = { registry: null, op: null, payload: null, db: null };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    const val = argv[i + 1];
    if (key === '--registry') { out.registry = val; i += 1; }
    else if (key === '--op') { out.op = val; i += 1; }
    else if (key === '--payload') { out.payload = val; i += 1; }
    else if (key === '--db') { out.db = val; i += 1; }
  }
  return out;
}

// Required LAZILY, inside the branch that needs it, for one reason: `loadRegistry` and the boot
// pass must answer on a machine where the ending store cannot be opened at all. A top-level
// require would make the liveness half of this module hostage to the endings half.
function openStore(dbPath) {
  // eslint-disable-next-line global-require
  const { openHeartStore, closeHeartStore } = require('../state-store/heart/heart-store');
  // eslint-disable-next-line global-require
  const endingStore = require('../state-store');
  const heart = openHeartStore({ dbPath });
  const api = endingStore.bind(heart.db);
  return { api, close: () => { heart.close(); closeHeartStore(); } };
}

function loadPayload(spec) {
  if (!spec || spec === '-') return {};
  if (spec.startsWith('{') || spec.startsWith('[')) return JSON.parse(spec);
  return JSON.parse(fs.readFileSync(spec, 'utf8'));
}

function runOp(op, payload, registryFile, store) {
  if (op === 'loadRegistry') return registry.loadRegistry(registryFile);
  if (op === 'recordSpawn') return registry.recordSpawn(payload, registryFile);
  if (op === 'recordCheckIn') return registry.recordCheckIn(payload, registryFile);
  if (op === 'dropRow') return registry.dropRow(payload, registryFile);
  if (op === 'isRowAlive') return registry.isRowAlive(payload);
  if (op === 'readopt') return readopt(registryFile);
  if (op === 'stampDeath') return stampDeath(payload, { store, registryFile });
  if (op === 'confirmAndReap') return confirmAndReap(payload, { registryFile });
  if (op === 'awaitingReap') {
    // The reap debt: a row still present whose sitting ALREADY carries an ending. The ending
    // lookup is the injected `hasEnding` the registry asks for, spelled once, here.
    return registry.awaitingReap(
      (row) => Boolean(store.getCurrentEnding({ goal: row.goal || payload.goal || '', seat: row.seat })),
      registryFile,
    );
  }
  if (op === 'seedRecoveryConfig') return seedRecoveryConfig(payload.workspace);
  if (op === 'loadRecoveryConfig') return loadRecoveryConfig(payload);
  if (op === 'recordSignal') return recordSignal(payload, { registryFile });
  if (op === 'lastProgressAt') return registry.lastProgressAt(payload, registryFile);
  throw new Error(`unknown op: ${op}`);
}

if (require.main === module) {
  const args = parseArgs(process.argv.slice(2));
  if (!args.op) {
    process.stderr.write('usage: supervisor-cli --op NAME [--registry PATH] [--payload JSON|PATH|-]\n');
    process.exit(2);
  }
  if (!OPS.has(args.op)) {
    process.stderr.write(`unknown op: ${args.op}\n`);
    process.exit(2);
  }
  if (STORE_OPS.has(args.op) && args.op !== 'confirmAndReap' && !args.db) {
    process.stderr.write(`--db PATH is required for op ${args.op}\n`);
    process.exit(2);
  }
  let opened = null;
  try {
    if (STORE_OPS.has(args.op) && args.db) opened = openStore(args.db);
    const result = runOp(args.op, loadPayload(args.payload), args.registry, opened && opened.api);
    process.stdout.write(`${JSON.stringify(result === undefined ? null : result)}\n`);
  } catch (err) {
    process.stderr.write(`${err && err.message ? err.message : String(err)}\n`);
    process.exit(1);
  } finally {
    if (opened) opened.close();
  }
}

module.exports = { OPS, STORE_OPS, parseArgs, runOp, openStore };
