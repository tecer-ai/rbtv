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

const fs = require('node:fs');
const registry = require('./registry');
const { readopt } = require('./readopt');

const OPS = new Set([
  'loadRegistry',
  'recordSpawn',
  'recordCheckIn',
  'dropRow',
  'isRowAlive',
  'readopt',
]);

function parseArgs(argv) {
  const out = { registry: null, op: null, payload: null };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    const val = argv[i + 1];
    if (key === '--registry') { out.registry = val; i += 1; }
    else if (key === '--op') { out.op = val; i += 1; }
    else if (key === '--payload') { out.payload = val; i += 1; }
  }
  return out;
}

function loadPayload(spec) {
  if (!spec || spec === '-') return {};
  if (spec.startsWith('{') || spec.startsWith('[')) return JSON.parse(spec);
  return JSON.parse(fs.readFileSync(spec, 'utf8'));
}

function runOp(op, payload, registryFile) {
  if (op === 'loadRegistry') return registry.loadRegistry(registryFile);
  if (op === 'recordSpawn') return registry.recordSpawn(payload, registryFile);
  if (op === 'recordCheckIn') return registry.recordCheckIn(payload, registryFile);
  if (op === 'dropRow') return registry.dropRow(payload, registryFile);
  if (op === 'isRowAlive') return registry.isRowAlive(payload);
  if (op === 'readopt') return readopt(registryFile);
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
  try {
    const result = runOp(args.op, loadPayload(args.payload), args.registry);
    process.stdout.write(`${JSON.stringify(result === undefined ? null : result)}\n`);
  } catch (err) {
    process.stderr.write(`${err && err.message ? err.message : String(err)}\n`);
    process.exit(1);
  }
}

module.exports = { OPS, parseArgs, runOp };
