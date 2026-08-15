'use strict';

// Self-check for R3a: `seeding.js#mintRetryGrants` stops reissuing a STRUCTURALLY-unfixable retry,
// and never stops reissuing a transient one.
//
// Drives the real `mintRetryGrants` over 10 passes (the daemon's shape: same goal, same rows, every
// 10s) with `execFileSync` intercepted so nothing spawns. Two seats, two refusal layers:
//   `structural` → coord refuses at the `input` layer  → must stop after REFUSAL_STRIKE_LIMIT
//   `transient`  → coord refuses at the `environment` layer → must be asked on all 10 passes
//
// NON-VACUOUS BY MUTATION: delete the `>= REFUSAL_STRIKE_LIMIT` guard in `mintRetryGrants` and the
// structural assert goes RED (10 calls, not 3). Delete `'state'`/`'input'` from
// STRUCTURAL_REFUSAL_LAYERS and it goes RED the same way.
//
// Deliberately NOT a probe (no `probes/` dir, not `probe-*`), matching its sibling
// `seeding-outcome-translation.selftest.js`. Run it by hand:
//   node engine/seeding-retry-strike-limit.selftest.js

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// MUST be patched BEFORE `seeding.js` is required — it destructures `execFileSync` at load.
const child = require('node:child_process');
const calls = [];
child.execFileSync = (_cmd, argv) => {
  const seat = argv[argv.indexOf('seat-retry') + 1];
  calls.push(seat);
  const err = new Error('stubbed — no python spawns in this self-check');
  // The layer token is coord's own (`coord.py#REFUSAL_LAYERS`), in coord's own wire format.
  err.stderr = seat === 'structural'
    ? 'refused [coord input]: `wat` is not a retryable outcome'
    : 'refused [coord environment]: the goal room is busy, try again';
  throw err;
};

const seeding = require('./seeding');

const goalFolder = fs.mkdtempSync(path.join(os.tmpdir(), 'seeding-strike-'));
fs.writeFileSync(path.join(goalFolder, 'executions.csv'),
  'seat,session-id,lane,started,ended,outcome\n'
  + 'structural,s1,daemon,t,t,crashed\n'
  + 'transient,s2,daemon,t,t,crashed\n');

const empty = new Map();
const rows = [{ seat: 'structural' }, { seat: 'transient' }];
const PASSES = 10;
for (let i = 0; i < PASSES; i += 1) {
  seeding.mintRetryGrants(goalFolder, rows,
    { view: { finished: empty, notFinished: empty, blocked: empty, foreign: empty },
      granted: new Set(),
      logger: null });
}

const seen = (seat) => calls.filter((s) => s === seat).length;
const LIMIT = 3;  // spelled out, NOT read from seeding.js: a check that reads the constant under
                  // test moves with it and passes any change to it.

assert.strictEqual(seen('structural'), LIMIT,
  `a structurally-refused retry must stop after ${LIMIT} strikes, got ${seen('structural')} calls`);
assert.strictEqual(seen('transient'), PASSES,
  `a transiently-refused retry must keep retrying, got ${seen('transient')} of ${PASSES}`);

// A NEW execution row is a new input and retries from zero — the strike is on the ask, not a
// permanent blacklist of the seat.
fs.appendFileSync(path.join(goalFolder, 'executions.csv'), 'structural,s9,daemon,t,t,crashed\n');
seeding.mintRetryGrants(goalFolder, rows,
  { view: { finished: empty, notFinished: empty, blocked: empty, foreign: empty },
    granted: new Set(),
    logger: null });
assert.strictEqual(seen('structural'), LIMIT + 1,
  'a new execution row must reset the strike count for that seat');

fs.rmSync(goalFolder, { recursive: true, force: true });
console.log(`seeding retry strike-limit selftest OK `
  + `(structural struck out at ${LIMIT}, transient asked all ${PASSES}, new row reset)`);
