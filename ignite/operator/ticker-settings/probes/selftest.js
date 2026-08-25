'use strict';

// `rbtv ignite ticker selftest` — runs this capability's probes as one act and REPORTS THE TALLY.
//
// It routes through `ignite/deploy/probe-suite.js --only`, never `node probe-x.js`, for two
// reasons that are the runner's whole point: the runner keeps preserve mode, so running a probe
// stops dirtying its tracked capture (`G-163`); and it establishes a DENOMINATOR before any work,
// so "every probe passed" and "the runner never executed them" cannot look alike (`G-141`).
//
// Exit codes are the runner's, deliberately unmapped: 0 green · 1 a probe FAILED · 2 the run was
// INCOMPLETE. Collapsing 2 into 1 would hide the distinction the runner exists to draw.

const path = require('node:path');
const { spawnSync } = require('node:child_process');

const SUITE = path.resolve(__dirname, '..', '..', '..', 'deploy', 'probe-suite.js');
const PROBES = ['probe-ticker-settings', 'probe-ticker-cadence-flow'];

function run() {
  const args = [SUITE];
  for (const p of PROBES) args.push('--only', p);
  process.stdout.write(
    `running ${PROBES.length} probe(s) through the suite runner (preserve mode, counted):\n` +
    `  ${PROBES.join('\n  ')}\n\n` +
    `note: the cadence-flow probe starts a THROWAWAY daemon on a THROWAWAY systemd unit and\n` +
    `takes ~40s. The live rbtv-ignite.service is never touched.\n\n`
  );
  const r = spawnSync(process.execPath, args, { stdio: 'inherit' });
  if (r.error) {
    process.stderr.write(`could not run the probe suite at ${SUITE}: ${r.error.message}\n`);
    return 2;
  }
  return r.status === null ? 2 : r.status;
}

module.exports = { run, PROBES };
