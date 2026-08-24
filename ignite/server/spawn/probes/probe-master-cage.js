'use strict';

// D49 — master cage is truly-everything (workspace RW); D48 — worker peer-seat writes refuse.
// Driven through composeCageFor (the ONE composer both spawn doors use) against the SHIPPED
// cage.SeatBinds + cage.MasterBinds. Scratch fixture under os.tmpdir — never a live goal.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeCageFor } = require('../spawn');
const { buildBwrapArgv } = require('../bwrap');
const { parseSeatPath, parseServiceSeatPath } = require('../../seat-identity/seat-folder');

const PROFILES = path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml');

function shippedSandbox() {
  const cfg = yaml.load(fs.readFileSync(PROFILES, 'utf8'));
  if (!Array.isArray(cfg?.cage?.SeatBinds) || !Array.isArray(cfg?.cage?.MasterBinds)) {
    throw new Error('cage.SeatBinds or cage.MasterBinds absent from ' + PROFILES);
  }
  return { SeatBinds: cfg.cage.SeatBinds, MasterBinds: cfg.cage.MasterBinds };
}

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'master-cage-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'scratch-mcage');
  const masterDir = path.join(goalDir, 'seats', 'goal-master');
  const workerDir = path.join(goalDir, 'seats', 'worker');
  const peerDir = path.join(goalDir, 'seats', 'peer');
  const coordDir = path.join(goalDir, 'coordination');
  const cfgDir = path.join(ws, '.rbtv', 'config');
  const ordinary = path.join(ws, '1-projects', 'notes.md');
  const chanDir = path.join(ws, '.rbtv', 'goals', '_channel-master');
  for (const d of [masterDir, workerDir, peerDir, coordDir, cfgDir, path.dirname(ordinary), chanDir]) {
    fs.mkdirSync(d, { recursive: true });
  }
  fs.writeFileSync(path.join(masterDir, 'seat.md'),
    '---\nseat: goal-master\nread-root: true\nbus-write: true\ngoals-write: true\n---\nbriefing\n');
  fs.writeFileSync(path.join(workerDir, 'seat.md'), '---\nseat: worker\n---\nbriefing\n');
  fs.writeFileSync(path.join(peerDir, 'seat.md'), '---\nseat: peer\n---\nPEER\n');
  fs.writeFileSync(path.join(chanDir, 'seat.md'),
    '---\nseat: channel-master\nread-root: true\n---\nbriefing\n');
  fs.writeFileSync(path.join(coordDir, 'permission-edits.csv'), 'seat,path\n');
  fs.writeFileSync(ordinary, 'ORDINARY\n');
  fs.writeFileSync(path.join(cfgDir, '.env'), 'SECRET=do-not-read\n');
  fs.writeFileSync(path.join(cfgDir, 'private.json'), '{"deny":["keep-this-secret"]}\n');
  fs.writeFileSync(path.join(goalDir, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\n');
  fs.writeFileSync(path.join(ws, 'rbtv-standin.js'), 'RBTV-ORIGINAL\n');

  return { root, ws, goalDir, masterDir, workerDir, peerDir, coordDir, cfgDir, ordinary, chanDir };
}

function cageFor(sandbox, seatDir) {
  const parsed = parseSeatPath(seatDir) || parseServiceSeatPath(seatDir);
  return composeCageFor(sandbox, parsed, seatDir, '127.0.0.1:7431');
}

function inCage(seatDir, flags, script) {
  const argv = buildBwrapArgv({ argv: ['bash', '-c', script], workdir: seatDir, harness: null, seatBinds: flags });
  try {
    const stdout = execFileSync(argv[0], argv.slice(1), {
      stdio: ['ignore', 'pipe', 'pipe'], timeout: 30000, encoding: 'utf8',
    });
    return { exit: 0, stdout };
  } catch (err) {
    return {
      exit: err.status === undefined ? -1 : err.status,
      stdout: (err.stdout || '').toString(),
      stderr: (err.stderr || '').toString(),
    };
  }
}

function bytes(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch (err) { return `<<ABSENT:${err.code}>>`; }
}

capture('probe-master-cage', async (lines) => {
  const f = fixture();
  const sandbox = shippedSandbox();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    const master = cageFor(sandbox, f.masterDir);
    const worker = cageFor(sandbox, f.workerDir);
    const channel = cageFor(sandbox, f.chanDir);
    const MARK = `MCAGE-${Date.now()}`;

    const workerMark = path.join(f.peerDir, 'from-master.txt');
    inCage(f.masterDir, master, `echo ${MARK} > ${workerMark}`);
    leg('M1', 'master write into own-goal seats/<worker>/ lands on disk (outside the cage)',
      bytes(workerMark) === `${MARK}\n`,
      `host bytes=${JSON.stringify(bytes(workerMark))} path=composeCageFor FIXTURE`);

    const seatMd = path.join(f.masterDir, 'seat.md');
    inCage(f.masterDir, master, `echo ${MARK} >> ${seatMd}`);
    leg('M2', "master write into own seat.md lands on disk",
      bytes(seatMd).includes(MARK),
      `host includes marker=${bytes(seatMd).includes(MARK)}`);

    const perm = path.join(f.coordDir, 'permission-edits.csv');
    inCage(f.masterDir, master, `echo ${MARK} >> ${perm}`);
    leg('M3', 'master write into permission-edits.csv lands on disk',
      bytes(perm).includes(MARK),
      `host includes marker=${bytes(perm).includes(MARK)}`);

    inCage(f.masterDir, master, `echo ${MARK} >> ${f.ordinary}`);
    leg('M4', 'master write into an ordinary workspace path lands on disk',
      bytes(f.ordinary).includes(MARK),
      `host=${JSON.stringify(bytes(f.ordinary))}`);

    const rbtvStandin = path.join(f.ws, 'rbtv-standin.js');
    inCage(f.masterDir, master, `echo ${MARK} >> ${rbtvStandin}`);
    leg('M5', 'master write into a workspace file (rbtv-shaped) lands on disk',
      bytes(rbtvStandin).includes(MARK),
      `host includes marker=${bytes(rbtvStandin).includes(MARK)}`);

    const envOut = inCage(f.masterDir, master, `echo ENV=[$(cat ${path.join(f.cfgDir, '.env')} 2>/dev/null)]`);
    const privOut = inCage(f.masterDir, master, `echo PRIV=[$(cat ${path.join(f.cfgDir, 'private.json')} 2>/dev/null)]`);
    const envText = ((envOut.stdout || '') + (envOut.stderr || '')).trim();
    const privText = ((privOut.stdout || '') + (privOut.stderr || '')).trim();
    leg('M6', 'master cage still read-masks .env and private.json',
      /ENV=\[\]/.test(envText) && /PRIV=\[\]/.test(privText),
      `env=${JSON.stringify(envText)} priv=${JSON.stringify(privText)}`);

    const newPeer = path.join(f.goalDir, 'seats', 'newpeer', 'x.txt');
    const w = inCage(f.workerDir, worker, `mkdir -p ${path.dirname(newPeer)} && echo FAKE > ${newPeer}`);
    const erofs = w.exit !== 0 && /Read-only file system|EROFS|Permission denied|EACCES/i.test((w.stderr || '') + (w.stdout || ''));
    leg('W1', 'worker write into peer seats/ FAILS loudly and does not land (D48)',
      erofs && bytes(newPeer).startsWith('<<ABSENT'),
      `exit=${w.exit} stdout=${JSON.stringify((w.stdout || '').trim().slice(0, 80))} stderr=${JSON.stringify((w.stderr || '').trim().slice(0, 120))} host=${bytes(newPeer)}`);

    const seatsMask = worker.some((a, i) => a === '--ro-bind' && worker[i + 2] === path.join(f.goalDir, 'seats') && worker[i + 1] !== path.join(f.goalDir, 'seats'));
    const masterSeatsMask = master.some((a, i) => a === '--ro-bind' && master[i + 2] === path.join(f.goalDir, 'seats') && master[i + 1] !== path.join(f.goalDir, 'seats'));
    leg('W2', 'worker cage still ro-masks peer seats/; master cage does not',
      seatsMask && !masterSeatsMask,
      `worker-ro-mask=${seatsMask} master-ro-mask=${masterSeatsMask}`);

    const chanOrdinary = path.join(f.ws, '1-projects', 'chan.txt');
    inCage(f.chanDir, channel, `echo ${MARK} > ${chanOrdinary}`);
    leg('C1', 'channel-master (service seat) write into workspace lands on disk',
      bytes(chanOrdinary) === `${MARK}\n`,
      `host=${JSON.stringify(bytes(chanOrdinary))}`);

    // S1/S2/S2-control REMOVED (T2-R11, redesign D19, 2026-08-24): those legs asserted the D4
    // exposedCliCode pierce reaching a declared CLI's config.yaml/credentials/ for a master seat.
    // That pierce is deleted — credentials are env-injected, never caged — so this probe no longer
    // carries a stools-shaped fixture; M6 above already covers master cages still read-masking
    // `.env`/`private.json` unconditionally.

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    lines.push('evidence-class: composeCageFor production composer; FIXTURE scratch (os.tmpdir), not a live goal');
    if (fails.length > 0) throw new Error(`master-cage probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
