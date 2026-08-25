'use strict';

// WALL PROBES for the seat fence (D3, 2026-08-19). Pre-registered bars P8/P9, inverted
// where D3 superseded the anti-forgery rule.
//
// THE EVIDENCE RULE THIS FILE OBEYS (design §6, D51): every wall claim is proven ON DISK, from
// OUTSIDE the cage, by the target file being unchanged, grown, or absent. An in-cage error
// message proves only that something said no — it does not prove the kernel refused, and a
// probe that accepts the error message as evidence would pass just as happily against a wall
// made of comments.
//
// So each leg runs the write INSIDE bwrap, ignores whatever the shell reports, and then compares
// the target's bytes from the parent. The in-cage exit status is recorded for information and is
// never the pass condition.
//
// The bind template is the SHIPPED `cage.SeatBinds` (no inline copy — a third copy of the same
// fact is how this probe drifted). Grant lines without a matching grant are skipped.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { capture } = require('./lib');
const { composeSeatCage, specToBwrapFlags, composeAncestorMasks } = require('../cage');
const { buildBwrapArgv } = require('../bwrap');

const IGNITE_ROOT = path.resolve(__dirname, '..', '..', '..');
const PROFILES = path.join(IGNITE_ROOT, 'envelope', 'spawn-profiles.yaml');
const RBTV_ROOT = path.resolve(IGNITE_ROOT, '..');

function shippedSeatBinds() {
  const cfg = yaml.load(fs.readFileSync(PROFILES, 'utf8'));
  const binds = cfg?.cage?.SeatBinds;
  if (!Array.isArray(binds) || binds.length === 0) {
    throw new Error('cage.SeatBinds absent from ' + PROFILES);
  }
  return binds;
}

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'g4-cage-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'testgoal');
  const runDir = goalDir;
  const seatDir = path.join(runDir, 'seats', 'mine');
  const peerDir = path.join(runDir, 'seats', 'peer');
  const coordDir = path.join(runDir, 'coordination');
  const areasDir = path.join(ws, '2-areas', 'finance');
  const mirrorDir = path.join(ws, '.rbtv', 'mirror');
  const envDir = path.join(ws, '.rbtv', 'config');
  for (const d of [seatDir, peerDir, coordDir, areasDir, mirrorDir, envDir]) {
    fs.mkdirSync(d, { recursive: true });
  }

  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,pid,pid-starttime\nmine,1,1\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: mine\n---\nbriefing\n');
  fs.writeFileSync(path.join(peerDir, 'PEER-SECRET.md'), 'peer briefing nobody may read\n');
  fs.writeFileSync(path.join(goalDir, 'decisions.md'), 'rulings\n');
  fs.writeFileSync(path.join(coordDir, 'messages.md'), 'log\n');
  fs.writeFileSync(path.join(areasDir, 'notes.md'), 'AREA-ORIGINAL\n');
  fs.writeFileSync(path.join(mirrorDir, 'hello.md'), 'MIRROR\n');
  fs.writeFileSync(path.join(envDir, '.env'), 'SECRET=do-not-read\n');
  fs.writeFileSync(path.join(envDir, 'sender-token.env'), 'IGNITE_SENDER_TOKEN=SENDER-TOKEN-VALUE\n');
  fs.mkdirSync(path.join(ws, 'credentials'), { recursive: true });
  fs.writeFileSync(path.join(ws, 'credentials', 'key.txt'), 'CRED\n');

  const repo = path.join(ws, 'repo');
  fs.mkdirSync(repo, { recursive: true });
  fs.writeFileSync(path.join(repo, 'source.js'), 'ORIGINAL\n');

  const wtRoot = path.join(ws, '.rbtv', 'worktrees');
  const mineWt = path.join(wtRoot, `repo--testgoal--mine`);
  const peerWt = path.join(wtRoot, `repo--testgoal--peer`);
  fs.mkdirSync(mineWt, { recursive: true });
  fs.mkdirSync(peerWt, { recursive: true });
  fs.writeFileSync(path.join(peerWt, 'peer-work.txt'), 'PEER WORK\n');

  return { root, ws, goalDir, runDir, seatDir, peerDir, coordDir, repo, mineWt, peerWt, areasDir, envDir };
}

function cageFor(f, extraGrants = []) {
  const spec = composeSeatCage({
    seatBinds: shippedSeatBinds(),
    values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir },
    grants: [
      { worktree: f.mineWt, worktreeName: 'repo--testgoal--mine' },
      { rbtvRoot: RBTV_ROOT },
      { rbtvMirror: path.join(f.ws, '.rbtv', 'mirror') },
      ...extraGrants,
    ],
  });
  return specToBwrapFlags(spec);
}

function cageWithMasks(f, extraGrants = []) {
  const spec = composeSeatCage({
    seatBinds: shippedSeatBinds(),
    values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir },
    grants: [
      { worktree: f.mineWt, worktreeName: 'repo--testgoal--mine' },
      { readRoot: f.ws },
      { rbtvRoot: RBTV_ROOT },
      { rbtvMirror: path.join(f.ws, '.rbtv', 'mirror') },
      ...extraGrants,
    ],
  });
  const mask = composeAncestorMasks(spec, { workspaceRoot: f.ws, launchFolder: f.seatDir });
  return [...specToBwrapFlags(spec), ...mask.flags];
}

function inCage(f, script, binds) {
  const argv = buildBwrapArgv({
    argv: ['bash', '-c', script],
    workdir: f.seatDir,
    harness: null,
    seatBinds: binds || cageFor(f),
  });
  try {
    const stdout = execFileSync(argv[0], argv.slice(1), {
      stdio: ['ignore', 'pipe', 'pipe'], timeout: 30000, encoding: 'utf8',
    });
    return { exit: 0, stdout };
  } catch (err) {
    return {
      exit: err.status === undefined ? -1 : err.status,
      stderr: (err.stderr || '').toString().trim(),
      stdout: (err.stdout || '').toString(),
    };
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
    // ── P8c INVERTED (D3) — sessions.csv IS writable. The former unwritable + compose-time
    // refusal arms asserted the superseded anti-forgery rule. Record forgery is a non-goal.
    const groundTruth = path.join(f.runDir, 'sessions.csv');
    const before = bytes(groundTruth);
    const r8c = inCage(f, `echo "imposter,999,999" >> ${groundTruth}`);
    const after = bytes(groundTruth);
    leg('P8c', 'goal sessions.csv GREW by the appended row (D3: ledgers writable)',
      after !== before && after.includes('imposter,999,999'),
      `on-disk bytes ${after === before ? 'UNCHANGED — FENCE TOO TIGHT' : 'GREW'}; in-cage exit ${r8c.exit}`);

    const coordFile = path.join(f.coordDir, 'messages.md');
    const coordBefore = bytes(coordFile);
    inCage(f, `echo "a message" >> ${coordFile}`);
    leg('P8c-coord', 'coordination/ file GREW (D3 item 5: ledgers writable, no proxy)',
      bytes(coordFile) !== coordBefore && bytes(coordFile).includes('a message'),
      `coordination file ${JSON.stringify(bytes(coordFile).trim())}`);

    // ── P8a — a main-repo working file, outside the seat's own worktree.
    const src = path.join(f.repo, 'source.js');
    const srcBefore = bytes(src);
    const r8a = inCage(f, `echo TAMPERED > ${src}`);
    leg('P8a', 'main repo working file unchanged (outside the seat worktree)',
      bytes(src) === srcBefore && srcBefore === 'ORIGINAL\n',
      `content still ${JSON.stringify(bytes(src))} (in-cage exit ${r8a.exit})`);

    // ── P8-areas — a 2-areas-shaped path outside the allow-list.
    const areaFile = path.join(f.areasDir, 'notes.md');
    const areaBefore = bytes(areaFile);
    const rArea = inCage(f, `echo TAMPERED > ${areaFile}`);
    leg('P8-areas', '2-areas path unchanged / not writable (outside the allow-list)',
      bytes(areaFile) === areaBefore,
      `content still ${JSON.stringify(bytes(areaFile))} (in-cage exit ${rArea.exit})`);

    // ── P8b — another seat's worktree.
    const peerWork = path.join(f.peerWt, 'peer-work.txt');
    const peerBefore = bytes(peerWork);
    const r8b = inCage(f, `echo TAMPERED > ${peerWork}`);
    leg('P8b', "another seat's worktree unchanged",
      bytes(peerWork) === peerBefore,
      `content still ${JSON.stringify(bytes(peerWork))} (in-cage exit ${r8b.exit})`);

    // ── P8d + P9a — same-folder pair: seat.md unwritable, seat folder writable.
    const seatMd = path.join(f.seatDir, 'seat.md');
    const mdBefore = bytes(seatMd);
    const r8d = inCage(f, `echo "seat: someone-else" > ${seatMd}`);
    leg('P8d', "the seat's own seat.md unchanged (ro carve-in inside a RW folder)",
      bytes(seatMd) === mdBefore,
      `descriptor still ${JSON.stringify(bytes(seatMd).slice(0, 24))}… (in-cage exit ${r8d.exit})`);

    const artifact = path.join(f.seatDir, 'sessions', 'sess-1', 'out.txt');
    inCage(f, `mkdir -p ${path.dirname(artifact)} && echo ARTIFACT > ${artifact}`);
    leg('P9a', 'session artifact lands in sessions/{session-id}/ under the seat folder',
      bytes(artifact) === 'ARTIFACT\n', `artifact reads ${JSON.stringify(bytes(artifact))}`);

    // ── P8e — READ of a peer seat folder. Absence, not permission.
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

    const newPeerFile = path.join(f.runDir, 'seats', 'newpeer', 'x.txt');
    const rPeerWrite = inCage(f, `mkdir -p ${path.dirname(newPeerFile)} && echo FAKE > ${newPeerFile}`);
    const hostPeer = bytes(newPeerFile);
    leg('P8e-write', 'write into peer seats/ FAILS (EROFS/EACCES) and does not land on disk (D48)',
      rPeerWrite.exit !== 0 && hostPeer.startsWith('<<ABSENT'),
      `in-cage exit ${rPeerWrite.exit} stderr=${JSON.stringify((rPeerWrite.stderr || '').slice(0, 80))} host=${hostPeer}`);

    const wtFile = path.join(f.mineWt, 'work.txt');
    inCage(f, `echo WORK > ${wtFile}`);
    leg('P9b', "the seat's OWN worktree is writable", bytes(wtFile) === 'WORK\n',
      `worktree file reads ${JSON.stringify(bytes(wtFile))}`);

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

    // ── P-proc — in-fence /proc sees host pids (PID namespace gone, D3).
    let hostDaemonPid = '';
    try {
      hostDaemonPid = execFileSync('systemctl', ['--user', 'show', '-p', 'MainPID', '--value', 'rbtv-ignite'],
        { encoding: 'utf8', timeout: 10000 }).trim();
    } catch { hostDaemonPid = ''; }
    const procArm = hostDaemonPid && hostDaemonPid !== '0'
      ? inCage(f, `cat /proc/${hostDaemonPid}/comm 2>&1`)
      : { exit: -1, stdout: '', stderr: 'no-daemon-pid' };
    const comm = ((procArm.stdout || '') + (procArm.stderr || '')).trim();
    leg('P-proc', 'in-fence /proc sees the host daemon pid (PID namespace shared)',
      comm.length > 0 && !comm.includes('No such file') && !comm.includes('no-daemon-pid'),
      `host MainPID=${hostDaemonPid}; in-fence /proc/${hostDaemonPid}/comm=${JSON.stringify(comm)}`);

    // ── P-env — env absence, measured from inside the fence against the fixture
    // workspace (same layout as the real one). private-scope masks .env; sender-token stays.
    const envOut = inCage(f, [
      `echo "env=[$(cat ${path.join(f.envDir, '.env')} 2>/dev/null)]"`,
      `echo "cfg=$(ls ${f.envDir} 2>/dev/null | tr '\\n' ' ')"`,
      `echo "credkey=[$(cat ${path.join(f.ws, 'credentials', 'key.txt')} 2>/dev/null)]"`,
      `echo "sender=[$(cat ${path.join(f.envDir, 'sender-token.env')} 2>/dev/null)]"`,
    ].join('; '), cageWithMasks(f));
    const envText = ((envOut.stdout || '') + (envOut.stderr || ''));
    const envAbsent = /env=\[\]/.test(envText) || /env=\[\s*\]/.test(envText);
    const credsHidden = /credkey=\[\]/.test(envText);
    const senderOk = envText.includes('SENDER-TOKEN-VALUE');
    leg('P-env', '.env absent/empty, credentials/key unreadable, sender-token.env still resolves',
      envAbsent && credsHidden && senderOk,
      `in-cage: ${JSON.stringify(envText.trim().slice(0, 240))}`);

    const argv = buildBwrapArgv({ argv: ['bash', '-c', 'true'], workdir: f.seatDir, harness: null, seatBinds: cageFor(f) });
    const joined = argv.join(' ');
    const workdirBindCount = argv.filter((a, i) => a === '--bind' && argv[i + 1] === f.seatDir).length;
    const hasUnshareAll = argv.includes('--unshare-all');
    const hasUnshareUser = argv.includes('--unshare-user');
    const hasUnsharePid = argv.includes('--unshare-pid');
    leg('P-wiring', 'the seat stack replaces the flat workdir bind; PID ns is NOT unshared',
      workdirBindCount === 1 && !hasUnshareAll && hasUnshareUser && !hasUnsharePid
        && joined.indexOf(`--bind ${f.goalDir} `) < joined.indexOf(`--bind ${f.seatDir} `),
      `seatDir --bind count ${workdirBindCount}; unshare-all=${hasUnshareAll} unshare-user=${hasUnshareUser} unshare-pid=${hasUnsharePid}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`wall probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
