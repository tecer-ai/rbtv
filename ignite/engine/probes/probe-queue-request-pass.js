#!/usr/bin/env node
'use strict';

// probe-queue-request-pass — Path A planning-seat mint door (spec-planning-door §1).
//
// THE QUESTION: a planning goal exists and its five pipeline seats are not on
// taskforce.csv. Does the door fire once? Is an already-minted goal a quiet
// no-op? Does a second cadence mint nothing? The door is not a queue-request
// row and is not keyed by milestone-id.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const ENGINE_SRC = path.resolve(__dirname, '..');
const QR_PATH = path.join(ENGINE_SRC, 'queue-request.js');
const SERVER_INDEX = path.resolve(ENGINE_SRC, '..', 'server', 'index.js');
const OUT_PATH = path.join(__dirname, 'probe-queue-request-pass.out');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => lines.push(s);
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}

function makeWorkspace(root, { taskforce, role = 'planning', lane = 'daemon' }) {
  const ws = path.join(root, 'ws');
  const goal = path.join(ws, '.rbtv', 'goals', 'g1');
  fs.mkdirSync(path.join(goal, 'coordination'), { recursive: true });
  const sheetDir = path.join(ws, '.rbtv', 'config', 'modules', 'meta', 'planning', 'bindings');
  fs.mkdirSync(sheetDir, { recursive: true });
  fs.writeFileSync(path.join(ws, 'rbtv.json'), JSON.stringify({ rbtv_path: path.resolve(ENGINE_SRC, '..', '..') }));
  const seats = {};
  for (const name of ['understand', 'design', 'draft', 'review-finalize', 'verify']) {
    seats[name] = { harness: 'claude', model: 'claude-fable-5', effort: 'high' };
  }
  fs.writeFileSync(path.join(sheetDir, 'plan.json'),
    JSON.stringify({ defaults: { 'cwd-mode': 'seat-folder' }, seats }, null, 1));
  fs.writeFileSync(path.join(goal, 'execution-lane'), `${lane}\n`);
  const fm = role
    ? `---\nname: g1\ntype: one-shot\nrole: ${role}\n---\n`
    : '---\nname: g1\ntype: one-shot\n---\n';
  fs.writeFileSync(path.join(goal, 'goal.md'), fm);
  fs.writeFileSync(path.join(goal, 'taskforce.csv'), taskforce);
  return { ws, goal, goalsRoot: path.join(ws, '.rbtv', 'goals'), sheet: path.join(sheetDir, 'plan.json') };
}

const TF_HEADER = 'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n';
const TF_EMPTY = `${TF_HEADER}`;
const TF_MINTED = `${TF_HEADER}`
  + 'tf-1,understand,,claude,claude-fable-5,high,35,\n'
  + 'tf-1,design,understand,claude,claude-fable-5,high,35,\n'
  + 'tf-1,draft,design,claude,claude-fable-5,high,35,\n'
  + 'tf-1,review-finalize,draft,claude,claude-fable-5,high,35,\n'
  + 'tf-1,verify,review-finalize,claude,claude-fable-5,high,35,\n';

function logger(sink) { return (m) => sink.push(m); }

function stubMint({ goalFolder, seats }) {
  const tf = path.join(goalFolder, 'taskforce.csv');
  const rows = seats.map((seat) => `tf-1,${seat},,claude,claude-fable-5,high,35,`);
  fs.writeFileSync(tf, TF_HEADER + `${rows.join('\n')}\n`);
}

function main() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-qr-'));
  const {
    runQueueRequestPass, planningMintArgv, pipelineMinted, PLANNING_SEATS,
  } = require('../queue-request');

  {
    const src = fs.readFileSync(SERVER_INDEX, 'utf8');
    check('S1 the daemon requires the pass', src.includes("require('../engine/queue-request')"));
    const boot = src.indexOf('queueRequestPass();');
    const bootLane = src.indexOf('laneWatchPass();');
    check('S1 the daemon CALLS the pass at boot and inside the interval',
      (src.match(/queueRequestPass\(\);/g) || []).length >= 2,
      `${(src.match(/queueRequestPass\(\);/g) || []).length} call site(s)`);
    check('S1 it runs BEFORE the lane watch', boot > 0 && bootLane > boot);
  }

  {
    const argv = planningMintArgv({ goalFolder: '/g', catalogRoot: '/c', sheet: '/s.json' });
    check('argv aims --package at the existing goal', argv.includes('--package') && argv.includes('/g'));
    check('argv is one --workflow, never --nested', argv.includes('--workflow') && !argv.includes('--nested'));
    check('argv never passes --milestone-id', !argv.includes('--milestone-id'));
    check('argv never branches full/collapsed', !argv.includes('full') && !argv.includes('collapsed'));
  }

  {
    const fx = makeWorkspace(path.join(tmp, 'fire'), { taskforce: TF_EMPTY });
    const log = [];
    let mintCalls = 0;
    const mint = (args) => { mintCalls += 1; stubMint(args); };
    const r1 = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger(log), mint });
    check('unminted planning goal: trigger fires once',
      r1.seeded.length === 1 && mintCalls === 1 && r1.seeded[0].goal === 'g1',
      `seeded ${r1.seeded.length} mintCalls ${mintCalls}`);
    check('unminted fire wrote the five pipeline seats',
      pipelineMinted(PLANNING_SEATS.map((seat) => ({ seat })))
      && fs.readFileSync(path.join(fx.goal, 'taskforce.csv'), 'utf8').includes('review-finalize'));
  }

  {
    const fx = makeWorkspace(path.join(tmp, 'minted'), { taskforce: TF_MINTED });
    const log = [];
    let mintCalls = 0;
    const r1 = runQueueRequestPass({
      goalsRoot: fx.goalsRoot, logger: logger(log), mint: () => { mintCalls += 1; },
    });
    check('already-minted: quiet no-op (nothing minted)',
      r1.seeded.length === 0 && mintCalls === 0,
      `seeded ${r1.seeded.length} mintCalls ${mintCalls}`);
    check('already-minted: skipped as already-minted',
      r1.skipped.some((s) => s.reason === 'already-minted'),
      r1.skipped.map((s) => s.reason).join(', '));
    const mintedLogs = log.filter((m) => /already minted/.test(m.message || ''));
    check('already-minted: the skip is DEBUG, not a warning',
      mintedLogs.length > 0 && mintedLogs.every((m) => m.level === 'debug'),
      mintedLogs.map((m) => m.level).join(',') || 'no log');
  }

  {
    const fx = makeWorkspace(path.join(tmp, 'second'), { taskforce: TF_EMPTY });
    let mintCalls = 0;
    const mint = (args) => { mintCalls += 1; stubMint(args); };
    const r1 = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]), mint });
    const r2 = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]), mint });
    check('second cadence mints nothing',
      r1.seeded.length === 1 && r2.seeded.length === 0 && mintCalls === 1,
      `pass1 ${r1.seeded.length} pass2 ${r2.seeded.length} mintCalls ${mintCalls}`);
    check('second cadence is already-minted',
      r2.skipped.some((s) => s.reason === 'already-minted'));
  }

  {
    const fx = makeWorkspace(path.join(tmp, 'exec'), { taskforce: TF_EMPTY, role: '' });
    let mintCalls = 0;
    const r1 = runQueueRequestPass({
      goalsRoot: fx.goalsRoot, logger: logger([]), mint: () => { mintCalls += 1; },
    });
    check('non-planning goal does not fire',
      r1.seeded.length === 0 && mintCalls === 0
      && r1.skipped.some((s) => s.reason === 'not-planning-goal'),
      r1.skipped.map((s) => s.reason).join(', '));
  }

  {
    const src = fs.readFileSync(QR_PATH, 'utf8');
    const dead = ['planningMode', 'passesMinted', 'materializeArgv'];
    for (const name of dead) {
      check(`${name} is gone`,
        !src.includes(`function ${name}`) && !src.includes(`${name}(`));
    }
  }

  fs.rmSync(tmp, { recursive: true, force: true });
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
  : 'RESULT: PASS — Path A door is goal-wide: fires once on an unminted planning goal, '
    + 'quiet no-op when minted, second cadence mints nothing.');
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, `${lines.join('\n')}\n`);
console.log(lines.join('\n'));
process.exit(exitCode);
