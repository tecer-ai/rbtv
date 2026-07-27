'use strict';

// Task 7.11 — WALL PROBES for the seat cage. Pre-registered bars P8(a-e) and the P9 write legs.
//
// THE EVIDENCE RULE THIS FILE OBEYS (design §6, D51): every wall claim is proven ON DISK, from
// OUTSIDE the cage, by the target file being unchanged or absent. An in-cage error message proves
// only that something said no — it does not prove the kernel refused, and a probe that accepts
// the error message as evidence would pass just as happily against a wall made of comments.
//
// So each leg runs the write INSIDE bwrap, ignores whatever the shell reports, and then compares
// the target's bytes from the parent. The in-cage exit status is recorded for information and is
// never the pass condition.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeSeatCage, assertGroundTruthUnwritable, specToBwrapFlags } = require('../cage');
const { buildBwrapArgv } = require('../bwrap');

// A fixture goal tree with the real shape: two seats (so peer-absence is testable), a run-level
// session log, a fake repo + worktree, and a file outside the tree entirely.
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'g4-cage-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'testgoal');
  const runDir = path.join(goalDir, 'runs', 'run-1');
  const seatDir = path.join(runDir, 'seats', 'mine');
  const peerDir = path.join(runDir, 'seats', 'peer');
  const coordDir = path.join(runDir, 'coordination');
  for (const d of [seatDir, peerDir, coordDir]) fs.mkdirSync(d, { recursive: true });

  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,pid,pid-starttime\nmine,1,1\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: mine\n---\nbriefing\n');
  fs.writeFileSync(path.join(peerDir, 'PEER-SECRET.md'), 'peer briefing nobody may read\n');
  fs.writeFileSync(path.join(goalDir, 'decisions.md'), 'rulings\n');
  fs.writeFileSync(path.join(coordDir, 'messages.md'), 'log\n');

  // A "main repo working tree" OUTSIDE the goal tree — the thing a seat must not be able to edit.
  const repo = path.join(ws, 'repo');
  fs.mkdirSync(repo, { recursive: true });
  fs.writeFileSync(path.join(repo, 'source.js'), 'ORIGINAL\n');

  // Another seat's worktree.
  const wtRoot = path.join(ws, '.rbtv', 'worktrees');
  const mineWt = path.join(wtRoot, `repo--testgoal--mine`);
  const peerWt = path.join(wtRoot, `repo--testgoal--peer`);
  fs.mkdirSync(mineWt, { recursive: true });
  fs.mkdirSync(peerWt, { recursive: true });
  fs.writeFileSync(path.join(peerWt, 'peer-work.txt'), 'PEER WORK\n');

  return { root, ws, goalDir, runDir, seatDir, peerDir, coordDir, repo, mineWt, peerWt };
}

const TEMPLATE = [
  'ro-bind:{goalDir}',
  'tmpfs:{goalDir}/runs',
  'ro-bind:{runDir}',
  'tmpfs:{runDir}/seats',
  'bind:{seatDir}',
  'ro-bind:{seatDir}/seat.md',
  'bind:{runDir}/coordination',
  'bind:{grant:worktree}',
];

function cageFor(f) {
  const spec = composeSeatCage({
    seatBinds: TEMPLATE,
    values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir, runDir: f.runDir },
    grants: [{ worktree: f.mineWt, worktreeName: 'repo--testgoal--mine' }],
  });
  assertGroundTruthUnwritable(spec, path.join(f.runDir, 'sessions.csv'));
  return specToBwrapFlags(spec);
}

// Run a shell line INSIDE the cage. Returns the in-cage exit status for information only.
function inCage(f, script) {
  const argv = buildBwrapArgv({
    argv: ['bash', '-c', script],
    workdir: f.seatDir,
    harness: null,
    seatBinds: cageFor(f),
  });
  try {
    execFileSync(argv[0], argv.slice(1), { stdio: ['ignore', 'pipe', 'pipe'], timeout: 30000 });
    return { exit: 0 };
  } catch (err) {
    return { exit: err.status === undefined ? -1 : err.status, stderr: (err.stderr || '').toString().trim() };
  }
}

function bytes(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch (err) { return `<<ABSENT:${err.code}>>`; }
}

capture('probe-seat-cage', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    // ── P8c — THE STRUCTURAL INVARIANT. The identity gate's ground truth must be unwritable.
    const groundTruth = path.join(f.runDir, 'sessions.csv');
    const before = bytes(groundTruth);
    const r8c = inCage(f, `echo "imposter,999,999" >> ${groundTruth}`);
    const after = bytes(groundTruth);
    leg('P8c', 'run-level sessions.csv is NOT writable from inside the cage',
      after === before,
      `on-disk bytes ${after === before ? 'UNCHANGED' : 'CHANGED — WALL BREACHED'} (in-cage exit ${r8c.exit}, not the evidence)`);

    // P8c(ii) — and the composer REFUSES to build a cage that would make it writable. This is the
    // half that generalises: the leg above proves THIS cage sound, the assertion proves all of them.
    let refused = false; let code = null;
    try {
      const bad = composeSeatCage({
        seatBinds: [...TEMPLATE, 'bind:{runDir}'],
        values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir, runDir: f.runDir },
        grants: [],
      });
      assertGroundTruthUnwritable(bad, groundTruth);
    } catch (err) { refused = true; code = err.code; }
    leg('P8c-ii', 'a template that WOULD expose the ground truth is refused at compose time',
      refused && code === 'E_CAGE_GROUND_TRUTH',
      `composer ${refused ? `REFUSED with ${code}` : 'ACCEPTED IT — the invariant is unenforced'}`);

    // ── P8a — a main-repo working file, outside the goal tree entirely.
    const src = path.join(f.repo, 'source.js');
    const srcBefore = bytes(src);
    const r8a = inCage(f, `echo TAMPERED > ${src}`);
    leg('P8a', 'main repo working file unchanged (the tree is never bound)',
      bytes(src) === srcBefore && srcBefore === 'ORIGINAL\n',
      `content still ${JSON.stringify(bytes(src))} (in-cage exit ${r8a.exit})`);

    // ── P8b — another seat's worktree.
    const peerWork = path.join(f.peerWt, 'peer-work.txt');
    const peerBefore = bytes(peerWork);
    const r8b = inCage(f, `echo TAMPERED > ${peerWork}`);
    leg('P8b', "another seat's worktree unchanged",
      bytes(peerWork) === peerBefore,
      `content still ${JSON.stringify(bytes(peerWork))} (in-cage exit ${r8b.exit})`);

    // ── P8d — the seat's OWN seat.md (the ro carve-IN inside the RW seat folder).
    const seatMd = path.join(f.seatDir, 'seat.md');
    const mdBefore = bytes(seatMd);
    const r8d = inCage(f, `echo "seat: someone-else" > ${seatMd}`);
    leg('P8d', "the seat's own seat.md unchanged (ro carve-in inside a RW folder)",
      bytes(seatMd) === mdBefore,
      `descriptor still ${JSON.stringify(bytes(seatMd).slice(0, 24))}… (in-cage exit ${r8d.exit})`);

    // ── P8e — READ of a peer seat folder. Absence, not permission: the tmpfs erases the subtree.
    const readOut = (() => {
      const argv = buildBwrapArgv({
        argv: ['bash', '-c', `cat ${path.join(f.peerDir, 'PEER-SECRET.md')} 2>&1; ls ${path.join(f.runDir, 'seats')} 2>&1`],
        workdir: f.seatDir, harness: null, seatBinds: cageFor(f),
      });
      try { return execFileSync(argv[0], argv.slice(1), { encoding: 'utf8', timeout: 30000 }); }
      catch (err) { return ((err.stdout || '') + (err.stderr || '')).toString(); }
    })();
    const leaked = readOut.includes('peer briefing');
    const peerListed = /(^|\s)peer(\s|$)/m.test(readOut);
    leg('P8e', 'peer seat folder is not merely unreadable — it is ABSENT',
      !leaked && !peerListed,
      `in-cage read yielded ${JSON.stringify(readOut.trim().slice(0, 120))}; seats/ ${peerListed ? 'STILL LISTS peer' : 'does not list peer'}`);

    // ── P9 write legs — the LEGITIMATE flow must actually work. A cage that refuses everything
    // passes every wall bar and is useless; these are the bars that stop over-tightening.
    const artifact = path.join(f.seatDir, 'sessions', 'sess-1', 'out.txt');
    inCage(f, `mkdir -p ${path.dirname(artifact)} && echo ARTIFACT > ${artifact}`);
    leg('P9a', 'session artifact lands in sessions/{session-id}/ under the seat folder',
      bytes(artifact) === 'ARTIFACT\n', `artifact reads ${JSON.stringify(bytes(artifact))}`);

    const wtFile = path.join(f.mineWt, 'work.txt');
    inCage(f, `echo WORK > ${wtFile}`);
    leg('P9b', "the seat's OWN worktree is writable", bytes(wtFile) === 'WORK\n',
      `worktree file reads ${JSON.stringify(bytes(wtFile))}`);

    const coordFile = path.join(f.coordDir, 'messages.md');
    inCage(f, `echo "a message" >> ${coordFile}`);
    leg('P9c', 'the S1 INTERIM coordination opening is writable (retires at 7.57)',
      bytes(coordFile).includes('a message'),
      `coordination file grew: ${JSON.stringify(bytes(coordFile).trim())}`);

    const goalRead = (() => {
      const argv = buildBwrapArgv({
        argv: ['bash', '-c', `cat ${path.join(f.goalDir, 'decisions.md')}`],
        workdir: f.seatDir, harness: null, seatBinds: cageFor(f),
      });
      try { return execFileSync(argv[0], argv.slice(1), { encoding: 'utf8', timeout: 30000 }).trim(); }
      catch { return '<<unreadable>>'; }
    })();
    leg('P9d', "the goal's decisions.md stays READABLE (a seat must still know its rulings)",
      goalRead === 'rulings', `in-cage read returned ${JSON.stringify(goalRead)}`);

    // ── The bwrap wiring itself: seatBinds must REPLACE the flat workdir opening, not join it.
    const argv = buildBwrapArgv({ argv: ['bash', '-c', 'true'], workdir: f.seatDir, harness: null, seatBinds: cageFor(f) });
    const joined = argv.join(' ');
    const workdirBindCount = argv.filter((a, i) => a === '--bind' && argv[i + 1] === f.seatDir).length;
    leg('P-wiring', 'the seat stack replaces the flat workdir bind (exactly one RW opening of the seat dir)',
      workdirBindCount === 1 && joined.indexOf(`--ro-bind ${f.goalDir} `) < joined.indexOf(`--bind ${f.seatDir} `),
      `seatDir --bind count ${workdirBindCount}; goal ro-bind precedes seat bind: ${joined.indexOf(`--ro-bind ${f.goalDir} `) < joined.indexOf(`--bind ${f.seatDir} `)}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`wall probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
