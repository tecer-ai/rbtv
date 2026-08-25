'use strict';

// Task 7.38 — THE KERNEL PROOF OF THE WORKTREE FLOW.
//
// probe-seat-cage.js (task 7.11) proved the cage over FAKE worktrees — plain directories with the
// right names. This probe proves it over REAL ones: a real git repo, real linked worktrees created
// by team-kit/worktree-flow.py, and the real `.git/worktrees/<name>` plumbing that a commit needs.
// It composes the cage from the SHIPPED template — the top-level shared cage.SeatBinds block
// (r-seats-only-architecture (1): the one sandbox shape, absorbed from the retired claude-seat
// profile), read out of config/spawn-profiles.yaml at run time — so what is proven is the thing
// that launches seats, not a copy of it pasted into a probe.
//
// THE EVIDENCE RULE (D51, and the row's own `_Criteria:_`): every wall claim is proven ON DISK
// from OUTSIDE the cage, by the target being unchanged or the file being ABSENT. The in-cage exit
// status and whatever the shell printed are recorded for information and are never the pass
// condition — a wall made entirely of comments produces the same error message as a real one.
//
// Each absence is read TWO DIFFERENTLY-KEYED WAYS (strategy A-3): once PATH-keyed (stat the exact
// path) and once LISTING-keyed (read the parent directory and look for the name). A single read
// that is silently broken — a typo'd path, a swallowed exception — reports absence for a file
// that is sitting right there. And both readers are put through a POSITIVE CONTROL on the same
// run: the write to the seat's OWN worktree, which MUST land and which both readers must SEE.
// An absence proven by readers that have not been shown to detect presence is not proven.
//
// GRANTS. The grant records handed to composeSeatCage are built here by the rule spawn.js states
// at :246-291 — a worktree is this seat's iff its directory name ends `--{goal}--{seat}`, and the
// git plumbing paths are read out of the worktree's own `.git` file. That resolver
// (resolveSeatGrants) is not exported, so this probe does not re-prove the RESOLVER; it proves the
// CAGE over the real directories the resolver reads. The resolver's own coverage is 7.11's.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { capture } = require('./lib');
const { requirePythonCmd } = require('../../../runtime/python-cmd');
const { composeSeatCage, specToBwrapFlags } = require('../cage');
const { buildBwrapArgv } = require('../bwrap');

const IGNITE_ROOT = path.resolve(__dirname, '..', '..', '..');
const PROFILES = path.join(IGNITE_ROOT, 'envelope', 'spawn-profiles.yaml');
const FLOW = path.join(IGNITE_ROOT, 'team-kit', 'worktree-flow.py');

const GOAL = 'probegoal';
const MINE = 'mine';
const PEER = 'peer';

function sh(cmd, args, cwd) {
  return execFileSync(cmd, args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
}

// The SHIPPED bind template. Read from the config the daemon reads; a probe that inlined the list
// would keep passing after someone edited the real one.
function shippedSeatBinds() {
  const cfg = yaml.load(fs.readFileSync(PROFILES, 'utf8'));
  const binds = cfg?.cage?.SeatBinds;
  if (!Array.isArray(binds) || binds.length === 0) {
    throw new Error('cage.SeatBinds (the shared seat-cage template, r-seats-only-architecture) absent from ' + PROFILES);
  }
  return binds;
}

// A real workspace: a real repo with a real working tree, a goal/run/seat tree, and two real
// linked worktrees produced by the flow tool itself.
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'r2-738-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', GOAL);
  const runDir = goalDir;   // 7.607 E2a — goal-direct: the goal folder IS the package
  const seatDir = path.join(runDir, 'seats', MINE);
  const peerSeatDir = path.join(runDir, 'seats', PEER);
  const coordDir = path.join(runDir, 'coordination');
  for (const d of [seatDir, peerSeatDir, coordDir]) fs.mkdirSync(d, { recursive: true });
  // 7.607 E2a — the `tmpfs:{goalDir}/runs` template line needs its mountpoint to EXIST: with
  // {goalDir} ro-bound, bwrap refuses `Can't mkdir <goalDir>/runs: Read-only file system`.
  // spawn.js#composeCageFor creates it for every real seat; this fixture mirrors that. Both
  // go away with the profile's template line (see the E2a note in spawn.js).
  fs.mkdirSync(path.join(goalDir, 'runs'), { recursive: true });
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,pid,pid-starttime\nmine,1,1\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: mine\n---\nbriefing\n');
  fs.writeFileSync(path.join(goalDir, 'decisions.md'), 'rulings\n');
  fs.writeFileSync(path.join(goalDir, 'goal.md'), '---\nrepos:\n  - repo\n---\n');

  const repo = path.join(ws, 'repo');
  fs.mkdirSync(repo, { recursive: true });
  sh('git', ['init', '-q', '-b', 'main', '.'], repo);
  sh('git', ['config', 'user.email', 'probe@local'], repo);
  sh('git', ['config', 'user.name', 'probe'], repo);
  fs.writeFileSync(path.join(repo, 'source.js'), 'ORIGINAL\n');
  sh('git', ['add', 'source.js'], repo);
  sh('git', ['commit', '-q', '-m', 'base'], repo);

  // THE FLOW UNDER TEST creates the worktrees — not this probe by hand.
  const flow = (...args) => sh(requirePythonCmd(), [FLOW, ...args, '--ws', ws, '--repo', repo, '--goal', GOAL], ws);
  flow('open-goal');
  flow('open-seat', '--seat', MINE);
  flow('open-seat', '--seat', PEER);

  const wtRoot = path.join(ws, '.rbtv', 'worktrees');
  const mineWt = path.join(wtRoot, `repo--${GOAL}--${MINE}`);
  const peerWt = path.join(wtRoot, `repo--${GOAL}--${PEER}`);
  fs.writeFileSync(path.join(peerWt, 'peer-work.txt'), 'PEER WORK\n');

  return { root, ws, goalDir, runDir, seatDir, coordDir, repo, wtRoot, mineWt, peerWt };
}

// spawn.js:246-291's rule, applied to the real directories. Suffix match on the seat's own name;
// plumbing read out of the worktree's own `.git` file, never guessed.
function grantsFor(f, seat) {
  const suffix = `--${GOAL}--${seat}`;
  const grants = [];
  for (const entry of fs.readdirSync(f.wtRoot, { withFileTypes: true })) {
    if (!entry.isDirectory() || !entry.name.endsWith(suffix)) continue;
    const worktree = path.join(f.wtRoot, entry.name);
    const grant = { worktree, worktreeName: entry.name };
    const dotGit = fs.readFileSync(path.join(worktree, '.git'), 'utf8').trim();
    const m = /^gitdir:\s*(.+)$/.exec(dotGit);
    if (m) {
      const gitdir = m[1].trim();
      const marker = `${path.sep}worktrees${path.sep}`;
      const idx = gitdir.lastIndexOf(marker);
      if (idx > 0) {
        grant.repoGit = gitdir.slice(0, idx);
        grant.worktreeGitDir = gitdir;
      }
    }
    grants.push(grant);
  }
  return grants;
}

function cageFlags(f) {
  const spec = composeSeatCage({
    seatBinds: shippedSeatBinds(),
    values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir, runDir: f.runDir },
    grants: grantsFor(f, MINE),
  });
  return { spec, flags: specToBwrapFlags(spec) };
}

function inCage(f, script) {
  const argv = buildBwrapArgv({
    argv: ['bash', '-c', script],
    workdir: f.mineWt,
    harness: null,
    seatBinds: cageFlags(f).flags,
  });
  try {
    const stdout = execFileSync(argv[0], argv.slice(1),
      { stdio: ['ignore', 'pipe', 'pipe'], timeout: 60000, encoding: 'utf8' });
    return { exit: 0, stdout };
  } catch (err) {
    return { exit: err.status === undefined ? -1 : err.status, stderr: String(err.stderr || '').trim() };
  }
}

// ── the two differently-keyed readers, both used for absence AND for the positive control ──
function readByPath(p) {
  try { fs.statSync(p); return true; } catch { return false; }
}
function readByListing(p) {
  try { return fs.readdirSync(path.dirname(p)).includes(path.basename(p)); } catch { return false; }
}
function bytes(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch (err) { return `<<ABSENT:${err.code}>>`; }
}

capture('probe-worktree-flow', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    const { spec } = cageFlags(f);
    lines.push('composed cage (shipped shared cage.SeatBinds template, real grants):');
    for (const e of spec) lines.push(`       ${e.verb} ${e.path}`);
    lines.push('');

    // ── W-1 — MAIN'S WORKING TREE. The file a seat must never be able to edit, and the new file
    // it must never be able to create beside it.
    const mainFile = path.join(f.repo, 'source.js');
    const mainNew = path.join(f.repo, 'INTRUDER-main.txt');
    const beforeMain = bytes(mainFile);
    const r1 = inCage(f, `echo BREACHED > ${mainFile}; echo BREACHED > ${mainNew}; exit 0`);
    leg('W-1a', "main's tracked working file is unchanged on disk",
      bytes(mainFile) === beforeMain && beforeMain === 'ORIGINAL\n',
      `bytes ${JSON.stringify(bytes(mainFile))} (was ${JSON.stringify(beforeMain)}); in-cage exit ${r1.exit}, not the evidence`);
    leg('W-1b', 'no new file appeared in main\'s working tree — PATH-keyed and LISTING-keyed',
      !readByPath(mainNew) && !readByListing(mainNew),
      `stat=${readByPath(mainNew)} listing=${readByListing(mainNew)} for ${mainNew}`);

    // ── W-2 — ANOTHER SEAT'S WORKTREE.
    const peerFile = path.join(f.peerWt, 'peer-work.txt');
    const peerNew = path.join(f.peerWt, 'INTRUDER-peer.txt');
    const beforePeer = bytes(peerFile);
    const r2 = inCage(f, `echo BREACHED > ${peerFile}; echo BREACHED > ${peerNew}; exit 0`);
    leg('W-2a', "the peer seat's worktree file is unchanged on disk",
      bytes(peerFile) === beforePeer && beforePeer === 'PEER WORK\n',
      `bytes ${JSON.stringify(bytes(peerFile))}; in-cage exit ${r2.exit}, not the evidence`);
    leg('W-2b', "no new file appeared in the peer's worktree — PATH-keyed and LISTING-keyed",
      !readByPath(peerNew) && !readByListing(peerNew),
      `stat=${readByPath(peerNew)} listing=${readByListing(peerNew)} for ${peerNew}`);

    // ── W-3 — THE POSITIVE CONTROL (C-3). The seat's OWN worktree MUST be writable, and both
    // readers above must SEE the file. Without this leg, W-1b/W-2b prove only that the readers
    // are capable of saying "absent".
    const mineNew = path.join(f.mineWt, 'seat-work.txt');
    const r3 = inCage(f, `echo "SEAT WORK" > ${mineNew}`);
    leg('W-3', "POSITIVE CONTROL — a write to the seat's OWN worktree DOES land, and both readers see it",
      readByPath(mineNew) && readByListing(mineNew) && bytes(mineNew) === 'SEAT WORK\n',
      `stat=${readByPath(mineNew)} listing=${readByListing(mineNew)} bytes=${JSON.stringify(bytes(mineNew))} (in-cage exit ${r3.exit})`);

    // ── W-4 — a real COMMIT from inside the cage. This is what the W3 plumbing openings exist
    // for: without them the seat's worktree would be writable but useless.
    const r4 = inCage(f, `cd ${f.mineWt} && git -c user.email=s@l -c user.name=s add seat-work.txt && ` +
      `git -c user.email=s@l -c user.name=s commit -q -m "in-cage commit" && git rev-parse HEAD`);
    const head = sh('git', ['rev-parse', `goal/${GOAL}/${MINE}`], f.repo).trim();
    const subject = sh('git', ['log', '-1', '--format=%s', `goal/${GOAL}/${MINE}`], f.repo).trim();
    leg('W-4', 'a commit made INSIDE the cage is visible on the seat branch from outside',
      subject === 'in-cage commit',
      `goal/${GOAL}/${MINE} @ ${head.slice(0, 12)} subject ${JSON.stringify(subject)} (in-cage exit ${r4.exit})`);

    // ── W-5 — the `.git` ROOT stays read-only, which is what kernel-blocks fetch/push/gc from
    // inside the cage and makes "no per-seat remote pushes" (R25) true below the review layer.
    const gitNew = path.join(f.repo, '.git', 'INTRUDER-config.txt');
    const r5 = inCage(f, `echo BREACHED > ${gitNew}; exit 0`);
    leg('W-5', "no new file appeared at the repo's .git ROOT — PATH-keyed and LISTING-keyed",
      !readByPath(gitNew) && !readByListing(gitNew),
      `stat=${readByPath(gitNew)} listing=${readByListing(gitNew)} for ${gitNew} (in-cage exit ${r5.exit})`);

    // ── W-6 — the flow's own cleanup, seen through the cage's eyes: after merge-seat the seat's
    // worktree is gone, so the grant that opened it resolves to nothing. Zero grants is the
    // correct answer for a closed seat, and it is reached without a special case.
    sh(requirePythonCmd(), [FLOW, 'merge-seat', '--ws', f.ws, '--repo', f.repo, '--goal', GOAL, '--seat', MINE], f.ws);
    const after = grantsFor(f, MINE);
    leg('W-6', 'after merge-seat the seat holds NO grant — cleanup closes the opening too',
      after.length === 0 && !readByPath(f.mineWt) && !readByListing(f.mineWt),
      `grants=${after.length} stat=${readByPath(f.mineWt)} listing=${readByListing(f.mineWt)} for ${f.mineWt}`);

    if (fails.length) throw new Error(`legs failed: ${fails.join(', ')}`);
  } finally {
    lines.push('');
    lines.push(`fixture: ${f.root}`);
    fs.rmSync(f.root, { recursive: true, force: true });
  }
});
