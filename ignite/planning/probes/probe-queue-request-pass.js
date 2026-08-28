#!/usr/bin/env node
'use strict';

// probe-queue-request-pass — the pipeline-seat DIVERGENCE ALARM (leg M).
//
// WHAT THIS PROBE USED TO ASK, and no longer does: the Path A planning-mint door
// (spec-planning-door §1) fired once on an unminted `role: planning` goal, was a quiet
// no-op when minted, and minted nothing on a second cadence. That door and its per-tick
// pass were DELETED on 2026-08-28 — `role: planning` had no producer in any creation
// route, so the door admitted nothing and logged nothing in 592,458 journal lines, while
// the five seats it existed to mint are written AT BIRTH by the creation route. Its legs
// went with it; only their names are recorded here, so a reader of the .out file learns
// the coverage was removed deliberately and not lost: `S1 the daemon requires/CALLS the
// pass`, `S1 it runs BEFORE the lane watch`, the four `argv …` legs, `unminted planning
// goal: trigger fires once`, `unminted fire wrote the five pipeline seats`, the three
// `already-minted: …` legs, `second cadence mints nothing`, `second cadence is
// already-minted`, and `non-planning goal does not fire`.
//
// THE QUESTION THAT REMAINS: are the seat ids `pipeline-seats.json` carries the ids the
// mint actually writes? That json is read by `argv.py` (`PLANNING_SEATS`, `--seats-json`,
// and `path_a.py`'s uncast set) and mirrors ONE authority — the workflow manifest on disk,
// meta/planning/workflows/plan-console/plan-console.csv. Leg M derives its whole
// expectation from that checked-in manifest, never from a fixture, so it goes RED the
// moment the two diverge. Its last check greps this file's own source and fails if any leg
// hand-types a seat id at all: a hand-typed fixture can agree with a wrong json forever,
// which is exactly how the divergence at `8713ca14` stayed green across nineteen legs.

const fs = require('node:fs');
const path = require('node:path');

const PLANNING_SRC = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(PLANNING_SRC, '..', '..');
const QR_PATH = path.join(PLANNING_SRC, 'queue-request.js');
const DOOR_PATH = path.join(PLANNING_SRC, 'door.js');
const SERVER_INDEX = path.resolve(PLANNING_SRC, '..', 'runtime', 'index.js');
const OUT_PATH = path.join(__dirname, 'probe-queue-request-pass.out');

const qr = require('../queue-request');
const { PLANNING_SEATS, PLANNING_MODULE, PLANNING_MANIFEST_REL } = qr;

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => lines.push(s);
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}

function main() {
  {
    // Leg M — the two vocabularies must be ONE. `pipeline-seats.json` (what `argv.py`
    // uncasts and mints from, and what `pipelineMinted()` looks for) against the real
    // workflow manifest's `Seat/workflow` column (what the mint actually writes onto
    // taskforce.csv). Read from the checked-in file, never a fixture.
    const manifest = path.join(REPO_ROOT, PLANNING_MODULE, PLANNING_MANIFEST_REL);
    check('M the real plan-console manifest is on disk', fs.existsSync(manifest), manifest);
    let manifestSeats = [];
    try {
      manifestSeats = qr.planningManifestSeats(path.join(REPO_ROOT, PLANNING_MODULE));
    } catch (err) {
      check('M the manifest seat column is readable', false, err.message);
    }
    check('M pipeline-seats.json IS the manifest Seat/workflow column, in order',
      JSON.stringify(manifestSeats) === JSON.stringify(PLANNING_SEATS.slice()),
      `manifest [${manifestSeats.join(' ')}] vs json [${PLANNING_SEATS.join(' ')}]`);
    check('M a manifest-seated taskforce reads MINTED',
      qr.pipelineMinted(manifestSeats.map((seat) => ({ seat }))),
      'a goal seated from the real manifest must answer minted');
    const self = fs.readFileSync(__filename, 'utf8');
    const typed = manifestSeats.filter((seat) => self.includes(`'${seat}'`) || self.includes(`,${seat},`));
    check('M no leg hand-types a seat id (they all derive from PLANNING_SEATS)',
      typed.length === 0, typed.join(', '));
  }

  {
    // Leg D — the deleted mechanism is deleted, in all three files that carried it. The
    // door's admission key is the one that matters: `role: planning` is a contract term
    // with no producer, so any reader of it is a mechanism that cannot fire.
    const doorSrc = fs.readFileSync(DOOR_PATH, 'utf8');
    const qrSrc = fs.readFileSync(QR_PATH, 'utf8');
    const serverSrc = fs.readFileSync(SERVER_INDEX, 'utf8');
    const gone = ['planningMode', 'passesMinted', 'materializeArgv',
      'runPlanningMintPass', 'isPlanningGoal', 'planningMintArgv', 'runPathA',
      'taskforceRows', 'runQueueRequestPass', 'resolveCatalogRoot'];
    for (const name of gone) {
      check(`D ${name} is gone from door.js and queue-request.js`,
        !doorSrc.includes(`function ${name}`) && !doorSrc.includes(`${name}(`)
        && !qrSrc.includes(`function ${name}`) && !qrSrc.includes(`${name}(`));
    }
    check('D door.js reads no `role:` frontmatter key — the admission term had no producer',
      !/role:/.test(doorSrc.replace(/^\s*\/\/.*$/gm, '')),
      'the regex that admitted the pass is deleted, not merely unreferenced');
    check('D the daemon neither requires nor calls the pass',
      !serverSrc.includes("require('../planning/queue-request')")
      && !/queueRequestPass\(\);/.test(serverSrc),
      'no require of the module and no `queueRequestPass()` call site survive in the loop');
    check('D the lane watch still requires the unbuilt-seat repair from this module',
      typeof qr.buildUnbuiltSeats === 'function',
      'deleting the pass must not take `buildUnbuiltSeats` with it');
  }
}

try {
  main();
} catch (err) {
  say(`FAIL probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
}

const exitCode = failures.length ? 1 : 0;
say('');
say(exitCode
  ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
  : 'RESULT: PASS — the seat vocabulary pipeline-seats.json carries IS the real plan-console '
    + 'manifest column, and the per-tick planning-mint door that once read `role: planning` is '
    + 'gone from door.js, queue-request.js and the daemon loop.');
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, `${lines.join('\n')}\n`);
console.log(lines.join('\n'));
process.exit(exitCode);
