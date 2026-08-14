'use strict';

// Self-check for ONE line of `seeding.js#mintRetryGrants`: the legacy-outcome translation.
//
// A seat whose last execution predates W2 (`f956f4c4`) still carries `done`/`blocked`/`failed` in
// `executions.csv` — words coord's `DAEMON_RETRY_FROM_OUTCOMES` refuses. The mint argv must carry
// the TRANSLATED process word. This drives the real `mintRetryGrants` against a real temp record
// and asserts on the argv the real code composes, with `execFileSync` intercepted so nothing spawns.
//
// Deliberately NOT a probe: it does not live in a `probes/` dir and is not named `probe-*`, so the
// suite's discovery (`deploy/probe-suite.js`) never sees it. Run it by hand:
//   node engine/seeding-outcome-translation.selftest.js

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// MUST be patched BEFORE `seeding.js` is required — it destructures `execFileSync` at load.
const child = require('node:child_process');
const calls = [];
child.execFileSync = (_cmd, argv) => {
  calls.push(argv);
  const err = new Error('stubbed — no python spawns in this self-check');
  err.stderr = 'refused [stub]';
  throw err;
};

const seeding = require('./seeding');

const goalFolder = fs.mkdtempSync(path.join(os.tmpdir(), 'seeding-xlate-'));
fs.writeFileSync(path.join(goalFolder, 'executions.csv'),
  'seat,session-id,lane,started,ended,outcome\n'
  + 'legacy-failed,s1,daemon,t,t,failed\n'      // legacy → must reach the mint as `crashed`
  + 'legacy-blocked,s2,daemon,t,t,blocked\n'    // legacy → CLEAN → skipped
  + 'legacy-done,s3,daemon,t,t,done\n'          // legacy → CLEAN → skipped
  + 'no-outcome,s4,daemon,t,t,\n'               // never recorded one → skipped, NOT `crashed`
  + 'garbage,s5,daemon,t,t,wat\n'               // unknown → passes through VERBATIM, refused once
  + 'already-new,s6,daemon,t,t,crashed\n');     // post-W2 word → unchanged

const empty = new Map();
seeding.mintRetryGrants(goalFolder,
  ['legacy-failed', 'legacy-blocked', 'legacy-done', 'no-outcome', 'garbage', 'already-new']
    .map((seat) => ({ seat })),
  { view: { finished: empty, notFinished: empty, blocked: empty, foreign: empty },
    granted: new Set(),
    logger: null });

const outcomeOf = (seat) => {
  const argv = calls.find((a) => a.includes(seat));
  return argv ? argv[argv.indexOf('--outcome') + 1] : null;
};

assert.strictEqual(outcomeOf('legacy-failed'), 'crashed', 'legacy `failed` must mint as `crashed`');
assert.strictEqual(outcomeOf('garbage'), 'wat', 'an unknown word must pass through verbatim');
assert.strictEqual(outcomeOf('already-new'), 'crashed', 'a post-W2 word must be unchanged');
for (const seat of ['legacy-blocked', 'legacy-done', 'no-outcome']) {
  assert.strictEqual(outcomeOf(seat), null, `${seat} must never reach the mint call`);
}
assert.strictEqual(calls.length, 3, `expected 3 mint calls, got ${calls.length}`);

fs.rmSync(goalFolder, { recursive: true, force: true });
console.log('seeding outcome-translation selftest OK (3 mints, 3 skips)');
